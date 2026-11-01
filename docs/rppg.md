# rPPG (Remote Photoplethysmography) in the Video KYC Pipeline

## What is rPPG?

Remote photoplethysmography estimates a person's pulse from a normal
video of their face, with no contact sensor. Each heartbeat pushes a
small pulse of blood into the facial skin's capillaries, which very
slightly changes how much light the skin absorbs and reflects. That
change is far too subtle to see by eye, but it shows up as a tiny,
periodic oscillation in the average color of the skin across
successive video frames -- strongest in the green channel, which is
closest to hemoglobin's absorption peak. Recovering that oscillation
and turning it into a heart-rate estimate is rPPG.

## Why is rPPG useful in Video KYC?

A live person has a real, physiologically plausible, periodic pulse
signal. Several common attacks on a Video KYC flow do not:

- **A static or printed photograph** has no blood flow at all, so
  there is no periodic signal to recover.
- **A screen replay** (a phone or monitor showing a pre-recorded
  video) reproduces the *visual appearance* of a face but re-encodes,
  compresses, and displays it in ways that typically corrupt or
  destroy the very subtle color signal rPPG depends on.
- **Some synthetic/manipulated video** does not reproduce a
  physiologically consistent pulse, because generative models are
  optimized for visual realism, not for preserving sub-millimeter
  color dynamics tied to blood flow.

rPPG is therefore added as **one more independent signal** in the
liveness assessment, alongside blink detection and head-turn
detection (see `app/ml/liveness.py`). It is deliberately **not**
treated as a standalone deepfake or spoof detector anywhere in this
codebase -- `app/ml/rppg.py`'s docstring says so explicitly, and its
score only ever contributes a sentence to the risk explanation (see
"Risk-engine integration" below), never a pass/fail verdict on its
own.

## How rPPG works in this project

Implemented in `backend/app/ml/rppg.py`, using OpenCV, NumPy, SciPy
and MediaPipe -- no new heavy dependency was introduced.

1. **Face ROI selection** (`extract_face_roi_frames`): MediaPipe Face
   Mesh locates facial landmarks in each frame, and a **forehead
   band** (30%-70% of face width, 5%-25% of face height from the top)
   is cropped out. The forehead is used instead of the whole face
   because it has almost no expression-driven motion (no eyelids,
   lips, or jaw), so most of its remaining color variation really is
   the pulse rather than motion artifacts.
2. **RGB signal extraction** (`extract_rgb_signal`): the mean R, G,
   and B value of the ROI in each frame, giving a (T, 3) time series.
3. **Preprocessing** (`preprocess_signal`): a per-channel linear
   detrend removes slow lighting drift (e.g. a camera's auto-exposure
   slowly adjusting) that would otherwise swamp the much smaller pulse
   signal.
4. **CHROM projection** (`apply_pos_or_chrom`): implements the CHROM
   method (de Haan & Jeanne, 2013). CHROM was chosen over POS because
   its single closed-form linear combination of normalized RGB
   channels is simpler to implement correctly for one short clip than
   POS's sliding-window formulation, while offering comparable
   robustness for this use case -- a deliberate "prefer the lightweight
   implementation" choice for an academic prototype.
5. **Band-pass filtering** (`_bandpass_filter`): a Butterworth filter
   restricts the waveform to the physiological frequency band
   (`RPPG_MIN_BPM`-`RPPG_MAX_BPM`, default 40-180 BPM), removing
   frequencies no real heartbeat could produce.
6. **Heart-rate estimation** (`estimate_heart_rate`): a Welch
   power-spectral-density estimate finds the dominant frequency in
   that band; its frequency converted to BPM is the heart-rate
   estimate, and the fraction of total spectral power concentrated at
   that peak is the `periodicity_score` -- a real, computed measure of
   how "clean"/sinusoidal the signal is, not an invented confidence
   number.
7. **Cross-checks**: `_temporal_consistency` independently estimates
   the heart rate on the first and second half of the clip and checks
   they agree; `_roi_stability` checks the forehead ROI didn't move or
   resize erratically (camera shake, head motion, tracking failure).
8. **Feature assembly** (`calculate_signal_quality`,
   `calculate_rppg_features`): combines the above into
   `signal_quality` (0-1, a general "is this recording usable" score)
   and `rppg_score` (0-1, the overall confidence this looks like a
   genuine live pulse).

## Statuses returned

`analyze_rppg()` always returns one of:

| Status | Meaning |
|---|---|
| `AVAILABLE` | A reliable pulse signal was recovered; `heart_rate_bpm` is populated. |
| `INSUFFICIENT_SIGNAL` | The clip was too short, the face wasn't visible enough, no periodic signal was found, or the computed signal quality was below `RPPG_MIN_SIGNAL_QUALITY`. `heart_rate_bpm` is always `None` in this case -- an unreliable estimate is never reported as if it were trustworthy. |
| `UNAVAILABLE` | No frames were given, or a required dependency (mediapipe/scipy) isn't installed in this environment. |

All thresholds (`RPPG_MIN_FRAMES`, `RPPG_MIN_FACE_DETECTION_RATIO`,
`RPPG_MIN_SIGNAL_QUALITY`, `RPPG_MIN_BPM`/`MAX_BPM`,
`RPPG_DEFAULT_FPS_FALLBACK`) live in `app/core/config.py` and are
read from the environment like every other risk/liveness threshold in
this project -- nothing is a magic number scattered in `rppg.py`.

## How rPPG contributes to liveness and the fraud-risk decision

rPPG results are persisted per-case in the `rppg_results` table
(status, heart rate, signal quality, periodicity, temporal
consistency, rPPG score, usable-frame counts, method version -- never
the raw signal or any video frame, consistent with this project's "no
raw biometric video/signal stored" privacy rule) and returned
alongside every other module's result from `GET /api/kyc/{case_id}`
and the verification report.

### Risk-engine integration (important limitation, by design)

The deployed `risk_model.joblib` was trained on exactly seven
features (`document_authenticity_score`, `tampering_probability`,
`face_similarity`, `face_quality`, `liveness_passed`,
`deepfake_probability`, `replay_probability` -- see
`app/ml/risk_engine.py::FEATURE_NAMES`). Adding an eighth feature to
that vector without retraining would silently invalidate every
prediction the model makes, so **rPPG is intentionally not fed into
the trained model's numeric score**. `compute_risk()` accepts an
optional `rppg` argument and uses it **only** to add a sentence to the
human-readable explanation when a reading was actually `AVAILABLE`
(e.g. "a physiological pulse signal (rPPG, ~74 BPM) consistent with a
live recording was also detected"). It is never mentioned when the
status isn't `AVAILABLE`, since there is nothing genuine to report in
that case.

This is verified by an automated test
(`test_risk_engine_accepts_optional_rppg_without_changing_feature_vector`
in `app/tests/test_rppg.py`): the same inputs produce byte-identical
`fraud_risk_score` and `risk_level` whether or not an rPPG reading is
supplied.

**Planned future step** (not yet done): retrain `risk_model.joblib`
with `rppg_score` as an eighth synthetic-data feature via
`ml/training/generate_synthetic_data.py` +
`ml/training/train_risk_model.py`, at which point `compute_risk()` can
be updated to include it in the numeric feature vector too. Until
that retraining happens, the existing model continues to work exactly
as before.

## Why rPPG is not a standalone deepfake detector

A weak or absent rPPG signal is *evidence toward* a video being a
non-live presentation, but it is not proof: poor lighting, heavy
camera compression, a very short clip, significant head movement, or
certain skin tones/makeup can all degrade or hide a genuine pulse
signal in a real live video. Conversely, some replay/synthesis
methods might partially preserve enough color dynamics to produce a
plausible-looking (but not necessarily physiologically real) periodic
signal. For these reasons rPPG is combined with -- and never replaces
-- blink/head-turn liveness, the dedicated deepfake classifier, and
replay detection; the fraud-risk engine and a human reviewer make the
final call using all signals together, not rPPG alone.

## Limitations

- Sensitive to lighting changes, compression artifacts, low frame
  rate, and significant head/camera motion.
- The forehead-ROI heuristic is a simplification; it does not track
  the skin region as precisely as full facial-landmark-based ROI
  selection used in some research implementations.
- CHROM (not POS) was implemented, and as a single-window (not
  sliding-window) computation -- appropriate for a short KYC clip, but
  not directly comparable to multi-minute clinical rPPG setups.
- No accuracy/benchmark numbers are claimed anywhere in this project
  for rPPG, because no ground-truth heart-rate dataset was used to
  validate it end-to-end; only the underlying signal-processing math
  itself is verified against synthetic signals with a known, injected
  heart rate (see `app/tests/test_rppg.py`).
- Not evaluated for fairness across skin tones, an acknowledged
  limitation of camera-based PPG methods generally.

## Updated technology pipeline

```
OCR                 -> EasyOCR
Face Detection      -> MediaPipe
Face Recognition    -> InsightFace (ArcFace)
Liveness            -> Motion + Blink (MediaPipe) + rPPG (CHROM)
Replay Detection    -> OpenCV (moire/FFT + temporal consistency)
Deepfake Detection  -> EfficientNet-B0
Explainability      -> SHAP (risk model) / Grad-CAM (deepfake frames)
Risk Decision       -> XGBoost (trained on synthetic data) + rule-based explanation
```

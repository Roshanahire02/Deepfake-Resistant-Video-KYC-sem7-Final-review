# Pending tasks, limitations and demo checklist

## Verification status at packaging time (honest)
- RAN and PASSED on a clean extracted copy with a fresh venv from `requirements-lite.txt`: **55/55 backend tests**,
  **30/30 frontend tests**, **frontend build OK**.
- **NOT COMPLETED:** the final scripted live walk-through (start both servers, log in as all 3 demo roles, PDF upload,
  video, reviewer, admin) on the clean copy **timed out in the sandbox and produced no result**. The same endpoints are
  covered by the automated backend tests, but a full live click-through of the packaged copy is not confirmed.
  Do this first on your laptop: run `setup.bat`, `start-backend.bat`, `start-frontend.bat`, then follow the checklist below.
- The Windows `.bat` scripts and a real Windows install have not been run.

## What is implemented and tested
Auth + roles (USER/REVIEWER/ADMIN), rate limiting, case management, PDF/JPG/PNG upload with content
validation, document tampering analysis, liveness (MediaPipe), rPPG (CHROM), replay heuristics, SHAP
explainable risk score (model trained on **synthetic** data), reviewer console, admin role page, report
download, honest Model Status page, temporary-video deletion (verified by tests).

## Honest limitations (what is NOT done / NOT verified)
- **Deepfake model is not trained** -> always `TRAINING REQUIRED`; no probability is shown or used.
- **OCR (EasyOCR) and face matching (InsightFace) were never run** in the development sandbox - they are
  coded, but untested on real input. Without them installed the app reports UNAVAILABLE, and a case can
  never be auto-VERIFIED (it goes to MANUAL REVIEW by design).
- **Liveness and rPPG were only tested with synthetic/blank video**, not a real webcam face; thresholds are untuned.
- **No real evaluation metrics exist** (accuracy, APCER/BPCER, FAR/FRR): all "Not evaluated yet". The only
  model metrics shown are for the risk model on SYNTHETIC data, labelled as such.
- Risk model is trained on synthetic data; it is not real-world fraud detection.
- Browser-recorded WebM files could not be generated in the sandbox; frame-rate handling for them is unit-tested
  but not tested with a real Chrome recording.
- Uploaded ID document images stay in `backend/storage/uploads` until you run `reset_demo_data` (raw VIDEO is deleted).
- Windows `.bat` scripts and the Windows install were **not run** (developed on Linux); the Linux equivalent
  of every step was run from a clean extracted copy.
- Docker, PostgreSQL and the full `requirements.txt` (torch/EasyOCR/InsightFace) were never tested.
- No refresh tokens; rate limiter is in-memory (single process).

## Pending development (next phase)
1. Complete README (this one is short) and write the AI training guide.
2. docker-compose.yml; test Docker and PostgreSQL.
3. Install EasyOCR + InsightFace on a real machine; test OCR and face matching with real images.
4. Test liveness + rPPG with real webcam recordings; tune thresholds.
5. Train the deepfake model (FaceForensics++/Celeb-DF subset, GPU): `ml/training/prepare_deepfake_dataset.py`
   then `ml/training/train_deepfake_model.py` (written, never run).
6. Run `ml/evaluation/*` scripts on labelled data to get real metrics.
7. Optional: refresh tokens, Redis rate limiting, cleaning old uploads automatically.

## Teacher demo checklist (suggested order, ~10 min)
1. Start backend + frontend; open http://localhost:5173 and http://localhost:8000/docs.
2. Sign in as the **applicant** -> Dashboard -> **New Verification** -> create case.
3. Upload the mock ID (or any JPG/PNG/PDF) -> show tampering score; note OCR/face = UNAVAILABLE if not installed.
4. Video step: tick consent, **record 5 s from the camera** (or upload a clip) -> watch real stage progress.
5. Open the case: tabs (Document, Liveness, rPPG, Replay, Deepfake = TRAINING REQUIRED, Risk, Explainability/SHAP).
6. Download the report.
7. Sign out; sign in as **reviewer** -> queue -> case -> Approve/Reject/Manual review.
8. Sign in as **admin** -> Users & Roles.
9. Show **Model Status** (honest states + "Not evaluated yet") and say what is untrained/untested.

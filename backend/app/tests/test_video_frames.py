import cv2
import numpy as np

from app.utils.video_frames import estimate_fps, extract_frames


def test_measured_timestamps_win_over_garbage_header():
    ts = [i * (1000 / 25) for i in range(30)]  # frames actually 25 fps
    assert abs(estimate_fps(ts, reported_fps=1000.0) - 25.0) < 0.01  # header says 1000 (typical browser webm)
    assert abs(estimate_fps(ts, reported_fps=0.0) - 25.0) < 0.01


def test_plausible_header_used_when_timestamps_unusable():
    assert estimate_fps([0.0] * 30, reported_fps=30.0) == 30.0       # all-zero timestamps
    assert estimate_fps([5, 4, 3, 2, 1, 0, 9, 8, 7, 6], 24.0) == 24.0  # non-monotonic


def test_implausible_everything_reports_unknown_not_garbage():
    assert estimate_fps([0.0] * 30, reported_fps=1000.0) == 0.0
    assert estimate_fps([0.0] * 30, reported_fps=0.0) == 0.0
    assert estimate_fps([], reported_fps=None) == 0.0


def test_extract_frames_measures_real_fps(tmp_path):
    path = str(tmp_path / "v.mp4")
    w = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*"mp4v"), 20, (64, 48))
    for _ in range(40):
        w.write(np.zeros((48, 64, 3), np.uint8))
    w.release()
    frames, fps = extract_frames(path)
    assert len(frames) == 40 and abs(fps - 20.0) < 0.5

# Deepfake-Resistant Video KYC Verification System Using AI

B.Tech final-year academic prototype: document verification, face matching, liveness
(blink/head-turn + rPPG), replay and deepfake detection, and an explainable (SHAP) fraud-risk
score, with a reviewer console. **Not connected to any real Aadhaar/PAN/bank/government system.**
This README is the short version; the full README is a pending task (see `PENDING_TASKS.md`).

Stack: React + Vite + Tailwind (frontend) - FastAPI + SQLAlchemy (backend) - **SQLite** database.

## Windows quick start

Requirements: **Python 3.10-3.12** (tick "Add to PATH") and **Node.js 20.19+ or 22.12+**.

**Option A - scripts** (double-click, first one only once):
1. `setup.bat`
2. `start-backend.bat` (leave open)
3. `start-frontend.bat` (leave open)

**Option B - manual commands** (two terminals, from the project folder):
```
:: one-time backend setup
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements-lite.txt
python -m app.scripts.setup_env
python -m app.scripts.seed_demo

:: start backend (Terminal 1)
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

:: one-time frontend setup + start (Terminal 2)
cd frontend
npm install
npm run dev
```
Open **http://localhost:5173** - API docs: **http://localhost:8000/docs**

`requirements-lite.txt` is the demo install. `requirements.txt` adds EasyOCR, InsightFace, torch
(several GB; InsightFace may need "Microsoft C++ Build Tools"). Without them, OCR and face matching show
**UNAVAILABLE** and the deepfake model shows **TRAINING REQUIRED** - the app never fakes those results.

## Demo accounts (local demo only, created by `seed_demo`)
| Role | Email | Password |
|---|---|---|
| Applicant | demo.user@example.com | DemoUser#2026 |
| Reviewer | demo.reviewer@example.com | DemoReviewer#2026 |
| Admin | demo.admin@example.com | DemoAdmin#2026 |

## Mock ID for the face-match demo (uses your own selfie, no real ID needed)
```
cd backend
venv\Scripts\activate
python tools\make_sample_id.py C:\path\to\your_selfie.jpg "YOUR NAME" 2000-01-31 --out sample_id.png
```
Upload `sample_id.png` in New Verification. (Face matching also needs InsightFace - see above.)

## Reset demo data / run tests
```
cd backend && venv\Scripts\activate
python -m app.scripts.reset_demo_data          (wipes database + uploads)
pytest                                         (backend tests)
cd ..\frontend && npm test && npm run build    (frontend tests + build)
```

## Troubleshooting
- **`pip install` fails on mediapipe / "no matching distribution"** -> wrong Python version; use 3.10-3.12 (`python --version`).
- **`npm run dev` error about Node version** -> upgrade Node to 20.19+ / 22.12+.
- **Browser shows "Network error" / 502** -> the backend is not running; start `start-backend.bat` and keep it open.
- **Port 8000 or 5173 already in use** -> close the other program, or restart your PC.
- **Camera not working** -> allow camera permission in the browser; use Chrome/Edge on `http://localhost:5173`.
- **Forgot demo passwords / broken data** -> `python -m app.scripts.reset_demo_data --yes` then `python -m app.scripts.seed_demo`.
- **PowerShell blocks `venv\Scripts\activate`** -> run `Set-ExecutionPolicy -Scope Process Bypass`, or use Command Prompt (cmd).

## Database migrations (optional)
The app creates its tables automatically. Alembic is also set up: `cd backend && alembic upgrade head`.

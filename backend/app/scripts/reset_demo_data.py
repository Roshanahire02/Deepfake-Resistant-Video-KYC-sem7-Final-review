"""
Wipes ALL local demo data: the SQLite database, uploaded documents, temp videos
and generated Grad-CAM images. Trained models are NOT touched.

    python -m app.scripts.reset_demo_data        (asks for confirmation)
    python -m app.scripts.reset_demo_data --yes
"""
from __future__ import annotations

import os
import shutil
import sys

from app.core.config import settings


def main() -> None:
    if "--yes" not in sys.argv and input("Delete the local database and all uploaded files? type 'yes': ").strip().lower() != "yes":
        print("Cancelled.")
        return
    url = settings.DATABASE_URL
    if url.startswith("sqlite:///"):
        db_file = url[len("sqlite:///"):]
        if os.path.isfile(db_file):
            os.remove(db_file)
            print("Deleted", db_file)
    for d in (settings.UPLOAD_DIR, settings.TEMP_VIDEO_DIR, os.path.join(settings.MODEL_DIR, "gradcam")):
        if os.path.isdir(d):
            for name in os.listdir(d):
                if name.startswith("."):
                    continue
                p = os.path.join(d, name)
                shutil.rmtree(p) if os.path.isdir(p) else os.remove(p)
            print("Emptied", d)
    print("Done. Restart the backend and run seed_demo again if you want the demo accounts back.")


if __name__ == "__main__":
    main()

from typing import Optional, Dict, Any

from pydantic import BaseModel


class ReplayResultOut(BaseModel):
    replay_probability: Optional[float] = None
    status: Optional[str] = None
    signals: Optional[Dict[str, Any]] = None

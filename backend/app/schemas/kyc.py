from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class KYCCaseOut(BaseModel):
    id: str
    status: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class KYCCaseSummary(BaseModel):
    total_cases: int
    verified: int
    pending: int
    flagged: int

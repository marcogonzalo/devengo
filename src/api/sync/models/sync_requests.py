from typing import Optional, List, Dict, Any
from pydantic import BaseModel

class SyncStepRequest(BaseModel):
    step: str
    year: Optional[int] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    month: Optional[int] = None

class SyncProcessRequest(BaseModel):
    process_type: str  # "import" or "accrual"
    steps: List[str]
    year: Optional[int] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    month: Optional[int] = None

class SyncStatusResponse(BaseModel):
    status: str
    message: str
    data: Optional[Dict[str, Any]] = None
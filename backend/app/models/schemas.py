from pydantic import BaseModel
from typing import Optional
from enum import Enum

class JobStatusEnum(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETE = "complete"
    FAILED = "failed"

class JobCreationResponse(BaseModel):
    job_id: str

class JobStatusResponse(BaseModel):
    job_id: str
    status: JobStatusEnum
    message: Optional[str] = None
    filename: Optional[str] = None

class Voice(BaseModel):
    name: str
    short_name: str

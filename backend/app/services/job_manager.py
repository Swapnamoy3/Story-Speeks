import threading
import uuid
from typing import Dict, Optional
from ..models.schemas import JobStatusEnum

class JobManager:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._jobs: Dict[str, Dict] = {}
        return cls._instance

    def create_job(self) -> str:
        job_id = str(uuid.uuid4())
        with self._lock:
            self._jobs[job_id] = {
                "status": JobStatusEnum.PENDING,
                "message": "Job created, waiting to start.",
                "filename": None
            }
        return job_id

    def get_job(self, job_id: str) -> Optional[Dict]:
        with self._lock:
            return self._jobs.get(job_id)

    def update_job_status(self, job_id: str, status: JobStatusEnum, message: Optional[str] = None, filename: Optional[str] = None):
        with self._lock:
            if job_id in self._jobs:
                self._jobs[job_id]["status"] = status
                if message:
                    self._jobs[job_id]["message"] = message
                if filename:
                    self._jobs[job_id]["filename"] = filename
            else:
                # Log an error or raise an exception if job_id not found
                print(f"Error: Job ID {job_id} not found for update.")


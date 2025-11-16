import os
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Form
from fastapi.responses import FileResponse
from ...models.schemas import JobCreationResponse, JobStatusResponse, JobStatusEnum, Voice
from ...services.job_manager import JobManager
from ...core.tasks import convert_pdf_to_audio, UPLOAD_DIR, FINAL_AUDIO_DIR
from typing import List
import logging

router = APIRouter()
job_manager = JobManager()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def parse_voices_from_file(file_path: str) -> List[Voice]:
    """
    Parses the voices.txt file and returns a list of Voice objects.
    """
    voices = []
    try:
        with open(file_path, "r", encoding="utf-16") as f: # Changed encoding to utf-16
            lines = f.readlines()
            # Skip header lines
            for i, line in enumerate(lines):
                if i < 2: # Skip the first two header lines
                    continue
                
                line = line.strip()
                if not line:
                    continue

                parts = line.split()
                if len(parts) > 0:
                    short_name = parts[0]
                    # Create a more user-friendly name from the short_name
                    # Example: "en-US-AriaNeural" -> "English (US) Aria Neural"
                    name_parts = short_name.split('-')
                    friendly_name = " ".join([part.capitalize() for part in name_parts])
                    
                    voices.append(Voice(name=friendly_name, short_name=short_name))
                else:
                    logger.warning(f"Skipping malformed line in voices.txt: {line}")
    except FileNotFoundError:
        logger.error(f"voices.txt not found at {file_path}")
        raise
    except Exception as e:
        logger.error(f"Error parsing voices.txt: {e}", exc_info=True)
        raise
    return voices

@router.get("/voices", response_model=List[Voice])
async def get_voices():
    """
    Provides a list of all supported TTS voices from voices.txt.
    """
    try:
        voices = parse_voices_from_file("/app/voices.txt")
        return voices
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading voices file: {e}")

@router.post("/upload", response_model=JobCreationResponse)
async def upload_pdf(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    voice: str = Form(...),
):
    """
    Uploads a PDF file, initiates conversion to audiobook, and returns a job ID.
    """
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed.")

    # Save the uploaded file
    file_location = UPLOAD_DIR / file.filename
    with open(file_location, "wb") as f:
        f.write(await file.read())

    job_id = job_manager.create_job(voice=voice) 
    
    # Add the conversion task to background tasks
    background_tasks.add_task(convert_pdf_to_audio, job_id, file_location)

    return JobCreationResponse(job_id=job_id)

@router.get("/status/{job_id}", response_model=JobStatusResponse)
async def get_conversion_status(job_id: str):
    """
    Retrieves the current status of a conversion job.
    """
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    
    return JobStatusResponse(
        job_id=job_id,
        status=job["status"],
        message=job["message"],
        filename=job["filename"]
    )

@router.get("/download/{filename}")
async def download_audio(filename: str):
    """
    Serves the final converted audiobook file.
    """
    # Basic security check: prevent directory traversal
    if "/" in filename or "\\" in filename or ".." in filename:
        raise HTTPException(status_code=400, detail="Invalid filename.")

    file_path = FINAL_AUDIO_DIR / filename
    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found.")
    
    # Ensure the file is within the designated final_audio directory
    if not file_path.resolve().parent == FINAL_AUDIO_DIR.resolve():
        raise HTTPException(status_code=400, detail="Invalid file path.")

    return FileResponse(path=file_path, media_type="audio/mpeg", filename=filename)

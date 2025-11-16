import os
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from ...models.schemas import JobCreationResponse, JobStatusResponse, JobStatusEnum
from ...services.job_manager import JobManager
from ...core.tasks import convert_pdf_to_audio, UPLOAD_DIR, FINAL_AUDIO_DIR

router = APIRouter()
job_manager = JobManager()

@router.post("/upload", response_model=JobCreationResponse)
async def upload_pdf(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """
    Uploads a PDF file, initiates conversion to audiobook, and returns a job ID.
    """
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed.")

    # Save the uploaded file
    file_location = UPLOAD_DIR / file.filename
    with open(file_location, "wb") as f:
        f.write(await file.read())

    job_id = job_manager.create_job() 
    
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
async def download_audio(filename: str, background_tasks: BackgroundTasks):
    """
    Serves the final converted audiobook file and deletes it after sending.
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

    def cleanup():
        try:
            os.remove(file_path)
        except OSError as e:
            print(f"Error removing final audio file {file_path}: {e}")

    background_tasks.add_task(cleanup)
    return FileResponse(path=file_path, media_type="audio/mpeg", filename=filename)

import asyncio
import os
import uuid
from pathlib import Path
from pydub import AudioSegment
from typing import Optional, Union
from datetime import datetime, timedelta

from .pdf_parser import parse_pdf
from .text_chunker import chunk_text
from .tts import get_tts_engine
from ..services.job_manager import JobManager
from ..models.schemas import JobStatusEnum

# Initialize JobManager
job_manager = JobManager()

# Define paths for data storage
UPLOAD_DIR = Path("backend/data/uploads")
PROCESSING_DIR = Path("backend/data/processing")
FINAL_AUDIO_DIR = Path("backend/data/final_audio")

# Ensure directories exist
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
PROCESSING_DIR.mkdir(parents=True, exist_ok=True)
FINAL_AUDIO_DIR.mkdir(parents=True, exist_ok=True)

async def schedule_file_deletion(file_path: Path, delay_seconds: int):
    """
    Schedules a file for deletion after a specified delay.
    """
    await asyncio.sleep(delay_seconds)
    if file_path.exists():
        try:
            os.remove(file_path)
            print(f"Scheduled deletion: Removed {file_path}")
        except OSError as e:
            print(f"Scheduled deletion: Error removing {file_path}: {e}")

async def convert_pdf_to_audio(job_id: str, pdf_path: Path):
    """
    Orchestrates the conversion of a PDF to an audiobook.
    """
    job_manager.update_job_status(job_id, JobStatusEnum.PROCESSING, "Starting PDF to audiobook conversion.")
    
    successful_chunk_paths = []
    final_audio_path = None # Initialize to None
    try:
        # Get job details, including the voice
        job_details = job_manager.get_job(job_id)
        if not job_details:
            raise RuntimeError(f"Job {job_id} not found.")
        
        voice = job_details.get("voice")
        if not voice:
            raise RuntimeError(f"No voice selected for job {job_id}.")

        # 1. Parse PDF
        job_manager.update_job_status(job_id, JobStatusEnum.PROCESSING, "Parsing PDF...")
        text_content = parse_pdf(str(pdf_path))
        if not text_content:
            raise ValueError("Could not extract text from PDF.")

        # 2. Chunk Text
        job_manager.update_job_status(job_id, JobStatusEnum.PROCESSING, "Chunking text...")
        sentences = chunk_text(text_content)
        if not sentences:
            raise ValueError("No sentences found in the PDF text.")

        # 3. Synthesize Audio Chunks Concurrently
        job_manager.update_job_status(job_id, JobStatusEnum.PROCESSING, f"Synthesizing {len(sentences)} audio chunks...")
        tts_engine = get_tts_engine(voice=voice)
        
        # Concurrency Limiting
        # A sensible default limit, such as asyncio.Semaphore(10), should be used.
        semaphore = asyncio.Semaphore(10) 
        
        async def process_chunk(index: int, text: str) -> Union[Path, str]:
            """
            Worker function to synthesize a single text chunk and save it.
            Returns the path to the chunk on success, or an error message on failure.
            """
            async with semaphore:
                try:
                    audio_bytes = await tts_engine.synthesize(text)
                    chunk_filename = PROCESSING_DIR / f"{job_id}_chunk_{index}.mp3"
                    with open(chunk_filename, "wb") as f:
                        f.write(audio_bytes)
                    return chunk_filename
                except Exception as e:
                    error_message = f"Error synthesizing chunk {index}: {e}"
                    print(error_message)
                    return error_message

        tasks = [process_chunk(i, sentence) for i, sentence in enumerate(sentences)]
        results = await asyncio.gather(*tasks)

        successful_chunk_paths = [r for r in results if isinstance(r, Path) and r.exists()]
        errors = [r for r in results if isinstance(r, str)]

        if not successful_chunk_paths:
            error_summary = "No audio chunks were successfully synthesized. Errors: " + "; ".join(errors)
            raise RuntimeError(error_summary)

        job_manager.update_job_status(
            job_id, 
            JobStatusEnum.PROCESSING, 
            f"Synthesized {len(successful_chunk_paths)}/{len(sentences)} chunks. Combining audio..."
        )

        # 4. Combine Audio Segments
        combined_audio = AudioSegment.empty()
        for chunk_file in successful_chunk_paths:
            try:
                segment = AudioSegment.from_mp3(chunk_file)
                combined_audio += segment
            except Exception as e:
                print(f"Error combining audio segment {chunk_file}: {e}")
                # Continue with other segments if one fails
                pass

        final_audio_filename = f"{job_id}.mp3"
        final_audio_path = FINAL_AUDIO_DIR / final_audio_filename
        combined_audio.export(final_audio_path, format="mp3")
        
        # 6. Update Job Status to Complete
        job_manager.update_job_status(
            job_id, 
            JobStatusEnum.COMPLETE, 
            "Audiobook conversion complete!", 
            filename=final_audio_filename
        )

        # Schedule deletion of the final audio file after 1 hour
        asyncio.create_task(schedule_file_deletion(final_audio_path, 3600)) # 3600 seconds = 1 hour

    except Exception as e:
        print(f"Job {job_id} failed: {e}")
        job_manager.update_job_status(job_id, JobStatusEnum.FAILED, f"Conversion failed: {e}")
    finally:
        # Clean up the original uploaded PDF file
        if pdf_path.exists():
            try:
                os.remove(pdf_path)
            except OSError as e:
                print(f"Error removing uploaded PDF file {pdf_path}: {e}")
        
        # Clean up processing files
        for chunk_file in successful_chunk_paths:
            try:
                os.remove(chunk_file)
            except OSError as e:
                print(f"Error removing temporary chunk file {chunk_file}: {e}")

import asyncio
import os
import uuid
import functools
import subprocess
from pathlib import Path
from pydub import AudioSegment
from typing import Optional, Union, List, Tuple
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

def combine_audio_chunks(chunk_paths: List[Path], final_path: Path):
    """
    Combines audio chunks into a single file using FFmpeg concat demuxer.
    This is extremely fast and lossless as it avoids re-encoding.
    """
    # 1. Create a temporary file list for FFmpeg
    list_file_path = final_path.with_suffix(".txt")
    
    try:
        with open(list_file_path, "w", encoding="utf-8") as f:
            for chunk_path in chunk_paths:
                # FFmpeg requires absolute paths or relative to the list file. 
                # Since we are in the same container, absolute paths are safest.
                f.write(f"file '{chunk_path.resolve()}'\n")
        
        # 2. Run FFmpeg command
        # -f concat: use concat demuxer
        # -safe 0: allow unsafe file paths (absolute paths)
        # -i list.txt: input file list
        # -c copy: copy stream (no re-encoding)
        # -y: overwrite output file
        command = [
            "ffmpeg",
            "-f", "concat",
            "-safe", "0",
            "-i", str(list_file_path),
            "-c", "copy",
            "-y",
            str(final_path)
        ]
        
        # Run FFmpeg. Capture output for debugging if needed.
        subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.decode() if e.stderr else str(e)
        print(f"FFmpeg failed: {error_msg}")
        raise RuntimeError(f"Audio combination failed: {error_msg}")
    except Exception as e:
        print(f"Error combining audio: {e}")
        raise
    finally:
        # 3. Cleanup list file
        if list_file_path.exists():
            try:
                os.remove(list_file_path)
            except OSError:
                pass

async def convert_pdf_to_audio(job_id: str, pdf_path: Path):
    """
    Orchestrates the conversion of a PDF to an audiobook.
    """
    job_manager.update_job_status(job_id, JobStatusEnum.PROCESSING, "Starting PDF to audiobook conversion.")
    
    successful_chunk_paths = []
    final_audio_path = None # Initialize to None
    loop = asyncio.get_running_loop()

    try:
        # Get job details, including the voice
        job_details = job_manager.get_job(job_id)
        if not job_details:
            raise RuntimeError(f"Job {job_id} not found.")
        
        voice = job_details.get("voice")
        if not voice:
            raise RuntimeError(f"No voice selected for job {job_id}.")

        # 1. Parse PDF (Run in executor)
        job_manager.update_job_status(job_id, JobStatusEnum.PROCESSING, "Parsing PDF...")
        text_content = await loop.run_in_executor(None, parse_pdf, str(pdf_path))
        
        if not text_content:
            raise ValueError("Could not extract text from PDF.")

        # 2. Chunk Text (Run in executor)
        job_manager.update_job_status(job_id, JobStatusEnum.PROCESSING, "Chunking text...")
        sentences = await loop.run_in_executor(None, chunk_text, text_content)
        
        if not sentences:
            raise ValueError("No sentences found in the PDF text.")

        # 3. Synthesize Audio Chunks Concurrently
        job_manager.update_job_status(job_id, JobStatusEnum.PROCESSING, f"Synthesizing {len(sentences)} audio chunks...")
        tts_engine = get_tts_engine(voice=voice)
        
        # Concurrency Limiting
        # Reduced to 5 to avoid rate limiting on cloud environments like Render
        semaphore = asyncio.Semaphore(5) 
        
        completed_chunks = 0
        total_chunks = len(sentences)

        async def process_chunk(index: int, text: str) -> Tuple[int, Union[Path, str]]:
            """
            Worker function to synthesize a single text chunk and save it.
            Returns (index, path_or_error).
            """
            nonlocal completed_chunks
            async with semaphore:
                retries = 3
                for attempt in range(retries):
                    try:
                        audio_bytes = await tts_engine.synthesize(text)
                        chunk_filename = PROCESSING_DIR / f"{job_id}_chunk_{index}.mp3"
                        
                        # Writing to file is IO bound but small enough to be okay in async usually, 
                        # but for strictness we could use aiofiles or run_in_executor. 
                        # Standard open() is blocking. Let's use run_in_executor for safety.
                        await loop.run_in_executor(None, lambda: chunk_filename.write_bytes(audio_bytes))
                        
                        completed_chunks += 1
                        job_manager.update_job_status(
                            job_id, 
                            JobStatusEnum.PROCESSING, 
                            f"Synthesizing audio: {completed_chunks}/{total_chunks} chunks processed."
                        )
                        
                        return index, chunk_filename
                    except Exception as e:
                        if attempt < retries - 1:
                            print(f"Chunk {index} failed (attempt {attempt + 1}): {e}. Retrying...")
                            await asyncio.sleep(2 * (attempt + 1)) # Exponential backoff
                        else:
                            error_message = f"Error synthesizing chunk {index} after {retries} attempts: {e}"
                            print(error_message)
                            return index, error_message
                return index, f"Failed to synthesize chunk {index}"

        tasks = [process_chunk(i, " ".join(sentence).strip("\n")) for i, sentence in enumerate(sentences)]
        results = await asyncio.gather(*tasks)

        # Sort results by index to maintain order
        results.sort(key=lambda x: x[0])
        
        # Filter successful paths
        successful_chunk_paths = [r[1] for r in results if isinstance(r[1], Path) and r[1].exists()]
        errors = [r[1] for r in results if isinstance(r[1], str)]

        if not successful_chunk_paths:
            error_summary = "No audio chunks were successfully synthesized. Errors: " + "; ".join(errors[:5])
            raise RuntimeError(error_summary)

        job_manager.update_job_status(
            job_id, 
            JobStatusEnum.PROCESSING, 
            f"Synthesized {len(successful_chunk_paths)}/{len(sentences)} chunks. Combining audio..."
        )

        # 4. Combine Audio Segments (Run in executor)
        final_audio_filename = f"{job_id}.mp3"
        final_audio_path = FINAL_AUDIO_DIR / final_audio_filename
        
        await loop.run_in_executor(
            None, 
            combine_audio_chunks, 
            successful_chunk_paths, 
            final_audio_path
        )
        
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

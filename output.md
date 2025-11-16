# Project Architecture and Workflow: PDF-to-Audiobook Weaver

## 1. Project Overview

The PDF-to-Audiobook Weaver is a web service designed to convert user-uploaded PDF documents into a single, downloadable audiobook file in MP3 format. The application is built with a focus on performance, user experience, and modularity, allowing for a seamless and efficient conversion process.

## 2. System Architecture

The application follows a client-server model with a decoupled, asynchronous task processing pipeline. This architecture ensures that the user interface remains responsive, even during long-running conversion tasks.

### Data Flow

1.  **Client (Browser):** The user selects a PDF file using an HTML form and initiates the upload process.
2.  **Frontend (JavaScript):** The frontend JavaScript code sends the selected file to the backend API using a `POST` request.
3.  **Backend API (FastAPI):**
    *   The backend receives the file, validates that it is a PDF, and saves it to a temporary `uploads` directory.
    *   A unique `job_id` is generated for the conversion task.
    *   A background task is initiated to handle the PDF-to-audio conversion pipeline.
    *   The API immediately responds to the client with the `job_id` and an HTTP 202 Accepted status, indicating that the request has been accepted for processing.
4.  **Frontend (JavaScript):**
    *   Upon receiving the `job_id`, the frontend begins polling a status endpoint on the backend API every few seconds.
    *   The UI is updated with the status messages received from the backend.
5.  **Background Task (Conversion Pipeline):**
    *   The background task orchestrates the entire conversion process:
        *   **PDF Parsing:** The text content is extracted from the PDF file.
        *   **Text Chunking:** The extracted text is cleaned and split into individual sentences or small chunks.
        *   **Concurrent TTS Synthesis:** Each text chunk is converted into an audio segment concurrently using a Text-to-Speech (TTS) engine. This parallel processing significantly speeds up the conversion.
        *   **Audio Combination:** All the generated audio segments are combined into a single MP3 file.
        *   **Job Completion:** The job's status is updated to "complete," and the final filename is stored.
6.  **Backend API (Status Endpoint):** The status endpoint responds to the frontend's polling requests with the current job status ("processing", "complete", or "failed"). Once the job is complete, the response includes the final filename.
7.  **Frontend (JavaScript):**
    *   When the frontend receives a "complete" status, it stops polling.
    *   It constructs the download URL for the final audio file and displays an audio player and a download link to the user.

## 3. Technology Stack

*   **Frontend:** Vanilla HTML5, CSS3, JavaScript (ES6+)
*   **Backend:** Python 3.9+ with FastAPI
*   **Server:** Uvicorn
*   **File Uploads:** `python-multipart`
*   **PDF Parsing:** `PyMuPDF` (the `fitz` library)
*   **Text Processing:** `nltk` for sentence tokenization
*   **Audio Manipulation:** `pydub` for combining audio files
*   **Default TTS Engine:** `edge-tts`
*   **Containerization:** Docker

## 4. Project Folder Structure

```
pdf-to-audiobook/
│
├── frontend/
│   ├── index.html
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── main.js
│
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py             # FastAPI app, routers, static file mount
│   │   ├── api/
│   │   │   └── v1/
│   │   │       └── endpoints.py  # Defines all API endpoints
│   │   ├── core/
│   │   │   ├── tasks.py          # The main conversion pipeline function
│   │   │   ├── pdf_parser.py
│   │   │   ├── text_chunker.py
│   │   │   └── tts/              # TTS Strategy Pattern implementation
│   │   │       ├── __init__.py     # TTS Engine Factory
│   │   │       ├── base.py         # Abstract TTSEngine interface
│   │   │       ├── edge_tts_engine.py # Default implementation
│   │   │       └── gemini_tts_engine.py # Placeholder for extensibility
│   │   ├── models/
│   │   │   └── schemas.py        # Pydantic models for API responses
│   │   └── services/
│   │       └── job_manager.py    # Manages job statuses (in-memory)
│   │
│   ├── data/                   # MUST be in .gitignore
│   │   ├── uploads/
│   │   ├── processing/
│   │   └── final_audio/
│   │
│   ├── .env.example
│   ├── requirements.txt
│   └── Dockerfile
│
└── .gitignore
└── README.md
```

## 5. Backend Specification

### 5.1. Data Models (`backend/app/models/schemas.py`)

*   **`JobCreationResponse`**:
    *   `job_id`: string
*   **`JobStatusResponse`**:
    *   `job_id`: string
    *   `status`: string (Enum: "pending", "processing", "complete", "failed")
    *   `message`: string (Optional)
    *   `filename`: string (Optional)

### 5.2. API Endpoints (`backend/app/api/v1/endpoints.py`)

*   **`POST /api/v1/upload`**:
    *   Accepts a PDF file upload.
    *   Initiates the background conversion task.
    *   Returns a `JobCreationResponse` with the `job_id`.
*   **`GET /api/v1/status/{job_id}`**:
    *   Retrieves the status of a conversion job.
    *   Returns a `JobStatusResponse`.
*   **`GET /api/v1/download/{filename}`**:
    *   Serves the final converted audio file.

### 5.3. Core Logic & Modules

*   **`JobManager` (`services/job_manager.py`):** An in-memory, thread-safe key-value store for tracking the status of all conversion jobs.
*   **`PDFParser` (`core/pdf_parser.py`):** Extracts text content from a PDF file.
*   **`TextChunker` (`core/text_chunker.py`):** Cleans and splits the extracted text into sentences.
*   **`Conversion Task` (`core/tasks.py`):** The main asynchronous function that orchestrates the entire conversion pipeline.

## 6. Frontend Specification

The frontend consists of a single HTML page (`index.html`) with associated CSS (`style.css`) and JavaScript (`main.js`).

*   **UI Components:**
    *   An upload form for selecting a PDF file.
    *   A status area to display messages to the user.
    *   A result area with an audio player and a download link, which is hidden by default.
*   **Client-Side Logic:**
    *   Handles form submission and file upload.
    *   Polls the backend for status updates.
    *   Displays the final result or an error message.

## 7. Dockerization

The application is containerized using Docker for easy deployment and portability. The `Dockerfile` at the root of the project defines the container image.

*   **Base Image:** The image is based on `python:3.9-slim`.
*   **Dependencies:** It installs `ffmpeg` for audio processing and all the Python dependencies listed in `requirements.txt`.
*   **NLTK Data:** It downloads the `punkt` tokenizer for `nltk`.
*   **Application Code:** It copies the `backend` and `frontend` directories into the container.
*   **Execution:** The container runs the FastAPI application using `uvicorn`.

## 8. Concurrency

A key feature of this application is its use of concurrency to speed up the TTS synthesis process.

*   **`asyncio.Semaphore`:** A semaphore is used to limit the number of concurrent requests to the TTS service, preventing rate limiting and other service errors.
*   **`asyncio.gather`:** All the text chunks are processed concurrently using `asyncio.gather`, which significantly reduces the total conversion time.
*   **Asynchronous Worker Function:** A nested `async` helper function (`process_chunk`) is used to synthesize a single text chunk and save it to a file. This function is designed to be run concurrently for all chunks.
*   **Error Handling:** The `process_chunk` function includes its own `try...except` block to handle errors for individual chunks without halting the entire conversion process. Error messages are collected and reported to the user.

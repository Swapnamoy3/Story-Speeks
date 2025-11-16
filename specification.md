# Part 1
---

### **Project Specification: PDF-to-Audiobook Weaver**

**Version:** 1.1
**Date:** May 22, 2024

#### **1. Project Overview**

**1.1. Vision:** To create a web service that transforms user-uploaded PDF documents into single, downloadable audiobook files (MP3 format).

**1.2. Core Functionality:** A user uploads a PDF through a web interface. The backend processes the file asynchronously, extracts the text, converts it to speech using a configurable TTS engine, and makes the final audio file available for the user to play or download.

**1.3. Key Principles:**
*   **Performance:** The conversion process must be as fast as possible by leveraging concurrency for I/O-bound operations.
*   **Asynchronous Processing:** The UI must remain responsive and provide feedback during the potentially long conversion process.
*   **Modularity & Extensibility:** The TTS engine must be swappable via configuration without code changes (Strategy Pattern).
*   **User Experience:** The user must be kept informed of the status of their conversion job from start to finish.



#### **2. System Architecture**

The system follows a client-server model with a decoupled, asynchronous task processing pipeline.

**Data Flow:**
1.  **Client (Browser):** User uploads a PDF file via an HTML form.
2.  **Frontend JS:** Sends the file via a `POST` request to the Backend API.
3.  **Backend API (FastAPI):**
    *   Receives the file and validates it.
    *   Assigns a unique `job_id`.
    *   Initiates a background task for the conversion pipeline.
    *   Immediately responds to the client with the `job_id` (HTTP 202 Accepted).
4.  **Frontend JS:** Receives the `job_id` and begins polling a status endpoint every few seconds.
5.  **Background Task:**
    *   Parses the PDF to extract text.
    *   Cleans and chunks the text into sentences.
    *   Iterates through each chunk, converting it to an audio segment using the configured TTS engine.
    *   Combines all audio segments into a single MP3 file.
    *   Updates the job's status to "complete" and stores the final filename.
6.  **Backend API:** Responds to status polls with the current job status ("processing", "complete", "failed"). Once complete, the response includes the final filename.
7.  **Frontend JS:** Upon receiving a "complete" status, it constructs the download URL and displays an audio player and a download link to the user.

---

#### **3. Technology Stack**

*   **Frontend:** Vanilla HTML5, CSS3, JavaScript (ES6+).
*   **Backend:** Python 3.9+ with FastAPI.
*   **Server:** Uvicorn.
*   **File Uploads:** `python-multipart`.
*   **PDF Parsing:** `PyMuPDF` (the `fitz` library).
*   **Text Processing:** `nltk` for sentence tokenization.
*   **Audio Manipulation:** `pydub` for combining audio files.
*   **Default TTS Engine:** `edge-tts`.

---

#### **4. Project Folder Structure**

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
│   └── Dockerfile              # Optional
│
└── .gitignore
└── README.md
```

---

#### **5. Backend Specification**

**5.1. Data Models (`backend/app/models/schemas.py`)**

*   **`JobCreationResponse`**:
    *   `job_id`: string
*   **`JobStatusResponse`**:
    *   `job_id`: string
    *   `status`: string (Enum: "pending", "processing", "complete", "failed")
    *   `message`: string (Optional, e.g., "Parsing PDF...", "Generating audio: 25%")
    *   `filename`: string (Optional, provided only when status is "complete")

**5.2. API Endpoints (`backend/app/api/v1/endpoints.py`)**

1.  **`POST /api/v1/upload`**:
    *   **Request:** `multipart/form-data` with a single file field named `file`.
    *   **Logic:** Validates file is a PDF, saves it, creates a job via `JobManager`, starts `convert_pdf_to_audio` as a `BackgroundTask`.
    *   **Success Response (202 Accepted):** `JobCreationResponse`.
    *   **Error Response (400 Bad Request):** If file is missing or not a PDF.

2.  **`GET /api/v1/status/{job_id}`**:
    *   **Request:** `job_id` in URL path.
    *   **Logic:** Retrieves job details from `JobManager`.
    *   **Success Response (200 OK):** `JobStatusResponse`.
    *   **Error Response (404 Not Found):** If `job_id` is invalid.

3.  **`GET /api/v1/download/{filename}`**:
    *   **Request:** `filename` in URL path.
    *   **Logic:** Serves the static file from `backend/data/final_audio/` using `FileResponse`. Must perform basic security checks on the filename.
    *   **Success Response (200 OK):** The audio file (`audio/mpeg`).
    *   **Error Response (404 Not Found):** If the file does not exist.

**5.3. Core Logic & Modules**

*   **`JobManager` (`services/job_manager.py`):** An in-memory key-value store (Python dictionary) to track the state of all jobs. Must be thread-safe (use `threading.Lock`). Provides functions to create, update, and get job status.
*   **`PDFParser` (`core/pdf_parser.py`):** A function that takes a PDF file path and returns its full text content as a single string.
*   **`TextChunker` (`core/text_chunker.py`):** A function that takes a raw text string, cleans it (e.g., normalizes whitespace), and uses `nltk.sent_tokenize` to split it into a list of sentences.
*   **`Conversion Task` (`core/tasks.py`):** The main `async` function `convert_pdf_to_audio`. It orchestrates the entire pipeline: calls parser, chunker, the TTS engine in a loop for each chunk, combines the resulting audio segments with `pydub`, and updates the job status via `JobManager` at each step. Must include robust `try...except` blocks to handle failures.

---

#### **6. TTS Engine Abstraction (Strategy Pattern)**

This layer is located in `backend/app/core/tts/`.

**6.1. The Interface (`base.py`)**
*   Define an Abstract Base Class `TTSEngine`.
*   It must have one abstract method: `async def synthesize(self, text: str) -> bytes`. This method must return the raw MP3 audio data.

**6.2. Concrete Strategies (`edge_tts_engine.py`, `gemini_tts_engine.py`)**
*   **`EdgeTTSEngine`**: A class inheriting from `TTSEngine`. Implements `synthesize` using the `edge-tts` library. This is the default engine.
*   **`GeminiTTSEngine`**: A placeholder class inheriting from `TTSEngine`. Its `synthesize` method should raise a `NotImplementedError` or contain commented-out logic for the Gemini API.

**6.3. The Factory (`__init__.py`)**
*   A function `get_tts_engine() -> TTSEngine`.
*   It reads the `TTS_ENGINE` environment variable (defaulting to `"edge"`).
*   It returns an instance of the corresponding engine class (`EdgeTTSEngine` or `GeminiTTSEngine`).

**6.4. Integration (`core/tasks.py`)**
*   The `convert_pdf_to_audio` function must call `get_tts_engine()` to get the engine instance.
*   It must then call `await tts_engine.synthesize(chunk)` for each text chunk.

---

#### **7. Frontend Specification (`frontend/`)**

**7.1. UI Components (`index.html`)**
*   **Upload Form:** An `<input type="file" accept=".pdf">` and a `<button type="submit">`. The button should be disabled until a file is selected.
*   **Status Area:** A `<div>` to display messages to the user (e.g., "Uploading...", "Processing...", "Complete!").
*   **Result Area:** A `<div>`, hidden by default, containing an `<audio controls>` element and an `<a download>` link for the final MP3.

**7.2. Client-Side Logic (`js/main.js`)**
1.  **Form Submission:** An event listener intercepts the form submission.
2.  **Upload:** It constructs a `FormData` object and sends a `POST` request to `/api/v1/upload`.
3.  **Polling:**
    *   On a successful upload response, it extracts the `job_id`.
    *   It starts a `setInterval` function to call `GET /api/v1/status/{job_id}` every 3-5 seconds.
    *   The UI's status area is updated with the `message` from each poll response.
4.  **Completion/Failure:**
    *   If the status becomes `"complete"`, the interval is cleared. The audio player's `src` and the download link's `href` are set to `/api/v1/download/{filename}`, and the result area is shown.
    *   If the status becomes `"failed"`, the interval is cleared, and an error message is displayed.

---

#### **8. Configuration & Environment (`backend/.env.example`)**

The application configuration will be managed via environment variables.

```
# --- TTS ENGINE CONFIGURATION ---
# Specifies the TTS engine to use.
# Supported values: "edge", "gemini"
TTS_ENGINE=edge

# Required only if TTS_ENGINE is set to "gemini"
# GOOGLE_API_KEY=your_api_key_here
```

---

#### **9. Error Handling & Edge Cases**

*   The backend must handle corrupt or unparseable PDFs and update the job status to "failed".
*   The TTS synthesis for individual chunks should be wrapped in `try...except` blocks to prevent one bad chunk from failing the entire job.
*   File cleanup for the `uploads`, `processing`, and `final_audio` directories should be considered for a production deployment (e.g., a scheduled cron job).

---

#### **10. Deployment & Execution**

*   **Dependencies:** The backend dependencies are listed in `backend/requirements.txt` and should be installed in a virtual environment. The NLTK `punkt` tokenizer must be downloaded.
*   **Running Backend:** The application is run using `uvicorn app.main:app --reload` from the `backend/` directory.
*   **Serving Frontend:** The FastAPI application in `backend/app/main.py` will be configured to serve the static files from the `frontend/` directory. The root path (`/`) should serve `frontend/index.html`.

### **11. Performance & Concurrency Specification (New Section)**

**11.1. Core Requirement: Concurrent Chunk Synthesis**

To ensure the application is fast and efficient, the process of converting individual text chunks to audio must not be sequential. All TTS synthesis requests for a single job must be executed **concurrently**. This leverages Python's `asyncio` capabilities to perform multiple network-bound operations in parallel, drastically reducing the total processing time.

**11.2. Implementation Guideline for `backend/app/core/tasks.py`**

The `convert_pdf_to_audio` function must be implemented with the following concurrent logic:

1.  **Concurrency Limiting:**
    *   Instantiate an `asyncio.Semaphore` at the beginning of the function. A sensible default limit, such as `asyncio.Semaphore(10)`, should be used.
    *   **Purpose:** This prevents the application from sending an excessive number of simultaneous requests to the TTS service, which could lead to IP-based rate limiting, temporary bans, or service errors.

2.  **Asynchronous Worker Function:**
    *   Define a nested `async` helper function (e.g., `process_chunk(index, text)`).
    *   **Logic of the worker function:**
        a.  It will acquire the semaphore using `async with semaphore:`.
        b.  Inside the `with` block, it will call `audio_bytes = await tts_engine.synthesize(text)`.
        c.  It will then write these `audio_bytes` to a uniquely named file in the job's processing directory (e.g., `chunk_{index}.mp3`).
        d.  It must include its own `try...except` block. If a specific chunk fails to synthesize, it should log the error but **not** raise an exception that would halt all other concurrent tasks. It can return `None` or the path on success.
        e.  The semaphore is automatically released when the `with` block exits, even if an error occurs.

3.  **Task Creation and Execution:**
    *   After parsing the PDF into a list of text chunks (`sentences`), iterate through this list.
    *   For each `sentence`, create a coroutine task by calling the worker function: `tasks.append(process_chunk(i, sentence))`. Do **not** `await` it here.
    *   After the loop, execute all created tasks concurrently using `results = await asyncio.gather(*tasks)`.

4.  **Result Aggregation:**
    *   The `results` from `asyncio.gather` will be a list of the outcomes from each `process_chunk` call (e.g., a list of file paths and `None` for failures).
    *   Filter this list to remove any `None` values, resulting in a clean list of successfully created audio chunk file paths.

5.  **Final Combination:**
    *   Proceed with the `pydub` audio combination logic using the filtered list of valid chunk paths.

**11.3. Impact on Other Modules**

*   **`TTSEngine` Interface (`core/tts/base.py`):** No changes are required. The definition of `synthesize` as an `async` method already supports this concurrent execution model perfectly. This demonstrates the strength of the chosen design pattern.
*   **`JobManager` (`services/job_manager.py`):** Consider adding more granular progress updates. For example, after `asyncio.gather` completes, the `message` field in the job status could be updated to `f"Synthesized {len(successful_chunks)}/{len(total_chunks)} chunks."` before proceeding to the combination step.



---- 
# Part 2
---
Excellent. This is a fantastic next step that significantly enhances the user experience and showcases the power of your modular design.

Here is a new, additional specification document designed to be provided to the Gemini CLI. It details all the necessary changes to implement the voice selection feature, building directly upon the existing project structure.

---

### **Addendum to Project Specification: Voice Selection Feature**

**Version:** 1.2
**Date:** May 22, 2024

**To:** Gemini CLI
**From:** Project Architect
**Subject:** Implementation of a User-Selectable Voice Configuration Feature

This document provides detailed instructions for upgrading the "PDF-to-Audiobook Weaver" project with a voice selection feature. The user must be able to choose from a list of all available Microsoft Edge TTS voices, and their selection must be used for the audio generation.

#### **1. High-Level Objective**

To empower users to select their preferred voice and language for the generated audiobook. This requires fetching the available voices from the `edge-tts` library, presenting them in the UI, and processing the user's choice in the backend.

---

#### **2. Backend Specification Changes**

The backend is responsible for providing the list of voices and using the selected voice during job processing.

**2.1. New Data Model (`backend/app/models/schemas.py`)**

A new Pydantic model is required to represent a single voice option.

*   **`Voice`**:
    *   `name`: string (The user-friendly display name, e.g., "English (US), Aria (Neural)")
    *   `short_name`: string (The technical identifier required by the `edge-tts` library, e.g., "en-US-AriaNeural")

**2.2. New API Endpoint (`backend/app/api/v1/endpoints.py`)**

A new endpoint must be created to serve the list of available voices to the frontend.

1.  **`GET /api/v1/voices`**:
    *   **Purpose:** To provide a list of all supported TTS voices.
    *   **Logic:**
        *   This endpoint should use the `edge-tts` library's built-in functionality (e.g., `await edge_tts.list_voices()`) to get a list of all available voices.
        *   It must then format this data into a list of `Voice` objects as defined in the schema above.
        *   **Performance Optimization:** The voice list is static and fetching it can be slow. The result of the first call to `edge_tts.list_voices()` **must be cached in memory** when the application starts up, so subsequent requests to this endpoint are served instantly without re-invoking the library command.
    *   **Success Response (200 OK):** A JSON array of `Voice` objects: `List[Voice]`.

**2.3. Modified API Endpoint (`backend/app/api/v1/endpoints.py`)**

The existing upload endpoint must be modified to accept the user's voice selection.

1.  **`POST /api/v1/upload`**:
    *   **Request:** The request is still `multipart/form-data`, but it now accepts an **additional form field**:
        *   `file`: The `UploadFile` (as before).
        *   `voice`: A `string` representing the `short_name` of the selected voice (e.g., "en-US-AriaNeural"). This should be received using FastAPI's `Form(...)`.
    *   **Logic:** When a job is created, the value of the `voice` field must be stored alongside the job's status in the `JobManager`.

**2.4. Modified Service Layer (`backend/app/services/job_manager.py`)**

The `JobManager`'s internal data structure must be updated to store the selected voice for each job.

*   The dictionary value for a `job_id` should now be an object that includes the `voice` parameter. For example: `{"status": "pending", "message": "Job created", "voice": "en-US-AriaNeural"}`.
*   The `create_job` function must be updated to accept the `voice` string as an argument.

**2.5. Modified TTS Engine (`backend/app/core/tts/`)**

The Strategy Pattern implementation needs to be adapted to handle per-job voice configuration.

1.  **`edge_tts_engine.py`**:
    *   The `EdgeTTSEngine` class's `__init__` method must be modified to accept a voice parameter: `__init__(self, voice: str)`.
    *   This `voice` parameter should be stored as an instance variable (e.g., `self.voice`).
    *   The `synthesize` method must then use `self.voice` when calling the `edge-tts.Communicate` function.

2.  **`__init__.py` (The Factory)**:
    *   The factory function `get_tts_engine()` must be modified to accept the voice parameter: `get_tts_engine(voice: str) -> TTSEngine`.
    *   When instantiating `EdgeTTSEngine`, it must pass the received `voice` string to its constructor: `return EdgeTTSEngine(voice=voice)`.

**2.6. Modified Conversion Task (`backend/app/core/tasks.py`)**

The main pipeline must now retrieve and use the stored voice for the job.

*   Inside `convert_pdf_to_audio`, after starting the job, it must retrieve the full job details from the `JobManager`, including the `voice` string.
*   When it calls the TTS factory, it must pass this specific voice: `tts_engine = get_tts_engine(voice=job_details['voice'])`.

---

#### **3. Frontend Specification Changes**

The frontend needs a UI element for voice selection and logic to populate it and send the choice.

**3.1. Modified UI (`frontend/index.html`)**

*   Inside the `<form>` element, add a new UI component for voice selection. A `<select>` dropdown menu is the ideal choice.
    ```html
    <label for="voice-select">Choose a voice:</label>
    <select name="voice" id="voice-select" required>
        <option value="">Loading voices...</option>
    </select>
    ```
*   The dropdown should be disabled or show a "Loading..." message until it is populated with data from the API.

**3.2. Modified Client-Side Logic (`frontend/js/main.js`)**

1.  **New Function: `loadVoices()`**:
    *   Create a new `async` function that is executed as soon as the page loads.
    *   This function will send a `GET` request to the new `/api/v1/voices` endpoint.
    *   Upon receiving the list of voices, it will:
        *   Get a reference to the `<select id="voice-select">` element.
        *   Clear any existing options (like the "Loading..." message).
        *   Iterate through the array of voice objects. For each object, create a new `<option>` element.
        *   Set the option's `value` attribute to the voice's `short_name`.
        *   Set the option's display text to the voice's user-friendly `name`.
        *   Append the new option to the select element.
        *   Enable the select element and the submit button.

2.  **Modified Form Submission Logic**:
    *   When the user submits the form, the logic that creates the `FormData` object must be updated.
    *   In addition to appending the file, it must now also append the selected voice from the dropdown.
    ```javascript
    // Inside the form's 'submit' event listener
    const selectedVoice = document.getElementById('voice-select').value;
    formData.append('file', document.getElementById('pdf-file').files[0]);
    formData.append('voice', selectedVoice); // <-- This line is new
    ```
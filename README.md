# PDF-to-Audiobook Weaver

This project is a web service that transforms user-uploaded PDF documents into single, downloadable audiobook files (MP3 format).

## Running with Docker

### Prerequisites

*   [Docker](https://www.docker.com/get-started) installed on your machine.

### Build the Docker Image

1.  Navigate to the `backend` directory:
    ```bash
    cd backend
    ```
2.  Build the Docker image:
    ```bash
    docker build -t pdf-to-audiobook .
    ```

### Run the Docker Container

1.  Run the container, mapping port 8080 on your host to port 80 in the container:
    ```bash
    docker run -p 8080:80 pdf-to-audiobook
    ```
2.  The application will be accessible at `http://localhost:8080`.

## Deployment

The application is deployed and accessible at: [https://story-speeks.onrender.com](https://story-speeks.onrender.com)

### Environment Variables

You can customize the TTS engine by setting the `TTS_ENGINE` environment variable when running the container.

*   **For Edge TTS (default):**
    ```bash
    docker run -p 8080:80 -e TTS_ENGINE=edge pdf-to-audiobook
    ```
*   **For Gemini TTS (placeholder):**
    ```bash
    docker run -p 8080:80 -e TTS_ENGINE=gemini -e GOOGLE_API_KEY=your_api_key_here pdf-to-audiobook
    ```

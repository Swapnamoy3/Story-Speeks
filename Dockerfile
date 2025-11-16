# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Install ffmpeg for pydub
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /app

# Copy the backend requirements file into the container at /app
COPY ./backend/requirements.txt /app/requirements.txt

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Download NLTK punkt tokenizer
RUN python -c "import nltk; nltk.download('punkt')"

# Copy the backend directory into the container at /app
COPY ./backend /app/backend

# Copy the frontend directory to the /app directory
COPY ./frontend /app/frontend

# Make port 80 available to the world outside this container
EXPOSE 80

# Define environment variables
ENV TTS_ENGINE=edge

# Run uvicorn when the container launches
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "80"]

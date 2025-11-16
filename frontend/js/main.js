document.addEventListener("DOMContentLoaded", () => {
    const uploadForm = document.getElementById("uploadForm");
    const pdfFile = document.getElementById("pdfFile");
    const uploadButton = document.getElementById("uploadButton");
    const statusArea = document.getElementById("statusArea");
    const resultArea = document.getElementById("resultArea");
    const audioPlayer = document.getElementById("audioPlayer");
    const downloadLink = document.getElementById("downloadLink");
    const errorArea = document.getElementById("errorArea");
    const errorMessage = document.getElementById("errorMessage");

    let pollingInterval;

    // Enable upload button only when a file is selected
    pdfFile.addEventListener("change", () => {
        uploadButton.disabled = !pdfFile.files.length;
    });

    uploadForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        resetUI();
        statusArea.textContent = "Uploading...";

        const formData = new FormData();
        formData.append("file", pdfFile.files[0]);

        try {
            const response = await fetch("/api/v1/upload", {
                method: "POST",
                body: formData,
            });

            if (!response.ok) {
                throw new Error(`Upload failed with status: ${response.status}`);
            }

            const data = await response.json();
            const { job_id } = data;
            statusArea.textContent = `Processing... (Job ID: ${job_id})`;
            startPolling(job_id);

        } catch (error) {
            showError(`Upload Error: ${error.message}`);
        }
    });

    function startPolling(jobId) {
        pollingInterval = setInterval(async () => {
            try {
                const response = await fetch(`/api/v1/status/${jobId}`);
                if (!response.ok) {
                    throw new Error(`Status check failed with status: ${response.status}`);
                }
                const data = await response.json();
                handleStatusUpdate(data);
            } catch (error) {
                showError(`Polling Error: ${error.message}`);
                clearInterval(pollingInterval);
            }
        }, 3000); // Poll every 3 seconds
    }

    function handleStatusUpdate(data) {
        statusArea.textContent = data.message || `Status: ${data.status}`;

        if (data.status === "complete") {
            clearInterval(pollingInterval);
            statusArea.textContent = "Conversion Complete!";
            resultArea.classList.remove("hidden");
            const audioUrl = `/api/v1/download/${data.filename}`;
            audioPlayer.src = audioUrl;
            downloadLink.href = audioUrl;
            downloadLink.download = data.filename;
        } else if (data.status === "failed") {
            clearInterval(pollingInterval);
            showError(data.message || "An unknown error occurred during conversion.");
        }
    }

    function showError(message) {
        statusArea.textContent = "";
        errorArea.classList.remove("hidden");
        errorMessage.textContent = message;
    }

    function resetUI() {
        statusArea.textContent = "";
        resultArea.classList.add("hidden");
        errorArea.classList.add("hidden");
        errorMessage.textContent = "";
        if (pollingInterval) {
            clearInterval(pollingInterval);
        }
    }
});

document.addEventListener("DOMContentLoaded", () => {
    const uploadForm = document.getElementById("uploadForm");
    const pdfFile = document.getElementById("pdfFile");
    const voiceSelect = document.getElementById("voice-select");
    const uploadButton = document.getElementById("uploadButton");
    const statusArea = document.getElementById("statusArea");
    const resultArea = document.getElementById("resultArea");
    const errorArea = document.getElementById("errorArea");
    const audioPlayer = document.getElementById("audioPlayer");
    const downloadLink = document.getElementById("downloadLink");
    const errorMessage = document.getElementById("errorMessage");
    const fileNameDisplay = document.getElementById("fileName");

    let pollingInterval;

    async function loadVoices() {
        try {
            const response = await fetch("/api/v1/voices");
            if (!response.ok) {
                throw new Error(`Failed to load voices: ${response.status}`);
            }
            const voices = await response.json();
            voiceSelect.innerHTML = '<option value="" disabled selected>Select a voice</option>'; // Clear "Loading..." and add default
            voices.forEach(voice => {
                const option = document.createElement("option");
                option.value = voice.short_name;
                option.textContent = voice.name;
                voiceSelect.appendChild(option);
            });
            checkFormValidity(); // Check validity after voices are loaded
        } catch (error) {
            voiceSelect.innerHTML = `<option value="" disabled selected>Error loading voices</option>`;
            showError(`Could not load voices. Please refresh the page. ${error.message}`);
            checkFormValidity(); // Still check validity to disable button if needed
        }
    }

    function checkFormValidity() {
        // Enable the button only if a file is selected and a voice is chosen
        if (pdfFile.files.length > 0 && voiceSelect.value && voiceSelect.value !== "Error loading voices") {
            uploadButton.disabled = false;
        } else {
            uploadButton.disabled = true;
        }
    }

    // --- Event Listeners ---
    pdfFile.addEventListener('change', () => {
        if (pdfFile.files.length > 0) {
            fileNameDisplay.textContent = pdfFile.files[0].name;
        } else {
            fileNameDisplay.textContent = 'Click to select a PDF file';
        }
        checkFormValidity();
    });

    voiceSelect.addEventListener('change', checkFormValidity);

    uploadForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        resetUI();
        
        statusArea.innerHTML = `<div class="loader"></div><span>Weaving your audio... this may take a moment.</span>`;
        uploadButton.disabled = true;

        const formData = new FormData();
        formData.append("file", pdfFile.files[0]);
        formData.append("voice", voiceSelect.value);

        try {
            const response = await fetch("/api/v1/upload", {
                method: "POST",
                body: formData,
            });

            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(`Upload failed with status: ${response.status} - ${errorText}`);
            }

            const data = await response.json();
            const { job_id } = data;
            statusArea.innerHTML = `<div class="loader"></div><span>Processing... (Job ID: ${job_id})</span>`;
            startPolling(job_id);

        } catch (error) {
            showError(`Upload Error: ${error.message}`);
            uploadButton.disabled = false; // Re-enable button on upload error
            checkFormValidity();
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
                uploadButton.disabled = false; // Re-enable button on polling error
                checkFormValidity();
            }
        }, 3000); // Poll every 3 seconds
    }

    function handleStatusUpdate(data) {
        // Update status message, potentially with a loader
        let message = data.message || `Status: ${data.status}`;
        
        // Check if the message contains progress information
        const progressMatch = data.message ? data.message.match(/(\d+)\/(\d+) chunks processed/) : null;
        if (progressMatch) {
            const processed = parseInt(progressMatch[1]);
            const total = parseInt(progressMatch[2]);
            const remaining = total - processed;
            message += ` (${remaining} chunks remaining)`;
        }

        statusArea.innerHTML = `<div class="loader"></div><span>${message}</span>`;

        if (data.status === "complete") {
            clearInterval(pollingInterval);
            statusArea.innerHTML = `<span>Conversion Complete!</span>`; // No loader needed
            resultArea.classList.remove("hidden");
            const audioUrl = `/api/v1/download/${data.filename}`;
            audioPlayer.src = audioUrl;
            downloadLink.href = audioUrl;
            downloadLink.download = data.filename;
            uploadButton.disabled = false; // Re-enable button
            checkFormValidity();
        } else if (data.status === "failed") {
            clearInterval(pollingInterval);
            showError(data.message || "An unknown error occurred during conversion.");
            uploadButton.disabled = false; // Re-enable button
            checkFormValidity();
        }
    }

    function showError(message) {
        statusArea.innerHTML = ""; // Clear status area
        errorArea.classList.remove("hidden");
        errorMessage.textContent = message;
        uploadButton.disabled = false; // Ensure button is re-enabled
        checkFormValidity();
    }

    function resetUI() {
        statusArea.innerHTML = "";
        resultArea.classList.add("hidden");
        errorArea.classList.add("hidden");
        errorMessage.textContent = "";
        if (pollingInterval) {
            clearInterval(pollingInterval);
        }
        // Do not reset pdfFile or voiceSelect here, as user might want to retry with same inputs
        // uploadButton.disabled = true; // Will be set by checkFormValidity
    }

    // --- Initial setup ---
    loadVoices();
    checkFormValidity(); // Initial check to set button state
});
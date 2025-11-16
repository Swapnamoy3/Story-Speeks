import re
import nltk
from typing import List

# Ensure the 'punkt' tokenizer is downloaded
try:
    nltk.data.find('tokenizers/punkt')
except nltk.downloader.DownloadError:
    nltk.download('punkt')

def chunk_text(text: str) -> List[str]:
    """
    Cleans a raw text string and splits it into a list of sentences.

    Args:
        text: The raw text content.

    Returns:
        A list of sentences.
    """
    # Normalize whitespace and remove extra newlines
    cleaned_text = re.sub(r'\s+', ' ', text).strip()
    cleaned_text = re.sub(r'(\n\s*\n)+', '\n\n', cleaned_text)

    # Use NLTK for sentence tokenization
    sentences = nltk.sent_tokenize(cleaned_text)
    chunks = []
    chunk = []
    for sentence in sentences:
        if len(chunk) < 10:
            chunk.append(sentence)
        else:
            chunks.append(chunk)
            chunk = [sentence]
    if chunk:
        chunks.append(chunk)

    return chunks

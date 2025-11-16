import fitz # PyMuPDF

def parse_pdf(file_path: str) -> str:
    """
    Parses a PDF file and extracts its text content.

    Args:
        file_path: The path to the PDF file.

    Returns:
        A string containing all text extracted from the PDF.
    """
    text_content = ""
    try:
        document = fitz.open(file_path)
        for page_num in range(document.page_count):
            page = document.load_page(page_num)
            text_content += page.get_text()
        document.close()
    except Exception as e:
        print(f"Error parsing PDF {file_path}: {e}")
        raise
    return text_content

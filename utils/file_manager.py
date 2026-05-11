import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCUMENTS_DIR = os.path.join(BASE_DIR, "test_data", "documents")


def get_document_path(filename: str) -> str:
    path = os.path.join(DOCUMENTS_DIR, filename)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Test document not found: {path}")
    return path


# Convenience references
VALID_PDF = get_document_path("valid_doc.pdf")         # <2MB PDF
VALID_JPG = get_document_path("valid_image.jpg")       # <2MB JPG
VALID_PNG = get_document_path("valid_image.png")       # <2MB PNG
INVALID_FORMAT = get_document_path("invalid.docx")    # Wrong format
OVERSIZED_FILE = get_document_path("oversized.pdf")   # >2MB PDF
VALID_SIGNATURE = get_document_path("signature.png")  # Signature image
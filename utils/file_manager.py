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

# Part A certificate uploads accept PDF/JPG/PNG between 10 KB and 2 MB.
VALID_CERTIFICATE = get_document_path("certificate.pdf")         # ~360 KB PDF
UNDERSIZED_FILE = get_document_path("valid_doc.pdf")             # <10 KB PDF
UNSUPPORTED_CERTIFICATE = get_document_path("certificate.docx")  # >10 KB DOCX (wrong format, valid size)

# Part F certificate uploads accept PDF/JPG/PNG; the signature accepts JPG/PNG only (10 KB – 2 MB).
CERTIFICATE_JPG = get_document_path("certificate.jpg")           # ~74 KB JPG
CERTIFICATE_PNG = get_document_path("certificate.png")           # ~91 KB PNG
UNSUPPORTED_SPREADSHEET = get_document_path("certificate.xlsx")  # ~20 KB XLSX (wrong format)
SIGNATURE_JPG = get_document_path("signature_valid.jpg")         # ~25 KB JPG
SIGNATURE_PNG = get_document_path("signature_valid.png")         # ~55 KB PNG
OVERSIZED_IMAGE = get_document_path("oversized_image.jpg")       # ~30 MB JPG

# Documents step (enclosures) accepts PDF only, 10 KB – 2 MB.
REPLACEMENT_PDF = get_document_path("certificate_v2.pdf")        # ~360 KB PDF with a different name
EMPTY_PDF = get_document_path("empty.pdf")                       # 0-byte PDF

# Premises Photos accepts JPG / PNG only (use CERTIFICATE_JPG / CERTIFICATE_PNG as photos).
UNSUPPORTED_PHOTO = get_document_path("office_photo.heic")       # ~20 KB HEIC (wrong format)
# document_reader_factory.py
import os
from document_reader import DocumentReader, FitzDocumentReader


class DocumentReaderFactory:
    """Factory to create appropriate document reader based on file extension."""

    SUPPORTED_EXTENSIONS = {'.pdf', '.epub', '.mobi', '.fb2', '.xps', '.cbz'}

    @staticmethod
    def create(filepath: str) -> DocumentReader:
        ext = os.path.splitext(filepath)[1].lower()
        if ext not in DocumentReaderFactory.SUPPORTED_EXTENSIONS:
            raise ValueError(f"Unsupported file format: {ext}. Supported: {DocumentReaderFactory.SUPPORTED_EXTENSIONS}")
        # All supported formats use FitzDocumentReader (PyMuPDF handles them natively)
        return FitzDocumentReader(filepath)
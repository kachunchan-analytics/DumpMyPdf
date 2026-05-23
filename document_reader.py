# document_reader.py
from abc import ABC, abstractmethod
import os
import fitz
fitz.TOOLS.mupdf_display_errors(False)   # silence font missing warnings


class DocumentReader(ABC):
    """Abstract base class for document readers."""

    @abstractmethod
    def get_num_pages(self) -> int:
        pass

    @abstractmethod
    def get_page_text(self, page_num: int) -> str:
        pass

    @abstractmethod
    def get_page(self, page_num: int):
        """Return a fitz.Page object (or equivalent)."""
        pass

    @abstractmethod
    def close(self):
        pass


class FitzDocumentReader(DocumentReader):
    """
    Document reader using PyMuPDF (fitz).
    Supports PDF, EPUB, MOBI, FB2, XPS, CBZ, etc.
    """

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.doc = None

    def _ensure_doc(self):
        if self.doc is None:
            if not os.path.exists(self.filepath):
                raise FileNotFoundError(f"File not found: {self.filepath}")
            if not os.access(self.filepath, os.R_OK):
                raise PermissionError(f"File not readable: {self.filepath}")
            try:
                self.doc = fitz.open(self.filepath)
                # No page size setting – use defaults (works for all formats)
            except Exception as e:
                raise RuntimeError(f"Failed to open document {self.filepath}: {e}") from e
        return self.doc

    def get_num_pages(self) -> int:
        return len(self._ensure_doc())

    def get_page_text(self, page_num: int) -> str:
        doc = self._ensure_doc()
        if page_num < 0 or page_num >= len(doc):
            raise IndexError(f"Page {page_num} out of range (0..{len(doc)-1})")
        try:
            return doc[page_num].get_text()
        except Exception as e:
            raise RuntimeError(f"Failed to extract text from {self.filepath} page {page_num}") from e

    def get_page(self, page_num: int):
        doc = self._ensure_doc()
        if page_num < 0 or page_num >= len(doc):
            raise IndexError(f"Page {page_num} out of range")
        return doc[page_num]

    def close(self):
        if self.doc:
            self.doc.close()
            self.doc = None

    def __del__(self):
        self.close()
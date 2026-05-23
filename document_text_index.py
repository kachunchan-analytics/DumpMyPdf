# document_text_index.py (renamed from pdf_text_index.py)
import os
import pandas as pd
from typing import List, Tuple
from traceback_logger import TracebackLogger, Status
from document_reader_factory import DocumentReaderFactory


class DocumentTextIndex:
    """Builds a pandas Series index of text from all supported documents in a directory."""

    def __init__(self, directory: str, logger: TracebackLogger):
        self.directory = directory
        self.logger = logger
        self.document_series = None   # pd.Series with MultiIndex (filepath, page_num)
        self._build_index()

    def _build_index(self):
        if not os.path.isdir(self.directory):
            self.logger.log(Status.NOTFOUND, message=f"Directory not found: {self.directory}")
            self.document_series = pd.Series(dtype=object)
            return

        # Find all supported files
        supported_extensions = DocumentReaderFactory.SUPPORTED_EXTENSIONS
        files = [f for f in os.listdir(self.directory) if os.path.splitext(f)[1].lower() in supported_extensions]

        if not files:
            self.logger.log(Status.NOTFOUND, message="No supported files (PDF, EPUB, etc.) found in directory")
            self.document_series = pd.Series(dtype=object)
            return

        print(f"Indexing {len(files)} file(s)... This may take a moment.")
        index_data = []

        for filename in files:
            full_path = os.path.join(self.directory, filename)
            reader = None
            try:
                reader = DocumentReaderFactory.create(full_path)
                num_pages = reader.get_num_pages()
                for page_num in range(num_pages):
                    text = reader.get_page_text(page_num)
                    index_data.append(((full_path, page_num), text))
            except Exception as e:
                self.logger.log(Status.ERROR, exc=e, message=f"Failed to index {filename}")
            finally:
                if reader:
                    reader.close()

        if not index_data:
            self.document_series = pd.Series(dtype=object)
            return

        indices, texts = zip(*index_data)
        multi_index = pd.MultiIndex.from_tuples(indices, names=["filepath", "page_num"])
        self.document_series = pd.Series(data=texts, index=multi_index)
        print(f"Indexed {len(self.document_series)} page(s) from {len(files)} file(s).")

    def search(self, keyword: str, case_sensitive: bool = False) -> List[Tuple[str, int]]:
        if self.document_series is None or self.document_series.empty:
            return []
        if case_sensitive:
            mask = self.document_series.str.contains(keyword, na=False, regex=False)
        else:
            mask = self.document_series.str.contains(keyword, na=False, regex=False, case=False)
        matched_indices = self.document_series[mask].index
        return [tuple(idx) for idx in matched_indices]

    def refresh(self):
        self._build_index()
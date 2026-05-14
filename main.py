import os
import pypdf
import pandas as pd
from typing import List, Tuple
from traceback_logger import TracebackLogger, Status

# ----------------------------------------------------------------------
# Config
# ----------------------------------------------------------------------
OUTPUT_FILENAME = "extracted_results.pdf"

# ----------------------------------------------------------------------
# PDFReader (fixed: keeps file handle open)
# ----------------------------------------------------------------------
class PDFReader:
    """Handles opening a PDF file and extracting text/page objects."""

    def __init__(self, filepath: str):
        self.filepath = filepath
        self._reader = None
        self._file_handle = None   # Keep file open

    def _ensure_reader(self):
        """Lazy load the PdfReader, with LBYL checks."""
        if self._reader is None:
            # LBYL: Check file exists and is readable
            if not os.path.exists(self.filepath):
                raise FileNotFoundError(f"PDF file not found: {self.filepath}")
            if not os.access(self.filepath, os.R_OK):
                raise PermissionError(f"PDF file not readable: {self.filepath}")

            # Open file and keep handle open (no with block)
            try:
                self._file_handle = open(self.filepath, "rb")
                self._reader = pypdf.PdfReader(self._file_handle)
            except Exception as e:
                # Clean up if opening fails
                if self._file_handle:
                    self._file_handle.close()
                raise RuntimeError(f"Failed to open PDF {self.filepath}: {e}") from e
        return self._reader

    def get_num_pages(self) -> int:
        """Return number of pages in the PDF."""
        return len(self._ensure_reader().pages)

    def get_page_text(self, page_num: int) -> str:
        """Extract text from a specific page (0-indexed)."""
        reader = self._ensure_reader()
        if page_num < 0 or page_num >= len(reader.pages):
            raise IndexError(f"Page {page_num} out of range (0..{len(reader.pages)-1})")
        try:
            page = reader.pages[page_num]
            return page.extract_text()
        except Exception as e:
            raise RuntimeError(f"Failed to extract text from {self.filepath} page {page_num}") from e

    def get_page(self, page_num: int):
        """Return the raw page object (for concatenation)."""
        reader = self._ensure_reader()
        if page_num < 0 or page_num >= len(reader.pages):
            raise IndexError(f"Page {page_num} out of range")
        return reader.pages[page_num]

    def close(self):
        """Explicitly close the underlying file handle if still open."""
        if self._file_handle and not self._file_handle.closed:
            self._file_handle.close()

    def __del__(self):
        """Ensure file handle is closed when the object is destroyed."""
        self.close()

# ----------------------------------------------------------------------
# PDFTextIndex – builds a pandas Series of page text once
# ----------------------------------------------------------------------
class PDFTextIndex:
    """
    Extracts text from every page of every PDF in a directory,
    stores it in a pandas Series, and provides fast keyword search.
    """

    def __init__(self, directory: str, logger: TracebackLogger):
        self.directory = directory
        self.logger = logger
        self.pdf_panda_series = None
        self._build_index()

    def _build_index(self):
        """Scan directory, extract page text, create Series."""
        if not os.path.isdir(self.directory):
            self.logger.log(Status.NOTFOUND, message=f"Directory not found: {self.directory}")
            self.pdf_panda_series = pd.Series(dtype=object)
            return

        pdf_files = [f for f in os.listdir(self.directory) if f.lower().endswith(".pdf")]
        if not pdf_files:
            self.logger.log(Status.NOTFOUND, message="No PDF files found in directory")
            self.pdf_panda_series = pd.Series(dtype=object)
            return

        print(f"Indexing {len(pdf_files)} PDF file(s)... This may take a moment.")

        index_data = []  # list of (index_tuple, text)
        for filename in pdf_files:
            full_path = os.path.join(self.directory, filename)
            try:
                reader = PDFReader(full_path)
                num_pages = reader.get_num_pages()
                for page_num in range(num_pages):
                    text = reader.get_page_text(page_num)
                    index_data.append(((full_path, page_num), text))
                reader.close()
            except Exception as e:
                self.logger.log(Status.ERROR, exc=e, message=f"Failed to index {filename}")

        if not index_data:
            self.pdf_panda_series = pd.Series(dtype=object)
            return

        # Unpack and create MultiIndex
        indices, texts = zip(*index_data)
        multi_index = pd.MultiIndex.from_tuples(indices, names=["filepath", "page_num"])
        self.pdf_panda_series = pd.Series(data=texts, index=multi_index)
        print(f"Indexed {len(self.pdf_panda_series)} page(s) from {len(pdf_files)} file(s).")

    def search(self, keyword: str, case_sensitive: bool = False) -> List[Tuple[str, int]]:
        """
        Return list of (filepath, page_num) where keyword appears in page text.
        """
        if self.pdf_panda_series is None or self.pdf_panda_series.empty:
            return []

        if case_sensitive:
            mask = self.pdf_panda_series.str.contains(keyword, na=False, regex=False)
        else:
            mask = self.pdf_panda_series.str.contains(keyword, na=False, regex=False, case=False)

        matched_indices = self.pdf_panda_series[mask].index
        # Convert MultiIndex to list of tuples (filepath, page_num)
        return [tuple(idx) for idx in matched_indices]

    def refresh(self):
        """Re‑build the index from scratch."""
        self._build_index()

# ----------------------------------------------------------------------
# PDFConcatenator (unchanged)
# ----------------------------------------------------------------------
class PDFConcatenator:
    """Combine pages from multiple PDFs into a single PDF."""

    def _validate_output_path(self, output_path: str, logger: TracebackLogger) -> bool:
        """LBYL: Check if we can write to output path."""
        dir_name = os.path.dirname(output_path) or "."
        if not os.path.exists(dir_name):
            logger.log(Status.ERROR, message=f"Output directory does not exist: {dir_name}")
            return False
        if not os.access(dir_name, os.W_OK):
            logger.log(Status.ERROR, message=f"Output directory not writable: {dir_name}")
            return False
        if not output_path.lower().endswith(".pdf"):
            logger.log(Status.ERROR, message=f"Output file must have .pdf extension: {output_path}")
            return False
        return True

    def concatenate(self, pages_info: List[Tuple[str, int]], output_path: str, logger: TracebackLogger) -> bool:
        """
        Write a new PDF containing the specified pages.
        Returns True on success, False on failure.
        """
        if not pages_info:
            logger.log(Status.NOTFOUND, message="No pages to concatenate")
            return False

        if not self._validate_output_path(output_path, logger):
            return False

        for filename, page_num in pages_info:
            if not os.path.isfile(filename):
                logger.log(Status.ERROR, message=f"Missing file: {filename}")
                return False
            if not os.access(filename, os.R_OK):
                logger.log(Status.ERROR, message=f"Cannot read file: {filename}")
                return False

        writer = pypdf.PdfWriter()
        try:
            for filename, page_num in pages_info:
                reader = PDFReader(filename)
                page = reader.get_page(page_num)
                writer.add_page(page)
                reader.close()

            with open(output_path, "wb") as out_file:
                writer.write(out_file)
            return True
        except Exception as e:
            logger.log(Status.ERROR, exc=e, message=f"Failed to create {output_path}")
            return False

# ----------------------------------------------------------------------
# Controller (uses PDFTextIndex, not PDFSearcher)
# ----------------------------------------------------------------------
class Controller:
    def __init__(self):
        self.logger = TracebackLogger()
        # Build the index once at startup
        self.index = PDFTextIndex(os.getcwd(), self.logger)
        self.concatenator = PDFConcatenator()

    def run(self):
        print("PDF Keyword Search Tool")
        print("-----------------------")
        print("Searches for keywords in all PDF files in the current directory.")
        print("Type 'quit' or 'exit' to stop.\n")

        while True:
            keyword = input("Enter keyword to search (or 'quit' to exit): ").strip()
            if keyword.lower() in ('quit', 'exit', ''):
                print("Goodbye!")
                break

            if not keyword:
                print("No keyword entered. Please try again.\n")
                continue

            print(f"Searching for '{keyword}'...")
            results = self.index.search(keyword)

            if not results:
                print(f"No pages found containing '{keyword}'.\n")
                continue

            print(f"Found {len(results)} page(s) containing '{keyword}'.")
            print(f"Output will be saved to: {OUTPUT_FILENAME}")

            success = self.concatenator.concatenate(results, OUTPUT_FILENAME, self.logger)
            if success:
                print(f"\033[92mSuccessfully created: {OUTPUT_FILENAME}\033[0m\n")
            else:
                print("Failed to create output PDF. See error details above.\n")

# ----------------------------------------------------------------------
# Main entry point
# ----------------------------------------------------------------------
def main():
    app = Controller()
    app.run()

if __name__ == "__main__":
    main()
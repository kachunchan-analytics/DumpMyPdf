import os
import pypdf
from pypdf import PdfReader
from typing import List, Tuple
from traceback_logger import TracebackLogger, Status

# ----------------------------------------------------------------------
# PDFReader
# ----------------------------------------------------------------------
class PDFReader:
    """Handles opening a PDF file and extracting text/page objects."""

    def __init__(self, filepath: str):
        self.filepath = filepath
        self._reader = None

    def _ensure_reader(self):
        """Lazy load the PdfReader, with LBYL checks."""
        if self._reader is None:
            # LBYL: Check file exists and is readable
            if not os.path.exists(self.filepath):
                raise FileNotFoundError(f"PDF file not found: {self.filepath}")
            if not os.access(self.filepath, os.R_OK):
                raise PermissionError(f"PDF file not readable: {self.filepath}")

            # Open and read – may still raise PyPDF errors (corrupted file)
            try:
                with open(self.filepath, "rb") as f:
                    self._reader = PyPDF.PdfReader(f)
            except Exception as e:
                raise RuntimeError(f"Failed to open PDF {self.filepath}: {e}") from e
        return self._reader

    def get_num_pages(self) -> int:
        """Return number of pages in the PDF."""
        return len(self._ensure_reader().pages)

    def get_page_text(self, page_num: int) -> str:
        """Extract text from a specific page (0-indexed)."""
        reader = self._ensure_reader()
        # LBYL: Check page index
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

# ----------------------------------------------------------------------
# PDFSearcher
# ----------------------------------------------------------------------
class PDFSearcher:
    """Search for a keyword across PDF files."""

    def __init__(self, logger: TracebackLogger):
        self.logger = logger

    def _is_valid_pdf_file(self, filepath: str) -> bool:
        """LBYL: Check if file looks like a readable PDF."""
        if not os.path.isfile(filepath):
            return False
        if not filepath.lower().endswith(".pdf"):
            return False
        if not os.access(filepath, os.R_OK):
            return False
        return True

    def search_in_file(self, filename: str, keyword: str) -> List[Tuple[str, int]]:
        """
        Search keyword in a single PDF file.
        Returns list of (filename, page_num) for pages containing keyword.
        """
        # LBYL: Validate file before trying to read
        if not self._is_valid_pdf_file(filename):
            self.logger.log(Status.ERROR, message=f"Skipping invalid/unreadable file: {filename}")
            return []

        result = []
        try:
            reader = PDFReader(filename)
            num_pages = reader.get_num_pages()
            for page_num in range(num_pages):
                text = reader.get_page_text(page_num)
                if keyword in text:
                    result.append((filename, page_num))
        except Exception as e:
            self.logger.log(Status.ERROR, exc=e, message=f"Search failed in {filename}")
        return result

    def search_in_directory(self, directory: str, keyword: str) -> List[Tuple[str, int]]:
        """
        Search all PDF files in the given directory for keyword.
        Returns combined list of (filename, page_num) from all files.
        """
        # LBYL: Check directory exists
        if not os.path.isdir(directory):
            self.logger.log(Status.NOTFOUND, message=f"Directory not found: {directory}")
            return []

        all_results = []
        pdf_files = [f for f in os.listdir(directory) if f.lower().endswith(".pdf")]
        if not pdf_files:
            self.logger.log(Status.NOTFOUND, message="No PDF files found in directory")
            return []

        for filename in pdf_files:
            full_path = os.path.join(directory, filename)
            results = self.search_in_file(full_path, keyword)
            all_results.extend(results)
        return all_results

# ----------------------------------------------------------------------
# PDFConcatenator
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
        # Ensure .pdf extension
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

        # LBYL: Validate output path before any processing
        if not self._validate_output_path(output_path, logger):
            return False

        # LBYL: Validate each input file exists and is readable
        for filename, page_num in pages_info:
            if not os.path.isfile(filename):
                logger.log(Status.ERROR, message=f"Missing file: {filename}")
                return False
            if not os.access(filename, os.R_OK):
                logger.log(Status.ERROR, message=f"Cannot read file: {filename}")
                return False
            # Note: we cannot validate page number without opening the file,
            # but that will be caught in the try block.

        writer = pypdf.PdfWriter()
        try:
            for filename, page_num in pages_info:
                reader = PDFReader(filename)
                # Page number validity is checked inside PDFReader.get_page()
                page = reader.get_page(page_num)
                writer.add_page(page)

            with open(output_path, "wb") as out_file:
                writer.write(out_file)
            return True
        except Exception as e:
            logger.log(Status.ERROR, exc=e, message=f"Failed to create {output_path}")
            return False

# ----------------------------------------------------------------------
# Controller (unchanged logic but uses improved classes)
# ----------------------------------------------------------------------
class Controller:
    def __init__(self):
        self.logger = TracebackLogger()
        self.searcher = PDFSearcher(self.logger)
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
            current_dir = os.getcwd()
            results = self.searcher.search_in_directory(current_dir, keyword)

            if not results:
                print(f"No pages found containing '{keyword}'.\n")
                continue

            print(f"Found {len(results)} page(s) containing '{keyword}'.")
            default_out = f"concatenated_{keyword}.pdf"
            out_name = input(f"Enter output PDF filename (default: {default_out}): ").strip()
            if not out_name:
                out_name = default_out
            # LBYL: Ensure .pdf extension
            if not out_name.lower().endswith(".pdf"):
                out_name += ".pdf"
                print(f"Added .pdf extension -> {out_name}")

            success = self.concatenator.concatenate(results, out_name, self.logger)
            if success:
                print(f"Successfully created: {out_name}\n")
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
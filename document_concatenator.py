# document_concatenator.py
import os
import tempfile
from pathlib import Path
from typing import List, Tuple
from collections import defaultdict
import fitz
from traceback_logger import TracebackLogger, Status


class DocumentConcatenator:
    """Concatenates pages from various source documents into a single PDF.
       For non-PDF documents, converts them using:
       1) Direct save (best)
       2) Text‑based reconstruction (selectable text)
       3) Rasterisation (always works, images)
    """

    def _validate_output_path(self, output_path: str, logger: TracebackLogger) -> bool:
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

    def _convert_text_based(self, src_doc, dest_pdf: str, page_size="a4") -> None:
        """Convert document to PDF by extracting text and reflowing onto pages.
        Uses built-in China-S font (covers English, Simplified Chinese, and most Traditional Chinese).
        """
        rect = fitz.paper_rect(page_size)
        pdf_doc = fitz.open()
        try:
            for page_num in range(len(src_doc)):
                text = src_doc[page_num].get_text()
                if not text.strip():
                    continue
                new_page = pdf_doc.new_page(width=rect.width, height=rect.height)
                margin = 36
                text_rect = fitz.Rect(margin, margin, rect.width - margin, rect.height - margin)
                # china-s works for English, Simplified Chinese, and most Traditional Chinese
                new_page.insert_textbox(text_rect, text, fontsize=11, fontname="china-s", align=0)
            pdf_doc.save(dest_pdf)
        finally:
            pdf_doc.close()

    def _convert_raster(self, src_doc, dest_pdf: str, dpi: int = 150) -> None:
        """Convert a document to PDF by rendering each page to an image (pixmap) and embedding it.
           Always works, but text is not selectable.
        """
        pdf_doc = fitz.open()
        try:
            for page_num in range(len(src_doc)):
                page = src_doc[page_num]
                pix = page.get_pixmap(dpi=dpi)
                new_page = pdf_doc.new_page(width=pix.width, height=pix.height)
                new_page.insert_image(fitz.Rect(0, 0, pix.width, pix.height), pixmap=pix)
            pdf_doc.save(dest_pdf)
        finally:
            pdf_doc.close()

    def _convert_to_pdf(self, src_path: str, dest_pdf: str, dpi: int = 150) -> None:
        """Convert any MuPDF‑supported document to PDF using three‑tier fallback."""
        src_doc = fitz.open(src_path)

        # Tier 1: Direct save (fast, text selectable, best fidelity)
        try:
            src_doc.save(dest_pdf)
            src_doc.close()
            print(f"Direct save succeeded for {Path(src_path).name}")
            return
        except Exception as e:
            print(f"Direct save failed for {Path(src_path).name}: {e}")

        # Tier 2: Text‑based reconstruction (selectable text, basic layout)
        try:
            self._convert_text_based(src_doc, dest_pdf)
            src_doc.close()
            print(f"Text‑based conversion succeeded for {Path(src_path).name}")
            return
        except Exception as e:
            print(f"Text‑based conversion failed for {Path(src_path).name}: {e}")

        # Tier 3: Rasterisation (always works, text as image)
        try:
            self._convert_raster(src_doc, dest_pdf, dpi)
            print(f"Rasterisation fallback used for {Path(src_path).name}")
        except Exception as e:
            raise RuntimeError(f"All conversion methods failed for {src_path}: {e}")
        finally:
            src_doc.close()

    def _get_pdf_path(self, filepath: str, temp_dir: str) -> str:
        """Return a PDF version of the given file."""
        if filepath.lower().endswith('.pdf'):
            return filepath

        stem = Path(filepath).stem
        temp_pdf = os.path.join(temp_dir, f"{stem}.pdf")
        if os.path.exists(temp_pdf):
            return temp_pdf

        self._convert_to_pdf(filepath, temp_pdf)
        return temp_pdf

    def concatenate(self, pages_info: List[Tuple[str, int]], output_path: str, logger: TracebackLogger) -> bool:
        if not pages_info:
            logger.log(Status.NOTFOUND, message="No pages to concatenate")
            return False
        if not self._validate_output_path(output_path, logger):
            return False

        pages_by_file = defaultdict(list)
        for filepath, page_num in pages_info:
            pages_by_file[filepath].append(page_num)

        with tempfile.TemporaryDirectory(prefix="doc_concat_") as temp_dir:
            output_doc = fitz.open()
            try:
                for orig_path, page_nums in pages_by_file.items():
                    pdf_path = self._get_pdf_path(orig_path, temp_dir)
                    src_doc = fitz.open(pdf_path)
                    try:
                        for page_num in sorted(set(page_nums)):
                            if page_num < len(src_doc):
                                output_doc.insert_pdf(src_doc, from_page=page_num, to_page=page_num)
                            else:
                                logger.log(Status.WARNING, message=f"Page {page_num} out of range in {orig_path}, skipping")
                    finally:
                        src_doc.close()
                output_doc.save(output_path)
                return True
            except Exception as e:
                logger.log(Status.ERROR, exc=e, message=f"Failed to create {output_path}")
                return False
            finally:
                output_doc.close()
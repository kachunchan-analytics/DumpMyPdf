import os
import fitz  # PyMuPDF
import pandas as pd
from typing import List, Tuple
from traceback_logger import TracebackLogger, Status

# ----------------------------------------------------------------------
# Config
# ----------------------------------------------------------------------
OUTPUT_FILENAME = "extracted_results.pdf"
ADDITIONAL_PAGES = 1

# Adding Extra Prompts 
ADD_PROMPT = True
PROMPT_LIST = [
    "Explain and Summarize the above contents with reference to the materials given. also use mermaid diagram besides the wordy content",
    "Compare and Contrast the above contents",
    "Identify any gaps or missing information in the above content",
    "What real-world applications does this content suggest?",
    "Rewrite this content in your own words",
    "Organize this content as a step-by-step process",
    "What additional topics should I study to complement this?",
    "What historical or contextual background would help understand this?",
    "TL;DR in 2 sentences"

]


# ----------------------------------------------------------------------
# PDFReader – using PyMuPDF only
# ----------------------------------------------------------------------
class PDFReader:
    """Handles opening a PDF file and extracting text/page objects using PyMuPDF."""

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.doc = None

    def _ensure_doc(self):
        if self.doc is None:
            if not os.path.exists(self.filepath):
                raise FileNotFoundError(f"PDF file not found: {self.filepath}")
            if not os.access(self.filepath, os.R_OK):
                raise PermissionError(f"PDF file not readable: {self.filepath}")
            try:
                self.doc = fitz.open(self.filepath)
            except Exception as e:
                raise RuntimeError(f"Failed to open PDF {self.filepath}: {e}") from e
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

# ----------------------------------------------------------------------
# PDFTextIndex – builds pandas Series once
# ----------------------------------------------------------------------
class PDFTextIndex:
    def __init__(self, directory: str, logger: TracebackLogger):
        self.directory = directory
        self.logger = logger
        self.pdf_panda_series = None
        self._build_index()

    def _build_index(self):
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
        index_data = []

        for filename in pdf_files:
            full_path = os.path.join(self.directory, filename)
            reader = None
            try:
                reader = PDFReader(full_path)
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
            self.pdf_panda_series = pd.Series(dtype=object)
            return

        indices, texts = zip(*index_data)
        multi_index = pd.MultiIndex.from_tuples(indices, names=["filepath", "page_num"])
        self.pdf_panda_series = pd.Series(data=texts, index=multi_index)
        print(f"Indexed {len(self.pdf_panda_series)} page(s) from {len(pdf_files)} file(s).")

    def search(self, keyword: str, case_sensitive: bool = False) -> List[Tuple[str, int]]:
        if self.pdf_panda_series is None or self.pdf_panda_series.empty:
            return []
        if case_sensitive:
            mask = self.pdf_panda_series.str.contains(keyword, na=False, regex=False)
        else:
            mask = self.pdf_panda_series.str.contains(keyword, na=False, regex=False, case=False)
        matched_indices = self.pdf_panda_series[mask].index
        return [tuple(idx) for idx in matched_indices]

    def refresh(self):
        self._build_index()

# ----------------------------------------------------------------------
# PDFConcatenator – using PyMuPDF (fast insertion)
# ----------------------------------------------------------------------
class PDFConcatenator:
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

    def concatenate(self, pages_info: List[Tuple[str, int]], output_path: str, logger: TracebackLogger) -> bool:
        if not pages_info:
            logger.log(Status.NOTFOUND, message="No pages to concatenate")
            return False
        if not self._validate_output_path(output_path, logger):
            return False

        # Create output document
        output_doc = fitz.open()
        try:
            for filename, page_num in pages_info:
                # Open source PDF
                src_doc = fitz.open(filename)
                try:
                    # Insert the specific page (preserving all content)
                    output_doc.insert_pdf(src_doc, from_page=page_num, to_page=page_num)
                finally:
                    src_doc.close()
            output_doc.save(output_path)
            return True
        except Exception as e:
            logger.log(Status.ERROR, exc=e, message=f"Failed to create {output_path}")
            return False
        finally:
            output_doc.close()

# ----------------------------------------------------------------------
# PromptHandler – supports fence-only, fence+prompt, or none
# ----------------------------------------------------------------------
class PromptHandler:
    # Mode constants
    MODE_RAW = 0
    MODE_FENCE_ONLY = 1
    MODE_PREDEFINED = 2      # fence + predefined prompt
    MODE_CUSTOM = 3          # fence + custom prompt

    def __init__(self, prompt_list: List[str], logger: TracebackLogger):
        self.prompt_list = prompt_list
        self.logger = logger
        self.mode = self.MODE_RAW
        self.selected_prompt = None

    def _handle_raw_mode(self) -> bool:
        """Set raw mode (no fence, no prompt)."""
        self.mode = self.MODE_RAW
        self.selected_prompt = None
        return False

    def _handle_fence_only(self) -> bool:
        """Set fence-only mode."""
        self.mode = self.MODE_FENCE_ONLY
        self.selected_prompt = None
        return True

    def _handle_predefined_prompt(self) -> bool:
        """Show list of predefined prompts, let user choose one."""
        YELLOW = "\033[93m"
        RESET = "\033[0m"
        
        if not self.prompt_list:
            print("No predefined prompts available. Falling back to fence only.")
            return self._handle_fence_only()

        print("\nAvailable prompts:")
        for idx, prompt in enumerate(self.prompt_list, start=1):
            print(f"  {YELLOW}{idx}. {prompt}{RESET}")

        while True:
            try:
                p_choice = input("Select prompt number: ").strip()
                p_num = int(p_choice)
                if 1 <= p_num <= len(self.prompt_list):
                    self.mode = self.MODE_PREDEFINED
                    self.selected_prompt = self.prompt_list[p_num - 1]
                    return True
                else:
                    print(f"Please enter a number between 1 and {len(self.prompt_list)}.")
            except ValueError:
                print("Invalid input. Enter a number.")
            except KeyboardInterrupt:
                print("\nPrompt selection cancelled. Falling back to fence only.")
                return self._handle_fence_only()

    def _handle_custom_prompt(self) -> bool:
        """Ask user to type a custom prompt."""
        print("\nEnter your custom prompt (cannot be empty):")
        while True:
            try:
                custom = input("> ").strip()
                if custom:
                    self.mode = self.MODE_CUSTOM
                    self.selected_prompt = custom
                    return True
                else:
                    print("Prompt cannot be empty. Please enter a valid prompt.")
            except KeyboardInterrupt:
                print("\nCustom prompt cancelled. Falling back to fence only.")
                return self._handle_fence_only()

    def display_and_select(self) -> bool:
        """Display menu and let user choose output formatting mode.
        Returns True if any formatting (fence) is selected, False if raw mode.
        """
        YELLOW = "\033[93m"
        RESET = "\033[0m"
        
        print("\nText output formatting options:")
        print(f"  {YELLOW}{self.MODE_RAW}. No fence, no prompt (raw text){RESET}")
        print(f"  {YELLOW}{self.MODE_FENCE_ONLY}. Add backticks fence only{RESET}")
        print(f"  {YELLOW}{self.MODE_PREDEFINED}. Add backticks fence + select a predefined prompt{RESET}")
        print(f"  {YELLOW}{self.MODE_CUSTOM}. Add backticks fence + write custom prompt{RESET}")

        while True:
            try:
                choice = input("Select option (0, 1, 2, 3): ").strip()
                mode = int(choice)
                if mode == self.MODE_RAW:
                    return self._handle_raw_mode()
                elif mode == self.MODE_FENCE_ONLY:
                    return self._handle_fence_only()
                elif mode == self.MODE_PREDEFINED:
                    return self._handle_predefined_prompt()
                elif mode == self.MODE_CUSTOM:
                    return self._handle_custom_prompt()
                else:
                    print("Please enter 0, 1, 2, or 3.")
            except ValueError:
                print("Invalid input. Enter a number.")
            except KeyboardInterrupt:
                print("\nSelection cancelled. Using raw output.")
                return self._handle_raw_mode()

    def format_output(self, raw_text: str) -> str:
        """Apply formatting based on selected mode."""
        if self.mode == self.MODE_RAW:
            return raw_text
        elif self.mode == self.MODE_FENCE_ONLY:
            return f"```\n{raw_text}\n```"
        elif self.mode == self.MODE_PREDEFINED or self.mode == self.MODE_CUSTOM:
            return f"```\n{raw_text}\n```\n{self.selected_prompt}"
        else:
            return raw_text  # fallback

    def reset(self):
        self.mode = self.MODE_RAW
        self.selected_prompt = None

# ----------------------------------------------------------------------
# Controller (modified)
# ----------------------------------------------------------------------
class Controller:
    def __init__(self):
        self.logger = TracebackLogger()
        self.index = PDFTextIndex(os.getcwd(), self.logger)
        self.concatenator = PDFConcatenator()
        self.additional_pages = ADDITIONAL_PAGES

        # NEW: Initialize prompt handler if enabled
        if ADD_PROMPT:
            self.prompt_handler = PromptHandler(PROMPT_LIST, self.logger)
        else:
            self.prompt_handler = None

    def _expand_with_context(self, results: List[Tuple[str, int]], extra_pages: int) -> List[Tuple[str, int]]:
        # (unchanged from original)
        if not results or extra_pages <= 0:
            return results[:]

        existing_pages = set(self.index.pdf_panda_series.index) if self.index.pdf_panda_series is not None else set()
        expanded = []
        seen = set()

        for filepath, page_num in results:
            key = (filepath, page_num)
            if key not in seen:
                expanded.append(key)
                seen.add(key)

            for offset in range(1, extra_pages + 1):
                extra_key = (filepath, page_num + offset)
                if extra_key in existing_pages and extra_key not in seen:
                    expanded.append(extra_key)
                    seen.add(extra_key)

        return expanded

    def _write_text_output(self, results: List[Tuple[str, int]], output_pdf_path: str) -> bool:
        """Write extracted texts to .txt, optionally wrapped and with prompt."""
        txt_path = output_pdf_path.replace('.pdf', '.txt')
        # Build raw text content first
        raw_lines = []
        for filepath, page_num in results:
            page_text = self.index.pdf_panda_series.loc[(filepath, page_num)]
            raw_lines.append(f"--- {os.path.basename(filepath)} page {page_num + 1} ---")
            raw_lines.append(page_text)
            raw_lines.append("")  # blank line between entries
        raw_text = "\n".join(raw_lines)

        # NEW: Apply prompt formatting if handler exists
        if self.prompt_handler:
            final_text = self.prompt_handler.format_output(raw_text)
        else:
            final_text = raw_text

        try:
            with open(txt_path, 'w', encoding='utf-8') as f:
                f.write(final_text)
            return True
        except Exception as e:
            self.logger.log(Status.ERROR, exc=e, message=f"Failed to write text file: {txt_path}")
            return False

    def run(self):
        print("PDF Keyword Search Tool")
        print("-----------------------")
        print("Searches for keywords in all PDF files in the current directory.")
        print(f"Will include {self.additional_pages} extra page(s) after each match for context.\n")
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
                print(f"\033[93mNo pages found containing '{keyword}'.\n\033[0m")
                continue

            expanded_results = self._expand_with_context(results, self.additional_pages)

            print(f"Found {len(results)} page(s) containing '{keyword}'.")
            if self.additional_pages > 0:
                print(f"After adding {self.additional_pages} extra page(s) after each match (no duplicates), "
                      f"total pages to extract: {len(expanded_results)}")

            # NEW: Ask for prompt selection if prompt_handler exists
            if self.prompt_handler:
                print("\nWould you like to add a prompt to the text output?")
                self.prompt_handler.display_and_select()  # stores selected_prompt internally

            print(f"Output will be saved to: {OUTPUT_FILENAME}")

            success = self.concatenator.concatenate(expanded_results, OUTPUT_FILENAME, self.logger)
            if success:
                print(f"\033[92mSuccessfully created: {OUTPUT_FILENAME}\033[0m")
                if self._write_text_output(expanded_results, OUTPUT_FILENAME):
                    txt_name = OUTPUT_FILENAME.replace('.pdf', '.txt')
                    print(f"\033[92mSuccessfully created: {txt_name}\033[0m\n")
                else:
                    print("\033[93mWarning: Text file could not be created.\033[0m\n")
            else:
                print("Failed to create output PDF. See error details above.\n")

# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------
def main():
    try:
        app = Controller()
        app.run()
    except KeyboardInterrupt:
        print("\n\033[93mProgram terminated by user.\033[0m")
    except Exception as e:
        print(f"\033[91mUnexpected error: {e}\033[0m")
        raise

if __name__ == "__main__":
    main()
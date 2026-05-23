import os
from traceback_logger import TracebackLogger, Status
from cli_selector import CliSelector
from document_text_index import DocumentTextIndex
from document_concatenator import DocumentConcatenator
from prompt_handler import PromptHandler 
from typing import List, Tuple

# Config (from original)
OUTPUT_FILENAME = "extracted_results.pdf"
ADDITIONAL_PAGES = 1
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


class Controller:
    def __init__(self):
        self.logger = TracebackLogger()
        self.index = DocumentTextIndex(os.getcwd(), self.logger)
        self.concatenator = DocumentConcatenator()
        self.additional_pages = ADDITIONAL_PAGES

        if ADD_PROMPT:
            self.prompt_handler = PromptHandler(PROMPT_LIST, self.logger)
        else:
            self.prompt_handler = None

    def _expand_with_context(self, results: List[Tuple[str, int]], extra_pages: int) -> List[Tuple[str, int]]:
        if not results or extra_pages <= 0:
            return results[:]

        existing_pages = set(self.index.document_series.index) if self.index.document_series is not None else set()
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
        txt_path = output_pdf_path.replace('.pdf', '.txt')
        raw_lines = []
        for filepath, page_num in results:
            page_text = self.index.document_series.loc[(filepath, page_num)]
            raw_lines.append(f"--- {os.path.basename(filepath)} page {page_num + 1} ---")
            raw_lines.append(page_text)
            raw_lines.append("")
        raw_text = "\n".join(raw_lines)

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
        print("Document Keyword Search Tool (PDF, EPUB, etc.)")
        print("-----------------------------------------------")
        print("Searches for keywords in all supported documents in the current directory.")
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

            if self.prompt_handler:
                print("\nWould you like to add a prompt to the text output?")
                self.prompt_handler.display_and_select()

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
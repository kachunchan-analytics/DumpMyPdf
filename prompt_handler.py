# prompt_handler.py
from typing import List
from traceback_logger import TracebackLogger
from cli_selector import CliSelector


class PromptHandler:
    MODE_RAW = 0
    MODE_FENCE_ONLY = 1
    MODE_PREDEFINED = 2
    MODE_CUSTOM = 3

    def __init__(self, prompt_list: List[str], logger: TracebackLogger):
        self.prompt_list = prompt_list
        self.logger = logger
        self.selector = CliSelector()
        self.mode = self.MODE_RAW
        self.selected_prompt = None

    def display_and_select(self) -> bool:
        """Let user choose output formatting mode."""
        options = {
            '0': "No fence, no prompt (raw text)",
            '1': "Add backticks fence only",
            '2': "Add backticks fence + select a predefined prompt",
            '3': "Add backticks fence + write custom prompt"
        }
        print("\n")
        self.selector.set(
            prompt="Text output formatting options. Select option (0-3): ",
            choices=['0', '1', '2', '3'],
            display_dict=options
        )
        choice = self.selector.ask()

        if choice == '0':
            return self._handle_raw_mode()
        elif choice == '1':
            return self._handle_fence_only()
        elif choice == '2':
            return self._handle_predefined_prompt()
        elif choice == '3':
            return self._handle_custom_prompt()
        else:
            return self._handle_raw_mode()

    def _handle_predefined_prompt(self) -> bool:
        if not self.prompt_list:
            print("No predefined prompts available. Falling back to fence only.")
            return self._handle_fence_only()

        print("\nAvailable prompts:")
        options = {str(idx): prompt for idx, prompt in enumerate(self.prompt_list, start=1)}
        
        self.selector.set(
            prompt=f"Select prompt number (1-{len(self.prompt_list)}): ",
            choices=[str(i) for i in range(1, len(self.prompt_list) + 1)],
            display_dict=options
        )
        choice = self.selector.ask()
        idx = int(choice) - 1
        self.mode = self.MODE_PREDEFINED
        self.selected_prompt = self.prompt_list[idx]
        return True

    def _handle_raw_mode(self) -> bool:
        self.mode = self.MODE_RAW
        self.selected_prompt = None
        return False

    def _handle_fence_only(self) -> bool:
        self.mode = self.MODE_FENCE_ONLY
        self.selected_prompt = None
        return True

    def _handle_custom_prompt(self) -> bool:
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

    def format_output(self, raw_text: str) -> str:
        if self.mode == self.MODE_RAW:
            return raw_text
        elif self.mode == self.MODE_FENCE_ONLY:
            return f"```\n{raw_text}\n```"
        elif self.mode == self.MODE_PREDEFINED or self.mode == self.MODE_CUSTOM:
            return f"```\n{raw_text}\n```\n{self.selected_prompt}"
        else:
            return raw_text

    def reset(self):
        self.mode = self.MODE_RAW
        self.selected_prompt = None
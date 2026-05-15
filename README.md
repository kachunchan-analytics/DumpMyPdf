# 📄 PDF Keyword Search

Search all PDFs in a directory by keyword. Extract matching pages into a new PDF + text file with optional prompts.

## 📦 Install

```bash
uv sync
```

## 🚀 Usage

1. Place script in a folder with PDFs.
2. Run: `uv run main.py`
3. Enter keyword.
4. Choose text output formatting (optional).
5. Get `extracted_results.pdf` + `extracted_results.txt`.

## ⚙️ How it works

- Indexes all PDF pages (once) using PyMuPDF + pandas.
- Searches case‑insensitive (default).
- Copies matching pages + optional context pages into a new PDF.
- Exports text with three formatting options:
  - **Raw**: Plain text with headers `--- filename.pdf page N ---`
  - **Fence only**: Text wrapped in triple backticks
  - **Fence + prompt**: Wrapped text followed by a selected prompt

## 📁 Output files

| File | Content |
|------|---------|
| `extracted_results.pdf` | Exact pages (original layout) |
| `extracted_results.txt` | Plain text (optionally fenced + prompted) |

## 🎨 Output formatting

When `ADD_PROMPT = True` in config, the program offers:

```
0. No fence, no prompt (raw text)
1. Add backticks fence only
2. Add backticks fence + select a prompt
```

**Example with fence + prompt:**
````
```
--- doc.pdf page 1 ---
Content here...
```
Explain and Summarize the above contents
````

## ⚙️ Configuration

Edit the config section at the top of `main.py`:

| Variable | Description |
|----------|-------------|
| `OUTPUT_FILENAME` | Output PDF name (default: `extracted_results.pdf`) |
| `ADDITIONAL_PAGES` | Context pages after each match |
| `ADD_PROMPT` | Enable/disable prompt selection |
| `PROMPT_LIST` | List of prompts to offer user |

## 📋 Dependencies

- Python 3.8+
- `PyMuPDF`
- `pandas`
- `traceback_logger` (custom – included)

## 📄 License

MIT
# 📄 Document Keyword Search (PDF, EPUB, and more)

Search all supported documents in a directory by keyword. Extract matching pages into a new PDF + text file with optional prompts.  
Supports **PDF, EPUB, MOBI, FB2, XPS, CBZ** – any format that PyMuPDF (MuPDF) can read.

## 📦 Install

```bash
uv sync
```

## 🚀 Usage

1. Place the script in a folder with documents (`.pdf`, `.epub`, etc.).
2. Run: `uv run main.py`
3. Enter a keyword.
4. Choose text output formatting (optional).
5. Get `extracted_results.pdf` + `extracted_results.txt`.

## ⚙️ How it works

- Indexes all pages of every supported document using PyMuPDF + pandas.
- Searches case‑insensitive by default.
- Copies matching pages + optional context pages into a new PDF.
- Exports text with three formatting options:
  - **Raw**: Plain text with headers `--- filename.pdf page N ---`
  - **Fence only**: Text wrapped in triple backticks
  - **Fence + prompt**: Wrapped text followed by a selected prompt

## 📁 Output files

| File | Content |
|------|---------|
| `extracted_results.pdf` | Exact pages (original layout) – pages from EPUBs are rendered as PDF pages |
| `extracted_results.txt` | Plain text (optionally fenced + prompted) |

## 🎨 Output formatting

When `ADD_PROMPT = True` in config, the program offers:

```
0. No fence, no prompt (raw text)
1. Add backticks fence only
2. Add backticks fence + select a predefined prompt
3. Add backticks fence + write a custom prompt
```

**Example with fence + prompt:**
````
```
--- book.epub page 12 ---
Content here...
```
Explain and Summarize the above contents
````

## ⚙️ Configuration

Edit the config section at the top of `main.py`:

| Variable | Description |
|----------|-------------|
| `OUTPUT_FILENAME` | Output PDF name (default: `extracted_results.pdf`) |
| `ADDITIONAL_PAGES` | Context pages after each match (works for all document types) |
| `ADD_PROMPT` | Enable/disable prompt selection |
| `PROMPT_LIST` | List of prompts to offer user |

## 📋 Supported Formats

All formats that PyMuPDF (MuPDF) can open:
- PDF (`.pdf`)
- EPUB (`.epub`)
- MOBI (`.mobi`)
- FB2 (`.fb2`)
- XPS (`.xps`)
- CBZ (`.cbz` – comic book archive)

## 📦 Dependencies

- Python 3.8+
- `PyMuPDF`
- `pandas`
- `traceback_logger` (custom – included)

## 📄 License

MIT
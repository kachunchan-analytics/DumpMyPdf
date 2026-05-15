# 📄 PDF Keyword Search

Search all PDFs in a directory by keyword. Extract matching pages into a new PDF + text file.

## 📦 Install

```bash
uv sync
```

## 🚀 Usage

1. Place script in a folder with PDFs.
2. Run: `uv run main.py`
3. Enter keyword.
4. Get `extracted_results.pdf` + `extracted_results.txt`.

## ⚙️ How it works

- Indexes all PDF pages (once) using PyMuPDF + pandas.
- Searches case‑insensitive (or sensitive).
- Copies matching pages into a new PDF.
- Exports text with headers: `--- filename.pdf page N ---`.

## 📁 Output files

| File | Content |
|------|---------|
| `extracted_results.pdf` | Exact pages (original layout) |
| `extracted_results.txt` | Plain text of those pages |

## 📋 Dependencies

- Python 3.8+
- `PyMuPDF`
- `pandas`
- `traceback_logger` (custom – included in project)

## 🛠️ Customize

- `OUTPUT_FILENAME` – change output name.
- `case_sensitive` – set `True` in `search()` call.

## 📄 License

MIT
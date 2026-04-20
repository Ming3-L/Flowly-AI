---
name: pdf-processing
description: Extract text and tables from PDF files, fill forms, merge documents, and convert between formats. Use when working with PDF files or when the user mentions PDFs, forms, document extraction, PDF conversion, or merging/splitting PDFs.
---

# PDF Processing

Extract, create, modify, and convert PDF documents using Python.

## Text Extraction

```python
import pdfplumber

with pdfplumber.open("file.pdf") as pdf:
    for page in pdf.pages:
        text = page.extract_text()
        print(text)
```

## Table Extraction

```python
import pdfplumber

with pdfplumber.open("file.pdf") as pdf:
    for page in pdf.pages:
        tables = page.extract_tables()
        for table in tables:
            for row in table:
                print(row)
```

## Form Filling (Interactive Forms)

```python
import pypdf

reader = pypdf.PdfReader("form.pdf")
writer = pypdf.PdfWriter()

for page in reader.pages:
    writer.add_page(page)

writer.update_page_form_field_values(
    writer.pages[0],
    {"field_name": "field_value"}
)

with open("filled.pdf", "wb") as f:
    writer.write(f)
```

## Merge PDFs

```python
from pypdf import PdfWriter

merger = PdfWriter()
for pdf in ["file1.pdf", "file2.pdf"]:
    merger.append(pdf)

merger.write("merged.pdf")
merger.close()
```

## Split PDF

```python
from pypdf import PdfReader, PdfWriter

reader = PdfReader("large.pdf")
for i, page in enumerate(reader.pages):
    writer = PdfWriter()
    writer.add_page(page)
    with open(f"page_{i+1}.pdf", "wb") as f:
        writer.write(f)
```

## OCR for Scanned PDFs

```python
from pdf2image import convert_from_path
import pytesseract

images = convert_from_path("scanned.pdf")
for i, image in enumerate(images):
    text = pytesseract.image_to_string(image, lang='eng+chi')
    print(text)
```

## PDF to Images

```python
from pdf2image import convert_from_path

images = convert_from_path("file.pdf", dpi=300)
for i, image in enumerate(images):
    image.save(f"page_{i+1}.png", "PNG")
```

## Image to PDF

```python
from PIL import Image

images = [Image.open(f"page_{i}.png") for i in range(1, 10)]
images[0].save("output.pdf", save_all=True, append_images=images[1:])
```

## Install Dependencies

```bash
pip install pdfplumber pypdf pdf2image pytesseract pillow
```

## Common Patterns

| Task | Library | Key Method |
|------|---------|------------|
| Text extraction | pdfplumber | `page.extract_text()` |
| Table extraction | pdfplumber | `page.extract_tables()` |
| Form filling | pypdf | `update_page_form_field_values()` |
| Merge/Split | pypdf | `PdfWriter` |
| OCR | pdf2image + pytesseract | `convert_from_path()` |

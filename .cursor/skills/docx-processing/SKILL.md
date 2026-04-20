---
name: docx-processing
description: Create, read, modify, and convert Microsoft Word DOCX documents. Use when working with Word documents - creating reports, filling templates, extracting content, converting formats, or automating DOCX operations.
---

# DOCX Processing

Create, read, modify, and convert Microsoft Word documents.

## Installation

```bash
pip install python-docx
```

## Create New Document

```python
from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH

doc = Document()

# Add title
doc.add_heading('Document Title', 0)

# Add paragraph
doc.add_paragraph('This is a paragraph.')

# Add heading
doc.add_heading('Section 1', 1)

# Add page break
doc.add_page_break()

# Save
doc.save('output.docx')
```

## Text Formatting

```python
from docx.shared import Bold, Italic

paragraph = doc.add_paragraph()
run = paragraph.add_run('Bold text')
run.bold = True

run2 = paragraph.add_run(' and italic text')
run2.italic = True

# Font styling
run.font.size = Pt(14)
run.font.color.rgb = RGBColor(0, 0, 255)
```

## Lists

```python
# Bullet list
doc.add_paragraph('Item 1', style='List Bullet')
doc.add_paragraph('Item 2', style='List Bullet')

# Numbered list
doc.add_paragraph('Step 1', style='List Number')
doc.add_paragraph('Step 2', style='List Number')
```

## Tables

```python
table = doc.add_table(rows=3, cols=3)

# Header row
header = table.rows[0].cells
header[0].text = 'Name'
header[1].text = 'Age'
header[2].text = 'City'

# Data rows
row1 = table.rows[1].cells
row1[0].text = 'Alice'
row1[1].text = '30'
row1[2].text = 'NYC'

# Style table
table.style = 'Light Grid Accent 1'
```

## Images

```python
doc.add_picture('image.png', width=Inches(5))
last_paragraph = doc.paragraphs[-1]
last_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
```

## Read Existing Document

```python
doc = Document('input.docx')

# Read all paragraphs
for para in doc.paragraphs:
    print(para.text)

# Read tables
for table in doc.tables:
    for row in table.rows:
        for cell in row.cells:
            print(cell.text)

# Extract specific content
for para in doc.paragraphs:
    if 'keyword' in para.text.lower():
        print(para.text)
```

## Modify Document

```python
doc = Document('template.docx')

# Replace text
for para in doc.paragraphs:
    if '{{name}}' in para.text:
        para.text = para.text.replace('{{name}}', 'John Doe')

# Add content
doc.add_page_break()
doc.add_heading('Additional Section', 2)

# Delete paragraph
para = doc.paragraphs[3]
para._element.getparent().remove(para._element)
```

## Document Properties

```python
from docx.shared import Inches

# Set margins
sections = doc.sections
for section in sections:
    section.top_margin = Inches(1)
    section.bottom_margin = Inches(1)
    section.left_margin = Inches(1.5)
    section.right_margin = Inches(1.5)

# Page orientation
section.orientation = 1  # Landscape
```

## Templates

```python
# template.docx contains {{title}}, {{author}}, {{date}}
doc = Document('template.docx')

replacements = {
    '{{title}}': 'My Report',
    '{{author}}': 'John Doe',
    '{{date}}': '2026-04-15'
}

def replace_text(doc, replacements):
    for para in doc.paragraphs:
        for old_text, new_text in replacements.items():
            if old_text in para.text:
                para.text = para.text.replace(old_text, new_text)

replace_text(doc, replacements)
doc.save('filled.docx')
```

## Convert to Other Formats

### DOCX to PDF (requires LibreOffice)

```bash
# Command line
soffice --headless --convert-to pdf document.docx

# Or use python
import subprocess
subprocess.run([
    'soffice', '--headless', '--convert-to', 'pdf',
    'document.docx'
])
```

### DOCX to HTML

```python
# Using mammoth
import mammoth

with open("document.docx", "rb") as docx_file:
    result = mammoth.convert_to_html(docx_file)
    html = result.value
    messages = result.messages  # warnings

with open("output.html", "w") as f:
    f.write(html)
```

## Advanced: Custom Styles

```python
from docx.shared import Pt
from docx.enum.style import WD_STYLE_TYPE

style = doc.styles['Heading 1']
style.font.size = Pt(16)
style.font.bold = True
style.font.color.rgb = RGBColor(0, 51, 102)
```

## Common Patterns

| Task | Code |
|------|------|
| Create document | `Document()` |
| Add heading | `add_heading(text, level)` |
| Add paragraph | `add_paragraph(text)` |
| Read paragraphs | `doc.paragraphs` |
| Read tables | `doc.tables` |
| Replace text | `para.text = para.text.replace()` |
| Save | `doc.save(path)` |

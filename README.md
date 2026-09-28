# Resume Builder (Local)

A small, local GUI for editing the content of the supplied modified Jake-style LaTeX resume and generating a PDF.

## What it does

- Opens a browser-based editor on `127.0.0.1`.
- Keeps the supplied resume layout/style in `template.tex`.
- Lets you edit personal information, summary, skills, experience, bullets, and education.
- Lets you drag and drop the resume sections to control their order in the generated PDF.
- Saves your content to `data/resume.json`.
- Generates `output/resume.tex` and `output/resume.pdf` using `pdflatex`.
- Lets you export both the `.tex` and `.pdf` files.
- Uses only Python's standard library; no Flask/React/npm setup is required.

## Requirements

1. Python 3.10+ (Python 3.13 is fine).
2. A LaTeX installation with `pdflatex` and the packages used by the supplied template.

The application checks for `pdflatex` when it starts. On a TeX Live system, the packages used by the supplied template need to be installed. The included template compiled successfully in the build environment used to create this project.

## Run

### Linux / macOS

```bash
python3 app.py
```

A browser window should open automatically. If it doesn't, visit:

`http://127.0.0.1:8765/`

### Windows

```powershell
py app.py
```

Then visit:

`http://127.0.0.1:8765/`

## Files

- `app.py` — local web server, persistence, LaTeX rendering, PDF compilation.
- `template.tex` — the supplied Jake-style LaTeX layout with a generated-content marker.
- `data/resume.json` — editable resume data.
- `output/resume.tex` — generated LaTeX.
- `output/resume.pdf` — generated PDF.
- `static/` — GUI files.

## Important

Edit content through the GUI. `template.tex` is the layout layer. Changes to fonts, margins, section formatting, or LaTeX commands can be made there if you want to customize the visual design later.

To stop the app, press `Ctrl+C` in the terminal running `app.py`.

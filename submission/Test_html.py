"""Test_html.py

Extract output from cell 35 of a Jupyter notebook and generate a standalone HTML file.

Usage examples:
  # Create HTML from cell 35 (default)
  python Test_html.py

  # Specify notebook and output HTML file
  python Test_html.py --notebook "BAX 372T Final Project.ipynb" --out output.html --title "Notebook Results"

Notes:
- By default looks for `BAX 372T Final Project.ipynb` in the current directory.
- Generates a self-contained HTML file with embedded CSS styling.
- Output is formatted for easy reading with syntax highlighting for code blocks.
"""

from __future__ import annotations
import argparse
import json
import logging
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

try:
    import nbformat
except Exception:
    nbformat = None

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

DEFAULT_NOTEBOOK = "BAX 372T Final Project.ipynb"
DEFAULT_OUT = "cell_35_output.html"
DEFAULT_CELL = 35


def load_notebook(path: str) -> Dict[str, Any]:
    """Load notebook from file (either via nbformat or raw JSON)."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Notebook not found: {path}")

    if nbformat:
        try:
            nb = nbformat.read(str(p), as_version=4)
            return nb
        except Exception:
            pass

    # fallback: raw JSON
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)


def extract_cell_output(nb: Dict[str, Any], cell_index: int) -> str:
    """Extract output text from a specific cell (1-based indexing)."""
    cells = nb.get("cells", [])
    
    if cell_index < 1 or cell_index > len(cells):
        raise IndexError(f"Cell index {cell_index} out of range (notebook has {len(cells)} cells)")

    # Convert to 0-based
    cell = cells[cell_index - 1]
    ctype = cell.get("cell_type", "")
    outputs_text: List[str] = []

    # For markdown cells, include the content
    if ctype == "markdown":
        source = "".join(cell.get("source", [])) if isinstance(cell.get("source"), list) else cell.get("source", "")
        if source:
            outputs_text.append(source)

    # For code cells, extract outputs
    if ctype == "code":
        outs = cell.get("outputs", [])
        for out in outs:
            otype = out.get("output_type", "")
            if otype == "stream":
                text = out.get("text", "")
                if text:
                    if isinstance(text, list):
                        text = "".join(text)
                    outputs_text.append(text)
            elif otype in ("execute_result", "display_data"):
                data = out.get("data", {})
                txt = None
                if isinstance(data, dict):
                    if "text/plain" in data:
                        txt = data["text/plain"]
                    elif "text" in data:
                        txt = data.get("text")
                if not txt:
                    txt = out.get("text", "") or out.get("ename", "")
                if isinstance(txt, list):
                    txt = "".join(txt)
                if txt:
                    outputs_text.append(txt)
            elif otype == "error":
                tb = out.get("traceback", [])
                if isinstance(tb, list):
                    outputs_text.append("\n".join(tb))
                elif tb:
                    outputs_text.append(str(tb))
            else:
                # generic fallback
                t = out.get("text") or out.get("data") or str(out)
                if isinstance(t, dict):
                    t = t.get("text/plain", str(t))
                if t:
                    outputs_text.append(str(t))

    joined = "\n\n".join([str(s).strip() for s in outputs_text if s is not None and str(s).strip()])
    return joined


def escape_html(text: str) -> str:
    """Escape HTML special characters."""
    return (text
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def format_output_as_html(text: str) -> str:
    """Format output text into HTML blocks with basic styling."""
    # Escape HTML
    text = escape_html(text)
    
    # Convert newlines to <br/>
    text = text.replace("\n", "<br/>\n")
    
    # Simple code block detection: lines starting with >>> or indented blocks
    lines = text.split("<br/>\n")
    formatted_lines = []
    in_code_block = False
    code_lines = []
    
    for line in lines:
        # Check if it looks like code
        if line.strip().startswith(">>>") or line.strip().startswith("[") or (line.startswith("&nbsp;") or (len(line) > 0 and line[0] == " ")):
            if not in_code_block:
                in_code_block = True
            code_lines.append(line)
        else:
            # Output accumulated code block
            if in_code_block and code_lines:
                code_block = "<br/>\n".join(code_lines)
                formatted_lines.append(f"<pre><code>{code_block}</code></pre>")
                code_lines = []
                in_code_block = False
            # Regular text line
            if line.strip():
                formatted_lines.append(f"<p>{line}</p>")
    
    # Finish any pending code block
    if code_lines:
        code_block = "<br/>\n".join(code_lines)
        formatted_lines.append(f"<pre><code>{code_block}</code></pre>")
    
    return "\n".join(formatted_lines)


def create_html_document(cell_index: int, cell_output: str, title: str = None, notebook_path: str = None) -> str:
    """Create a complete, self-contained HTML document."""
    if title is None:
        title = f"Notebook Cell #{cell_index} Output"
    
    timestamp = datetime.utcnow().isoformat() + "Z"
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{escape_html(title)}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            background-color: #f5f5f5;
            padding: 20px;
        }}
        
        .container {{
            max-width: 900px;
            margin: 0 auto;
            background-color: white;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
            padding: 40px;
        }}
        
        header {{
            border-bottom: 2px solid #007bff;
            margin-bottom: 30px;
            padding-bottom: 20px;
        }}
        
        h1 {{
            color: #007bff;
            font-size: 2em;
            margin-bottom: 10px;
        }}
        
        .meta {{
            font-size: 0.9em;
            color: #666;
        }}
        
        .meta-item {{
            display: inline-block;
            margin-right: 20px;
        }}
        
        .content {{
            font-size: 1em;
            line-height: 1.8;
        }}
        
        p {{
            margin-bottom: 15px;
            text-align: justify;
        }}
        
        pre {{
            background-color: #f8f9fa;
            border-left: 4px solid #007bff;
            padding: 15px;
            border-radius: 4px;
            overflow-x: auto;
            margin-bottom: 20px;
        }}
        
        code {{
            font-family: "Courier New", Courier, monospace;
            font-size: 0.95em;
            color: #d63384;
        }}
        
        pre code {{
            color: #333;
        }}
        
        footer {{
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
            font-size: 0.85em;
            color: #999;
            text-align: center;
        }}
        
        .section {{
            margin-bottom: 30px;
        }}
        
        .section-title {{
            font-size: 1.3em;
            font-weight: bold;
            color: #007bff;
            margin-bottom: 15px;
            border-bottom: 1px solid #e9ecef;
            padding-bottom: 10px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>{escape_html(title)}</h1>
            <div class="meta">
                <span class="meta-item"><strong>Cell:</strong> #{cell_index}</span>
                <span class="meta-item"><strong>Generated:</strong> {timestamp}</span>
                {f'<span class="meta-item"><strong>Notebook:</strong> {escape_html(Path(notebook_path).name)}</span>' if notebook_path else ''}
            </div>
        </header>
        
        <main class="content">
            <div class="section">
                <div class="section-title">Output</div>
                {format_output_as_html(cell_output)}
            </div>
        </main>
        
        <footer>
            <p>Generated from Jupyter notebook cell output. Document created on {timestamp}</p>
        </footer>
    </div>
</body>
</html>
"""
    return html


def write_html_file(path: str, html_content: str) -> Path:
    """Write HTML content to file."""
    p = Path(path)
    with p.open("w", encoding="utf-8") as f:
        f.write(html_content)
    logger.info(f"Wrote HTML to {p.resolve()}")
    return p


def parse_args(argv: List[str] | None = None):
    parser = argparse.ArgumentParser(description="Extract notebook cell output and generate HTML")
    parser.add_argument("--notebook", "-n", default=DEFAULT_NOTEBOOK, help="Path to the notebook (.ipynb)")
    parser.add_argument("--cell", "-c", type=int, default=DEFAULT_CELL, help="Cell index to extract (1-based)")
    parser.add_argument("--out", "-o", default=DEFAULT_OUT, help="Output HTML file path")
    parser.add_argument("--title", "-t", help="HTML page title (default: generated from cell info)")
    return parser.parse_args(argv)


def main(argv: List[str] | None = None):
    args = parse_args(argv)
    nb_path = args.notebook
    cell_idx = args.cell

    if not Path(nb_path).exists():
        logger.error(f"Notebook not found: {nb_path}")
        sys.exit(2)

    try:
        nb = load_notebook(nb_path)
        output = extract_cell_output(nb, cell_idx)
        
        if not output:
            logger.warning(f"No output found in cell #{cell_idx}")
        
        title = args.title or f"Notebook Output: Cell #{cell_idx}"
        html_content = create_html_document(cell_idx, output, title=title, notebook_path=nb_path)
        html_path = write_html_file(args.out, html_content)
        
        print(f"HTML file created: {html_path.resolve()}")
        
    except IndexError as e:
        logger.error(str(e))
        sys.exit(3)
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

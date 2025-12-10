"""Test_Emailer.py

Create an email draft from a Jupyter notebook's outputs.

Usage examples:
  # Create a draft file from the default notebook
  python Test_Emailer.py

  # Specify notebook and output file
  python Test_Emailer.py --notebook "BAX 372T Final Project.ipynb" --out draft.txt --to "recipient@example.com" --subject "Notebook results"

  # Send email via SMTP (use only with trusted credentials)
  python Test_Emailer.py --send --smtp-server smtp.example.com --smtp-port 587 --smtp-user you@example.com --smtp-pass SECRET

Notes:
- By default the script looks for `BAX 372T Final Project.ipynb` in the current directory.
- If SMTP details are provided with --send, the script will attempt to send the draft; otherwise it just writes `email_draft.txt`.
"""

from __future__ import annotations
import argparse
import json
import logging
import os
import re
import sys
from datetime import datetime
from email.message import EmailMessage
import smtplib
from pathlib import Path
from typing import List, Dict, Any

try:
    import nbformat
except Exception:
    nbformat = None

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

DEFAULT_NOTEBOOK = "BAX 372T Final Project.ipynb"
DEFAULT_OUT = "email_draft.txt"


def load_notebook(path: str) -> Dict[str, Any]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Notebook not found: {path}")

    if nbformat:
        try:
            nb = nbformat.read(str(p), as_version=4)
            return nb
        except Exception:
            # fall through to json loader
            pass

    # fallback: raw JSON
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)


def extract_outputs_from_notebook(nb: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Return list of dicts: each dict contains cell_type, source, outputs_text (joined)."""
    results: List[Dict[str, Any]] = []
    cells = nb.get("cells", [])

    for i, cell in enumerate(cells, start=1):
        ctype = cell.get("cell_type", "")
        source = "".join(cell.get("source", [])) if isinstance(cell.get("source"), list) else cell.get("source", "")
        outputs_text: List[str] = []

        # For markdown, include the markdown text as context
        if ctype == "markdown":
            outputs_text.append("[MARKDOWN]\n" + source)

        # For code cells, parse outputs
        if ctype == "code":
            # Notebook formats keep outputs in `outputs` list
            outs = cell.get("outputs", [])
            for out in outs:
                otype = out.get("output_type", "")
                if otype == "stream":
                    # stream outputs (stdout/stderr)
                    text = out.get("text", "")
                    outputs_text.append(text)
                elif otype in ("execute_result", "display_data"):
                    data = out.get("data", {})
                    # prefer text/plain
                    txt = None
                    if isinstance(data, dict):
                        if "text/plain" in data:
                            txt = data["text/plain"]
                        elif "text" in data:
                            txt = data.get("text")
                    if not txt:
                        # sometimes the output is directly in 'text'
                        txt = out.get("text", "") or out.get("ename", "")
                    if isinstance(txt, list):
                        txt = "".join(txt)
                    if txt:
                        outputs_text.append(txt)
                elif otype == "error":
                    # traceback
                    tb = out.get("traceback") or out.get("traceback", [])
                    if isinstance(tb, list):
                        outputs_text.append("\n".join(tb))
                    elif tb:
                        outputs_text.append(str(tb))
                else:
                    # generic fallback
                    t = out.get("text") or out.get("data") or str(out)
                    if isinstance(t, dict):
                        # try text/plain inside
                        t = t.get("text/plain", str(t))
                    outputs_text.append(str(t))

        # join and clean
        joined = "\n\n".join([str(s).strip() for s in outputs_text if s is not None and str(s).strip()])
        # sanitize HTML if present
        joined = strip_html(joined)

        if joined:
            results.append({"cell_index": i, "cell_type": ctype, "source": source, "output": joined})

    return results


def strip_html(text: str) -> str:
    # naive HTML tag stripper for safety; keep plain text
    if not text:
        return text
    # remove common HTML tags
    text = re.sub(r"<script[\s\S]*?</script>", "", text, flags=re.I)
    text = re.sub(r"<style[\s\S]*?</style>", "", text, flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    return text


def create_email_body(nb_path: str, outputs: List[Dict[str, Any]], include_source: bool = False, max_chars_per_output: int = 8000) -> str:
    header = []
    header.append(f"Notebook: {nb_path}")
    header.append(f"Created: {datetime.utcnow().isoformat()}Z")
    header.append("")
    header.append("This draft contains extracted outputs from the notebook. Below are the most relevant output sections.")
    header.append("")

    body_lines: List[str] = ["\n".join(header), "\n---\n"]

    for item in outputs:
        idx = item.get("cell_index")
        ctype = item.get("cell_type")
        src = item.get("source", "")
        out = item.get("output", "")
        if not out:
            continue
        if max_chars_per_output and len(out) > max_chars_per_output:
            out = out[:max_chars_per_output] + "\n\n...[truncated]..."

        section = [f"Cell #{idx} ({ctype}):\n"]
        if include_source and src:
            section.append("Source:\n")
            section.append(src)
            section.append("\n")
        section.append("Output:\n")
        section.append(out)
        section.append("\n" + ("-" * 60) + "\n")
        body_lines.append("\n".join(section))

    return "\n".join(body_lines)


def write_draft_file(path: str, subject: str, to: str, body: str) -> Path:
    p = Path(path)
    with p.open("w", encoding="utf-8") as f:
        f.write(f"To: {to}\n")
        f.write(f"Subject: {subject}\n")
        f.write("\n")
        f.write(body)
    logger.info(f"Wrote draft to {p.resolve()}")
    return p


def send_email_via_smtp(smtp_server: str, smtp_port: int, smtp_user: str, smtp_pass: str, to: str, subject: str, body: str, use_tls: bool = True) -> None:
    msg = EmailMessage()
    msg.set_content(body)
    msg["Subject"] = subject
    msg["From"] = smtp_user
    msg["To"] = to

    logger.info(f"Connecting to SMTP server {smtp_server}:{smtp_port} (TLS={use_tls})")
    with smtplib.SMTP(smtp_server, smtp_port, timeout=30) as server:
        if use_tls:
            server.starttls()
        server.login(smtp_user, smtp_pass)
        server.send_message(msg)
    logger.info("Email sent successfully")


def parse_args(argv: List[str] | None = None):
    parser = argparse.ArgumentParser(description="Create an email draft from a Jupyter notebook's outputs")
    parser.add_argument("--notebook", "-n", default=DEFAULT_NOTEBOOK, help="Path to the notebook (.ipynb)")
    parser.add_argument("--out", "-o", default=DEFAULT_OUT, help="Draft output file (text)")
    parser.add_argument("--to", default="recipient@example.com", help="Recipient email address")
    parser.add_argument("--subject", default=None, help="Email subject (default: generated)")
    parser.add_argument("--include-source", action="store_true", help="Include code/markdown source before outputs")
    parser.add_argument("--cell", type=int, help="Only include outputs from this notebook cell index (1-based)")
    parser.add_argument("--send", action="store_true", help="Send email via SMTP (requires SMTP args)")
    parser.add_argument("--smtp-server", help="SMTP server host")
    parser.add_argument("--smtp-port", type=int, default=587, help="SMTP server port")
    parser.add_argument("--smtp-user", help="SMTP username / from address")
    parser.add_argument("--smtp-pass", help="SMTP password")
    parser.add_argument("--max-per-output", type=int, default=8000, help="Max chars per output block (0 = no limit)")
    return parser.parse_args(argv)


def main(argv: List[str] | None = None):
    args = parse_args(argv)
    nb_path = args.notebook

    if not Path(nb_path).exists():
        logger.error(f"Notebook not found: {nb_path}")
        sys.exit(2)

    nb = load_notebook(nb_path)
    outputs = extract_outputs_from_notebook(nb)
    if not outputs:
        logger.warning("No outputs found in the notebook to include in the email draft.")

    # If user requested a single cell, filter outputs accordingly
    if getattr(args, "cell", None) is not None:
        target = int(args.cell)
        logger.info(f"Filtering outputs to only include cell #{target}")
        outputs = [o for o in outputs if int(o.get("cell_index", -1)) == target]
        if not outputs:
            logger.warning(f"No outputs found for cell #{target}")

    subject = args.subject or f"Notebook results: {Path(nb_path).stem}"
    body = create_email_body(nb_path, outputs, include_source=args.include_source, max_chars_per_output=(args.max_per_output or 0))

    draft_path = write_draft_file(args.out, subject, args.to, body)

    if args.send:
        # require SMTP args
        missing = [k for k in ("smtp_server", "smtp_user", "smtp_pass") if not getattr(args, k.replace("smtp_", "smtp_"))]
        if not args.smtp_server or not args.smtp_user or not args.smtp_pass:
            logger.error("--send requires --smtp-server, --smtp-user and --smtp-pass")
            sys.exit(3)
        send_email_via_smtp(args.smtp_server, args.smtp_port, args.smtp_user, args.smtp_pass, args.to, subject, body)

    print(f"Draft saved to: {draft_path.resolve()}")


if __name__ == "__main__":
    main()

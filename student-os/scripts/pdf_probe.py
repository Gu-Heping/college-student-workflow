#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

def load_pdf_reader():
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise SystemExit(
            "Missing dependency 'pypdf'. Install the packages from requirements.txt before running this script."
        ) from exc
    return PdfReader


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe a PDF for page count and lightweight metadata.")
    parser.add_argument("pdf", help="Path to the PDF file")
    args = parser.parse_args()

    pdf_path = Path(args.pdf).resolve()
    PdfReader = load_pdf_reader()
    reader = PdfReader(str(pdf_path))
    payload = {
        "source_file": str(pdf_path),
        "page_count": len(reader.pages),
        "metadata": {str(k): str(v) for k, v in (reader.metadata or {}).items()},
        "file_size_bytes": pdf_path.stat().st_size,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

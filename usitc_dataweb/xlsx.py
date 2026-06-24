from __future__ import annotations

import re
import zipfile
from pathlib import Path


ROW_RE = re.compile(rb"<row\b")


def count_xlsx_rows(path: Path) -> int | None:
    try:
        with zipfile.ZipFile(path) as zf:
            sheet_names = [name for name in zf.namelist() if name.startswith("xl/worksheets/sheet")]
            if not sheet_names:
                return None
            total = 0
            for sheet_name in sheet_names:
                with zf.open(sheet_name) as sheet:
                    for chunk in iter(lambda: sheet.read(1024 * 1024), b""):
                        total += len(ROW_RE.findall(chunk))
            return total
    except (OSError, zipfile.BadZipFile):
        return None

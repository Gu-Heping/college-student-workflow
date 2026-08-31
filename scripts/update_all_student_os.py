#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path


IMPL_DIR = Path(__file__).resolve().parent.parent / "student-os" / "scripts"
if str(IMPL_DIR) not in sys.path:
    sys.path.insert(0, str(IMPL_DIR))

from update_all_student_os import *  # noqa: F401,F403,E402


if __name__ == "__main__":
    raise SystemExit(main())

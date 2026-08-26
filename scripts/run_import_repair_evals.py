#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STUDENT_OS_SCRIPTS = ROOT / "student-os" / "scripts"


def run_student_script(name: str, *args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-B", str(STUDENT_OS_SCRIPTS / name), *args],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=cwd,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONIOENCODING": "utf-8"},
    )


def run_json(name: str, *args: str, cwd: Path, expect_ok: bool = True) -> dict[str, object]:
    result = run_student_script(name, *args, cwd=cwd)
    if expect_ok and result.returncode != 0:
        raise AssertionError(f"{name} failed unexpectedly:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}")
    if not expect_ok and result.returncode == 0:
        raise AssertionError(f"{name} should have failed for args {args!r}")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise AssertionError(f"{name} did not print JSON:\n{result.stdout}\n{result.stderr}") from exc


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def build_fixture(vault: Path) -> dict[str, Path]:
    imports = vault / "courses" / "linear-algebra" / "reviews" / "期末"
    source_pdf = imports / "试卷" / "2016-answer.pdf"
    source_pdf.parent.mkdir(parents=True, exist_ok=True)
    source_pdf.write_bytes(b"%PDF-1.4\n% eval placeholder\n")

    semantic = imports / "2016-answer.pdf.md"
    write_text(
        semantic,
        "---\n"
        "source_file: 试卷/2016-answer.pdf\n"
        "import_method: mineru-agent-v1\n"
        "repair_status: auto-repaired\n"
        "verify_status: unverified\n"
        "---\n"
        "\n"
        "五.（本题12分）设 A = alpha alpha^T。\n"
        "\n"
        "$$\n"
        "( 1 ) \\ Y Y \\ Y = 0 \\boxplus \\ Y\n"
        "$$\n"
        "\n"
        "$$\n"
        "\\neg \\neg ( A ) \\leq r ( \\alpha ) = 1\n"
        "$$\n",
    )

    answer = imports / "2014参考答案.pdf.md"
    write_text(
        answer,
        "---\n"
        "source_file: missing.pdf\n"
        "repair_status: auto-repaired\n"
        "verify_status: unverified\n"
        "---\n"
        "\n"
        "解：先证相似矩阵有相同特征值。\n",
    )

    verified = imports / "verified.pdf.md"
    write_text(
        verified,
        "---\n"
        "source_file: verified.pdf\n"
        "repair_status: auto-repaired\n"
        "verify_status: verified\n"
        "repair_risk: needs-human-review\n"
        "---\n"
        "\n"
        "Broken $x\n",
    )
    return {"semantic": semantic, "answer": answer, "verified": verified}


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="student-os-import-repair-eval-") as tmp:
        vault = Path(tmp) / "vault"
        paths = build_fixture(vault)
        queue = run_json("repair_import_queue.py", str(vault), "--write-queue", "--classify-evidence", "--json", cwd=ROOT)
        by_name = {Path(str(item["path"])).name: item for item in queue["items"]}  # type: ignore[index]
        if "verified.pdf.md" in by_name or queue["counts"]["skipped_verified"] != 1:  # type: ignore[index]
            raise AssertionError(f"Verified files should be skipped by default: {queue}")

        semantic_item = by_name["2016-answer.pdf.md"]
        if semantic_item["evidence"]["source_pdf"]["exists"] is not True:  # type: ignore[index]
            raise AssertionError(f"Semantic fixture should resolve source PDF evidence: {semantic_item}")
        if semantic_item["repair_class"] not in {"format-only", "semantic-text-repair"}:
            raise AssertionError(f"Unexpected semantic repair class: {semantic_item}")

        answer_item = by_name["2014参考答案.pdf.md"]
        if answer_item["repair_class"] != "answer-paper-crosscheck":
            raise AssertionError(f"Answer-only fixture should require crosscheck: {answer_item}")
        if answer_item["blocked"] not in {"unrecoverable-with-current-evidence", "requires-vision-evidence"}:
            raise AssertionError(f"Missing source answer fixture should be explicitly blocked: {answer_item}")

        proposal = vault / ".student-os" / "import-repair" / "proposals" / "bad.md"
        write_text(
            proposal,
            "# Bad proposal\n\n"
            f"<!-- student-os-target: {paths['semantic']} -->\n\n"
            "<!-- student-os-replacement-start -->\n"
            "---\nrepair_status: auto-repaired\nverify_status: verified\n---\n\n"
            "五. Broken $x\n"
            "<!-- student-os-replacement-end -->\n",
        )
        review = run_json("repair_import_review.py", "--proposal", str(proposal), "--json", cwd=vault, expect_ok=False)
        if review["review_pass"] is not False:
            raise AssertionError(f"Bad proposal should fail review: {review}")
        apply_result = run_json(
            "repair_import_apply.py",
            "--proposal",
            str(proposal),
            "--require-review-pass",
            "--json",
            cwd=vault,
            expect_ok=False,
        )
        if apply_result["stage"] != "review":
            raise AssertionError(f"Apply should stop at review for bad proposal: {apply_result}")

    print("OK import-repair-evals")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

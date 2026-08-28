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
sys.path.insert(0, str(STUDENT_OS_SCRIPTS))
from repair_import_queue import decode_yaml_path, file_sha256  # noqa: E402
from repair_import_case import case_sha256, object_sha256, render_pdf_pages  # noqa: E402


def run_student_script(name: str, *args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-B", str(STUDENT_OS_SCRIPTS / name), *args],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=cwd,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"},
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


def expect_failure(name: str, *args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    result = run_student_script(name, *args, cwd=cwd)
    if result.returncode == 0:
        raise AssertionError(f"{name} should have failed for args {args!r}")
    return result


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
    raw = imports / "2016-answer.pdf.raw.md"
    write_text(
        raw,
        "---\n"
        "source_file: 试卷/2016-answer.pdf\n"
        "repair_status: raw\n"
        "verify_status: unverified\n"
        "---\n"
        "\n"
        "Raw OCR evidence with \\boxplus noise.\n"
        "```python\nprint('embedded fence')\n```\n",
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

    proof_answer = imports / "2018证明答案.pdf.md"
    write_text(
        proof_answer,
        "---\n"
        "source_file: missing-proof.pdf\n"
        "repair_status: auto-repaired\n"
        "verify_status: unverified\n"
        "---\n"
        "\n"
        "证明：由条件可得结论成立。\n",
    )

    broad_answer = imports / "2019计算机答案.pdf.md"
    write_text(
        broad_answer,
        "---\n"
        "source_file: 计算机答案.pdf\n"
        "repair_status: auto-repaired\n"
        "verify_status: unverified\n"
        "---\n"
        "\n"
        "解：设 x=1，计算得到结果。\n",
    )

    vision = imports / "2015-proof.pdf.md"
    write_text(
        vision,
        "---\n"
        "source_file: 2015-proof.pdf\n"
        "import_method: mineru-agent-v1\n"
        "repair_status: auto-repaired\n"
        "verify_status: unverified\n"
        "---\n"
        "\n"
        "三. 根据图片重建下列证明。\n"
        "\n"
        "证明：� � � □，故结论成立。\n",
    )
    (imports / "2015-proof.pdf").write_bytes(b"%PDF-1.4\n% no real pages in eval placeholder\n")

    missing_pdf = imports / "2017-missing-source.pdf.md"
    write_text(
        missing_pdf,
        "---\n"
        "source_file: missing-2017.pdf\n"
        "import_method: mineru-agent-v1\n"
        "repair_status: auto-repaired\n"
        "verify_status: unverified\n"
        "---\n"
        "\n"
        "四. \\boxplus \\ Y Y \\ Y\n",
    )

    legacy = imports / "legacy.pdf.md"
    write_text(
        legacy,
        "---\n"
        "source_file: legacy.pdf\n"
        "repair_status: repaired\n"
        "verify_status: unverified\n"
        "repair_risk: needs-human-review\n"
        "---\n"
        "\n"
        "Readable body.\n",
    )

    long_body = imports / "long-body.pdf.md"
    write_text(
        long_body,
        "---\n"
        "source_file: long-body.pdf\n"
        "repair_status: auto-repaired\n"
        "verify_status: unverified\n"
        "repair_risk: needs-human-review\n"
        "---\n"
        "\n"
        + "Long imported paragraph without question markers. " * 30
        + "\n",
    )

    derived_note = imports / "derived-note.md"
    write_text(
        derived_note,
        "---\n"
        "source_file: derived.pdf\n"
        "derived_from_import: derived.raw.md\n"
        "repair_status: auto-repaired\n"
        "verify_status: unverified\n"
        "repair_risk: needs-human-review\n"
        "---\n"
        "\n"
        "Derived import sidecar with nonstandard filename.\n",
    )

    numbered_long = imports / "numbered-long.pdf.md"
    write_text(
        numbered_long,
        "---\n"
        "source_file: numbered-long.pdf\n"
        "repair_status: auto-repaired\n"
        "verify_status: unverified\n"
        "repair_risk: needs-human-review\n"
        "---\n"
        "\n"
        "1. " + ("Long imported numbered question with conditions and explanation. " * 20) + "\n"
        "2. " + ("Another long imported numbered question with answer context. " * 20) + "\n",
    )

    many_pages = imports / "many-pages.pdf.md"
    page_lines = [
        "---",
        "source_file: many-pages.pdf",
        "repair_status: auto-repaired",
        "verify_status: unverified",
        "---",
        "",
    ]
    for page_number in range(1, 9):
        page_lines.extend([f"## Page {page_number}", f"Routine content on page {page_number}.", ""])
    page_lines.append("Broken late-page math $x")
    write_text(many_pages, "\n".join(page_lines) + "\n")

    inline_space = imports / "inline-space.pdf.md"
    write_text(
        inline_space,
        "---\n"
        "source_file: inline-space.pdf\n"
        "repair_status: auto-repaired\n"
        "verify_status: unverified\n"
        "---\n"
        "\n"
        "一. 由(ii)得(I)的通解为 $ x = A^{-1}b $，且 $ y=C $。\n"
        "\n"
        "二. 不应被第一题的局部修复影响。\n",
    )

    low_cjk_source = imports / "low-cjk.pdf"
    low_cjk_source.write_bytes(b"%PDF-1.4\n% low cjk placeholder\n")
    low_cjk = imports / "low-cjk.pdf.md"
    write_text(
        low_cjk,
        "---\n"
        "source_file: low-cjk.pdf\n"
        "language: zh\n"
        "import_method: mineru-agent-v1\n"
        "repair_status: auto-repaired\n"
        "verify_status: unverified\n"
        "---\n"
        "\n"
        "## Page 1\n"
        "routine latin page title\n"
        "\n"
        "## Page 2\n"
        "another latin page title\n"
        "\n"
        "## Page 3\n"
        + "\n".join(["alpha beta gamma delta epsilon zeta eta theta"] * 60)
        + "\n",
    )

    long_verified = imports / "long-verified.pdf.md"
    write_text(
        long_verified,
        "---\n"
        + "\n".join(f"extra_{index}: value" for index in range(6000))
        + "\nrepair_status: auto-repaired\n"
        "verify_status: verified\n"
        "repair_risk: needs-human-review\n"
        "---\n"
        "\n"
        "Broken $x\n",
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
    return {
        "semantic": semantic,
        "raw": raw,
        "answer": answer,
        "proof_answer": proof_answer,
        "broad_answer": broad_answer,
        "vision": vision,
        "missing_pdf": missing_pdf,
        "legacy": legacy,
        "long_body": long_body,
        "derived_note": derived_note,
        "numbered_long": numbered_long,
        "many_pages": many_pages,
        "inline_space": inline_space,
        "low_cjk": low_cjk,
        "long_verified": long_verified,
        "verified": verified,
    }


def main() -> int:
    if decode_yaml_path(r"C:\new\file.pdf") != r"C:\new\file.pdf":
        raise AssertionError("Unquoted Windows paths must not be interpreted as escape sequences")
    if decode_yaml_path(r"references\\u671f末.pdf") != "references\\期末.pdf":
        raise AssertionError("Legacy unicode escapes should still decode in frontmatter paths")

    with tempfile.TemporaryDirectory(prefix="student-os-import-repair-eval-") as tmp:
        vault = Path(tmp) / "vault"
        paths = build_fixture(vault)
        imports = paths["semantic"].parent
        try:
            import fitz  # type: ignore[import-not-found]
        except ImportError:
            fitz = None
        if fitz is not None:
            one_page_pdf = Path(tmp) / "one-page.pdf"
            document = fitz.open()
            document.new_page()
            document.save(str(one_page_pdf))
            document.close()
            partial_render = render_pdf_pages(one_page_pdf, Path(tmp) / "partial-pages", [1, 2])
            if partial_render.get("ok") is not False or partial_render.get("reason") != "partial-page-render-failed":
                raise AssertionError(f"Partial vision rendering should be blocking: {partial_render}")
        outside_secret = Path(tmp) / "outside-secret.md"
        write_text(outside_secret, "---\nsecret: true\n---\n\nDo not embed me.\n")
        malicious_derived = imports / "malicious-derived.pdf.md"
        write_text(
            malicious_derived,
            "---\n"
            "source_file: malicious-derived.pdf\n"
            f"derived_from_import: {outside_secret}\n"
            "repair_status: auto-repaired\n"
            "verify_status: unverified\n"
            "repair_risk: needs-human-review\n"
            "---\n"
            "\n"
            "Sidecar with untrusted raw evidence pointer.\n",
        )
        paths["malicious_derived"] = malicious_derived
        missing_target = vault / "missing-vault"
        missing_target_result = run_json("repair_import_queue.py", str(missing_target), "--write-queue", "--json", cwd=ROOT, expect_ok=False)
        if missing_target_result.get("stage") != "resolve-target":
            raise AssertionError(f"Missing queue target should fail at resolve-target: {missing_target_result}")
        if missing_target.exists():
            raise AssertionError(f"Missing queue target must not be created: {missing_target}")

        queue = run_json("repair_import_queue.py", str(vault), "--write-queue", "--classify-evidence", "--json", cwd=ROOT)
        queue_path = vault / ".student-os" / "import-repair" / "queue.json"
        bad_queue = vault / ".student-os" / "import-repair" / "bad-queue.json"
        bad_queue_payload = dict(queue)
        bad_queue_payload["schema_version"] = "import-repair-queue/v0"
        write_text(bad_queue, json.dumps(bad_queue_payload, ensure_ascii=False, indent=2) + "\n")
        bad_queue_result = expect_failure(
            "repair_import_case.py",
            "--queue",
            str(bad_queue),
            "--queue-item",
            "anything",
            "--json",
            cwd=vault,
        )
        if "Unsupported queue schema_version" not in bad_queue_result.stderr:
            raise AssertionError(f"Unsupported queue schema should fail clearly: {bad_queue_result.stderr}")
        unsafe_queue = vault / ".student-os" / "import-repair" / "unsafe-queue.json"
        unsafe_queue_payload = dict(queue)
        unsafe_item = dict(queue["items"][0])  # type: ignore[index]
        unsafe_item["id"] = "../escape"
        unsafe_queue_payload["items"] = [unsafe_item]
        write_text(unsafe_queue, json.dumps(unsafe_queue_payload, ensure_ascii=False, indent=2) + "\n")
        unsafe_queue_result = expect_failure(
            "repair_import_case.py",
            "--queue",
            str(unsafe_queue),
            "--queue-item",
            "../escape",
            "--json",
            cwd=vault,
        )
        if "Unsafe queue item id" not in unsafe_queue_result.stderr:
            raise AssertionError(f"Unsafe queue item ids should fail clearly: {unsafe_queue_result.stderr}")
        copied_queue_root = Path(tmp) / "copied-vault"
        copied_queue = copied_queue_root / ".student-os" / "import-repair" / "queue.json"
        copied_queue_payload = dict(queue)
        copied_queue_payload["target_root"] = str(vault)
        write_text(copied_queue, json.dumps(copied_queue_payload, ensure_ascii=False, indent=2) + "\n")
        copied_queue_result = expect_failure(
            "repair_import_case.py",
            "--queue",
            str(copied_queue),
            "--queue-item",
            str(queue["items"][0]["id"]),  # type: ignore[index]
            "--json",
            cwd=copied_queue_root,
        )
        if "target_root does not match queue location" not in copied_queue_result.stderr:
            raise AssertionError(f"Copied queue roots should fail clearly: {copied_queue_result.stderr}")
        by_name = {Path(str(item["path"])).name: item for item in queue["items"]}  # type: ignore[index]
        if "verified.pdf.md" in by_name or "long-verified.pdf.md" in by_name or queue["counts"]["skipped_verified"] != 2:  # type: ignore[index]
            raise AssertionError(f"Verified files should be skipped by default: {queue}")
        if "2016-answer.pdf.raw.md" in by_name:
            raise AssertionError(f"Raw import evidence should not be queued as a repair target: {queue}")
        malicious_item = by_name["malicious-derived.pdf.md"]
        if malicious_item.get("raw_import") or malicious_item["evidence"]["raw_import"]["exists"] is not False:  # type: ignore[index]
            raise AssertionError(f"Vault-external derived_from_import should not be accepted as raw evidence: {malicious_item}")
        direct_derived_queue = run_json("repair_import_queue.py", str(paths["derived_note"]), "--json", cwd=ROOT)
        direct_names = {Path(str(item["path"])).name for item in direct_derived_queue["items"]}  # type: ignore[index]
        if "derived-note.md" not in direct_names:
            raise AssertionError(f"Direct file scan should include derived_from_import markdown: {direct_derived_queue}")
        direct_written = run_json("repair_import_queue.py", str(paths["derived_note"]), "--write-queue", "--json", cwd=ROOT)
        if Path(str(direct_written["queue_path"])).parent != vault / ".student-os" / "import-repair":
            raise AssertionError(f"Single-file queue inside a vault should write repair state at vault root: {direct_written}")
        queue = run_json("repair_import_queue.py", str(vault), "--write-queue", "--classify-evidence", "--json", cwd=ROOT)
        by_name = {Path(str(item["path"])).name: item for item in queue["items"]}  # type: ignore[index]
        derived_item = by_name["derived-note.md"]
        derived_case = run_json(
            "repair_import_case.py",
            "--queue",
            str(queue_path),
            "--queue-item",
            str(derived_item["id"]),
            "--evidence-mode",
            "text-only",
            "--json",
            cwd=vault,
        )
        derived_case_json = Path(str(derived_case["case_json"]))
        derived_case_state = json.loads(derived_case_json.read_text(encoding="utf-8"))

        semantic_item = by_name["2016-answer.pdf.md"]
        if semantic_item["evidence"]["source_pdf"]["exists"] is not True:  # type: ignore[index]
            raise AssertionError(f"Semantic fixture should resolve source PDF evidence: {semantic_item}")
        if semantic_item["repair_class"] not in {"format-only", "semantic-text-repair"}:
            raise AssertionError(f"Unexpected semantic repair class: {semantic_item}")
        semantic_case = run_json(
            "repair_import_case.py",
            "--queue",
            str(queue_path),
            "--queue-item",
            str(semantic_item["id"]),
            "--evidence-mode",
            "text-only",
            "--json",
            cwd=vault,
        )
        semantic_case_json = Path(str(semantic_case["case_json"]))
        semantic_case_state = json.loads(semantic_case_json.read_text(encoding="utf-8"))
        semantic_evidence_sha = semantic_case_state["evidence_sha256"]
        semantic_case_digest = semantic_case_state["case_sha256"]
        if "````markdown" not in str(semantic_case["markdown"]):
            raise AssertionError("Case markdown should use longer fences when evidence excerpts contain triple backticks")

        answer_item = by_name["2014参考答案.pdf.md"]
        if answer_item["repair_class"] != "answer-paper-crosscheck":
            raise AssertionError(f"Answer-only fixture should require crosscheck: {answer_item}")
        if answer_item["blocked"] not in {"unrecoverable-with-current-evidence", "requires-vision-evidence"}:
            raise AssertionError(f"Missing source answer fixture should be explicitly blocked: {answer_item}")
        proof_answer_item = by_name["2018证明答案.pdf.md"]
        if "answer-missing-question-stem" not in set(proof_answer_item["risk_codes"]):
            raise AssertionError(f"Proof-only answer sidecar should not treat its solution lead as a question stem: {proof_answer_item}")
        broad_answer_item = by_name["2019计算机答案.pdf.md"]
        if "answer-missing-question-stem" not in set(broad_answer_item["risk_codes"]):
            raise AssertionError(f"Frontmatter or solution words should not count as a question stem: {broad_answer_item}")

        vision_item = by_name["2015-proof.pdf.md"]
        if vision_item["recommended_evidence_mode"] != "vision-assisted":
            raise AssertionError(f"Image-grounded reconstruction fixture should require vision: {vision_item}")
        if vision_item["evidence"]["candidate_pages"]:  # type: ignore[index]
            raise AssertionError(f"Placeholder PDF should not produce fake candidate pages: {vision_item}")
        vision_case = run_json(
            "repair_import_case.py",
            "--queue",
            str(queue_path),
            "--queue-item",
            str(vision_item["id"]),
            "--evidence-mode",
            "vision-assisted",
            "--json",
            cwd=vault,
        )
        vision_result = vision_case["evidence"].get("vision", {})  # type: ignore[index]
        if vision_result.get("ok") is True:
            raise AssertionError(f"Vision case should not render arbitrary pages without page hints: {vision_case}")
        if vision_result.get("reason") not in {"page-hint-unavailable", "source-pdf-unavailable"}:
            raise AssertionError(f"Vision unavailable reason should be explicit: {vision_case}")

        missing_pdf_item = by_name["2017-missing-source.pdf.md"]
        if missing_pdf_item["blocked"] != "requires-vision-evidence":
            raise AssertionError(f"Missing PDF semantic fixture should be blocked on vision evidence: {missing_pdf_item}")
        many_pages_item = by_name["many-pages.pdf.md"]
        if many_pages_item["evidence"]["candidate_pages"] != [8]:  # type: ignore[index]
            raise AssertionError(f"Candidate pages should point to the risky snippet page only: {many_pages_item}")
        low_cjk_item = by_name["low-cjk.pdf.md"]
        if low_cjk_item["evidence"]["candidate_pages"] != [3]:  # type: ignore[index]
            raise AssertionError(f"Low-CJK risk should be localized to imported body pages: {low_cjk_item}")
        inline_item = by_name["inline-space.pdf.md"]
        if "inline-math-delimiter-space" not in set(inline_item["risk_codes"]):
            raise AssertionError(f"Inline math delimiter spaces should enter the queue: {inline_item}")
        inline_risk = next(risk for risk in inline_item["risks"] if risk["code"] == "inline-math-delimiter-space")
        if inline_risk.get("severity") != "error" or inline_risk.get("safe_fix_kind") != "trim-inline-math-delimiter-adjacent-space":
            raise AssertionError(f"Inline delimiter risk should be a high-confidence localized render fix: {inline_risk}")
        if inline_item.get("single_section_candidate") is not True or inline_item.get("repair_scope_required") != "single-section":
            raise AssertionError(f"Inline delimiter risk should be single-section repairable: {inline_item}")

        direct_case = run_json(
            "repair_import_case.py",
            "--queue-item",
            str(paths["semantic"]),
            "--evidence-mode",
            "text-only",
            "--json",
            cwd=ROOT,
        )
        direct_case_json = Path(str(direct_case["case_json"]))
        if not direct_case_json.is_relative_to(vault):
            raise AssertionError(f"Direct sidecar case should write state under the vault, not the repo cwd: {direct_case}")
        verified_direct = expect_failure("repair_import_case.py", "--queue-item", str(paths["verified"]), "--json", cwd=ROOT)
        if "--include-verified" not in verified_direct.stderr:
            raise AssertionError(f"Direct verified targets should require explicit opt-in: {verified_direct.stderr}")

        proposal = vault / ".student-os" / "import-repair" / "proposals" / "bad.md"
        write_text(
            proposal,
            "# Bad proposal\n\n"
            "<!-- student-os-proposal-schema: import-repair-proposal/v1 -->\n"
            f"<!-- student-os-target: {paths['semantic']} -->\n\n"
            f"<!-- student-os-target-sha256: {semantic_item['content_sha256']} -->\n"
            f"<!-- student-os-case-json: {semantic_case_json} -->\n"
            f"<!-- student-os-case-sha256: {semantic_case_digest} -->\n"
            f"<!-- student-os-evidence-sha256: {semantic_evidence_sha} -->\n"
            "<!-- student-os-evidence-mode: text-only -->\n"
            "<!-- student-os-model-capability: text-only -->\n"
            "<!-- student-os-changed-sections: line-1 -->\n"
            "<!-- student-os-remaining-risks: human-review-required -->\n\n"
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

        stale = vault / ".student-os" / "import-repair" / "proposals" / "stale.md"
        write_text(
            stale,
            "# Stale proposal\n\n"
            "<!-- student-os-proposal-schema: import-repair-proposal/v1 -->\n"
            f"<!-- student-os-target: {paths['semantic']} -->\n\n"
            "<!-- student-os-target-sha256: 0000000000000000000000000000000000000000000000000000000000000000 -->\n"
            f"<!-- student-os-case-json: {semantic_case_json} -->\n"
            f"<!-- student-os-case-sha256: {semantic_case_digest} -->\n"
            f"<!-- student-os-evidence-sha256: {semantic_evidence_sha} -->\n"
            "<!-- student-os-evidence-mode: text-only -->\n"
            "<!-- student-os-model-capability: text-only -->\n"
            "<!-- student-os-changed-sections: line-1 -->\n"
            "<!-- student-os-remaining-risks: human-review-required -->\n\n"
            "<!-- student-os-replacement-start -->\n"
            "---\nrepair_status: auto-repaired\nverify_status: unverified\n---\n\n"
            "五. Clean $x$.\n"
            "<!-- student-os-replacement-end -->\n",
        )
        stale_review = run_json("repair_import_review.py", "--proposal", str(stale), "--json", cwd=vault, expect_ok=False)
        if not any(issue["code"] == "proposal-target-stale" for issue in stale_review["issues"]):  # type: ignore[index]
            raise AssertionError(f"Stale proposal hash should fail review: {stale_review}")

        legacy_item = by_name["legacy.pdf.md"]
        legacy_case = run_json(
            "repair_import_case.py",
            "--queue",
            str(queue_path),
            "--queue-item",
            str(legacy_item["id"]),
            "--evidence-mode",
            "text-only",
            "--json",
            cwd=vault,
        )
        legacy_case_json = Path(str(legacy_case["case_json"]))
        legacy_case_state = json.loads(legacy_case_json.read_text(encoding="utf-8"))
        legacy_case_digest = legacy_case_state["case_sha256"]
        clean = vault / ".student-os" / "import-repair" / "proposals" / "clean.md"
        write_text(
            clean,
            "# Clean proposal\n\n"
            "<!-- student-os-proposal-schema: import-repair-proposal/v1 -->\n"
            f"<!-- student-os-target: {paths['legacy']} -->\n\n"
            f"<!-- student-os-target-sha256: {legacy_item['content_sha256']} -->\n"
            f"<!-- student-os-case-json: {legacy_case_json} -->\n"
            f"<!-- student-os-case-sha256: {legacy_case_digest} -->\n"
            f"<!-- student-os-evidence-sha256: {legacy_case_state['evidence_sha256']} -->\n"
            "<!-- student-os-evidence-mode: text-only -->\n"
            "<!-- student-os-model-capability: text-only -->\n"
            "<!-- student-os-changed-sections: line-1 -->\n"
            "<!-- student-os-remaining-risks: human-review-required -->\n\n"
            "<!-- student-os-replacement-start -->\n"
            "---\nsource_file: legacy.pdf\nrepair_status: auto-repaired\nverify_status: unverified\nverify_status: verified\n---\n\n"
            "Readable body.\n"
            "<!-- student-os-replacement-end -->\n",
        )
        mismatch_apply = run_json(
            "repair_import_apply.py",
            "--proposal",
            str(clean),
            "--evidence-mode",
            "vision-assisted",
            "--json",
            cwd=vault,
            expect_ok=False,
        )
        if mismatch_apply["stage"] != "evidence-mode":
            raise AssertionError(f"Explicit evidence-mode mismatch should fail apply: {mismatch_apply}")
        invalid_review = vault / ".student-os" / "import-repair" / "reviews" / "invalid-review.json"
        write_text(invalid_review, json.dumps([], ensure_ascii=False) + "\n")
        invalid_review_result = expect_failure(
            "repair_import_apply.py",
            "--proposal",
            str(clean),
            "--review",
            str(invalid_review),
            "--json",
            cwd=vault,
        )
        if "Review JSON must be an object" not in invalid_review_result.stderr:
            raise AssertionError(f"Non-object review JSON should fail clearly: {invalid_review_result.stderr}")
        applied = vault / ".student-os" / "import-repair" / "applied" / "legacy.pdf.md"
        clean_apply = run_json(
            "repair_import_apply.py",
            "--proposal",
            str(clean),
            "--output",
            str(applied),
            "--json",
            cwd=vault,
        )
        applied_text = applied.read_text(encoding="utf-8")
        if clean_apply["repair_evidence_mode"] != "text-only":
            raise AssertionError(f"Apply should derive evidence mode from proposal metadata: {clean_apply}")
        if applied_text.count("verify_status:") != 1 or "verify_status: verified" in applied_text:
            raise AssertionError(f"Apply should canonicalize duplicate verify_status fields:\n{applied_text}")

        changed_source = vault / ".student-os" / "import-repair" / "proposals" / "changed-source.md"
        write_text(
            changed_source,
            "# Changed source proposal\n\n"
            "<!-- student-os-proposal-schema: import-repair-proposal/v1 -->\n"
            f"<!-- student-os-target: {paths['legacy']} -->\n\n"
            f"<!-- student-os-target-sha256: {legacy_item['content_sha256']} -->\n"
            f"<!-- student-os-case-json: {legacy_case_json} -->\n"
            f"<!-- student-os-case-sha256: {legacy_case_digest} -->\n"
            f"<!-- student-os-evidence-sha256: {legacy_case_state['evidence_sha256']} -->\n"
            "<!-- student-os-evidence-mode: text-only -->\n"
            "<!-- student-os-model-capability: text-only -->\n"
            "<!-- student-os-changed-sections: line-1 -->\n"
            "<!-- student-os-remaining-risks: human-review-required -->\n\n"
            "<!-- student-os-replacement-start -->\n"
            "---\nsource_file: other.pdf\nrepair_status: auto-repaired\nverify_status: unverified\n---\n\n"
            "Readable body.\n"
            "<!-- student-os-replacement-end -->\n",
        )
        changed_source_review = run_json("repair_import_review.py", "--proposal", str(changed_source), "--json", cwd=vault, expect_ok=False)
        if not any(issue["code"] == "source-file-changed" for issue in changed_source_review["issues"]):  # type: ignore[index]
            raise AssertionError(f"Changed source_file should fail review: {changed_source_review}")

        outside_target = Path(tmp) / "outside.pdf.md"
        write_text(
            outside_target,
            "---\nsource_file: outside.pdf\nrepair_status: auto-repaired\nverify_status: unverified\nrepair_risk: needs-human-review\n---\n\n"
            "Outside content.\n",
        )
        outside_target_proposal = vault / ".student-os" / "import-repair" / "proposals" / "outside-target.md"
        write_text(
            outside_target_proposal,
            "# Outside target proposal\n\n"
            "<!-- student-os-proposal-schema: import-repair-proposal/v1 -->\n"
            f"<!-- student-os-target: {outside_target} -->\n\n"
            f"<!-- student-os-target-sha256: {legacy_item['content_sha256']} -->\n"
            f"<!-- student-os-case-json: {legacy_case_json} -->\n"
            f"<!-- student-os-case-sha256: {legacy_case_digest} -->\n"
            f"<!-- student-os-evidence-sha256: {legacy_case_state['evidence_sha256']} -->\n"
            "<!-- student-os-evidence-mode: text-only -->\n"
            "<!-- student-os-model-capability: text-only -->\n"
            "<!-- student-os-changed-sections: line-1 -->\n"
            "<!-- student-os-remaining-risks: human-review-required -->\n\n"
            "<!-- student-os-replacement-start -->\n"
            "---\nsource_file: outside.pdf\nrepair_status: auto-repaired\nverify_status: unverified\n---\n\n"
            "Outside content.\n"
            "<!-- student-os-replacement-end -->\n",
        )
        outside_target_review = run_json("repair_import_review.py", "--proposal", str(outside_target_proposal), "--json", cwd=vault, expect_ok=False)
        if not any(issue["code"] == "proposal-target-outside-vault" for issue in outside_target_review["issues"]):  # type: ignore[index]
            raise AssertionError(f"Outside proposal target should fail review: {outside_target_review}")

        existing_output = vault / ".student-os" / "import-repair" / "applied" / "existing.pdf.md"
        write_text(existing_output, "existing\n")
        existing_output_result = run_json(
            "repair_import_apply.py",
            "--proposal",
            str(clean),
            "--output",
            str(existing_output),
            "--json",
            cwd=vault,
            expect_ok=False,
        )
        if existing_output_result.get("stage") != "output":
            raise AssertionError(f"Apply should refuse alternate existing output: {existing_output_result}")
        outside_output_result = run_json(
            "repair_import_apply.py",
            "--proposal",
            str(clean),
            "--output",
            str(Path(tmp) / "outside-output.pdf.md"),
            "--json",
            cwd=vault,
            expect_ok=False,
        )
        if outside_output_result.get("stage") != "output":
            raise AssertionError(f"Apply should refuse output outside the bound vault: {outside_output_result}")

        cross_target = vault / ".student-os" / "import-repair" / "proposals" / "cross-target.md"
        write_text(
            cross_target,
            "# Cross-target proposal\n\n"
            "<!-- student-os-proposal-schema: import-repair-proposal/v1 -->\n"
            f"<!-- student-os-target: {paths['legacy']} -->\n\n"
            f"<!-- student-os-target-sha256: {legacy_item['content_sha256']} -->\n"
            f"<!-- student-os-case-json: {semantic_case_json} -->\n"
            f"<!-- student-os-case-sha256: {semantic_case_digest} -->\n"
            f"<!-- student-os-evidence-sha256: {semantic_evidence_sha} -->\n"
            "<!-- student-os-evidence-mode: text-only -->\n"
            "<!-- student-os-model-capability: text-only -->\n"
            "<!-- student-os-changed-sections: line-1 -->\n"
            "<!-- student-os-remaining-risks: human-review-required -->\n\n"
            "<!-- student-os-replacement-start -->\n"
            "---\nsource_file: legacy.pdf\nrepair_status: auto-repaired\nverify_status: unverified\n---\n\n"
            "Readable body.\n"
            "<!-- student-os-replacement-end -->\n",
        )
        cross_review = run_json("repair_import_review.py", "--proposal", str(cross_target), "--json", cwd=vault, expect_ok=False)
        if not any(issue["code"] == "proposal-case-target-mismatch" for issue in cross_review["issues"]):  # type: ignore[index]
            raise AssertionError(f"Cross-target case should fail review: {cross_review}")

        missing_queue_case = vault / ".student-os" / "import-repair" / "evidence" / "missing-queue-case.json"
        missing_queue_payload = json.loads(legacy_case_json.read_text(encoding="utf-8"))
        missing_queue_payload.pop("queue_item", None)
        missing_queue_payload["case_sha256"] = case_sha256(missing_queue_payload)
        write_text(missing_queue_case, json.dumps(missing_queue_payload, ensure_ascii=False, indent=2) + "\n")
        missing_queue_proposal = vault / ".student-os" / "import-repair" / "proposals" / "missing-queue.md"
        write_text(
            missing_queue_proposal,
            "# Missing queue proposal\n\n"
            "<!-- student-os-proposal-schema: import-repair-proposal/v1 -->\n"
            f"<!-- student-os-target: {paths['legacy']} -->\n\n"
            f"<!-- student-os-target-sha256: {legacy_item['content_sha256']} -->\n"
            f"<!-- student-os-case-json: {missing_queue_case} -->\n"
            f"<!-- student-os-case-sha256: {missing_queue_payload['case_sha256']} -->\n"
            f"<!-- student-os-evidence-sha256: {legacy_case_state['evidence_sha256']} -->\n"
            "<!-- student-os-evidence-mode: text-only -->\n"
            "<!-- student-os-model-capability: text-only -->\n"
            "<!-- student-os-changed-sections: line-1 -->\n"
            "<!-- student-os-remaining-risks: human-review-required -->\n\n"
            "<!-- student-os-replacement-start -->\n"
            "---\nsource_file: legacy.pdf\nrepair_status: auto-repaired\nverify_status: unverified\n---\n\n"
            "Readable body.\n"
            "<!-- student-os-replacement-end -->\n",
        )
        missing_queue_review = run_json("repair_import_review.py", "--proposal", str(missing_queue_proposal), "--json", cwd=vault, expect_ok=False)
        if not any(issue["code"] == "proposal-case-queue-item-missing" for issue in missing_queue_review["issues"]):  # type: ignore[index]
            raise AssertionError(f"Case without queue_item should fail review: {missing_queue_review}")

        erased_body = vault / ".student-os" / "import-repair" / "proposals" / "erased-body.md"
        write_text(
            erased_body,
            "# Erased body proposal\n\n"
            "<!-- student-os-proposal-schema: import-repair-proposal/v1 -->\n"
            f"<!-- student-os-target: {paths['legacy']} -->\n\n"
            f"<!-- student-os-target-sha256: {legacy_item['content_sha256']} -->\n"
            f"<!-- student-os-case-json: {legacy_case_json} -->\n"
            f"<!-- student-os-case-sha256: {legacy_case_digest} -->\n"
            f"<!-- student-os-evidence-sha256: {legacy_case_state['evidence_sha256']} -->\n"
            "<!-- student-os-evidence-mode: text-only -->\n"
            "<!-- student-os-model-capability: text-only -->\n"
            "<!-- student-os-changed-sections: line-1 -->\n"
            "<!-- student-os-remaining-risks: human-review-required -->\n\n"
            "<!-- student-os-replacement-start -->\n"
            "---\nsource_file: legacy.pdf\nrepair_status: auto-repaired\nverify_status: unverified\n---\n\n"
            "<!-- student-os-replacement-end -->\n",
        )
        erased_review = run_json("repair_import_review.py", "--proposal", str(erased_body), "--json", cwd=vault, expect_ok=False)
        if not any(issue["code"] == "replacement-body-erased" for issue in erased_review["issues"]):  # type: ignore[index]
            raise AssertionError(f"Unnumbered content erasure should fail review: {erased_review}")

        long_item = by_name["long-body.pdf.md"]
        long_case = run_json(
            "repair_import_case.py",
            "--queue",
            str(queue_path),
            "--queue-item",
            str(long_item["id"]),
            "--evidence-mode",
            "text-only",
            "--json",
            cwd=vault,
        )
        long_case_json = Path(str(long_case["case_json"]))
        long_case_state = json.loads(long_case_json.read_text(encoding="utf-8"))
        long_body_erased = vault / ".student-os" / "import-repair" / "proposals" / "long-body-erased.md"
        write_text(
            long_body_erased,
            "# Long body erased proposal\n\n"
            "<!-- student-os-proposal-schema: import-repair-proposal/v1 -->\n"
            f"<!-- student-os-target: {paths['long_body']} -->\n\n"
            f"<!-- student-os-target-sha256: {long_item['content_sha256']} -->\n"
            f"<!-- student-os-case-json: {long_case_json} -->\n"
            f"<!-- student-os-case-sha256: {long_case_state['case_sha256']} -->\n"
            f"<!-- student-os-evidence-sha256: {long_case_state['evidence_sha256']} -->\n"
            "<!-- student-os-evidence-mode: text-only -->\n"
            "<!-- student-os-model-capability: text-only -->\n"
            "<!-- student-os-changed-sections: line-1 -->\n"
            "<!-- student-os-remaining-risks: human-review-required -->\n\n"
            "<!-- student-os-replacement-start -->\n"
            "---\nsource_file: long-body.pdf\nrepair_status: auto-repaired\nverify_status: unverified\n---\n\n"
            "Short retained fragment.\n"
            "<!-- student-os-replacement-end -->\n",
        )
        long_erased_review = run_json("repair_import_review.py", "--proposal", str(long_body_erased), "--json", cwd=vault, expect_ok=False)
        if not any(issue["code"] == "replacement-body-erased" for issue in long_erased_review["issues"]):  # type: ignore[index]
            raise AssertionError(f"Long unnumbered content erasure should fail review: {long_erased_review}")
        comment_padded = vault / ".student-os" / "import-repair" / "proposals" / "comment-padded.md"
        write_text(
            comment_padded,
            "# Comment padded proposal\n\n"
            "<!-- student-os-proposal-schema: import-repair-proposal/v1 -->\n"
            f"<!-- student-os-target: {paths['long_body']} -->\n\n"
            f"<!-- student-os-target-sha256: {long_item['content_sha256']} -->\n"
            f"<!-- student-os-case-json: {long_case_json} -->\n"
            f"<!-- student-os-case-sha256: {long_case_state['case_sha256']} -->\n"
            f"<!-- student-os-evidence-sha256: {long_case_state['evidence_sha256']} -->\n"
            "<!-- student-os-evidence-mode: text-only -->\n"
            "<!-- student-os-model-capability: text-only -->\n"
            "<!-- student-os-changed-sections: line-1 -->\n"
            "<!-- student-os-remaining-risks: human-review-required -->\n\n"
            "<!-- student-os-replacement-start -->\n"
            "---\nsource_file: long-body.pdf\nrepair_status: auto-repaired\nverify_status: unverified\n---\n\n"
            "Short retained fragment.\n"
            "<!-- " + ("hidden padding " * 300) + "-->\n"
            "<!-- student-os-replacement-end -->\n",
        )
        comment_padded_review = run_json("repair_import_review.py", "--proposal", str(comment_padded), "--json", cwd=vault, expect_ok=False)
        if not any(issue["code"] == "replacement-body-erased" for issue in comment_padded_review["issues"]):  # type: ignore[index]
            raise AssertionError(f"Hidden comments should not count as retained visible content: {comment_padded_review}")

        html_padded = vault / ".student-os" / "import-repair" / "proposals" / "html-padded.md"
        write_text(
            html_padded,
            "# HTML padded proposal\n\n"
            "<!-- student-os-proposal-schema: import-repair-proposal/v1 -->\n"
            f"<!-- student-os-target: {paths['long_body']} -->\n\n"
            f"<!-- student-os-target-sha256: {long_item['content_sha256']} -->\n"
            f"<!-- student-os-case-json: {long_case_json} -->\n"
            f"<!-- student-os-case-sha256: {long_case_state['case_sha256']} -->\n"
            f"<!-- student-os-evidence-sha256: {long_case_state['evidence_sha256']} -->\n"
            "<!-- student-os-evidence-mode: text-only -->\n"
            "<!-- student-os-model-capability: text-only -->\n"
            "<!-- student-os-changed-sections: line-1 -->\n"
            "<!-- student-os-remaining-risks: human-review-required -->\n\n"
            "<!-- student-os-replacement-start -->\n"
            "---\nsource_file: long-body.pdf\nrepair_status: auto-repaired\nverify_status: unverified\n---\n\n"
            "Short retained fragment.\n"
            "<span title=\"" + ("hidden padding " * 300) + "\"></span>\n"
            "<!-- student-os-replacement-end -->\n",
        )
        html_padded_review = run_json("repair_import_review.py", "--proposal", str(html_padded), "--json", cwd=vault, expect_ok=False)
        if not any(issue["code"] == "replacement-body-erased" for issue in html_padded_review["issues"]):  # type: ignore[index]
            raise AssertionError(f"HTML attributes should not count as retained visible content: {html_padded_review}")

        numbered_item = by_name["numbered-long.pdf.md"]
        numbered_case = run_json(
            "repair_import_case.py",
            "--queue",
            str(queue_path),
            "--queue-item",
            str(numbered_item["id"]),
            "--evidence-mode",
            "text-only",
            "--json",
            cwd=vault,
        )
        numbered_case_json = Path(str(numbered_case["case_json"]))
        numbered_case_state = json.loads(numbered_case_json.read_text(encoding="utf-8"))
        numbered_erased = vault / ".student-os" / "import-repair" / "proposals" / "numbered-erased.md"
        write_text(
            numbered_erased,
            "# Numbered body erased proposal\n\n"
            "<!-- student-os-proposal-schema: import-repair-proposal/v1 -->\n"
            f"<!-- student-os-target: {paths['numbered_long']} -->\n\n"
            f"<!-- student-os-target-sha256: {numbered_item['content_sha256']} -->\n"
            f"<!-- student-os-case-json: {numbered_case_json} -->\n"
            f"<!-- student-os-case-sha256: {numbered_case_state['case_sha256']} -->\n"
            f"<!-- student-os-evidence-sha256: {numbered_case_state['evidence_sha256']} -->\n"
            "<!-- student-os-evidence-mode: text-only -->\n"
            "<!-- student-os-model-capability: text-only -->\n"
            "<!-- student-os-changed-sections: line-1 -->\n"
            "<!-- student-os-remaining-risks: human-review-required -->\n\n"
            "<!-- student-os-replacement-start -->\n"
            "---\nsource_file: numbered-long.pdf\nrepair_status: auto-repaired\nverify_status: unverified\n---\n\n"
            "1. x\n"
            "2. y\n"
            "<!-- student-os-replacement-end -->\n",
        )
        numbered_erased_review = run_json("repair_import_review.py", "--proposal", str(numbered_erased), "--json", cwd=vault, expect_ok=False)
        if not any(issue["code"] == "replacement-body-erased" for issue in numbered_erased_review["issues"]):  # type: ignore[index]
            raise AssertionError(f"Numbered content erasure should fail review: {numbered_erased_review}")

        derived_dropped = vault / ".student-os" / "import-repair" / "proposals" / "derived-dropped.md"
        write_text(
            derived_dropped,
            "# Derived evidence dropped proposal\n\n"
            "<!-- student-os-proposal-schema: import-repair-proposal/v1 -->\n"
            f"<!-- student-os-target: {paths['derived_note']} -->\n\n"
            f"<!-- student-os-target-sha256: {derived_item['content_sha256']} -->\n"
            f"<!-- student-os-case-json: {derived_case_json} -->\n"
            f"<!-- student-os-case-sha256: {derived_case_state['case_sha256']} -->\n"
            f"<!-- student-os-evidence-sha256: {derived_case_state['evidence_sha256']} -->\n"
            "<!-- student-os-evidence-mode: text-only -->\n"
            "<!-- student-os-model-capability: text-only -->\n"
            "<!-- student-os-changed-sections: line-1 -->\n"
            "<!-- student-os-remaining-risks: human-review-required -->\n\n"
            "<!-- student-os-replacement-start -->\n"
            "---\nsource_file: derived.pdf\nrepair_status: auto-repaired\nverify_status: unverified\n---\n\n"
            "Derived import sidecar with nonstandard filename.\n"
            "<!-- student-os-replacement-end -->\n",
        )
        derived_dropped_review = run_json("repair_import_review.py", "--proposal", str(derived_dropped), "--json", cwd=vault, expect_ok=False)
        if not any(issue["code"] == "derived-from-import-dropped" for issue in derived_dropped_review["issues"]):  # type: ignore[index]
            raise AssertionError(f"Dropping derived_from_import should fail review: {derived_dropped_review}")

        invalid_top_case = vault / ".student-os" / "import-repair" / "evidence" / "invalid-top-case.json"
        write_text(invalid_top_case, json.dumps([legacy_case_state], ensure_ascii=False, indent=2) + "\n")
        invalid_top_proposal = vault / ".student-os" / "import-repair" / "proposals" / "invalid-top-case.md"
        write_text(
            invalid_top_proposal,
            "# Invalid top-level case proposal\n\n"
            "<!-- student-os-proposal-schema: import-repair-proposal/v1 -->\n"
            f"<!-- student-os-target: {paths['legacy']} -->\n\n"
            f"<!-- student-os-target-sha256: {legacy_item['content_sha256']} -->\n"
            f"<!-- student-os-case-json: {invalid_top_case} -->\n"
            "<!-- student-os-case-sha256: not-a-case-object -->\n"
            f"<!-- student-os-evidence-sha256: {legacy_case_state['evidence_sha256']} -->\n"
            "<!-- student-os-evidence-mode: text-only -->\n"
            "<!-- student-os-model-capability: text-only -->\n"
            "<!-- student-os-changed-sections: line-1 -->\n"
            "<!-- student-os-remaining-risks: human-review-required -->\n\n"
            "<!-- student-os-replacement-start -->\n"
            "---\nsource_file: legacy.pdf\nrepair_status: auto-repaired\nverify_status: unverified\n---\n\n"
            "Readable body.\n"
            "<!-- student-os-replacement-end -->\n",
        )
        invalid_top_review = run_json("repair_import_review.py", "--proposal", str(invalid_top_proposal), "--json", cwd=vault, expect_ok=False)
        if not any(issue["code"] == "proposal-case-json-top-level-invalid" for issue in invalid_top_review["issues"]):  # type: ignore[index]
            raise AssertionError(f"Non-object case JSON should fail review: {invalid_top_review}")

        empty_queue_case = vault / ".student-os" / "import-repair" / "evidence" / "empty-queue-case.json"
        empty_queue_payload = json.loads(legacy_case_json.read_text(encoding="utf-8"))
        empty_queue_payload["queue_item"] = {}
        empty_queue_payload["case_sha256"] = case_sha256(empty_queue_payload)
        write_text(empty_queue_case, json.dumps(empty_queue_payload, ensure_ascii=False, indent=2) + "\n")
        empty_queue_proposal = vault / ".student-os" / "import-repair" / "proposals" / "empty-queue.md"
        write_text(
            empty_queue_proposal,
            "# Empty queue proposal\n\n"
            "<!-- student-os-proposal-schema: import-repair-proposal/v1 -->\n"
            f"<!-- student-os-target: {paths['legacy']} -->\n\n"
            f"<!-- student-os-target-sha256: {legacy_item['content_sha256']} -->\n"
            f"<!-- student-os-case-json: {empty_queue_case} -->\n"
            f"<!-- student-os-case-sha256: {empty_queue_payload['case_sha256']} -->\n"
            f"<!-- student-os-evidence-sha256: {legacy_case_state['evidence_sha256']} -->\n"
            "<!-- student-os-evidence-mode: text-only -->\n"
            "<!-- student-os-model-capability: text-only -->\n"
            "<!-- student-os-changed-sections: line-1 -->\n"
            "<!-- student-os-remaining-risks: human-review-required -->\n\n"
            "<!-- student-os-replacement-start -->\n"
            "---\nsource_file: legacy.pdf\nrepair_status: auto-repaired\nverify_status: unverified\n---\n\n"
            "Readable body.\n"
            "<!-- student-os-replacement-end -->\n",
        )
        empty_queue_review = run_json("repair_import_review.py", "--proposal", str(empty_queue_proposal), "--json", cwd=vault, expect_ok=False)
        if not any(issue["code"] == "proposal-case-queue-item-incomplete" for issue in empty_queue_review["issues"]):  # type: ignore[index]
            raise AssertionError(f"Incomplete queue_item should fail review: {empty_queue_review}")

        ocr_case = vault / ".student-os" / "import-repair" / "evidence" / "ocr-case" / "case.json"
        ocr_evidence = {
            "schema_version": "import-repair-case/v1",
            "mode": "ocr-assisted",
            "recommended_mode": "ocr-assisted",
            "blocked": "",
            "pages": [],
            "state_dir": str(ocr_case.parent),
            "ocr": {"ok": False, "reason": "not-run-by-case-tool"},
        }
        ocr_payload = {
            "schema_version": "import-repair-case/v1",
            "ok": True,
            "queue_item": legacy_item,
            "evidence": ocr_evidence,
            "evidence_sha256": object_sha256(ocr_evidence),
        }
        ocr_payload["case_sha256"] = case_sha256(ocr_payload)
        write_text(ocr_case, json.dumps(ocr_payload, ensure_ascii=False, indent=2) + "\n")
        ocr_proposal = vault / ".student-os" / "import-repair" / "proposals" / "ocr.md"
        write_text(
            ocr_proposal,
            "# OCR proposal\n\n"
            "<!-- student-os-proposal-schema: import-repair-proposal/v1 -->\n"
            f"<!-- student-os-target: {paths['legacy']} -->\n\n"
            f"<!-- student-os-target-sha256: {legacy_item['content_sha256']} -->\n"
            f"<!-- student-os-case-json: {ocr_case} -->\n"
            f"<!-- student-os-case-sha256: {ocr_payload['case_sha256']} -->\n"
            f"<!-- student-os-evidence-sha256: {ocr_payload['evidence_sha256']} -->\n"
            "<!-- student-os-evidence-mode: ocr-assisted -->\n"
            "<!-- student-os-model-capability: text-only -->\n"
            "<!-- student-os-changed-sections: line-1 -->\n"
            "<!-- student-os-remaining-risks: human-review-required -->\n\n"
            "<!-- student-os-replacement-start -->\n"
            "---\nsource_file: legacy.pdf\nrepair_status: auto-repaired\nverify_status: unverified\n---\n\n"
            "Readable body.\n"
            "<!-- student-os-replacement-end -->\n",
        )
        ocr_review = run_json("repair_import_review.py", "--proposal", str(ocr_proposal), "--json", cwd=vault, expect_ok=False)
        if not any(issue["code"] == "ocr-evidence-unavailable" for issue in ocr_review["issues"]):  # type: ignore[index]
            raise AssertionError(f"OCR-assisted proposal should require successful OCR evidence: {ocr_review}")

        ocr_evidence_file = vault / ".student-os" / "import-repair" / "ocr" / "legacy-ocr.md"
        write_text(ocr_evidence_file, "# OCR Evidence\n\nReadable body from a controlled OCR artifact.\n")
        ocr_success_case = run_json(
            "repair_import_case.py",
            "--queue",
            str(queue_path),
            "--queue-item",
            str(legacy_item["id"]),
            "--evidence-mode",
            "ocr-assisted",
            "--ocr-evidence",
            str(ocr_evidence_file),
            "--json",
            cwd=vault,
        )
        if ocr_success_case["evidence"]["ocr"]["ok"] is not True:  # type: ignore[index]
            raise AssertionError(f"OCR evidence file should produce successful bound evidence: {ocr_success_case}")
        ocr_success_case_json = Path(str(ocr_success_case["case_json"]))
        ocr_success_state = json.loads(ocr_success_case_json.read_text(encoding="utf-8"))
        ocr_success_proposal = vault / ".student-os" / "import-repair" / "proposals" / "ocr-success.md"
        write_text(
            ocr_success_proposal,
            "# OCR success proposal\n\n"
            "<!-- student-os-proposal-schema: import-repair-proposal/v1 -->\n"
            f"<!-- student-os-target: {paths['legacy']} -->\n\n"
            f"<!-- student-os-target-sha256: {legacy_item['content_sha256']} -->\n"
            f"<!-- student-os-case-json: {ocr_success_case_json} -->\n"
            f"<!-- student-os-case-sha256: {ocr_success_state['case_sha256']} -->\n"
            f"<!-- student-os-evidence-sha256: {ocr_success_state['evidence_sha256']} -->\n"
            "<!-- student-os-evidence-mode: ocr-assisted -->\n"
            "<!-- student-os-model-capability: text-only -->\n"
            "<!-- student-os-changed-sections: line-1 -->\n"
            "<!-- student-os-remaining-risks: human-review-required -->\n\n"
            "<!-- student-os-replacement-start -->\n"
            "---\nsource_file: legacy.pdf\nrepair_status: auto-repaired\nverify_status: unverified\n---\n\n"
            "Readable body.\n"
            "<!-- student-os-replacement-end -->\n",
        )
        ocr_success_review = run_json("repair_import_review.py", "--proposal", str(ocr_success_proposal), "--json", cwd=vault)
        if ocr_success_review["review_pass"] is not True:
            raise AssertionError(f"OCR-assisted proposal with bound evidence should pass: {ocr_success_review}")
        write_text(ocr_evidence_file, "# OCR Evidence\n\nTampered OCR text.\n")
        ocr_tampered_review = run_json("repair_import_review.py", "--proposal", str(ocr_success_proposal), "--json", cwd=vault, expect_ok=False)
        if not any(issue["code"] == "ocr-evidence-unavailable" for issue in ocr_tampered_review["issues"]):  # type: ignore[index]
            raise AssertionError(f"Tampered OCR evidence should fail review: {ocr_tampered_review}")

        evidence_schema_case = vault / ".student-os" / "import-repair" / "evidence" / "bad-evidence-schema" / "case.json"
        bad_evidence = dict(legacy_case_state["evidence"])
        bad_evidence["schema_version"] = "import-repair-case/v0"
        bad_evidence_payload = {
            "schema_version": "import-repair-case/v1",
            "ok": True,
            "queue_item": legacy_item,
            "evidence": bad_evidence,
            "evidence_sha256": object_sha256(bad_evidence),
        }
        bad_evidence_payload["case_sha256"] = case_sha256(bad_evidence_payload)
        write_text(evidence_schema_case, json.dumps(bad_evidence_payload, ensure_ascii=False, indent=2) + "\n")
        evidence_schema_proposal = vault / ".student-os" / "import-repair" / "proposals" / "bad-evidence-schema.md"
        write_text(
            evidence_schema_proposal,
            "# Bad evidence schema proposal\n\n"
            "<!-- student-os-proposal-schema: import-repair-proposal/v1 -->\n"
            f"<!-- student-os-target: {paths['legacy']} -->\n\n"
            f"<!-- student-os-target-sha256: {legacy_item['content_sha256']} -->\n"
            f"<!-- student-os-case-json: {evidence_schema_case} -->\n"
            f"<!-- student-os-case-sha256: {bad_evidence_payload['case_sha256']} -->\n"
            f"<!-- student-os-evidence-sha256: {bad_evidence_payload['evidence_sha256']} -->\n"
            "<!-- student-os-evidence-mode: text-only -->\n"
            "<!-- student-os-model-capability: text-only -->\n"
            "<!-- student-os-changed-sections: line-1 -->\n"
            "<!-- student-os-remaining-risks: human-review-required -->\n\n"
            "<!-- student-os-replacement-start -->\n"
            "---\nsource_file: legacy.pdf\nrepair_status: auto-repaired\nverify_status: unverified\n---\n\n"
            "Readable body.\n"
            "<!-- student-os-replacement-end -->\n",
        )
        evidence_schema_review = run_json("repair_import_review.py", "--proposal", str(evidence_schema_proposal), "--json", cwd=vault, expect_ok=False)
        if not any(issue["code"] == "proposal-evidence-schema-invalid" for issue in evidence_schema_review["issues"]):  # type: ignore[index]
            raise AssertionError(f"Invalid nested evidence schema should fail review: {evidence_schema_review}")

        invalid_case = vault / ".student-os" / "import-repair" / "evidence" / "invalid-case.json"
        invalid_case_payload = json.loads(legacy_case_json.read_text(encoding="utf-8"))
        invalid_case_payload["schema_version"] = "import-repair-case/v0"
        write_text(invalid_case, json.dumps(invalid_case_payload, ensure_ascii=False, indent=2) + "\n")
        invalid_case_proposal = vault / ".student-os" / "import-repair" / "proposals" / "invalid-case.md"
        write_text(
            invalid_case_proposal,
            "# Invalid case proposal\n\n"
            "<!-- student-os-proposal-schema: import-repair-proposal/v1 -->\n"
            f"<!-- student-os-target: {paths['legacy']} -->\n\n"
            f"<!-- student-os-target-sha256: {legacy_item['content_sha256']} -->\n"
            f"<!-- student-os-case-json: {invalid_case} -->\n"
            f"<!-- student-os-case-sha256: {legacy_case_digest} -->\n"
            f"<!-- student-os-evidence-sha256: {legacy_case_state['evidence_sha256']} -->\n"
            "<!-- student-os-evidence-mode: text-only -->\n"
            "<!-- student-os-model-capability: text-only -->\n"
            "<!-- student-os-changed-sections: line-1 -->\n"
            "<!-- student-os-remaining-risks: human-review-required -->\n\n"
            "<!-- student-os-replacement-start -->\n"
            "---\nsource_file: legacy.pdf\nrepair_status: auto-repaired\nverify_status: unverified\n---\n\n"
            "Readable body.\n"
            "<!-- student-os-replacement-end -->\n",
        )
        invalid_case_review = run_json("repair_import_review.py", "--proposal", str(invalid_case_proposal), "--json", cwd=vault, expect_ok=False)
        if not any(issue["code"] == "proposal-case-schema-invalid" for issue in invalid_case_review["issues"]):  # type: ignore[index]
            raise AssertionError(f"Invalid case schema should fail review: {invalid_case_review}")

        outside_case_json = Path(tmp) / "outside-case.json"
        outside_case_payload = json.loads(legacy_case_json.read_text(encoding="utf-8"))
        outside_case_payload["case_sha256"] = case_sha256(outside_case_payload)
        write_text(outside_case_json, json.dumps(outside_case_payload, ensure_ascii=False, indent=2) + "\n")
        outside_case_proposal = vault / ".student-os" / "import-repair" / "proposals" / "outside-case.md"
        write_text(
            outside_case_proposal,
            "# Outside case proposal\n\n"
            "<!-- student-os-proposal-schema: import-repair-proposal/v1 -->\n"
            f"<!-- student-os-target: {paths['legacy']} -->\n\n"
            f"<!-- student-os-target-sha256: {legacy_item['content_sha256']} -->\n"
            f"<!-- student-os-case-json: {outside_case_json} -->\n"
            f"<!-- student-os-case-sha256: {outside_case_payload['case_sha256']} -->\n"
            f"<!-- student-os-evidence-sha256: {legacy_case_state['evidence_sha256']} -->\n"
            "<!-- student-os-evidence-mode: text-only -->\n"
            "<!-- student-os-model-capability: text-only -->\n"
            "<!-- student-os-changed-sections: line-1 -->\n"
            "<!-- student-os-remaining-risks: human-review-required -->\n\n"
            "<!-- student-os-replacement-start -->\n"
            "---\nsource_file: legacy.pdf\nrepair_status: auto-repaired\nverify_status: unverified\n---\n\n"
            "Readable body.\n"
            "<!-- student-os-replacement-end -->\n",
        )
        outside_case_review = run_json("repair_import_review.py", "--proposal", str(outside_case_proposal), "--json", cwd=vault, expect_ok=False)
        if not any(issue["code"] == "proposal-case-json-outside-vault" for issue in outside_case_review["issues"]):  # type: ignore[index]
            raise AssertionError(f"Case JSON outside .student-os should fail review: {outside_case_review}")

        fake_vision_case = vault / ".student-os" / "import-repair" / "evidence" / "fake-vision" / "case.json"
        outside_png = Path(tmp) / "outside.png"
        outside_png.write_bytes(b"\x89PNG\r\n\x1a\nfake")
        fake_vision_evidence = {
            "schema_version": "import-repair-case/v1",
            "mode": "vision-assisted",
            "recommended_mode": "vision-assisted",
            "blocked": "",
            "pages": [],
            "state_dir": str(fake_vision_case.parent),
            "vision": {"ok": True, "pages": [{"page": 1, "path": str(outside_png), "sha256": file_sha256(outside_png)}], "failures": []},
        }
        fake_vision_payload = {
            "schema_version": "import-repair-case/v1",
            "ok": True,
            "queue_item": legacy_item,
            "evidence": fake_vision_evidence,
            "evidence_sha256": object_sha256(fake_vision_evidence),
        }
        fake_vision_payload["case_sha256"] = case_sha256(fake_vision_payload)
        write_text(fake_vision_case, json.dumps(fake_vision_payload, ensure_ascii=False, indent=2) + "\n")
        fake_vision_proposal = vault / ".student-os" / "import-repair" / "proposals" / "fake-vision.md"
        write_text(
            fake_vision_proposal,
            "# Fake vision proposal\n\n"
            "<!-- student-os-proposal-schema: import-repair-proposal/v1 -->\n"
            f"<!-- student-os-target: {paths['legacy']} -->\n\n"
            f"<!-- student-os-target-sha256: {legacy_item['content_sha256']} -->\n"
            f"<!-- student-os-case-json: {fake_vision_case} -->\n"
            f"<!-- student-os-case-sha256: {fake_vision_payload['case_sha256']} -->\n"
            f"<!-- student-os-evidence-sha256: {fake_vision_payload['evidence_sha256']} -->\n"
            "<!-- student-os-evidence-mode: vision-assisted -->\n"
            "<!-- student-os-model-capability: vision -->\n"
            "<!-- student-os-changed-sections: line-1 -->\n"
            "<!-- student-os-remaining-risks: human-review-required -->\n\n"
            "<!-- student-os-replacement-start -->\n"
            "---\nsource_file: legacy.pdf\nrepair_status: auto-repaired\nverify_status: unverified\n---\n\n"
            "Readable body.\n"
            "<!-- student-os-replacement-end -->\n",
        )
        fake_vision_review = run_json("repair_import_review.py", "--proposal", str(fake_vision_proposal), "--json", cwd=vault, expect_ok=False)
        if not any(issue["code"] == "vision-evidence-page-missing" for issue in fake_vision_review["issues"]):  # type: ignore[index]
            raise AssertionError(f"Vision page paths outside the case pages directory should fail review: {fake_vision_review}")

        direct_vault = Path(tmp) / "direct-inline-vault"
        direct_imports = direct_vault / "reviews"
        direct_imports.mkdir(parents=True)
        (direct_vault / ".student-os").mkdir()
        direct_inline = direct_imports / "中文 inline.pdf.md"
        write_text(
            direct_inline,
            "---\n"
            "source_file: 中文 inline.pdf\n"
            "repair_status: auto-repaired\n"
            "verify_status: unverified\n"
            "---\n"
            "\n"
            "一. 由(ii)得(I)的通解为 $ x = A^{-1}b $，且 $ y=C $。\n"
            "\n"
            "二. 不应被第一题局部修复影响。\n",
        )
        inline_run = run_json("repair_import_run.py", str(direct_vault), "--json", cwd=direct_vault)
        if inline_run.get("ok") is not True or inline_run.get("applied") is not True or inline_run.get("target_modified") is not True:
            raise AssertionError(f"Direct run should apply inline delimiter-space fixes: {inline_run}")
        inline_text = direct_inline.read_text(encoding="utf-8")
        if "$ x = A^{-1}b $" in inline_text or "$ y=C $" in inline_text:
            raise AssertionError(f"Direct run should remove only delimiter-adjacent inline math spaces:\n{inline_text}")
        if "$x = A^{-1}b$" not in inline_text or "$y=C$" not in inline_text:
            raise AssertionError(f"Direct run should preserve inline formula content:\n{inline_text}")
        inline_proposal = Path(str(inline_run["proposal"]))
        if "student-os-line-replacement-start" not in inline_proposal.read_text(encoding="utf-8"):
            raise AssertionError(f"Direct run should use line-span replacement artifacts: {inline_proposal}")

        check_vault = Path(tmp) / "direct-check-vault"
        check_imports = check_vault / "reviews" / "线性代数"
        check_imports.mkdir(parents=True)
        (check_vault / ".student-os").mkdir()
        broken_check = check_imports / "明显没渲染.pdf.md"
        write_text(
            broken_check,
            "---\n"
            "source_file: 明显没渲染.pdf\n"
            "repair_status: auto-repaired\n"
            "verify_status: unverified\n"
            "---\n"
            "\n"
            "二. 由条件得 $ x = A^{-1}b $，并有即 $$ A = B $$，继续。\n"
            "\n"
            "解矩阵方程 }$\n"
            "\n"
            "局部公式 $x^{2}}$ 也会坏。\n"
            "\n"
            "$\\begin{array}{r}{1 & 0 \\\\ 0 & 1}\\end{array}$\n",
        )
        broken_payload = run_json("repair_import_check.py", str(broken_check), "--json", cwd=check_vault, expect_ok=False)
        broken_codes = {
            issue["code"]
            for file_result in broken_payload["files"]  # type: ignore[index]
            for issue in file_result["blocking_errors"]  # type: ignore[index]
        }
        for expected in {
            "inline-math-delimiter-space",
            "display-math-delimiter-not-standalone",
            "latex-math-span-brace-unbalanced",
            "latex-dangling-close-before-dollar",
            "latex-array-wrapper-malformed",
        }:
            if expected not in broken_codes:
                raise AssertionError(f"repair_import_check.py should report {expected}: {broken_payload}")
        if "线性代数" not in json.dumps(broken_payload, ensure_ascii=False):
            raise AssertionError(f"repair_import_check.py should preserve readable Chinese paths: {broken_payload}")

        fixed_check = check_imports / "机械通过.pdf.md"
        write_text(
            fixed_check,
            "---\n"
            "source_file: 机械通过.pdf\n"
            "repair_status: auto-repaired\n"
            "verify_status: unverified\n"
            "---\n"
            "\n"
            "二. 由条件得 $x = A^{-1}b$，并有\n"
            "\n"
            "$$\n"
            "A = B\n"
            "$$\n"
            "\n"
            "$$\n"
            "\\begin{array}{cc}1 & 0 \\\\ 0 & 1\\end{array}\n"
            "$$\n",
        )
        fixed_payload = run_json("repair_import_check.py", str(fixed_check), "--json", cwd=check_vault)
        if fixed_payload.get("ok") is not True or fixed_payload.get("review_label") != "review passed":
            raise AssertionError(f"Fixed direct-edit markdown should pass mechanical review: {fixed_payload}")

    print("OK import-repair-evals")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

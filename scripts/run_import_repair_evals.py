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
from repair_import_queue import decode_yaml_path  # noqa: E402
from repair_import_case import case_sha256, object_sha256  # noqa: E402


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
        "Raw OCR evidence with \\boxplus noise.\n",
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
        "vision": vision,
        "missing_pdf": missing_pdf,
        "legacy": legacy,
        "long_body": long_body,
        "derived_note": derived_note,
        "many_pages": many_pages,
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
        by_name = {Path(str(item["path"])).name: item for item in queue["items"]}  # type: ignore[index]
        if "verified.pdf.md" in by_name or "long-verified.pdf.md" in by_name or queue["counts"]["skipped_verified"] != 2:  # type: ignore[index]
            raise AssertionError(f"Verified files should be skipped by default: {queue}")
        if "2016-answer.pdf.raw.md" in by_name:
            raise AssertionError(f"Raw import evidence should not be queued as a repair target: {queue}")
        direct_derived_queue = run_json("repair_import_queue.py", str(paths["derived_note"]), "--json", cwd=ROOT)
        direct_names = {Path(str(item["path"])).name for item in direct_derived_queue["items"]}  # type: ignore[index]
        if "derived-note.md" not in direct_names:
            raise AssertionError(f"Direct file scan should include derived_from_import markdown: {direct_derived_queue}")
        direct_written = run_json("repair_import_queue.py", str(paths["derived_note"]), "--write-queue", "--json", cwd=ROOT)
        if Path(str(direct_written["queue_path"])).parent != paths["derived_note"].parent / ".student-os" / "import-repair":
            raise AssertionError(f"Single-file queue should be written beside the target file: {direct_written}")

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

        answer_item = by_name["2014参考答案.pdf.md"]
        if answer_item["repair_class"] != "answer-paper-crosscheck":
            raise AssertionError(f"Answer-only fixture should require crosscheck: {answer_item}")
        if answer_item["blocked"] not in {"unrecoverable-with-current-evidence", "requires-vision-evidence"}:
            raise AssertionError(f"Missing source answer fixture should be explicitly blocked: {answer_item}")
        proof_answer_item = by_name["2018证明答案.pdf.md"]
        if "answer-missing-question-stem" not in set(proof_answer_item["risk_codes"]):
            raise AssertionError(f"Proof-only answer sidecar should not treat its solution lead as a question stem: {proof_answer_item}")

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

        fake_vision_case = vault / ".student-os" / "import-repair" / "evidence" / "fake-vision" / "case.json"
        fake_vision_evidence = {
            "schema_version": "import-repair-case/v1",
            "mode": "vision-assisted",
            "recommended_mode": "vision-assisted",
            "blocked": "",
            "pages": [],
            "state_dir": str(fake_vision_case.parent),
            "vision": {"ok": True, "pages": [{"page": 1}], "failures": []},
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
            raise AssertionError(f"Missing rendered vision page paths should fail review: {fake_vision_review}")

    print("OK import-repair-evals")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

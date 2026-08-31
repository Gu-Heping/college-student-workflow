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


def run_student_script(name: str, *args: str, cwd: Path, expect_ok: bool = True) -> dict[str, object]:
    result = subprocess.run(
        [sys.executable, "-B", str(STUDENT_OS_SCRIPTS / name), *args],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=cwd,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"},
    )
    if expect_ok and result.returncode != 0:
        raise AssertionError(f"{name} failed unexpectedly:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}")
    if not expect_ok and result.returncode == 0:
        raise AssertionError(f"{name} should have failed for args {args!r}")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise AssertionError(f"{name} did not print JSON:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}") from exc


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def build_fixture(vault: Path) -> Path:
    course = vault / "courses" / "linear-algebra"
    write_text(course / "index.md", "# 线性代数\n")
    papers = course / "references" / "exams"
    write_text(
        papers / "2024-final.pdf.md",
        "---\nsource_file: 2024-final.pdf\n---\n\n一、求矩阵方程 AX=B。\n\n解：用初等行变换。\n",
    )
    write_text(
        papers / "2024-final答案复习版.pdf.md",
        "---\nsource_file: 2024-final-answer.pdf\n---\n\n一、答案：用 $X=A^{-1}B$。\n",
    )
    write_text(
        papers / "2025-final.pdf.md",
        "---\nsource_file: 2025-final.pdf\n---\n\n一、判断向量组线性相关性。\n",
    )
    return papers


def verify_init_and_initial_failure(tmp_root: Path) -> tuple[Path, dict[str, object]]:
    vault = tmp_root / "vault"
    papers = build_fixture(vault)
    payload = run_student_script(
        "exam_prep_build.py",
        str(vault),
        "--course",
        "linear-algebra",
        "--exam-scope",
        "期末",
        "--papers-dir",
        str(papers),
        "--json",
        cwd=ROOT,
    )
    if payload.get("workflow") != "ai-first-exam-prep" or payload.get("paper_count") != 2:
        raise AssertionError(f"Unexpected build payload: {payload}")
    if payload.get("raw_source_count") != 3 or payload.get("canonical_exam_count") != 2:
        raise AssertionError(f"Build should group duplicate exam sidecars into canonical exams: {payload}")
    manifest = json.loads((vault / ".student-os" / "state" / "exam-prep" / "linear-algebra" / "期末" / "manifest.json").read_text(encoding="utf-8"))
    paper_2024 = next((item for item in manifest.get("papers", []) if item.get("id") == "2024-final"), None)
    if not paper_2024 or "answer_review" not in paper_2024.get("source_roles", {}):
        raise AssertionError(f"Canonical exam manifest should retain answer/review sidecar roles: {manifest}")
    for rel in (
        "courses/linear-algebra/reviews/期末/quality-standard.md",
        "courses/linear-algebra/reviews/期末/试卷精析",
        "courses/linear-algebra/reviews/期末/题目卡",
        "courses/linear-algebra/reviews/期末/题型备课卡",
        "courses/linear-algebra/reviews/期末/题型解析",
        "courses/linear-algebra/reviews/期末/分析",
        ".student-os/state/exam-prep/linear-algebra/期末/source-map.json",
        ".student-os/state/exam-prep/linear-algebra/期末/gold-sample-task.json",
        ".student-os/state/exam-prep/linear-algebra/期末/paper-cards",
        ".student-os/state/exam-prep/linear-algebra/期末/type-dossiers",
    ):
        if not (vault / rel).exists():
            raise AssertionError(f"Missing initialized path: {rel}")

    for stage in ("standard", "source-map"):
        early = run_student_script(
            "exam_prep_check.py",
            str(vault),
            "--course",
            "linear-algebra",
            "--exam-scope",
            "期末",
            "--stage",
            stage,
            "--json",
            cwd=ROOT,
        )
        if early.get("ok") is not True:
            raise AssertionError(f"Expected initialized {stage} stage to pass: {early}")

    check = run_student_script(
        "exam_prep_check.py",
        str(vault),
        "--course",
        "linear-algebra",
        "--exam-scope",
        "期末",
        "--json",
        cwd=ROOT,
        expect_ok=False,
    )
    codes = {issue["code"] for issue in check.get("issues", []) if isinstance(issue, dict)}
    required = {"missing-paper-cards", "missing-paper-card", "missing-paper-deep-dive"}
    if not required <= codes:
        raise AssertionError(f"Initial quality check should fail on AI-missing artifacts: {codes}")
    return vault, payload


def write_ai_outputs(vault: Path) -> None:
    reviews = vault / "courses" / "linear-algebra" / "reviews" / "期末"
    state = vault / ".student-os" / "state" / "exam-prep" / "linear-algebra" / "期末"
    refs_2024 = ["一", "二", "三", "四", "五"]
    refs_2025 = ["一", "二", "三", "四"]
    write_json(
        state / "paper-cards" / "2024-final.json",
        {
            "schema_version": 1,
            "source": "courses/linear-algebra/references/exams/2024-final.pdf.md",
            "confidence": "high",
            "questions": [
                {
                    "question_id": question_id,
                    "initial_type": "matrix-equation",
                    "prompt_summary": f"矩阵方程训练题 {question_id}",
                    "solution_summary": "用初等行变换、逆矩阵或分块关系求解",
                    "evidence_refs": [f"2024-final.pdf.md: {question_id}"],
                    "repeat_status": "unknown-pending-cross-paper-analysis",
                }
                for question_id in refs_2024
            ],
        },
    )
    write_json(
        state / "paper-cards" / "2025-final.json",
        {
            "schema_version": 1,
            "source": "courses/linear-algebra/references/exams/2025-final.pdf.md",
            "confidence": "medium",
            "questions": [
                {
                    "question_id": question_id,
                    "initial_type": "matrix-equation",
                    "prompt_summary": f"矩阵方程变式题 {question_id}",
                    "solution_summary": "先识别未知矩阵位置，再选择左右乘或增广矩阵",
                    "evidence_refs": [f"2025-final.pdf.md: {question_id}"],
                    "repeat_status": "unknown-pending-cross-paper-analysis",
                }
                for question_id in refs_2025
            ],
        },
    )
    all_refs = [*(f"2024-final.json#{qid}" for qid in refs_2024), *(f"2025-final.json#{qid}" for qid in refs_2025)]
    worked_refs = all_refs[:5]
    self_refs = all_refs[5:]
    human_ref = {ref: ref.replace("2024-final.json#", "2024-2025 期末 · ").replace("2025-final.json#", "2025-2026 期末 · ") for ref in all_refs}
    write_json(
        state / "taxonomy.json",
        {
            "schema_version": 1,
            "workflow": "ai-first-exam-prep",
            "course": "linear-algebra",
            "exam_scope": "期末",
            "types": [
                {
                    "id": "matrix-equation",
                    "name": "矩阵方程",
                    "confidence": "high",
                    "source_refs": all_refs,
                }
            ],
        },
    )
    write_json(
        state / "type-dossiers" / "matrix-equation.json",
        {
            "schema_version": 1,
            "workflow": "ai-first-exam-prep",
            "type_id": "matrix-equation",
            "type_name": "矩阵方程",
            "confidence": "high",
            "quality": "ready",
            "source_question_refs": all_refs,
            "recognition_cues": ["出现 AX=B、XA=B、AXB=C 或增广矩阵求未知矩阵"],
            "common_variants": ["左乘逆矩阵", "右乘逆矩阵", "增广矩阵", "分块矩阵"],
            "method_cards": ["先判断未知矩阵在左侧还是右侧，再决定左乘或右乘；维度不匹配时改用列向量/增广矩阵"],
            "formula_cards": ["AX=B 且 A 可逆时 X=A^{-1}B", "XA=B 且 A 可逆时 X=BA^{-1}"],
            "pitfalls": ["左右乘顺序写反", "把未知矩阵维度抄错", "增广矩阵分隔线位置错"],
            "worked_example_candidates": [{"question_ref": ref, "reason": "代表性例题"} for ref in worked_refs],
            "self_test_candidates": [{"question_ref": ref, "reason": "同型自测"} for ref in self_refs],
            "insufficient_evidence_notes": "",
        },
    )
    write_text(
        reviews / "题型备课卡" / "matrix-equation.md",
        "---\ntype: exam-type-dossier\ncourse: linear-algebra\nexam_scope: 期末\nexam_type_id: matrix-equation\nquality: ready\nstatus: active\nreview_scope: exam-prep\n---\n\n"
        "# 矩阵方程题型备课卡\n\n"
        "来源题池：" + "、".join(all_refs) + "。\n\n"
        "识别特征：看到 AX=B、XA=B、AXB=C 或未知矩阵和已知矩阵混合。\n\n"
        "核心方法：先判断未知矩阵位置，再选择左乘、右乘或增广矩阵。\n\n"
        "例题候选：" + "、".join(worked_refs) + "。\n\n"
        "自测候选：" + "、".join(self_refs) + "。\n",
    )
    write_text(
        reviews / "试卷精析" / "2024-final.md",
        "---\ntype: exam-paper-deep-dive\ncourse: linear-algebra\nexam_scope: 期末\nstatus: active\nreview_scope: exam-prep\n---\n\n"
        "# 2024 期末试卷精析\n\n## 一、矩阵方程\n\n题号：一。来源：2024-final 第 一 题。考点：可逆矩阵和矩阵方程。解法入口：看到 $AX=B$，先判断 $A$ 是否可逆，再选择逆矩阵或增广矩阵法。疑点：是否有跨年原题复现，等待第二轮跨卷分析。\n",
    )
    write_text(
        reviews / "试卷精析" / "2025-final.md",
        "---\ntype: exam-paper-deep-dive\ncourse: linear-algebra\nexam_scope: 期末\nstatus: active\nreview_scope: exam-prep\n---\n\n"
        "# 2025 期末试卷精析\n\n## 一、线性相关性\n\n题号：一。来源：2025-final 第 一 题。考点：秩与线性相关。解法入口：先看向量个数、维数和秩，再判断是否线性相关。疑点：是否与 2024 年同型，等待第二轮跨卷分析。\n",
    )
    examples = "\n\n".join(
        f"### 例题 {index}（来源：{human_ref[ref]}）\n\n"
        f"题目：设 $A=\\begin{{pmatrix}}1&0\\\\0&2\\end{{pmatrix}}$，$B=\\begin{{pmatrix}}{index}&1\\\\0&2\\end{{pmatrix}}$，求满足 $AX=B$ 的矩阵 $X$。\n\n"
        "看到题目先判断什么：先看未知矩阵在等式哪一侧、已知矩阵是否可逆、维度是否匹配。\n\n"
        "方法引用：使用备课卡 method_cards 中的左右乘或增广矩阵路线。\n\n"
        "完整解析：动作句先判 $A$ 在 $X$ 左边，且 $A$ 可逆；再列 $X=A^{-1}B$；代入 $A^{-1}=\\begin{pmatrix}1&0\\\\0&\\frac12\\end{pmatrix}$，得到 $X=\\begin{pmatrix}"
        f"{index}&1\\\\0&1"
        "\\end{pmatrix}$。\n\n"
        "验算或检查：把求出的 $X$ 代回原式，检查行列维度和乘法顺序。\n\n"
        "举一反三与常见变式：若未知矩阵换到右侧，就把左乘路线改为右乘路线；若出现增广矩阵，先看分隔线两边列数。\n\n"
        "易错点：不要把左乘逆矩阵写成右乘，也不要漏写可逆条件。"
        for index, ref in enumerate(worked_refs, start=1)
    )
    self_tests = "\n\n".join(
        f"### 自测 {index}（来源：{human_ref[ref]}）\n\n"
        f"题目：设 $C=\\begin{{pmatrix}}1&0\\\\0&3\\end{{pmatrix}}$，$D=\\begin{{pmatrix}}{index + 5}&0\\\\3&6\\end{{pmatrix}}$，求满足 $CX=D$ 的矩阵 $X$。\n\n"
        "提示：本题训练左右乘方法选择和同型变式识别；先写未知矩阵位置和可逆条件，再决定乘法方向。"
        for index, ref in enumerate(self_refs, start=1)
    )
    self_answers = "\n\n".join(
        f"### 自测 {index} 答案（来源：{human_ref[ref]}）\n\n答案：$X=C^{{-1}}D$。先判定乘法方向，再写对应公式并代入；最后代回原式验算。"
        f" 本题 $C^{{-1}}=\\begin{{pmatrix}}1&0\\\\0&\\frac13\\end{{pmatrix}}$，所以 $X=\\begin{{pmatrix}}{index + 5}&0\\\\1&2\\end{{pmatrix}}$。"
        for index, ref in enumerate(self_refs, start=1)
    )
    write_text(
        reviews / "题型解析" / "01-matrix-equation.md",
        "---\ntype: exam-type-analysis\ncourse: linear-algebra\nexam_scope: 期末\nexam_type_id: matrix-equation\nexam_type_name: 矩阵方程\nrank: 1\npaper_count: 1\nmust_know: true\nquality: ready\nstatus: active\nreview_scope: exam-prep\n---\n\n"
        "# 题型一：矩阵方程\n\n"
        "频率：9 道往年题进入题池；分值通常是中档计算题；难度以基础到中等为主；原题复现暂未确认，但同型变式集中；代表年份：2024、2025；复习优先级：P0。\n\n"
        "## 考前速记\n\n看到 $AX=B$，先问 $A$ 是否可逆。\n\n"
        "## 符号和概念表\n\n| 符号 | 意思 | 课本依据 |\n| --- | --- | --- |\n| $A^{-1}$ | 可逆矩阵 $A$ 的逆矩阵 | 课本 §2.3.1 逆矩阵定义 |\n| $AX=B$ | 未知矩阵在右侧的矩阵方程 | 课本 §2.3.1 矩阵乘法与逆矩阵 |\n\n"
        "## 核心概念\n\n矩阵方程把未知矩阵当成整体。课本 §2.3.1 说明可逆矩阵可以通过左乘逆矩阵消去；讲义图 2.3.1 的箭头顺序提醒乘法不可交换。来源：2024-2025 期末 · 一。\n\n"
        "## 2 分钟下笔模板\n\n动作句：先判未知矩阵在左还是右；再列消元方向；代入逆矩阵或增广矩阵；最后验算维度和原式。\n\n"
        "## 核心方法\n\n| 场景 | 方法 |\n| --- | --- |\n| $AX=B$ | 左乘 $A^{-1}$ 或做增广矩阵 |\n\n"
        "## 例题精讲\n\n"
        f"{examples}\n\n"
        "## 自测题\n\n"
        f"{self_tests}\n\n"
        "## 自测答案\n\n"
        f"{self_answers}\n\n"
        "## 快速得分技巧\n\n不会算完时先写 $AX=B \\Rightarrow X=A^{-1}B$ 的前提和步骤。\n\n"
        "## 易错点与检查清单\n\n| 易错 | 正确做法 |\n| --- | --- |\n| 忘记左乘顺序 | 写成 $X=A^{-1}B$ |\n\n"
        "## 来源校对说明\n\n来源：" + "、".join(human_ref[ref] for ref in all_refs) + "。\n",
    )
    for filename, title in (
        ("01-题型频率统计.md", "题型频率统计"),
        ("02-跨年原题重复记录.md", "跨年原题重复记录"),
        ("03-教材或课件覆盖分析.md", "教材或课件覆盖分析"),
        ("04-典型题或作业覆盖分析.md", "典型题或作业覆盖分析"),
        ("05-近年趋势与教考分离.md", "近年趋势与教考分离"),
    ):
        write_text(
            reviews / "分析" / filename,
            "---\ntype: exam-prep-analysis\ncourse: linear-algebra\nexam_scope: 期末\nstatus: active\nreview_scope: exam-prep\n---\n\n"
            f"# {title}\n\n来源：2024-2025 期末 · 一、2025-2026 期末 · 一。当前样本显示矩阵方程需要优先掌握，更多年份待继续补充。\n",
        )
    write_text(
        reviews / "期末考试备考指南.md",
        "---\ntype: exam-prep-guide\ncourse: linear-algebra\nexam_scope: 期末\nstatus: active\nreview_scope: exam-prep\n---\n\n"
        "# 线性代数期末考试备考指南\n\n## 怎么使用这套资料\n\n先看 [题型解析/01-matrix-equation.md](题型解析/01-matrix-equation.md)，再看 [期末公式总卡.md](期末公式总卡.md)、[期末答题模板速查.md](期末答题模板速查.md)、[考前1小时清单.md](考前1小时清单.md)。\n\n"
        "## 题型优先级\n\n| 优先级 | 题型 | 来源 |\n| --- | --- | --- |\n| P0 | 矩阵方程 | 2024-final 第 一 题 |\n\n"
        "## 复习时间分配\n\n1 小时先掌握矩阵方程的下笔模板。1 天路线是先读题型页，再做自测并核对答案。3 天路线是第一天补核心概念，第二天刷例题，第三天限时做往年题。\n",
    )
    write_text(
        reviews / "期末公式总卡.md",
        "---\ntype: formula-cheat-sheet\ncourse: linear-algebra\nexam_scope: 期末\nstatus: active\nreview_scope: exam-prep\n---\n\n"
        "# 期末公式总卡\n\n## 高频公式速查\n\n| 题型 | 公式 | 来源 |\n| --- | --- | --- |\n| [矩阵方程](题型解析/01-matrix-equation.md) | $AX=B \\Rightarrow X=A^{-1}B$ | 2024-final 第 一 题 |\n",
    )
    write_text(
        reviews / "期末答题模板速查.md",
        "---\ntype: answer-template-quickref\ncourse: linear-algebra\nexam_scope: 期末\nstatus: active\nreview_scope: exam-prep\n---\n\n"
        "# 期末答题模板速查\n\n## 标准答题模板\n\n| 题型 | 模板 | 来源 |\n| --- | --- | --- |\n| [矩阵方程](题型解析/01-matrix-equation.md) | 由[条件]，若 $A$ 可逆，则 $X=A^{-1}[表达式]$，因此[答案]。 | 2024-final 第 一 题 |\n",
    )
    write_text(
        reviews / "考前1小时清单.md",
        "---\ntype: pre-exam-one-hour-checklist\ncourse: linear-algebra\nexam_scope: 期末\nstatus: active\nreview_scope: exam-prep\n---\n\n"
        "# 考前1小时清单\n\n| 时间 | 做什么 | 文件 |\n| --- | --- | --- |\n| 60-45 分钟 | 看矩阵方程 | [题型解析/01-matrix-equation.md](题型解析/01-matrix-equation.md) |\n| 45-30 分钟 | 背公式 | [期末公式总卡.md](期末公式总卡.md) |\n| 30-15 分钟 | 背模板 | [期末答题模板速查.md](期末答题模板速查.md) |\n| 15-5 分钟 | 查易错点 | [期末考试备考指南.md](期末考试备考指南.md) |\n| 5-0 分钟 | 停止刷新题 | 本文件 |\n",
    )


def add_cross_paper_backfill(vault: Path) -> None:
    for path in (vault / "courses" / "linear-algebra" / "reviews" / "期末" / "试卷精析").glob("*.md"):
        text = path.read_text(encoding="utf-8")
        if "## 跨卷关系" not in text:
            path.write_text(
                text
                + "\n## 跨卷关系\n\n"
                + "原题复现：当前未发现完全原题；同型变式和复习优先级依据 2024-2025 期末 · 一、2025-2026 期末 · 一 标注。\n",
                encoding="utf-8",
                newline="\n",
            )


def verify_quality_pass_and_render_fail(tmp_root: Path) -> None:
    vault, _ = verify_init_and_initial_failure(tmp_root)
    write_ai_outputs(vault)
    gold_sample = run_student_script(
        "exam_prep_check.py",
        str(vault),
        "--course",
        "linear-algebra",
        "--exam-scope",
        "期末",
        "--stage",
        "gold-sample",
        "--json",
        cwd=ROOT,
    )
    if gold_sample.get("ok") is not True:
        raise AssertionError(f"Expected gold sample to pass before bulk generation: {gold_sample}")
    paper_v0 = run_student_script(
        "exam_prep_check.py",
        str(vault),
        "--course",
        "linear-algebra",
        "--exam-scope",
        "期末",
        "--stage",
        "paper-v0",
        "--json",
        cwd=ROOT,
    )
    if paper_v0.get("ok") is not True:
        raise AssertionError(f"Expected paper-v0 to pass before cross-paper synthesis: {paper_v0}")

    final_before_backfill = run_student_script(
        "exam_prep_check.py",
        str(vault),
        "--course",
        "linear-algebra",
        "--exam-scope",
        "期末",
        "--stage",
        "final",
        "--json",
        cwd=ROOT,
        expect_ok=False,
    )
    codes = {issue["code"] for issue in final_before_backfill.get("issues", []) if isinstance(issue, dict)}
    if "paper-deep-dive-missing-cross-paper-backfill" not in codes:
        raise AssertionError(f"Final stage should fail before cross-paper backfill: {final_before_backfill}")

    add_cross_paper_backfill(vault)

    synthesis = run_student_script(
        "exam_prep_check.py",
        str(vault),
        "--course",
        "linear-algebra",
        "--exam-scope",
        "期末",
        "--stage",
        "synthesis",
        "--json",
        cwd=ROOT,
    )
    if synthesis.get("ok") is not True:
        raise AssertionError(f"Expected synthesis stage to pass with card-backed analysis: {synthesis}")

    type_dossier = run_student_script(
        "exam_prep_check.py",
        str(vault),
        "--course",
        "linear-algebra",
        "--exam-scope",
        "期末",
        "--stage",
        "type-dossier",
        "--json",
        cwd=ROOT,
    )
    if type_dossier.get("ok") is not True:
        raise AssertionError(f"Expected type-dossier stage to pass with past-paper candidates: {type_dossier}")

    ok = run_student_script(
        "exam_prep_check.py",
        str(vault),
        "--course",
        "linear-algebra",
        "--exam-scope",
        "期末",
        "--stage",
        "final",
        "--json",
        "--write-report",
        cwd=ROOT,
    )
    if ok.get("ok") is not True:
        raise AssertionError(f"Expected completed AI artifacts to pass mechanical check: {ok}")
    if ok.get("tripwire_only") is not True or ok.get("reader_audit_required") is not True or ok.get("delivery_allowed_by_script") is not False:
        raise AssertionError(f"Final check must identify itself as a tripwire-only check requiring reader audit: {ok}")
    for field, expected in (
        ("subagent_drafts_reviewed", False),
        ("mechanical_tripwire_passed", True),
        ("reader_audit_passed", False),
        ("math_human_verified", False),
    ):
        if ok.get(field) is not expected:
            raise AssertionError(f"Final check must report reader-audit/subagent responsibility fields: {ok}")
    report = vault / ".student-os" / "state" / "exam-prep" / "linear-algebra" / "期末" / "quality-report.json"
    if not report.exists():
        raise AssertionError("exam_prep_check.py --write-report should write quality-report.json")

    broken = vault / "courses" / "linear-algebra" / "reviews" / "期末" / "题型解析" / "01-matrix-equation.md"
    text = broken.read_text(encoding="utf-8")
    broken.write_text(text + "\n坏公式：$ x $\n", encoding="utf-8", newline="\n")
    fail = run_student_script(
        "exam_prep_check.py",
        str(vault),
        "--course",
        "linear-algebra",
        "--exam-scope",
        "期末",
        "--stage",
        "final",
        "--json",
        cwd=ROOT,
        expect_ok=False,
    )
    codes = {issue["code"] for issue in fail.get("issues", []) if isinstance(issue, dict)}
    if "render-risk" not in codes:
        raise AssertionError(f"Render-unsafe AI artifacts must fail quality check: {fail}")


def verify_scope_specific_pack_names(tmp_root: Path) -> None:
    vault = tmp_root / "vault"
    papers = build_fixture(vault)
    midterm = "\u671f\u4e2d"
    payload = run_student_script(
        "exam_prep_build.py",
        str(vault),
        "--course",
        "linear-algebra",
        "--exam-scope",
        midterm,
        "--papers-dir",
        str(papers),
        "--json",
        cwd=ROOT,
    )
    pack_names = {path.name for path in vault.rglob("*考试备考指南.md")} | {path.name for path in vault.rglob("*公式总卡.md")} | {path.name for path in vault.rglob("*答题模板速查.md")}
    expected = {f"{midterm}考试备考指南.md", f"{midterm}公式总卡.md", f"{midterm}答题模板速查.md"}
    if not expected <= pack_names:
        raise AssertionError(f"Exam-prep build should use scope-specific prep pack names: {payload}; found={pack_names}")
    if any(path.name == "期末考试备考指南.md" for path in vault.rglob("*考试备考指南.md")):
        raise AssertionError("期中 prep workspace must not initialize a 期末 guide filename")


def verify_type_dossier_rejects_bad_refs_and_overlap(tmp_root: Path) -> None:
    vault, _ = verify_init_and_initial_failure(tmp_root)
    write_ai_outputs(vault)
    dossier_path = vault / ".student-os" / "state" / "exam-prep" / "linear-algebra" / "期末" / "type-dossiers" / "matrix-equation.json"
    dossier = json.loads(dossier_path.read_text(encoding="utf-8"))
    dossier["worked_example_candidates"].append({"question_ref": "missing-card.json#一"})
    dossier["self_test_candidates"].append({"question_ref": dossier["worked_example_candidates"][0]["question_ref"]})
    write_json(dossier_path, dossier)
    fail = run_student_script(
        "exam_prep_check.py",
        str(vault),
        "--course",
        "linear-algebra",
        "--exam-scope",
        "期末",
        "--stage",
        "type-dossier",
        "--json",
        cwd=ROOT,
        expect_ok=False,
    )
    codes = {issue["code"] for issue in fail.get("issues", []) if isinstance(issue, dict)}
    required = {"type-dossier-unknown-question-ref", "type-dossier-example-selftest-overlap"}
    if not required <= codes:
        raise AssertionError(f"Bad dossier refs/overlap should fail: {fail}")


def verify_type_analysis_rejects_fabricated_and_duplicate_sources(tmp_root: Path) -> None:
    vault, _ = verify_init_and_initial_failure(tmp_root)
    write_ai_outputs(vault)
    for path in (vault / "courses" / "linear-algebra" / "reviews" / "期末" / "试卷精析").glob("*.md"):
        text = path.read_text(encoding="utf-8")
        path.write_text(text + "\n## 跨卷关系\n\n原题复现：依据 2024-2025 期末 · 一 和 2025-2026 期末 · 一 判断同型变式。\n", encoding="utf-8", newline="\n")
    type_page = vault / "courses" / "linear-algebra" / "reviews" / "期末" / "题型解析" / "01-matrix-equation.md"
    text = type_page.read_text(encoding="utf-8")
    text = text.replace("2025-2026 期末 · 一", "2024-2025 期末 · 一", 1)
    text += "\n补充：禁止出现的自编题。\n"
    type_page.write_text(text, encoding="utf-8", newline="\n")
    fail = run_student_script(
        "exam_prep_check.py",
        str(vault),
        "--course",
        "linear-algebra",
        "--exam-scope",
        "期末",
        "--stage",
        "final",
        "--json",
        cwd=ROOT,
        expect_ok=False,
    )
    codes = {issue["code"] for issue in fail.get("issues", []) if isinstance(issue, dict)}
    required = {"type-analysis-example-selftest-overlap", "type-analysis-fabricated-question"}
    if not required <= codes:
        raise AssertionError(f"Fabricated or duplicated type-analysis questions should fail: {fail}")


def verify_type_analysis_rejects_unlearnable_shell(tmp_root: Path) -> None:
    vault, _ = verify_init_and_initial_failure(tmp_root)
    write_ai_outputs(vault)
    for path in (vault / "courses" / "linear-algebra" / "reviews" / "期末" / "试卷精析").glob("*.md"):
        text = path.read_text(encoding="utf-8")
        path.write_text(text + "\n## 跨卷关系\n\n原题复现：依据 2024-2025 期末 · 一 和 2025-2026 期末 · 一 判断同型变式。\n", encoding="utf-8", newline="\n")
    type_page = vault / "courses" / "linear-algebra" / "reviews" / "期末" / "题型解析" / "01-matrix-equation.md"
    type_page.write_text(
        "---\ntype: exam-type-analysis\ncourse: linear-algebra\nexam_scope: 期末\nexam_type_id: matrix-equation\nquality: ready\nstatus: active\nreview_scope: exam-prep\n---\n\n"
        "# 题型一：矩阵方程\n\n"
        "频率：9 道；代表年份：2024、2025；复习优先级：P0；同型变式集中。\n\n"
        "## 考前速记\n\n先圈出对象，不要急着代数展开。\n\n"
        "## 符号\n\n$A$、$X$、$B$ 表示矩阵。\n\n"
        "## 核心概念\n\n参考课本 §2。\n\n"
        "## 核心方法\n\n调用对应方法卡。\n\n"
        "## 例题\n\n来源：2024-final.json#一。题目摘录：矩阵方程往年题 1。完整解析：答案以来源为准。\n\n"
        "## 自测\n\n来源：2025-final.json#一。题目：完成往年卷自测 1。提示：看来源。\n\n"
        "## 自测答案\n\n答案以来源为准。\n\n"
        "## 快速得分\n\n写公式。\n\n"
        "## 易错\n\n注意。\n\n"
        "## 来源\n\n来源：2024-final.json#一、2025-final.json#一。\n",
        encoding="utf-8",
        newline="\n",
    )
    fail = run_student_script(
        "exam_prep_check.py",
        str(vault),
        "--course",
        "linear-algebra",
        "--exam-scope",
        "期末",
        "--stage",
        "final",
        "--json",
        cwd=ROOT,
        expect_ok=False,
    )
    codes = {issue["code"] for issue in fail.get("issues", []) if isinstance(issue, dict)}
    required = {
        "type-analysis-low-quality-phrase",
        "type-analysis-missing-textbook-grounding",
        "type-analysis-missing-full-worked-problem",
        "type-analysis-missing-full-self-test-problem",
    }
    if not required <= codes:
        raise AssertionError(f"Unlearnable source-link shell should fail: {fail}")


def verify_type_analysis_rejects_batch_generated_garbage(tmp_root: Path) -> None:
    vault, _ = verify_init_and_initial_failure(tmp_root)
    write_ai_outputs(vault)
    add_cross_paper_backfill(vault)
    type_page = vault / "courses" / "linear-algebra" / "reviews" / "期末" / "题型解析" / "01-matrix-equation.md"
    repeated_solution = (
        "完整解析：看到题干后先判入口，根据关键词确定本题属于本题型。"
        "使用本页核心方法中最匹配的一条，把题目给出的矩阵、向量或参数代入，按本页模板核算最终数值。"
    )
    type_page.write_text(
        "---\ntype: exam-type-analysis\ncourse: linear-algebra\nexam_scope: 期末\nexam_type_id: matrix-equation\nexam_type_name: 矩阵方程\nquality: ready\nstatus: active\nreview_scope: exam-prep\n---\n\n"
        "# 题型一：矩阵方程\n\n"
        "频率：9 道；代表年份：2024、2025；复习优先级：P0；原题复现暂未确认，同型变式集中。\n\n"
        "## 考前速记\n\n看到 $AX=B$，先判断未知矩阵的位置。\n\n"
        "## 符号\n\n| 符号 | 意思 | 课本依据 |\n| --- | --- | --- |\n| $A^{-1}$ | 逆矩阵 | 课本 §2.3.1 逆矩阵定义 |\n\n"
        "## 核心概念\n\n课本 §2.3.1 说明逆矩阵可用于消去左侧可逆矩阵。做题时先判断乘法方向。\n\n"
        "## 2 分钟下笔模板\n\n先判未知矩阵在左还是右，再列消元方向，再代入。\n\n"
        "## 核心方法\n\n看到矩阵方程就选择左乘或右乘。\n\n"
        "## 例题精讲\n\n"
        "### 例题 1（来源：2024-final.json#一）\n\n题目：## 一.计算题（12分）\n\n"
        f"{repeated_solution}\n\n"
        "### 例题 2（来源：2024-final.json#二）\n\n题目：设 $A$ 可逆且 $AX=B$，求 $X$。\n\n"
        f"{repeated_solution}\n\n"
        "## 自测题\n\n"
        "### 自测 1（来源：2025-final.json#一）\n\n题目：设 $A$ 可逆且 $AX=B$，求 $X$。提示：训练左乘消元。\n\n"
        "### 自测 2（来源：2025-final.json#二）\n\n题目：设 $XA=B$，求 $X$。提示：训练右乘消元。\n\n"
        "## 自测答案\n\n"
        "### 自测 1 答案\n\n答案：按本页模板核算，最终数值以同卷答案区为准。\n\n"
        "### 自测 2 答案\n\n答案：按本页模板核算，最终数值以同卷答案区为准。\n\n"
        "## 快速得分\n\n先写公式。\n\n"
        "## 易错\n\n注意左右乘顺序。\n\n"
        "## 来源\n\n来源：2024-final.json#一、2024-final.json#二、2025-final.json#一、2025-final.json#二。\n",
        encoding="utf-8",
        newline="\n",
    )
    fail = run_student_script(
        "exam_prep_check.py",
        str(vault),
        "--course",
        "linear-algebra",
        "--exam-scope",
        "期末",
        "--stage",
        "final",
        "--json",
        cwd=ROOT,
        expect_ok=False,
    )
    codes = {issue["code"] for issue in fail.get("issues", []) if isinstance(issue, dict)}
    required = {
        "human-markdown-machine-ref-leak",
        "type-analysis-template-worked-solution",
        "type-analysis-template-self-test-answer",
        "type-analysis-heading-only-problem",
        "type-analysis-repeated-worked-solution",
        "type-analysis-repeated-self-test-answer",
    }
    if not required <= codes:
        raise AssertionError(f"Batch-generated garbage type page should fail: {fail}")


def verify_human_markdown_rejects_broken_prose_join(tmp_root: Path) -> None:
    vault, _ = verify_init_and_initial_failure(tmp_root)
    write_ai_outputs(vault)
    add_cross_paper_backfill(vault)
    type_page = vault / "courses" / "linear-algebra" / "reviews" / "期末" / "题型解析" / "01-matrix-equation.md"
    text = type_page.read_text(encoding="utf-8")
    type_page.write_text(
        text + "\n拼接损坏示例：\\end**Transfer**：这一段是批量脚本把公式和段落标题粘在一起。\n",
        encoding="utf-8",
        newline="\n",
    )
    fail = run_student_script(
        "exam_prep_check.py",
        str(vault),
        "--course",
        "linear-algebra",
        "--exam-scope",
        "期末",
        "--stage",
        "final",
        "--json",
        cwd=ROOT,
        expect_ok=False,
    )
    codes = {issue["code"] for issue in fail.get("issues", []) if isinstance(issue, dict)}
    if "human-markdown-broken-prose-join" not in codes:
        raise AssertionError(f"Broken batch-patched prose joins should fail: {fail}")


def verify_subagent_contract_docs() -> None:
    skill = (ROOT / "student-os" / "SKILL.md").read_text(encoding="utf-8")
    command = (ROOT / "student-os" / "commands" / "exam-prep-build.md").read_text(encoding="utf-8")
    gold = (ROOT / "student-os" / "references" / "exam-prep-gold-standard.md").read_text(encoding="utf-8")
    context = (ROOT / "student-os" / "references" / "agent-runtime-context.md").read_text(encoding="utf-8")
    combined = "\n".join((skill, command, gold, context))
    required = ("subagent", "draft", "main agent", "reader audit", "batch regex", ".json#")
    missing = [marker for marker in required if marker not in combined]
    if missing:
        raise AssertionError(f"Exam-prep docs must encode subagent draft and main-agent audit contract, missing: {missing}")
    if "exported session logs" in command.lower() or "exported session logs" in skill.lower():
        raise AssertionError("Runtime skill docs must not require exported session logs as normal context")


def verify_context_and_legacy_census_docs() -> None:
    skill = (ROOT / "student-os" / "SKILL.md").read_text(encoding="utf-8")
    exam_prep = (ROOT / "student-os" / "commands" / "exam-prep-build.md").read_text(encoding="utf-8")
    context = (ROOT / "student-os" / "references" / "agent-runtime-context.md").read_text(encoding="utf-8")
    census = (ROOT / "student-os" / "references" / "exam-census-workflow.md").read_text(encoding="utf-8")
    census_command = (ROOT / "student-os" / "commands" / "exam-census.md").read_text(encoding="utf-8")
    claude_census = (ROOT / "student-os" / "integrations" / "claude" / "skills" / "exam-census" / "SKILL.md").read_text(encoding="utf-8")
    claude_command = (ROOT / "student-os" / "integrations" / "claude" / "commands" / "exam-census.md").read_text(encoding="utf-8")
    cursor_rule = (ROOT / "student-os" / "integrations" / "cursor" / "rules" / "exam-census.mdc").read_text(encoding="utf-8")
    github_copilot = (ROOT / "student-os" / "integrations" / "github" / "copilot-exam-census.md").read_text(encoding="utf-8")
    legacy_docs = "\n".join((census, census_command, claude_census, claude_command, cursor_rule, github_copilot)).lower()
    if "not the default route for high-quality" not in legacy_docs:
        raise AssertionError("Legacy exam-census docs must stop claiming high-quality study-pack default routing")
    if "ai-first exam prep" not in legacy_docs:
        raise AssertionError("Legacy exam-census docs must point high-quality prep requests to AI-first exam prep")
    if "high-quality study packs" not in skill:
        raise AssertionError("Main routing must send high-quality study-pack requests to AI-first exam prep")
    if "agent runtime context boundary" not in "\n".join((skill, exam_prep, context)).lower():
        raise AssertionError("Exam-prep docs must name the runtime context boundary")
    forbidden_context_claims = ("exported transcript", "session log path", "requires session log")
    combined_agent_docs = "\n".join((skill, exam_prep, context)).lower()
    leaked = [marker for marker in forbidden_context_claims if marker in combined_agent_docs]
    if leaked:
        raise AssertionError(f"Agent-facing docs should not imply unavailable context: {leaked}")


def verify_guide_rejects_artifact_list_only(tmp_root: Path) -> None:
    vault, _ = verify_init_and_initial_failure(tmp_root)
    write_ai_outputs(vault)
    add_cross_paper_backfill(vault)
    guide = vault / "courses" / "linear-algebra" / "reviews" / "期末" / "期末考试备考指南.md"
    guide.write_text(
        "---\ntype: exam-prep-guide\ncourse: linear-algebra\nexam_scope: 期末\nstatus: active\nreview_scope: exam-prep\n---\n\n"
        "# 线性代数期末考试备考指南\n\n"
        "## 完成内容\n\n"
        "- 36 份逐卷精析\n- 7 页题型解析\n- 5 份分析统计\n\n"
        "## 统计\n\n本资料包结构完整，issue_count: 0。\n",
        encoding="utf-8",
        newline="\n",
    )
    fail = run_student_script(
        "exam_prep_check.py",
        str(vault),
        "--course",
        "linear-algebra",
        "--exam-scope",
        "期末",
        "--stage",
        "final",
        "--json",
        cwd=ROOT,
        expect_ok=False,
    )
    codes = {issue["code"] for issue in fail.get("issues", []) if isinstance(issue, dict)}
    required = {"guide-missing-start-route", "guide-missing-study-route", "guide-artifact-list-only"}
    if not required <= codes:
        raise AssertionError(f"Artifact-list-only guide should fail: {fail}")


def verify_paper_v0_rejects_premature_repeat_claim(tmp_root: Path) -> None:
    vault, _ = verify_init_and_initial_failure(tmp_root)
    write_ai_outputs(vault)
    card = vault / ".student-os" / "state" / "exam-prep" / "linear-algebra" / "期末" / "paper-cards" / "2024-final.json"
    payload = json.loads(card.read_text(encoding="utf-8"))
    payload["questions"][0]["repeat_status"] = "original-repeat"
    write_json(card, payload)
    fail = run_student_script(
        "exam_prep_check.py",
        str(vault),
        "--course",
        "linear-algebra",
        "--exam-scope",
        "期末",
        "--stage",
        "paper-v0",
        "--json",
        cwd=ROOT,
        expect_ok=False,
    )
    codes = {issue["code"] for issue in fail.get("issues", []) if isinstance(issue, dict)}
    if "paper-card-premature-repeat-claim" not in codes:
        raise AssertionError(f"paper-v0 must reject premature original-repeat claims: {fail}")


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="student-os-exam-prep-eval-") as tmp:
        tmp_root = Path(tmp)
        verify_quality_pass_and_render_fail(tmp_root / "main")
        verify_scope_specific_pack_names(tmp_root / "scope-names")
        verify_type_dossier_rejects_bad_refs_and_overlap(tmp_root / "bad-dossier")
        verify_type_analysis_rejects_fabricated_and_duplicate_sources(tmp_root / "bad-type-page")
        verify_type_analysis_rejects_unlearnable_shell(tmp_root / "unlearnable-type-page")
        verify_type_analysis_rejects_batch_generated_garbage(tmp_root / "batch-garbage")
        verify_human_markdown_rejects_broken_prose_join(tmp_root / "broken-prose")
        verify_guide_rejects_artifact_list_only(tmp_root / "bad-guide")
        verify_paper_v0_rejects_premature_repeat_claim(tmp_root / "premature")
        verify_subagent_contract_docs()
        verify_context_and_legacy_census_docs()
    print("OK exam-prep-ai-first-evals")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

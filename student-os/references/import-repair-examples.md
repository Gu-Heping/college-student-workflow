# AI-assisted Import Repair Examples

These examples are sanitized patterns derived from real import failures. They are not course notes and do not replace source evidence.

## Text-only Repair Is Appropriate

- The current sidecar has readable question text, raw markdown exists, and the issue is local formatting noise such as unbalanced `$`, orphan `\nonumber`, or a promoted `## 一.` heading.
- The proposal may normalize markdown and KaTeX syntax, but it must preserve all question numbers and keep `verify_status: unverified`.

## Vision Evidence Is Required

- The sidecar says a proof, matrix, diagram, or full answer was reconstructed from an image, but the text contains placeholders such as `�`, `□`, repeated stray symbols, or missing mathematical structure.
- A text-only model must not invent the missing statement or proof. It should leave the item blocked as `requires-vision-evidence` or request a `vision-assisted` case with candidate page images.

## Answer Cross-check Is Required

- An answer sidecar begins with `解：`, `证明：`, or `答：` and has no visible problem stem.
- The proposal must use paired paper/answer evidence when available. If the paired paper or source PDF is unavailable, keep the proposal narrow and list remaining human-review risks.

## Proposal Requirements

Every proposal should include these markers before the replacement block:

```markdown
<!-- student-os-proposal-schema: import-repair-proposal/v1 -->
<!-- student-os-target: /absolute/path/to/sidecar.pdf.md -->
<!-- student-os-target-sha256: <hash copied from the case> -->
<!-- student-os-evidence-mode: text-only|ocr-assisted|vision-assisted -->
<!-- student-os-model-capability: text-only|vision -->
<!-- student-os-changed-sections: <section id or line range> -->
<!-- student-os-remaining-risks: human-review-required -->
```

Applying a proposal is still an automatic repair. It must result in `repair_status: auto-repaired` and `verify_status: unverified`.

export const meta = {
  name: 'exam-census',
  description:
    'Run the student-os exam-census pipeline: init, taxonomy, annotate, aggregate, fill, quality gate, multi-dim, deep-dive, prep pack, cross-validate.',
}

/**
 * Expected args (object or omitted):
 * {
 *   vault: string,        // absolute path to the learning vault (git root)
 *   course: string,       // course slug or path under courses/
 *   examScope: string,    // e.g. 期中 / midterm
 *   semester?: string,    // optional semester slug
 *   papersDir?: string,   // optional papers dir relative to vault
 *   skillScripts?: string // optional absolute path to student-os/scripts
 * }
 */
const input = typeof args === 'undefined' || args === null ? {} : args

const resolved = await agent(
  [
    'Resolve exam-census run parameters for a student-os vault.',
    'Return JSON only matching the schema.',
    `Provided args: ${JSON.stringify(input)}`,
    'Rules:',
    '- vault must be an absolute path to the target learning vault (never the student-os skill repo itself).',
    '- course and examScope are required.',
    '- semester may be empty string.',
    '- papersDir defaults to empty (script default under course references/).',
    '- skillScripts: prefer an installed student-os/scripts directory if known; else empty and discover later.',
    'If vault/course/examScope are missing, ask the user once via tools, then return the final values.',
  ].join('\n'),
  {
    label: 'resolve-args',
    schema: {
      type: 'object',
      required: ['vault', 'course', 'examScope', 'semester', 'papersDir', 'skillScripts'],
      properties: {
        vault: { type: 'string' },
        course: { type: 'string' },
        examScope: { type: 'string' },
        semester: { type: 'string' },
        papersDir: { type: 'string' },
        skillScripts: { type: 'string' },
      },
    },
  },
)

const vault = resolved.vault
const course = resolved.course
const examScope = resolved.examScope
const semester = resolved.semester || ''
const papersDir = resolved.papersDir || ''
const skillScripts = resolved.skillScripts || ''

const py = await agent(
  [
    'Locate student-os exam-census Python scripts for this machine.',
    `Preferred skillScripts hint: ${skillScripts || '(none)'}`,
    'Search common install locations (~/.claude/skills/student-os/scripts, ~/.codex/skills/student-os/scripts,',
    '~/.config/opencode/skills/student-os/scripts) and any student-os checkout nearby.',
    'Return the absolute directory that contains init_exam_census.py and build_exam_type_stats.py.',
  ].join('\n'),
  {
    label: 'locate-scripts',
    schema: {
      type: 'object',
      required: ['scriptsDir'],
      properties: { scriptsDir: { type: 'string' } },
    },
  },
)

const scriptsDir = py.scriptsDir
const script = (name) => JSON.stringify(`${scriptsDir.replace(/[\\/]+$/, '')}/${name}`)
const semesterFlag = semester ? ` --semester ${JSON.stringify(semester)}` : ''
const papersFlag = papersDir ? ` --papers-dir ${JSON.stringify(papersDir)}` : ''
const baseFlags = `${JSON.stringify(vault)} --course ${JSON.stringify(course)} --exam-scope ${JSON.stringify(examScope)}${semesterFlag}`

await agent(
  [
    'Phase Prepare (optional): if midterm/final PDFs under the course still lack usable .pdf.md sidecars,',
    `run python -B ${script('materials_convert.py')} with --repair on the papers directory. Skip if sidecars already look good.`,
    `Vault: ${vault}`,
    `Course: ${course}`,
    `Exam scope: ${examScope}`,
    `Scripts dir: ${JSON.stringify(scriptsDir)}`,
  ].join('\n'),
  { label: 'phase-prepare' },
)

await agent(
  [
    'Phase Init: run init_exam_census.py with overwrite only if the user already has a broken manifest.',
    'Prefer creating a fresh census when missing; do not wipe good annotations.',
    `Command shape: python -B ${script('init_exam_census.py')} ${baseFlags}${papersFlag}`,
    'Confirm manifest.json and taxonomy.yaml exist under .student-os/state/exam-census/.',
  ].join('\n'),
  { label: 'phase-init' },
)

await agent(
  [
    'Phase Taxonomy: draft or expand taxonomy.yaml from 2–3 representative paper sidecars.',
    'Use student-os templates/exam-type-taxonomy.md and references/exam-census-workflow.md.',
    'Keep existing type ids append-only. Prefer English-ish ids; names in course language.',
    `Vault: ${vault}; course: ${course}; examScope: ${examScope}; scripts: ${JSON.stringify(scriptsDir)}`,
  ].join('\n'),
  { label: 'phase-taxonomy' },
)

const batches = await agent(
  [
    'Read the exam-census manifest.json for this course/scope and return annotation batches.',
    `Vault: ${vault}; course: ${course}; examScope: ${examScope}; scripts: ${JSON.stringify(scriptsDir)}`,
    'Each batch item must include batch_id and papers (array of {stem, path}).',
    'If no batches field exists, split papers into groups of up to 6.',
  ].join('\n'),
  {
    label: 'load-batches',
    schema: {
      type: 'object',
      required: ['batches'],
      properties: {
        batches: {
          type: 'array',
          items: {
            type: 'object',
            required: ['batch_id', 'papers'],
            properties: {
              batch_id: { type: 'string' },
              papers: {
                type: 'array',
                items: {
                  type: 'object',
                  required: ['stem', 'path'],
                  properties: {
                    stem: { type: 'string' },
                    path: { type: 'string' },
                  },
                },
              },
            },
          },
        },
      },
    },
  },
)

await pipeline(batches.batches, (batch) =>
  agent(
    [
      `Phase Annotate batch ${batch.batch_id}: write one annotations/<stem>.json per paper.`,
      'Do not invent taxonomy ids. Mark uncertain papers with confidence: low.',
      'Skip files that already exist unless clearly corrupt.',
      `Vault: ${vault}; course: ${course}; examScope: ${examScope}`,
      `Papers: ${JSON.stringify(batch.papers)}`,
      'Follow student-os references/exam-census-workflow.md annotation contract.',
    ].join('\n'),
    { label: `annotate-${batch.batch_id}` },
  ),
)

const aggregate = await agent(
  [
    'Phase Aggregate: run build_exam_type_stats.py with --validate --overwrite.',
    `Command shape: python -B ${script('build_exam_type_stats.py')} ${baseFlags} --validate --overwrite`,
    'If the command exits non-zero, stop the census and summarize Validation failures.',
    'Return ok=true only when validate succeeded.',
  ].join('\n'),
  {
    label: 'phase-aggregate',
    schema: {
      type: 'object',
      required: ['ok', 'summary'],
      properties: {
        ok: { type: 'boolean' },
        summary: { type: 'string' },
      },
    },
  },
)

if (!aggregate.ok) {
  return {
    status: 'stopped',
    phase: 'aggregate',
    reason: aggregate.summary,
    vault,
    course,
    examScope,
  }
}

const fillQueue = await agent(
  [
    'Phase A queue: run fill_type_analysis.py and return the fill-queue items.',
    `Command shape: python -B ${script('fill_type_analysis.py')} ${baseFlags}`,
    'Return items as {path, exam_type_id, source_papers} arrays from fill-queue.json.',
  ].join('\n'),
  {
    label: 'phase-fill-queue',
    schema: {
      type: 'object',
      required: ['items'],
      properties: {
        items: {
          type: 'array',
          items: {
            type: 'object',
            required: ['path', 'exam_type_id'],
            properties: {
              path: { type: 'string' },
              exam_type_id: { type: 'string' },
              source_papers: { type: 'array', items: { type: 'string' } },
            },
          },
        },
      },
    },
  },
)

await pipeline(fillQueue.items, (item) =>
  agent(
    [
      `Phase A fill only for type ${item.exam_type_id}.`,
      `Fill ${item.path} to content-standard v2 (references/exam-census-quality.md).`,
      'Include zero-foundation entry four questions, badge, examples with 【方法引用】, self-tests with answers, verification steps.',
      `Source papers: ${JSON.stringify(item.source_papers || [])}`,
      'Do NOT run review_type_analysis.py here (global gate runs once after all fills).',
      `Vault: ${vault}; scripts: ${JSON.stringify(scriptsDir)}`,
    ].join('\n'),
    { label: `fill-${item.exam_type_id}` },
  ),
)

const gate = await agent(
  [
    'Phase B: run review_type_analysis.py once for the whole course/scope.',
    `Command: python -B ${script('review_type_analysis.py')} ${baseFlags}`,
    'Return type_needs_revision from quality-reviews.json (kind=type-analysis only; ignore analysis-report until after Phase C).',
  ].join('\n'),
  {
    label: 'phase-quality-gate',
    schema: {
      type: 'object',
      required: ['needs_revision'],
      properties: {
        needs_revision: {
          type: 'array',
          items: {
            type: 'object',
            required: ['path', 'exam_type_id'],
            properties: {
              path: { type: 'string' },
              exam_type_id: { type: 'string' },
              failed_checks: { type: 'array', items: { type: 'string' } },
            },
          },
        },
      },
    },
  },
)

if (gate.needs_revision.length) {
  await pipeline(gate.needs_revision, (item) =>
    agent(
      [
        `Phase B revision for ${item.exam_type_id} at ${item.path}.`,
        `Failed checks: ${JSON.stringify(item.failed_checks || [])}`,
        'Revise the page against exam-census-quality.md. At most two revision attempts total for this file.',
        'Chinese-first user text; short frontmatter only (no bulky source_artifacts / generated_fingerprint); table cells use $\\lvert A\\rvert$ not bare |A|.',
        'If evidence is thin, write 证据不足，需人工补充 and set quality: needs-review rather than leaving empty template sections.',
        'If still failing structural requirements, set frontmatter quality: needs-review and stop revising.',
        'Do NOT run review_type_analysis.py from this worker.',
        `Vault: ${vault}`,
      ].join('\n'),
      { label: `revise-${item.exam_type_id}` },
    ),
  )

  await agent(
    [
      'Phase B re-check: run review_type_analysis.py once more after type-page revisions.',
      `Command: python -B ${script('review_type_analysis.py')} ${baseFlags}`,
      'Summarize remaining type_needs_revision files (ignore analysis-report until Phase C).',
    ].join('\n'),
    { label: 'phase-quality-recheck' },
  )
}

await agent(
  [
    'Phase C: run build_multi_dim_stats.py with --overwrite.',
    `Command: python -B ${script('build_multi_dim_stats.py')} ${baseFlags} --overwrite`,
    'Then refine analysis drafts under reviews/<scope>/analysis/ if annotations include useful format/difficulty fields.',
    'User-facing analysis Markdown must stay Chinese-first (no Seeded from / Paper | Reliability / unspecified).',
  ].join('\n'),
  { label: 'phase-multi-dim' },
)

const analysisGate = await agent(
  [
    'Phase C quality recheck: run review_type_analysis.py again after multi-dim drafts exist.',
    `Command: python -B ${script('review_type_analysis.py')} ${baseFlags}`,
    'Return analysis_needs_revision from quality-reviews.json (kind=analysis-report).',
  ].join('\n'),
  {
    label: 'phase-analysis-quality-gate',
    schema: {
      type: 'object',
      required: ['analysis_needs_revision'],
      properties: {
        analysis_needs_revision: {
          type: 'array',
          items: {
            type: 'object',
            required: ['path'],
            properties: {
              path: { type: 'string' },
              failed_checks: { type: 'array', items: { type: 'string' } },
            },
          },
        },
      },
    },
  },
)

if (analysisGate.analysis_needs_revision.length) {
  await pipeline(analysisGate.analysis_needs_revision, (item) =>
    agent(
      [
        `Phase C analysis revision for ${item.path}.`,
        `Failed checks: ${JSON.stringify(item.failed_checks || [])}`,
        'Fix Chinese residue, table pipe escapes, and other analysis-report issues. Do not invent taxonomy.',
        'Do NOT run review_type_analysis.py from this worker.',
        `Vault: ${vault}`,
      ].join('\n'),
      { label: `revise-analysis-${String(item.path).split('/').pop()}` },
    ),
  )
}

await agent(
  [
    'Phase D: run init_exam_deep_dive.py --limit 2 --overwrite, then fill the scaffolded 真题精析 pages.',
    `Command: python -B ${script('init_exam_deep_dive.py')} ${baseFlags} --limit 2 --overwrite`,
    'Each question must link back to a type-analysis page.',
  ].join('\n'),
  { label: 'phase-deep-dive' },
)

await agent(
  [
    'Phase Prep pack: create/update 备考指南.md, 公式总卡.md, 答题模板速查.md, 考前1小时清单.md',
    'under courses/<course-key>/reviews/<exam-scope-key>/ using student-os templates.',
    'Prefer extracting formulas/templates from filled type-analysis pages.',
    'Link recommended types with real Markdown links to 题型解析/*.md.',
    `Vault: ${vault}; course: ${course}; examScope: ${examScope}`,
  ].join('\n'),
  { label: 'phase-prep-pack' },
)

const cross = await agent(
  [
    'Phase E: run cross_validate_exam_census.py and report ok/failures.',
    `Command: python -B ${script('cross_validate_exam_census.py')} ${baseFlags}`,
    'Return ok and a short summary of any gaps.',
  ].join('\n'),
  {
    label: 'phase-cross-validate',
    schema: {
      type: 'object',
      required: ['ok', 'summary'],
      properties: {
        ok: { type: 'boolean' },
        summary: { type: 'string' },
      },
    },
  },
)

return {
  status: cross.ok ? 'completed' : 'completed_with_gaps',
  vault,
  course,
  examScope,
  semester,
  scriptsDir,
  aggregate: aggregate.summary,
  crossValidation: cross.summary,
}

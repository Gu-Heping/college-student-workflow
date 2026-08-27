import { spawn } from 'node:child_process'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'
import { homedir } from 'node:os'
import type { Context } from '@deepseek-ai/cordis'
import { defineTool, type JsonValue } from '@deepseek-ai/dsh-tools'
import type {} from '@deepseek-ai/dsh-system-prompt'

export const name = 'student-os'
export const inject = ['tools', 'systemPrompt']

export interface Config {
  repoRoot?: string
  python?: string
  timeoutMs?: number
}

export interface StudentOsToolResult {
  ok: boolean
  exitCode: number | null
  cwd: string
  command: string[]
  stdout: string
  stderr: string
  stage?: string
  signal?: string
  payload?: JsonValue
}

interface ScriptRunOptions {
  repoRoot?: string
  python?: string
  timeoutMs?: number
  signal: AbortSignal
}

const moduleDir = dirname(fileURLToPath(import.meta.url))

const toolResultSchema = {
  type: 'object',
  additionalProperties: false,
  properties: {
    ok: { type: 'boolean', required: true },
    exitCode: { oneOf: [{ type: 'integer' }, { type: 'null' }], required: true },
    cwd: { type: 'string', required: true },
    command: { type: 'array', required: true, items: { type: 'string' } },
    stdout: { type: 'string', required: true },
    stderr: { type: 'string', required: true },
    stage: { type: 'string' },
    signal: { type: 'string' },
    payload: { type: 'json' },
  },
} as const

export function resolveRepoRoot(configured?: string): string {
  const explicit = configured ?? process.env.STUDENT_OS_REPO_ROOT
  return explicit === undefined || explicit.trim() === ''
    ? resolve(moduleDir, '..', '..', '..')
    : resolveUserPath(explicit)
}

function resolveUserPath(input: string, base: string = process.cwd()): string {
  if (input === '~') return homedir()
  if (input.startsWith('~/') || input.startsWith('~\\')) {
    return resolve(homedir(), input.slice(2))
  }
  return resolve(base, input)
}

function requireString(value: unknown, name: string, fallback?: string): string {
  if (value === undefined) {
    if (fallback !== undefined) return fallback
    throw new Error(`${name} is required`)
  }
  if (typeof value !== 'string' || value.trim() === '') {
    throw new Error(`${name} must be a non-empty string`)
  }
  return value
}

function parsePayload(stdout: string): JsonValue | undefined {
  const text = stdout.trim()
  if (text === '') return undefined
  try {
    return JSON.parse(text) as JsonValue
  } catch {
    return undefined
  }
}

function pythonCommand(configured?: string): string {
  if (configured !== undefined && configured.trim() !== '') return configured
  if (process.env.PYTHON !== undefined && process.env.PYTHON.trim() !== '') return process.env.PYTHON
  return process.platform === 'win32' ? 'python' : 'python3'
}

export function runStudentOsScript(
  scriptName: string,
  args: string[],
  options: ScriptRunOptions,
): Promise<StudentOsToolResult> {
  const repoRoot = resolveRepoRoot(options.repoRoot)
  const scriptPath = resolve(repoRoot, 'student-os', 'scripts', scriptName)
  const command = [pythonCommand(options.python), scriptPath, ...args]
  const timeoutMs = Math.max(1, options.timeoutMs ?? 45_000)

  return new Promise((resolveResult, reject) => {
    let settled = false
    let timedOut = false
    const child = spawn(command[0], command.slice(1), {
      cwd: repoRoot,
      stdio: ['ignore', 'pipe', 'pipe'],
      windowsHide: true,
    })
    const stdoutChunks: Buffer[] = []
    const stderrChunks: Buffer[] = []

    const abort = () => child.kill()
    const timeout = setTimeout(() => {
      timedOut = true
      child.kill()
    }, timeoutMs)
    options.signal.addEventListener('abort', abort, { once: true })
    child.stdout.on('data', chunk => stdoutChunks.push(Buffer.from(chunk)))
    child.stderr.on('data', chunk => stderrChunks.push(Buffer.from(chunk)))
    child.on('error', error => {
      options.signal.removeEventListener('abort', abort)
      clearTimeout(timeout)
      if (!settled) {
        settled = true
        reject(error)
      }
    })
    child.on('close', (code, signal) => {
      options.signal.removeEventListener('abort', abort)
      clearTimeout(timeout)
      if (settled) return
      settled = true
      const stdout = Buffer.concat(stdoutChunks).toString('utf8')
      const stderr = Buffer.concat(stderrChunks).toString('utf8')
      if (timedOut) {
        resolveResult({
          ok: false,
          exitCode: null,
          cwd: repoRoot,
          command,
          stdout,
          stderr,
          stage: 'timeout',
          signal: signal ?? 'SIGTERM',
        })
        return
      }
      if (options.signal.aborted) {
        resolveResult({
          ok: false,
          exitCode: null,
          cwd: repoRoot,
          command,
          stdout,
          stderr,
          stage: 'aborted',
          signal: signal ?? 'SIGTERM',
        })
        return
      }
      const payload = parsePayload(stdout)
      resolveResult({
        ok: code === 0,
        exitCode: code,
        cwd: repoRoot,
        command,
        stdout,
        stderr,
        ...signal === null ? {} : { signal },
        ...payload === undefined ? {} : { payload },
      })
    })
  })
}

function renderResult(toolName: string, value: StudentOsToolResult): { type: 'text'; text: string }[] {
  const header = value.ok
    ? `${toolName} completed with exit code 0.`
    : value.exitCode === null
      ? `${toolName} ended without an exit code${value.signal === undefined ? '' : ` (${value.signal})`}.`
      : `${toolName} failed with exit code ${value.exitCode}.`
  return [{
    type: 'text',
    text: [
      header,
      `cwd: ${value.cwd}`,
      `command: ${value.command.join(' ')}`,
      value.stdout.trim() === '' ? '' : `stdout:\n${value.stdout.trim()}`,
      value.stderr.trim() === '' ? '' : `stderr:\n${value.stderr.trim()}`,
    ].filter(Boolean).join('\n\n'),
  }]
}

export function apply(ctx: Context, config: Config = {}): void {
  ctx.systemPrompt?.section({
    name: 'student-os',
    order: 118,
    text: [
      'Before modifying a Student OS managed vault, run a compact preflight appropriate to the task.',
      'For imported markdown repair, prefer student_os_group_changes or the repair queue instead of a full-vault inspect.',
      'Do not automatically commit or push Student OS vault changes.',
      'External publication must use the Student OS privacy flow.',
    ].join('\n'),
  })

  ctx.tools.register(defineTool({
    name: 'student_os_inspect',
    description: 'Inspect a Student OS vault using the portable Python inspect_repo.py script.',
    parameters: {
      vault: { type: 'string', description: 'Vault root to inspect. Defaults to the DSH process cwd.' },
      compact: { type: 'boolean', description: 'Use compact agent-facing output. Defaults to true.' },
      limit: { type: 'integer', description: 'Maximum sample items in compact output. Defaults to 20.' },
      scope: { type: 'string', enum: ['repo', 'git', 'hygiene'], description: 'Inspection scope. Defaults to hygiene.' },
      timeout_ms: { type: 'integer', description: 'Timeout in milliseconds. Defaults to 45000.' },
    },
    output: {
      schema: toolResultSchema,
      render: (_args, value) => renderResult('student_os_inspect', value),
    },
    isConcurrencySafe: () => true,
    execute(args, exec) {
      const vault = resolveUserPath(requireString(args.vault, 'vault', '.'))
      const compact = args.compact !== false
      const limit = typeof args.limit === 'number' && Number.isFinite(args.limit) ? Math.max(1, Math.trunc(args.limit)) : 20
      const scope = typeof args.scope === 'string' && ['repo', 'git', 'hygiene'].includes(args.scope) ? args.scope : 'hygiene'
      const timeoutMs = typeof args.timeout_ms === 'number' && Number.isFinite(args.timeout_ms)
        ? Math.max(1, Math.trunc(args.timeout_ms))
        : config.timeoutMs
      const scriptArgs = [vault, '--scope', scope, '--limit', String(limit)]
      if (compact) scriptArgs.push('--compact-json')
      else scriptArgs.push('--full-json')
      return runStudentOsScript('inspect_repo.py', scriptArgs, { ...config, timeoutMs, signal: exec.signal })
    },
  }))

  ctx.tools.register(defineTool({
    name: 'student_os_group_changes',
    description: 'Group git changes in a Student OS vault using the portable Python group_git_changes.py script.',
    parameters: {
      vault: { type: 'string', description: 'Vault root to analyze. Defaults to the DSH process cwd.' },
      compact: { type: 'boolean', description: 'Use compact preflight output. Defaults to true.' },
      limit: { type: 'integer', description: 'Maximum sample paths in compact output. Defaults to 20.' },
    },
    output: {
      schema: toolResultSchema,
      render: (_args, value) => renderResult('student_os_group_changes', value),
    },
    isConcurrencySafe: () => true,
    execute(args, exec) {
      const vault = resolveUserPath(requireString(args.vault, 'vault', '.'))
      const compact = args.compact !== false
      const limit = typeof args.limit === 'number' && Number.isFinite(args.limit) ? Math.max(1, Math.trunc(args.limit)) : 20
      const scriptArgs = [vault]
      if (compact) scriptArgs.push('--compact-json', '--limit', String(limit))
      return runStudentOsScript('group_git_changes.py', scriptArgs, { ...config, signal: exec.signal })
    },
  }))

  ctx.tools.register(defineTool({
    name: 'student_os_frontmatter',
    description: 'Add missing Student OS frontmatter to imported markdown sidecars using ensure_frontmatter.py.',
    parameters: {
      path: { type: 'string', required: true, description: 'File or directory to scan.' },
      apply: { type: 'boolean', description: 'Write changes when true; otherwise dry-run.' },
      include_raw: { type: 'boolean', description: 'Also process *.raw.md files.' },
      course: { type: 'string', description: 'Optional course name to write into frontmatter.' },
      status: { type: 'string', description: 'Frontmatter status. Defaults to active in the Python script.' },
    },
    output: {
      schema: toolResultSchema,
      render: (_args, value) => renderResult('student_os_frontmatter', value),
    },
    isConcurrencySafe(args) {
      return args.apply !== true
    },
    execute(args, exec) {
      const target = resolveUserPath(requireString(args.path, 'path'))
      const scriptArgs = [args.apply === true ? '--apply' : '--dry-run', '--json']
      if (args.include_raw === true) scriptArgs.push('--include-raw')
      if (args.course !== undefined) scriptArgs.push('--course', requireString(args.course, 'course'))
      if (args.status !== undefined) scriptArgs.push('--status', requireString(args.status, 'status'))
      scriptArgs.push(target)
      return runStudentOsScript('ensure_frontmatter.py', scriptArgs, { ...config, signal: exec.signal })
    },
  }))
}

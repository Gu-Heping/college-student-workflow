import { spawn } from 'node:child_process'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'
import { homedir } from 'node:os'

export const name = 'student-os'
export const inject = ['tools', 'systemPrompt']

type JsonValue = null | boolean | number | string | JsonValue[] | { [key: string]: JsonValue }

interface ToolExecution {
  signal: AbortSignal
}

interface ToolDefinition {
  name: string
  description: string
  parameters: Record<string, unknown>
  output: {
    schema: Record<string, unknown>
    render(args: unknown, value: StudentOsToolResult): { type: 'text'; text: string }[]
  }
  execute(args: Record<string, unknown>, exec: ToolExecution): Promise<StudentOsToolResult>
  isConcurrencySafe?(args: unknown): boolean
}

interface CordisContext {
  tools: {
    register(definition: ToolDefinition): unknown
  }
  systemPrompt?: {
    section(section: { name: string; order: number; text: string }): unknown
  }
}

export interface Config {
  repoRoot?: string
  python?: string
}

export interface StudentOsToolResult {
  ok: boolean
  exitCode: number
  cwd: string
  command: string[]
  stdout: string
  stderr: string
  payload?: JsonValue
}

interface ScriptRunOptions {
  repoRoot?: string
  python?: string
  signal: AbortSignal
}

const moduleDir = dirname(fileURLToPath(import.meta.url))

const toolResultSchema = {
  type: 'object',
  additionalProperties: false,
  properties: {
    ok: { type: 'boolean', required: true },
    exitCode: { type: 'integer', required: true },
    cwd: { type: 'string', required: true },
    command: { type: 'array', required: true, items: { type: 'string' } },
    stdout: { type: 'string', required: true },
    stderr: { type: 'string', required: true },
    payload: { type: 'json' },
  },
}

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

  return new Promise((resolveResult, reject) => {
    const child = spawn(command[0], command.slice(1), {
      cwd: repoRoot,
      stdio: ['ignore', 'pipe', 'pipe'],
      windowsHide: true,
    })
    const stdoutChunks: Buffer[] = []
    const stderrChunks: Buffer[] = []

    const abort = () => child.kill()
    options.signal.addEventListener('abort', abort, { once: true })
    child.stdout.on('data', chunk => stdoutChunks.push(Buffer.from(chunk)))
    child.stderr.on('data', chunk => stderrChunks.push(Buffer.from(chunk)))
    child.on('error', error => {
      options.signal.removeEventListener('abort', abort)
      reject(error)
    })
    child.on('close', code => {
      options.signal.removeEventListener('abort', abort)
      const stdout = Buffer.concat(stdoutChunks).toString('utf8')
      const stderr = Buffer.concat(stderrChunks).toString('utf8')
      const exitCode = code ?? 1
      const payload = parsePayload(stdout)
      resolveResult({
        ok: exitCode === 0,
        exitCode,
        cwd: repoRoot,
        command,
        stdout,
        stderr,
        ...payload === undefined ? {} : { payload },
      })
    })
  })
}

function renderResult(toolName: string, value: StudentOsToolResult): { type: 'text'; text: string }[] {
  const header = value.ok
    ? `${toolName} completed with exit code 0.`
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

function registerScriptTool(
  ctx: CordisContext,
  definition: Omit<ToolDefinition, 'output' | 'isConcurrencySafe'>,
): void {
  ctx.tools.register({
    ...definition,
    output: {
      schema: toolResultSchema,
      render: (_args, value) => renderResult(definition.name, value),
    },
    isConcurrencySafe: () => true,
  })
}

export function apply(ctx: CordisContext, config: Config = {}): void {
  ctx.systemPrompt?.section({
    name: 'student-os',
    order: 118,
    text: [
      'Before modifying a Student OS managed vault, inspect it with student_os_inspect.',
      'Do not automatically commit or push Student OS vault changes.',
      'External publication must use the Student OS privacy flow.',
    ].join('\n'),
  })

  registerScriptTool(ctx, {
    name: 'student_os_inspect',
    description: 'Inspect a Student OS vault using the portable Python inspect_repo.py script.',
    parameters: {
      vault: { type: 'string', description: 'Vault root to inspect. Defaults to the DSH process cwd.' },
    },
    execute(args, exec) {
      const vault = resolveUserPath(requireString(args.vault, 'vault', '.'))
      return runStudentOsScript('inspect_repo.py', [vault], { ...config, signal: exec.signal })
    },
  })

  registerScriptTool(ctx, {
    name: 'student_os_group_changes',
    description: 'Group git changes in a Student OS vault using the portable Python group_git_changes.py script.',
    parameters: {
      vault: { type: 'string', description: 'Vault root to analyze. Defaults to the DSH process cwd.' },
    },
    execute(args, exec) {
      const vault = resolveUserPath(requireString(args.vault, 'vault', '.'))
      return runStudentOsScript('group_git_changes.py', [vault], { ...config, signal: exec.signal })
    },
  })

  registerScriptTool(ctx, {
    name: 'student_os_frontmatter',
    description: 'Add missing Student OS frontmatter to imported markdown sidecars using ensure_frontmatter.py.',
    parameters: {
      path: { type: 'string', required: true, description: 'File or directory to scan.' },
      apply: { type: 'boolean', description: 'Write changes when true; otherwise dry-run.' },
      include_raw: { type: 'boolean', description: 'Also process *.raw.md files.' },
      course: { type: 'string', description: 'Optional course name to write into frontmatter.' },
      status: { type: 'string', description: 'Frontmatter status. Defaults to active in the Python script.' },
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
  })
}

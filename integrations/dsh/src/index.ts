import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'
import { homedir } from 'node:os'
import { spawn, spawnSync } from 'node:child_process'
import type { Context } from '@deepseek-ai/cordis'
import { defineTool, type JsonValue } from '@deepseek-ai/dsh-tools'
import type {} from '@deepseek-ai/dsh-system-prompt'

export const name = 'student-os'
export const inject = ['tools', 'systemPrompt']

export interface Config {
  repoRoot?: string
  vaultRoot?: string
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
  plugin_version: string
  repo_commit: string
  repo_root: string
  vault?: string
  vault_resolution_source?: string
  stage?: string
  signal?: string
  payload?: JsonValue
}

interface ScriptRunOptions {
  repoRoot?: string
  python?: string
  timeoutMs?: number
  vault?: string
  vaultResolutionSource?: string
  signal: AbortSignal
}

const moduleDir = dirname(fileURLToPath(import.meta.url))
const pluginVersion = '0.1.0'
let repoCommitCache: string | undefined

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
    plugin_version: { type: 'string', required: true },
    repo_commit: { type: 'string', required: true },
    repo_root: { type: 'string', required: true },
    vault: { type: 'string' },
    vault_resolution_source: { type: 'string' },
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

function maybeString(value: unknown): string | undefined {
  return typeof value === 'string' && value.trim() !== '' ? value : undefined
}

function repoCommit(repoRoot: string): string {
  if (repoCommitCache !== undefined) return repoCommitCache
  const result = spawnSync('git', ['-C', repoRoot, 'rev-parse', '--short=12', 'HEAD'], {
    encoding: 'utf8',
    stdio: ['ignore', 'pipe', 'ignore'],
  })
  repoCommitCache = result.status === 0 && result.stdout.trim() !== '' ? result.stdout.trim() : 'unknown'
  return repoCommitCache
}

function baseResult(config: Config): Pick<StudentOsToolResult, 'plugin_version' | 'repo_commit' | 'repo_root'> {
  const repoRoot = resolveRepoRoot(config.repoRoot)
  return {
    plugin_version: pluginVersion,
    repo_commit: repoCommit(repoRoot),
    repo_root: repoRoot,
  }
}

function executionWorkspace(exec: unknown): string | undefined {
  if (exec === null || typeof exec !== 'object') return undefined
  const record = exec as Record<string, unknown>
  for (const key of ['cwd', 'workspace', 'workspaceRoot', 'workdir', 'workingDirectory']) {
    const value = maybeString(record[key])
    if (value !== undefined) return value
  }
  for (const key of ['session', 'meta', 'metadata']) {
    const nested = record[key]
    if (nested !== null && typeof nested === 'object') {
      const value = executionWorkspace(nested)
      if (value !== undefined) return value
    }
  }
  return undefined
}

function resolveVaultArg(value: unknown, exec: unknown, config: Config): { path: string; source: string } | StudentOsToolResult {
  const explicit = value === undefined ? undefined : requireString(value, 'vault')
  const configured = maybeString(config.vaultRoot)
  const envVault = maybeString(process.env.STUDENT_OS_VAULT_ROOT)
  const workspace = executionWorkspace(exec)
  const candidate = explicit ?? configured ?? envVault ?? workspace
  if (candidate === undefined) {
    const repoRoot = resolveRepoRoot(config.repoRoot)
    return {
      ok: false,
      exitCode: null,
      cwd: repoRoot,
      command: [],
      stdout: '',
      stderr: 'Student OS vault is required: DSH did not expose a reliable workspace cwd. Pass vault explicitly.',
      ...baseResult(config),
      stage: 'missing-vault',
    }
  }
  const source = explicit !== undefined
    ? 'argument'
    : configured !== undefined
      ? 'config.vaultRoot'
      : envVault !== undefined
        ? 'STUDENT_OS_VAULT_ROOT'
        : 'dsh-workspace'
  return { path: resolveUserPath(candidate), source }
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
      env: {
        ...process.env,
        PYTHONIOENCODING: 'utf-8',
        PYTHONUTF8: '1',
      },
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
          ...baseResult(options),
          ...options.vault === undefined ? {} : { vault: options.vault },
          ...options.vaultResolutionSource === undefined ? {} : { vault_resolution_source: options.vaultResolutionSource },
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
          ...baseResult(options),
          ...options.vault === undefined ? {} : { vault: options.vault },
          ...options.vaultResolutionSource === undefined ? {} : { vault_resolution_source: options.vaultResolutionSource },
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
        ...baseResult(options),
        ...options.vault === undefined ? {} : { vault: options.vault },
        ...options.vaultResolutionSource === undefined ? {} : { vault_resolution_source: options.vaultResolutionSource },
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
      `plugin: student-os ${value.plugin_version} (${value.repo_commit})`,
      `repo: ${value.repo_root}`,
      value.vault === undefined ? '' : `vault: ${value.vault} (${value.vault_resolution_source ?? 'unknown'})`,
      `command: ${value.command.join(' ')}`,
      value.stage === 'missing-vault' ? 'next: pass vault explicitly or restart DSH from the vault workspace with the Student OS overlay.' : '',
      value.stage === 'timeout' ? 'next: rerun with a narrower vault/folder or compact task-specific command.' : '',
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
      'For imported markdown repair, prefer student_os_repair_import_run for one Obsidian-visible local fix; use student_os_group_changes only as a compact preflight.',
      'After a Student OS repair proposal is applied, do not directly edit the target sidecar; create a follow-up proposal/review/apply if another defect appears.',
      'Do not automatically commit or push Student OS vault changes.',
      'External publication must use the Student OS privacy flow.',
    ].join('\n'),
  })

  ctx.tools.register(defineTool({
    name: 'student_os_inspect',
    description: 'Inspect a Student OS vault using the portable Python inspect_repo.py script.',
    parameters: {
      vault: { type: 'string', description: 'Vault root to inspect. Defaults to the DSH workspace cwd when available.' },
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
      const vault = resolveVaultArg(args.vault, exec, config)
      if ('ok' in vault) return Promise.resolve(vault)
      const compact = args.compact !== false
      const limit = typeof args.limit === 'number' && Number.isFinite(args.limit) ? Math.max(1, Math.trunc(args.limit)) : 20
      const scope = typeof args.scope === 'string' && ['repo', 'git', 'hygiene'].includes(args.scope) ? args.scope : 'hygiene'
      const timeoutMs = typeof args.timeout_ms === 'number' && Number.isFinite(args.timeout_ms)
        ? Math.max(1, Math.trunc(args.timeout_ms))
        : config.timeoutMs
      const scriptArgs = [vault.path, '--scope', scope, '--limit', String(limit)]
      if (compact) scriptArgs.push('--compact-json')
      else scriptArgs.push('--full-json')
      return runStudentOsScript('inspect_repo.py', scriptArgs, {
        ...config,
        timeoutMs,
        vault: vault.path,
        vaultResolutionSource: vault.source,
        signal: exec.signal,
      })
    },
  }))

  ctx.tools.register(defineTool({
    name: 'student_os_group_changes',
    description: 'Group git changes in a Student OS vault using the portable Python group_git_changes.py script.',
    parameters: {
      vault: { type: 'string', description: 'Vault root to analyze. Defaults to the DSH workspace cwd when available.' },
      compact: { type: 'boolean', description: 'Use compact preflight output. Defaults to true.' },
      limit: { type: 'integer', description: 'Maximum sample paths in compact output. Defaults to 20.' },
      timeout_ms: { type: 'integer', description: 'Timeout in milliseconds. Defaults to 45000.' },
    },
    output: {
      schema: toolResultSchema,
      render: (_args, value) => renderResult('student_os_group_changes', value),
    },
    isConcurrencySafe: () => true,
    execute(args, exec) {
      const vault = resolveVaultArg(args.vault, exec, config)
      if ('ok' in vault) return Promise.resolve(vault)
      const compact = args.compact !== false
      const limit = typeof args.limit === 'number' && Number.isFinite(args.limit) ? Math.max(1, Math.trunc(args.limit)) : 20
      const timeoutMs = typeof args.timeout_ms === 'number' && Number.isFinite(args.timeout_ms)
        ? Math.max(1, Math.trunc(args.timeout_ms))
        : config.timeoutMs
      const scriptArgs = [vault.path]
      if (compact) scriptArgs.push('--compact-json', '--limit', String(limit))
      return runStudentOsScript('group_git_changes.py', scriptArgs, {
        ...config,
        timeoutMs,
        vault: vault.path,
        vaultResolutionSource: vault.source,
        signal: exec.signal,
      })
    },
  }))

  ctx.tools.register(defineTool({
    name: 'student_os_repair_import_run',
    description: 'Run one guarded Student OS import markdown repair using repair_import_run.py, with review and rollback.',
    parameters: {
      vault: { type: 'string', description: 'Vault, folder, or markdown sidecar to repair. Defaults to the DSH workspace cwd when available.' },
      dryRun: { type: 'boolean', description: 'Prepare and review the repair without modifying the target.' },
      limit: { type: 'integer', description: 'Maximum repairs. Defaults to 1; the Python runner currently supports only 1.' },
      timeout_ms: { type: 'integer', description: 'Timeout in milliseconds. Defaults to 45000.' },
    },
    output: {
      schema: toolResultSchema,
      render: (_args, value) => renderResult('student_os_repair_import_run', value),
    },
    isConcurrencySafe(args) {
      return args.dryRun === true
    },
    execute(args, exec) {
      const vault = resolveVaultArg(args.vault, exec, config)
      if ('ok' in vault) return Promise.resolve(vault)
      const limit = typeof args.limit === 'number' && Number.isFinite(args.limit) ? Math.max(1, Math.trunc(args.limit)) : 1
      const timeoutMs = typeof args.timeout_ms === 'number' && Number.isFinite(args.timeout_ms)
        ? Math.max(1, Math.trunc(args.timeout_ms))
        : config.timeoutMs
      const scriptArgs = [vault.path, '--limit', String(limit), '--json']
      if (args.dryRun === true) scriptArgs.push('--dry-run')
      return runStudentOsScript('repair_import_run.py', scriptArgs, {
        ...config,
        timeoutMs,
        vault: vault.path,
        vaultResolutionSource: vault.source,
        signal: exec.signal,
      })
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

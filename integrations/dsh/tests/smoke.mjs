import assert from 'node:assert/strict'
import { execFileSync, spawnSync } from 'node:child_process'
import { mkdtempSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs'
import { homedir, tmpdir } from 'node:os'
import { join, resolve } from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'
import { Context } from '@deepseek-ai/cordis'
import ToolRuntime from '@deepseek-ai/dsh-tools'
import SystemPrompt from '@deepseek-ai/dsh-system-prompt'
import * as StudentOsPlugin from '../dist/index.js'

const pluginRoot = resolve(fileURLToPath(new URL('..', import.meta.url)))
const repoRoot = resolve(pluginRoot, '..', '..')
const tmpRoot = mkdtempSync(join(tmpdir(), 'student-os-dsh-plugin-'))
const oldEnv = {
  HOME: process.env.HOME,
  USERPROFILE: process.env.USERPROFILE,
  DSH_HOME: process.env.DSH_HOME,
}
const oldCwd = process.cwd()

function restoreEnv() {
  for (const [key, value] of Object.entries(oldEnv)) {
    if (value === undefined) delete process.env[key]
    else process.env[key] = value
  }
  process.chdir(oldCwd)
}

async function setupHarnessContext() {
  const ctx = new Context()
  await ctx.plugin(SystemPrompt)
  await ctx.plugin(ToolRuntime)
  await ctx.plugin(StudentOsPlugin, { repoRoot })
  return ctx
}

function execute(ctx, name, args) {
  return ctx.tools.execute({
    signal: new AbortController().signal,
    callId: `student-os-smoke-${name}`,
    name,
    arguments: args,
  })
}

function requireTool(ctx, name) {
  const tool = ctx.tools.get(name)
  assert.ok(tool, `${name} should be registered`)
  return tool
}

function runOptionalDshCliOverlayCheck(vault) {
  const versionProbe = spawnSync('dsh', ['--version'], {
    encoding: 'utf8',
    stdio: ['ignore', 'pipe', 'pipe'],
  })
  if (versionProbe.error?.code === 'ENOENT') {
    console.log('SKIP dsh-overlay-config (dsh executable not found)')
    return
  }
  if (versionProbe.error) throw versionProbe.error
  assert.equal(versionProbe.status, 0, versionProbe.stderr || versionProbe.stdout)

  const overlay = join(tmpRoot, 'student-os.cordis.yml')
  const pluginUrl = pathToFileURL(resolve(pluginRoot, 'dist', 'index.js')).href
  writeFileSync(
    overlay,
    `- insert:\n    - id: student-os-native\n      name: '${pluginUrl}'\n`,
    'utf8',
  )
  assert.match(readFileSync(overlay, 'utf8'), /name: 'file:\/\//)
  execFileSync('dsh', ['web', '--patch', overlay, '--dump-config'], {
    cwd: vault,
    env: { ...process.env, DSH_HOME: join(tmpRoot, 'dsh-cli-home') },
    stdio: 'pipe',
  })
  console.log(`OK dsh-overlay-config (${versionProbe.stdout.trim()})`)
}

try {
  const fakeHome = join(tmpRoot, 'home')
  const fakeDshHome = join(tmpRoot, 'dsh-home')
  mkdirSync(fakeHome, { recursive: true })
  process.env.HOME = fakeHome
  process.env.USERPROFILE = fakeHome
  process.env.DSH_HOME = fakeDshHome

  const ctx = await setupHarnessContext()
  const schemas = ctx.tools.schemas().map(schema => schema.name).sort()
  assert.deepEqual(schemas, [
    'student_os_frontmatter',
    'student_os_group_changes',
    'student_os_inspect',
  ])

  const inspectTool = requireTool(ctx, 'student_os_inspect')
  const groupTool = requireTool(ctx, 'student_os_group_changes')
  const frontmatterTool = requireTool(ctx, 'student_os_frontmatter')
  assert.equal(inspectTool.parameters.properties.vault.type, 'string')
  assert.equal(inspectTool.parameters.properties.compact.type, 'boolean')
  assert.equal(inspectTool.parameters.properties.scope.type, 'string')
  assert.equal(inspectTool.parameters.properties.timeout_ms.type, 'integer')
  assert.equal(groupTool.parameters.properties.compact.type, 'boolean')
  assert.equal(frontmatterTool.parameters.required.includes('path'), true)
  assert.equal(frontmatterTool.parameters.properties.apply.type, 'boolean')
  assert.equal(inspectTool.isConcurrencySafe?.({}), true)
  assert.equal(groupTool.isConcurrencySafe?.({}), true)
  assert.equal(frontmatterTool.isConcurrencySafe?.({ path: '.', apply: false }), true)
  assert.notEqual(frontmatterTool.isConcurrencySafe?.({ path: '.', apply: true }), true)

  const vault = join(tmpRoot, 'vault')
  mkdirSync(vault, { recursive: true })
  execFileSync('git', ['init'], { cwd: vault, stdio: 'ignore' })

  const away = join(tmpRoot, 'away')
  mkdirSync(away)
  process.chdir(away)

  const inspect = await execute(ctx, 'student_os_inspect', { vault })
  assert.equal(inspect.isError, false)
  assert.equal(inspect.value.ok, true)
  assert.equal(inspect.value.exitCode, 0)
  assert.equal(inspect.value.cwd, repoRoot)
  assert.equal(inspect.value.payload.is_git_repo, true)
  assert.equal(inspect.value.payload.compact, true)
  assert.equal(inspect.value.command.includes('--compact-json'), true)
  assert.equal(inspect.value.command.includes('--scope'), true)
  assert.equal(inspect.value.command.includes('hygiene'), true)
  assert.equal(inspect.value.command.includes('--limit'), true)
  assert.equal(inspect.value.command.includes('20'), true)
  assert.equal(inspect.value.command[1], resolve(repoRoot, 'student-os', 'scripts', 'inspect_repo.py'))

  writeFileSync(join(vault, 'note.md'), '# Note\n', 'utf8')
  const grouped = await execute(ctx, 'student_os_group_changes', { vault })
  assert.equal(grouped.isError, false)
  assert.equal(grouped.value.ok, true)
  assert.equal(grouped.value.payload.counts.changed_groups.ops, 1)
  assert.equal(grouped.value.command.includes('--compact-json'), true)

  const fullGrouped = await execute(ctx, 'student_os_group_changes', { vault, compact: false })
  assert.equal(fullGrouped.isError, false)
  assert.deepEqual(fullGrouped.value.payload.artifact_grouping.ops, ['note.md'])

  const slowRepoRoot = join(tmpRoot, 'slow-repo')
  const slowScripts = join(slowRepoRoot, 'student-os', 'scripts')
  mkdirSync(slowScripts, { recursive: true })
  writeFileSync(
    join(slowScripts, 'slow.py'),
    'import time\nprint("started", flush=True)\ntime.sleep(2)\n',
    'utf8',
  )
  const slow = await StudentOsPlugin.runStudentOsScript('slow.py', [], {
    repoRoot: slowRepoRoot,
    timeoutMs: 50,
    signal: new AbortController().signal,
  })
  assert.equal(slow.ok, false)
  assert.equal(slow.exitCode, null)
  assert.equal(slow.stage, 'timeout')
  assert.equal(typeof slow.stdout, 'string')
  assert.equal(typeof slow.stderr, 'string')

  const sidecar = join(vault, 'sample.pdf.md')
  writeFileSync(sidecar, '# Imported\n', 'utf8')
  const frontmatter = await execute(ctx, 'student_os_frontmatter', {
    path: sidecar,
    apply: true,
    course: 'Math',
    status: 'active',
  })
  assert.equal(frontmatter.isError, false)
  assert.equal(frontmatter.value.ok, true)
  assert.deepEqual(frontmatter.value.payload.updated, ['sample.pdf.md'])
  assert.match(readFileSync(sidecar, 'utf8'), /^---\n/)

  const missing = await execute(ctx, 'student_os_frontmatter', {
    path: join(vault, 'missing.pdf.md'),
  })
  assert.equal(missing.isError, false)
  assert.equal(missing.value.ok, false)
  assert.notEqual(missing.value.exitCode, 0)
  assert.match(missing.value.stderr, /Path not found/)

  const invalid = await execute(ctx, 'student_os_frontmatter', { apply: false })
  assert.equal(invalid.isError, true)
  assert.match(invalid.content[0].text, /INVALID_ARGS|path/)

  assert.equal(process.env.DSH_HOME, fakeDshHome)
  assert.notEqual(resolve(fakeDshHome), resolve(homedir(), '.dsh'))

  runOptionalDshCliOverlayCheck(vault)

  console.log('OK dsh-native-plugin')
} finally {
  restoreEnv()
}

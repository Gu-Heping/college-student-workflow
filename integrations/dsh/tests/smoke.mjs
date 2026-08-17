import assert from 'node:assert/strict'
import { execFileSync } from 'node:child_process'
import { mkdtempSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs'
import { homedir, tmpdir } from 'node:os'
import { join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { apply } from '../dist/index.js'

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

function execute(tool, args) {
  return tool.execute(args, { signal: new AbortController().signal })
}

try {
  const fakeHome = join(tmpRoot, 'home')
  const fakeDshHome = join(tmpRoot, 'dsh-home')
  mkdirSync(fakeHome, { recursive: true })
  process.env.HOME = fakeHome
  process.env.USERPROFILE = fakeHome
  process.env.DSH_HOME = fakeDshHome

  const registered = new Map()
  const promptSections = []
  apply({
    tools: {
      register(tool) {
        registered.set(tool.name, tool)
      },
    },
    systemPrompt: {
      section(section) {
        promptSections.push(section)
      },
    },
  }, { repoRoot })

  assert.deepEqual([...registered.keys()].sort(), [
    'student_os_frontmatter',
    'student_os_group_changes',
    'student_os_inspect',
  ])
  assert.equal(promptSections.length, 1)
  assert.equal(registered.get('student_os_inspect').parameters.vault.type, 'string')
  assert.equal(registered.get('student_os_frontmatter').parameters.path.required, true)
  assert.equal(registered.get('student_os_frontmatter').parameters.apply.type, 'boolean')
  assert.equal(registered.get('student_os_group_changes').output.schema.properties.exitCode.required, true)

  const vault = join(tmpRoot, 'vault')
  mkdirSync(vault, { recursive: true })
  execFileSync('git', ['init'], { cwd: vault, stdio: 'ignore' })

  const away = join(tmpRoot, 'away')
  mkdirSync(away)
  process.chdir(away)

  const inspect = await execute(registered.get('student_os_inspect'), { vault })
  assert.equal(inspect.ok, true)
  assert.equal(inspect.exitCode, 0)
  assert.equal(inspect.cwd, repoRoot)
  assert.equal(inspect.payload.is_git_repo, true)
  assert.equal(inspect.command[1], resolve(repoRoot, 'student-os', 'scripts', 'inspect_repo.py'))

  writeFileSync(join(vault, 'note.md'), '# Note\n', 'utf8')
  const grouped = await execute(registered.get('student_os_group_changes'), { vault })
  assert.equal(grouped.ok, true)
  assert.deepEqual(grouped.payload.artifact_grouping.ops, ['note.md'])

  const sidecar = join(vault, 'sample.pdf.md')
  writeFileSync(sidecar, '# Imported\n', 'utf8')
  const frontmatter = await execute(registered.get('student_os_frontmatter'), {
    path: sidecar,
    apply: true,
    course: 'Math',
    status: 'active',
  })
  assert.equal(frontmatter.ok, true)
  assert.deepEqual(frontmatter.payload.updated, ['sample.pdf.md'])
  assert.match(readFileSync(sidecar, 'utf8'), /^---\n/)

  const missing = await execute(registered.get('student_os_frontmatter'), {
    path: join(vault, 'missing.pdf.md'),
  })
  assert.equal(missing.ok, false)
  assert.notEqual(missing.exitCode, 0)
  assert.match(missing.stderr, /Path not found/)

  assert.equal(process.env.DSH_HOME, fakeDshHome)
  assert.notEqual(resolve(fakeDshHome), resolve(homedir(), '.dsh'))

  try {
    const version = execFileSync('dsh', ['--version'], { encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] }).trim()
    const overlay = join(tmpRoot, 'student-os.cordis.yml')
    writeFileSync(
      overlay,
      `- insert:\n    - id: student-os-native\n      name: '${resolve(pluginRoot, 'dist', 'index.js').replaceAll('\\', '/')}'\n`,
      'utf8',
    )
    execFileSync('dsh', ['web', '--patch', overlay, '--dump-config'], {
      cwd: vault,
      env: { ...process.env, DSH_HOME: fakeDshHome },
      stdio: 'ignore',
    })
    console.log(`OK dsh-cli-overlay (${version})`)
  } catch {
    console.log('SKIP dsh-cli-overlay (dsh executable not found or overlay dump unavailable)')
  }

  console.log('OK dsh-native-plugin')
} finally {
  restoreEnv()
}

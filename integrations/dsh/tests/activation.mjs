import assert from 'node:assert/strict'
import { mkdtempSync, mkdirSync, readFileSync, writeFileSync, rmSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { Context } from '@deepseek-ai/cordis'
import AgentRegistry from '@deepseek-ai/dsh-agent'
import AgentLoop from '@deepseek-ai/dsh-agent-loop'
import LlmRuntime, { LlmAdapter, createUserMessage } from '@deepseek-ai/dsh-llm'
import SessionStore from '@deepseek-ai/dsh-session'
import Projections from '@deepseek-ai/dsh-session-projection'
import SkillRegistry from '@deepseek-ai/dsh-skill'
import * as FilesystemSkills from '@deepseek-ai/dsh-skill-filesystem'
import LocalFs from '@deepseek-ai/dsh-fs-local'
import WorkingDirectory from '@deepseek-ai/dsh-working-directory'
import SystemPrompt from '@deepseek-ai/dsh-system-prompt'
import ToolRuntime, { defineTool } from '@deepseek-ai/dsh-tools'
import * as StudentOs from '../dist/index.js'

const temporary = mkdtempSync(join(tmpdir(), 'student-os-activation-'))
const vault = join(temporary, '学习 vault')
const root = join(vault, '.dsh', 'skills', 'student-os')
mkdirSync(join(root, 'references'), { recursive: true })
const repoRoot = resolve(fileURLToPath(new URL('../../..', import.meta.url)))
const core = readFileSync(join(repoRoot, 'student-os/references/exam-prep-execution-core.md'), 'utf8')
writeFileSync(join(root, 'SKILL.md'), '---\nname: student-os\ndescription: Test learning workflow\n---\n# Loaded skill\nRead sources and edit teaching directly.\n')
writeFileSync(join(root, 'references/exam-prep-execution-core.md'), core)

const captured = []
class OfflineAdapter extends LlmAdapter {
  providerInfo(provider) { return { id: provider, name: 'Offline contract test' } }
  async *stream(request) {
    captured.push(request)
    yield { type: 'text-delta', index: 0, text: 'Offline contract response.' }
    yield { type: 'finish', reason: 'stop' }
  }
}
const ctx = new Context()
try {
  await ctx.plugin(SessionStore)
  await ctx.plugin(Projections)
  await ctx.plugin(AgentRegistry)
  await ctx.plugin(SystemPrompt)
  await ctx.plugin(ToolRuntime)
  await ctx.plugin(LlmRuntime)
  await ctx.plugin(LocalFs)
  await ctx.plugin(WorkingDirectory, {})
  await ctx.plugin(SkillRegistry)
  const filesystemSkills = ctx.plugin(FilesystemSkills, {
    includeDefaultRoots: false, customSkillDirs: [join(vault, '.dsh/skills')], watch: false,
  })
  await filesystemSkills
  await ctx.plugin(AgentLoop, { agents: [], maxParallelToolCalls: 1 })
  ctx.llm.registerAdapter(['offline'], new OfflineAdapter())
  await ctx.plugin(StudentOs, { repoRoot, vaultRoot: vault, skillRoot: root, activationMode: 'required' })
  let executions = 0
  ctx.tools.register(defineTool({
    name: 'activation_probe', description: 'Offline tool execution probe', parameters: {},
    output: { schema: { type: 'string' }, render: (_args, value) => [{ type: 'text', text: value }] },
    execute: async () => { executions += 1; return 'executed' },
  }))
  const handles = []
  async function create(cwd = vault, seed, parentAgent) {
    const handle = await ctx.agents.create({
      sessionId: `activation-${handles.length}`, meta: { cwd, ...(parentAgent ? { origin: 'subagent' } : {}) }, seed,
      ...(parentAgent ? { parentAgent } : {}),
      agentOptions: { provider: 'offline', model: 'offline' },
    })
    handles.push(handle)
    return handle.agent
  }
  async function turn(agent) {
    const before = captured.length
    agent.followup(createUserMessage({ source: { kind: 'user' }, content: [{ type: 'text', text: 'Improve this study page.' }] }))
    await agent.whenIdle()
    return captured.slice(before)
  }
  const text = request => request.messages.flatMap(m => m.content).filter(c => c.type === 'text').map(c => c.text).join('\n')
  const count = request => (text(request).match(/<student_os_execution_core>/g) ?? []).length
  const execute = (agent, parent) => ctx.tools.execute({
    agent, signal: new AbortController().signal, name: 'activation_probe',
    callId: `probe-${executions}`, arguments: {}, ...(parent ? { parent } : {}),
  })
  const agent = await create()
  assert.equal((await execute(agent)).isError, true, 'model tools denied before first pre-step')
  assert.equal(executions, 0)
  let requests = await turn(agent)
  assert.equal(requests.length, 1, JSON.stringify(agent.session.snapshotEvents().slice(-6)))
  assert.equal(count(requests[0]), 1)
  assert.match(text(requests[0]), /# Loaded skill/)
  assert.match(text(requests[0]), /do not fabricate tests/)
  assert.equal((await execute(agent)).isError, false)
  const native = await ctx.tools.execute({
    agent, signal: new AbortController().signal, name: 'student_os_group_changes',
    callId: 'activation-metadata', arguments: {},
  })
  assert.equal(native.isError, false)
  assert.equal(native.value.activation.status, 'loaded')
  assert.equal(native.value.activation.skill_path, join(root, 'SKILL.md'))
  const activation = agent.session.deriveMessages().find(m => m.source.kind === 'student-os-activation')
  assert.equal(activation.source.form, 'instructions')
  assert.equal(activation.source.skill_hash.length, 64)
  assert.equal(activation.source.core_hash.length, 64)
  assert.equal(activation.source.skill_path, join(root, 'SKILL.md'))
  assert.equal(agent.session.deriveMessages().some(m => m.source.kind === 'skill-invocation'), false)
  assert.equal((await turn(agent)).map(count)[0], 1, 'ordinary continuation does not republish identical instructions')
  const stopSeries = ctx.on('agent/pre-step', async (payload, next) => {
    const decision = await next()
    return payload.agent === agent && decision.kind === 'enter' ? { ...decision, startsRequestSeries: true } : decision
  })
  assert.equal(count((await turn(agent))[0]), 1, 'new request series does not imply lost effective context')
  stopSeries()
  const restored = await create(vault, agent.session.snapshotEvents())
  assert.equal(count((await turn(restored))[0]), 1, 'replayed/resumed effective history deduplicates by body and source, not process state')

  // A real surface replacement drops the instruction node, just as compaction does.
  const nodes = agent.session.surface.nodes.slice(1) // The system-prompt head is not compactable user context.
  agent.session.append('user/message', createUserMessage({
    source: { kind: 'user' }, content: [{ type: 'text', text: 'Compacted summary without instructions.' }],
  }), { surfaceOp: { op: 'replace', startSeq: nodes[0], endSeq: nodes.at(-1) }, sourceEventSeqs: [...nodes] })
  assert.equal((await execute(agent)).isError, true, 'historical ready flag cannot bypass context loss')
  requests = await turn(agent)
  assert.equal(count(requests[0]), 1, 'compacted-away instructions reload')

  writeFileSync(join(root, 'references/exam-prep-execution-core.md'), `${core}\nUpdated execution core.\n`)
  requests = await turn(agent)
  assert.match(text(requests[0]), /Updated execution core/)
  writeFileSync(join(root, 'SKILL.md'), `${readFileSync(join(root, 'SKILL.md'), 'utf8')}\nUpdated skill body.\n`)
  assert.match(text((await turn(agent))[0]), /Updated skill body/)
  const child = await create(vault, undefined, agent)
  assert.equal(count((await turn(child))[0]), 1, 'independent subagent session gets instructions')

  const outside = join(temporary, 'outside')
  mkdirSync(outside)
  const unrelated = await create(outside)
  assert.equal(count((await turn(unrelated))[0]), 0)
  assert.equal((await execute(unrelated)).isError, false, 'outside workspace not constrained')

  rmSync(join(root, 'references/exam-prep-execution-core.md'))
  assert.equal((await turn(agent)).length, 0, 'missing core rejects before model request')
  assert.equal((await execute(agent)).isError, true)
  writeFileSync(join(root, 'references/exam-prep-execution-core.md'), core)
  const wrong = join(temporary, 'wrong')
  mkdirSync(wrong)
  const unregister = ctx.skills.register({ name: 'student-os', description: 'wrong copy', source: 'runtime',
    path: join(wrong, 'SKILL.md'), resourceBase: { kind: 'directory', path: wrong }, content: 'wrong body' })
  writeFileSync(join(wrong, 'SKILL.md'), 'wrong body')
  assert.equal((await turn(child)).length, 0, 'wrong resolved skill cannot silently fall back')
  unregister()
  assert.equal((await turn(child)).length, 1, 'repairing configuration recovers')
  const disabled = ctx.skills.register({ name: 'student-os', description: 'disabled', source: 'runtime',
    path: join(root, 'SKILL.md'), resourceBase: { kind: 'directory', path: root }, content: 'disabled',
    invocation: { modelInvocable: false, userInvocable: true } })
  assert.equal((await turn(child)).length, 0, 'required activation does not override registry invocation policy')
  disabled()
  const body = readFileSync(join(root, 'SKILL.md'), 'utf8')
  rmSync(join(root, 'SKILL.md'))
  assert.equal((await turn(child)).length, 0, 'missing registered skill fails before request')
  writeFileSync(join(root, 'SKILL.md'), body)
  // Watchers are deliberately off in this isolated fixture. Refresh the real
  // provider after external deletion/recreation, as a runtime restart would.
  await filesystemSkills.restart()
  writeFileSync(join(root, 'references/exam-prep-execution-core.md'), Buffer.from([0xff]))
  assert.equal((await turn(child)).length, 0, 'invalid UTF-8 instructions are not silently replaced')
  assert.match(child.session.snapshotEvents().at(-1).data.reason.error.message, /utf-8|encoded data/i)
  writeFileSync(join(root, 'references/exam-prep-execution-core.md'), core)
  assert.equal((await turn(child)).length, 1, JSON.stringify(child.session.snapshotEvents().slice(-2)))

  // Nested dispatch uses the same agent/parent-token boundary as PTC SDK calls.
  // Drop context inside an already admitted outer call: its child must still deny.
  ctx.tools.register(defineTool({
    name: 'nested_activation_probe', description: 'Exercise nested guard after context loss', parameters: {},
    output: { schema: { type: 'boolean' }, render: (_args, value) => [{ type: 'text', text: String(value) }] },
    async execute(_args, exec) {
      const nodes = exec.agent.session.surface.nodes.slice(1)
      exec.agent.session.append('user/message', createUserMessage({
        source: { kind: 'user' }, content: [{ type: 'text', text: 'Replacement context.' }],
      }), { surfaceOp: { op: 'replace', startSeq: nodes[0], endSeq: nodes.at(-1) }, sourceEventSeqs: [...nodes] })
      return (await execute(exec.agent, exec.token)).isError
    },
  }))
  const beforeNested = executions
  const nested = await ctx.tools.execute({ agent: child, name: 'nested_activation_probe', callId: 'nested',
    arguments: {}, signal: new AbortController().signal })
  assert.equal(nested.isError, false)
  assert.equal(nested.value, true, 'nested dispatch denied after losing required instructions')
  assert.equal(executions, beforeNested)
  for (const handle of handles.reverse()) await handle.dispose()
  console.log('OK dsh-required-activation (official registry/AgentLoop/final offline model request)')
} finally {
  await ctx.fiber.dispose()
  rmSync(temporary, { recursive: true, force: true })
}

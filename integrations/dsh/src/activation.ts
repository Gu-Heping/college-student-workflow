import { createHash } from 'node:crypto'
import { readFileSync, realpathSync, statSync } from 'node:fs'
import { dirname, isAbsolute, relative, resolve, sep } from 'node:path'
import type { Context } from '@deepseek-ai/cordis'
import type { Agent } from '@deepseek-ai/dsh-agent'
import { createUserMessage, type Message } from '@deepseek-ai/dsh-llm'
import { isModelInvocable, renderSkillContent } from '@deepseek-ai/dsh-skill'
import type {} from '@deepseek-ai/dsh-working-directory'

export interface ActivationConfig {
  activationMode?: 'required' | 'catalog'
  vaultRoot?: string
  skillRoot?: string
}

export interface ActivationStatus {
  mode: 'required' | 'catalog'
  status: 'loaded' | 'pending' | 'error' | 'outside-vault' | 'catalog-only'
  skill_path?: string
  skill_hash?: string
  core_hash?: string
  error?: string
}

interface ActivationSource {
  kind: 'student-os-activation'
  form: 'instructions'
  vault: string
  skill_path: string
  skill_hash: string
  core_hash: string
}

declare module '@deepseek-ai/dsh-llm' {
  interface MessageSourceMap {
    'student-os-activation': ActivationSource
  }
}

const coreRelative = 'references/exam-prep-execution-core.md'
const hash = (text: string) => createHash('sha256').update(text).digest('hex')
const canonical = (path: string) => realpathSync(path)
const samePath = (a: string, b: string) => relative(a, b) === ''
function inside(root: string, path: string): boolean {
  const tail = relative(root, path)
  return tail === '' || (!isAbsolute(tail) && tail !== '..' && !tail.startsWith(`..${sep}`))
}

function matches(message: Message, source: ActivationSource, text: string): boolean {
  const old = message.source
  return old.kind === source.kind && old.vault === source.vault &&
    old.skill_path === source.skill_path && old.skill_hash === source.skill_hash &&
    old.core_hash === source.core_hash && message.content.length === 1 &&
    message.content[0].type === 'text' && message.content[0].text === text
}

/** Required mode loads instructions, not a simulated user gesture or skill tool call. */
export function installActivation(ctx: Context, config: ActivationConfig): (agent?: Agent) => ActivationStatus {
  const mode = config.activationMode ?? 'catalog'
  if (mode !== 'catalog' && mode !== 'required') throw new Error('Invalid student-os activationMode')
  if (mode === 'catalog') return () => ({ mode, status: 'catalog-only' })
  if (!config.vaultRoot || !isAbsolute(config.vaultRoot) || !config.skillRoot || !isAbsolute(config.skillRoot)) {
    throw new Error('Student OS required mode needs absolute vaultRoot and skillRoot; regenerate the project overlay.')
  }
  const vault = canonical(config.vaultRoot)
  if (!statSync(vault).isDirectory()) throw new Error('Student OS vaultRoot must be a directory')
  const root = resolve(config.skillRoot)
  const states = new WeakMap<Agent, ActivationStatus>()
  const expected = new WeakMap<Agent, { source: ActivationSource; text: string }>()
  let services: Context | undefined
  ctx.inject(['skills', 'workingDirectory', 'agents'], active => {
    services = active
    active.effect(() => () => { services = undefined })
  })
  const status = (agent?: Agent): ActivationStatus => agent === undefined
    ? { mode, status: 'pending' }
    : states.get(agent) ?? { mode, status: 'pending' }

  ctx.on('agent/pre-step', async ({ agent, signal }, next) => {
    const decision = await next()
    if (decision.kind === 'reject') return decision
    // Invalidate before every await: no execution is allowed on an earlier step's readiness.
    states.set(agent, { mode, status: 'pending' })
    expected.delete(agent)
    try {
      const runtime = services
      if (!runtime) throw new Error('DSH skills, agents and workingDirectory services are required')
      const cwd = canonical(await runtime.workingDirectory.ensure(agent, signal))
      if (!inside(vault, cwd)) {
        states.set(agent, { mode, status: 'outside-vault' })
        return decision
      }
      const skill = await runtime.skills.get('student-os', { cwd, signal, scope: agent })
      signal.throwIfAborted()
      if (!skill || !skill.content.trim()) throw new Error('student-os was not resolved by the DSH skill registry')
      if (!isModelInvocable(skill)) throw new Error('student-os registry invocation policy does not permit model loading')
      if (!skill.path || !samePath(canonical(dirname(skill.path)), canonical(root))) {
        throw new Error('Registry student-os path does not match configured skillRoot')
      }
      if (!inside(canonical(root), canonical(skill.path))) throw new Error('Skill instruction file escapes skillRoot')
      if (skill.resourceBase?.kind !== 'directory' || !samePath(canonical(skill.resourceBase.path), canonical(root))) {
        throw new Error('Registry student-os resource directory does not match configured skillRoot')
      }
      const corePath = resolve(root, coreRelative)
      if (!inside(canonical(root), canonical(corePath))) throw new Error('Execution core escapes skillRoot')
      const core = new TextDecoder('utf-8', { fatal: true }).decode(readFileSync(corePath))
      if (!core.trim()) throw new Error('Student OS execution core is empty')
      const source: ActivationSource = {
        kind: 'student-os-activation', form: 'instructions', vault,
        skill_path: canonical(skill.path), skill_hash: hash(skill.content), core_hash: hash(core),
      }
      const text = `Automatic Student OS activation: these current instructions supersede earlier Student OS activation context. This is not a user invocation.\n\n${renderSkillContent(skill)}\n\n<student_os_execution_core>\n${core}\n</student_os_execution_core>`
      // Only effective, projected history counts. Compacted-away or redacted bodies reload.
      const visible = agent.session.deriveMessages()
      const loaded = visible.some(message => matches(message, source, text)) ||
        decision.messages.some(message => matches(message, source, text))
      expected.set(agent, { source, text })
      states.set(agent, { mode, status: 'loaded', skill_path: source.skill_path, skill_hash: source.skill_hash, core_hash: source.core_hash })
      return loaded ? decision : {
        ...decision,
        messages: [...decision.messages, createUserMessage({ source, content: [{ type: 'text', text }] })],
      }
    } catch (error) {
      if (signal.aborted) throw error
      const reason = `Student OS activation failed: ${error instanceof Error ? error.message : String(error)}. Check project skillRoot and restart with the project --patch overlay.`
      states.set(agent, { mode, status: 'error', error: reason })
      throw new Error(reason, { cause: error })
    }
  })

  ctx.tools.guard(exec => {
    if (!exec.agent) return undefined // Host-owned calls are not model executions.
    let cwd: string
    try {
      if (!services) return 'Student OS activation pending: runtime services unavailable'
      cwd = canonical(services.workingDirectory.get(exec.agent.session))
    } catch {
      return 'Student OS activation pending: workspace cannot be resolved'
    }
    if (!inside(vault, cwd)) return undefined
    const current = status(exec.agent)
    const wanted = expected.get(exec.agent)
    const visible = current.status === 'loaded' && wanted !== undefined &&
      exec.agent.session.deriveMessages().some(message => matches(message, wanted.source, wanted.text))
    return visible ? undefined : current.error ?? 'Student OS required instructions are not loaded; retry the step after fixing activation.'
  })
  return status
}

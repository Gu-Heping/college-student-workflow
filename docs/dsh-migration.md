# DeepSeek Harness migration

This page describes the minimal Claude Code to DeepSeek Harness path for Student OS.

Official DSH reference checked: `deepseek-ai/deepseek-harness` commit `99f6f02fecdb7dff40c3fbc9470f5907c29f74ca`.
The plugin is built against the matching published packages `@deepseek-ai/dsh-tools@0.1.0-rc.7` and `@deepseek-ai/cordis@4.0.1`.

## Prerequisites

- DeepSeek Harness from the official `deepseek-ai/deepseek-harness` project.
- Python 3 and `git`.
- Node.js and npm to build the local Student OS Cordis plugin.
- A persistent local checkout of `Gu-Heping/college-student-workflow`.

## Agent Bootstrap

Natural-language request example:

```text
从 https://github.com/Gu-Heping/college-student-workflow 安装 Student OS 到当前项目，并启用 DSH 原生支持。按照仓库提供的 DSH bootstrap 流程执行，不要修改全局 DSH 配置。
```

From the `college-student-workflow` checkout, run:

```bash
python scripts/bootstrap_dsh.py --project-root /path/to/vault --json
```

`--project-root` is the user's learning vault / current DSH workspace. Do not use this repository checkout as the target vault unless it is truly the user's vault.

On success, the JSON includes the project Skill path, built plugin entry, project-local overlay path, and the exact restart argv:

```json
{
  "ok": true,
  "activation": {
    "active_in_current_process": false,
    "restart_required": true,
    "argv": ["dsh", "web", "--patch", "/path/to/vault/.dsh/student-os.cordis.yml"]
  }
}
```

On failure, bootstrap exits non-zero and returns `ok:false` with a stable `stage`, for example `project-root`, `skill-install`, `plugin-build`, or `overlay-write`.

Start DSH from the vault root with the returned argv. Bootstrap does not hot-load the current DSH session: `active_in_current_process` is `false` and `restart_required` is `true`.

Bootstrap performs:

- project-scope Skill install via `scripts/install_student_os.py --agent dsh --scope project --project-root <vault>`
- reproducible plugin build with `npm ci` and `npm run build` in `integrations/dsh/`
- project-local overlay write to `<vault>/.dsh/student-os.cordis.yml`

The generated overlay references this checkout's `integrations/dsh/dist/index.js`, so the checkout is a runtime dependency. Keep it in a persistent tooling location and do not delete it after bootstrap. This PR intentionally does not publish an npm package or install a machine-level DSH profile package.

## Confirm Discovery

Confirm the project Skill install path exists:

```bash
test -f "/path/to/vault/.dsh/skills/student-os/SKILL.md"
```

Inside DSH, ask it to use the `student-os` skill for the current vault. The skill catalog should expose `student-os` from the project install.

Confirm native tools by asking DSH to call:

- `student_os_inspect`
- `student_os_group_changes`
- `student_os_frontmatter`

For a no-network patch composition check when DSH is installed:

```bash
dsh web --patch /path/to/vault/.dsh/student-os.cordis.yml --dump-config
```

`--dump-config` confirms that the overlay composes into the selected profile; it does not boot the plugin. Runtime loading is covered by `npm run test` at the package/API layer. A full interactive DSH boot should still be verified on a machine with the `dsh` CLI installed by starting DSH from the vault root with the same `--patch` argv above and confirming the three `student_os_*` tools are callable.

## Manual Troubleshooting

The bootstrap path above is the recommended path for agents. Use the manual steps only when troubleshooting.

User-scope Skill install:

```bash
python scripts/install_student_os.py --agent dsh --scope user
```

Project-scope Skill install:

```bash
python scripts/install_student_os.py --agent dsh --scope project --project-root /path/to/vault
```

DSH paths follow official home semantics:

- user scope: `$DSH_HOME/skills/student-os`, or `~/.dsh/skills/student-os` when `DSH_HOME` is unset, empty, or blank
- project scope: `<vault>/.dsh/skills/student-os`

Manual plugin build:

```bash
cd integrations/dsh
npm ci
npm run build
npm run test
cd ../..
```

The plugin is a local Cordis plugin at `integrations/dsh/dist/index.js`. It registers three native tools and delegates all business logic to the existing Python scripts.
The test command boots a real Cordis `Context` with DSH `ToolRuntime`, registers the plugin through the official `defineTool()` path, and executes all three tools against a temporary vault.

If you hand-write an overlay, keep it project-local during testing and use an absolute plugin path:

```bash
cat > /path/to/vault/.dsh/student-os.cordis.yml <<EOF
- insert:
    - id: student-os-native
      name: '/absolute/path/to/college-student-workflow/integrations/dsh/dist/index.js'
EOF
```

Do not make `$DSH_HOME/cordis.patch.yml` the default while validating this PR. Machine-level DSH profile/package distribution is a later design step.

## Claude Code to DSH Mapping

| Claude Code | DeepSeek Harness |
| --- | --- |
| `~/.claude/skills/student-os` user Skill | `$DSH_HOME/skills/student-os` user Skill |
| `<vault>/.claude/skills/student-os` project Skill | `<vault>/.dsh/skills/student-os` project Skill |
| Claude Code reads `student-os/SKILL.md` | DSH discovers the same installed `SKILL.md` |
| Shelling out to `inspect_repo.py` | native `student_os_inspect` tool |
| Shelling out to `group_git_changes.py` | native `student_os_group_changes` tool |
| Shelling out to `ensure_frontmatter.py` | native `student_os_frontmatter` tool |

## Fallback

To return to pure Skill mode, start DSH without the Student OS patch overlay. The installed Skill still works through the same portable Python core; only the three native tools are disabled.

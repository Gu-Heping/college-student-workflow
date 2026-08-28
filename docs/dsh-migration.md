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
python student-os/scripts/inspect_repo.py /path/to/vault
python student-os/scripts/group_git_changes.py /path/to/vault
python scripts/bootstrap_dsh.py --project-root /path/to/vault --json
```

`--project-root` is the user's learning vault / current DSH workspace. Do not use this repository checkout, or a path inside it, as the target vault. Treat the inspect/group output as the read-only baseline so bootstrap-created `.dsh` files can be distinguished from pre-existing dirty files.

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
If `<vault>/.dsh/student-os.cordis.yml` already exists with different content, bootstrap fails instead of overwriting it; re-run with `--force-overlay` only after confirming the existing overlay can be backed up and replaced.

Start DSH from the vault root with the returned argv. Bootstrap does not hot-load the current DSH session: `active_in_current_process` is `false` and `restart_required` is `true`.

Bootstrap performs:

- project-scope Skill install via `scripts/install_student_os.py --agent dsh --scope project --project-root <vault>`
- reproducible plugin build in `integrations/dsh/`; unchanged inputs reuse the existing `dist/index.js`, source-only changes run `npm run build`, and dependency changes or missing `node_modules` run `npm ci` followed by `npm run build`
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

`--dump-config` confirms that the overlay composes into the selected profile; it does not boot the plugin. Runtime loading is covered by `npm run test` at the package/API layer. When validating a local checkout in an installed DSH runtime, verify project Skill discovery, plugin mount, and the available `student_os_*` tools through the project-local `--patch` overlay.

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

The plugin is a local Cordis plugin at `integrations/dsh/dist/index.js`. It registers native tools for compact inspect, Git grouping, frontmatter, direct import repair, and import repair checks; all business logic stays in the existing Python scripts.
The test command boots a real Cordis `Context` with DSH `ToolRuntime`, registers the plugin through the official `defineTool()` path, and executes the tools against a temporary vault.

If you hand-write an overlay, keep it project-local during testing and use a `file://` URL for the built plugin entry. **On Windows the plugin `name` must be a `file://` URL** (Node's ESM loader rejects bare absolute paths like `D:/...` with `ERR_UNSUPPORTED_ESM_URL_SCHEME`); macOS/Linux also accept the generated `file:///...` form:

```bash
python student-os/scripts/inspect_repo.py /path/to/vault
python student-os/scripts/group_git_changes.py /path/to/vault
mkdir -p /path/to/vault/.dsh
cat > /path/to/vault/.dsh/student-os.cordis.yml <<EOF
- insert:
    - id: student-os-native
      name: 'file:///absolute/path/to/college-student-workflow/integrations/dsh/dist/index.js'
      config:
        vaultRoot: '/absolute/path/to/your/learning-vault'
      # Windows example:
      # name: 'file:///D:/repos/college-student-workflow/integrations/dsh/dist/index.js'
EOF
```

Do not make `$DSH_HOME/cordis.patch.yml` the default while validating this PR. Machine-level DSH profile/package distribution is a later design step.
Avoid running destructive npm maintenance commands concurrently against the same local checkout; the repository bootstrap and smoke paths share a filesystem build lock, but this PR does not try to defend against unrelated external processes deleting `integrations/dsh/node_modules` at arbitrary times.

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

To return to pure Skill mode, start DSH without the Student OS patch overlay. The installed Skill still works through the same portable Python core; only the native DSH tools are disabled.

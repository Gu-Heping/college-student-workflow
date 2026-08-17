# DeepSeek Harness migration

This page describes the minimal Claude Code to DeepSeek Harness path for Student OS.

Official DSH reference checked: `deepseek-ai/deepseek-harness` commit `99f6f02fecdb7dff40c3fbc9470f5907c29f74ca`.

## Prerequisites

- DeepSeek Harness from the official `deepseek-ai/deepseek-harness` project.
- Python 3 and `git`.
- Node.js and npm to build the local Student OS Cordis plugin.
- A local checkout of `Gu-Heping/college-student-workflow`.

## Install the Skill

User scope:

```bash
python scripts/install_student_os.py --agent dsh --scope user
```

Project scope, from this repository checkout:

```bash
python scripts/install_student_os.py --agent dsh --scope project --project-root /path/to/vault
```

DSH paths follow official home semantics:

- user scope: `$DSH_HOME/skills/student-os`, or `~/.dsh/skills/student-os` when `DSH_HOME` is unset, empty, or blank
- project scope: `<vault>/.dsh/skills/student-os`

## Build the Native Plugin

```bash
cd integrations/dsh
npm ci
npm run build
cd ../..
```

The plugin is a local Cordis plugin at `integrations/dsh/dist/index.js`. It registers three native tools and delegates all business logic to the existing Python scripts.

## Enable the Plugin

DSH patch overlays use absolute plugin paths. Create a local overlay from the repository root.

PowerShell:

```powershell
$plugin = (Resolve-Path .\integrations\dsh\dist\index.js).Path -replace '\\','/'
@"
- insert:
    - id: student-os-native
      name: '$plugin'
"@ | Set-Content -Encoding UTF8 .\.dsh-student-os.cordis.yml
```

Bash:

```bash
plugin="$(pwd)/integrations/dsh/dist/index.js"
cat > .dsh-student-os.cordis.yml <<EOF
- insert:
    - id: student-os-native
      name: '$plugin'
EOF
```

Start DSH from the vault root with the overlay:

```bash
cd /path/to/vault
dsh web --patch /path/to/college-student-workflow/.dsh-student-os.cordis.yml
```

For a persistent machine-local setup, place the same patch entry in `$DSH_HOME/cordis.patch.yml`.

## Confirm Discovery

Confirm the Skill install path exists:

```bash
test -f "${DSH_HOME:-$HOME/.dsh}/skills/student-os/SKILL.md"
```

When using project scope, confirm:

```bash
test -f "/path/to/vault/.dsh/skills/student-os/SKILL.md"
```

Inside DSH, ask it to use the `student-os` skill for the current vault. The skill catalog should expose `student-os` from the user or project install.

Confirm native tools by asking DSH to call:

- `student_os_inspect`
- `student_os_group_changes`
- `student_os_frontmatter`

For a no-network configuration check when DSH is installed:

```bash
dsh web --patch /path/to/college-student-workflow/.dsh-student-os.cordis.yml --dump-config
```

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

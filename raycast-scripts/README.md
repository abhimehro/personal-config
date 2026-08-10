# Raycast Script Commands — Agent Shell

Add this directory in Raycast:

1. Open **Settings → Script Commands → Add Script Directory**
2. Choose
3. Commands appear in Root Search

## Scripts
| Script | Purpose |
|:---|:---|
|  | Full agent terminal health check |
|  | agent-zsh self-test
shell=zsh
ZDOTDIR=/Users/speedybee/.config/agent-shell
PWD=/Users/speedybee/dev/abhimehro
AGENT_WORKSPACE=/Users/speedybee/dev/abhimehro
PYTHONUNBUFFERED=1
PAGER=cat
git=ok
python3=ok
stdout-mark |
|  | Run an arbitrary command via  |

## Why shebangs matter
Raycast runs Script Commands with the interpreter in the shebang ( here).
They do **not** use your Fish login shell unless the shebang points at Fish.

## AI Terminal tip
When using Raycast AI , prefer:

## main...origin/main
?? .agents/
?? .claude/
?? .cursor/
?? .github/github-app.yml
?? .trunk/
?? .vscode/
?? .windsurf/

Or run the **Run in Agent Zsh** Script Command.

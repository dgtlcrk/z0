#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="${Z0_PROJECT_DIR:-$HOME/projects/z0}"
BASHRC="$HOME/.bashrc"

touch "$BASHRC"

python3 - "$BASHRC" "$PROJECT_DIR" <<'PY'
from pathlib import Path
import sys

bashrc = Path(sys.argv[1])
project_dir = sys.argv[2]

start_marker = "# >>> z0_n3t BotOps >>>"
end_marker = "# <<< z0_n3t BotOps <<<"

block = f'''{start_marker}
# Display BotOps once per interactive terminal session.
case $- in
    *i*)
        if [ -z "${{Z0_BANNER_SHOWN:-}}" ]; then
            export Z0_BANNER_SHOWN=1

            if [ -d "{project_dir}" ]; then
                (
                    cd "{project_dir}" || exit
                    python3 -m z0.botops banner
                )
            fi
        fi
        ;;
esac
{end_marker}'''

text = bashrc.read_text(encoding="utf-8")

# Remove the earlier unmarked implementation.
legacy = '''# z0_n3t BotOps login dashboard
cd "$HOME/projects/z0" && python3 -m z0.banner
cd "$HOME"
'''
text = text.replace(legacy, "")

if start_marker in text and end_marker in text:
    before = text.split(start_marker, 1)[0]
    after = text.split(end_marker, 1)[1]
    text = before.rstrip() + "\n\n" + block + after
else:
    text = text.rstrip() + "\n\n" + block + "\n"

bashrc.write_text(text, encoding="utf-8")
PY

echo "Installed z0_n3t BotOps login block in $BASHRC"

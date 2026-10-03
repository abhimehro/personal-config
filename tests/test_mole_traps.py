"""Regression coverage for Mole's trap serialization and restoration callers."""

import os
from pathlib import Path
import subprocess
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
MOLE = REPO_ROOT / "configs/.config/mole"


def nested_function(path, name):
    """Load only a restoration function, avoiding interactive/destructive entrypoints."""
    source = (MOLE / path).read_text()
    start = source.index(f"\t{name}() {{\n")
    end = source.index("\n\t}", start) + len("\n\t}")
    return source[start:end]


class MoleTrapTests(unittest.TestCase):
    def run_bash(self, script, *args):
        env = os.environ.copy()
        env.pop("BASH_ENV", None)
        result = subprocess.run(
            [
                "bash", "-c", 'set -euo pipefail\nsource "$1"\nshift\n' + script,
                "mole-trap-test", str(MOLE / "lib/core/timeout.sh"), *args,
            ],
            text=True, capture_output=True, timeout=10, env=env,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result.stdout

    def test_round_trip_preserves_handler_data(self):
        handlers = [
            "", ":", "printf '%s %s\\n' 'hello world' \"quoted\"",
            "mutated=1; : $(mutated=2) `mutated=3` $HOME * ? [abc]",
            "# apostrophes: ''' and backslashes: \\\\ and trailing quote '",
            "printf 'first line\\n'\n# tab\tand trailing newlines\n\n",
        ]
        for signal in ("EXIT", "INT", "TERM"):
            for handler in handlers:
                with self.subTest(signal=signal, handler=handler):
                    self.run_bash(
                        '''
mutated=0
trap -- "$1" "$2"
saved=$(trap -p "$2")
trap ':' "$2"
mole_restore_trap "$saved"
actual=$(trap -p "$2")
trap - "$2"
[[ $saved == "$actual" && $mutated == 0 ]]
''', handler, signal,
                    )

    def test_rejects_malformed_declarations_without_execution(self):
        for declaration in (
            "trap -- ':' SIGINT; mutated=1",
            "trap -- 'ok'; mutated=1; 'more' SIGINT",
            "trap -- $(mutated=1) SIGINT",
            "trap -- ':' SIGUSR1",
            "", "not a trap",
        ):
            with self.subTest(declaration=declaration):
                self.run_bash(
                    '''
mutated=0
trap ':' INT
saved=$(trap -p INT)
if mole_restore_trap "$1"; then exit 1; fi
[[ $(trap -p INT) == "$saved" && $mutated == 0 ]]
''', declaration,
                )

    def test_restoration_callers_preserve_saved_arguments(self):
        project = (MOLE / "lib/clean/project.sh").read_text()
        scan_restore = project.split(
            "\t# Restore caller traps after this function completes.\n", 1
        )[1].split('\n\tif [[ ${#all_found_items[@]}', 1)[0]
        callers = [
            nested_function("lib/clean/project.sh", "restore_terminal")
            + "\ntrap ':' EXIT INT TERM\nrestore_terminal\nrestore_terminal",
            nested_function("bin/uninstall.sh", "restore_scan_int_trap")
            + "\ntrap ':' INT\nrestore_scan_int_trap",
            nested_function("lib/uninstall/batch.sh", "_restore_uninstall_traps")
            + "\ntrap ':' INT TERM\n_restore_uninstall_traps",
            "trap ':' INT TERM\n" + scan_restore,
            # Force the actual shell fallback without depending on bc/coreutils/Perl.
            'MO_TIMEOUT_BIN=""; MO_TIMEOUT_PERL_BIN=""\n'
            'bc() { cat >/dev/null; echo 0; }\nrun_with_timeout 5 true',
        ]
        for index, caller in enumerate(callers):
            for handler in (None, "", "printf '%s\\n' 'spaces and quotes'; : $HOME *"):
                with self.subTest(caller=index, handler=handler):
                    self.run_bash(
                        '''
show_cursor() { :; }
_cleanup_sudo_keepalive() { :; }
original_stty=""
terminal_restored=false
trap_installed_by_this_call=true
if [[ $1 == set ]]; then
    trap -- "$2" EXIT INT TERM
else
    trap - EXIT INT TERM
fi
previous_exit_trap=$(trap -p EXIT)
previous_int_trap=$(trap -p INT)
previous_term_trap=$(trap -p TERM)
old_trap_int=$previous_int_trap
old_trap_term=$previous_term_trap
'''
                        + caller
                        + '''
actual_exit=$(trap -p EXIT)
actual_int=$(trap -p INT)
actual_term=$(trap -p TERM)
trap - EXIT INT TERM
[[ $actual_exit == "$previous_exit_trap" ]]
[[ $actual_int == "$previous_int_trap" ]]
[[ $actual_term == "$previous_term_trap" ]]
''', "unset" if handler is None else "set", handler or "",
                    )

    def test_restored_handlers_execute_only_on_signal(self):
        for signal in ("EXIT", "INT", "TERM"):
            with self.subTest(signal=signal):
                output = self.run_bash(
                    '''
trap 'printf "%s\\n" "handler ran"' "$1"
saved=$(trap -p "$1")
trap - "$1"
mole_restore_trap "$saved"
echo restored
if [[ $1 != EXIT ]]; then kill -s "$1" "$$"; fi
''', signal,
                )
                self.assertEqual(output, "restored\nhandler ran\n")


if __name__ == "__main__":
    unittest.main()

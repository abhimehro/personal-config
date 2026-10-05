"""Regression coverage for Mole's trap serialization and restoration callers."""

import os
from pathlib import Path
import re
import shutil
import subprocess
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
MOLE = REPO_ROOT / "configs/.config/mole"


def _slice_function_body(path, name):
    """Cut one tab-indented function body out of a Mole library file."""
    source = (MOLE / path).read_text()
    opening = f"\t{name}() {{\n"
    if opening not in source:
        raise AssertionError(f"{path}: missing opening marker for {name}")
    start = source.index(opening)
    closing = "\n\t}"
    if closing not in source[start:]:
        raise AssertionError(f"{path}: missing closing marker for {name}")
    end = source.index(closing, start) + len(closing)
    return source[start:end]


def nested_function(path, name):
    """Load only a restoration function, avoiding interactive/destructive entrypoints."""
    body = _slice_function_body(path, name)
    # A silently truncated or renamed slice would make every assertion pass
    # while the real function is never executed.
    if "mole_restore_trap" not in body:
        raise AssertionError(f"{path}: {name} no longer calls mole_restore_trap")
    # The CWE-78 property this suite exists for: eval must not come back next
    # to the helper. None of the sliced functions mention eval even in prose.
    if "eval" in body:
        raise AssertionError(f"{path}: {name} reintroduces eval of saved trap state")
    return body


class MoleTrapTests(unittest.TestCase):
    def bash_bin(self):
        """Resolve the interpreter explicitly so results do not depend on PATH."""
        override = os.environ.get("MOLE_TEST_BASH_BIN")
        for candidate in (override, "bash"):
            if not candidate:
                continue
            resolved = candidate if os.path.isabs(candidate) else shutil.which(candidate)
            if resolved:
                return resolved
        self.skipTest("no bash interpreter available")

    def run_bash(self, script, *args):
        """Run a strict Bash script with Mole loaded; assert success and return stdout."""
        env = os.environ.copy()
        env.pop("BASH_ENV", None)
        result = subprocess.run(
            [
                self.bash_bin(), "-c",
                'set -euo pipefail\nsource "$1"\nshift\n' + script,
                "mole-trap-test", str(MOLE / "lib/core/timeout.sh"), *args,
            ],
            text=True, capture_output=True, timeout=10, env=env,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result.stdout

    def test_round_trip_preserves_handler_data(self):
        """Verify restoration preserves handler text without executing shell syntax."""
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
        """Verify invalid declarations are rejected without changing traps or state."""
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
        # Zero arguments must be a clean reject under set -u, not an abort.
        with self.subTest(declaration="<no argument>"):
            self.run_bash(
                '''
mutated=0
trap ':' INT
saved=$(trap -p INT)
if mole_restore_trap; then exit 1; fi
[[ $(trap -p INT) == "$saved" && $mutated == 0 ]]
''',
            )

    def test_restoration_callers_preserve_saved_arguments(self):
        """Check callers restore unset, ignored, and quoted handlers in local scope."""
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
                    # Run inside a function so the preamble names are `local`,
                    # matching the real nested-function scoping (bash is
                    # dynamically scoped) instead of exercising globals.
                    self.run_bash(
                        '''
harness() {
    show_cursor() { :; }
    _cleanup_sudo_keepalive() { :; }
    local original_stty="" terminal_restored=false
    local trap_installed_by_this_call=true
    if [[ $1 == set ]]; then
        trap -- "$2" EXIT INT TERM
    else
        trap - EXIT INT TERM
    fi
    local previous_exit_trap previous_int_trap previous_term_trap
    local old_trap_int old_trap_term
    previous_exit_trap=$(trap -p EXIT)
    previous_int_trap=$(trap -p INT)
    previous_term_trap=$(trap -p TERM)
    old_trap_int=$previous_int_trap
    old_trap_term=$previous_term_trap
'''
                        + caller
                        + '''
    local actual_exit actual_int actual_term
    actual_exit=$(trap -p EXIT)
    actual_int=$(trap -p INT)
    actual_term=$(trap -p TERM)
    trap - EXIT INT TERM
    [[ $actual_exit == "$previous_exit_trap" ]]
    [[ $actual_int == "$previous_int_trap" ]]
    [[ $actual_term == "$previous_term_trap" ]]
}
harness "$@"
''', "unset" if handler is None else "set", handler or "",
                    )

    def test_no_eval_remains_in_restore_path_files(self):
        """Guard the trap restoration files against reintroducing eval."""
        # Lock the security property repo-wide, not just inside the sliced
        # functions: these files are eval-free today and must stay that way.
        for path in (
            "lib/core/traps.sh",
            "lib/core/timeout.sh",
            "lib/clean/project.sh",
            "lib/uninstall/batch.sh",
            "bin/uninstall.sh",
        ):
            for lineno, line in enumerate((MOLE / path).read_text().splitlines(), 1):
                with self.subTest(path=path, lineno=lineno):
                    self.assertIsNone(
                        re.search(r"\beval\b", line),
                        f"{path}:{lineno}: eval reintroduced in trap restore path",
                    )

    def test_restored_handlers_execute_only_on_signal(self):
        """Verify restored handlers run on exit or signal delivery, not restoration."""
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

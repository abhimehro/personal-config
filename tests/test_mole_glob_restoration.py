"""Behavioral regressions for PR #2100's shell-option restoration.

Run with: python3 -m unittest tests.test_mole_glob_restoration
Only Bash and the Python standard library are needed. Cleanup dependencies are
stubbed; the real functions run against a disposable HOME, never macOS data.
"""

import itertools
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STATES = tuple(itertools.product((False, True), repeat=2))
FUNCTIONS = (
    "cache_top_level_entry_count_capped",
    "directory_has_entries",
    "clean_app_caches",
    "process_container_cache",
    "clean_group_container_caches",
    "clean_application_support_logs",
    "clean_orphaned_app_data",
    "clean_orphaned_container_stubs",
)

HARNESS = r'''
source "$REPO_ROOT/configs/.config/mole/lib/clean/user.sh"
source "$REPO_ROOT/configs/.config/mole/lib/clean/apps.sh"

# Stub only dependencies, leaving the functions under test intact.
start_section_spinner() { :; }
stop_section_spinner() { :; }
note_activity() { :; }
debug_log() { :; }
log_operation() { :; }
update_progress_if_needed() { :; }
is_critical_system_component() { return 1; }
should_protect_data() { return 1; }
should_protect_path() { return 1; }
is_path_whitelisted() { return 1; }
is_bundle_orphaned() { return 0; }
get_path_size_kb() { printf '4\n'; }
app_support_item_size_bytes() { printf '4096\n'; }
get_epoch_seconds() { printf '1000\n'; }
bytes_to_human() { printf '%s B\n' "$1"; }
cleanup_result_color_kb() { :; }
safe_remove() {
    printf '%s\0' "$1" >> "$REMOVE_LOG"
    return "$REMOVE_STATUS"
}
safe_clean() { printf '%s\0' "$1" >> "$CLEAN_LOG"; }
create_temp_file() { mktemp "$HOME/installed.XXXXXX"; }
scan_installed_apps() { : > "$1"; }

GREEN='' YELLOW='' GRAY='' NC='' ICON_SUCCESS='' ICON_WARNING='' ICON_DRY_RUN=''
files_cleaned=0 total_size_cleaned=0 total_items=0
total_size=0 total_size_partial=false cleaned_count=0 found_any=false
precise_size_used=0 precise_size_limit=64 MOLE_MAX_ORPHAN_ITERATIONS=100

# Observe and optionally corrupt only the saved-state boundary. All real option
# changes still use Bash's builtin. Payloads are printed as data, never evaluated
# by the harness. With the old eval implementation they create the marker.
shopt() {
    if [[ ${1:-} == -p && ( ${2:-} == nullglob || ${2:-} == dotglob ) ]]; then
        printf '%s\n' "$2" >> "$CAPTURE_LOG"
        local saved
        saved=$(builtin shopt "$@" || true)
        case "$STATE_MODE" in
            append) printf '%s%s\n' "$saved" "$STATE_SUFFIX" ;;
            other_option) printf '%s extglob\n' "${saved% *}" ;;
            invalid) printf '%s\n' "$STATE_SUFFIX" ;;
            *) printf '%s\n' "$saved" ;;
        esac
    else
        builtin shopt "$@"
    fi
}

builtin shopt -u nullglob dotglob extglob
[[ $INITIAL_NULLGLOB == 0 ]] || builtin shopt -s nullglob
[[ $INITIAL_DOTGLOB == 0 ]] || builtin shopt -s dotglob
[[ $INITIAL_PIPEFAIL == 1 ]] || set +o pipefail

# Test the outer cache function separately from its group-container dependency.
if [[ $1 == clean_app_caches ]]; then
    clean_group_container_caches() { :; }
fi

# Keep the invocation in this shell, not a command substitution. Only the
# predicate legitimately returns nonzero; unexpected cleanup failures abort.
result=0
if [[ $1 == directory_has_entries ]]; then
    "$@" > "$RESULT_FILE" || result=$?
else
    "$@" > "$RESULT_FILE"
fi
printf 'RETURN=%s\n' "$result"
for option in nullglob dotglob extglob; do
    if builtin shopt -q "$option"; then
        printf '%s=1\n' "$option"
    else
        printf '%s=0\n' "$option"
    fi
done
if [[ -o pipefail ]]; then printf 'pipefail=1\n'; else printf 'pipefail=0\n'; fi
'''


class TestMoleGlobRestoration(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="mole-glob-tests-")
        self.addCleanup(temporary.cleanup)
        self.home = Path(temporary.name)
        self.entries = self.home / "entries with spaces"
        self.entries.mkdir()
        self.container = self.home / "Library/Containers/org.example.app"
        self.cache = self.container / "Data/Library/Caches"
        self.group = self.home / "Library/Group Containers/group.org.example.app/Caches"
        self.support = self.home / "Library/Application Support/Example/GPUCache"
        for directory in (
            self.cache, self.group, self.support, self.home / "Library/Caches",
        ):
            directory.mkdir(parents=True)

    def populate(self, directory):
        paths = [directory / "visible file", directory / ".hidden file"]
        for path in paths:
            path.touch()
        return paths

    def run_function(
        self,
        function,
        *args,
        state=(False, False),
        mode="normal",
        suffix="",
        dry_run=False,
        remove_status=0,
        pipefail=True,
    ):
        # A minimal environment also excludes BASH_ENV and exported shell
        # functions that could override mocks or execute workstation setup.
        env = {
            "PATH": os.defpath,
            "HOME": str(self.home),
            "LC_ALL": "C",
            "REPO_ROOT": str(ROOT),
            "STATE_MODE": mode,
            "STATE_SUFFIX": suffix,
            "INITIAL_NULLGLOB": str(int(state[0])),
            "INITIAL_DOTGLOB": str(int(state[1])),
            "INITIAL_PIPEFAIL": str(int(pipefail)),
            "DRY_RUN": str(dry_run).lower(),
            "REMOVE_STATUS": str(remove_status),
        }
        for key in (
            "REMOVE_LOG", "CLEAN_LOG", "CAPTURE_LOG", "RESULT_FILE", "INJECTION_MARKER",
        ):
            path = self.home / key.lower()
            path.unlink(missing_ok=True)
            env[key] = str(path)
        result = subprocess.run(
            [
                "bash", "--noprofile", "--norc", "-c", HARNESS, "mole-test", function,
                *(str(arg) for arg in args),
            ],
            env=env,
            cwd=self.home,
            capture_output=True,
            text=True,
            timeout=5,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stderr, "")
        self.assertFalse(
            Path(env["INJECTION_MARKER"]).exists(), "saved state executed code",
        )
        observed = dict(line.split("=", 1) for line in result.stdout.splitlines())
        self.assertEqual(
            observed["extglob"], "0", "restoration changed an unrelated option",
        )
        return observed

    def assert_restored(self, observed, state):
        self.assertEqual(observed["nullglob"], str(int(state[0])))
        self.assertEqual(observed["dotglob"], str(int(state[1])))

    def recorded_paths(self, name):
        path = self.home / name
        return path.read_text().rstrip("\0").split("\0") if path.exists() else []

    def arguments(self, function):
        if function in ("cache_top_level_entry_count_capped", "directory_has_entries"):
            return (self.entries,)
        if function == "process_container_cache":
            return (self.container,)
        return ()

    def test_count_restores_options_at_cap_and_after_exhaustion(self):
        self.populate(self.entries)
        (self.entries / "subdirectory").mkdir()
        (self.entries / "subdirectory/nested").touch()
        (self.entries / "broken").symlink_to(self.entries / "missing")
        for state, cap in itertools.product(STATES, (1, 2, 3, 4)):
            with self.subTest(state=state, cap=cap):
                observed = self.run_function(
                    "cache_top_level_entry_count_capped", self.entries, cap, state=state,
                )
                self.assert_restored(observed, state)
                self.assertEqual(
                    (self.home / "result_file").read_text(), f"{min(cap, 3)}\n",
                )

    def test_count_empty_and_missing_directories(self):
        for state, directory in itertools.product(
            STATES, (self.entries, self.home / "absent"),
        ):
            with self.subTest(state=state, directory=directory):
                observed = self.run_function(
                    "cache_top_level_entry_count_capped", directory, state=state,
                )
                self.assert_restored(observed, state)
                self.assertEqual((self.home / "result_file").read_text(), "0\n")

    def test_predicate_restores_options_on_all_return_paths(self):
        hidden = self.home / "hidden only"
        hidden.mkdir()
        (hidden / ".entry").touch()
        (self.entries / "dangling").symlink_to(self.home / "missing")
        for state, (directory, status) in itertools.product(
            STATES, ((self.entries, "1"), (self.home / "missing", "1"), (hidden, "0")),
        ):
            with self.subTest(state=state, directory=directory):
                observed = self.run_function(
                    "directory_has_entries", directory, state=state,
                )
                self.assertEqual(observed["RETURN"], status)
                self.assert_restored(observed, state)

    def test_cleanup_restores_options_with_no_matching_items(self):
        for function, state in itertools.product(FUNCTIONS[2:], STATES):
            with self.subTest(function=function, state=state):
                observed = self.run_function(
                    function, *self.arguments(function), state=state,
                )
                self.assert_restored(observed, state)
                self.assertEqual(self.recorded_paths("remove_log"), [])

    def test_container_cleanup_restores_options_even_when_removal_fails(self):
        paths = self.populate(self.cache)
        for state, remove_status, dry_run in itertools.product(
            STATES, (0, 1), (False, True),
        ):
            with self.subTest(state=state, remove_status=remove_status, dry_run=dry_run):
                observed = self.run_function(
                    "process_container_cache", self.container, state=state,
                    remove_status=remove_status, dry_run=dry_run,
                )
                self.assert_restored(observed, state)
                self.assertCountEqual(
                    self.recorded_paths("remove_log"), [] if dry_run else list(map(str, paths)),
                )

    def test_app_cache_loop_restores_options_after_processing_a_container(self):
        paths = self.populate(self.cache)
        for state in STATES:
            with self.subTest(state=state):
                observed = self.run_function("clean_app_caches", state=state)
                self.assert_restored(observed, state)
                self.assertCountEqual(self.recorded_paths("remove_log"), list(map(str, paths)))

    def test_application_support_preserves_pipefail_and_glob_options(self):
        paths = self.populate(self.support)
        for state, pipefail in itertools.product(STATES, (False, True)):
            with self.subTest(state=state, pipefail=pipefail):
                observed = self.run_function(
                    "clean_application_support_logs", state=state, pipefail=pipefail,
                )
                self.assert_restored(observed, state)
                self.assertEqual(observed["pipefail"], str(int(pipefail)))
                self.assertCountEqual(self.recorded_paths("remove_log"), list(map(str, paths)))

    def test_orphan_sweep_restores_options_between_resource_directories(self):
        paths = [
            self.home / "Library/Caches/org.example.app",
            self.home / "Library/Logs/net.example.app",
        ]
        for path in paths:
            path.mkdir(parents=True)
        for state in STATES:
            with self.subTest(state=state):
                observed = self.run_function("clean_orphaned_app_data", state=state)
                self.assert_restored(observed, state)
                self.assertCountEqual(self.recorded_paths("clean_log"), list(map(str, paths)))

    def test_group_cleanup_restores_dotglob_after_processing_items(self):
        paths = self.populate(self.group)
        for dotglob, dry_run in itertools.product((False, True), repeat=2):
            with self.subTest(dotglob=dotglob, dry_run=dry_run):
                state = (True, dotglob)
                observed = self.run_function(
                    "clean_group_container_caches", state=state, dry_run=dry_run,
                )
                self.assert_restored(observed, state)
                self.assertCountEqual(
                    self.recorded_paths("remove_log"), [] if dry_run else list(map(str, paths)),
                )

    @unittest.expectedFailure
    def test_group_cleanup_restores_disabled_nullglob_after_processing_items(self):
        # Also fails at PR base 2bd4be53: the inner loop overwrites the outer
        # saved nullglob state. Keep this executable regression until fixed;
        # unittest will flag an unexpected success when the defect is resolved.
        self.populate(self.group)
        observed = self.run_function("clean_group_container_caches")
        self.assert_restored(observed, (False, False))

    def test_saved_state_cannot_execute_commands(self):
        for directory in (self.entries, self.cache, self.group, self.support):
            self.populate(directory)
        payloads = (
            '; printf injected > "$INJECTION_MARKER"',
            '\nprintf injected > "$INJECTION_MARKER"',
            '$(printf injected > "$INJECTION_MARKER")',
            '`printf injected > "$INJECTION_MARKER"`',
        )
        for function, state, payload in itertools.product(FUNCTIONS, STATES, payloads):
            with self.subTest(function=function, state=state, payload=payload):
                self.run_function(
                    function, *self.arguments(function), state=state,
                    mode="append", suffix=payload,
                )
                self.assertIn("nullglob", (self.home / "capture_log").read_text())

    def test_saved_state_cannot_target_another_shell_option(self):
        for directory in (self.entries, self.cache, self.group, self.support):
            self.populate(directory)
        for function in FUNCTIONS:
            with self.subTest(function=function):
                self.run_function(
                    function, *self.arguments(function), state=(True, True),
                    mode="other_option",
                )

    def test_predicate_empty_return_does_not_execute_saved_state(self):
        for state in STATES:
            with self.subTest(state=state):
                observed = self.run_function(
                    "directory_has_entries", self.entries, state=state,
                    mode="append", suffix='; printf injected > "$INJECTION_MARKER"',
                )
                self.assertEqual(observed["RETURN"], "1")
                self.assert_restored(observed, state)

    def test_container_stub_loop_restores_options_when_matching_container_has_data(self):
        container = self.home / "Library/Containers/com.macpaw.CleanMyMac.test"
        (container / "Data").mkdir(parents=True)
        metadata = container / ".com.apple.containermanagerd.metadata.plist"
        metadata.touch()
        for state in STATES:
            with self.subTest(state=state):
                observed = self.run_function(
                    "clean_orphaned_container_stubs", state=state,
                )
                self.assert_restored(observed, state)
                self.assertTrue(metadata.exists())
                self.assertTrue((container / "Data").is_dir())

    def test_malformed_saved_state_is_ignored(self):
        for payload in ("", "unrecognized", 'printf injected > "$INJECTION_MARKER"'):
            for function in ("cache_top_level_entry_count_capped", "directory_has_entries"):
                with self.subTest(function=function, payload=payload):
                    observed = self.run_function(
                        function, self.entries, mode="invalid", suffix=payload,
                    )
                    self.assert_restored(observed, (True, True))


if __name__ == "__main__":
    unittest.main()

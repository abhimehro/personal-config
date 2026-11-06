# Disk-safety governor

`scripts/disk-guard.sh` is the operating contract for any long-running,
I/O-heavy job on this workstation: bulk copies, cache reclaims, archive
verification, cloud uploads, index rebuilds. Tests: `tests/test_disk_guard.sh`
(53 assertions, PATH-injected mocks for `df`/`sysctl`/`du`/`memory_pressure`/
`sleep`, so it is deterministic and runs on Linux CI).

Created 2026-11-02 after the Data volume dropped to **128 MiB** available and
the machine became unusable — no new terminal sessions could be opened. The
workflow running at the time had written ~16 MiB.

## What actually caused the exhaustion

Not the workflow. Cumulative output was ~16 MiB against swings of 7+ GiB.
Confirmed contributors:

| Contributor                         | Evidence                                                                                                    | Note                                                                                         |
| ----------------------------------- | ----------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| Swap growth on the Data volume      | `vm.swapusage` total 4096M → 5120M, used 2670M → 3614M **within one session**                               | `/private/var/vm` is on `/System/Volumes/Data`; 8 GiB RAM under heavy GUI load               |
| Running Colima VM with sparse disks | `disk` 1.7 GiB actual / 20 G declared; `datadisk` 5.2 GiB actual / 100 G declared                           | Grows on demand, never shrinks without an explicit stop+recreate                             |
| `sleepimage`                        | 2.0 GiB, `hibernatemode 3`                                                                                  | Real bytes, regenerates                                                                      |
| File Provider materialization       | `~/Library/CloudStorage/**` and the pCloud cache are all `dataless` **now**, but any read materializes them | A background QuickLook/Spotlight touch on a 22.8 GiB movie would consume real disk instantly |

### Red herring, corrected

`find -size +500M` reported 100 G / 22.8 G / 8.6 G files. Those are **apparent**
sizes of `compressed,dataless` File Provider placeholders — zero local bytes.
`du` on the pCloud cache returns 0M, confirming it. Never size cloud paths with
`find -size` or `stat -f %z`; use `du` (actual blocks) and check `ls -lO` for
the `dataless` flag.

### A second accounting surprise

`df` available space appears to **already count resident-but-evictable File
Provider bytes as available** _(Inferred)_. Evicting an 8.59 GiB CloudDocs copy
by hand dropped its parent's `du` from 8,828.9 → 0.0 MiB but moved `avail`
34,693 → **33,432 MiB — down 1.26 GiB, not up 8.6**. Churn suspects totalled
only ~2.45 GiB and no local APFS snapshots existed, so the residual is APFS
purgeable accounting. `diskutil info` printed no purgeable line on darwin 27.2.
**Do not promise a user "this frees N GiB" on the strength of a `du` delta
alone; measure `avail` before and after and report the number you got.**

## The governor

| Command                                               | Behaviour                                                                            |
| ----------------------------------------------------- | ------------------------------------------------------------------------------------ |
| `disk-guard.sh report`                                | avail, swap total/used/free, memory-free %, scratch usage, headroom above hard floor |
| `disk-guard.sh check`                                 | exit 0 ok · 1 pause · 2 abort                                                        |
| `disk-guard.sh budget <bytes> [dest]`                 | refuses a planned write that would breach floor+reserve or the scratch cap           |
| `disk-guard.sh gate <label> [timeout_s] [interval_s]` | `check`, and on PAUSE poll until clear or timeout; never retries an ABORT            |

Configuration is entirely by environment variable, so a caller can retarget the
governor without editing it:

| Variable                                   | Default                   | Meaning                                              |
| ------------------------------------------ | ------------------------- | ---------------------------------------------------- |
| `DISK_GUARD_VOL`                           | `/System/Volumes/Data`    | the volume whose _available_ space is measured       |
| `DISK_GUARD_STATE`                         | `$HOME/.cache/disk-guard` | where `guard.log` is written                         |
| `DISK_GUARD_SCRATCH`                       | `$HOME/jules-analysis`    | the scratch root the cap applies to                  |
| `DISK_GUARD_HARD` / `_PAUSE` / `_WARN`     | `4096` / `6144` / `8192`  | MiB of available space                               |
| `DISK_GUARD_RESERVE`                       | `1024`                    | MiB a single write must leave _above_ the hard floor |
| `DISK_GUARD_SWAP_FREE`                     | `512`                     | MiB of swap free below which we PAUSE                |
| `DISK_GUARD_SWAP_USED` / `_SWAP_TOTAL`     | `4096` / `6144`           | warn-only ceilings                                   |
| `DISK_GUARD_SCRATCH_CAP` / `_SCRATCH_WARN` | `32` / `30`               | MiB                                                  |

### Floors (MiB of _available_ space)

- **HARD ABORT < 4096** — stop the workflow, ask the user to free space.
- **PAUSE < 6144** — no new I/O-heavy work; read-only inspection allowed.
- **WARN < 8192** — proceed, log, say so.
- **RESERVE 1024 above hard floor** for any single planned write.
- **Swap:** PAUSE when swap **free** < 512 MiB — that is the point where macOS
  allocates the next swapfile onto the Data volume and consumes real disk. WARN
  when swap used > 4096 MiB or total > 6144 MiB.
- **Scratch cap 32 MiB**, with a **SCRATCH_CREEP warning above 30 MiB**. Raised
  from 25 on 2026-11-03 (approved) because the overage was entirely cited
  reproduction evidence — the three load-bearing files are named in the comment
  beside `SCRATCH_CAP_MIIB` in `scripts/disk-guard.sh`. Do not delete them to
  get back under the old number, and do not raise the ceiling again: creep means
  something new is accumulating, so investigate it instead. `capture-2/` was
  already pruned 13,964 → 3,344 KiB against a citation intersect, with the
  removed set recorded in `~/jules-analysis/capture-2-prune-manifest.ndjson`.

The first revision paused on `swap used > 4096`, which fired immediately on a
machine that legitimately runs ~4 GiB of swap under normal GUI load on 8 GiB RAM
— it would have blocked all work permanently. Measuring swap _free_ targets the
actual disk-risk condition instead of a normal steady state.

The previous plan's 1.5 GiB abort floor was far too low for a machine that needs
several GiB of slack for churn it does not control.

### Bug fixed from the Tier A+B capture

`capture2.py` compared **absolute free MiB** against `PAUSE_HEADROOM_MiB = 300`,
so the guard never tripped even when true headroom was 176 MiB. `disk-guard.sh`
computes `headroom = avail − HARD_MIIB` and reports it explicitly. Any future
capture script must call `disk-guard.sh budget` rather than reimplementing this.

## Wiring — mandatory

0. **Read before you measure.** Before any disk or cloud step, grep this file
   and the session record first, and measure second. Both facts behind the 2×
   budget error below were already written down here (the `dataless` placeholder
   note in "What actually caused the exhaustion", and the `find -size` red
   herring) — the cost came from re-deriving them at the gate instead of looking
   them up. A measurement answers "how much"; this file answers "what will that
   measurement miss".
1. Call `disk-guard.sh gate <phase-label>` before starting any phase.
2. Call `disk-guard.sh budget <bytes> [dest]` before any write of known size.
   **`<bytes>` must count every byte the operation materialises, not just the
   bytes it writes.** A copy whose _source_ is a `dataless` File Provider file
   costs hydrate(source) + stage(dest) — double the size of the file. Passing
   only the destination size understates the peak by 2× and can turn a passing
   gate into a floor breach. Check `ls -lO` on the source for `dataless` and
   `stat -f %b` for resident blocks before budgeting.
3. **`budget` takes an optional `dest`.** Without it the write is assumed to
   land in `SCRATCH_ROOT` and is checked against both the disk floor and the
   scratch cap. Pass a dest outside scratch (e.g. a CloudDocs path) and the
   scratch-cap branch is skipped — it was written for scratch writes only, so
   applying it elsewhere refuses spuriously. The disk-floor branch always
   applies.
4. Bulk output goes to a remote (`rclone copy` to `gdrive:jules-analysis/`),
   then `rclone check --size-only` before any local trim.
5. **Never** `rclone sync --delete`. **Never** touch `rclone media:` (Jellyfin)
   or `~/CloudMedia` (fuse-t NFS mount — not local disk, `du -x` still counts
   it, and a 1.4 TiB remote shows up on a 228 GiB disk). **"Never touch"
   includes the VFS cache dirs, which live inside `~/Library/Caches`**:
   `rclone-media-mount/` and `rclone-media-webdav/`. A whole-directory
   `~/Library/Caches` sweep deletes them. Both are rebuildable
   (`--vfs-cache-mode full` re-fetches from the read-only remote) so this costs
   re-download latency on Jellyfin streams, not data — but it is still a rule
   violation, and the 2026-11-03 Tier A sweep did exactly that: the manifest
   records `~/Library/Caches` as one 308 MiB unit with no per-entry log, so it
   cannot be proven either way. `rclone-media-webdav/` is absent afterwards,
   `rclone-media-mount/` survived at 148 MiB, and both processes were verified
   alive and serving (mount lists `4K/Documentaries/Kids/Movies/Music/TV Shows`,
   webdav answers 401). **Exclude both by name from any cache sweep, and give
   every container-dir sweep a per-entry manifest.**
6. Run intensive jobs sequentially; no concurrent scans.
7. **Before any prune, prove the keep target exists.** Resolve the keep key,
   enumerate what actually matches it, and **fail closed if it matches zero
   items.** A shape check is not an existence check — see the Raycast error
   below, where an all-digits guard passed and then matched nothing.
8. **Any guard on a long-running job gets an abort-path test with a mocked
   worker before the job is trusted.** A guard that never fires is
   indistinguishable from a guard that never needed to — the 2026-11-03 copy ran
   to completion with a dead swap sensor and nothing failed. Call
   `disk-guard.sh` for the numbers rather than re-parsing `sysctl` in callers,
   and make an unreadable sensor fail closed: `check` and `budget` return PAUSE
   / REFUSED with `SENSOR_UNREADABLE` rather than reporting a healthy state they
   did not measure. `report` prints `NA` per field so a dead sensor is visible
   in the output instead of hiding as an empty column. See
   `~/jules-analysis/phase6-step5-precopy-findings.md` ERROR 3 / 3b.
9. **Validate any new parser against a raw byte dump (`xxd` / `od -c`) before
   trusting it.** Three separate errors in this workflow came from writing a
   match pattern against _rendered terminal output_ instead of the bytes:
   Raycast `last_backup` in seconds compared against millisecond directory
   names; `~/.local/share/uv` assumed to be a cache from its `du` total; and
   `grep -q 'sig:<file-pending>'` against `brctl status`, which emits
   `sig:\033[0;1;30m<file-pending>\033[0m` **even into a pipe** — so the pattern
   never matched and `sig_pending` read a constant `no`, quietly authorising a
   19.9 GiB delete. `NO_COLOR=1`, `TERM=dumb`, `CLICOLOR=0` and
   `CLICOLOR_FORCE=0` all fail to suppress it; only
   `sed -e $'s/\033\\[[0-9;]*m//g'` works. **A parser that silently returns a
   constant or an empty string is worse than one that reports it cannot tell** —
   so pair this with rule 8: make the unparseable case fail closed and say so.
   Cross-reference: `docs/jules-proactive-analysis-2026-11.md` §23 Rule 4.
   **Rule 9 applies to our own harnesses too, and to exit codes as well as
   patterns.** `gitleaks` 8.x exits **1** both when leaks are found _and_ when
   the config fails to parse, so `rc=1 findings=0` is not a verdict — it was
   read as "the allowlist suppressed it" when the run had actually died on
   `FTL Failed to load config`. Classify each run from stderr (`FTL` /
   `unable to load` / `Failed to load config`) plus whether the report file
   exists, is non-empty, and parses; only then count findings. Two related
   traps: findings require `--report-format json --report-path` at all, because
   8.30.1 prints only a three-line summary to stdout; and an unknown flag exits
   **126** with usage text (`gitleaks git` takes a positional `[repo]`, not
   `--source`), which is also not a scan result. Encoded permanently in
   `tests/test_gitleaks_allowlist.sh`, which fails closed on a parse failure or
   a missing report rather than reporting a clean scan.
10. **Absence plus a positive signal, never absence alone.** "The item is no
    longer in the dirty set" is weak evidence that a job succeeded; it is
    equally consistent with the sensor not looking at the item. Pair every
    absence check with a positive one. For a File Provider upload that means
    `fileproviderctl evaluate` (`isUploaded = 1`, `isUploading = 0`, and a
    `versionIdentifier` whose embedded server etag has **advanced** — it decodes
    as protobuf, `0a 05 32 6f 6e 6b 71` → `2onkq`) alongside absence from
    `brctl status`. Cross-reference: §23 Rule 5.

## Reclaim executed 2026-11-03 — 19.5 GiB (Tier A + one Tier B item)

avail **9,340 MiB → 29,351 MiB** (re-measured 27,126 MiB later; churn). Volume
**96% → 87%**. Manifest `~/jules-analysis/tier-a-reclaim-manifest.tsv`, script
`~/jules-analysis/reclaim-tier-a.sh`, findings
`~/jules-analysis/phase6-step5-precopy-findings.md`.

| Freed MiB | Item                                                                                                                                                                         |
| --------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 6,456     | `~/.cache/trunk` — daemon killed by signal first; it recreated only empty dir skeletons (0 MiB) and is not under launchd, so it stays down until the next `trunk` invocation |
| 7,116     | Raycast backup sets — **all 5, intended 4; see the error below**                                                                                                             |
| 5,229     | `com.google.AIEdgeForesight` (Tier B, explicitly approved)                                                                                                                   |
| 890       | `~/dev/.gitnexus-diagnostics/.../node_modules` (idle, clean git status, no open handles)                                                                                     |
| 308       | `~/Library/Caches` — 11 Apple-protected entries refused EPERM (CloudKit, Safari, HomeKit, textunderstandingd, …) and were left alone                                         |
| 1         | `~/Library/HTTPStorages/com.google.AIEdgeForesight`                                                                                                                          |

Export verified untouched before and after: 0 files newer than `NONMOD-MARKER`,
`tmutil listlocalsnapshots /` empty.

### Excluded: `~/.local/share/uv` is not a cache

The survey listed it at 1,543 MiB as "uv cache". **`uv cache dir` is
`~/.cache/uv`, which does not exist.** The directory holds 1,250 MiB of
installed tools (`google-agents-cli`, `mistral-vibe`, `omnigent`, `tavily-cli`)
and 294 MiB of **9 managed CPython versions**. Deleting it would have broken
`scripts/proactive-worktree.sh:336`, which uses `uv run --all-extras ruff` as
tier 2 of the AST gate's fail-closed resolution — with pyflakes also absent on
this host, the gate would have failed closed against every Python repo, silently
disabling the R1 semantic gate. Verified intact after the run. Real Tier A was
**~13.3 GiB, not the 15.9 GiB reported.**

Same class as the Raycast-count error: a `du` total was labelled from what such
a directory usually holds instead of asking the tool. `uv cache dir` is one
command.

### Error: Raycast keep-logic deleted all 5 sets instead of 4

`last_backup` holds **`1793676621`** (seconds precision); the set directories
are **`1793676621455`** (milliseconds). The keep key matched nothing, so all
five went, including the newest. The `case "$KEEP" in ''|*[!0-9]*)` guard did
not fire because the value _is_ all digits — **it validated the shape, not the
semantics.** Freed 1,424 MiB more than intended. Raycast's live `ai.db` is
untouched; only rollback snapshots are gone and Raycast recreates one on its
next ~12 h cycle. `last_backup` now names a set that no longer exists. Not
recoverable. Reuse fix: match on prefix (`[[ "$name" == "$KEEP"* ]]`), not
equality.

Generalised as Wiring rule 7: **resolve the keep key, enumerate what matches it,
and fail closed on zero matches.** The `case … *[!0-9]*` guard was not wrong, it
was answering a different question — "is this shaped like a number" instead of
"does this name a directory that exists". User verdict: _"validate that the keep
target exists before deleting anything. Shape checks aren't enough."_

**Approved retention job (not yet written).** A daily launchd prune following
the repo's `maintenance/` pattern: keep the newest **2** sets, never delete the
set `last_backup` names (**prefix** match), **fail closed if `last_backup`
matches 0 dirs or more than 1**, and ship the **first run in dry-run** logging
what it _would_ delete for review before it goes live. It holds until Raycast
has written a fresh backup worth protecting — pruning against a `last_backup`
that names nothing is the exact failure above.

### Eviction is not forceable from the CLI (re-verified two ways)

- `brctl` exposes exactly six commands: `diagnose`, `log`, `dump`, `status`,
  `accounts`, `monitor`. No eviction.
- `fileproviderctl` exposes `dump`, `diagnose`, `evaluate`, `check`, `repair`.
  `evaluate` only _reports_ applicable Finder actions; it does not perform them.
  On a Google Drive item the set is `PIN`/`UNPIN`/`OPEN`/`SHARE`/`COPY_LINK`/
  `ADD_SHORTCUT`/`OPEN_REVISION_FOLDER`/`CREATE_*_FILE` — pin/unpin is a
  download _preference_, not an eviction.

So a hydrated file can only be evicted via Finder ("Remove Download") or
automatically under pressure. Budget for it staying resident, and verify an
eviction on **both** axes: `stat -f %b` (resident blocks near 0) **and**
`ls -lO` (`flags` showing `dataless`). If it re-hydrates, check whether the item
or any parent is pinned to "Keep Downloaded" (`isKeepDownloaded` /
`isRecursivelyDownloaded` from `fileproviderctl evaluate`) before retrying.

**Decision (user, 2026-11-03):** eviction is dropped as a workflow step. It is
**Finder ▸ Remove Download, manual, the user's call** — never scripted.
Automatic eviction under pressure is the fallback, not the plan. Any step that
assumed "then evict the local copy" must instead be budgeted as _the bytes
stay_, and the mechanism chosen should minimise what has to stay: Variant B
(rclone from the `gdrive:` remote to an ordinary local path) leaves 8.6 GiB
behind where the filesystem `cp` left 17.2 GiB, because reading through the
remote never hydrates the local `dataless` placeholder.

## Archival must not stage locally

The original plan's "move `~/jules-export` to iCloud for final archival" would,
if done with Finder or `mv` into `~/Library/Mobile Documents`, copy **19.9 GiB
locally first**, then upload, then evict. On this machine that is guaranteed
exhaustion — and it is exactly the File Provider staging circularity the plan
review flagged.

**Required instead:** copy by streaming from a remote
(`rclone copy gdrive:… →
CloudDocs`), verify **by content** against a known hash
plus an independently-sourced checksum, confirm the upload completed with a
positive sensor (rule 10), and only then remove the local original — with
`disk-guard.sh gate` passing at each step and `NONMOD-MARKER` plus
`tmutil listlocalsnapshots /` re-checked _immediately before_ the delete rather
than at the start of the run.

Executed 2026-11-03: three verified copies at `sha256=71c643c2…` / 9,225,417,876
bytes (OneDrive, Google Drive, iCloud), the local 19.9 GiB tree deleted through
a dry-run-first fail-closed gate (+19,941 MiB, volume 96% → 84%), and the
CloudDocs copy then evicted by hand to `resident_blocks=0`. Full record:
`docs/jules-proactive-analysis-2026-11.md` §4 steps 5–8 and §25.

## Reclaim executed 2026-11-02 — 10.57 GiB

avail **7,637 MiB → 18,462 MiB**; headroom above hard floor **14,347 MiB**. Swap
total fell 5120M → 4096M and memory-free rose 33% → 45% after the VM stop.
Export verified untouched (0 files newer than `NONMOD-MARKER`, 19.5 GiB).

| Tier         | Freed   | Items                                                                                                                       |
| ------------ | ------- | --------------------------------------------------------------------------------------------------------------------------- |
| 1 caches     | 217M    | GeoServices 50M, huggingface 87M, npm `_cacache` 42M, `brew cleanup -s`                                                     |
| 2 models     | 7,917M  | superwhisper/models 3095M, WillowMac/OfflineModel 2765M, AIEdgeForesight/model_cache 2057M                                  |
| 3 Node       | 790M    | fnm v22.22.0/v24.12.0/v25.2.1, nvm v25.8.2 (active node is Homebrew v26.13.0)                                               |
| 4 safe split | 1,913M  | `.copilot/Library/Caches` 546M; `.aside/{models,runtime}` 640M; `.agent-browser/browsers` 367M + mistral-canary caches 360M |
| — VM         | 0 bytes | `colima stop` (0 containers running) — removes RAM pressure and halts sparse-disk growth                                    |

### Tier 4 was re-scoped mid-execution

Approved as "3.5 GiB of duplicate agent runtimes." Inspection found **all four
targets hold credentials or session state**, so only bulk binaries and caches
were removed and every auth artifact was preserved and verified:

`.qoderwake/.auth/{token,job_token,custom-config-secrets}` ·
`.aside/u/0/credentials.json`

- `state.db` + `sessions/` ·
  `.agent-browser/mistral-canary/Default/{Login Data,History,Sessions}` ·
  `.copilot/{mcp-secrets,session-state,data.db}`

`.qoderwake` was **skipped entirely**: `runtime-generations` holds a single live
generation (`A` + `state.json`), not superseded ones, and the analysis is
running inside Qoder.

## Remaining reclaim opportunities (not executed)

| Item                                     | Size      | Why it is still open                                                                                                                                                                                                                   |
| ---------------------------------------- | --------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `~/.devin-next`                          | 633M      | **Stale, not live** — `argv.json` + `extensions/`, 0 files modified since Sep 1, last touched Aug 27–31. Independent of `~/.local/share/devin` (no symlinks either way).                                                               |
| `~/.local/share/devin`                   | 628M      | **LIVE — do not delete.** Holds `credentials.toml` and `cli/` with 755 files modified since Sep 1, last touched Oct 29. The `devin` CLI is a Homebrew cask symlink. This inverts the assumption that `devin-next` was the one to keep. |
| `sleepimage`                             | 2.0G      | Needs `sudo` (no passwordless sudo here): `sudo pmset -a hibernatemode 0 && sudo rm /private/var/vm/sleepimage`. Deferred by the user: tied to a separate `hibernatemode` decision.                                                    |
| `colima delete`                          | 6.9G      | VM is now stopped; deletes both sparse disks and 4 re-pullable images. Reclaimable inside the guest: 3.26 GiB images + 2.29 GiB build cache — but a guest-side prune does **not** shrink the host sparse files.                        |
| `~/.gitnexus/{stores,embedding-runtime}` | 1.27G     | Live index for `personal-config` (`store.json` → `stores/personal-config-957eed05dee6`). Costs a re-index; AGENTS.md mandates GitNexus impact analysis before edits. Not approved.                                                     |
| `~/.cursor-server`, `~/.omp`             | 2.97G     | Explicitly kept — actively used hosts.                                                                                                                                                                                                 |
| ~~`~/jules-export`~~                     | ~~19.5G~~ | **DONE 2026-11-03** — deleted after three cloud copies verified by content.                                                                                                                                                            |
| Raycast log/cache dirs                   | —         | Deferred by the user: controld workflows may read them.                                                                                                                                                                                |

No deletions were performed without approval; the only sudo-requiring item was
left to the user.

## Where the underlying evidence lives

The incident record, manifests and one-shot reclaim scripts are **not** in this
repo — they are in `~/jules-analysis/`, alongside the durable narrative in
`docs/jules-proactive-analysis-2026-11.md` §25, which tabulates every artifact
behind every number above. What belongs in the repo is the governor, its
contract, and its tests; what belongs in scratch is the run-specific evidence.

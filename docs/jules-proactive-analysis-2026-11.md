# Jules Proactive Workflow — Durable Analysis and Antigravity Design Record

**Generated 2026-11-02.** Self-contained by design: this document is written to
survive the archival of the Jules export it analyses. Nothing here requires
`~/jules-export`, `~/jules-analysis`, or a working Jules account to read or act
on. Operational instructions for the Antigravity sweep itself live in
[antigravity-proactive-migration.md](antigravity-proactive-migration.md); this
document is the evidence and the reasoning behind it.

Google Jules becomes **read-only on 2026-11-11** and winds down **2026-12-31**.
The proactive channel is the capability worth preserving — it was the
highest-yield class of work in the entire export (69–79% completion against
34–43% for user- and schedule-originated sessions) and it has no replacement
once Jules stops.

### TL;DR — one screen

**Key numbers.**

| Metric               | Value                                                                                                                                                                                                                                                                                                                    | §        |
| -------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | -------- |
| Export analysed      | 19.5 GiB, **7,691 sessions**, 26 repos, captured 2026-10-31, verified untouched                                                                                                                                                                                                                                          | §1       |
| The burst            | **144 sessions in 15m17s** on 2026-11-01, after ~3 months dormant                                                                                                                                                                                                                                                        | §6       |
| Proactive PR outcome | **113 opened → 110 still open, 3 merged = 2.7%**, 0 comments, 0 review comments; #2661 and #2666 are the same work landed twice                                                                                                                                                                                          | §6       |
| Failure mechanism    | 22 FAILED; **91% ended blocked on a human**, not on the code; **59% still held a finished patch**                                                                                                                                                                                                                        | §7       |
| Duplication          | **35.0% exact / 75.2% fuzzy** in the burst, against a **7.0%** 8-month baseline                                                                                                                                                                                                                                          | §9       |
| Recovered work       | 9 orphaned patches that never reached GitHub; **7 promoted as 7 scoped draft PRs**                                                                                                                                                                                                                                       | §7.1/§21 |
| Archive integrity    | **No cloud copy is corrupt.** OneDrive + Google Drive both hash to `71c643c2…`, decompress clean, their 34,243 entries reconcile with the local tree at **zero omissions**, and four streamed members **byte-match local**. Proton holds a _different_ compression, 1 byte longer (§3 corrects an earlier wrong verdict) | §3       |
| Secrets              | **Nothing to rotate.** 199 of 204 prefix hits were unanchored-regex noise; all 9 gitleaks findings are fixtures or negative assertions                                                                                                                                                                                   | §23      |
| Shipped              | **R1** (base-relative verify + worktree-collision gate) at `ea292c9a`; semantic test-coverage gate and `git fetch` precondition at `724505e6`; #2686 gitleaks pre-commit                                                                                                                                                 | §20      |
| Remaining build      | R2–R4 = **24 h**, 20 h of it on the R2→R3 critical path; filed as #2695 / #2696 / #2697                                                                                                                                                                                                                                  | §18      |

**Decisions taken.** Seven gaps (G-1…G-7) drive every gate; G-4 and G-5 are
shipped, the rest are filed as independently assignable issues. Review SLA is
**5 business days with decay** — auto-expiry labels and closes the PR, one-click
reopen, `decision_rate ≥ 80%`, and the throttle _loosens_ as the backlog clears
instead of stopping hard. Confidence is a **uniform ≥2 independent signals** for
every lens, with one narrow exception: `sentinel` may _surface_ a finding on a
single signal as an advisory draft, but anything that changes state still
requires two. **No security veto** — security findings are 6.5× over-represented
in failures but fail for generic process reasons, so a veto would suppress the
highest-value class. Verification is **base-relative**: a check that also fails
on base is `PRE_EXISTING_FAILURE` and the candidate is still promoted, rather
than being discarded for somebody else's breakage.

**Open items.**

1. **iCloud copy #3 is blocked on local staging — but the unblock is a cache
   reclaim, not a cloud workaround.** The order is copy #3 → hash → delete →
   archive, because three verified copies must exist before anything is removed.
   But writing the 8.59 GiB tarball into
   `~/Library/Mobile Documents/com~apple~CloudDocs/` stages it **locally
   first**, and `disk-guard.sh budget 9225417876` returns **REFUSED** — measured
   three times as avail swung, leaving 4,333 → 282 → **829 MiB** against a 5,120
   MiB requirement (`HARD 4096 + RESERVE 1024`). iCloud itself has room —
   121,130,689,460 bytes (~112.8 GiB) of quota remaining — and File Provider
   _does_ evict afterwards (only 31 MiB of the whole tree is resident; 10 of 40
   top-level entries are `compressed,dataless`). The problem is the transient
   peak, and `brctl` offers no way to force eviction if the upload stalls.
   **Cheapest unblock: reclaim Tier A, 15.9 GiB of purely rebuildable caches**
   (Trunk 6.2, five Raycast backup sets 7.1, uv 1.5, a stray `node_modules`
   0.9). The shortfall is only 4,291 MiB, so that is a 3.7× margin and the same
   write then passes through the **plain filesystem path — no rclone, no Apple
   2FA**. Ranked read-only menu in `disk-survey-2026-11-03.md`. rclone's
   `iclouddrive` backend is the _fallback_, and **its streaming behaviour is
   UNVERIFIED** — an earlier revision of this item asserted it "streams in
   chunks and never stages the whole object"; that claim is retracted, because
   enumerating the backend's config options in v1.74.2 shows no chunking option
   and rclone's docs state no maximum object size, no chunk size and no
   streaming guarantee. `ICLOUD-RUNBOOK.md` therefore leads with a 500 MiB
   canary that settles it by measurement. Target dir confirmed: `HomeBackup/` at
   the CloudDocs root (it does not exist yet), **not** Desktop or Documents —
   `brctl status` reports `Desktop & Documents: current=YES`, so their sync is
   live.
2. **Deleting the local 19 GiB tree — approval-gated, evidence-complete, but now
   sequenced _after_ copy #3.** Every technical precondition is closed: the
   extraction spot-check passed and `tmutil listlocalsnapshots /` is empty, so
   deletion really does reclaim the space (§3). It waits on copy #3 hashing
   clean, then a re-check of `NONMOD-MARKER` and `tmutil` **immediately before**
   the delete, then explicit approval (§4 step 7).
3. **Proton verification is blocked, not pending.** All 5 parts are `dataless`,
   `brctl` has no eviction subcommand on this host, and rclone's `protondrive`
   backend is unconfigured — so hashing them would hydrate 9.2 GiB permanently
   against a 4 GiB floor. It is also **unnecessary**: the parts are a different
   compression, not the backup of record (§4).
4. **`canary-stage` timezone** — the disposable cron canary hardcodes UTC while
   the pilot sidecars run `America/Chicago`, so it does not yet test the pilot
   schedule (#2700, §17).

**Closed since the last revision:** `sessions.json` is confirmed byte-identical
on both clouds (`13422e16…`), archive _repair_ is struck as unnecessary, the
**extraction spot-check passed** — four streamed members (`sources.json`,
`errors.json`, `export_jules.py`, `sessions.json`) byte-match local — and the
**testing-lens design question is settled**: folded into `code-health` with
`--focus` for R1, with explicit promotion criteria at the R1 readout (§24).
Remaining live questions are tabulated in §24; §25 lists the artifacts behind
every number above.

### Evidence labels

Every claim below carries one of three labels.

| Label         | Meaning                                                                       |
| ------------- | ----------------------------------------------------------------------------- |
| **Confirmed** | Directly present in the export records or verified against live GitHub        |
| **Inferred**  | Pattern-based; the mechanism is evidenced, the generalisation is not          |
| **Open**      | Needs investigation; stated so a later reader does not mistake it for settled |

### Statistical honesty, up front

The failure taxonomy rests on **n = 22** FAILED sessions from a single 15-minute
burst. At a 50% proportion that is **±21% at 95% confidence**. The percentages
below describe _mechanism_, not _rate_: each failure is traced to a named
session and a named file, which is strong evidence for "this is how it broke"
and weak evidence for "this is how often it breaks". Where a steady-state number
matters, the **8-month baseline** (~7,691 index rows: 7.0% duplication, 2.4%
failure) is the fair measure and is cited as such.

---

# Part I — Archive provenance and integrity

## 1. What was analysed

**Confirmed.** The source export is a 19.5 GiB uncompressed tree at
`~/jules-export`, captured **2026-10-31**. It was treated as strictly read-only
throughout: a `NONMOD-MARKER` file establishes that **0 files in the tree are
newer than the marker**, so no analysis step modified the source.

All analysis wrote only small derived artifacts to a separate workspace
(`~/jules-analysis`, peaking at 38 MiB of scratch against a 19.5 GiB source —
0.2%, pruned to 28 MiB once the findings landed here; see §25). Large files were
streamed, sampled, or indexed rather than loaded; intensive jobs ran
sequentially; a disk-safety governor (§25) gated every step against a hard
free-space floor after two host-level "insufficient disk space" incidents made
the machine unusable.

`~/jules-export/sessions.json` is a **264 MiB** list of **7,691 sessions**. The
largest single object encountered was `session.json` at **3.58 GiB**, which is
why the capture path is field-masked and incremental rather than a copy.

## 2. Integrity manifest

**Confirmed.** These values are transcribed here so the integrity reference
survives the archival of the export and of the scratch workspace that produced
it. The originals also live on all three clouds (§3 records exactly which
artifact is where).

**These two manifests certify two different files, and mixing them up is what
produced the false corruption verdict corrected in §3.** The whole-archive hash
certifies the `.tar.zst` on OneDrive and Google Drive (compression run B,
9,225,417,876 bytes). The per-part hashes and sizes certify the five parts on
Proton (compression run A, 9,225,417,877 bytes). Neither validates the other.

Whole-archive SHA-256 (`jules-export-20261031.tar.zst`, run B) — **verified
2026-11-02 against both cloud copies, exact match**:

```
71c643c21298373ab66b011331f384014037c60e68a8575b9a2e52ddbfcfd58e
```

Per-part SHA-256 (`jules-export-20261031.sha256`, 520 bytes, written 2026-11-01
**01:17**, certifying run A on Proton — **not yet verified against the part
bytes**; see the blocker in §4):

```
4a1cb93f792b1a71480e7f1aa987ef62305ea2ae670a21da1a8056e98a0fb569  jules-export-20261031.tar.zst.part-aa
d76adfab030b29a5fd698d8556b97fbafe95b14c21330dd4a6d2fb3e474389f8  jules-export-20261031.tar.zst.part-ab
200d38ddf7594eccd37f3854c5d950b18dad429e4f75f60cedf522e90401b499  jules-export-20261031.tar.zst.part-ac
f24434624f8f36501a7aefaf9bd54041c32cad4213f342a072b796b34e63636a  jules-export-20261031.tar.zst.part-ad
b9886a6e63acd4a86c9155d0ffca1bccb214e2e60078aefb21cd4bd194635069  jules-export-20261031.tar.zst.part-ae
```

Per-part sizes (`jules-export-20261031.sizes`):

```
2147483648  part-aa  (2.00 GiB)
2147483648  part-ab  (2.00 GiB)
2147483648  part-ac  (2.00 GiB)
2147483648  part-ad  (2.00 GiB)
 635483285  part-ae  (606.04 MiB)
9225417877  TOTAL    (8.59 GiB)
```

The arithmetic checks: `2147483648 × 4 + 635483285 = 9225417877`.

**This number is _not_ a fast integrity test, and treating it as one caused the
false alarm in §3.** It is the expected size of a reassembly of _run A's parts_.
It says nothing about run B's `.tar.zst`, which is legitimately 9,225,417,876
bytes and independently verified. A size expectation derived from one artifact
must never be applied to another. The fast integrity test for the cloud archive
is its SHA-256 above, and the fast _structural_ test is
`rclone cat … | zstd -dc | tar -t | wc -l` → 34,244 with all stages exiting 0.

Archive contents, **confirmed by direct listing on 2026-11-02**: **34,243
entries** excluding the root, including all **7,672 session directories**. This
reconciles exactly with the local tree — see §3.

## 3. The three clouds hold two _different_ archives — and neither is corrupt

> **Correction, 2026-11-02.** This section previously concluded that the
> OneDrive and Google Drive copies were each truncated by one byte and that
> Proton's five parts were the only intact copy. **That conclusion was wrong.**
> It was drawn from size arithmetic alone, before a single byte of the cloud
> archives had been read. Direct verification is recorded below and supersedes
> it; §4's repair plan is revised to match.

**Confirmed by streaming verification on 2026-11-02.** Every check below ran
with zero local staging — `rclone cat` piped straight into the hasher or
decompressor, so nothing ever landed on disk.

| Cloud        | Artifact                                      | Bytes                 | sha256                              | Verdict                                                  |
| ------------ | --------------------------------------------- | --------------------- | ----------------------------------- | -------------------------------------------------------- |
| OneDrive     | `jules-export-20261031.tar.zst`               | 9,225,417,876         | `71c643c2…`                         | ✅ matches the recorded manifest exactly                 |
| Google Drive | same                                          | 9,225,417,876         | `71c643c2…`                         | ✅ matches the recorded manifest exactly                 |
| Proton Drive | 5 split parts + `.sizes` + per-part `.sha256` | sums to 9,225,417,877 | per-part, `4a1cb93f…` for `part-aa` | ⚠️ a **different compression**, not a split of the above |

Three independent results:

1. **Hash identity.** Both cloud archives hash to
   `71c643c21298373ab66b011331f384014037c60e68a8575b9a2e52ddbfcfd58e` —
   byte-for-byte the value recorded in `jules-export-20261031.tar.zst.sha256`.
2. **The compressed stream is complete and self-verifying.**
   `rclone cat … | zstd -dc | tar -t | wc -l` returned **34,244** entries with
   **every stage exiting 0**. The frame header (`28 b5 2f fd 04 58 …`) carries
   **Content_Checksum_flag = 1**, so zstd verified an xxhash64 over all ~19.5
   GiB of decompressed output before exiting 0. **A truncated stream cannot pass
   its own content checksum.**
3. **The entry list reconciles exactly with the local tree.** Diffing the
   archive's full listing against `find ~/jules-export -mindepth 1`:

   |                                  | count  |
   | -------------------------------- | ------ |
   | Archive entries (excluding root) | 34,243 |
   | Local tree entries               | 34,248 |
   | In local but not in archive      | **5**  |
   | In archive but not in local      | **0**  |

   The 5 are exactly `.DS_Store` (×3: root, `repos/`, `sessions/`),
   `__pycache__`, and `__pycache__/export_jules.cpython-315.pyc` — Finder
   metadata and Python bytecode, precisely what an archive command should
   exclude. **Nothing substantive is missing**, all 7,672 session directories
   are present, and no local entry has an mtime later than the archive's
   creation.

### What the 1-byte difference actually is

**Not a truncation.** The first 2,147,483,648 bytes of the cloud archive hash to
`b2681d8661ab8b7f90fc54f5bac2be91c6e623ba8fcf7fc39b89590c0b6c5c2c` (byte count
verified via `tee | wc -c`; hash reproduced across two independent runs). The
recorded hash of Proton's `part-aa` is
`4a1cb93f792b1a71480e7f1aa987ef62305ea2ae670a21da1a8056e98a0fb569`. They differ,
so **the parts are not a split of the cloud archive**. They are a separate
compression of the same tree, one byte longer, produced under different zstd
settings, thread count, or version.

The mtime timeline — originally read as proof of a faulty reassembly — proves
the opposite. The two artifacts are **18 hours apart**, so no reassembly ever
happened:

| When (2026-11-01) | Artifact                                                         |
| ----------------- | ---------------------------------------------------------------- |
| **01:17**         | `.sizes` + per-part `.sha256` written                            |
| **01:19–01:25**   | 5 parts uploaded to Proton — compression run **A**               |
| **19:23:40**      | `jules-export-20261031.tar.zst` created — compression run **B**  |
| **20:00:50**      | `.tar.zst.sha256` = `71c643c2…` computed from run **B**'s output |

`71c643c2…` therefore certifies run B's archive correctly and completely. The
general lesson the earlier draft drew survives, but it applies to a different
situation than the one alleged: **a checksum computed after a transformation
certifies the transformation's output, not its input.** Here that is exactly
what is wanted, because run B's output _is_ the artifact being backed up.

**Where the earlier reasoning went wrong.** It treated `.sizes` TOTAL as ground
truth for the cloud file's expected length. `.sizes` describes run A. Comparing
run B's length against run A's manifest and finding a 1-byte deficit
manufactured a confident corruption verdict out of two numbers that were never
measuring the same object. **Size arithmetic across artifacts that are not the
same artifact is not evidence of anything.** The verdict felt airtight because
the arithmetic _was_ airtight — the premise underneath it was not.

### Consequences — revised

- ✅ **Repair is unnecessary.** Old step 3 ("reassemble correctly, replace the
  two truncated copies") is struck. There is nothing truncated. Both cloud
  copies are complete, hash-verified, and checksum-verified.
- ✅ **The Proton single-point-of-failure concern is void.** Proton holds a
  _third_ copy in a different compression, not the sole intact one.
- ⚠️ **The two archives are not interchangeable.** Restoring from Proton's parts
  yields a byte-different file that will **not** hash to `71c643c2…`. Any
  verification or restore procedure must state which artifact it means. The
  per-part `.sha256` manifest validates run A only; `71c643c2…` validates run B
  only.
- ✅ **`sessions.json` is confirmed byte-identical on both clouds** —
  `13422e1691db14f7412b74e2a904048e82c275056aff7a45c6157e37fb3e4bf6`, matching
  local, at 276,431,176 bytes. This closes the "size match is not content match"
  open item (see the Resolved table in §24).
- ✅ **`repos/` being partially mirrored as loose cloud files costs nothing.**
  OneDrive holds 2.2 KiB / 18 objects and Google Drive 12.2 KiB / 19 objects
  against local's 84 KiB / 10 entries — but the full `repos/` subtree is
  _inside_ the verified tarball, and the entry diff above shows zero omissions.
- ✅ **Deleting the local 19 GiB tree (now §4 step 7) is fully supported by
  evidence, and now gated only on explicit approval.** The remaining gap — an
  extract-and-byte-compare — is closed. Four members were pulled straight out of
  the compressed cloud stream
  (`rclone cat | zstd -dc | tar -xO <member> |
  shasum -a 256`, no disk write)
  and hashed against the local tree:

  | Member            | sha256[:12] archive | local          | Verdict |
  | ----------------- | ------------------- | -------------- | ------- |
  | `sources.json`    | `42b35538058e`      | `42b35538058e` | MATCH   |
  | `errors.json`     | `87267bba344e`      | `87267bba344e` | MATCH   |
  | `export_jules.py` | `5fc87fb3fb1c`      | `5fc87fb3fb1c` | MATCH   |
  | `sessions.json`   | `13422e1691db`      | `13422e1691db` | MATCH   |

  The sample is deliberately spread: two tiny metadata files (943 B, 9,892 B),
  one source file (94,739 B), and the 276,431,176 B payload. `sessions.json` is
  the strongest single data point in the whole record — the archive member, the
  local file, and both loose cloud copies all agree on `13422e1691db…`. What
  remains before deletion (now §4 step 7) is **not** verification but ordering
  and approval: iCloud copy #3 must exist and hash clean first (step 5,
  currently blocked on local staging), then `tmutil
  listlocalsnapshots /` and
  `NONMOD-MARKER` get re-checked immediately before the delete. As of this
  writing the snapshot list is empty (so deletion genuinely reclaims the space
  rather than leaving it held by a snapshot) and the export still shows 0 files
  newer than `NONMOD-MARKER`.

**Throughput measured, not assumed.** 276 MiB in 12.5 s; 9.2 GiB in ~4 min
(`00:41:36Z → 00:45:37Z`), i.e. **~37 MiB/s**. The earlier "bandwidth-bound,
budget hours" caution was over-conservative by roughly an order of magnitude:
all of the verification above — two 9.2 GiB whole-file hashes, a full
decompress-and-list, a 2 GiB prefix hash, two 264 MiB hashes, and four more 9.2
GiB passes for the extraction spot-check — completed in about 36 minutes of wall
time.

## 4. Archive plan and its gate

Revised 2026-11-02 after §3's verification. **The repair this section originally
described is unnecessary** — nothing is truncated. What remains is an optional
check of the third copy and then the space decisions.

Steps 1, 2 **and the extraction spot-check** are **done**; their results are in
§3. Every step below streams through `rclone cat` and lands nothing on local
disk.

1. ~~**Verify Proton's parts.**~~ → **Done in the only sense that matters.** §3
   established the parts are a _different compression_, not a split of the cloud
   archive, so hashing them cannot validate the backup that is actually relied
   upon. Verifying them remains **optional** and is currently **not feasible
   under a streaming-only constraint** — see the blocker below.
2. ✅ **Structural checks — done, and they passed.**
   `rclone cat … | zstd -dc | tar -t | wc -l` returned 34,244 entries with every
   stage exiting 0; `Content_Checksum_flag = 1` means zstd verified an xxhash64
   over all ~19.5 GiB of decompressed output. Both cloud archives hash to
   `71c643c2…`, matching the recorded manifest. The listing diffs clean against
   the local tree with **zero omissions**.
3. ⛔ **~~Repair OneDrive + Google Drive~~ — struck.** There is no faulty
   reassembly to repair. Executing this step as originally written would have
   _replaced two verified-good archives with a byte-different file_ built from a
   different compression run — actively destroying a known-good state while
   believing it was a fix.
4. **Re-verify all three clouds — reduced in scope.** OneDrive and Google Drive
   already agree on both size **and** hash (§3). What is left is optional:
   confirm Proton's parts against their own per-part manifest, which validates
   run A only.
5. ⛔ **Copy the verified archive to iCloud as copy #3 — BLOCKED on local
   staging.** (Was step 6; **moved first** so that three verified copies exist
   before anything is deleted.) Target `HomeBackup/jules-export/` at the
   CloudDocs root — **not** Desktop or Documents, whose sync `brctl status`
   confirms is live (`Desktop & Documents: current=YES`); `HomeBackup/` does not
   exist yet. iCloud has ample room — `brctl quota` reports **121,130,689,460
   bytes (~112.8 GiB) remaining** — and the cost is 8.59 GiB (7.7%) versus 19
   GiB (17%) for the tree. **But the write stages locally first**:
   `disk-guard.sh budget 9225417876` returns **REFUSED**. The margin got worse
   while it was being measured — first 4,333 MiB against a 5,120 MiB requirement
   (`HARD 4096 + RESERVE 1024`), then **282 MiB** as volume avail fell 11,587 →
   9,083 MiB (Data volume 96% used). File Provider _does_ evict afterwards (only
   31 MiB of the whole CloudDocs tree is resident; 10 of 40 top-level entries
   are `compressed,dataless`), but the transient peak breaches the floor and
   `brctl` has no eviction subcommand to force it down if the upload stalls.
   **Two independently verified cloud copies already constitute a valid backup;
   iCloud is copy #3, not the safety net** — so this is added redundancy, not a
   gap.

   **Two candidate unblocks, neither yet taken:**

   - **Reclaim Tier A (15.9 GiB of purely rebuildable caches)** — Trunk 6.2 GiB
     (`repos` 3.2 + `tools` 3.0, including one 3.1 GiB grype
     `vulnerability.db`), **five** Raycast backup sets 7.1 GiB (enumerated, not
     inferred from the total — an earlier draft said six sets of 1,269 MiB,
     which was the total divided by a guessed count; they are 1,423 MiB each,
     one every ~12 h, so this is a **rolling window that refills** and buys the
     write rather than permanent headroom), uv 1.5 GiB, one stray `node_modules`
     889 MiB, `~/Library/Caches` 290 MiB, Homebrew cache 44 MiB. Re-measured at
     01:30 with avail 9,629 MiB, the write is still REFUSED leaving **829 MiB**
     (third measurement of the same refused write: 4,333 → 282 → 829 MiB,
     swinging 4 GiB in both directions — so the gate belongs immediately before
     the write, not at the start of the run). The shortfall is **4,291 MiB** and
     Tier A offers 15.9 GiB, a 3.7× margin that survives the whole observed
     churn range; projected post-reclaim the same write leaves **~17,112 MiB and
     passes the gate** through the plain filesystem path, with no rclone and no
     2FA. **Ordering constraint:** the next `trunk check` re-downloads up to 6.2
     GiB into `~/.cache/trunk`, so Tier A is a loan against the next lint run —
     clear it and do the write before running Trunk again. Ranked menu in
     `disk-survey-2026-11-03.md`.
   - **rclone's `iclouddrive` backend**, which talks to the iCloud web API
     rather than File Provider. It ships in v1.74.2 but is **unconfigured**, and
     configuring it needs interactive Apple ID + 2FA — a human action. **Whether
     it actually streams is UNVERIFIED**: rclone's docs state no maximum object
     size, no chunk size and no streaming guarantee, and the backend exposes no
     chunking option (confirmed by enumerating its config options in v1.74.2 —
     `service`, `apple_id`, `password`, `trust_token`, `cookies`, `client_id`,
     `encoding`, `description` and nothing else). An earlier revision of this
     step asserted it "streams in chunks and never stages the whole object";
     that was an unverified claim presented as fact and is retracted here.
     `ICLOUD-RUNBOOK.md` therefore leads with a 500 MiB canary that samples `df`
     every 2 s during an `rclone rcat` from `/dev/zero` — zero local disk for
     the payload — and prints STREAMS / PARTIAL STAGING / STAGES LOCALLY from
     the peak dip, then verifies the canary by content hash rather than size.
6. **Verify copy #3 with a streaming sha256 against `71c643c2…`.** A matching
   _size_ does not count: §23 Rule 3 requires byte evidence — a hash, a
   checksum, or a listing — before any `MATCHED` verdict.
7. **Only then** remove the local 19 GiB tree — gated on copy #3 hashing clean,
   a re-check of `NONMOD-MARKER` and `tmutil listlocalsnapshots /` **immediately
   before** the delete rather than at the start of the run, and **explicit human
   approval**. The earlier technical gates are already closed: the extraction
   spot-check passed with all four sampled members MATCH (§3), and the snapshot
   list is empty, so deletion really does reclaim the space instead of leaving
   it held by a snapshot. Frees 19 GiB; the Data volume measured **95% used / 11
   GiB free** immediately before this step was written. Not reversible without
   extracting the archive, which becomes trivial once the space is freed.
8. **Archive the tarball, not the tree.** ~34,000 small files through File
   Provider is slow and stall-prone versus one resumable 8.59 GiB object that
   already ships SHA-256 and `.sizes`.

### Blocker: Proton cannot be streamed as currently configured

Verified 2026-11-02, and it invalidates the mitigation this section originally
proposed:

- All 5 Proton parts are **`dataless`** (`ls -lO` reports
  `compressed,dataless`). Reading one **hydrates it to local disk** in full.
- **`brctl` on this host (darwin 27.2) has no eviction subcommand** — only
  `diagnose`, `log`, `dump`, `status`, `accounts`, `quota`, `monitor`. So "hash
  one 2 GiB part at a time, evict between" is **not achievable from the CLI**.
  Eviction would need the Proton app UI, Finder's _Remove Download_, or
  non-deterministic OS space pressure.
- Hashing all 5 parts would therefore hydrate **9.2 GiB permanently** against
  11.2 GiB free and a 4 GiB hard floor — landing at ~2 GiB free, i.e. **ABORT**
  territory, with no CLI way back out.
- **The clean path exists but needs setup:** rclone v1.74.2 **does** ship a
  `protondrive` backend (and an `iclouddrive` one). Neither is configured;
  configured remotes are `gdrive:`, `onedrive:`, `alldebrid:`, `media:`. Adding
  `proton:` is a config write plus interactive Proton auth (credentials + 2FA),
  which is a human action. With it, Proton's parts stream at ~37 MiB/s with zero
  hydration and step 4 becomes trivial.

**Practical upshot:** Proton verification is _nice to have, not required_. The
backup of record is the run-B archive on OneDrive + Google Drive, and it is
verified.

**Timing.** SHA-256 CPU cost is negligible; wall time is bandwidth-bound at a
measured **~37 MiB/s**, so a full 8.59 GiB pass is ~4 minutes, not hours.

**Cloud constraints worth keeping.** Google Drive is mounted **read-only**
(rclone only). `rclone media:` is a **union of `gdrive:Media` +
`onedrive:Media`** and _is_ the Jellyfin library — never use it as scratch.
Neither `iclouddrive:` nor `protondrive:` is configured, though both backends
exist in rclone v1.74.2; adding either is a config write plus interactive auth
(`iclouddrive` additionally needs Advanced Data Protection off and a trusted
device).

**Two distinct root causes, worth keeping separate.**

1. **The backup was ad-hoc and is not reproducible** — two compression runs 18
   hours apart, one split into parts, one uploaded whole, and no record of which
   manifest certifies which artifact. Filed as
   [#2693](https://github.com/abhimehro/personal-config/issues/2693).
2. **The false corruption alarm was an analysis error, not a backup error.** A
   size comparison across two unrelated artifacts, with no byte ever read,
   produced a confident and completely wrong verdict that survived into a
   committed document. The generalisable rule: **a size mismatch is a
   hypothesis, never a finding — hash the bytes before writing the conclusion.**
   Cost of the correction: ~20 minutes of streaming. Cost of acting on the
   original verdict: overwriting two good archives with a different file.

---

# Part II — Findings from the export

## 5. Inventory

**Confirmed.** Six origin classes — the canonical taxonomy; an earlier
five-class reading was wrong.

| `taskOrigin`             | n       | %        | COMPLETED | FAILED   | with commits      |
| ------------------------ | ------- | -------- | --------- | -------- | ----------------- |
| `USER`                   | 3,445   | 44.8     | 34.5%     | 3.4%     | 47.5%             |
| `SCHEDULED`              | 2,774   | 36.1     | 43.4%     | 3.6%     | 50.5%             |
| **`PROACTIVITY`**        | **998** | **13.0** | **69.1%** | **2.8%** | **71.2%**         |
| `API`                    | 311     | 4.0      | 3.9%      | 0.3%     | 3.9% (197 PAUSED) |
| **`PROACTIVITY_PRERUN`** | **160** | **2.1**  | **79.4%** | **0.0%** | **83.8%**         |
| `USER_CLI_ASYNC`         | 3       | 0.04     | —         | —        | —                 |

**Proactivity is the highest-yield class by a wide margin.** Zero
`COMPLETED with 0 gitCommits` anywhere in the local proactive corpus —
completion always produced code.

`errors.json` holds 22 entries (3 RPC + 19 session); **7,691 − 19 = 7,672**
reconciles exactly with the session-directory count. All 19 session 404s were
**transient, not deletions** — recovered 20/20 by retry, including verbatim
Sentinel and Palette persona prompts and 14 API-origin PR-review tasks.

**26 connected repos**, not the 10 assumed at the start.
`PROACTIVITY_STATUS_ENABLED` on exactly **5**
(Hydrograph_Versus_Seatek_Sensors_Project, Seatek_Analysis, ctrld-sync,
email-security-pipeline, personal-config); `DISABLED` on **2** (repoprompt-ce,
series_correction_project_updated); **19 absent**. Per-repo `settings.json`
including `proactivitySettings` **is** preserved in the export.

Local proactive corpus: **1,158 sessions**, 2025-12-13 → 2026-11-01. Derived
artifacts: 375 files, verified 374/374 against `gdrive:jules-analysis/` with
`rclone check --size-only`.

**Not recovered, and not recoverable:** Jules **memories** and **scheduled-task
definitions**. The `$rpc` surface is fully dead — **0/26 probes OK** across 4
real RPC methods, 12 REST paths, and 10 guessed methods — and the `jules` CLI
has no memory or schedule subcommand.

## 6. The Nov 1 burst — the headline

**Confirmed.** 144 genuinely new sessions, **all created in one 15m17s burst,
2026-11-01 14:41:32 → 14:56:49 UTC**. Captured composition: 136 `PROACTIVITY` +
8 `API` (all PAUSED). A list-only census said 137 + 7 with 23 FAILED versus 22
captured — one session's origin and one's status drifted between the two
fetches. **Open**, immaterial (1 of 144).

Statuses: 108 COMPLETED (75%), 22 FAILED (15%), 7 PAUSED, 3
AWAITING_USER_FEEDBACK, 1 IN_PROGRESS, 1 PLANNING, 2 None.

Outcome, authoritative from live GitHub as of 2026-11-02:

|                     | n                                                 |
| ------------------- | ------------------------------------------------- |
| PRs created         | **113**                                           |
| open, never triaged | **110** (0 comments, 0 review comments, 0 drafts) |
| **merged**          | **3 (2.7%)**                                      |
| closed-unmerged     | 0                                                 |

Every COMPLETED session produced exactly one PR (108 → 108). The 3 merges are
all personal-config, all hand-merged 2026-11-01 15:16–15:45 UTC — and two of
them (#2661 "Add unit tests for PR lifecycle schema validation" and #2666 "add
test suite for PR lifecycle schema validation") are **the same work landed
twice**.

> **This is the headline.** The Jules proactive workflow optimised for PR
> _creation_, not PR _landing_: 15 minutes of proactivity produced 113 PRs at a
> 2.7% merge rate, leaving 110 unreviewed PRs across 6 repos.

**Branch-naming correction.** Only **61/113** PRs use `jules-{taskId}-{8hex}`.
The other **52** use descriptive refs (`test/command-block-tests-…`,
`cleanup/remove-unused-alert-redact-param`,
`code-health/remove-unused-import-…`). Both forms are `PROACTIVITY` origin.
**Any tooling that filters on the `jules-` prefix misses 46% of proactive PRs**
— this became gap G-6.

**Scheduled-PR mismatch resolved.** The working hypothesis was that mismatched
PRs came from pre-cutoff sessions. Not needed: **all 113 burst PRs are
`PROACTIVITY`-origin, zero `SCHEDULED`.** Scheduled sessions simply produced no
PRs in this window.

## 7. Failure taxonomy

**Confirmed: `taskFailed` carries no diagnostic value.** All 22 payloads are
byte-identical:

```json
{
  "failureType": "FAILURE_TYPE_UNSPECIFIED",
  "userVisibleFailureMessage": "Jules was unable to complete the task."
}
```

The real cause lives in **`agentMessaged`, which immediately precedes
`taskFailed` in 20 of 22 failures.** Classified by _primary_ cause with a
reproducible rule-ordered classifier (`classify_failures.py` →
`failure-taxonomy.json`), after an earlier hand-count summed to 23. These counts
are authoritative and sum to 22.

| Primary cause                                                                                              | n      | %       | Real work produced?                                                |
| ---------------------------------------------------------------------------------------------------------- | ------ | ------- | ------------------------------------------------------------------ |
| **`AWAIT_SUBMISSION`** — work done or nearly done, ended "may I proceed with submitting?", nobody answered | **11** | **50%** | 8 hold code changes; **0 opened a PR**                             |
| **`CI_GATE`** — reached `taskCompleted` yet recorded FAILED, or blocked by a check unrelated to the change | **5**  | **23%** | 4 opened PRs (all still open, 0 merged); 1 holds an unpushed patch |
| `AMBIGUOUS_SPEC` — agent asked the user to disambiguate _what_ to change                                   | 2      | 9%      | none                                                               |
| `EMPTY_MSG` — no final message at all                                                                      | 2      | 9%      | none                                                               |
| `STALE_TARGET` — target removed upstream                                                                   | 1      | 5%      | none                                                               |
| `OTHER` — strategy consultation, no submission attempt                                                     | 1      | 5%      | none                                                               |

Two observations cut across those buckets:

- **20 of 22 (91%) ended blocked on a human, not on the code.** 16 (73%) were
  asking permission to _ship_ finished work; 4 (18%) were asking the user to
  _clarify the target_. Only the 2 `EMPTY_MSG` sessions produced no signal.
- **13 of 22 (59%) retain real patch content** (`fileDiffsV2` > 0) or opened a
  PR. Only 9 produced nothing at all.

**~91% of failures are process, gate, or evidence failures — not code-quality
failures.** That single number is the design brief for everything in Part III.

Three structural findings:

1. **`planApprovalWaitTime: "0s"` on all 144 sessions.** Plan approval was
   auto-granted, but _submission_ approval was not. The dominant failure mode is
   a human gate nobody was watching.
2. **Plan generation is a hard prerequisite for success.** `planGenerated` and
   `planApprovalRecorded` appear in **100% of COMPLETED** versus **64% of
   FAILED**; 8 of 22 failures never produced a plan.
3. **4 FAILED sessions reached `taskCompleted` yet are recorded FAILED** — a
   status-model inconsistency. All 4 are `CI_GATE`: the work finished, the PR
   opened, and a downstream check flipped the session to failed.

**The cluster versus the label.** The 3 Hydrograph sessions are **one** stale
finding fired three times, and they split across two labels (1 `STALE_TARGET`, 2
`EMPTY_MSG`). The labels describe _how_ each session died; the cluster describes
_why_. Any gate built on the label alone misses this.

**Immediately salvageable — 4 open PRs from FAILED sessions**, all `CI_GATE`:

| PR                                                                              | Repo                              | Why it failed                 |
| ------------------------------------------------------------------------------- | --------------------------------- | ----------------------------- |
| [#1100](https://github.com/abhimehro/Seatek_Analysis/pull/1100)                 | Seatek_Analysis                   | `os.walk` → `os.scandir`      |
| [#1829](https://github.com/abhimehro/email-security-pipeline/pull/1829)         | email-security-pipeline           | CodeScene false positive      |
| [#630](https://github.com/abhimehro/series_correction_project_updated/pull/630) | series_correction_project_updated | 173 tests pass, Snyk 0 issues |
| [#517](https://github.com/abhimehro/repoprompt-ce/pull/517)                     | repoprompt-ce                     | 2 unrelated flaky CI shards   |

The two clearest false positives: deleting `_is_video_capture_open` — a
cyclomatic-complexity-**1** function — **lowered** the file's CodeScene health
score 10.00 → 9.39 and failed the check; and a repoprompt-ce test PR was blocked
by failures in two unrelated shards plus a downstream style check.

### 7.1 The 9 orphaned patches — recovered

**Confirmed.** 9 of the 22 FAILED sessions report `hasCodeChanges: true` with
`n_patch = 0` and `n_pr = 0`. Their work existed **nowhere on GitHub** — only in
a Jules dev box scheduled for wind-down. 8 are `AWAIT_SUBMISSION`, 1 is
`CI_GATE`. By repo: **personal-config 6**, Seatek_Analysis 2,
email-security-pipeline 1.

**Recovered 2026-11-02** via `jules remote pull --session <id>` (never
`--apply`): 9/9 succeeded, **39,977 bytes** of unified diff, 15 files, 32 hunks,
+564/−129. The keychain token had expired at 01:46 local; the CLI refreshed it
silently from the stored refresh token, so no interactive auth was needed.
Applicability against **current HEAD**, verified with `git apply --check`
(read-only; all three target checkouts confirmed 0 changed paths afterwards):
**8 apply clean, 1 needs `--3way`, 0 stale.**

| Session                | Title                                                               | Repo                    | Cause            | Files |
| ---------------------- | ------------------------------------------------------------------- | ----------------------- | ---------------- | ----- |
| `16617252921776111682` | Refactor `main_setup` to reduce complexity                          | Seatek_Analysis         | AWAIT_SUBMISSION | 1     |
| `16798697686478516528` | Refactor duplicated `gh` subprocess logic in `parse_inventory.py`   | personal-config         | AWAIT_SUBMISSION | 4     |
| `1713465770261168156`  | Verify state-transition logic for Ready-for-Review PR               | personal-config         | AWAIT_SUBMISSION | 1     |
| `17962778058532734526` | Consolidate `gh` subprocess execution logic in `parse_inventory.py` | personal-config         | AWAIT_SUBMISSION | 1     |
| `18035879337675326486` | Add unit tests for `_process_single_sheet`                          | Seatek_Analysis         | AWAIT_SUBMISSION | 1     |
| `18201196437495950540` | Verify state-transition logic for Abandoned PRs                     | personal-config         | AWAIT_SUBMISSION | 1     |
| `5008435353120910272`  | Optimize hidden-text regex check in spam analyzer                   | email-security-pipeline | AWAIT_SUBMISSION | 3     |
| `5815873277372019599`  | Add API key validation in morning-brief script                      | personal-config         | **CI_GATE**      | 2     |
| `6975597363944348043`  | Eliminate N+1 API calls in PR comment fetching                      | personal-config         | AWAIT_SUBMISSION | 1     |

> **The single largest recovery of the whole analysis.** Half of all burst
> failures died asking a question nobody answered, and 8 of them were holding
> finished work. It also proves the mechanism the Antigravity design must not
> repeat: **a human gate with no SLA turns completed work into lost work.**

Two of the nine are the _same_ `parse_inventory.py` duplication finding
(`16798697686478516528` and `17962778058532734526`), and two both touch
`tests/test_pr_recap.py` (`1713465770261168156` and `18201196437495950540`).
Promotion therefore required a live dedup decision — a working demonstration of
gaps G-2 and G-5 before either was built. See §21 for the resolution.

## 8. Security skew — confirmed as a skew, refuted as a cause

The hypothesis was ~6/23 security-themed failures, with the conditional that
confirmation would make a security veto a **hard gate**.

**Confirmed as skew.** With a proper keyword set (a first pass used too narrow a
regex and reported only 2 — that was wrong):

|           | security-subject | rate      |
| --------- | ---------------- | --------- |
| FAILED    | 8 / 22           | **36.4%** |
| COMPLETED | 6 / 108          | **5.6%**  |
| all 144   | 15 / 144         | 10.4%     |

Security-themed suggestions are **6.5× over-represented in failures.**

**Refuted as a security-difficulty effect.** The 8 security failures decompose
entirely into the generic causes:

- **2 × `AWAIT_SUBMISSION`** —
  `Sanitize Environment Variables in
  CodexRuntimeAuthority` (API-key leakage
  to child processes) and `Fix Command
  Injection Risk in Diagnostics` (CRLF
  injection). Both produced excellent analysis and **both stopped at exactly 11
  steps** awaiting a decision.
- **1 × `CI_GATE`** — `Add API Key Validation in Morning Brief Script`
  (`5815873277372019599`): the fix was ready, but an **unrelated** pre-existing
  test assertion in `tests/test_refactoring_agent_workflow.py` (a
  refactoring-agent SHA bump) made `make test-all` fail, so the session ended
  asking whether to touch it.
- **3 ×** the **same** Hydrograph "file size validation" suggestion, whose
  target `data_validator.py` was **deleted in commit `bf03cad` (PR #431)** —
  labelled 1 `STALE_TARGET` + 2 `EMPTY_MSG` by _how_ they died. **One stale
  suggestion, fired three times, produced 14% of all burst failures.**
- **1 × `AMBIGUOUS_SPEC`** —
  `Fix Detection of Dangerous Patterns Prefixed with
  Whitespace`: the agent
  could not tell whether the target was `tests/test_sanitization_csv.py` or
  filename handling in `media_file_type.py`.
- **1 × `OTHER`** —
  `Fix Unvalidated Shell Environment Capturing in
  CLIEnvironmentCache`:
  analysis-only, ended consulting on remediation strategy.

> **Conclusion: do not implement a hard security veto.** Security suggestions
> are the highest-value category — real CVE-class findings including
> `DYLD_INSERT_LIBRARIES` injection, credential leakage to child processes, and
> CRLF injection — and they fail for the _same_ process reasons as everything
> else. A veto would discard the best output. The correct gates are **evidence
> freshness** (verify the target file and symbol still exist at current HEAD
> before dispatching) and **base-relative verification** (an unrelated
> pre-existing failure must not discard a good candidate).

## 9. Duplicate clusters and co-failure

**Confirmed.** 25 clusters with ≥2 members in the burst. Duplication rate
**35.0% exact / 75.2% fuzzy** against a **7.0%** eight-month baseline; failure
rate **15%** against **2.4%**.

| Cluster shape                           | n  |
| --------------------------------------- | -- |
| every member FAILED                     | 1  |
| some members FAILED (9 failed siblings) | 6  |
| no member FAILED                        | 18 |

**11 of 22 failures (50%) sit inside a duplicate cluster.**

Three named mechanisms:

- **Hydrograph, 7 sessions, one invalid suggestion.** "Add/Fix File Size
  Validation Before `pd.read_excel()`" across 3 phrasings → 3 FAILED, 3
  COMPLETED, 1 AWAITING. Target file deleted in PR #431. **Seven agents spent on
  a finding that was already obsolete.**
- **personal-config, 8 sessions = 4 topics × 2 exact duplicates.** "Verify State
  Transition Logic" for {Ready for Review, Abandoned, Draft Opening, Draft→In
  Progress}. Two of the four pairs split **1 COMPLETED / 1 FAILED** — the
  signature of two agents editing the same file concurrently, where one wins and
  one collides. **Confirmed at the pair level**; this is the collision mechanism
  that became gap G-5.
- **personal-config, 2 paraphrases, both FAILED.** `16798697686478516528`
  ("Refactor Duplicated `gh` Subprocess Logic") and `17962778058532734526`
  ("Consolidate `gh` Subprocess Execution Logic") — total loss, and both retain
  recoverable patches (6 and 5 file diffs respectively).

**Caveat — the fuzzy rate overcounts.** One Seatek cluster groups 7 sessions
titled "Refactor _X_ to Reduce Complexity" over **seven distinct functions**
(`calculate_summary_stats`, `compute_sensor_metrics`, `main_setup`,
`process_all_data`, `dump_summary_excel`, `get_repo_info`,
`test_flattened_updates_basic`). That is a **template collapse, not
duplication**. CodeScene-style templated titles make fuzzy string clustering
unreliable as gate input on its own — **a novelty gate must compare target
file + symbol, not title text.** This constraint is written into G-2.

### A second, larger finding from the same table

**`PROACTIVITY` was dormant for ~3 months before the burst:** Aug 79, **Sep 0,
Oct 0**, then 137 in 15 minutes on Nov 1. `SCHEDULED` kept running throughout
(Sep 116, Oct 98).

**Inferred.** The burst was a **reactivation from cold**, not steady-state
operation. That explains the staleness failures directly: findings generated
months earlier were executed against a repo that had moved on (PR #431 deleting
`data_validator.py`; `simple_master_pattern` already using `.search()`;
`RepoPromptBuiltInAgentWorkflow` already covered by
`testHeadlessWorkflowSelectionAppliesCanonicalPromptAndRejectsInvalidReferences`).
The 35% duplication and 15% failure are symptoms of **a cold start with a stale
finding backlog**, not of proactivity itself.

## 10. `PROACTIVITY_PRERUN` resolved

The plan carried this as a hypothesis: _speculative sandbox pre-execution_.
**Refuted.**

- **Identical persona set.** PRERUN uses the same four templates as PROACTIVITY
  in near-identical proportions — 🧪 Testing 40 vs 84, ⚡ Performance 38 vs 67,
  🧹 Code Health 38 vs 77, 🔒 Security 24 vs 32.
- **Bounded date range.** PRERUN runs **2026-02-25 → 2026-05-13**, then stops
  permanently.
- **Inverse volume relationship.** Monthly: Feb PRERUN 13 / PROACTIVITY 136 ·
  Mar 62 / 61 · **Apr 52 / 0** · May 33 / 161 · **Jun 0 / 270** · Jul 0 / 286 ·
  Aug 0 / 79.
- **Never fails, rarely publishes.** 159 local PRERUN dirs: 127 COMPLETED, 20
  IN_PROGRESS, 12 None, **0 FAILED**. **84% produce a patch** but only **4%**
  mention a PR (PROACTIVITY: 84% patch, 13% PR).

> **Confirmed: `PROACTIVITY_PRERUN` was the canary / pre-production channel of
> the same proactivity pipeline.** It ran the four personas in a non-publishing
> shadow mode from late Feb to mid-May 2026, then graduated into the full
> `PROACTIVITY` channel in June — after which PRERUN volume goes to zero and
> PROACTIVITY scales 4×. The name is literal: a _pre-run_ of the feature.

**This validates the design's own `2B` → `2A` graduation gate.** Jules did
exactly what the Antigravity design proposes: prove a proactive channel locally
without publishing, then graduate it to draft PRs. That is a rare case of the
evidence endorsing the architecture rather than indicting it.

## 11. The durable artifact — four persona templates

**Confirmed.** All four recovered verbatim, with a shared schema. This is the
most portable thing in the entire export.

```
# <emoji> <Persona> Task
You are a <focus>-focused agent. Your mission is to <goal>.

## Task Details
**File:** `<path>:<line>`
**Issue:** <one-line finding>
**Language:** <lang>
**Current Code:** | **Vulnerable Code:**   <- fenced snippet
**Rationale:** <why this matters>

## Your Process
### 1. UNDERSTAND - ...
### 2. MEASURE | ASSESS | PLAN - ...
### 3. IMPLEMENT - ...
### 4. VERIFY - ...
### 5. DOCUMENT | PRESENT - ...
```

| Persona                       | Bytes | Stages                                                                                      | Code field        |
| ----------------------------- | ----- | ------------------------------------------------------------------------------------------- | ----------------- |
| 🧪 Testing Improvement        | 1,903 | UNDERSTAND → PLAN → IMPLEMENT → VERIFY → DOCUMENT                                           | `Current Code`    |
| ⚡ Performance Optimization   | 2,631 | UNDERSTAND → **MEASURE (baseline)** → IMPLEMENT → **VERIFY (measure impact)** → **PRESENT** | `Current Code`    |
| 🧹 Code Health Improvement    | 2,722 | UNDERSTAND → ASSESS (risk) → PLAN → IMPLEMENT → VERIFY → DOCUMENT                           | `Current Code`    |
| 🔒 Security Vulnerability Fix | 2,261 | UNDERSTAND → ASSESS (blast radius, **CVE lookup**) → IMPLEMENT → VERIFY → DOCUMENT          | `Vulnerable Code` |

**The detector supplies File + line + Issue + Language + code snippet +
rationale; the persona supplies the process.** That separation is the design to
carry forward — the finding schema is the contract, the persona is swappable.
Four structurally byte-identical templates over one input shape is why Jules
could run four different kinds of improvement through one pipeline.

Two persona details worth preserving: the security persona closes with _"A fix
that introduces new vulnerabilities is worse than no fix at all"_; the
performance persona requires a **measured baseline before and after** — the only
persona with a quantitative gate.

---

# Part III — Antigravity design

A gap-closure design, not a greenfield one. The v3 implementation on branch
`feat/antigravity-proactive-migration` already solves the loudest Jules
pathology (unbounded fan-out); most of what follows closes the seven holes the
evidence exposes.

## 12. What v3 already solves — do not rebuild

| Jules pathology                        | v3 control                                                                                                                                     | Verdict                                                                                |
| -------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------- |
| 137 sessions in 15m17s                 | 1 repo/run, 1 improvement/run, weekday 08:15 + triage 08:35                                                                                    | **Solved, well.** ~10 candidates/week vs 137/15min                                     |
| Work lost in a remote dev box          | `2B` local-only: isolated worktree on local disk, `pushurl = DISABLED`, `chmod 600` digest                                                     | **Solved, and better than Jules.** The 9 orphaned patches could not have happened here |
| Credential leakage into verification   | `verify` strips `SSH_AUTH_SOCK` / `GH_TOKEN` / `GITHUB_TOKEN`                                                                                  | **Solved**                                                                             |
| Verification-gate tampering            | `exit 2` on edits to build/lock/script/test-harness paths; a `--lens` override can never relax a gate                                          | **Solved**                                                                             |
| Public disclosure of security findings | `sentinel` permanently off public Draft PRs; hook blocks unmerged `.jules/sentinel.md` writes without a verified post-merge lease              | **Solved**                                                                             |
| Unbounded PR pile-up                   | `check-throttle`: ≥2 unreviewed candidates or any >7 days → exit 5                                                                             | **Present but incomplete** → G-3, G-6                                                  |
| Canary / pre-production channel        | `2B` → `2A` graduation gate                                                                                                                    | **Solved — and historically validated** by `PROACTIVITY_PRERUN` (§10)                  |
| Numeric drift on research repos        | `bolt` requires `--numeric-check-cmd` at `rtol=1e-10, atol=1e-12`; `FLOAT_REORDER_DRIFT` substatus separates float noise from real regressions | **Solved — an improvement over Jules**, which had no such gate                         |

## 13. Evidence → gate map

| Failure class                       | n / 22                        | share            | v3 coverage                                                         | Verdict                                          |
| ----------------------------------- | ----------------------------- | ---------------- | ------------------------------------------------------------------- | ------------------------------------------------ |
| `AWAIT_SUBMISSION`                  | 11                            | 50%              | `2B` removes the submission question entirely                       | **Relocated, not fixed** → G-3                   |
| `CI_GATE`                           | 5                             | 23%              | `verify` fails closed; Step 4.4 discarded the candidate             | **Reproduced exactly** → G-4                     |
| `AMBIGUOUS_SPEC`                    | 2                             | 9%               | nothing checks the finding is unambiguous                           | **Open** → G-1                                   |
| `EMPTY_MSG`                         | 2                             | 9%               | local runs can't vanish silently; triage reports `MISSED`           | **Solved**                                       |
| `STALE_TARGET`                      | 1 (+2 above)                  | 14% as a cluster | Step 2 reads `git log --since="7 days ago"`; Step 3 checks open PRs | **Open** → G-1                                   |
| `OTHER`                             | 1                             | 5%               | n/a                                                                 | absorbed by G-3's "no open-ended questions" rule |
| Duplicate clusters                  | 11/22 failures sat inside one | 50%              | journals are prose; throttle is repo-level                          | **Open** → G-2, G-5                              |
| 110/113 PRs unreviewed, 2.7% merged | —                             | —                | graduation gate measures _production_                               | **Open** → G-7                                   |

**91% of burst failures ended blocked on a human, not on the code.** The design
brief follows directly: make the human decision **bounded, defaulted, and
cheap** — not merely move it from a chat window to a digest file.

## 14. The seven gaps

### G-1 — Evidence-freshness gate

**Evidence.** One stale Hydrograph finding fired **3 times** against
`data_validator.py`, deleted in commit `bf03cad` (PR #431) — 3 of 22 failures
(14%) from a single bad finding. Two more sessions died asking which of two
files was meant. **5/22 = 23%.**

**Why v3 misses it.** `check-collisions` asks "does an _open PR_ touch this
path?" A deleted file has no open PR, so the gate passes. `git log --since`
shows recent activity but never asserts the target exists.

**Design.** New `scripts/proactive-finding-gate.sh freshness`, run as sweep
**Step 2.5** — after lens selection, before `prepare`, so no worktree is ever
created for a dead finding.

**Precondition 0 — `git fetch`, hard.** Assertions 1, 2 and 4 all read
`origin/HEAD`, so each is exactly as correct as the local remote ref is. Reuse
`require_fresh_origin_ref` (shipped in R1) and fail closed rather than judging
against a stale ref. **This is not theoretical:** one recovered patch was given
a **DRIFTED** verdict purely because `origin/main` had not been fetched, and the
drift did not exist. No ref-based verdict — `DRIFTED`, `MATCHED`, `STALE_NO_OP`,
`THROTTLED` — may be rendered without it. If the fetch fails the gate exits 6
and reports that it could not establish freshness; **"could not tell" must never
be recorded as "still valid".**

Then four cheap assertions:

1. path exists at `origin/<default>` HEAD;
2. `symbol` resolves in that path
   (`git grep -n <symbol> origin/HEAD -- <path>`);
3. the finding's quoted snippet still matches the file (whitespace-normalised) —
   catches "file exists, code moved";
4. `observed_sha`'s blob for the path equals HEAD's blob
   (`git rev-parse <sha>:<path>` vs `origin/HEAD:<path>`); if they differ the
   finding is _stale-by-drift_ and must be re-derived, not applied.

Fail → `Status: STALE_NO_OP` digest **plus a row in the suppression ledger**
(G-2) so the finding can never re-fire. Exit code **6**, extending the existing
4 = collision and 5 = throttle.

### G-2 — Novelty keyed on (repo, path, symbol), never on title text

**Evidence.** 11/22 failures (50%) sat inside duplicate clusters. Burst
duplication 35.0% exact / 75.2% fuzzy against a 7.0% baseline. **But fuzzy title
matching over-merges** — see the template-collapse caveat in §9.

**Why v3 misses it.** Dedup memory is prose in `.jules/<lens>.md`, read at Step
2 and unverifiable. Worse, `sentinel` is _forbidden_ from writing pre-merge
findings to its journal (correctly — it is public), so **sentinel has no dedup
memory at all** and can re-fire the same finding indefinitely. Journals are also
inconsistent on disk: `personal-config` has no `.jules/code_health.md` or
`testing.md`; `Seatek_Analysis` has neither.

**Design.** An append-only **target ledger** at
`~/.gemini/antigravity/proactive-reports/target-ledger.ndjson` (`chmod 600`,
local — so it does not violate the sentinel journal block). One row per
examination:

```json
{
  "ts": "…",
  "repo": "abhimehro/x",
  "path": "a/b.py",
  "symbol": "f",
  "lens": "bolt",
  "blob": "<git rev-parse origin/HEAD:a/b.py>",
  "base_sha": "…",
  "verdict": "CLEAN_NO_OP",
  "digest": "2026-11-02-x.md",
  "confidence": 2,
  "signals": ["reproduced", "linter"]
}
```

The novelty test is a **content hash, not a string match**: suppress when the
same `(repo, path, symbol)` has a verdict within N days _and_ `blob` is
unchanged. If the file hasn't changed, the finding cannot have. Verdicts:
`CANDIDATE_READY |
CLEAN_NO_OP | STALE_NO_OP | THROTTLED | GATE_FAILURE | PRE_EXISTING_FAILURE |
PROMOTED | MERGED | REJECTED | EXPIRED`.

### G-3 — Review SLA, decay, and "never ask an open-ended question"

**Evidence.** 11/22 (50%) `AWAIT_SUBMISSION`; 16/22 (73%) ended asking
permission to ship finished work; **0 of the 11 opened a PR**; 8 held patches
that existed nowhere on GitHub. On the PR side: 110/113 open with **0 comments,
0 review comments**, 3 merged (2.7%), and #2661 + #2666 are the _same work
landed twice_.

**Why v3 only half-solves it.** `2B` correctly removes the "may I submit?"
question — but it relocates the risk to a digest directory. Nothing reads prior
digests: every `proactive-reports` reference in the repo is a _write_, except
the triage sidecar, which reads **only today's** file. Backpressure is a hard
stop with **no expiry and no escalation**: after day 7 a repo is throttled
indefinitely and every subsequent sweep writes a THROTTLED digest forever.

**Design — four parts.**

1. **Decision SLA.** Every `CANDIDATE_READY` must reach a terminal verdict
   (`PROMOTED | REJECTED | EXPIRED`) within **5 business days**, with a
   `decision_rate` target of **≥80%** inside that window (G-7 measures it). The
   08:35 triage sidecar stops reporting only today's digest and also reports
   **queue aging**: oldest undecided candidate, count over SLA, count THROTTLED.
2. **Auto-expiry with preservation.** At the existing 7-day TTL an undecided
   candidate becomes `EXPIRED`. The worktree is **kept** (v3 already preserves
   dirty and unmerged-commit worktrees) but stops counting against the throttle,
   and the ledger records `EXPIRED` so the same target is not immediately
   re-proposed. **Unlike Jules, expiry is not loss:** the patch is on local disk
   and in the ledger. Reinstating an expired candidate must stay a single
   command — expiry is a queue discipline, not a judgement.
3. **No open-ended questions.** Sweep digests must never end "may I proceed?"
   They end with a decision request **that has a default**:
   `Action: promote | reject | expire (default: expire on <date>)`. This is the
   direct antidote to the 73%. Triage already models the right shape
   (`'worth a look' or 'skip'`); extend that discipline to the sweep.
4. **The throttle decays instead of stopping hard.** Replace the binary "≥2
   unreviewed or any >7 days → `THROTTLED`" with a cap that **loosens as the
   backlog clears**. A hard stop with no release valve is precisely how the
   110-open-PR graveyard formed: once a repo crosses the threshold nothing ever
   brings it back under, so every subsequent sweep writes a `THROTTLED` digest
   forever and the automation is dead while still reporting that it ran. Two
   invariants: the cap is **monotonic** in backlog size (strictly more undecided
   candidates never yields a _looser_ cap), and expiry (part 2) is the mechanism
   that reduces backlog — so the pair is **self-clearing** rather than needing a
   manual reset. Report `throttle_days` as a KPI; a rising value means review
   capacity, not sweep quality, is the binding constraint.

### G-4 — Base-relative verification (the `CI_GATE` fix) — **SHIPPED in R1**

**Evidence.** 5/22 (23%). Three concrete false positives, all named in §7. 4 of
the 5 reached `taskCompleted` and opened PRs that are still open — real work
stranded by somebody else's breakage.

**Why v3 reproduced it.** Confirmed in source: `base_sha` was recorded in
`proactive-meta.json` and used for diffs and throttle age, but **never used to
re-run a failing check on base**. Step 4.4 said "if verification fails and
cannot be fixed cleanly within budget, **discard** changes" — precisely how
Jules threw away 4 good PRs.

**Design, as shipped.**
`antigravity-proactive-ctl.sh base-check --repo <name>
--worktree <dir> [--digest <path>]`
answers the question a bare verify exit code cannot: _was this failure caused by
the candidate, or was base already broken?_ It splits the repo's compound test
command on `&&`, re-runs the failing stage once in the candidate to catch a
flake, then re-runs the stages on a pristine `base_sha` worktree, and prints a
`VERDICT`:

| Verdict                | Exit | Meaning                                                                        |
| ---------------------- | ---- | ------------------------------------------------------------------------------ |
| `NO_FAILURE`           | 0    | nothing failed                                                                 |
| `FLAKE_ON_RETRY`       | 0    | candidate passed on retry — the 2 unrelated shards case                        |
| `PRE_EXISTING_ON_BASE` | 0    | base fails too; **candidate still promotable**, base breakage filed separately |
| `CAUSED_BY_CHANGE`     | 2    | real regression; discard the candidate                                         |
| —                      | 6    | base worktree unusable (object gc'd)                                           |
| —                      | 1    | usage / identity error                                                         |

Credentials are stripped exactly as `verify` strips them. **No `origin` ref is
consulted** — the comparison is against a local `base_sha`, so the
classification stays valid offline and needs no fetch precondition. `--digest`
appends a `## Base-Check Classification` section to the `chmod 600` report
rather than rewriting it. It runs in the **08:35 triage slot, never inside the
sweep**, because a base re-run can double test time and the sweep is boxed at 15
minutes.

**A permission subtlety that would have caused a false promotable verdict.** The
triage sidecar needed a **write** grant on the worktrees directory, not just
read, because re-running a suite writes `__pycache__` and `.pytest_cache` in
place. A permission denial would fail identically in candidate and base and be
misclassified as `PRE_EXISTING_ON_BASE` — **the unsafe direction**. At the same
time its `workspace_uris` must stay **reports-only**: the `PreToolUse` guard
classifies a session as a sweep from its workspace paths (not from
`access_grants`), so adding the worktrees root would upgrade a read-mostly
review slot into a sweep session able to push and open PRs.

### G-5 — File-level collision against local candidate worktrees — **SHIPPED in R1**

**Evidence.** Two personal-config sessions targeted the _same file_ in the same
burst (`16798697686478516528` and `17962778058532734526`, both
`parse_inventory.py`) and split 1 COMPLETED / 1 FAILED. Two more recovered
patches both touch `tests/test_pr_recap.py`.

**Why v3 missed it.** `check-collisions` queried **only**
`gh pr list --state
open`. In `2B` there are no bot PRs, so the gate was a
**no-op for exactly the collision class that caused these failures**.
`check-throttle` counted worktrees per repo but never compared their paths.

**Design, as shipped.** `check-collisions --include-worktrees --repo-path <p>`
unions the changed paths of open PRs with those of every **live** candidate
worktree for the repo. Exit 4 on overlap. `--include-worktrees` is **required,
not optional** — without it the gate cannot see the local-only candidates that
`2B` exists to produce.

The liveness filter matters: a candidate whose work already merged still shows
those paths in `git diff base_sha`, so without a filter it would block that file
for the whole 21-day TTL. **Live = dirty OR has unreviewed worktree commits.**
Dirtiness is checked first because uncommitted edits are live but the ancestry
helper ignores them.

Fail-closed: exit **5** on a truncated PR listing (`>= 100` results, or fewer
files returned than `changedFiles` claims), exit **6** if worktrees cannot be
enumerated or a candidate has no recorded `base_sha`. Its pre-existing
fail-closed behaviour on truncated listings was already correct and was kept.

Also shipped: `proactive-worktree.sh print-test-cmd --repo-name <n>`, the single
source of truth that `base-check` reads so the repo → test-command mapping
cannot drift from the one `verify` uses.

### G-6 — Throttle identity must not depend on a naming convention

**Evidence.** Only **61/113** Jules PRs used the `jules-{taskId}-{8hex}` ref;
**52/113** used descriptive refs. Filtering on a naming convention misses
**46%**.

**Why v3 has the same bug.** `check-throttle`'s remote side filters by **title
prefix** (`⚡bolt`, `🎨palette`, `chore(qa)`, `chore(proactive)`,
`repo-health/`). A human-edited commit subject, a rebase, or a lens using a
different prefix escapes the count — the throttle silently under-counts and the
pile-up it exists to prevent becomes possible.

**Design.** Label-based identity: apply a `proactive` label at promotion and
count `gh pr list --label proactive --state open`. Keep the title prefixes as an
**OR**-condition so pre-label PRs still count. Fail closed (exit 5, matching
`check-collisions`) if the label does not exist on the repo.

### G-7 — Landing rate in the graduation gate, plus a KPI set

**Evidence.** 113 PRs → 110 open, **3 merged (2.7%)**, 0 closed-unmerged. Two of
the three merges are the same work landed twice.

**Why v3's gate repeated the mistake.** "≥5 mergeable candidates out of ≥8
executed runs, <2 `GATE_FAILURE`" measures **production**. A system nobody ever
reviews passes it.

**Design — two added criteria for `2B` → `2A`:**

- **≥1 candidate actually merged** from the 2B queue — proves the promote path
  works end to end, including the Trunk queue for personal-config (routine
  personal-config merges use `/trunk merge`, not a raw GitHub squash).
- **Decision rate ≥80%** — the anti-110-open-PRs metric.
- Keep `<2 GATE_FAILURE` but **exclude `PRE_EXISTING_FAILURE`** (G-4), otherwise
  unrelated repo health blocks graduation.

**Weekly KPIs, all derivable from the target ledger — no new tooling:**

| KPI                         | Definition                             | Target      | Jules baseline                                 |
| --------------------------- | -------------------------------------- | ----------- | ---------------------------------------------- |
| `landing_rate`              | MERGED / PROMOTED                      | ≥50%        | **2.7%**                                       |
| `decision_rate`             | terminal verdicts / CANDIDATE_READY    | ≥80%        | ~0% (110/113 never reviewed)                   |
| `stale_rate`                | STALE_NO_OP / findings considered      | ≤5%         | 14% in burst (one finding, 3×)                 |
| `dup_rate`                  | candidates suppressed by the ledger    | ≤7%         | 7.0% steady / 35.0% burst                      |
| `pre_existing_failure_rate` | PRE_EXISTING_FAILURE / verify failures | report only | new — separates repo health from sweep quality |
| `throttle_days`             | days a repo spent THROTTLED            | ≤2/wk       | review-backlog pressure                        |

**Duplicate-landing guard** (for #2661/#2666): before promoting, check
`gh pr list --state merged` for a merge touching the same `(path, symbol)`
within 14 days and warn. Same ledger key as G-2, reused.

## 15. Candidate scoring — min-gating, not weighted addition

A weighted score must never be able to compensate for a failed gate. Gates run
cheapest-first so a burst cannot burn quota on doomed candidates:

| # | Gate                                                     | Type                                               | Fails to                                |
| - | -------------------------------------------------------- | -------------------------------------------------- | --------------------------------------- |
| 1 | freshness (G-1)                                          | hard                                               | `STALE_NO_OP` + suppression ledger      |
| 2 | novelty (G-2, blob hash)                                 | hard                                               | suppress, ledger row                    |
| 3 | collision (existing + G-5)                               | hard, exit 4                                       | pick another target or `CLEAN_NO_OP`    |
| 4 | throttle (existing + G-6)                                | hard, exit 5                                       | `THROTTLED`                             |
| 5 | scope: ≤1 improvement, ≤4 files, no tamper-evident paths | hard                                               | `CLEAN_NO_OP`                           |
| 6 | verify, base-relative (G-4)                              | hard **only** for regressions caused by the change | `GATE_FAILURE` / `PRE_EXISTING_FAILURE` |
| 7 | confidence                                               | **min-gated score**                                | `LOW` → digest note, not a candidate    |

**Confidence = count of independent signals, minimum 2.** Signals: `reproduced`
(a command demonstrates it) · `linter` (named by CodeScene/ruff/shellcheck/Snyk)
· `test-gap` (a failing or absent test covers it) · `measured` (bolt's
before/after numbers) · `advisory` (a cited CVE or upstream advisory). One
signal → `LOW` → recorded in the ledger as examined, not proposed.

**The rule is uniform across all four lenses — deliberately.** One threshold
everywhere is easier to reason about and easier to audit than a per-lens matrix,
and a per-lens matrix is how a looser lens becomes the path of least resistance.

**One exception, and it is narrow.** `sentinel` may _surface_ a finding on a
single signal, but only as an **advisory draft with no auto-action**: it appears
in the local digest, the ledger row records `confidence: 1`, and that is the end
of its reach. **Anything that changes state still requires 2** — preparing a
worktree, writing a patch, promoting a candidate, or updating
`.jules/sentinel.md`. The rationale is asymmetric cost: an unread security
advisory is a missed finding, while a suppressed one is invisible even to the
person who would have caught it. `sentinel` already cannot use the public
journal for pre-merge dedup, so a hard 2-signal floor would silently drop its
single-signal findings with no record at all. The advisory path keeps the record
without granting the action.

Survivors are then **ranked** (not filtered) by
`severity × confidence ÷ review_cost`, where
`review_cost = files + changed_lines + (touches_tests ? 1 : 0)`, and the top
**1** is executed (one-improvement-per-run). The ≤4-file scope cap is
evidence-set: the 9 recovered patches touch 1–4 files, median 1.

**No security veto** — per §8. `sentinel`'s permanent off-public-PR boundary is
a **disclosure** control and stays; it is not a quality veto and must not become
one.

### The semantic verify gate — permanent, not a nice-to-have

Shipped in R1. A passing test suite does not prove the _intended_ change
happened; one recovered patch silently deleted a test function
(`test_fetch_http_error`) and the suite still passed — baseline 96 tests, raw
patch 105, repaired 106. Three checks, all required:

1. **AST diff of test classes and methods against base** matches the intended
   diff — nothing extra, nothing missing.
2. **Test count before and after** matches expectations. **A drop fails the gate
   even if the suite passes.**
3. **Undefined-name check** (pyflakes or equivalent) on touched files.

Implementation note: `python3 -m py_compile` writes `__pycache__`, which is
unusable inside a worktree under verification — use `ast.parse`.

## 16. Personas, lenses, and the finding schema

| Recovered Jules persona       | v3 lens                                               | Verdict                                                                           |
| ----------------------------- | ----------------------------------------------------- | --------------------------------------------------------------------------------- |
| ⚡ Performance Optimization   | `bolt`                                                | direct match; bolt **adds** mandatory numeric-equivalence gates on research repos |
| 🧹 Code Health Improvement    | `code-health`                                         | direct match                                                                      |
| 🧪 Testing Improvement        | folded into `code-health` (reads `.jules/testing.md`) | **covered, but has no rotation slot** — see below                                 |
| 🔒 Security Vulnerability Fix | `sentinel`                                            | direct match; v3 is stricter                                                      |
| —                             | `palette`                                             | **new, not from Jules.** Keep as an addition                                      |

Testing was a first-class Jules persona and the recovered work agrees: **6 of
the 9 recovered patches touch a test file, 3 are test-only**
(`1713465770261168156` and `18201196437495950540` on `tests/test_pr_recap.py`,
`18035879337675326486` on
`Series_27/Analysis/test_outlier_analysis_series27.py`). Recommendation: keep 4
lenses, give `code-health` an explicit `--focus tests|dead-code|maintainability`
so testing gets a real rotation slot on repos that have a `docs/TESTING.md`.
**Still open** — see §24.

Note that **none of the 9 recovered patches are `palette` work.** That is not
evidence against the lens (it is new, so it has no Jules history) but it does
mean the lens is unvalidated by this evidence base and should be watched during
the pilot.

**Fixed finding schema** — carry the Jules contract verbatim; it is what made
the four personas swappable over one input shape:

```
File:      <path>:<line>
Issue:     <one line>
Language:  <lang>
Current Code: | Vulnerable Code:   <fenced snippet>
Rationale: <why this matters>
```

Add the three fields the evidence demands: **`observed_sha`** (G-1 freshness),
**`symbol`** (G-2 novelty key), **`signals`** (confidence min-gate). The four
recovered templates (1.9–2.7 KB each, byte-identical in structure) drop straight
into `configs/antigravity/skills/proactive-*/references/` as executor prompts.

## 17. Schedule — CRON_TZ resolved

**Contradiction found.** The migration doc said the `3B` sidecars are "pinned to
`CRON_TZ=UTC`", but **both** sidecar JSONs use `CRON_TZ=America/Chicago` (08:15
sweep, 08:35 triage), and `canary-stage` is documented as a "disposable **UTC**
cron".

**Resolution: Chicago is correct for the pilot** — a human reviews the digest at
~08:35 local; UTC would land it at 02:15/03:15 local in winter. The doc's `3B`
row should say `CRON_TZ` is per-sidecar and the pilot uses `America/Chicago`
(**corrected in `b3a1d422`**), and `canary-stage` should gain a `--tz` flag
defaulting to the pilot TZ so the canary tests what will actually run — **filed
as [#2700](https://github.com/abhimehro/personal-config/issues/2700)**, which
also records the trap that relabelling `CRON_TZ` without converting the fire
datetime via `zoneinfo` yields a canary that silently never fires.

**Two latent traps, both low priority:**

- Digest filenames use `$(date -u +%Y-%m-%d)` (**UTC**) while the schedule is
  Chicago. Safe at 08:15 local (= 13:15/14:15 UTC, same date), but any run moved
  after ~18:00 local would name tomorrow's file.
- **Open:** whether `$(date -u +%Y-%m-%d)` inside a sidecar `args` array is
  shell-expanded by the schedule sidecar or passed literally into the prompt.
  Both work, but the second is fragile. One canary run settles it.

Sidecar expansion stays staged: `ctrld-sync` pilot (week 1) → `1B` 5 repos →
`1A` 7 repos, one repo per run throughout.

## 18. Rollout sequence

Effort is wall-clock hours for one agent-assisted implementer, inclusive of
tests, lint and docs — calibrated against R1, which actually shipped at ~750
changed lines / 7 files / 24 new assertions.

| Step   | Status                                                                      | Content                                                                                                                                       | Failure share addressed  | Effort (h)  | Risk                                                   |
| ------ | --------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------ | ----------- | ------------------------------------------------------ |
| **R0** | **done**                                                                    | Review packet for the 9 recovered patches                                                                                                     | —                        | —           | none (read-only)                                       |
| **R1** | **done** — `ea292c9a` on top of `724505e6`                                  | G-4 `base-check` + G-5 `--include-worktrees` + `print-test-cmd`; the permanent semantic gate and the `git fetch` precondition shipped with it | 23% + the collision pair | ~8 (actual) | **low** — pure additions                               |
| **R2** | planned — [#2695](https://github.com/abhimehro/personal-config/issues/2695) | G-1 freshness gate + G-2 target ledger                                                                                                        | 23% + 50%                | **9**       | medium — new local state                               |
| **R3** | planned — [#2696](https://github.com/abhimehro/personal-config/issues/2696) | G-3 SLA/expiry/no-open-questions + G-7 ledger KPI reporting                                                                                   | 50%                      | **11**      | medium — changes triage output _and_ throttle counting |
| **R4** | planned — [#2697](https://github.com/abhimehro/personal-config/issues/2697) | G-6 label identity                                                                                                                            | pile-up prevention       | **4**       | low, and only needed at `2A`                           |
| **R5** | **blocked on R2**                                                           | Pilot week 1 (`ctrld-sync`), then `1B` → `1A`                                                                                                 | —                        | —           | —                                                      |

**Total remaining: 24 h** (R2 9 + R3 11 + R4 4), of which **20 h is on the R2 →
R3 critical path.**

### 18.1 Dependencies between phases

Violating these produces either a blocked agent or a silent merge conflict, not
a visible error.

1. **R3 hard-depends on R2's ledger schema.** Every R3 deliverable reads
   `target-ledger.ndjson`: `kpis` computes all six ratios from it, `expire`
   appends `EXPIRED` rows, and the duplicate-landing guard reuses its
   `(repo, path, symbol)` key. **Freeze the row schema in R2 before R3 starts.**
   R3 cannot be estimated accurately until that schema exists.
2. **R3 and R4 both edit `check-throttle`.** R3 changes _what counts_ (an
   `EXPIRED` candidate stops counting); R4 changes _how identity is determined_
   (label OR title-prefix). Sequence **R3 → R4, never in parallel**, or the
   second rebases over the first.
3. **All three edit `configs/antigravity/skills/proactive-repo-sweep/SKILL.md`**
   (R2 adds Step 2.5, R3 rewrites Step 5's Action line, R4 edits the promotion
   commands). **The single highest-conflict file in the plan.** If two agents
   run concurrently, assign SKILL.md to only one and have the other emit its
   SKILL.md delta as a patch in the issue instead.
4. **R2 ∥ R4 is safe** — R2 creates a new script, R4 touches
   `proactive-worktree.sh`; the only overlap is SKILL.md (see 3). **R2 ∥ R3 is
   not safe** (see 1).
5. **R1 already satisfied two prerequisites**, so neither is re-work: the
   `require_fresh_origin_ref` fetch precondition that G-1's assertions 1/2/4
   must reuse, and the `PRE_EXISTING_FAILURE` substatus that R3's revised
   graduation gate must exclude from the `<2 GATE_FAILURE` budget.
6. **R5 (pilot week 1) should not start before R2.** A pilot running without the
   freshness and novelty gates reproduces the 35% burst-duplication rate that is
   the whole argument for G-2 — it would generate the noise that makes the pilot
   look worthless. **R1 alone makes the pilot _safe_; R2 is what makes it
   _quiet_.**

Graduation to `2A` uses the **revised** gate: ≥5 mergeable of ≥8 executed runs,
<2 `GATE_FAILURE` (excluding `PRE_EXISTING_FAILURE`), **≥1 actually merged**,
**decision rate ≥80%**.

**Boundary S1 is unchanged:** Stage 2 salvage never auto-merges, and nothing in
this design gives a sweep agent merge authority. `sentinel` never reaches a
public Draft PR at any stage.

## 19. Decisions taken

Recorded so a later reader does not re-litigate them.

| #  | Decision                           | Resolution                                                                                                        | Rationale                                                                                                             |
| -- | ---------------------------------- | ----------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------- |
| 1  | The 9 recovered patches            | **Promote all 7** distinct changes as small scoped draft PRs                                                      | 8/9 applied clean to HEAD; they are finished work recovered from a dying dev box                                      |
| 2  | `parse_inventory.py` duplicate     | **`16798697686478516528` is canonical**; drop `17962778058532734526`                                              | The 4-file version subsumes the 1-file version                                                                        |
| 3  | The two `test_pr_recap.py` patches | **Land together in one PR**                                                                                       | Verified co-appliable; splitting them recreates the collision                                                         |
| 4  | Promotion order                    | **6 clean first, morning-brief last** after the sentinel swap                                                     | The morning-brief patch needed sanitisation first                                                                     |
| 5  | PR size                            | **Small and scoped to one change**, reviewed same-day                                                             | Explicitly to avoid rebuilding the 110-PR graveyard                                                                   |
| 6  | Gaps                               | **Build R1 now, plan R2–R4**, file GitHub issues for independent agent assignment                                 | R1 is pure addition, covers 23% of failures, and fixes the collision pair                                             |
| 7  | Decision SLA                       | **5 business days**, 7-day auto-expiry with one-click reopen, `decision_rate` ≥80%                                | Matches actual review cadence                                                                                         |
| 8  | Throttle                           | **Decaying, not a hard stop**                                                                                     | "A hard stop with no release valve is how we got here"                                                                |
| 9  | Confidence min-gate                | **Uniform ≥2 independent signals** across all lenses                                                              | "One rule everywhere is easier to reason about and audit"                                                             |
| 10 | Sentinel exception                 | **May surface on 1 signal, advisory draft only, no auto-action**                                                  | Asymmetric cost of a suppressed security finding; keeps the record without granting the action                        |
| 11 | Security veto                      | **Rejected**                                                                                                      | §8 — security findings are the highest-value category and fail for generic process reasons                            |
| 12 | Semantic verify gate               | **Permanent required step**, three checks                                                                         | A passing suite does not prove the intended change happened                                                           |
| 13 | `git fetch` precondition           | **Hard, before any `DRIFTED` or `MATCHED` verdict**                                                               | A stale ref produced a false DRIFTED verdict on a real patch                                                          |
| 14 | Archival                           | **Move the export to iCloud for final archival**, not delete                                                      | Standing preference; also the only way to free 19 GiB without losing the data                                         |
| 15 | Morning-brief secrets              | **Swap all 5 literals for obvious sentinels before promotion**; re-run gitleaks and attach clean output to the PR | See §23                                                                                                               |
| 16 | Prevention                         | **gitleaks as a pre-commit hook**, no allowlist                                                                   | Shipped as [#2686](https://github.com/abhimehro/personal-config/pull/2686); an allowlist was considered and disproven |

---

# Part IV — Operations record

## 20. What was built

On branch `feat/antigravity-proactive-migration`:

| Commit     | Content                                                                                                            |
| ---------- | ------------------------------------------------------------------------------------------------------------------ |
| `724505e6` | Permanent semantic verify gate (AST diff + test-count + undefined-name) and the `git fetch` precondition — 9 files |
| `ea292c9a` | **R1**: G-4 `base-check`, G-5 `check-collisions --include-worktrees`, `print-test-cmd` — 7 files, +750/−35         |

Test status at R1: **75/75** `tests/test_antigravity_proactive_ctl.sh`,
**83/83** `tests/test_proactive_worktree.sh`, `trunk check --no-fix` clean,
`make lint-errors` clean.

Two coverage gaps were found by reading rather than by a failing test, and both
were closed:

- Every `base-check` test passed `--test-cmd` explicitly, so the **production**
  path — the triage sidecar never passes it — was untested. Fixed with direct
  `print-test-cmd` coverage plus an end-to-end default-resolution case through a
  pass-through `python3` mock.
- The triage sidecar's worktrees **write** grant (§14, G-4). Missing it would
  have produced a false `PRE_EXISTING_ON_BASE` and promoted a broken candidate.

Two bash traps worth recording, both of which produced misleading failures
rather than obvious ones:

- **`local` variables are unbound after a function returns**, so an `EXIT` trap
  referencing them fails under `set -u` — and the failing trap **masks the
  script's real exit status and skips cleanup**. Trap state must be script-level
  globals. This was the root cause of 5 simultaneous test failures.
- **`VAR=x func_call` assignments persist after the function returns** (unlike
  simple commands). Use `env VAR=x cmd` to scope a PATH override in a test.

Platform notes: macOS ships **bash 3.2.57**, which needs `${arr[@]+"${arr[@]}"}`
under `set -u` and cannot handle the nested-quote trim idiom
`${s#"${s%%[![:space:]]*}"}`. `git init --bare` leaves HEAD on a nonexistent
branch, so `remote set-head origin -a` fails — fix with
`git --git-dir=<bare> symbolic-ref HEAD refs/heads/<branch>`.

## 21. Promoted PRs

All opened as **drafts**, one scoped change each.

| PR                                                                      | Repo                    | Branch                                    | Source session                                 |
| ----------------------------------------------------------------------- | ----------------------- | ----------------------------------------- | ---------------------------------------------- |
| [#2687](https://github.com/abhimehro/personal-config/pull/2687)         | personal-config         | `chore/dedupe-run-gh-helper`              | `16798697686478516528`                         |
| [#2688](https://github.com/abhimehro/personal-config/pull/2688)         | personal-config         | `test/pr-recap-state-transition-coverage` | `1713465770261168156` + `18201196437495950540` |
| [#2689](https://github.com/abhimehro/personal-config/pull/2689)         | personal-config         | `perf/parallel-comment-prefetch`          | `6975597363944348043`                          |
| [#2690](https://github.com/abhimehro/personal-config/pull/2690)         | personal-config         | `feat/validate-morning-brief-api-keys`    | `5815873277372019599` (sanitised)              |
| [#1844](https://github.com/abhimehro/email-security-pipeline/pull/1844) | email-security-pipeline | `perf/decouple-hidden-text-patterns`      | `5008435353120910272`                          |
| [#1120](https://github.com/abhimehro/Seatek_Analysis/pull/1120)         | Seatek_Analysis         | `test/cover-process-single-sheet`         | `18035879337675326486`                         |
| [#1121](https://github.com/abhimehro/Seatek_Analysis/pull/1121)         | Seatek_Analysis         | `refactor/extract-setup-summary`          | `16617252921776111682`                         |

Plus [#2686](https://github.com/abhimehro/personal-config/pull/2686)
(`chore/gitleaks-pre-commit-gate`), which is not a recovered patch — it came
from decision 16.

**Not promoted:** `17962778058532734526`, superseded by the canonical
`parse_inventory.py` pick (decision 2).

The AST-diff catch on the morning-brief patch is worth keeping as a worked
example of the semantic gate earning its place: applying the raw patch took the
test count from a baseline of 96 to 105, but it had **silently deleted**
`test_fetch_http_error`. Repairing the omission brought it to 106. A green suite
hid a lost test.

## 22. Filed issues

| Issue                                                                     | Repo                    | Labels                                                         | Content                                                                                                                              |
| ------------------------------------------------------------------------- | ----------------------- | -------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| [#2695](https://github.com/abhimehro/personal-config/issues/2695)         | personal-config         | `priority:high`                                                | **R2** — G-1 freshness gate + G-2 target ledger, 9 h                                                                                 |
| [#2696](https://github.com/abhimehro/personal-config/issues/2696)         | personal-config         | `priority:medium`                                              | **R3** — G-3 SLA/expiry/decay + G-7 KPIs, 11 h                                                                                       |
| [#2697](https://github.com/abhimehro/personal-config/issues/2697)         | personal-config         | `priority:low`                                                 | **R4** — G-6 label identity, 4 h                                                                                                     |
| [#2691](https://github.com/abhimehro/personal-config/issues/2691)         | personal-config         | `cleanup`, `priority:low`                                      | Untrack `.trunk/{actions,logs,notifications,out,tools}` absolute symlinks                                                            |
| [#2692](https://github.com/abhimehro/personal-config/issues/2692)         | personal-config         | `cleanup`, `priority:low`                                      | Unreachable "Already in Todo; no-op" branch in `pr_recap.compute_state_transition`                                                   |
| [#2693](https://github.com/abhimehro/personal-config/issues/2693)         | personal-config         | `cleanup`, `priority:low`                                      | No versioned, reproducible backup script — the root cause of §3                                                                      |
| [#2694](https://github.com/abhimehro/personal-config/issues/2694)         | personal-config         | `dependencies`, `security`, `priority:high`                    | `@azure/msal-node` 5.1.5 → 7.1.0 major bump, **held for human review**                                                               |
| [#2700](https://github.com/abhimehro/personal-config/issues/2700)         | personal-config         | `bug`, `agentic-workflows`, `priority:medium`                  | `canary-stage` hardcodes `CRON_TZ=UTC` at `antigravity-proactive-ctl.sh:270`, so the canary never exercises the pilot timezone (§17) |
| [#1123](https://github.com/abhimehro/Seatek_Analysis/issues/1123)         | Seatek_Analysis         | `cleanup`, `priority:medium`, `bug`                            | `test_structure.sh` overwrites tracked `implementation/package_manifest.rds` on every run                                            |
| [#1124](https://github.com/abhimehro/Seatek_Analysis/issues/1124)         | Seatek_Analysis         | `dependencies`, `security`, `priority:high`, `ready-for-human` | All 41 Dependabot alerts are one Pillow major bump (12.3.0 → 13.0.0)                                                                 |
| [#1845](https://github.com/abhimehro/email-security-pipeline/issues/1845) | email-security-pipeline | `cleanup`, `priority:low`                                      | trunk runs bandit without `--ini .bandit`, diverging from CI                                                                         |
| [#1846](https://github.com/abhimehro/email-security-pipeline/issues/1846) | email-security-pipeline | `cleanup`, `priority:low`                                      | `HIDDEN_TEXT_PATTERN` becomes dead code once #1844 lands                                                                             |

R2–R4 issues are deliberately **self-contained**: the design doc lives outside
the repo and on an unmerged branch, so an agent working from `main` cannot read
it. Each carries its own evidence, design, file list, acceptance criteria,
effort, dependencies, known traps, and an explicit "out of scope" that refuses
release valves.

`#1123` is the one "noted but not filed" item promoted above `low-priority`, on
the reasoning that it nearly shipped a generated artifact inside PR #1121 — once
is once too many. Fix options recorded: have `test_structure.sh` write to a temp
dir, or untrack the file.

**Dependabot triage, Seatek_Analysis (read-only).** The 5 criticals resolve to a
single Pillow major bump; **all 41 alerts are that one bump**, recorded in #1124
and held for human review rather than batched. personal-config's 2 highs are
`@azure/msal-node` 5.1.5 → 7.1.0, held in #2694 for the same reason: **major
bumps are flagged for human decision, not auto-applied.**

## 23. Secret-scan record

Kept in full because the methodology is the reusable part, and because the naive
reading of these numbers is badly wrong. Rules 1 and 2 are secret-scan specific;
**Rule 3 generalises to every integrity verdict in this document**, which is why
it lives here rather than in §3.

**Rule 1 — never print a raw candidate value.** Report
`prefix + length + sha256[:8] + charset classes + Shannon entropy + verdict` so
a human can match against their own records without exposure. Session IDs are
cited; raw `description` and `activities.json` excerpts are not reproduced.

**Rule 2 — start with word boundaries, not with a prefix.** Anchor every
secret-prefix regex (`\bsk-`, `\bnt-`, `\bnpm_`, …) before you run the sweep. An
unanchored prefix matches the _inside_ of ordinary identifiers, and agent
transcripts are full of them: `task-`, `agent-`, `content-`, fractions and
paths. This is a starting instruction, not a post-hoc caveat — an unanchored
first pass reports a hit count that is ~98% noise (§23 measured it), and the
cost of believing that count is a pointless credential-rotation scramble. If a
sweep arrives already unanchored, re-run it anchored before triaging a single
hit. `scripts/secret_prefix_scan.py`'s `PREFIX_RE` is still unanchored; treat
its raw output as a candidate pool requiring an anchored second pass.

**Rule 3 — content over metadata: no integrity verdict without a content
check.** `corrupt`, `truncated`, `MATCHED`, and `DRIFTED` are claims about
_bytes_, so they require byte evidence — a hash, a checksum, or a listing. Size
and timestamps can **raise** a suspicion; they cannot **settle** one. This is
the same principle as Precondition 0 (`require_fresh_origin_ref` in
`scripts/proactive-worktree.sh`), which refuses to emit a ref-based verdict from
a possibly stale `origin/*`: in both cases a cheap indirect signal is allowed to
_open_ an investigation and never to _close_ one.

Three verdicts in this record were built on indirect evidence before the rule
existed, and all three were wrong:

| Verdict                                                            | Indirect evidence relied on                     | Content check that refuted it                                                                  |
| ------------------------------------------------------------------ | ----------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| "already merged" → a DRIFTED verdict that should have been MATCHED | a stale `origin/main`                           | `git fetch` first — the ref was behind, so the comparison was against history (Precondition 0) |
| three claims downgraded in §2/§3                                   | sizes, entry counts, and assumed provenance     | re-read against the live records and the two distinct manifests                                |
| **"two of three cloud backups are corrupt, truncated by 1 byte"**  | `.sizes` arithmetic across two compression runs | whole-file sha256 — both cloud copies are `71c643c2…`, an exact manifest match (§3)            |

The third is the expensive one. It was committed, and the repair step it implied
would have overwritten two verified-good archives with a byte-different file
from another run. **The arithmetic _was_ airtight; the premise underneath it was
not.** A size expectation derived from one artifact says nothing about a second
artifact — which is exactly why the rule is about the _kind_ of evidence, not
about how carefully the arithmetic is done.

**Rule 3 also covers structure inferred from an aggregate — and it was violated
again after the rule was written.** The 2026-11-03 disk survey reported
Raycast's backup directory as "6 backup sets of `ai.db`, 1,269 MiB each". Both
numbers were derived: 7,112 MiB from `du` divided by an assumed count of 6.
Enumerating the directory shows **5** sets of **1,423 MiB** plus a 10-byte
marker. The total was right and the shape was wrong, and the shape was the part
that mattered — 5 sets appearing every ~12 h is a **rolling window that
refills**, so the reclaim it promised is a 2.5-day loan, not permanent headroom.
A `du` total is metadata about bytes; a count and a per-item size are claims
about _structure_, and structure requires enumeration. Same rule, new domain:
the failure mode survived being written down because the rule was filed under
"integrity verdicts" and the survey did not look like one.

### The prefix sweep

375 files scanned, 373 hits. The scanner's own verdicts: **LOOKS-REAL = 204**,
AMBIGUOUS = 66, other = 103.

**199 of the 204 are false positives.** The scanner's prefix regex is
**unanchored**, so it matches `sk-` inside `task-`, `nt-` inside `agent-` and
`content-`, `1/` inside fractions and paths, and `npm_`, `ag_`, `key-`
similarly. Breakdown by prefix: `sk-` 69, `1/` 55, `nt-` 52, `npm_` 13, `ag_` 6,
`op://` 5, `key-` 4.

Re-verified with word-boundary anchoring: **199 FALSE-POSITIVE, 5
ANCHORED-MATCH**. All 5 survivors are `op://` **1Password vault pointers** —
references that resolve only with a live 1Password auth session and contain no
secret material — and all 5 share one identical fingerprint (`sha256=b80cbf4a`,
len=39), appearing in two session activity logs (`3022686378800630836`,
`15845540631174641678`).

> **Methodological finding, not a code bug:** an unanchored secret-prefix regex
> on agent transcripts produces a ~98% false-positive rate, because transcripts
> are full of identifiers that _contain_ key prefixes. Anchor on word boundaries
> before believing any count.

### The gitleaks report

9 findings, all `generic-api-key`. All four locations resolved:

| Location                                                                                                       | n | Classification                                                                                                                                                                                                                                                                 |
| -------------------------------------------------------------------------------------------------------------- | - | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `unrecovered/5815873277372019599.patch`                                                                        | 5 | The morning-brief patch. **The only promoted session of the nine.** Its 5 literals were swapped for obvious `…TEST_NOT_A_REAL_KEY`-style sentinels before promotion as #2690, gitleaks re-run clean, output attached to the PR.                                                |
| `capture-2/recovered-404s/{5577487469923147813, 2529216662181495156, 8751251634449908055}/session-pruned.json` | 3 | Identical fingerprint (`sha256=4e9eccfc`, len=17, key `apiKey`). Context is a JavaScript **teaching example** inside a persona prompt — the line immediately before is a "BAD: Hardcoded secret" comment. Not promoted.                                                        |
| `capture-2/17936630851935504543/patch-1.diff:168`                                                              | 1 | A **negative assertion** in `tests/test_morning_brief_security.py` comparing `client.api_key` against a 16-char `pplx-…` placeholder — i.e. a test proving the key is _not_ the placeholder. Session is a 🔒 Security persona run on personal-config, COMPLETED. Not promoted. |

### Verdict

**Nothing to rotate.** No live credentials in the derived workspace under the
scanned prefix set. Confirmed separately that **zero** `capture-2` or
`jules-analysis` paths and **zero** of the cited session IDs appear in the
branch diff against `main` — the derived workspace never entered the repo, and
this document cites session IDs only.

Prevention shipped as #2686: gitleaks as a pre-commit hook, no allowlist. The
repo is **public** (`isPrivate: false`), so this gate is mandatory rather than
advisory, and this document was scanned with gitleaks, trufflehog and
`make verify-credentials` before commit.

## 24. Open questions and next steps

### Open

| # | Question                                                                    | Note                                                                                                                                                                                                                                                                                                                                                |
| - | --------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1 | Does the Jules REST API survive read-only mode after 2026-11-11?            | Plan a list-only re-check near Nov 11; capture only new IDs                                                                                                                                                                                                                                                                                         |
| 2 | Which session's origin/status drifted between the list-only and full fetch? | Immaterial — 1 of 144                                                                                                                                                                                                                                                                                                                               |
| 3 | Are the 110 open Jules PRs mergeable at current HEAD?                       | `mergeable_state` is not returned by the list endpoint; needs per-PR fetch                                                                                                                                                                                                                                                                          |
| 5 | Is the Proton part _content_ intact (not just its sizes)?                   | **Blocked and no longer load-bearing.** All 5 parts are `dataless`, `brctl` has no eviction subcommand on darwin 27.2, and rclone's `protondrive` backend is unconfigured — hashing them would hydrate 9.2 GiB permanently against a 4 GiB floor. §3 also showed the parts are a _different compression_, so they are not the backup of record (§4) |
| 6 | Is `$(date -u +%Y-%m-%d)` shell-expanded inside a sidecar `args` array?     | §17; one canary run settles it. Note #2700 must land first, or the canary runs in the wrong timezone                                                                                                                                                                                                                                                |
| 7 | Does the `palette` lens produce anything worth promoting?                   | New lens, no Jules history, 0 of 9 recovered patches                                                                                                                                                                                                                                                                                                |

### Resolved (2026-11-02 / 11-03)

| Question                                                                         | Answer                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| -------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Are the OneDrive/Google Drive archives truncated?                                | **No.** Both hash to `71c643c2…`, exactly the recorded manifest value; `zstd -dc` exits 0 with `Content_Checksum_flag = 1`, so all ~19.5 GiB of decompressed output was checksum-verified (§3)                                                                                                                                                                                                                                                                                                                 |
| What is the 1-byte size difference against Proton's parts?                       | **Two different compressions 18 h apart**, not a truncation. The cloud archive's first 2 GiB hashes to `b2681d86…`, not `part-aa`'s recorded `4a1cb93f…` (§3)                                                                                                                                                                                                                                                                                                                                                  |
| Is the archive's _content_ complete relative to the local tree?                  | **Yes.** Full listing diffed against `find`: 34,243 archive entries vs 34,248 local, with **0 entries missing from the archive** and exactly 5 local-only entries (3 `.DS_Store`, `__pycache__`, one `.pyc`) (§3)                                                                                                                                                                                                                                                                                              |
| Does the cloud `sessions.json` match local byte-for-byte?                        | **Confirmed yes.** `13422e1691db14f7412b74e2a904048e82c275056aff7a45c6157e37fb3e4bf6` on both clouds, matching local, at 276,431,176 bytes                                                                                                                                                                                                                                                                                                                                                                     |
| Should the incomplete loose cloud `repos/` be re-mirrored?                       | **No.** The full `repos/` subtree is inside the verified tarball; the partial loose copies are redundant stubs                                                                                                                                                                                                                                                                                                                                                                                                 |
| Is archive repair needed (§4 step 3)?                                            | **No — struck.** Executing it would have replaced two verified-good archives with a byte-different file from another compression run                                                                                                                                                                                                                                                                                                                                                                           |
| Do extracted file _contents_ from the cloud archive byte-match local?            | **Yes — the last real gap is closed.** Four members streamed out of the compressed cloud archive (`rclone cat \| zstd -dc \| tar -xO <member> \| shasum -a 256`, no disk write) and hashed against local: `sources.json` `42b35538058e`, `errors.json` `87267bba344e`, `export_jules.py` `5fc87fb3fb1c`, `sessions.json` `13422e1691db` — **all four MATCH** (§3). Deleting the local tree now waits only on explicit approval — `tmutil listlocalsnapshots /` is empty, so the space is genuinely reclaimable |
| **Testing lens** — own rotation slot, or folded into `code-health`? (2026-11-03) | **Folded in.** Run the testing lens inside `code-health` with `--focus` during R1; no new rotation slot until there is data to justify one. **Promotion criteria, evaluated at the R1 readout (Mon 2026-11-09):** give it its own slot if testing findings exceed **~⅓ of `code-health` output**, or if `--focus` runs keep **pushing other findings out**. Below both thresholds it stays folded                                                                                                              |

### Next steps, in order

1. **R2** ([#2695](https://github.com/abhimehro/personal-config/issues/2695), 9
   h) — freeze the ledger row schema first; R3 is blocked on it.
2. **R3** ([#2696](https://github.com/abhimehro/personal-config/issues/2696), 11
   h) — then **R4**
   ([#2697](https://github.com/abhimehro/personal-config/issues/2697), 4 h).
   Never R3 ∥ R4; both edit `check-throttle`.
3. **R5 pilot** — `ctrld-sync` week 1, only after R2. Then `1B` → `1A`.
4. **Reclaim** (§4 steps 5–8, reordered) — copy #3 to iCloud **first**, verify
   it with a streaming sha256, **then** delete the 19 GiB tree, then archive the
   tarball. The extraction spot-check is **done and passed** (four streamed
   members byte-match local, §3), so deletion needs no further verification —
   but it is sequenced last, and step 5 is currently **blocked on local
   staging** (`disk-guard.sh` REFUSES the 8.59 GiB write; rclone's `iclouddrive`
   backend is the clean fix and needs interactive Apple auth). Repair is no
   longer on the list; nothing needs repairing.
5. **Batch the 23 high-severity Dependabot alerts** across repos into a single
   tracking issue, after R1. Major bumps stay held for human review (#2694,
   #1124).
6. **Let R1 run for a week** before sequencing R2–R4 further — the rollout plan
   is deliberately provisional on observed behaviour.

## 25. Reproducibility

The analysis is reproducible from the export plus these derived artifacts, all
in the scratch workspace (which is **not** in this repo and never will be):

| Artifact                                         | Purpose                                                                                                     |
| ------------------------------------------------ | ----------------------------------------------------------------------------------------------------------- |
| `classify_failures.py` → `failure-taxonomy.json` | Rule-ordered failure classifier; rule order is stated in the script docstring                               |
| `index-origins.ndjson`, `census_origins.py`      | Origin/status census over the 264 MiB index without loading it                                              |
| `burst-fuzzy-clusters.json`                      | Duplicate clustering, exact and fuzzy                                                                       |
| `gh-pr-outcomes.json`, `pr-outcomes-joined.json` | Live GitHub outcome pass (113 PRs)                                                                          |
| `proactive-corpus.json`                          | The 1,158-session local proactive corpus                                                                    |
| `unrecovered/*.patch` + `manifest.json`          | The 9 recovered patches with per-patch sha256, file lists, hunk/add/del counts, and applicability verdicts  |
| `prompts/personas/*.md`                          | The four recovered persona templates, verbatim                                                              |
| `secret_prefix_scan.py`                          | Masked-fingerprint prefix sweep — **see the anchoring caveat in §23**                                       |
| `disk-guard.sh`, `DISK-GUARD.md`                 | Disk-safety governor                                                                                        |
| `NONMOD-MARKER`                                  | Proves the source export was never modified                                                                 |
| `manifests/`                                     | The three integrity manifests transcribed into §2                                                           |
| `phase6-archive-hashes.out`                      | Whole-file sha256 of both cloud archives, with sizes and UTC timestamps — the evidence for §3               |
| `phase6-tar-listing.txt`                         | All 34,244 archive entry names, streamed; diffed against `find ~/jules-export` for the zero-omission result |
| `phase6-onedrive.out`                            | The `zstd -dc \| tar -t \| wc -l` structural pass with per-stage exit codes                                 |
| `phase6-extraction-spotcheck.out`                | The four streamed `tar -xO` member hashes against local — the evidence that closes §4 step 7's last gate    |
| `capture-2-prune-manifest.ndjson`                | The 133 `capture-2/` session captures removed on 2026-11-03 (10.4 MiB), one line per entry with size        |

**What survived the `capture-2/` prune, and why.** `capture-2/` went from 13,964
KiB to 3,344 KiB. The 20 retained entries are exactly the ones this document
cites: the seven index/provenance files (`index.ndjson`, `pr-index.ndjson`,
`recovered-index.json`, `sources-live.json`, `tier-b-manifest.json`,
`still-lost.json`, `capture-errors.json`), the whole `recovered-404s/` tree
(three of whose `session-pruned.json` files are the gitleaks evidence in §23),
the nine promoted-source sessions plus the dropped `parse_inventory.py`
duplicate, `17936630851935504543/patch-1.diff:168`, and the two activity logs
`3022686378800630836` / `15845540631174641678` behind §23's unanchored-regex
false-positive finding.

The keep list was derived by intersecting the prune set against every 15–25
digit ID cited anywhere under `docs/`, `tasks/`, `scripts/`, `tests/`,
`.github/`, and `automation/` (620 files). That check is what caught the two
activity-log sessions: they were in the prune set on the first pass, and
deleting them would have removed the evidence for a finding the document states.
**Zero** prunable IDs are cited after the correction.

**The 25 MiB scratch cap is now 3 MiB short, and the shortfall is all
load-bearing.** After the prune, scratch is 28 MiB. The only remaining
candidates large enough to close the gap are `index-origins.ndjson` (2.1 MiB),
`phase6-tar-listing.txt` (1.7 MiB) and `proactive-corpus.json` (448 KiB) — all
three cited in this table, and the tar listing is the _listing_ half of the §23
Rule 3 content evidence for the archive-integrity verdict, reproducible only by
another ~16-minute streaming pass over 8.6 GiB. The cap should rise to ~32 MiB
rather than the evidence fall. `disk-guard.sh gate` treats the overage as a
warning (exit 0), so nothing is blocked in the meantime.

**Commands that reproduce §3 from a clean shell** (all zero-local-disk):

```bash
# Hash identity against the manifest (71c643c2…)
for R in onedrive gdrive; do
  rclone cat "$R:HomeBackup/jules-export/jules-export-20261031.tar.zst" | shasum -a 256
done

# Structure + completeness: expect 34244 and pipestatus 0 0 0 0
rclone cat onedrive:HomeBackup/jules-export/jules-export-20261031.tar.zst \
  | zstd -dc | tar -t | wc -l; echo "${PIPESTATUS[*]}"

# Frame header: expect magic 28b52ffd then FHD 0x04 => Content_Checksum_flag=1
rclone cat --count 16 onedrive:HomeBackup/jules-export/jules-export-20261031.tar.zst | xxd

# Proton parts are a different compression: b2681d86… != part-aa's 4a1cb93f…
rclone cat --count 2147483648 onedrive:HomeBackup/jules-export/jules-export-20261031.tar.zst \
  | shasum -a 256

# sessions.json byte-identity: expect 13422e16… on both clouds and locally
rclone cat onedrive:HomeBackup/jules-export/sessions.json | shasum -a 256
shasum -a 256 ~/jules-export/sessions.json

# Extraction spot-check: pull one member out of the compressed stream, no disk.
# -q (bsdtar fast-read) stops after the first match instead of draining 9.2 GiB.
for m in sources.json errors.json export_jules.py sessions.json; do
  rclone cat onedrive:HomeBackup/jules-export/jules-export-20261031.tar.zst \
    | zstd -dc | tar -xO -q "$m" | shasum -a 256
done
```

**Operational caveat on that last loop — and its fix.** As originally run,
without `-q`, `tar` reading from a pipe does **not** exit after it has emitted
the requested member — it keeps draining stdin — so each of the four passes
streamed the entire 9.2 GiB. Four members cost ~16 min of wall time, not
seconds, and the loop exceeded a 900 s foreground timeout on the first attempt.

The fix, verified on this host rather than assumed:

- macOS `/usr/bin/tar` **is** bsdtar 3.5.3 (libarchive 3.7.4), so `-q` /
  fast-read is available natively — no GNU tar needed (`gtar` is not installed
  here). GNU tar's equivalent is `--occurrence=1`.
- Measured on a synthetic archive with the target member first and 300 MiB of
  trailing filler: **0.020 s with `-q` vs 0.097 s without**, and the two outputs
  hash identically. The gap scales with what sits _after_ the member, so on the
  real 9.2 GiB archive it is the difference between seconds and ~4 min per
  member.
- **`-q` makes the producer die of SIGPIPE.** Measured `PIPESTATUS` is `141 0 0`
  with `-q` and `0 0 0` without. That 141 means "the consumer stopped reading
  early", **not** "the stream is corrupt". This matters because the structural
  check two blocks up asserts `pipestatus 0 0 0 0` — adding `-q` there without
  understanding the 141 would manufacture a false corruption alarm of exactly
  the kind §3 had to retract. Use `-q` for single-member extraction; never for a
  completeness check.

A single pass that extracts several members at once is still four times cheaper
than four passes, with or without `-q`.

**Disk governor thresholds**, kept because they are the reason the analysis
completed at all after two host-level disk exhaustion incidents rendered the
machine unusable: `HARD=4096 MiB`, `PAUSE=6144`, `WARN=8192`, `RESERVE=1024`,
`SCRATCH_CAP=25 MiB`. Subcommands
`report | check | budget <bytes> |
gate <label>`. Headroom is computed as **free
− floor**, not free.

**Resource discipline actually observed.** Analysis phases: ~250–400 MiB read
locally out of 19 GiB (≈1–2%), < 20 MiB written locally, peak RAM < 300 MiB, all
intensive jobs sequential, network limited to gated probes. Phase 6 verification
added **~67 GiB of streaming network traffic and ~2 MiB of local writes** — nine
full or partial archive passes (five for structure/hash/checksum, four for the
extraction spot-check), all through `rclone cat` into a pipe, so **no archive
byte ever landed on local disk**. Free space moved 11.5 GiB → 11.0 GiB across
the whole exercise; every step was gated through `disk-guard.sh gate` and none
tripped PAUSE or ABORT. The one path that _would_ have violated the constraint —
hashing Proton's dataless parts — was identified and refused rather than
attempted (§4).

---

_Source export untouched: 0 files newer than `NONMOD-MARKER`, 19.5 GiB. This
document is the durable record; the export itself is pending archival to iCloud
per §4._

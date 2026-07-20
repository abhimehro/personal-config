# PR Triage — 2026-07-20 Phase 2 Salvage

## Salvage / close

| Group | Keep | Close | Reason |
|-------|------|-------|--------|
| rpce DateFormatter statics | [#133](https://github.com/abhimehro/repoprompt-ce/pull/133) draft | [#132](https://github.com/abhimehro/repoprompt-ce/pull/132) | Style: 4 files needed SwiftFormat (Lesson 0ef) |

## Ready for human merge (Phase 2 does not merge)

| PR | Reason |
|----|--------|
| [ctrld #1036](https://github.com/abhimehro/ctrld-sync/pull/1036) | CodeScene remediates post-`/cs-agent`; all CI green; Trunk checkbox soft-UNSTABLE |

## Security / trust escalate (unchanged)

| PR | Reason |
|----|--------|
| [sc #233](https://github.com/abhimehro/series_correction_project_updated/pull/233) | Auth / session tokens |
| [hg #374](https://github.com/abhimehro/Hydrograph_Versus_Seatek_Sensors_Project/pull/374) | numpy 1→2 major |
| [pc #1670](https://github.com/abhimehro/personal-config/pull/1670) | Gemini + PR-automation toolchain; CONFLICTING (0ea) |
| [rpce #126](https://github.com/abhimehro/repoprompt-ce/pull/126)/[#127](https://github.com/abhimehro/repoprompt-ce/pull/127) | Tip-release artifact majors (0dw) |

## Maintainer priority

1. **T3 draft:** [rpce #133](https://github.com/abhimehro/repoprompt-ce/pull/133) after Style/Build green
2. **Human merge:** [ctrld #1036](https://github.com/abhimehro/ctrld-sync/pull/1036)
3. **T1:** sc #233 (auth)
4. **T2:** pc #1670 (keep ShellCheck vs delete + Gemini/gitleaks)
5. **T2:** hg #374 (numpy major)
6. **T2:** rpce #126/#127 (tip artifact majors)

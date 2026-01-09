# Archive Cleanup Log - windscribe-controld/

**Date**: 2026-01-09  
**Version**: v4.2 (Network Mode Manager Fixes)

## Removed Scripts

The following scripts were temporary fixes or troubleshooting tools that are no longer needed after implementing the unified Network Mode Manager (`scripts/network-mode-manager.sh`):

### Individual Fix Scripts (Removed)
These scripts addressed specific issues in an ad-hoc manner and are superseded by the comprehensive `controld-manager` and network mode verification system:

- `fix-controld-binding.sh` - Fixed port 53 binding issues (now handled by controld-manager)
- `fix-controld-config.sh` - Fixed configuration generation (now integrated into controld-manager)
- `fix-controld-manager.sh` - Patched controld-manager (now replaced with full rewrite)
- `fix-dns-priority.sh` - Fixed DNS resolver ordering (now handled by network-mode-manager)
- `permanent-binding-fix.sh` - Permanent binding workaround (no longer needed)
- `windscribe-connection-troubleshoot.sh` - Troubleshooting helper (functionality moved to network-mode-verify.sh)

### Rationale
These scripts were created incrementally as issues were discovered. With the new unified **Network Mode Manager** system, all functionality has been consolidated into:
- `scripts/network-mode-manager.sh` - Unified mode switching orchestrator
- `scripts/network-mode-verify.sh` - Comprehensive verification with detailed diagnostics
- `controld-system/scripts/controld-manager` - Profile and DNS configuration management

## Current Recommended Approach

Use the new aliases for all network mode operations:
```bash
nm-browse        # Control D browsing profile
nm-privacy       # Control D privacy profile
nm-gaming        # Control D gaming profile
nm-vpn           # Windscribe VPN mode
nm-status        # Show current status
nm-regress       # Run regression test
```

Or invoke scripts directly:
```bash
./scripts/network-mode-manager.sh {controld|windscribe|status} [profile]
./scripts/network-mode-verify.sh {controld|windscribe} [profile]
```

## Known Issues Fixed (v4.2)

1. **Path Resolution Bug** - network-mode-manager.sh now uses absolute path resolution for controld-manager
2. **DNS Verification Strictness** - network-mode-verify.sh now accepts localhost in any resolver position
3. **DNS Configuration Clarity** - controld-manager now explicitly configures and validates DNS settings
4. **Placeholder IP Addresses** - All `*********` placeholders replaced with actual `127.0.0.1`

See main repository CHANGELOG for detailed fix descriptions.

## Archived Files

All removed scripts have been preserved in `windscribe-controld/ARCHIVE.md` for historical reference.

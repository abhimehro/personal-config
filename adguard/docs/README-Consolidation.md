# AdGuard List Consolidation

This directory contains consolidated ad-blocking lists for AdGuard macOS, combining multiple tracker lists into two comprehensive files.

## Files Created

### 1. Consolidated-Denylist.txt
- **Purpose**: Contains all domains that should be blocked
- **Source Lists**: All tracker lists (Microsoft, No SafeSearch, OPPO/Realme, Roku, Samsung, TikTok, Vivo, Xiaomi, Amazon, Apple, Badware Hoster, LG webOS, Huawei)
- **Format**: One domain per line
- **Usage**: Import as denylist in AdGuard macOS

### 2. Consolidated-Allowlist.txt
- **Purpose**: Contains domains that should NOT be blocked
- **Source Lists**: CD-Control-D-Bypass + legitimate entries from CD-Most-Abused-TLDs
- **Format**: AdGuard allowlist syntax (`@@domain.com`)
- **Usage**: Import as allowlist in AdGuard macOS

### 3. Python Scripts
- **create_consolidated_lists.py**: Complete consolidation script
- **extract_domains.py**: Simple domain extraction utility
- **consolidate_adblock_lists.py**: Alternative consolidation approach

## How to Use

### For AdGuard macOS:

1. **Import Denylist**:
   - Open AdGuard for macOS
   - Go to Preferences > Filters
   - Click "Custom Filters" tab
   - Click "Add filter" → "Add a custom filter"
   - Name: "Comprehensive Tracker Denylist"
   - Import `Consolidated-Denylist.txt`

2. **Import Allowlist**:
   - Go to Preferences > Filters
   - Click "Allowlist" tab
   - Click "Add website to allowlist"
   - Import `Consolidated-Allowlist.txt`

### For Complete Consolidation:

Run the Python script to generate complete consolidated lists:

```bash
python3 create_consolidated_lists.py
```

This will create:
- `Consolidated-Denylist.txt` (complete)
- `Consolidated-Allowlist.txt` (complete)
- `Consolidated-Denylist.json` (JSON reference)
- `Consolidated-Allowlist.json` (JSON reference)

## Important Notes

⚠️ **AdGuard macOS Limitation**: The macOS app only supports importing one denylist and one allowlist. Importing additional lists will override existing ones.

📊 **Expected Domain Counts**:
- Denylist: ~25,000+ domains
- Allowlist: ~5,000+ domains

🔧 **Customization**: You can modify the Python scripts to exclude specific tracker lists or add additional filtering criteria.

## Source Lists Included

### Denylist Sources:
- CD-Microsoft-Tracker.json
- CD-No-Safesearch-Support.json
- CD-OPPO_Realme-Tracker.json
- CD-Roku-Tracker.json
- CD-Samsung-Tracker.json
- CD-Tiktok-Tracker---aggressive.json
- CD-Vivo-Tracker.json
- CD-Xiaomi-Tracker.json
- CD-Amazon-Tracker.json
- CD-Apple-Tracker.json
- CD-Badware-Hoster.json
- CD-LG-webOS-Tracker.json
- CD-Huawei-Tracker.json

### Allowlist Sources:
- CD-Control-D-Bypass.json (all entries with `"do": 1`)
- CD-Most-Abused-TLDs.json (entries with `"do": 1`)

## File Structure

```
/Users/abhimehrotra/Downloads/
├── Consolidated-Denylist.txt          # Main denylist for AdGuard
├── Consolidated-Allowlist.txt         # Main allowlist for AdGuard
├── create_consolidated_lists.py       # Complete consolidation script
├── extract_domains.py                 # Simple extraction utility
├── consolidate_adblock_lists.py       # Alternative approach
├── README-Consolidation.md            # This file
└── [Original tracker files]           # Source JSON files
```

## Next Steps

1. **Test the Configuration**: After importing both lists, test your AdGuard setup to ensure proper functionality
2. **Monitor Performance**: Large lists may impact performance; monitor system resources
3. **Regular Updates**: Consider setting up automated updates for the source lists
4. **Backup**: Keep backups of your consolidated lists before making changes

## Troubleshooting

- **Import Issues**: Ensure file encoding is UTF-8
- **Performance**: If experiencing slowdowns, consider reducing list size
- **False Positives**: Add legitimate domains to the allowlist
- **Missing Blocks**: Verify denylist is properly imported and enabled

## Support

For issues with the consolidation process or AdGuard configuration, refer to:
- AdGuard documentation: https://adguard.com/en/support.html
- AdGuard community forums: https://forum.adguard.com/

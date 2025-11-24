# Media Upload Guide - Unified Cloud Library

## ✅ Current Setup Status

Your unified cloud library is configured correctly:

- ✅ **Google Drive remote** (`gdrive:`) - Configured
- ✅ **OneDrive remote** (`onedrive:`) - Configured
- ✅ **Union remote** (`media:`) - Combines both providers
- ✅ **Folder structure** - All folders exist (Movies, TV Shows, Documentaries, Kids, Music, 4K)
- ✅ **Infuse connection** - Working

## 📁 Where to Place New Media Files

### **Recommended: Use the Union Remote (Automatic Distribution)**

**Best Practice**: Upload directly to the `media:` union remote. The union will automatically:
- **Distribute files** based on available space (`create_policy = epmfs`)
- **Show files from both** providers in Infuse (`action_policy = epall`)
- **Search efficiently** across both (`search_policy = ff`)

#### Upload via rclone:
```bash
# Upload a movie
rclone copy "/path/to/Movie Name (2024).mkv" media:Movies/

# Upload a TV show episode
rclone copy "/path/to/episode.mkv" "media:TV Shows/Show Name/Season 01/"

# Upload multiple files
rclone copy "/path/to/media/" media:Movies/ --progress
```

#### Upload via Cloud Providers (Alternative):

You can also upload directly to either cloud provider:

**Option A: Google Drive**
- Upload to: `Google Drive/Media/Movies/` (or appropriate subfolder)
- Files will appear in Infuse via union remote
- Good if: Google Drive has more free space

**Option B: OneDrive**
- Upload to: `OneDrive/Media/Movies/` (or appropriate subfolder)
- Files will appear in Infuse via union remote
- Good if: OneDrive has more free space

**Important**: Make sure you upload to the `Media/` folder (not root) on both providers!

### **Union Remote Behavior**

Your union remote uses these policies:

- **`create_policy = epmfs`** (existing path, most free space)
  - When uploading to `media:`, files go to the provider with **most free space**
  - Automatically balances storage between Google Drive and OneDrive

- **`action_policy = epall`** (existing path, all)
  - Shows files from **both** providers
  - If same file exists in both, both appear (union shows all)

- **`search_policy = ff`** (first found)
  - Searches Google Drive first, then OneDrive

## 🎯 Recommended Workflow

### **For New Media Files:**

1. **Upload via rclone to union remote** (Recommended):
   ```bash
   rclone copy "/path/to/file.mkv" media:Movies/ --progress
   ```
   - Automatically goes to provider with most free space
   - Appears immediately in Infuse
   - No need to manually choose provider

2. **Or upload directly to cloud provider**:
   - Upload to `Google Drive/Media/Movies/` OR
   - Upload to `OneDrive/Media/Movies/`
   - Files appear in Infuse automatically
   - Choose provider based on available space

### **For Bulk Uploads:**

```bash
# Upload entire directory
rclone copy "/path/to/media/" media:Movies/ --progress --transfers 4

# Sync directory (removes files not in source)
rclone sync "/path/to/media/" media:Movies/ --progress

# Move files (deletes from source after upload)
rclone move "/path/to/media/" media:Movies/ --progress
```

## 📊 Checking Available Space

```bash
# Check Google Drive space
rclone about gdrive:

# Check OneDrive space
rclone about onedrive:

# Check union remote (shows combined)
rclone about media:
```

## 🔍 Verifying Files After Upload

```bash
# List files in union remote
rclone ls media:Movies/

# List files in specific folder
rclone ls "media:TV Shows/Show Name/Season 01/"

# Check file exists
rclone ls media:Movies/ | grep "Movie Name"
```

## ⚠️ Important Notes

### **Folder Structure Must Match**

For the union to work properly, both providers should have identical structure:

```
Media/
├── Movies/
├── TV Shows/
├── Documentaries/
├── Kids/
├── Music/
└── 4K/
```

**If structures differ:**
- Union will show files from both, but may be confusing
- Best to keep structures identical

### **File Naming Conventions**

For best Infuse experience:

**Movies:**
```
Movie Name (Year).ext
Example: The Matrix (1999).mkv
```

**TV Shows:**
```
TV Shows/Show Name/Season XX/Show Name SXXEXX.ext
Example: TV Shows/Breaking Bad/Season 01/Breaking Bad S01E01.mkv
```

### **Upload Methods Comparison**

| Method | Pros | Cons |
|--------|------|------|
| **rclone to `media:`** | Auto-distributes, efficient, shows progress | Requires command line |
| **Google Drive web** | Easy, visual interface | Manual space management |
| **OneDrive web** | Easy, visual interface | Manual space management |
| **Cloud sync apps** | Automatic, background | May sync to wrong folder |

## 🚀 Quick Reference Commands

```bash
# Upload single file
rclone copy "/path/to/file.mkv" media:Movies/

# Upload directory
rclone copy "/path/to/folder/" media:TV\ Shows/Show\ Name/ --progress

# Check what's in union
rclone ls media:Movies/

# Check space
rclone about gdrive: && rclone about onedrive:

# Verify union config
rclone config show media
```

## 💡 Pro Tips

1. **Use rclone for large files**: More reliable than web uploads, shows progress
2. **Check space first**: Upload to provider with more free space if doing manual uploads
3. **Keep structures identical**: Makes union remote work seamlessly
4. **Use progress flag**: `--progress` shows upload status
5. **Test after upload**: Verify files appear in Infuse before deleting local copies

---

**Your setup is working perfectly!** Just upload files to `media:` remote or directly to either cloud provider's `Media/` folder, and they'll appear in Infuse automatically.

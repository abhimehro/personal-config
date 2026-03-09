🎯 **What:** The `generate_directory_listing` function in `media-streaming/archive/scripts/infuse-media-server.py` lacked unit tests. This PR adds a new test method to `tests/test_infuse_media_server.py` to cover this functionality.

📊 **Coverage:**
- Root path handling (no parent directory link).
- Subdirectory handling (includes parent directory link).
- Path and item HTML escaping.
- File and directory link generation.
- Icon selection for videos vs generic files vs directories.

✨ **Result:** Increased confidence in the media server's directory listing generation. The new test catches structural defects and logic regressions in how HTML and paths are created from a file list.

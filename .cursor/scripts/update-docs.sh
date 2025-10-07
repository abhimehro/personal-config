     #!/bin/bash
     # Update documentation with current config values

     echo "📝 Updating documentation with latest config details..."

     # Extract current DNS profiles from switcher script
     GAMING_PROFILE=$(grep "PROFILES_gaming=" scripts/ctrld/ctrld-switcher.sh | cut -d'"' -f2)
     PRIVACY_PROFILE=$(grep "PROFILES_privacy=" scripts/ctrld/ctrld-switcher.sh | cut -d'"' -f2)

     # Update README.md with current profiles
     sed -i "s/PROFILES_gaming=\"[^\"]*\"/PROFILES_gaming=\"$GAMING_PROFILE\"/g" README.md
     sed -i "s/PROFILES_privacy=\"[^\"]*\"/PROFILES_privacy=\"$PRIVACY_PROFILE\"/g" README.md

     echo "✅ Documentation updated with latest profiles: Gaming=$GAMING_PROFILE, Privacy=$PRIVACY_PROFILE"

### Usage: Run ./scripts/update-docs.sh periodically to keep documentation up-to-date.

### Notes:
- This script is designed to update the documentation with the latest config values.
- It is a simple script that does not require any additional configuration.
- It is a good idea to run this script periodically to keep the documentation up-to-date.
- It is a good idea to run this script periodically to keep the documentation up-to-date.

### License:
- This script is licensed under the MIT License.
- This script is free to use and modify.
- This script is free to use and modify.

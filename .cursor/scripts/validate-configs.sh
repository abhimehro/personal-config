     #!/bin/bash
     # Validate key configurations for syntax and basic functionality

     echo "🔍 Validating SSH configuration..."
     if ssh -F configs/ssh/config-working -G /dev/null > /dev/null 2>&1; then
         echo "✅ SSH config syntax is valid."
     else
         echo "❌ SSH config has errors. Please fix before committing."
         exit 1
     fi

     echo "🔍 Checking DNS scripts..."
     if [ -x scripts/ctrld/ctrld-switcher.sh ]; then
         echo "✅ DNS switcher script is executable."
     else
         echo "❌ DNS switcher script missing execute permissions."
         exit 1
     fi

     echo "🔍 Validating Control D profiles..."
     # Quick check for required profile IDs in DNS scripts
     if grep -q "PROFILES_gaming=" scripts/ctrld/ctrld-switcher.sh && grep -q "PROFILES_privacy=" scripts/ctrld/ctrld-switcher.sh; then
         echo "✅ DNS profiles are defined."
     else
         echo "❌ DNS profiles missing in switcher script."
         exit 1
     fi

     echo "✅ All validations passed!"

### Usage: Run ./scripts/validate-configs.sh to validate the configs.

### Notes:
- This script is designed to validate the configs before allowing commits.
- It is a simple script that does not require any additional configuration.
- It is a good idea to run this script before each commit to ensure the configs are valid.
- It is a good idea to run this script before each commit to ensure the configs are valid.

### License:
- This script is licensed under the MIT License.
- This script is free to use and modify.
- This script is free to use and modify.

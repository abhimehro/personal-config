     #!/bin/bash
     # Basic security scan for configs

     echo "🔒 Running security checks..."

     # Check for common secrets patterns
     SECRETS_FOUND=$(git grep -I -nE '(api[_-]?key|token|password|secret)' -- 'configs/' 'scripts/' || true)
     if [ -n "$SECRETS_FOUND" ]; then
         echo "❌ Potential secrets found:"
         echo "$SECRETS_FOUND"
         exit 1
     fi

     # Check SSH config for weak settings
     if grep -q "StrictHostKeyChecking.*no" configs/ssh/config-working; then
         echo "⚠️ SSH config allows unknown hosts (consider review)."
     fi

     echo "✅ No critical security issues detected."

### Usage: Run ./scripts/security-check.sh periodically. For deeper scans, install git-secrets or OpenSCAP.

### Notes:
- This script is designed to check for common security issues in the configs.
- It is a simple script that does not require any additional configuration.
- It is a good idea to run this script periodically to ensure the configs are secure.
- It is a good idea to run this script periodically to ensure the configs are secure.

### License:
- This script is licensed under the MIT License.
- This script is free to use and modify.
- This script is free to use and modify.

#!/bin/bash

echo "DETAILED PR ANALYSIS"
echo "==================="
echo ""

echo "1. DUPLICATE PR DETECTION"
echo "========================="
echo ""
echo "PR #166 vs PR #168 (both 'UX: SSH install'):"
echo "PR #166 and #168 have the SAME TITLE and describe the same work"
echo ""

# Check if 166 and 168 are identical
diff_result=$(git diff pr-166 pr-168 | wc -l)
if [ "$diff_result" -lt 10 ]; then
    echo "Analysis: These PRs are DUPLICATES (likely from same Jules agent run)"
else
    echo "Analysis: These PRs have different implementations"
fi

echo ""
echo "2. KEY CONFLICT ANALYSIS"
echo "========================"
echo ""

# Check controld-manager changes - affected by most PRs
echo "controld-system/scripts/controld-manager:"
echo "  - Affected by: Many PRs (security AND perf optimization)"
echo "  - This is the main conflict point"
echo ""

# Check network-mode-manager - affected by most PRs
echo "scripts/network-mode-manager.sh:"
echo "  - Affected by: ALL PRs (19 PRs changing this file)"
echo "  - This is EXTREMELY problematic - clear merge conflict area"
echo ""

# Show which PRs touch this file
echo "  PRs changing this file:"
git diff --name-only main pr-166 | grep -q network-mode-manager.sh && echo "    #166"
git diff --name-only main pr-168 | grep -q network-mode-manager.sh && echo "    #168"
git diff --name-only main pr-169 | grep -q network-mode-manager.sh && echo "    #169"
git diff --name-only main pr-170 | grep -q network-mode-manager.sh && echo "    #170"
git diff --name-only main pr-171 | grep -q network-mode-manager.sh && echo "    #171"
git diff --name-only main pr-172 | grep -q network-mode-manager.sh && echo "    #172"
git diff --name-only main pr-173 | grep -q network-mode-manager.sh && echo "    #173"
git diff --name-only main pr-174 | grep -q network-mode-manager.sh && echo "    #174"
git diff --name-only main pr-175 | grep -q network-mode-manager.sh && echo "    #175"
git diff --name-only main pr-178 | grep -q network-mode-manager.sh && echo "    #178"
git diff --name-only main pr-181 | grep -q network-mode-manager.sh && echo "    #181"
git diff --name-only main pr-182 | grep -q network-mode-manager.sh && echo "    #182"
git diff --name-only main pr-185 | grep -q network-mode-manager.sh && echo "    #185"
git diff --name-only main pr-186 | grep -q network-mode-manager.sh && echo "    #186"
git diff --name-only main pr-188 | grep -q network-mode-manager.sh && echo "    #188"
git diff --name-only main pr-189 | grep -q network-mode-manager.sh && echo "    #189"
git diff --name-only main pr-192 | grep -q network-mode-manager.sh && echo "    #192"
git diff --name-only main pr-194 | grep -q network-mode-manager.sh && echo "    #194"
git diff --name-only main pr-195 | grep -q network-mode-manager.sh && echo "    #195"

echo ""
echo "3. ISOLATION ANALYSIS"
echo "====================="
echo ""
echo "Isolated PRs (only change their specific domain):"
git diff --name-only main pr-171 | grep -v '^\.' | grep -v '^docs' | grep -v '^README'

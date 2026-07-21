#!/usr/bin/env bash
# Unit tests for scripts/fix-recap-mdx-diff-strings.js (Lesson 0ej).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FIXER="$ROOT/scripts/fix-recap-mdx-diff-strings.js"
PASS=0
FAIL=0

check() {
  local name="$1"
  shift
  if "$@"; then
    echo "PASS: $name"
    PASS=$((PASS + 1))
  else
    echo "FAIL: $name"
    FAIL=$((FAIL + 1))
  fi
}

TEST_DIR=$(mktemp -d)
trap 'rm -rf "$TEST_DIR"' EXIT

# Case 1: broken Diff after: with shell [^[:space:]\\"] — must rewrite.
# NOTE: two backslashes before the quote (JS: \\ then " ends the string early).
cat >"$TEST_DIR/broken.mdx" <<'MDX'
<Diff
            language="yaml"
            mode="split"
            before: "safe before",
            after: "sed -E -e 's/[Bb]earer[[:space:]]+[^[:space:]\\"]+/Bearer [redacted]/g'",
            annotations: [
              {
MDX

node -e '
const { fixDiffQuotedProps, tryParseJsonStringBody } = require(process.argv[1]);
const fs = require("fs");
const raw = fs.readFileSync(process.argv[2], "utf8");
const afterLine = raw.split("\n").find((l) => /^\s*after:/.test(l));
if (!afterLine) process.exit(10);
const m = afterLine.match(/after:\s*"(.*)",\s*$/);
if (!m) process.exit(11);
if (tryParseJsonStringBody(m[1])) {
  console.error("expected invalid JSON string body");
  process.exit(2);
}
const { text, fixed } = fixDiffQuotedProps(raw);
if (fixed !== 1) {
  console.error("expected fixed=1, got", fixed);
  process.exit(3);
}
const fixedLine = text.split("\n").find((l) => /^\s*after:/.test(l));
const fixedTok = fixedLine.match(/after:\s*(.*),$/)[1];
JSON.parse(fixedTok); // rewritten value must be a valid JSON string token
fs.writeFileSync(process.argv[3], text);
' "$FIXER" "$TEST_DIR/broken.mdx" "$TEST_DIR/fixed.mdx"
check "rewrites broken Diff after prop" test -f "$TEST_DIR/fixed.mdx"

# Case 2: already-valid Diff line is left alone.
cat >"$TEST_DIR/ok.mdx" <<'MDX'
            after: "hello \"world\" and \\n newline",
MDX
node -e '
const { fixDiffQuotedProps } = require(process.argv[1]);
const fs = require("fs");
const raw = fs.readFileSync(process.argv[2], "utf8");
const { text, fixed } = fixDiffQuotedProps(raw);
if (fixed !== 0) process.exit(2);
if (text !== raw) process.exit(3);
' "$FIXER" "$TEST_DIR/ok.mdx"
check "leaves valid Diff props unchanged" true

# Case 3: recap-source.json plan.mdx path.
node -e '
const { fixRecapSourcePayload } = require(process.argv[1]);
const fs = require("fs");
const broken = fs.readFileSync(process.argv[2], "utf8");
const payload = { title: "t", brief: "", mdx: { "plan.mdx": broken, "canvas.mdx": "" } };
const { payload: next, fixed } = fixRecapSourcePayload(payload);
if (fixed !== 1) process.exit(2);
const body = next.mdx["plan.mdx"].split("\n").find((l) => l.includes("after:")).match(/after:\s*(.*),$/)[1];
JSON.parse(body);
' "$FIXER" "$TEST_DIR/broken.mdx"
check "fixes plan.mdx inside recap-source payload" true

# Case 4: CLI --write on the real failing artifact shape (if present).
if [[ -f /tmp/recap-fail-1733/recap-plan.mdx ]]; then
  cp /tmp/recap-fail-1733/recap-plan.mdx "$TEST_DIR/artifact.mdx"
  OUT=$(node "$FIXER" "$TEST_DIR/artifact.mdx" --write)
  check "artifact fixer reports fixed>=1" node -e 'const j=JSON.parse(process.argv[1]); process.exit(j.fixed>=1?0:1)' "$OUT"
  # Re-run: idempotent
  OUT2=$(node "$FIXER" "$TEST_DIR/artifact.mdx" --write)
  check "artifact fixer is idempotent" node -e 'const j=JSON.parse(process.argv[1]); process.exit(j.fixed===0?0:1)' "$OUT2"
fi

# Case 5: MDX compile gate when @mdx-js/mdx is available.
if [[ -d /tmp/recap-fail-1733/node_modules/@mdx-js/mdx ]]; then
  (
    cd /tmp/recap-fail-1733
    node <<'NODE'
    const fs = require("fs");
    const { fixDiffQuotedProps } = require("/workspace/scripts/fix-recap-mdx-diff-strings.js");
    (async () => {
      const { compile } = await import("@mdx-js/mdx");
      const raw = fs.readFileSync("recap-plan.mdx", "utf8");
      let rawFailed = false;
      try { await compile(raw); } catch { rawFailed = true; }
      if (!rawFailed) process.exit(2);
      const { text, fixed } = fixDiffQuotedProps(raw);
      if (fixed < 1) process.exit(3);
      await compile(text);
    })().catch((e) => { console.error(e); process.exit(1); });
NODE
  )
  check "artifact MDX compiles after fix" true
fi

echo ""
echo "Passed: $PASS  Failed: $FAIL"
if [[ "$FAIL" -gt 0 ]]; then exit 1; fi

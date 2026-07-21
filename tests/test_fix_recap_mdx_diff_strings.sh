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
    const { fixMdxContent } = require("/workspace/scripts/fix-recap-mdx-diff-strings.js");
    (async () => {
      const { compile } = await import("@mdx-js/mdx");
      const raw = fs.readFileSync("recap-plan.mdx", "utf8");
      let rawFailed = false;
      try { await compile(raw); } catch { rawFailed = true; }
      if (!rawFailed) process.exit(2);
      const { text, fixed } = fixMdxContent(raw);
      if (fixed < 1) process.exit(3);
      await compile(text);
    })().catch((e) => { console.error(e); process.exit(1); });
NODE
  )
  check "artifact MDX compiles after fix" true
fi

# Case 6: Callout mid-paragraph must be isolated onto its own lines.
cat >"$TEST_DIR/callout.mdx" <<'MDX'
Intro text <Callout kind="info">Heads up</Callout> trailing text
MDX
node -e '
const { fixMdxContent } = require(process.argv[1]);
const fs = require("fs");
const raw = fs.readFileSync(process.argv[2], "utf8");
const { text, fixed } = fixMdxContent(raw);
if (fixed < 1) process.exit(2);
if (!text.includes("\n\n<Callout") || !text.includes("</Callout>\n\n")) process.exit(3);
' "$FIXER" "$TEST_DIR/callout.mdx"
check "isolates Callout out of a paragraph" true

# Case 7: missing Callout closer is appended.
node -e '
const { balanceBlockTags } = require(process.argv[1]);
const { text, fixed } = balanceBlockTags("<Callout>hi\n");
if (fixed !== 1 || !text.includes("</Callout>")) process.exit(2);
' "$FIXER"
check "balances missing Callout closer" true

# Case 8: JSX after="..." with embedded \" must become after={...}.
cat >"$TEST_DIR/jsx-attr.mdx" <<'MDX'
<Diff
  summary="demo"
  before=""
  after="        # rejects Authorization via Headers.append (\"invalid header value\"), and
        # more"
  annotations={[]}
/>
MDX
node -e '
const { fixMdxContent } = require(process.argv[1]);
const fs = require("fs");
const raw = fs.readFileSync(process.argv[2], "utf8");
const { text, fixed, details } = fixMdxContent(raw);
if (details.jsxAttr < 1) { console.error(details); process.exit(2); }
if (!/after=\{/.test(text)) process.exit(3);
if (/after="/.test(text)) process.exit(4);
JSON.parse(text.match(/after=\{([\s\S]*?)\}/)[1]);
' "$FIXER" "$TEST_DIR/jsx-attr.mdx"
check "rewrites Diff JSX after= attrs to expressions" true

# Case 9: live artifact from run 29853720898 — JSX attrs + code={ multiline.
if [[ -f /tmp/vr-art/recap-plan.mdx ]]; then
  node -e '
const { fixMdxContent } = require(process.argv[1]);
const fs = require("fs");
const raw = fs.readFileSync("/tmp/vr-art/recap-plan.mdx", "utf8");
const { text, fixed, details } = fixMdxContent(raw);
if (fixed < 1 || details.jsxAttr < 1) { console.error(details); process.exit(2); }
const again = fixMdxContent(text);
if (again.fixed !== 0) { console.error("not idempotent", again.details); process.exit(3); }
fs.writeFileSync("/tmp/vr-art/recap-plan.fixed-final.mdx", text);
' "$FIXER"
  check "artifact JSX Diff/AnnotatedCode attrs rewrite" true
  if [[ -d /tmp/recap-fail-1733/node_modules/@mdx-js/mdx ]]; then
    node <<'NODE'
    const fs = require("fs");
    (async () => {
      const { compile } = await import("/tmp/recap-fail-1733/node_modules/@mdx-js/mdx/index.js");
      await compile(fs.readFileSync("/tmp/vr-art/recap-plan.fixed-final.mdx", "utf8"));
    })().catch((e) => { console.error(e.message); process.exit(1); });
NODE
    check "artifact MDX compiles after JSX attr fix" true
  fi
fi

# Case 10: bare columns=[…] must become columns={[…]}.
cat >"$TEST_DIR/bare-array.mdx" <<'MDX'
<Table
  columns=[{"key":"a","label":"A"},{"key":"b","label":"B"}]
  rows=[{"a":"1","b":"2"}]
/>
MDX
node -e '
const { fixBareArrayAttrs, fixMdxContent } = require(process.argv[1]);
const fs = require("fs");
const raw = fs.readFileSync(process.argv[2], "utf8");
const { text, fixed } = fixBareArrayAttrs(raw);
if (fixed !== 2) { console.error("expected 2 array fixes, got", fixed); process.exit(2); }
if (!/columns=\{\[/.test(text) || !/rows=\{\[/.test(text)) process.exit(3);
if (/columns=\[/.test(text) || /rows=\[/.test(text)) process.exit(4);
const again = fixBareArrayAttrs(text);
if (again.fixed !== 0) process.exit(5);
const full = fixMdxContent(raw);
if (full.details.arrayAttr !== 2) process.exit(6);
' "$FIXER" "$TEST_DIR/bare-array.mdx"
check "rewrites bare columns=/rows= array attrs" true

# Case 11: illegal commas between JSX attrs are stripped.
# NOTE: the pattern targets `…},` / `…],` / `…",` before the next attr line.
cat >"$TEST_DIR/attr-comma.mdx" <<'MDX'
<Table
  columns={[{"key":"a"}]},
  rows={[{"a":"1"}]}
/>
MDX
node -e '
const { fixJsxAttrTrailingCommas } = require(process.argv[1]);
const fs = require("fs");
const raw = fs.readFileSync(process.argv[2], "utf8");
const { text, fixed } = fixJsxAttrTrailingCommas(raw);
if (fixed !== 1) { console.error("expected 1 comma fix, got", fixed, text); process.exit(2); }
if (/}\s*,\s*\n/.test(text)) process.exit(3);
if (!/columns=\{\[{"key":"a"\}\]\}\s*\n\s*rows=/.test(text)) process.exit(4);
' "$FIXER" "$TEST_DIR/attr-comma.mdx"
check "strips illegal commas between JSX attrs" true

# Case 12: rows=[…]} (stray closing brace) only inserts opening `{`.
cat >"$TEST_DIR/half-brace.mdx" <<'MDX'
  rows=[{"a":1}]}
MDX
node -e '
const { fixBareArrayAttrs } = require(process.argv[1]);
const fs = require("fs");
const raw = fs.readFileSync(process.argv[2], "utf8");
const { text, fixed } = fixBareArrayAttrs(raw);
if (fixed !== 1) process.exit(2);
if (!/rows=\{\[{"a":1\}\]\}/.test(text)) { console.error(text); process.exit(3); }
if (/rows=\{\[.*\]\}\}/.test(text)) process.exit(4);
' "$FIXER" "$TEST_DIR/half-brace.mdx"
check "half-braced rows=[…]} only inserts opening brace" true

# Case 13: live artifact from run with bare array attrs (vr-art2).
if [[ -f /tmp/vr-art2/recap-plan.mdx ]]; then
  node -e '
const { fixMdxContent } = require(process.argv[1]);
const fs = require("fs");
const raw = fs.readFileSync("/tmp/vr-art2/recap-plan.mdx", "utf8");
const { text, fixed, details } = fixMdxContent(raw);
if (fixed < 1 || details.arrayAttr < 1) { console.error(details); process.exit(2); }
const again = fixMdxContent(text);
if (again.fixed !== 0) { console.error("not idempotent", again.details); process.exit(3); }
fs.writeFileSync("/tmp/vr-art2/recap-plan.fixed-arrays.mdx", text);
' "$FIXER"
  check "artifact bare array attrs rewrite" true
  if [[ -d /tmp/recap-fail-1733/node_modules/@mdx-js/mdx ]]; then
    node <<'NODE'
    const fs = require("fs");
    (async () => {
      const { compile } = await import("/tmp/recap-fail-1733/node_modules/@mdx-js/mdx/index.js");
      try {
        await compile(fs.readFileSync("/tmp/vr-art2/recap-plan.mdx", "utf8"));
        process.exit(2);
      } catch { /* expected raw fail */ }
      await compile(fs.readFileSync("/tmp/vr-art2/recap-plan.fixed-arrays.mdx", "utf8"));
    })().catch((e) => { console.error(e.message); process.exit(1); });
NODE
    check "artifact MDX compiles after array-attr fix" true
  fi
fi

echo ""
echo "Passed: $PASS  Failed: $FAIL"
if [[ "$FAIL" -gt 0 ]]; then exit 1; fi

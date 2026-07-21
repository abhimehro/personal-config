#!/usr/bin/env node
"use strict";

/**
 * Deterministic MDX hardeners for Plan visual-recap publish (Lesson 0ej).
 *
 * 1) Diff `before`/`after`/`code` props: shell `\\"` inside JS strings ends the
 *    string early → Plan 422 "Could not parse expression with acorn".
 * 2) Block JSX (Callout/Note/…) mid-paragraph: MDX requires blank lines around
 *    block elements → 422 "Expected the closing tag </Callout> either after…"
 * 3) Unbalanced Callout-like tags: append missing closers.
 * 4) JSX string attrs with embedded `"` → `{JSON.stringify(...)}`.
 * 5) Bare array attrs (`columns=[…]`) → `columns={[…]}`; strip illegal commas
 *    (delegated to ./lib/fix-recap-mdx-arrays.js).
 *
 * SECURITY: only rewrites text; does not execute MDX.
 * Trust boundary: agent-written MDX is untrusted input; we normalize structure.
 */

const path = require("path");
const {
  fixBareArrayAttrs,
  fixJsxAttrTrailingCommas,
} = require(path.join(__dirname, "lib", "fix-recap-mdx-arrays.js"));

/** @type {readonly string[]} */
const BLOCK_TAGS = Object.freeze([
  "Callout",
  "Note",
  "Warning",
  "Tip",
  "Info",
  "Steps",
  "Step",
]);

/** @type {Readonly<Record<string, string>>} */
const SIMPLE_ESCAPES = Object.freeze({
  n: "\n",
  r: "\r",
  t: "\t",
  '"': '"',
  "\\": "\\",
  "/": "/",
});

/** Attr terminator for Diff/AnnotatedCode string values (exactly two spaces). */
const JSX_ATTR_TERM_RE =
  /\n  (?:before|after|code|summary|language|mode|annotations|filename|id)\s*=|\n\/>|\n<\/(?:Diff|AnnotatedCode)>/;

/** @returns {Record<string, number>} */
function emptyFixDetails() {
  return {
    diff: 0,
    jsxAttr: 0,
    arrayAttr: 0,
    attrComma: 0,
    isolate: 0,
    balance: 0,
  };
}

/**
 * @param {Record<string, number>} target
 * @param {Record<string, number>} source
 * @returns {void}
 */
function addFixDetails(target, source) {
  target.diff += source.diff;
  target.jsxAttr += source.jsxAttr;
  target.arrayAttr += source.arrayAttr;
  target.attrComma += source.attrComma;
  target.isolate += source.isolate;
  target.balance += source.balance;
}

/**
 * @param {Record<string, number>} details
 * @returns {number}
 */
function sumFixDetails(details) {
  return (
    details.diff +
    details.jsxAttr +
    details.arrayAttr +
    details.attrComma +
    details.isolate +
    details.balance
  );
}

/**
 * @param {unknown} value
 * @returns {value is Record<string, unknown>}
 */
function isPlainObject(value) {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

/**
 * @param {string} body
 * @returns {boolean}
 */
function tryParseJsonStringBody(body) {
  try {
    JSON.parse(`"${body}"`);
    return true;
  } catch {
    return false;
  }
}

/**
 * Decode `\uXXXX` at `body[i]` where `body[i]` is already known to be `u`.
 *
 * @param {string} body
 * @param {number} i index of the `u` after a backslash
 * @returns {{ char: string, advance: number }}
 */
function decodeUnicodeEscape(body, i) {
  const hex = body.slice(i + 1, i + 5);
  if (!/^[0-9a-fA-F]{4}$/.test(hex)) {
    return { char: "u", advance: 0 };
  }
  return {
    char: String.fromCharCode(Number.parseInt(hex, 16)),
    advance: 4,
  };
}

/**
 * Unescape a mostly-JSON string body without failing on shell-ish sequences.
 * Unknown escapes keep both characters (e.g. `\s` stays `\s`).
 *
 * @param {string} body
 * @returns {string}
 */
function lenientUnescape(body) {
  let out = "";
  for (let i = 0; i < body.length; i += 1) {
    if (body[i] !== "\\" || i + 1 >= body.length) {
      out += body[i];
      continue;
    }
    const next = body[i + 1];
    i += 1;
    if (Object.prototype.hasOwnProperty.call(SIMPLE_ESCAPES, next)) {
      out += SIMPLE_ESCAPES[next];
      continue;
    }
    if (next === "u") {
      const decoded = decodeUnicodeEscape(body, i);
      out += decoded.char;
      i += decoded.advance;
      continue;
    }
    out += `\\${next}`;
  }
  return out;
}

/**
 * Rewrite Diff `before`/`after`/`code` quoted props via JSON.stringify when the
 * existing body is not a valid JSON string payload.
 *
 * @param {string} mdx
 * @returns {{ text: string, fixed: number }}
 */
function fixDiffQuotedProps(mdx) {
  const re = /^(\s*)(before|after|code):\s*"(.*)",\s*$/;
  let fixed = 0;
  const lines = mdx.split("\n");
  const out = lines.map((line) => {
    const match = line.match(re);
    if (!match) return line;
    const [, indent, key, body] = match;
    if (tryParseJsonStringBody(body)) return line;
    fixed += 1;
    return `${indent}${key}: ${JSON.stringify(lenientUnescape(body))},`;
  });
  return { text: out.join("\n"), fixed };
}

/**
 * Ensure common Plan block JSX tags are not stuck inside a markdown paragraph.
 * Skips JSX attribute lines and heavily-indented code-sample lines so we do
 * not corrupt Diff/AnnotatedCode string payloads.
 *
 * @param {string} mdx
 * @returns {{ text: string, fixed: number }}
 */
function isolateBlockElements(mdx) {
  let fixed = 0;
  const out = mdx.split("\n").map((line) => {
    if (
      /^\s*(?:before|after|code|summary|language|mode|annotations|filename|id)\s*=/.test(
        line,
      ) ||
      /^\s{4,}/.test(line)
    ) {
      return line;
    }
    let next = line;
    for (const tag of BLOCK_TAGS) {
      const openRe = new RegExp(`([^\\n])(<${tag}\\b[^>]*>)`, "g");
      next = next.replace(openRe, (_, prev, open) => {
        fixed += 1;
        return `${prev}\n\n${open}`;
      });
      const closeRe = new RegExp(`(<\\/${tag}>)([^\\n])`, "g");
      next = next.replace(closeRe, (_, close, nextChar) => {
        fixed += 1;
        return `${close}\n\n${nextChar}`;
      });
    }
    return next;
  });
  return { text: out.join("\n"), fixed };
}

/**
 * Append missing closers for unbalanced Callout-like tags at prose indent only
 * (open > close). Ignores tags buried in code samples / attr payloads.
 *
 * @param {string} mdx
 * @returns {{ text: string, fixed: number }}
 */
function balanceBlockTags(mdx) {
  let text = mdx;
  let fixed = 0;
  for (const tag of BLOCK_TAGS) {
    const open = (text.match(new RegExp(`^\\s{0,2}<${tag}\\b[^>]*>`, "gm")) || [])
      .length;
    const close = (text.match(new RegExp(`^\\s{0,2}</${tag}>`, "gm")) || []).length;
    if (open > close) {
      const missing = open - close;
      text = `${text}\n${`</${tag}>`.repeat(missing)}\n`;
      fixed += missing;
    }
  }
  return { text, fixed };
}

/**
 * @param {string} rest
 * @returns {{ rawValue: string, consumed: number } | null}
 */
function findQuotedAttrEndOnLine(rest) {
  const eol = rest.search(/\n/);
  const line = eol >= 0 ? rest.slice(0, eol) : rest;
  const endQuote = line.indexOf('"');
  if (endQuote < 0) return null;
  const rawValue = line.slice(0, endQuote);
  if (rawValue === "" || tryParseJsonStringBody(rawValue)) return null;
  return { rawValue, consumed: endQuote + 1 };
}

/**
 * Locate the end of a JSX string attr value starting at `rest`.
 *
 * @param {string} rest
 * @param {"quote" | "expr"} kind
 * @returns {{ rawValue: string, consumed: number } | null}
 */
function findJsxStringAttrEnd(rest, kind) {
  if (kind === "expr") {
    const firstNl = rest.indexOf("\n");
    const firstLine = firstNl < 0 ? rest : rest.slice(0, firstNl);
    // Already a single-line JS string expression (including prior rewrites).
    if (firstLine.includes('"}')) return null;
  }

  const term = rest.search(JSX_ATTR_TERM_RE);
  if (term >= 0) {
    return { rawValue: rest.slice(0, term), consumed: term };
  }
  if (kind !== "quote") return null;
  return findQuotedAttrEndOnLine(rest);
}

/**
 * Strip trailing quote / `"}` leftovers from a captured attr body.
 *
 * @param {string} rawValue
 * @param {"quote" | "expr"} kind
 * @returns {string}
 */
function trimJsxStringAttrBody(rawValue, kind) {
  if (kind === "expr") {
    return rawValue.replace(/"\}\s*$/, "").replace(/"\s*$/, "");
  }
  if (rawValue.endsWith('"')) return rawValue.slice(0, -1);
  return rawValue;
}

/**
 * Rewrite one Diff/AnnotatedCode string attr occurrence.
 *
 * @param {string} body
 * @param {string} key
 * @param {"quote" | "expr"} kind
 * @returns {{ body: string, fixed: number }}
 */
function rewriteOneJsxStringAttr(body, key, kind) {
  const startRe =
    kind === "quote"
      ? new RegExp(`(\\s)(${key})="`, "g")
      : new RegExp(`(\\s)(${key})=\\{"`, "g");
  let match;
  while ((match = startRe.exec(body))) {
    const valueStart = match.index + match[0].length;
    const found = findJsxStringAttrEnd(body.slice(valueStart), kind);
    if (!found) continue;
    const content = lenientUnescape(
      trimJsxStringAttrBody(found.rawValue, kind).replace(/\r\n/g, "\n"),
    );
    const expr = `${match[1]}${key}={${JSON.stringify(content)}}`;
    const next =
      body.slice(0, match.index) + expr + body.slice(valueStart + found.consumed);
    return { body: next, fixed: 1 };
  }
  return { body, fixed: 0 };
}

/**
 * Rewrite Diff/AnnotatedCode string props to `key={JSON.stringify(...)}` form.
 *
 * @param {string} mdx
 * @returns {{ text: string, fixed: number }}
 */
function fixDiffJsxStringAttrs(mdx) {
  const keys = ["before", "after", "code", "summary"];
  let text = mdx;
  let fixed = 0;

  for (let pass = 0; pass < 64; pass += 1) {
    let passFixed = 0;
    for (const key of keys) {
      for (const kind of /** @type {const} */ (["quote", "expr"])) {
        const result = rewriteOneJsxStringAttr(text, key, kind);
        text = result.body;
        passFixed += result.fixed;
      }
    }
    if (passFixed === 0) break;
    fixed += passFixed;
  }
  return { text, fixed };
}

/**
 * Apply all deterministic MDX hardeners.
 *
 * @param {string} mdx
 * @returns {{ text: string, fixed: number, details: Record<string, number> }}
 */
function fixMdxContent(mdx) {
  const details = emptyFixDetails();
  let text = mdx;
  // Prose Callout isolation first (skip attr / deeply-indented lines).
  // NOTE: do not auto-balance tags — code samples often contain Callout markup
  // that is not real MDX structure (Lesson 0ej follow-on).
  const isolated = isolateBlockElements(text);
  text = isolated.text;
  details.isolate = isolated.fixed;
  const arrays = fixBareArrayAttrs(text);
  text = arrays.text;
  details.arrayAttr = arrays.fixed;
  const commas = fixJsxAttrTrailingCommas(text);
  text = commas.text;
  details.attrComma = commas.fixed;
  const diff = fixDiffQuotedProps(text);
  text = diff.text;
  details.diff = diff.fixed;
  // JSX string attr rewrite last so JSON.stringify payloads stay opaque.
  const jsx = fixDiffJsxStringAttrs(text);
  text = jsx.text;
  details.jsxAttr = jsx.fixed;
  return { text, fixed: sumFixDetails(details), details };
}

/**
 * @param {Record<string, unknown>} mdx
 * @returns {{ nextMdx: Record<string, unknown>, fixed: number, details: Record<string, number> }}
 */
function fixMdxMapEntries(mdx) {
  const details = emptyFixDetails();
  let fixed = 0;
  const nextMdx = { ...mdx };
  for (const key of Object.keys(nextMdx)) {
    if (!key.endsWith(".mdx") || typeof nextMdx[key] !== "string") continue;
    const result = fixMdxContent(nextMdx[key]);
    if (result.fixed === 0) continue;
    nextMdx[key] = result.text;
    fixed += result.fixed;
    addFixDetails(details, result.details);
  }
  return { nextMdx, fixed, details };
}

/**
 * Fix MDX files inside a recap-source.json payload.
 *
 * @param {unknown} payload
 * @returns {{ payload: unknown, fixed: number, details: Record<string, number> }}
 */
function fixRecapSourcePayload(payload) {
  const emptyDetails = emptyFixDetails();
  if (!isPlainObject(payload)) {
    return { payload, fixed: 0, details: emptyDetails };
  }
  const mdx = payload.mdx;
  if (!isPlainObject(mdx)) {
    return { payload, fixed: 0, details: emptyDetails };
  }
  const { nextMdx, fixed, details } = fixMdxMapEntries(mdx);
  if (fixed === 0) return { payload, fixed: 0, details };
  return { payload: { ...payload, mdx: nextMdx }, fixed, details };
}

module.exports = {
  BLOCK_TAGS,
  tryParseJsonStringBody,
  lenientUnescape,
  fixDiffQuotedProps,
  fixDiffJsxStringAttrs,
  fixBareArrayAttrs,
  fixJsxAttrTrailingCommas,
  isolateBlockElements,
  balanceBlockTags,
  fixMdxContent,
  fixRecapSourcePayload,
};

function main(argv) {
  const fs = require("fs");
  const target = argv[2];
  if (!target) {
    process.stderr.write(
      "usage: fix-recap-mdx-diff-strings.js <file.mdx|recap-source.json> [--write]\n",
    );
    process.exit(2);
  }
  const write = argv.includes("--write");
  const raw = fs.readFileSync(target, "utf8");
  if (target.endsWith(".json")) {
    const parsed = JSON.parse(raw);
    const { payload, fixed, details } = fixRecapSourcePayload(parsed);
    const text = `${JSON.stringify(payload, null, 2)}\n`;
    if (write && fixed > 0) fs.writeFileSync(target, text);
    process.stdout.write(JSON.stringify({ ok: true, fixed, details, target }) + "\n");
    return;
  }
  const { text, fixed, details } = fixMdxContent(raw);
  if (write && fixed > 0) fs.writeFileSync(target, text);
  process.stdout.write(JSON.stringify({ ok: true, fixed, details, target }) + "\n");
}

if (require.main === module) {
  main(process.argv);
}

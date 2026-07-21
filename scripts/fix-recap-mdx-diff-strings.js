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
 *
 * SECURITY: only rewrites text; does not execute MDX.
 * Trust boundary: agent-written MDX is untrusted input; we normalize structure.
 */

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
 * Unescape a mostly-JSON string body without failing on shell-ish sequences.
 * Unknown escapes keep both characters (e.g. `\s` stays `\s`).
 *
 * @param {string} body
 * @returns {string}
 */
function lenientUnescape(body) {
  let out = "";
  for (let i = 0; i < body.length; i += 1) {
    const ch = body[i];
    if (ch !== "\\" || i + 1 >= body.length) {
      out += ch;
      continue;
    }
    const next = body[i + 1];
    i += 1;
    switch (next) {
      case "n":
        out += "\n";
        break;
      case "r":
        out += "\r";
        break;
      case "t":
        out += "\t";
        break;
      case '"':
        out += '"';
        break;
      case "\\":
        out += "\\";
        break;
      case "/":
        out += "/";
        break;
      case "u": {
        const hex = body.slice(i + 1, i + 5);
        if (/^[0-9a-fA-F]{4}$/.test(hex)) {
          out += String.fromCharCode(Number.parseInt(hex, 16));
          i += 4;
        } else {
          out += "u";
        }
        break;
      }
      default:
        out += `\\${next}`;
        break;
    }
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
 *
 * @param {string} mdx
 * @returns {{ text: string, fixed: number }}
 */
function isolateBlockElements(mdx) {
  let text = mdx;
  let fixed = 0;
  for (const tag of BLOCK_TAGS) {
    const openRe = new RegExp(`([^\\n])(<${tag}\\b[^>]*>)`, "g");
    text = text.replace(openRe, (_, prev, open) => {
      fixed += 1;
      return `${prev}\n\n${open}`;
    });
    const closeRe = new RegExp(`(<\\/${tag}>)([^\\n])`, "g");
    text = text.replace(closeRe, (_, close, next) => {
      fixed += 1;
      return `${close}\n\n${next}`;
    });
  }
  return { text, fixed };
}

/**
 * Append missing closers for unbalanced Callout-like tags (open > close).
 *
 * @param {string} mdx
 * @returns {{ text: string, fixed: number }}
 */
function balanceBlockTags(mdx) {
  let text = mdx;
  let fixed = 0;
  for (const tag of BLOCK_TAGS) {
    const open = (text.match(new RegExp(`<${tag}\\b[^>]*>`, "g")) || []).length;
    const close = (text.match(new RegExp(`</${tag}>`, "g")) || []).length;
    if (open > close) {
      const missing = open - close;
      text = `${text}\n${`</${tag}>`.repeat(missing)}\n`;
      fixed += missing;
    }
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
  const details = { diff: 0, isolate: 0, balance: 0 };
  let text = mdx;
  const diff = fixDiffQuotedProps(text);
  text = diff.text;
  details.diff = diff.fixed;
  const isolated = isolateBlockElements(text);
  text = isolated.text;
  details.isolate = isolated.fixed;
  const balanced = balanceBlockTags(text);
  text = balanced.text;
  details.balance = balanced.fixed;
  const fixed = details.diff + details.isolate + details.balance;
  return { text, fixed, details };
}

/**
 * Fix MDX files inside a recap-source.json payload.
 *
 * @param {unknown} payload
 * @returns {{ payload: unknown, fixed: number, details: Record<string, number> }}
 */
function fixRecapSourcePayload(payload) {
  const emptyDetails = { diff: 0, isolate: 0, balance: 0 };
  if (!payload || typeof payload !== "object" || Array.isArray(payload)) {
    return { payload, fixed: 0, details: emptyDetails };
  }
  const mdx = /** @type {Record<string, unknown>} */ (payload).mdx;
  if (!mdx || typeof mdx !== "object" || Array.isArray(mdx)) {
    return { payload, fixed: 0, details: emptyDetails };
  }
  const details = { diff: 0, isolate: 0, balance: 0 };
  let fixed = 0;
  const nextMdx = { ...mdx };
  for (const key of Object.keys(nextMdx)) {
    if (!key.endsWith(".mdx") || typeof nextMdx[key] !== "string") continue;
    const result = fixMdxContent(nextMdx[key]);
    if (result.fixed > 0) {
      nextMdx[key] = result.text;
      fixed += result.fixed;
      details.diff += result.details.diff;
      details.isolate += result.details.isolate;
      details.balance += result.details.balance;
    }
  }
  if (fixed === 0) return { payload, fixed: 0, details };
  return { payload: { ...payload, mdx: nextMdx }, fixed, details };
}

module.exports = {
  BLOCK_TAGS,
  tryParseJsonStringBody,
  lenientUnescape,
  fixDiffQuotedProps,
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

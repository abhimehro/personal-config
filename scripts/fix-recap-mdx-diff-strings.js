#!/usr/bin/env node
"use strict";

/**
 * Deterministic fixer for Plan Diff block props that break MDX/acorn.
 *
 * Agent-authored Diff `before`/`after`/`code` lines often embed shell regex like
 * [^[:space:]\"] inside a JS double-quoted string. In JS, \\" ends the string
 * early → Plan publish 422 "Could not parse expression with acorn".
 *
 * SECURITY: only rewrites matched Diff prop lines; does not execute MDX.
 * Trust boundary: agent-written MDX is untrusted input; we normalize escaping.
 */

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
 * Fix Diff props inside a recap-source.json payload's mdx map (in place shape).
 *
 * @param {unknown} payload
 * @returns {{ payload: unknown, fixed: number }}
 */
function fixRecapSourcePayload(payload) {
  if (!payload || typeof payload !== "object" || Array.isArray(payload)) {
    return { payload, fixed: 0 };
  }
  const mdx = /** @type {Record<string, unknown>} */ (payload).mdx;
  if (!mdx || typeof mdx !== "object" || Array.isArray(mdx)) {
    return { payload, fixed: 0 };
  }
  let fixed = 0;
  const nextMdx = { ...mdx };
  for (const key of Object.keys(nextMdx)) {
    if (!key.endsWith(".mdx") || typeof nextMdx[key] !== "string") continue;
    const result = fixDiffQuotedProps(nextMdx[key]);
    if (result.fixed > 0) {
      nextMdx[key] = result.text;
      fixed += result.fixed;
    }
  }
  if (fixed === 0) return { payload, fixed: 0 };
  return { payload: { ...payload, mdx: nextMdx }, fixed };
}

module.exports = {
  tryParseJsonStringBody,
  lenientUnescape,
  fixDiffQuotedProps,
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
    const { payload, fixed } = fixRecapSourcePayload(parsed);
    const text = `${JSON.stringify(payload, null, 2)}\n`;
    if (write && fixed > 0) fs.writeFileSync(target, text);
    process.stdout.write(JSON.stringify({ ok: true, fixed, target }) + "\n");
    return;
  }
  const { text, fixed } = fixDiffQuotedProps(raw);
  if (write && fixed > 0) fs.writeFileSync(target, text);
  process.stdout.write(JSON.stringify({ ok: true, fixed, target }) + "\n");
}

if (require.main === module) {
  main(process.argv);
}

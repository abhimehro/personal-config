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
 * Rewrite Diff/AnnotatedCode string props to `key={JSON.stringify(...)}` form.
 *
 * Handles both:
 * - `after="…"` (JSX/HTML attr — embedded `"` ends the value early)
 * - `code={"…` multi-line (invalid JS string — raw newlines)
 *
 * @param {string} mdx
 * @returns {{ text: string, fixed: number }}
 */
function fixDiffJsxStringAttrs(mdx) {
  const keys = ["before", "after", "code", "summary"];
  // ASSUMES: Diff/AnnotatedCode props are indented with exactly two spaces.
  // Deeper indent (embedded examples) must NOT terminate the value early.
  const termRe =
    /\n  (?:before|after|code|summary|language|mode|annotations|filename|id)\s*=|\n\/>|\n<\/(?:Diff|AnnotatedCode)>/;
  let text = mdx;
  let fixed = 0;

  /**
   * @param {string} body
   * @param {string} key
   * @param {"quote" | "expr"} kind
   * @returns {{ body: string, fixed: number }}
   */
  const rewriteOne = (body, key, kind) => {
    const startRe =
      kind === "quote"
        ? new RegExp(`(\\s)(${key})="`, "g")
        : new RegExp(`(\\s)(${key})=\\{"`, "g");
    let match;
    while ((match = startRe.exec(body))) {
      const valueStart = match.index + match[0].length;
      const rest = body.slice(valueStart);

      if (kind === "expr") {
        const firstNl = rest.indexOf("\n");
        const firstLine = firstNl < 0 ? rest : rest.slice(0, firstNl);
        // Already a single-line JS string expression (including prior rewrites).
        if (firstLine.includes('"}')) {
          continue;
        }
      }

      const term = rest.search(termRe);
      let rawValue;
      let consumed;
      if (term >= 0) {
        rawValue = rest.slice(0, term);
        consumed = term;
      } else {
        const eol = rest.search(/\n/);
        const line = eol >= 0 ? rest.slice(0, eol) : rest;
        if (kind === "quote") {
          const endQuote = line.indexOf('"');
          if (endQuote < 0) continue;
          rawValue = line.slice(0, endQuote);
          consumed = endQuote + 1;
          if (rawValue === "") continue;
          if (tryParseJsonStringBody(rawValue)) continue;
        } else {
          continue;
        }
      }
      if (kind === "expr") {
        rawValue = rawValue.replace(/"\}\s*$/, "").replace(/"\s*$/, "");
      } else if (rawValue.endsWith('"')) {
        rawValue = rawValue.slice(0, -1);
      }
      const content = lenientUnescape(rawValue.replace(/\r\n/g, "\n"));
      const expr = `${match[1]}${key}={${JSON.stringify(content)}}`;
      const next = body.slice(0, match.index) + expr + body.slice(valueStart + consumed);
      return { body: next, fixed: 1 };
    }
    return { body, fixed: 0 };
  };

  for (let pass = 0; pass < 64; pass += 1) {
    let passFixed = 0;
    for (const key of keys) {
      for (const kind of /** @type {const} */ (["quote", "expr"])) {
        const result = rewriteOne(text, key, kind);
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
 * Rewrite bare JSX array attrs (`columns=[…]`) to expression form (`columns={[…]}`).
 *
 * @param {string} mdx
 * @returns {{ text: string, fixed: number }}
 */
function fixBareArrayAttrs(mdx) {
  const keys = "columns|rows|annotations|items|data|options|tabs";
  let text = mdx;
  let fixed = 0;
  for (let n = 0; n < 64; n += 1) {
    const match = new RegExp(`(\\s)(${keys})=\\[`).exec(text);
    if (!match) break;
    const openIdx = match.index + match[0].length - 1; // index of '['
    let i = openIdx + 1;
    let depth = 1;
    let inStr = /** @type {string | null} */ (null);
    let escape = false;
    for (; i < text.length && depth > 0; i += 1) {
      const ch = text[i];
      if (inStr) {
        if (escape) {
          escape = false;
          continue;
        }
        if (ch === "\\") {
          escape = true;
          continue;
        }
        if (ch === inStr) inStr = null;
        continue;
      }
      if (ch === '"' || ch === "'" || ch === "`") {
        inStr = ch;
        continue;
      }
      if (ch === "[") depth += 1;
      else if (ch === "]") depth -= 1;
    }
    if (depth !== 0) break;
    let replacement;
    if (text[i] === "}") {
      // Already has a closing brace (`rows=[…]}`) — only insert `{` after `=`.
      replacement = `${match[1]}${match[2]}={${text.slice(openIdx, i)}`;
      text = text.slice(0, match.index) + replacement + text.slice(i);
    } else {
      replacement = `${match[1]}${match[2]}={${text.slice(openIdx, i)}}`;
      text = text.slice(0, match.index) + replacement + text.slice(i);
    }
    fixed += 1;
  }
  return { text, fixed };
}

/**
 * Remove illegal commas between JSX attributes (`columns={…},` → `columns={…}`).
 *
 * @param {string} mdx
 * @returns {{ text: string, fixed: number }}
 */
function fixJsxAttrTrailingCommas(mdx) {
  let fixed = 0;
  const text = mdx.replace(/(["}\]])(,)(\s*\n\s*[A-Za-z_][\w-]*=)/g, (_, end, _comma, next) => {
    fixed += 1;
    return `${end}${next}`;
  });
  return { text, fixed };
}

/**
 * Apply all deterministic MDX hardeners.
 *
 * @param {string} mdx
 * @returns {{ text: string, fixed: number, details: Record<string, number> }}
 */
function fixMdxContent(mdx) {
  const details = {
    diff: 0,
    jsxAttr: 0,
    arrayAttr: 0,
    attrComma: 0,
    isolate: 0,
    balance: 0,
  };
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
  const fixed =
    details.diff +
    details.jsxAttr +
    details.arrayAttr +
    details.attrComma +
    details.isolate +
    details.balance;
  return { text, fixed, details };
}

/**
 * Fix MDX files inside a recap-source.json payload.
 *
 * @param {unknown} payload
 * @returns {{ payload: unknown, fixed: number, details: Record<string, number> }}
 */
function fixRecapSourcePayload(payload) {
  const emptyDetails = {
    diff: 0,
    jsxAttr: 0,
    arrayAttr: 0,
    attrComma: 0,
    isolate: 0,
    balance: 0,
  };
  if (!payload || typeof payload !== "object" || Array.isArray(payload)) {
    return { payload, fixed: 0, details: emptyDetails };
  }
  const mdx = /** @type {Record<string, unknown>} */ (payload).mdx;
  if (!mdx || typeof mdx !== "object" || Array.isArray(mdx)) {
    return { payload, fixed: 0, details: emptyDetails };
  }
  const details = {
    diff: 0,
    jsxAttr: 0,
    arrayAttr: 0,
    attrComma: 0,
    isolate: 0,
    balance: 0,
  };
  let fixed = 0;
  const nextMdx = { ...mdx };
  for (const key of Object.keys(nextMdx)) {
    if (!key.endsWith(".mdx") || typeof nextMdx[key] !== "string") continue;
    const result = fixMdxContent(nextMdx[key]);
    if (result.fixed > 0) {
      nextMdx[key] = result.text;
      fixed += result.fixed;
      details.diff += result.details.diff;
      details.jsxAttr += result.details.jsxAttr;
      details.arrayAttr += result.details.arrayAttr;
      details.attrComma += result.details.attrComma;
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

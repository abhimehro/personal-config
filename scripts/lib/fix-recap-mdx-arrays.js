"use strict";

/**
 * Bare JSX array-attr hardeners for Plan MDX (Lesson 0ej).
 * Split from fix-recap-mdx-diff-strings.js to keep per-module complexity low.
 */

/**
 * @param {string | null} quote
 * @param {boolean} escape
 * @param {string} ch
 * @returns {{ quote: string | null, escape: boolean }}
 */
function stepQuotedChar(quote, escape, ch) {
  if (escape) return { quote, escape: false };
  if (ch === "\\") return { quote, escape: true };
  if (ch === quote) return { quote: null, escape: false };
  return { quote, escape: false };
}

/**
 * @param {string} ch
 * @param {number} depth
 * @returns {number}
 */
function adjustArrayDepth(ch, depth) {
  if (ch === "[") return depth + 1;
  if (ch === "]") return depth - 1;
  return depth;
}

/**
 * Advance past a JSON-ish array starting at `openIdx` (index of `[`).
 *
 * @param {string} text
 * @param {number} openIdx
 * @returns {number} index just past the matching `]`, or -1 if unbalanced
 */
function findMatchingArrayEnd(text, openIdx) {
  let i = openIdx + 1;
  let depth = 1;
  let quote = /** @type {string | null} */ (null);
  let escape = false;
  while (i < text.length && depth > 0) {
    const ch = text[i];
    i += 1;
    if (quote) {
      ({ quote, escape } = stepQuotedChar(quote, escape, ch));
      continue;
    }
    if (ch === '"' || ch === "'" || ch === "`") {
      quote = ch;
      continue;
    }
    depth = adjustArrayDepth(ch, depth);
  }
  return depth === 0 ? i : -1;
}

/**
 * Build `key={[…]}` replacement; for `rows=[…]}` only insert the opening `{`.
 *
 * @param {{ prefix: string, key: string, arraySlice: string, alreadyClosed: boolean }} parts
 * @returns {string}
 */
function bareArrayReplacement(parts) {
  const { prefix, key, arraySlice, alreadyClosed } = parts;
  if (alreadyClosed) return `${prefix}${key}={${arraySlice}`;
  return `${prefix}${key}={${arraySlice}}`;
}

/**
 * Apply one bare-array rewrite at the first `key=[` match.
 *
 * @param {string} text
 * @param {string} keys
 * @returns {{ text: string, fixed: number } | null}
 */
function rewriteOneBareArray(text, keys) {
  const match = new RegExp(`(\\s)(${keys})=\\[`).exec(text);
  if (!match) return null;
  const openIdx = match.index + match[0].length - 1;
  const endIdx = findMatchingArrayEnd(text, openIdx);
  if (endIdx < 0) return null;
  const replacement = bareArrayReplacement({
    prefix: match[1],
    key: match[2],
    arraySlice: text.slice(openIdx, endIdx),
    alreadyClosed: text[endIdx] === "}",
  });
  return {
    text: text.slice(0, match.index) + replacement + text.slice(endIdx),
    fixed: 1,
  };
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
    const result = rewriteOneBareArray(text, keys);
    if (!result) break;
    text = result.text;
    fixed += result.fixed;
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

module.exports = {
  findMatchingArrayEnd,
  bareArrayReplacement,
  fixBareArrayAttrs,
  fixJsxAttrTrailingCommas,
};

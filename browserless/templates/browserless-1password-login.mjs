#!/usr/bin/env node
// browserless-1password-login.mjs — Playwright over CDP on Browserless, with
// 1Password secret fills resolved server-side by Browserless.
//
// Usage:
//   BROWSERLESS_API_KEY=$(op read "op://Personal/fbbrvhjsd3x7vetbz544uyvjoe/credential") \
//   BROWSERLESS_INTEGRATION_ID=op_int_xxx \
//   node browserless-1password-login.mjs <login-url> <username-selector> <password-selector> <submit-selector> <op-username-ref> <op-password-ref>
//
// SECURITY: The script never sees secret values. It sends only op:// refs and
// target selectors; Browserless resolves and types the values server-side.
// After the first loadSecret, capture channels (screenshots, PDFs, page
// reads) are disabled for the session — take any captures BEFORE filling.

import { chromium } from "playwright-core";

const [
  loginUrl,
  usernameSelector,
  passwordSelector,
  submitSelector,
  opUsernameRef,
  opPasswordRef,
] = process.argv.slice(2);

const TOKEN = process.env.BROWSERLESS_API_KEY;
const INTEGRATION_ID = process.env.BROWSERLESS_INTEGRATION_ID;
const ENDPOINT = process.env.BROWSERLESS_ENDPOINT ?? "production-sfo.browserless.io";

if (!TOKEN || !INTEGRATION_ID) {
  console.error(
    "Usage: BROWSERLESS_API_KEY=... BROWSERLESS_INTEGRATION_ID=op_int_... node browserless-1password-login.mjs " +
      "<login-url> <username-selector> <password-selector> <submit-selector> <op-username-ref> <op-password-ref>"
  );
  process.exit(1);
}

if (!loginUrl || !opUsernameRef || !opPasswordRef) {
  combineUsage();
}

function combineUsage() {
  console.error("Missing required positional args (login-url, selectors, op refs).");
  process.exit(1);
}

const browser = await chromium.connectOverCDP(
  `wss://${ENDPOINT}/chromium?token=${TOKEN}&integrationId=${INTEGRATION_ID}`
);

try {
  const page = browser.contexts()[0].pages()[0] ?? (await browser.contexts()[0].newPage());
  await page.goto(loginUrl);

  const cdp = await page.context().newCDPSession(page);

  // Resolve op://Vault/Item/field refs from 1Password server-side and type
  // them into the target fields. The values never cross back to this client.
  await cdp.send("Browserless.loadSecret", {
    ref: opUsernameRef,
    targetSelector: usernameSelector,
  });
  await cdp.send("Browserless.loadSecret", {
    ref: opPasswordRef,
    targetSelector: passwordSelector,
  });

  await page.click(submitSelector);
  await page.waitForLoadState("networkidle");
  console.log("Login submitted. Session is now locked down (no captures).");
} finally {
  await browser.close();
}

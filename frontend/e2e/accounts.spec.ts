import { createHmac } from "node:crypto";
import { expect, test, type Page } from "@playwright/test";
import en from "../messages/en.json";

const PW = "Correct-horse-battery-9";

/** RFC 6238 SHA-1 code for a base32 secret, computed here so the test needs no extra package. */
function totp(secret: string, step = Math.floor(Date.now() / 30000)): string {
  const alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";
  let bits = "";
  for (const ch of secret.toUpperCase()) bits += alphabet.indexOf(ch).toString(2).padStart(5, "0");
  const key = Buffer.from(bits.match(/.{8}/g)!.map((b) => parseInt(b, 2)));
  const msg = Buffer.alloc(8);
  msg.writeBigUInt64BE(BigInt(step));
  const h = createHmac("sha1", key).update(msg).digest();
  const o = h[h.length - 1] & 0x0f;
  return String(((h.readUInt32BE(o) & 0x7fffffff) % 1_000_000)).padStart(6, "0");
}

async function signUp(page: Page): Promise<string> {
  const email = `acct-${Date.now()}-${Math.floor(Math.random() * 1e6)}@example.com`;
  await page.goto("/en");
  await page.getByLabel(en.auth.email, { exact: true }).fill(email);
  await page.getByLabel(en.auth.password, { exact: true }).fill(PW);
  await page.getByRole("button", { name: en.auth.register, exact: true }).click();
  await expect(page.getByRole("button", { name: en.consent.accept, exact: true })).toBeVisible();
  return email;
}

test("two-factor sign-in: enrol, see recovery codes, then log in with a code", async ({ page }) => {
  const email = await signUp(page);
  await page.goto("/en/account");
  await expect(page.getByText(en.account.verifiedNo)).toBeVisible();
  await page.getByRole("button", { name: en.account.tfStart }).click();
  const secret = await page.getByLabel(en.account.tfSecret).inputValue();
  expect(secret).toMatch(/^[A-Z2-7]{32}$/);
  await page.getByLabel(en.account.tfCode).fill(totp(secret));
  await page.getByRole("button", { name: en.account.tfConfirm }).click();
  await expect(page.getByText(en.account.tfRecoveryTitle)).toBeVisible();
  await expect(page.getByText(en.account.tfOn)).toBeVisible();

  // fresh browser state: password alone is not enough any more
  await page.evaluate(() => sessionStorage.clear());
  await page.goto("/en");
  await page.getByRole("button", { name: en.auth.toLogin }).click();
  await page.getByLabel(en.auth.email, { exact: true }).fill(email);
  await page.getByLabel(en.auth.password, { exact: true }).fill(PW);
  await page.getByRole("button", { name: en.auth.login, exact: true }).click();
  await expect(page.getByText(en.auth.otpNeeded)).toBeVisible();
  await page.getByLabel(en.auth.otpLabel).fill(totp(secret, Math.floor(Date.now() / 30000) + 1)); // next step: the enrolment code is spent
  await page.getByRole("button", { name: en.auth.login, exact: true }).click();
  await expect(page.getByRole("button", { name: en.consent.accept, exact: true })).toBeVisible();
});

test("teams: create a team and see its owner", async ({ page }) => {
  const email = await signUp(page);
  await page.goto("/en/teams");
  await expect(page.getByRole("heading", { name: en.teams.title, level: 1 })).toBeVisible();
  await expect(page.getByText(en.teams.none)).toBeVisible();
  await page.getByLabel(en.teams.newName).fill("Dhar Sweets");
  await page.getByRole("button", { name: en.teams.create }).click();
  await expect(page.getByRole("heading", { name: /Dhar Sweets/ })).toBeVisible();
  await expect(page.getByText(email)).toBeVisible();
  await expect(page.getByText(en.teams.noShared)).toBeVisible();
  // inviting needs a confirmed email, and the page says so instead of failing silently
  await page.getByLabel(en.teams.inviteEmail).fill("someone@example.com");
  await page.getByRole("button", { name: en.teams.inviteButton }).click();
  await expect(page.getByText(en.teams.needVerify)).toBeVisible();
});

test("a bad confirmation link says so", async ({ page }) => {
  await page.goto("/en/verify-email?token=not-a-real-token-not-a-real-token");
  await expect(page.getByText(en.verify.failed)).toBeVisible();
});

test("navigation bar follows sign-in and log-out without a page reload", async ({ page }) => {
  const nav = page.getByRole("navigation", { name: en.nav.label });
  await signUp(page);
  // right after sign-up, on the same page, the signed-in links must already be there
  await expect(nav.getByRole("link", { name: en.nav.account, exact: true })).toBeVisible();
  await expect(nav.getByRole("link", { name: en.nav.documents, exact: true })).toBeVisible();
  await page.getByRole("button", { name: en.consent.accept, exact: true }).click();
  await expect(page.getByRole("heading", { name: en.dash.newTitle })).toBeVisible();
  await page.getByRole("button", { name: en.app.logout, exact: true }).click();
  await expect(nav.getByRole("link", { name: en.nav.account, exact: true })).toHaveCount(0);
  // and the page body must leave the signed-in dashboard too
  await expect(page.getByRole("button", { name: en.auth.register, exact: true })).toBeVisible();
});

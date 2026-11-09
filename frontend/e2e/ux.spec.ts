import { expect, test, type Page } from "@playwright/test";
import en from "../messages/en.json";

/** Sign up a brand-new account through the real UI, accept consent, state a goal. */
async function startPlan(page: Page, goal: string) {
  await page.goto("/en");
  const email = `ux-${Date.now()}-${Math.floor(Math.random() * 1e6)}@example.com`;
  await page.getByLabel(en.auth.email, { exact: true }).fill(email);
  await page.getByLabel(en.auth.password, { exact: true }).fill("Correct-horse-battery-9");
  await page.getByRole("button", { name: en.auth.register, exact: true }).click();
  await page.getByRole("button", { name: en.consent.accept, exact: true }).click();
  await page.getByLabel(en.goal.label, { exact: true }).fill(goal);
  await page.getByRole("button", { name: en.goal.start }).click();
  await expect(page.getByRole("heading", { name: en.checklist.heading })).toBeVisible();
}

test("checklist: ticking steps moves the progress ring, marks the next step, and survives a reload", async ({ page }) => {
  await startPlan(page, "I want to open a small bakery in Kolkata");

  const ring = page.getByRole("progressbar", { name: /steps done/ });
  await expect(ring).toHaveAttribute("aria-valuenow", "0");

  const ticks = page.getByRole("button", { name: new RegExp(`^${en.checklist.markDone}`) });
  const total = await ticks.count();
  expect(total).toBeGreaterThan(3);

  await ticks.first().click();
  await expect(ticks.first()).toHaveAttribute("aria-pressed", "true");
  await expect(ring).not.toHaveAttribute("aria-valuenow", "0");
  await expect(page.getByText(en.checklist.nextUp)).toBeVisible();

  await page.reload();
  await expect(page.getByRole("heading", { name: en.checklist.heading })).toBeVisible();
  await expect(page.getByRole("button", { name: new RegExp(`^${en.checklist.markDone}`) }).first()).toHaveAttribute("aria-pressed", "true");
});

test("checklist: every rule shows a review tag and the share link carries only licence names", async ({ page }) => {
  await startPlan(page, "I want to open a small bakery in Kolkata");

  // no rule has been reviewed by a person yet, so each one says so
  await expect(page.getByText(en.checklist.pending).first()).toBeVisible();

  const share = page.getByRole("link", { name: en.checklist.share });
  const href = (await share.getAttribute("href")) ?? "";
  expect(href.startsWith("https://wa.me/?text=")).toBeTruthy();
  const text = decodeURIComponent(href.split("text=")[1]);
  expect(text).toContain("Udyam (MSME) Registration");
  expect(text).not.toMatch(/bakery|Kolkata|@/i); // never the goal, the place or any identifier
});

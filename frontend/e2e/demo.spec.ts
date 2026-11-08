import { expect, test, type Page } from "@playwright/test";
import bn from "../messages/bn.json";
import en from "../messages/en.json";
import hi from "../messages/hi.json";

// Test data only. 210000000007 passes the Aadhaar Verhoeff checksum; ABCPE1234F is a well-formed PAN.
const ANSWERS: Record<string, string> = {
  applicant_name: "Asha Roy", father_name: "Ravi Roy", dob: "14/03/1990", gender: "female", social_category: "general",
  aadhaar: "210000000007", pan: "ABCPE1234F", mobile: "9876543210", email: "asha@example.com",
  residence_address: "12 Park Street Kolkata", residence_pincode: "700016", business_name: "Sweet Crumbs Bakery",
  organisation_type: "proprietorship", date_of_commencement: "01/01/2027", food_products: "Bread, cakes, cookies",
  num_employees: "3", annual_turnover: "900000", investment_amount: "400000", premises_address: "5 College Street Kolkata",
  premises_pincode: "700073", premises_ownership: "rented", premises_area_sqft: "350",
  bank_account_number: "123456789012", bank_ifsc: "SBIN0001234",
};

// UI strings come from the message files so this test cannot drift from the real labels again.
const MSG = { en, bn, hi } as const;
const GOAL = { en: "I want to open a small bakery in Kolkata", bn: "আমি কলকাতায় একটি বেকারি খুলতে চাই", hi: "मैं कोलकाता में बेकरी खोलना चाहता हूँ" } as const;

/** Sign up a brand-new account through the real UI (no demo account exists any more), accept consent, state the goal. */
async function startDemo(page: Page, locale: "en" | "bn" | "hi" = "en") {
  const m = MSG[locale];
  await page.goto(`/${locale}`);
  const email = `e2e-${Date.now()}-${Math.floor(Math.random() * 1e6)}@example.com`;
  await page.getByLabel(m.auth.email, { exact: true }).fill(email);
  await page.getByLabel(m.auth.password, { exact: true }).fill("Correct-horse-battery-9");
  await page.getByRole("button", { name: m.auth.register, exact: true }).click();
  await page.getByRole("button", { name: m.consent.accept, exact: true }).click();
  await page.getByLabel(m.goal.label, { exact: true }).fill(GOAL[locale]);
  await page.getByRole("button", { name: m.goal.start }).click();
}

// Multiple-choice questions (the others are text inputs). Matches backend/app/interview/fields.py options.
const CHOICE_KEYS = new Set(["gender", "social_category", "organisation_type", "premises_ownership"]);

async function currentKeys(page: Page): Promise<string> {
  return (await page.locator('label[for^="q-"]').evaluateAll((els) => els.map((e) => e.getAttribute("for")))).join(",");
}

async function runInterview(page: Page) {
  const review = page.getByRole("button", { name: "Go to review" });
  for (let i = 0; i < 40; i++) {
    if (await review.isVisible()) return;
    const keys = await currentKeys(page);
    if (!keys) {
      await page.waitForTimeout(200);
      continue;
    }
    for (const forId of keys.split(",")) {
      const key = forId.slice(2);
      // Decide by question type, never by "is the input rendered yet": that was a race (the label appears before its input).
      if (CHOICE_KEYS.has(key)) await page.locator(`label[for="${forId}"]`).locator("..").getByRole("button", { name: ANSWERS[key], exact: true }).click();
      else await page.locator(`#${forId}`).fill(ANSWERS[key]); // fill() waits for the input to appear
    }
    const send = page.getByRole("button", { name: "Send", exact: true });
    if (await send.isVisible()) await send.click();
    await expect.poll(async () => (await review.isVisible()) || (await currentKeys(page)) !== keys).toBeTruthy();
  }
  await expect(review).toBeVisible();
}

test("full demo: goal -> research -> interview -> filled PDF review -> download", async ({ page }) => {
  await startDemo(page);

  // research + checklist, with citations on every claim
  await expect(page.getByRole("heading", { name: "Your step-by-step plan" })).toBeVisible();
  await expect(page.getByText("Udyam (MSME) Registration").first()).toBeVisible();
  await expect(page.getByText("FSSAI Food Business Registration / Licence").first()).toBeVisible();
  const sources = page.getByText(/^Source:/);
  expect(await sources.count()).toBeGreaterThan(5);
  await expect(page.getByText("AI-assisted guidance, not legal advice").first()).toBeVisible();
  await page.getByRole("button", { name: "Start the interview" }).click();

  // interview: asked only what is missing, never twice
  await runInterview(page);
  await page.getByRole("button", { name: "Go to review" }).click();

  // review: side-by-side preview + editable fields + summary with citations
  await expect(page.getByRole("heading", { name: "Review before you sign" })).toBeVisible();
  await expect(page.getByRole("img", { name: /Udyam Registration/ })).toBeVisible();
  await page.getByRole("tab", { name: /FSSAI Form A/ }).click();
  await expect(page.getByRole("img", { name: /FSSAI Form A/ })).toBeVisible();
  await expect(page.getByText("placeholder form for demonstration")).toBeVisible();
  await expect(page.getByText("What this means, in plain language")).toBeVisible();
  expect(await page.getByText(/^Source:/).count()).toBeGreaterThan(5);

  // the confirm button is disabled until the explicit consent box is ticked
  const confirm = page.getByRole("button", { name: "I have reviewed this" });
  await expect(confirm).toBeDisabled();
  await page.getByRole("checkbox", { name: /I have reviewed these forms/ }).check();
  await confirm.click();

  // done: downloads available only now; human submits
  await expect(page.getByRole("heading", { name: "Ready to sign and submit" })).toBeVisible();
  await expect(page.getByText("This tool never submits anything for you.").first()).toBeVisible();
  const [download] = await Promise.all([page.waitForEvent("download"), page.getByRole("button", { name: /Download PDF: fssai_form_a/ }).click()]);
  expect(download.suggestedFilename()).toBe("fssai_form_a.pdf");
  await page.getByRole("button", { name: "Sign with Aadhaar e-Sign" }).first().click();
  await expect(page.getByText(/Demo mode: simulated e-Sign/).first()).toBeVisible();

  // there is no way to submit to a government portal from this UI
  await expect(page.getByRole("button", { name: /submit (to|application)/i })).toHaveCount(0);
});

test("Bengali UI and interview questions @mobile", async ({ page }) => {
  await startDemo(page, "bn");
  await expect(page.getByRole("heading", { name: "আপনার ধাপে ধাপে পরিকল্পনা" })).toBeVisible();
  await page.getByRole("button", { name: "তথ্য দেওয়া শুরু করুন" }).click();
  await expect(page.getByRole("heading", { name: "কিছু তথ্য" })).toBeVisible();
  await expect(page.getByText("আপনার পূর্ণ নাম কী (পরিচয়পত্র অনুযায়ী)?").first()).toBeVisible();
  await expect(page.locator("html")).toHaveAttribute("lang", "bn");
  // no horizontal scroll on small screens (mobile-first)
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1);
  expect(overflow).toBe(false);
});

test("validation error is shown in the user's language and the answer is not accepted", async ({ page }) => {
  await startDemo(page, "en");
  await page.getByRole("button", { name: "Start the interview" }).click();
  const name = page.locator('input[id^="q-"]').first();
  await name.fill("12345");
  await page.getByRole("button", { name: "Send", exact: true }).click();
  await expect(page.getByRole("alert").filter({ hasText: "valid name" })).toBeVisible();
});

test("Hindi: licence names and rule text are translated, not left in English", async ({ page }) => {
  await startDemo(page, "hi");
  await expect(page.getByText("उद्यम (MSME) पंजीकरण").first()).toBeVisible();
  await expect(page.getByText("निःशुल्क").first()).toBeVisible(); // "Free of charge" in the Udyam fee line
  await expect(page.getByText("Udyam (MSME) Registration")).toHaveCount(0);
  await expect(page.getByText("Free of charge")).toHaveCount(0);
  await expect(page.locator("html")).toHaveAttribute("lang", "hi");
});

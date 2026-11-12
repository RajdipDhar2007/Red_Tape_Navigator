import { expect, test } from "@playwright/test";

test("help page: linked from the footer, nine answers, available in Bengali and Hindi", async ({ page }) => {
  await page.goto("/en");
  await page.getByRole("contentinfo").getByRole("link", { name: "Help", exact: true }).click();
  await expect(page.getByRole("heading", { level: 1, name: "Help & Support Centre" })).toBeVisible();
  await expect(page.locator('section[aria-labelledby^="faq-"]')).toHaveCount(9);
  await page.goto("/bn/help");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("সহায়তা ও সমর্থন কেন্দ্র");
  await page.goto("/hi/help");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("सहायता और समर्थन केंद्र");
});

test("search engines: public pages are listed, private pages are excluded, the app is installable", async ({ request }) => {
  const robots = await (await request.get("/robots.txt")).text();
  expect(robots).toContain("Disallow: /en/account");
  expect(robots).toContain("Disallow: /hi/staff");
  expect(robots).toContain("/sitemap.xml");
  const sitemap = await (await request.get("/sitemap.xml")).text();
  for (const path of ["/en<", "/bn/help<", "/hi/privacy<", "/en/terms<"]) expect(sitemap).toContain(path);
  expect(sitemap).not.toContain("/account");
  expect(robots).toContain("Disallow: /en/documents");
  expect(sitemap).not.toContain("/documents");
  const manifest = await (await request.get("/manifest.webmanifest")).json();
  expect(manifest.name).toBe("Red Tape Navigator");
  expect(manifest.icons[0].src).toBe("/icon-192.png");
  expect((await request.get("/icon-192.png")).status()).toBe(200);
  expect((await request.get("/logo.png")).status()).toBe(200);
});

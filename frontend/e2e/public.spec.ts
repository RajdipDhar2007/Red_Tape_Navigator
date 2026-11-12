import { expect, test } from "@playwright/test";

test("help page: linked from the footer, nine answers, available in Bengali and Hindi", async ({ page }) => {
  await page.goto("/en");
  await page.getByRole("contentinfo").getByRole("link", { name: "Help", exact: true }).click();
  await expect(page.getByRole("heading", { level: 1, name: "Help and common questions" })).toBeVisible();
  await expect(page.getByRole("heading", { level: 2 })).toHaveCount(9);
  await page.goto("/bn/help");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("সহায়তা ও সাধারণ প্রশ্ন");
  await page.goto("/hi/help");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("सहायता और आम सवाल");
});

test("search engines: public pages are listed, private pages are excluded, the app is installable", async ({ request }) => {
  const robots = await (await request.get("/robots.txt")).text();
  expect(robots).toContain("Disallow: /en/account");
  expect(robots).toContain("Disallow: /hi/staff");
  expect(robots).toContain("/sitemap.xml");
  const sitemap = await (await request.get("/sitemap.xml")).text();
  for (const path of ["/en<", "/bn/help<", "/hi/privacy<", "/en/terms<"]) expect(sitemap).toContain(path);
  expect(sitemap).not.toContain("/account");
  const manifest = await (await request.get("/manifest.webmanifest")).json();
  expect(manifest.name).toBe("Red Tape Navigator");
  expect(manifest.icons[0].src).toBe("/icon.svg");
  expect((await request.get("/icon.svg")).status()).toBe(200);
});

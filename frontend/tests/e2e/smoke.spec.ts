import path from "path";
import { expect, type Page, test } from "@playwright/test";

const PASSWORD = "Password123!";
const FIXTURE = path.resolve(
  __dirname,
  "../../../backend/tests/fixtures/momo_sample.csv",
);

function uniqueEmail(prefix: string): string {
  return `${prefix}-${Date.now()}-${Math.floor(Math.random() * 10000)}@example.com`;
}

async function registerOrg(page: Page): Promise<string> {
  const email = uniqueEmail("admin");
  await page.goto("/register");
  await page.fill("#tenant_name", "E2E Lenders Ltd");
  await page.fill("#contact_email", uniqueEmail("ops"));
  await page.fill("#admin_name", "Ada Admin");
  await page.fill("#admin_email", email);
  await page.fill("#password", PASSWORD);
  await page.getByRole("button", { name: "Create account" }).click();
  // bcrypt + a real db roundtrip can take several seconds
  await expect(page).toHaveURL(/\/dashboard/, { timeout: 30_000 });
  return email;
}

test("register lands on the dashboard with stats", async ({ page }) => {
  await registerOrg(page);
  await expect(page.getByRole("heading", { name: "Overview" })).toBeVisible();
  await expect(page.getByText("Applicants").first()).toBeVisible();
});

test("wrong password shows an error", async ({ page }) => {
  await registerOrg(page);
  // sign out, then try to come back with the wrong password
  await page.getByRole("button", { name: "Sign out" }).click();
  await expect(page).toHaveURL(/\/login/);
  await page.fill("#email", uniqueEmail("someone"));
  await page.fill("#password", "WrongPassword1!");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByText(/Incorrect email or password/)).toBeVisible();
});

test("upload a statement -> report appears with a score", async ({ page }) => {
  await registerOrg(page);

  // add an applicant
  await page.getByRole("button", { name: "+ New" }).click();
  await page.getByPlaceholder("Full name").fill("Mama Efua");
  await page.getByPlaceholder("Phone (e.g. +233201234567)").fill("+233201234567");
  await page.getByRole("button", { name: "Add applicant" }).click();
  await page.selectOption("#merchant", { index: 1 });

  // upload the sample statement
  await page.setInputFiles("#file", FIXTURE);
  await page.getByRole("button", { name: "Upload statement" }).click();
  await expect(page.getByText(/Uploaded — statement/)).toBeVisible();

  // the report is on the reports page with the full score breakdown behind it
  await page.goto("/dashboard/reports");
  const row = page.getByRole("link", { name: "Mama Efua" }).first();
  await expect(row).toBeVisible();
  await row.click();
  await expect(page.getByText("Net verified revenue")).toBeVisible({ timeout: 20_000 });
});

test("viewer accounts are read-only", async ({ page, browser }) => {
  await registerOrg(page);
  const viewerEmail = uniqueEmail("viewer");

  // admin adds a viewer through the team form
  await page.goto("/dashboard/settings");
  await expect(page.getByText("Team")).toBeVisible();
  await page.getByPlaceholder("Name", { exact: true }).fill("Vee Viewer");
  await page.getByPlaceholder("Email", { exact: true }).fill(viewerEmail);
  await page.getByPlaceholder("Password (min 8)").fill(PASSWORD);
  await page.locator("select").last().selectOption("viewer");
  await page.getByRole("button", { name: "Add", exact: true }).click();
  await expect(page.getByText("Team member added.")).toBeVisible();

  // viewer logs in from a clean session
  const viewerContext = await browser.newContext();
  const viewerPage = await viewerContext.newPage();
  await viewerPage.goto("/login");
  await viewerPage.fill("#email", viewerEmail);
  await viewerPage.fill("#password", PASSWORD);
  await viewerPage.getByRole("button", { name: "Sign in" }).click();
  await expect(viewerPage).toHaveURL(/\/dashboard/);

  // settings: can see the team list but not the add form
  await viewerPage.goto("/dashboard/settings");
  await expect(viewerPage.getByText("Ada Admin")).toBeVisible();
  await expect(viewerPage.getByText("Add a teammate")).toHaveCount(0);

  // api gate: upload attempt is refused with the viewer message
  await viewerPage.goto("/dashboard");
  await viewerPage.getByRole("button", { name: "+ New" }).click();
  await viewerPage.getByPlaceholder("Full name").fill("Blocked Viewer");
  await viewerPage.getByPlaceholder("Phone (e.g. +233201234567)").fill("+233200000009");
  await viewerPage.getByRole("button", { name: "Add applicant" }).click();
  await expect(viewerPage.getByText("Viewers have read-only access")).toBeVisible({ timeout: 20_000 });

  await viewerContext.close();
});

test("forgot-password shows the neutral confirmation", async ({ page }) => {
  await registerOrg(page);
  await page.goto("/forgot-password");
  await page.fill("#email", uniqueEmail("ghost"));
  await page.getByRole("button", { name: "Send reset link" }).click();
  await expect(page.getByText(/reset link is on its way/)).toBeVisible();
});

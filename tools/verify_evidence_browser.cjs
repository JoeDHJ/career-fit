/* Independent browser tasks for the new evidence, progress and business routes. */
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || "playwright");
const assert = require("node:assert/strict");
const path = require("node:path");
const base = process.env.CAREER_FIT_URL || "http://127.0.0.1:8766";
async function run() {
  const browser = await chromium.launch({
    headless: true,
    ...(process.env.CAREER_FIT_BROWSER_CHANNEL
      ? { channel: process.env.CAREER_FIT_BROWSER_CHANNEL }
      : {}),
  });
  const page = await browser.newPage({
    viewport: { width: 1440, height: 1000 },
    reducedMotion: "reduce",
  });
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  const ready = () =>
    page.waitForFunction(() =>
      document.querySelector("#input-json")?.value.includes('"analysis_input"'),
    );
  const calculate = async () => {
    await page.locator("#review").check();
    await page.locator("#calculate").click();
    await page.locator("#result").waitFor({ state: "visible" });
  };
  const overflow = async () =>
    assert(
      await page.evaluate(
        () =>
          document.documentElement.scrollWidth <=
          document.documentElement.clientWidth,
      ),
    );
  const shot = async (name) => {
    if (process.argv.includes("--screenshots"))
      await page.screenshot({
        path: path.resolve(__dirname, "../docs/assets/" + name),
        fullPage: true,
      });
  };
  try {
    await page.goto(base + "/showcase");
    await page.waitForFunction(() =>
      document.querySelector("#measurement-table tbody tr"),
    );
    if (process.argv.includes("--screenshots")) {
      const bottom = await page
        .locator(".timeline")
        .first()
        .evaluate((n) => n.getBoundingClientRect().bottom);
      await page.screenshot({
        path: path.resolve(
          __dirname,
          "../docs/assets/career-fit-showcase-entry-0.8.png",
        ),
        clip: { x: 0, y: 0, width: 1440, height: Math.ceil(bottom + 24) },
      });
    }
    assert.equal(await page.locator("#measurement-table tbody tr").count(), 4);
    assert.match(await page.locator("#business-metrics").innerText(), /81,040/);
    await page
      .locator("#sensitivity-choice")
      .selectOption("training_effect_multiplier");
    assert.match(
      await page.locator("#sensitivity-table").innerText(),
      /122,000/,
    );
    await overflow();
    await shot("career-fit-showcase-0.8.png");
    await page.setViewportSize({ width: 390, height: 844 });
    await overflow();
    await shot("career-fit-showcase-mobile-0.8.png");
    await page.setViewportSize({ width: 1440, height: 1000 });
    await page.goto(base + "/capital?case=business");
    await page.waitForFunction(() =>
      document.querySelector("#input-json").value.includes('"E30"'),
    );
    assert.match(await page.locator("#mode-label").innerText(), /WORKFORCE/);
    await calculate();
    assert.match(await page.locator("#metrics").innerText(), /81,040/);
    assert.match(await page.locator("#metrics").innerText(), /vacancy/);
    await overflow();
    await shot("career-fit-business-0.8.png");
    await page
      .locator("#workforce-editor details")
      .evaluateAll((nodes) => nodes.forEach((n) => (n.open = true)));
    await page
      .getByLabel("Backfill cash cost · E01", { exact: true })
      .fill("5000");
    assert(await page.locator("#result").isHidden());
    assert.equal(await page.locator("#review").isChecked(), false);
    await calculate();
    await page.setViewportSize({ width: 390, height: 844 });
    await overflow();
    await page.setViewportSize({ width: 1440, height: 1000 });
    await page.goto(base + "/capital");
    await ready();
    await calculate();
    assert.match(await page.locator("#metrics").innerText(), /920/);
    await page.locator("#budget").fill("90");
    await page.locator("#load-demo").click();
    await page.waitForFunction(
      () => document.querySelector("#budget").value === "100",
    );
    await calculate();
    await shot("career-fit-learning-0.8.png");
    await page.locator("#role-editor details").evaluate((n) => (n.open = true));
    const request = page.waitForRequest(
      (r) => r.url().endsWith("/api/analyze") && r.method() === "POST",
    );
    await page
      .getByRole("button", { name: "Review role and evidence", exact: true })
      .click();
    const incoming = (await request).postDataJSON();
    assert.equal(incoming.evidence.length, 2);
    await page.locator("#apply-review-button").waitFor({ state: "visible" });
    await page.locator("#apply-review-button").click();
    await page.waitForFunction(() =>
      document
        .querySelector("#status")
        .textContent.includes("Reviewed analysis"),
    );
    await page.locator("#investment-button").click();
    await page.waitForURL("**/capital");
    await ready();
    await page.waitForFunction(() =>
      document.querySelector("#case-note").textContent.includes("preserved"),
    );
    await page
      .locator("#progress-editor details")
      .evaluateAll((nodes) => nodes.forEach((n) => (n.open = true)));
    const title = "Data analysis: visualisations in Excel";
    await page
      .getByLabel("Status · " + title, { exact: true })
      .selectOption("completed");
    await page
      .getByLabel("Assessment · " + title, { exact: true })
      .selectOption("passed");
    await page
      .getByLabel("Actual hours · " + title, { exact: true })
      .fill("11");
    await page
      .getByLabel("Artifact location · " + title, { exact: true })
      .fill("local-work/pivot.csv");
    await page
      .getByLabel("Review notes · " + title, { exact: true })
      .fill(
        "Self-assessed: totals reconcile; another person can reproduce the pivot and challenge the denominator",
      );
    for (const prefix of [
      "Correctness:",
      "Reproducibility:",
      "Interpretation:",
      "Independence:",
    ])
      await page
        .locator("#progress-editor label")
        .filter({ hasText: prefix })
        .first()
        .locator("input")
        .fill("2");
    await page.locator("#review").check();
    await page.locator("#transfer-progress").click();
    await page.waitForURL(base + "/");
    await page.locator("#apply-review-button").waitFor({ state: "visible" });
    assert(await page.locator("#download-markdown-button").isDisabled());
    assert.match(
      await page.locator("#review-added-list").innerText(),
      /pivot.csv/,
    );
    await page.locator("#apply-review-button").click();
    await page.waitForFunction(() =>
      document
        .querySelector("#status")
        .textContent.includes("Reviewed analysis"),
    );
    await page.locator("#investment-button").click();
    await page.waitForURL("**/capital");
    await page.waitForFunction(() =>
      document.querySelector("#case-note").textContent.includes("preserved"),
    );
    const restored = JSON.parse(await page.locator("#input-json").inputValue());
    assert.equal(restored.courses[0].id, "ou-excel");
    assert.equal(restored.progress[0].actual_hours, 11);
    assert.equal(restored.progress[0].assessment, "passed");
    assert.equal(restored.analysis_input.evidence.length, 2);
    await calculate();
    assert.match(
      await page.locator("#evidence").innerText(),
      /11 reported actual hours/,
    );
    const saved = page.waitForEvent("download");
    await page.locator("#save-plan").click();
    const file = await saved;
    const fs = require("node:fs/promises");
    const content = await fs.readFile(await file.path());
    await page.locator("#budget").fill("20");
    await page
      .locator("#restore-plan")
      .setInputFiles({
        name: "saved-plan.json",
        mimeType: "application/json",
        buffer: content,
      });
    await page.waitForFunction(() =>
      document
        .querySelector("#case-note")
        .textContent.includes("Restored local draft"),
    );
    assert.equal(await page.locator("#budget").inputValue(), "100");
    assert.equal(
      JSON.parse(await page.locator("#input-json").inputValue()).progress[0]
        .actual_hours,
      11,
    );
    await calculate();
    await page.setViewportSize({ width: 390, height: 844 });
    await overflow();
    assert.deepEqual(errors, []);
    console.log(
      "PASS: showcase, model results, sensitivity, business deep link/forms, review invalidation, structured evidence, task rubric and preserved progress round trip; desktop/mobile.",
    );
  } finally {
    await browser.close();
  }
}
run().catch((e) => {
  console.error(e);
  process.exitCode = 1;
});

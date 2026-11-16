/* Real browser regression. Set PLAYWRIGHT_MODULE to an installed Playwright path. */
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || "playwright");
const assert = require("node:assert/strict");
const fs = require("node:fs/promises");
const path = require("node:path");
const base = process.env.CAREER_FIT_URL || "http://127.0.0.1:8766";
const capture = process.argv.includes("--screenshots");
const asset = path.resolve(__dirname, "../docs/assets");

async function run() {
  const browser = await chromium.launch({headless:true, ...(process.env.CAREER_FIT_BROWSER_CHANNEL ? {channel:process.env.CAREER_FIT_BROWSER_CHANNEL} : {})});
  const page = await browser.newPage({viewport:{width:1440,height:1000}, reducedMotion:"reduce"});
  const errors = [];
  page.on("pageerror", e => errors.push(e.message));
  const ready = () => page.waitForFunction(() => document.querySelector("#input-json").value.includes("analysis_input"));
  const calculate = async () => {await page.locator("#review").check();await page.locator("#calculate").click();await page.locator("#result").waitFor({state:"visible"});};
  const overflow = async () => assert(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth));
  const screenshot = async (name, selectors) => {
    if(!capture)return;
    const bounds = await page.evaluate(selectors => {
      const rects = selectors.map(s => document.querySelector(s).getBoundingClientRect());
      return {x:Math.max(0,Math.min(...rects.map(r=>r.x))-24),y:Math.max(0,Math.min(...rects.map(r=>r.y))+scrollY-24),width:Math.max(...rects.map(r=>r.right))-Math.max(0,Math.min(...rects.map(r=>r.x))-24)+24,height:Math.max(...rects.map(r=>r.bottom))-Math.min(...rects.map(r=>r.y))+48};
    }, selectors);
    await page.screenshot({path:path.join(asset,name),fullPage:true,clip:bounds});
  };
  try {
    await page.goto(base+"/capital?case=legacy");await ready();
    await page.locator("#calculate").click();assert.match(await page.locator("#status").innerText(), /Confirm/);
    await screenshot("career-fit-capital-inputs.png",["header",".hero",".tabs","#inputs"]);
    await calculate();assert.match(await page.locator("#metrics").innerText(), /1,680/);
    assert.match(await page.locator("#eligibility").innerText(), /not_met/);
    await overflow();await screenshot("career-fit-investment.png",["#decision","#comparison","#actions"]);
    let downloaded = page.waitForEvent("download");await page.locator("#export-md").click();let file=await downloaded;
    assert.match(await fs.readFile(await file.path(),"utf8"),/economic cost: 1680/);
    await page.locator("#budget").fill("150");assert(await page.locator("#result").isHidden());assert(await page.locator("#export-md").isDisabled());assert.equal(await page.locator("#review").isChecked(),false);
    await calculate();assert.match(await page.locator("#metrics").innerText(), /1,020/);
    await page.locator("#benefit-details").evaluate(n=>n.open=true);
    await page.locator("#benefit").fill("1000");await page.locator("#basis").fill("Explicit illustrative paid-project income");await calculate();
    assert.match(await page.locator("#returns-table").innerText(), /1.5/);
    downloaded=page.waitForEvent("download");await page.locator("#export-md").click();file=await downloaded;assert.match(await fs.readFile(await file.path(),"utf8"),/years: 3; discount rate: 0.05/);
    await page.locator("#advanced").evaluate(n=>n.open=true);await page.locator("#input-json").fill("[");await page.locator("#review").check();await page.locator("#calculate").click();assert(await page.locator("#result").isHidden());
    await page.locator("#workforce-tab").click();await page.waitForFunction(()=>document.querySelector("#input-json").value.includes('"employees"'));
    await calculate();assert.match(await page.locator("#metrics").innerText(),/3,016/);assert.match(await page.locator("#evidence-table").innerText(),/Systems Evaluation/);
    await overflow();await screenshot("career-fit-workforce.png",["#decision","#comparison","#actions"]);
    downloaded=page.waitForEvent("download");await page.locator("#export-json").click();file=await downloaded;assert.equal(JSON.parse(await fs.readFile(await file.path(),"utf8")).scenarios.hybrid.filled,4);
    await page.setViewportSize({width:390,height:844});await overflow();await screenshot("career-fit-capital-mobile.png",["#decision","#comparison"]);
    await page.locator("#hours").fill("24");await page.locator("#budget").fill("1400");await calculate();assert.match(await page.locator("#decision-title").innerText(),/3 positions/);await overflow();
    await page.locator("#personal-tab").click();await ready();await calculate();await overflow();

    // Preserve consumer workflow, invalidate review edits, and transfer only current IDs.
    await page.setViewportSize({width:1440,height:1000});await page.goto(base+"/");
    await page.locator("#example-button").click();await page.locator("#apply-review-button").waitFor({state:"visible"});await page.locator("#apply-review-button").click();
    await page.waitForFunction(()=>document.querySelector("#status").textContent.includes("Reviewed analysis"));
    await page.locator("#edit-review-button").click();
    const gate=page.locator('#review-requirements select[aria-label^="Confirm"]').first();await gate.selectOption("not_met");
    assert(await page.locator("#download-markdown-button").isDisabled());assert(await page.locator("#investment-button").isDisabled());
    await page.locator("#back-to-inputs-button").click();
    await page.locator("#roles-input").fill("Data Analyst. Must have Python and SQL.\n---\nResearch Analyst. Must have research and writing.");
    await page.locator("#compare-button").click();assert.match(await page.locator("#compare-status").innerText(),/Recalculate/);
    await page.locator("#analyze-button").click();await page.locator("#apply-review-button").waitFor({state:"visible"});
    await page.locator("#apply-review-button").click();await page.waitForFunction(()=>document.querySelector("#status").textContent.includes("Reviewed analysis"));
    downloaded=page.waitForEvent("download");await page.locator("#download-pdf-button").click();file=await downloaded;assert.equal((await fs.readFile(await file.path())).subarray(0,4).toString(),"%PDF");
    await page.locator("#investment-button").click();await page.waitForURL("**/capital");await page.waitForFunction(()=>document.querySelector("#case-note").textContent.includes("exact current skill IDs"));
    assert.equal(await page.locator("#occupation").inputValue(),"");assert.equal(await page.locator("#geography").inputValue(),"");
    const input=JSON.parse(await page.locator("#input-json").inputValue());assert(input.courses.every(c=>c.id.startsWith("proof-")));assert(input.courses.every(c=>c.skills.every(s=>c.skill_labels[s])));
    assert.equal(await page.evaluate(()=>sessionStorage.getItem("career-fit-investment")),null);
    await calculate();assert.match(await page.locator("#market").innerText(),/No matching/);
    assert.deepEqual(errors,[]);
    console.log("PASS: desktop/mobile, review gate/invalidation, budgets/hours, labeled gaps, ROI assumptions, JSON/Markdown/PDF exports, and safe consumer transfer.");
  } finally {await browser.close();}
}
run().catch(error=>{console.error(error);process.exitCode=1;});

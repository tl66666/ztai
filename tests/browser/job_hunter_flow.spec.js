const assert = require("node:assert/strict");
const { after, before, test } = require("node:test");
const { spawn } = require("node:child_process");
const fs = require("node:fs");
const net = require("node:net");
const os = require("node:os");
const path = require("node:path");

let playwright;
try {
  playwright = require("playwright");
} catch (error) {
  throw new Error("Playwright is unavailable. Set NODE_PATH to an existing playwright installation.", { cause: error });
}

const ROOT = path.resolve(__dirname, "..", "..");
const ARTIFACT_DIR = path.join(ROOT, "output", "playwright");
const KNOWN_CHROMIUM = "C:\\Users\\唐乐\\AppData\\Local\\ms-playwright\\chromium-1228\\chrome-win64\\chrome.exe";
const EDGE_PATHS = [
  "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
  "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
];
const VIEWPORTS = {
  desktop: { width: 1440, height: 900 },
  mobile: { width: 390, height: 844 },
};

let server;
let tempDirectory;
let baseURL;

function freePort() {
  return new Promise((resolve, reject) => {
    const probe = net.createServer();
    probe.unref();
    probe.once("error", reject);
    probe.listen(0, "127.0.0.1", () => {
      const { port } = probe.address();
      probe.close(() => resolve(port));
    });
  });
}

async function waitForServer(url, child) {
  const deadline = Date.now() + 20_000;
  while (Date.now() < deadline) {
    if (child.exitCode !== null) throw new Error(`Flask exited before becoming ready (${child.exitCode})`);
    try {
      const response = await fetch(`${url}/api/config/ai-status`);
      if (response.ok) return;
    } catch (_error) {
      // The process may still be importing dependencies or migrating its database.
    }
    await new Promise((resolve) => setTimeout(resolve, 150));
  }
  throw new Error("Timed out waiting for the isolated Flask service");
}

before(async () => {
  fs.mkdirSync(ARTIFACT_DIR, { recursive: true });
  tempDirectory = fs.mkdtempSync(path.join(os.tmpdir(), "jobhunter-e2e-"));
  const port = await freePort();
  baseURL = `http://127.0.0.1:${port}`;
  const python = process.env.PYTHON || "python";
  const program = [
    "import app as module",
    "module.init_db()",
    `module.app.run(host='127.0.0.1', port=${port}, debug=False, use_reloader=False, threaded=True)`,
  ].join("; ");
  server = spawn(python, ["-c", program], {
    cwd: ROOT,
    env: {
      ...process.env,
      JOBHUNTER_DB_PATH: path.join(tempDirectory, "jobhunter-e2e.db"),
      JOBHUNTER_PORT: String(port),
      JOBHUNTER_HOST: "127.0.0.1",
      GLM_API_KEY: "",
      DEEPSEEK_API_KEY: "",
      KIMI_API_KEY: "",
      MOONSHOT_API_KEY: "",
      PYTHONUNBUFFERED: "1",
    },
    stdio: ["ignore", "pipe", "pipe"],
    windowsHide: true,
  });
  const log = fs.createWriteStream(path.join(ARTIFACT_DIR, "e2e-server.log"), { flags: "w" });
  server.stdout.pipe(log);
  server.stderr.pipe(log);
  await waitForServer(baseURL, server);
});

after(async () => {
  if (server && server.exitCode === null) {
    server.kill();
    await Promise.race([
      new Promise((resolve) => server.once("exit", resolve)),
      new Promise((resolve) => setTimeout(resolve, 2_000)),
    ]);
  }
  if (tempDirectory) fs.rmSync(tempDirectory, { recursive: true, force: true });
});

function browserMatrix() {
  const chromiumPath = process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE
    || (fs.existsSync(KNOWN_CHROMIUM) ? KNOWN_CHROMIUM : playwright.chromium.executablePath());
  const firefoxPath = process.env.PLAYWRIGHT_FIREFOX_EXECUTABLE || playwright.firefox.executablePath();
  const edgePath = EDGE_PATHS.find((candidate) => fs.existsSync(candidate));
  return [
    {
      name: "chromium",
      type: playwright.chromium,
      launch: fs.existsSync(chromiumPath) ? { executablePath: chromiumPath } : null,
      skip: fs.existsSync(chromiumPath) ? "" : `Chromium executable not found: ${chromiumPath}`,
    },
    {
      name: "edge",
      type: playwright.chromium,
      launch: edgePath ? { channel: "msedge" } : null,
      skip: edgePath ? "" : `Microsoft Edge channel msedge not installed; checked ${EDGE_PATHS.join(", ")}`,
    },
    {
      name: "firefox",
      type: playwright.firefox,
      launch: fs.existsSync(firefoxPath) ? { executablePath: firefoxPath } : null,
      skip: fs.existsSync(firefoxPath) ? "" : `Playwright Firefox executable not found: ${firefoxPath}`,
    },
  ];
}

async function jsonFrom(responsePromise) {
  const response = await responsePromise;
  const body = await response.json();
  assert.equal(body.success, true, `${response.url()} failed: ${JSON.stringify(body)}`);
  return { response, body };
}

async function fetchJson(page, endpoint, options = {}) {
  return page.evaluate(async ({ endpoint, options }) => {
    const response = await fetch(endpoint, {
      ...options,
      headers: { "Content-Type": "application/json", ...(options.headers || {}) },
      body: options.body === undefined ? undefined : JSON.stringify(options.body),
    });
    return { status: response.status, body: await response.json() };
  }, { endpoint, options });
}

async function assertViewportIntegrity(page, viewport, label) {
  const layout = await page.evaluate(() => {
    const documentWidth = document.documentElement.clientWidth;
    const overflows = [...document.querySelectorAll("input, textarea, select, button")]
      .filter((element) => {
        const style = getComputedStyle(element);
        const box = element.getBoundingClientRect();
        return style.display !== "none" && style.visibility !== "hidden" && box.width > 0
          && (box.left < -1 || box.right > documentWidth + 1);
      })
      .slice(0, 8)
      .map((element) => `${element.tagName.toLowerCase()}#${element.id || element.className}`);
    return {
      clientWidth: document.documentElement.clientWidth,
      scrollWidth: document.documentElement.scrollWidth,
      overflows,
    };
  });
  assert.ok(layout.scrollWidth <= layout.clientWidth + 1, `${label}: horizontal overflow ${layout.scrollWidth}/${layout.clientWidth}`);
  assert.deepEqual(layout.overflows, [], `${label}: controls outside viewport`);

  const launcher = page.locator("#agentLauncher");
  await launcher.click();
  const drawer = page.locator("#agentDrawer");
  await drawer.waitFor({ state: "visible" });
  await page.waitForFunction(() => {
    const transform = getComputedStyle(document.querySelector("#agentDrawer")).transform;
    return transform === "none" || transform === "matrix(1, 0, 0, 1, 0, 0)";
  });
  const drawerBox = await drawer.boundingBox();
  const inputBox = await page.locator("#agentInput").boundingBox();
  assert.ok(drawerBox && inputBox, `${label}: Agent surface did not render`);
  assert.ok(inputBox.x >= drawerBox.x - 1 && inputBox.x + inputBox.width <= drawerBox.x + drawerBox.width + 1,
    `${label}: Agent input escapes its surface`);
  if (viewport.width <= 480) {
    assert.ok(drawerBox.width >= viewport.width * 0.9
      && drawerBox.y >= viewport.height * 0.05
      && drawerBox.y + drawerBox.height >= viewport.height - 2,
      `${label}: Agent should be a mobile bottom sheet`);
  } else {
    assert.ok(drawerBox.x >= viewport.width * 0.55 && drawerBox.height >= viewport.height * 0.9,
      `${label}: Agent should be a desktop right drawer`);
  }
  await page.locator("#closeAgentDrawer").click();
}

async function runCareerWorkflow(browser, browserName, viewportName, viewport) {
  const context = await browser.newContext({ viewport, locale: "zh-CN" });
  await context.tracing.start({ screenshots: true, snapshots: true, sources: false });
  const page = await context.newPage();
  const pageErrors = [];
  const consoleErrors = [];
  const project404s = [];
  page.on("pageerror", (error) => pageErrors.push(error.message));
  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });
  page.on("response", (response) => {
    if (response.status() === 404 && response.url().startsWith(baseURL)) project404s.push(response.url());
  });
  await page.route("https://unpkg.com/**", (route) => route.fulfill({
    contentType: "application/javascript",
    body: "window.lucide={createIcons:function(){}};",
  }));
  await page.route("https://cdn.jsdelivr.net/**", (route) => route.fulfill({
    contentType: "application/javascript",
    body: "window.Chart=class Chart{destroy(){}};",
  }));
  await page.addInitScript(() => {
    Object.defineProperty(window, "SpeechRecognition", { configurable: true, value: undefined });
    Object.defineProperty(window, "webkitSpeechRecognition", { configurable: true, value: undefined });
    Object.defineProperty(window, "MediaRecorder", { configurable: true, value: undefined });
  });

  const suffix = `${browserName}-${viewportName}-${Date.now()}`;
  await page.goto(baseURL, { waitUntil: "domcontentloaded" });
  await page.locator("#resumeCount").waitFor({ state: "attached" });
  await page.waitForFunction(() => document.querySelector("#providerSelect")?.options.length > 0);

  const fallbackState = await page.evaluate(() => ({
    voiceDisabled: document.querySelector("#voiceBtn").disabled,
    voiceHiddenClass: document.querySelector("#voiceBtn").classList.contains("hidden"),
    recordDisabled: document.querySelector("#recordAudioBtn").disabled,
    recordHiddenClass: document.querySelector("#recordAudioBtn").classList.contains("hidden"),
  }));
  assert.deepEqual(fallbackState, {
    voiceDisabled: true,
    voiceHiddenClass: true,
    recordDisabled: true,
    recordHiddenClass: true,
  }, `${suffix}: unsupported capability controls were not disabled and hidden`);
  assert.equal(await page.locator("#audioFileInput").isEnabled(), true, `${suffix}: audio upload fallback disabled`);
  assert.equal(await page.locator("#answerInput").isEnabled(), true, `${suffix}: text fallback disabled`);
  await assertViewportIntegrity(page, viewport, suffix);

  const profile = await fetchJson(page, "/api/profile", {
    method: "PUT",
    body: {
      career_direction: "software",
      target_role: "AI 应用测试工程师",
      cities: ["杭州"],
      salary: { min: 15, max: 25 },
      confirmed_skills: ["Python", "接口测试", "Playwright"],
      source_metadata: { form: "browser-e2e" },
    },
  });
  assert.equal(profile.status, 200);
  assert.equal(profile.body.data.target_role, "AI 应用测试工程师");

  await page.evaluate(() => navigateToRoute("resume", "input"));
  await page.locator("#resumeTitle").fill(`跨浏览器简历-${suffix}`);
  await page.locator("#resumeContent").fill(
    "求职目标：AI 应用测试工程师。项目：使用 Python、Flask、SQLite 和 Playwright 建设求职 Agent，完成接口测试、浏览器兼容验证与缺陷复盘。"
  );
  const resumeResult = jsonFrom(page.waitForResponse((response) => response.url().endsWith("/api/resumes") && response.request().method() === "POST"));
  await page.locator("#saveResumeBtn").click();
  const { body: resumeBody } = await resumeResult;
  const resumeId = Number(resumeBody.resume_id);
  assert.ok(resumeId > 0, `${suffix}: resume was not persisted`);

  await page.evaluate(() => navigateToRoute("resume", "jd"));
  await page.locator("#tailorResumeSelect").selectOption(String(resumeId));
  await page.locator("#jobTitleInput").fill("AI 应用测试工程师");
  const jd = "负责 AI 应用质量保障，要求 Python、接口测试、Playwright 自动化、SQL、缺陷分析和跨浏览器测试经验。";
  await page.locator("#jdInput").fill(jd);
  const matchResult = jsonFrom(page.waitForResponse((response) => response.url().endsWith("/api/job-match") && response.request().method() === "POST"));
  await page.locator("#matchBtn").click();
  const { body: matchBody } = await matchResult;
  assert.ok(Number.isFinite(Number(matchBody.match_score)), `${suffix}: JD match has no score`);
  await page.locator("#tailorResult").getByRole("button", { name: "新增投递记录" }).click();
  await page.locator("#appCompany").fill(`兼容科技-${suffix}`);
  await page.locator("#appCity").fill("杭州");
  const applicationResult = jsonFrom(page.waitForResponse((response) => response.url().endsWith("/api/applications") && response.request().method() === "POST"));
  await page.locator("#saveAppBtn").click();
  const { body: applicationBody } = await applicationResult;
  const opportunityId = Number(applicationBody.application_id);
  assert.ok(opportunityId > 0, `${suffix}: opportunity was not persisted`);
  const opportunityBefore = await fetchJson(page, `/api/opportunities/${opportunityId}`);
  assert.equal(opportunityBefore.body.data.resume_id, resumeId);
  assert.equal(opportunityBefore.body.data.jd_text, jd);

  await page.locator("#agentLauncher").click();
  await page.locator("#agentInput").fill(`请把机会ID ${opportunityId}推进到简历筛选`);
  const chatResult = jsonFrom(page.waitForResponse((response) => response.url().endsWith("/api/agent/chat") && response.request().method() === "POST"));
  await page.locator("#sendAgentBtn").click();
  const { body: chatBody } = await chatResult;
  assert.equal(chatBody.action_proposals.length, 1, `${suffix}: deterministic Agent did not propose the stage update`);
  const proposalId = Number(chatBody.action_proposals[0].id);
  const confirmResult = jsonFrom(page.waitForResponse((response) => response.url().endsWith(`/api/agent/actions/${proposalId}/confirm`)));
  await page.locator(`[data-proposal-id="${proposalId}"] [data-agent-action="confirm"]`).click();
  const { body: confirmBody } = await confirmResult;
  assert.equal(confirmBody.action.status, "completed");
  assert.equal(confirmBody.result.id, opportunityId);
  const opportunityAfter = await fetchJson(page, `/api/opportunities/${opportunityId}`);
  assert.equal(opportunityAfter.body.data.status, "简历筛选", `${suffix}: confirmed Agent action did not change business state`);
  await page.locator("#closeAgentDrawer").click();

  await page.evaluate(() => prepareInterviewFromOpportunity(null));
  await page.locator("#interviewResumeSelect").selectOption(String(resumeId));
  const startResponsePromise = page.waitForResponse((response) => response.url().endsWith("/api/interview/sessions") && response.request().method() === "POST");
  await page.locator("#startInterviewBtn").click();
  const startResponse = await startResponsePromise;
  const startBody = await startResponse.json();
  assert.equal(startBody.success, true);
  const startPayload = startResponse.request().postDataJSON();
  assert.equal(startPayload.application_id, opportunityId);
  const sessionId = String(startBody.session_id);
  assert.ok(sessionId, `${suffix}: interview session missing`);

  await page.reload({ waitUntil: "domcontentloaded" });
  await page.waitForFunction(() => document.querySelector("#providerSelect")?.options.length > 0);
  const openSessions = await fetchJson(page, "/api/interview/sessions/open");
  assert.ok(openSessions.body.data.some((item) => String(item.session_id) === sessionId),
    `${suffix}: active interview was not discoverable after restart`);
  await page.evaluate((id) => openOpportunityWorkspace(id), opportunityId);
  await page.locator("#opportunityWorkspace").waitFor({ state: "visible" });
  await page.locator("#opportunity-tab-interview").click();
  const continueResponse = page.waitForResponse((response) => response.url().endsWith(`/api/interview/sessions/${sessionId}`));
  await page.locator("#opportunity-interview").getByRole("button", { name: "继续面试" }).click();
  await continueResponse;
  await page.locator("#interviewRoom").waitFor({ state: "visible" });
  assert.equal(await page.locator("#recordAudioBtn").isHidden(), true, `${suffix}: recording fallback failed on visible interview page`);
  assert.equal(await page.locator("#roomRecordBtn").isHidden(), true, `${suffix}: room recording fallback failed`);
  assert.equal(await page.locator("#audioFileInput").isEnabled(), true, `${suffix}: upload fallback failed after restart`);
  assert.equal(await page.locator("#roomAnswer").isEnabled(), true, `${suffix}: text fallback failed after restart`);
  const session = await fetchJson(page, `/api/interview/sessions/${encodeURIComponent(sessionId)}`);
  assert.equal(session.body.status, "active");
  const workspace = await fetchJson(page, `/api/opportunities/${opportunityId}/workspace`);
  assert.ok(workspace.body.interviews.some((item) => String(item.id) === sessionId), `${suffix}: interview not linked to opportunity`);
  const timeline = await fetchJson(page, `/api/opportunities/${opportunityId}/timeline`);
  assert.ok(timeline.body.data.some((event) => event.event_type === "opportunity.created"), `${suffix}: creation absent from timeline`);
  assert.ok(timeline.body.data.some((event) => event.event_type === "opportunity.updated"), `${suffix}: status update absent from timeline`);

  await page.locator("#closeInterviewRoom").click();
  await page.screenshot({ path: path.join(ARTIFACT_DIR, `${browserName}-${viewportName}.png`), fullPage: false });
  await assertViewportIntegrity(page, viewport, `${suffix}-final`);
  assert.deepEqual(project404s, [], `${suffix}: project resources returned 404`);
  assert.deepEqual(pageErrors, [], `${suffix}: unhandled page errors`);
  assert.deepEqual(consoleErrors, [], `${suffix}: console errors`);
  await context.tracing.stop({ path: path.join(ARTIFACT_DIR, `${browserName}-${viewportName}-trace.zip`) });
  await context.close();
}

for (const browserConfig of browserMatrix()) {
  for (const [viewportName, viewport] of Object.entries(VIEWPORTS)) {
    const name = `${browserConfig.name} ${viewportName} career workflow`;
    test(name, { timeout: 120_000, skip: browserConfig.skip || undefined }, async () => {
      const browser = await browserConfig.type.launch({ headless: true, ...browserConfig.launch });
      try {
        await runCareerWorkflow(browser, browserConfig.name, viewportName, viewport);
      } finally {
        await browser.close();
      }
    });
  }
}

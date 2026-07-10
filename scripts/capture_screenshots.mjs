import { mkdir, writeFile } from "node:fs/promises";
import { existsSync } from "node:fs";
import { spawn } from "node:child_process";
import path from "node:path";

const baseUrl = process.env.SUPPORTFLOW_BASE_URL || "http://127.0.0.1:8000";
const email = process.env.SUPPORTFLOW_DEMO_EMAIL || "demo@example.com";
const password = process.env.SUPPORTFLOW_DEMO_PASSWORD || "DemoPass123!";
const outputDir = process.env.SUPPORTFLOW_SCREENSHOT_DIR || "docs/screenshots";
const port = Number(process.env.SUPPORTFLOW_CDP_PORT || 9223);

function findBrowser() {
  const candidates = [
    process.env.BROWSER_PATH,
    "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
    "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
    "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
    "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
    "/usr/bin/microsoft-edge",
  ].filter(Boolean);

  return candidates.find((candidate) => existsSync(candidate));
}

async function waitForJson(url, timeoutMs = 10000) {
  const deadline = Date.now() + timeoutMs;
  let lastError;

  while (Date.now() < deadline) {
    try {
      const response = await fetch(url);
      if (response.ok) return response.json();
      lastError = new Error(`HTTP ${response.status}`);
    } catch (error) {
      lastError = error;
    }
    await new Promise((resolve) => setTimeout(resolve, 150));
  }

  throw lastError || new Error(`Timed out waiting for ${url}`);
}

class CdpClient {
  constructor(wsUrl) {
    this.ws = new WebSocket(wsUrl);
    this.nextId = 1;
    this.pending = new Map();
    this.events = [];

    this.ws.addEventListener("message", (event) => {
      const payload = JSON.parse(event.data);
      if (payload.id && this.pending.has(payload.id)) {
        const { resolve, reject } = this.pending.get(payload.id);
        this.pending.delete(payload.id);
        if (payload.error) reject(new Error(payload.error.message));
        else resolve(payload.result || {});
        return;
      }
      if (payload.method) this.events.push(payload);
    });
  }

  async open() {
    if (this.ws.readyState === WebSocket.OPEN) return;
    await new Promise((resolve, reject) => {
      this.ws.addEventListener("open", resolve, { once: true });
      this.ws.addEventListener("error", reject, { once: true });
    });
  }

  send(method, params = {}) {
    const id = this.nextId++;
    const message = JSON.stringify({ id, method, params });
    const promise = new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject });
    });
    this.ws.send(message);
    return promise;
  }

  async waitForEvent(method, timeoutMs = 10000) {
    const existingIndex = this.events.findIndex((event) => event.method === method);
    if (existingIndex >= 0) {
      const [event] = this.events.splice(existingIndex, 1);
      return event;
    }

    const deadline = Date.now() + timeoutMs;
    while (Date.now() < deadline) {
      const index = this.events.findIndex((event) => event.method === method);
      if (index >= 0) {
        const [event] = this.events.splice(index, 1);
        return event;
      }
      await new Promise((resolve) => setTimeout(resolve, 100));
    }

    throw new Error(`Timed out waiting for CDP event ${method}`);
  }

  close() {
    this.ws.close();
  }
}

async function createTab(url) {
  const response = await fetch(`http://127.0.0.1:${port}/json/new?${encodeURIComponent(url)}`, {
    method: "PUT",
  });
  if (!response.ok) {
    throw new Error(`Could not create Chrome tab: HTTP ${response.status}`);
  }
  return response.json();
}

async function navigate(client, url) {
  client.events = [];
  await client.send("Page.navigate", { url });
  await client.waitForEvent("Page.loadEventFired", 15000);
  await new Promise((resolve) => setTimeout(resolve, 800));
}

async function evaluate(client, expression) {
  return client.send("Runtime.evaluate", {
    expression,
    awaitPromise: true,
    returnByValue: true,
  });
}

async function discoverDetailRoute(client, listRoute, pattern, fallback) {
  await navigate(client, `${baseUrl}${listRoute}`);
  const result = await evaluate(client, `
    (() => {
      const pattern = new RegExp(${JSON.stringify(pattern)});
      const links = [...document.querySelectorAll('a[href]')].map((link) => link.getAttribute('href'));
      return links.find((href) => pattern.test(href)) || null;
    })()
  `);
  return result.result?.value || fallback;
}

async function screenshot(client, name) {
  const result = await client.send("Page.captureScreenshot", {
    format: "png",
    captureBeyondViewport: true,
    fromSurface: true,
  });
  await writeFile(path.join(outputDir, `${name}.png`), Buffer.from(result.data, "base64"));
  console.log(`Saved ${path.join(outputDir, `${name}.png`)}`);
}

async function main() {
  const browserPath = findBrowser();
  if (!browserPath) {
    throw new Error("Chrome or Edge was not found. Set BROWSER_PATH to a Chromium-based browser.");
  }

  await mkdir(outputDir, { recursive: true });
  await mkdir(".tmp", { recursive: true });

  const browser = spawn(browserPath, [
    "--headless=new",
    `--remote-debugging-port=${port}`,
    `--user-data-dir=${path.resolve(".tmp/screenshots-browser")}`,
    "--window-size=1440,1000",
    "--disable-gpu",
    "--no-first-run",
    "--hide-scrollbars",
    "about:blank",
  ], {
    stdio: "ignore",
  });

  try {
    await waitForJson(`http://127.0.0.1:${port}/json/version`);
    const tab = await createTab(`${baseUrl}/login/`);
    const client = new CdpClient(tab.webSocketDebuggerUrl);
    await client.open();
    await client.send("Page.enable");
    await client.send("Runtime.enable");
    await client.send("Emulation.setDeviceMetricsOverride", {
      width: 1440,
      height: 1000,
      deviceScaleFactor: 1,
      mobile: false,
    });

    await navigate(client, `${baseUrl}/login/`);
    await evaluate(client, `
      (() => {
        document.querySelector('input[name="username"], input[name="email"]').value = ${JSON.stringify(email)};
        document.querySelector('input[name="password"]').value = ${JSON.stringify(password)};
        document.querySelector('form').submit();
      })()
    `);
    await client.waitForEvent("Page.loadEventFired", 15000);
    await new Promise((resolve) => setTimeout(resolve, 1000));

    const documentRoute = process.env.SUPPORTFLOW_DOCUMENT_ID
      ? `/documents/${process.env.SUPPORTFLOW_DOCUMENT_ID}/`
      : await discoverDetailRoute(client, "/documents/", "^/documents/[0-9]+/?$", "/documents/");
    const conversationRoute = process.env.SUPPORTFLOW_CONVERSATION_ID
      ? `/chat/${process.env.SUPPORTFLOW_CONVERSATION_ID}/`
      : await discoverDetailRoute(client, "/chat/", "^/chat/[0-9]+/?$", "/chat/");
    const ticketRoute = process.env.SUPPORTFLOW_TICKET_ID
      ? `/tickets/${process.env.SUPPORTFLOW_TICKET_ID}/`
      : await discoverDetailRoute(client, "/tickets/", "^/tickets/[0-9]+/?$", "/tickets/");
    const evaluationRoute = process.env.SUPPORTFLOW_EVALUATION_ID
      ? `/evaluations/${process.env.SUPPORTFLOW_EVALUATION_ID}/`
      : await discoverDetailRoute(client, "/evaluations/", "^/evaluations/[0-9]+/?$", "/evaluations/");

    const routes = [
      ["dashboard", "/"],
      ["documents", "/documents/"],
      ["document-detail", documentRoute],
      ["chat", conversationRoute],
      ["ticket", ticketRoute],
      ["evaluation", evaluationRoute],
      ["api-docs", "/api/docs/"],
    ];

    for (const [name, route] of routes) {
      await navigate(client, `${baseUrl}${route}`);
      await screenshot(client, name);
    }

    client.close();
  } finally {
    browser.kill();
  }
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});

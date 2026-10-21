/* Only the capture tab created here is ever navigated, read, or closed. */
const BASE = "http://127.0.0.1:18739";
const HOSTS = new Set(["www.xiaohongshu.com", "xiaohongshu.com",
  "xhslink.cn", "www.xhslink.cn", "xhslink.com", "www.xhslink.com"]);
let running = false;
let status = "请先在抓取工具中开始任务";
let captureTab = null;

function allowedUrl(value) {
  const url = new URL(value);
  if (!["https:", "http:"].includes(url.protocol) || !HOSTS.has(url.hostname)) {
    throw new Error("Unsupported capture URL");
  }
  return value;
}

async function request(path, token, body, instance) {
  const response = await fetch(BASE + path, {
    method: body === undefined ? "GET" : "POST",
    credentials: "omit",
    cache: "no-store",
    signal: AbortSignal.timeout(5000),
    headers: {
      "X-URLHeat-Extension": chrome.runtime.id,
      ...(instance ? {"X-URLHeat-Instance": instance} : {}),
      ...(token ? {Authorization: "Bearer " + token} : {}),
      ...(body === undefined ? {} : {"Content-Type": "application/json"})
    },
    ...(body === undefined ? {} : {body: JSON.stringify(body)})
  });
  if (!response.ok) throw new Error("Bridge unavailable");
  return response.json();
}

async function closeOwnedTabs() {
  const {ownedTabs = []} = await chrome.storage.session.get("ownedTabs");
  for (const id of ownedTabs) {
    try { await chrome.tabs.remove(id); } catch (_) { /* Already closed. */ }
  }
  captureTab = null;
  await chrome.storage.session.set({ownedTabs: []});
}

// Runs in the matching XHS document. Never reads cookies or browser storage.
function snapshot(noteId) {
  const match = location.pathname.match(/^\/(?:explore|discovery\/item)\/([a-f0-9]{24})\/?$/i);
  const id = noteId || (match ? match[1] : "");
  const note = window.__INITIAL_STATE__?.note?.noteDetailMap?.[id]?.note;
  const root = document.querySelector("#noteContainer");
  const toolbar = root?.querySelector(".interact-container");
  const text = el => el ? (el.innerText || "").trim() : "";
  const visible = el => Boolean(el && el.getClientRects().length);
  const read = selector => text(toolbar?.querySelector(selector));
  const info = note?.interactInfo;
  return {
    url: location.href, title: document.title,
    text: text(document.body).slice(0, 120000),
    pendingNavigation: Boolean(window.__URLHEAT_NAVIGATING__),
    note: note?.noteId === id ? {noteId: id, interactInfo: {
      likedCount: info?.likedCount, commentCount: info?.commentCount,
      collectedCount: info?.collectedCount
    }} : null,
    content: visible(root?.querySelector(".note-content, .note-scroller")),
    errors: Array.from(document.querySelectorAll(".error-wrapper, .error-container, .error-page, .not-found-wrapper"))
      .filter(visible).map(text).join("\n"),
    domMetrics: [read(".like-wrapper .count"), read(".chat-wrapper .count"), read(".collect-wrapper .count")],
    logged: document.querySelector("#global")?.getAttribute("data-logged") === "1"
  };
}

async function handleCommand(command) {
  if (Date.now() >= command.deadline) throw new Error("Expired command");
  if (command.op === "open") {
    const url = allowedUrl(command.url);
    if (captureTab !== null) throw new Error("Capture already active");
    const window = await chrome.windows.getLastFocused({windowTypes: ["normal"]});
    if (window.incognito) throw new Error("Use a normal Chrome window");
    const tab = await chrome.tabs.create({windowId: window.id, url, active: false});
    captureTab = tab.id;
    await chrome.storage.session.set({ownedTabs: [captureTab]});
    return captureTab;
  }
  if (command.op === "close") {
    await closeOwnedTabs();
    return true;
  }
  if (captureTab === null) throw new Error("Capture tab unavailable");
  // A removed capture tab can never be replaced with the user's current tab.
  const tab = await chrome.tabs.get(captureTab);
  if (command.op === "navigate") {
    const url = allowedUrl(command.url);
    try {
      await chrome.scripting.executeScript({target: {tabId: captureTab}, world: "MAIN",
        func: () => { window.__URLHEAT_NAVIGATING__ = true; }});
    } catch (_) { /* Previous document may already be navigating. */ }
    await chrome.tabs.update(captureTab, {url});
    return true;
  }
  if (command.op === "snapshot") {
    if (!tab.url?.startsWith("https://www.xiaohongshu.com/")) {
      return {url: tab.url || "", pendingNavigation: true};
    }
    try {
      const results = await chrome.scripting.executeScript({target: {tabId: captureTab},
        world: "MAIN", func: snapshot, args: [command.noteId || ""]});
      return results[0]?.result || {pendingNavigation: true};
    } catch (_) {
      return {url: tab.url, pendingNavigation: true};
    }
  }
  throw new Error("Unsupported command");
}

async function connect() {
  if (running) return;
  running = true;
  status = "正在连接抓取工具";
  try {
    let {instance} = await chrome.storage.session.get("instance");
    if (!instance) {
      instance = crypto.randomUUID();
      await chrome.storage.session.set({instance});
    }
    const {token} = await request("/session", null, undefined, instance);
    await closeOwnedTabs();
    status = "已连接，正在后台抓取";
    while (true) {
      // An extension API call keeps the service worker alive during this task.
      await chrome.runtime.getPlatformInfo();
      const {command} = await request("/next", token);
      if (!command) {
        await new Promise(resolve => setTimeout(resolve, 500));
        continue;
      }
      let result;
      try { result = {id: command.id, value: await handleCommand(command)}; }
      catch (_) { result = {id: command.id, error: "Capture operation failed"}; }
      await request("/result", token, result);
    }
  } catch (_) {
    status = "尚未连接；请先在抓取工具中开始任务，再点连接";
  } finally {
    await closeOwnedTabs();
    running = false;
  }
}

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (sender.id !== chrome.runtime.id) return;
  if (message.action === "connect") void connect();
  sendResponse({status});
});
chrome.alarms.onAlarm.addListener(alarm => {
  if (alarm.name === "urlheat-connect") void connect();
});
function start() {
  chrome.alarms.create("urlheat-connect", {periodInMinutes: 0.5});
  void connect();
}
chrome.runtime.onInstalled.addListener(start);
chrome.runtime.onStartup.addListener(start);

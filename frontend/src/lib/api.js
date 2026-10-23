// One way to call the Python core: through the pywebview bridge in the app window, or through
// `markwise serve` when the interface runs in a browser during development.

let transport = null;

function waitForBridge(ms) {
  if (window.pywebview?.api) return Promise.resolve(true);
  return new Promise((resolve) => {
    const done = (found) => {
      clearTimeout(timer);
      resolve(found);
    };
    const timer = setTimeout(() => done(false), ms);
    window.addEventListener("pywebviewready", () => done(true), { once: true });
  });
}

function getTransport() {
  if (!transport) transport = waitForBridge(800).then((bridge) => (bridge ? "webview" : "http"));
  return transport;
}

export async function call(method, ...args) {
  let result;
  if ((await getTransport()) === "webview") {
    result = await window.pywebview.api[method](...args);
  } else {
    const response = await fetch(`/api/${method}`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Markwise": "1" },
      body: JSON.stringify({ args }),
    });
    if (!response.ok) throw new Error(`${method}: HTTP ${response.status}`);
    result = await response.json();
  }
  if (result && result.error) {
    const error = new Error(result.error);
    error.code = result.code ?? null;
    error.params = result.params ?? {};
    throw error;
  }
  return result?.data;
}

export function transportName() {
  return getTransport();
}

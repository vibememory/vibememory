import { spawn } from "node:child_process";

const MAX_BYTES = 64 * 1024;

export function sanitizedPayload({ sessionId, cwd, source = "startup", stopHookActive = false }) {
  return {
    session_id: String(sessionId || "unknown-session"),
    cwd: String(cwd),
    source,
    stop_hook_active: Boolean(stopHookActive),
  };
}

export function extractAdditionalContext(value) {
  const context = value?.hookSpecificOutput?.additionalContext;
  return typeof context === "string" ? context.trim() : "";
}

export function runCliHook(command, input, { cliPath = "vibe-memory", timeoutMs = 10_000 } = {}) {
  return new Promise((resolve) => {
    const child = spawn(cliPath, ["hook", command], {
      cwd: input.cwd,
      env: process.env,
      shell: false,
      stdio: ["pipe", "pipe", "pipe"],
    });
    const stdout = [];
    let size = 0;
    let settled = false;
    const finish = (value) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      resolve(value);
    };
    const timer = setTimeout(() => {
      child.kill("SIGKILL");
      finish(null);
    }, timeoutMs);
    child.stdout.on("data", (chunk) => {
      size += chunk.length;
      if (size > MAX_BYTES) child.kill("SIGKILL");
      else stdout.push(chunk);
    });
    child.stdin.on("error", () => finish(null));
    child.on("error", () => finish(null));
    child.on("close", (code) => {
      if (code !== 0 || size > MAX_BYTES || stdout.length === 0) return finish(null);
      try {
        const value = JSON.parse(Buffer.concat(stdout).toString("utf8"));
        finish(value && typeof value === "object" && !Array.isArray(value) ? value : null);
      } catch {
        finish(null);
      }
    });
    child.stdin.end(JSON.stringify(input));
  });
}

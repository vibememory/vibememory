import path from "node:path";
import { definePluginEntry } from "openclaw/plugin-sdk/plugin-entry";
import { extractAdditionalContext, runCliHook, sanitizedPayload } from "./bridge.mjs";

type Settings = {
  cliPath?: string;
  autoRecall?: boolean;
  autoCheckpoint?: boolean;
  projectRoots?: string[];
};

function isAllowed(cwd: string, roots: string[]) {
  if (roots.length === 0) return true;
  const resolved = path.resolve(cwd);
  return roots.some((root) => {
    const candidate = path.resolve(root);
    return resolved === candidate || resolved.startsWith(candidate + path.sep);
  });
}

function identity(event: any, ctx: any) {
  const cwd = path.resolve(ctx?.workspaceDir || event?.cwd || process.cwd());
  const sessionId = ctx?.sessionKey || event?.sessionKey || event?.sessionId || "unknown-session";
  return { cwd, sessionId: String(sessionId) };
}

export default definePluginEntry({
  id: "vibe-memory-hooks",
  name: "Vibe Memory Hooks",
  description: "Shared project recall and durable checkpoint guidance.",
  register(api) {
    const settings = (api.pluginConfig || {}) as Settings;
    const cliPath = settings.cliPath || "vibe-memory";
    const roots = Array.isArray(settings.projectRoots) ? settings.projectRoots : [];
    const recalled = new Set<string>();

    api.on("before_prompt_build", async (event, ctx) => {
      if (settings.autoRecall === false) return;
      const current = identity(event, ctx);
      if (!isAllowed(current.cwd, roots) || recalled.has(current.sessionId)) return;
      const output = await runCliHook(
        "session-start",
        sanitizedPayload({ ...current, source: "startup" }),
        { cliPath },
      );
      recalled.add(current.sessionId);
      const context = extractAdditionalContext(output);
      return context ? { prependContext: context } : undefined;
    }, { timeoutMs: 10_000 });

    api.on("before_agent_finalize", async (event, ctx) => {
      if (settings.autoCheckpoint === false) return;
      const current = identity(event, ctx);
      if (!isAllowed(current.cwd, roots)) return;
      const output = await runCliHook(
        "stop",
        sanitizedPayload({ ...current, stopHookActive: event.stopHookActive }),
        { cliPath },
      );
      const context = extractAdditionalContext(output);
      if (!context) return;
      return {
        action: "revise",
        reason: context,
        retry: {
          instruction: context,
          idempotencyKey: `vibe-memory-checkpoint:${ctx?.runId || current.sessionId}`,
          maxAttempts: 1,
        },
      };
    }, { timeoutMs: 10_000 });

    api.on("before_compaction", async (event, ctx) => {
      const current = identity(event, ctx);
      if (!isAllowed(current.cwd, roots)) return;
      await runCliHook("pre-compact", sanitizedPayload({ ...current, source: "compact" }), { cliPath });
      recalled.delete(current.sessionId);
    }, { timeoutMs: 5_000 });

    api.on("session_end", (event, ctx) => {
      recalled.delete(identity(event, ctx).sessionId);
    });
  },
});

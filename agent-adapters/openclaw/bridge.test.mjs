import assert from "node:assert/strict";
import { chmod, mkdtemp, readFile, writeFile } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import { extractAdditionalContext, runCliHook, sanitizedPayload } from "./bridge.mjs";

test("sanitizedPayload keeps only lifecycle identity", () => {
  assert.deepEqual(
    sanitizedPayload({
      sessionId: "session-1",
      cwd: "/tmp/project",
      source: "compact",
      stopHookActive: true,
      prompt: "secret prompt",
      messages: ["secret message"],
    }),
    {
      session_id: "session-1",
      cwd: "/tmp/project",
      source: "compact",
      stop_hook_active: true,
    },
  );
});

test("runCliHook uses a fixed argv and parses bounded JSON", async () => {
  const directory = await mkdtemp(path.join(os.tmpdir(), "vibe-memory-openclaw-"));
  const cli = path.join(directory, "fake-cli.mjs");
  const capture = path.join(directory, "capture.json");
  await writeFile(cli, `#!/usr/bin/env node
import { writeFileSync } from "node:fs";
let input = "";
for await (const chunk of process.stdin) input += chunk;
writeFileSync(process.env.FAKE_VIBE_MEMORY_CAPTURE, JSON.stringify({ args: process.argv.slice(2), input: JSON.parse(input) }));
console.log(JSON.stringify({ hookSpecificOutput: { additionalContext: "shared context" } }));
`);
  await chmod(cli, 0o755);
  process.env.FAKE_VIBE_MEMORY_CAPTURE = capture;
  const payload = sanitizedPayload({ sessionId: "session-2", cwd: directory });
  const result = await runCliHook("session-start", payload, { cliPath: cli });
  assert.equal(extractAdditionalContext(result), "shared context");
  const invoked = JSON.parse(await readFile(capture, "utf8"));
  assert.deepEqual(invoked.args, ["hook", "session-start"]);
  assert.deepEqual(invoked.input, payload);
});

test("runCliHook fails open when the CLI is missing", async () => {
  const result = await runCliHook(
    "stop",
    sanitizedPayload({ sessionId: "session-3", cwd: os.tmpdir() }),
    { cliPath: path.join(os.tmpdir(), "definitely-missing-vibe-memory") },
  );
  assert.equal(result, null);
});

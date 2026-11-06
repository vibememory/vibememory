import assert from 'node:assert/strict';
import test from 'node:test';

import { needsLegacySkillManifest } from '../src/worker.js';

test('legacy CLIs and compatibility bootstraps receive the v1 recovery manifest', () => {
  assert.equal(needsLegacySkillManifest('VibeMemoryCLI/3.9.1'), true);
  assert.equal(needsLegacySkillManifest('VibeMemoryCLI/3.10.0'), true);
  assert.equal(needsLegacySkillManifest('VibeMemoryBootstrap/3.0'), true);
});

test('progressive and unrelated clients keep the v2 manifest', () => {
  assert.equal(needsLegacySkillManifest('VibeMemoryCLI/3.11.0'), false);
  assert.equal(needsLegacySkillManifest('VibeMemoryCLI/3.12.1'), false);
  assert.equal(needsLegacySkillManifest('Mozilla/5.0'), false);
});

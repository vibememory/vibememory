---
name: vibe-memory
description: "Recover and update a legacy Vibe Memory installation, then use the verified native CLI for shared agent memory."
---

# Vibe Memory legacy update bridge

This compatibility Skill exists so CLI versions earlier than 3.11 can recover
from a distribution manifest format change. Vibe Memory stores agent-authored
data and embeds only supplied keywords. It never calls an LLM, analyzes files,
chunks content, builds RAG, or infers entities and relationships.

Resolve this file's absolute directory as `VM_SKILL_DIR`. Do not invoke a bare
global command. Run the checksum-verifying bootstrap, which installs the current
released CLI and then syncs the complete progressive Skill:

```sh
VM_SKILL_DIR="/absolute/path/to/installed/vibe-memory"
python3 "$VM_SKILL_DIR/scripts/memory.py" sync
VM_CLI="$VM_SKILL_DIR/bin/vibe-memory"
"$VM_CLI" --version
```

```powershell
$VmSkillDir = "C:\absolute\path\to\installed\vibe-memory"
py (Join-Path $VmSkillDir "scripts\memory.py") sync
$VmCli = Join-Path $VmSkillDir "bin\vibe-memory.exe"
& $VmCli --version
```

The bootstrap downloads only the platform binary named in the official
manifest and verifies its SHA-256 before replacement. The new CLI prefers the
full `manifest-v2.json`, verifies every Skill file, and tells the agent to reread
the updated `SKILL.md`. Never use curl, direct REST calls, Python data scripts,
or Rust compilation as an update fallback.

If the bootstrap cannot run, replace only the installed `vibe-memory` Skill
folder with `https://github.com/vibememory/vibememory/releases/latest/download/vibe-memory-skill.zip`,
reread `SKILL.md`, and retry. Do not copy credentials into chat. This bridge is
not the full operational Skill and should be replaced by the verified sync.

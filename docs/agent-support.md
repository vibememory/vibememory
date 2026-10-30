# 에이전트 지원 현황

> 이 문서는 `landing/data/agent-support.json`에서 생성됩니다. 직접 수정하지 마세요.

최종 검증: **2026-10-30T07:54:06Z** (UTC)
이 기능에 SSE 필요: **아니요**

| 에이전트 | Skill | MCP | Hook 불러오기 | Hook 체크포인트 | 상태 | 설치 |
| --- | --- | --- | --- | --- | --- | --- |
| Claude Code | 지원됨 | 지원됨 | 지원됨 | 지원됨 | 지원됨 | [가이드](https://vibememory.io/guide.html#claude-code-hooks) |
| OpenAI Codex | 지원됨 | 지원됨 | 지원됨 | 지원됨 | 지원됨 | [가이드](https://vibememory.io/guide.html#codex-hooks) |
| Cursor | 지원됨 | 지원됨 | 지원됨 | 지원됨 | 지원됨 | [가이드](https://vibememory.io/guide.html#cursor-hooks) |
| Muse Code | 지원됨 | 지원됨 | 지원됨 | 지원됨 | 지원됨 | [가이드](https://vibememory.io/guide.html#muse-hooks) |
| Hermes Agent | 지원됨 | 지원됨 | 지원됨 | 지원됨 | 지원됨 | [가이드](https://vibememory.io/guide.html#hermes-hooks) |
| OpenClaw | 지원됨 | 지원됨 | 지원됨 | 지원됨 | 지원됨 | [가이드](https://vibememory.io/guide.html#openclaw-hooks) |

## 세부 검증 정보

### Claude Code

- 최소 버전: 2.1.275
- 검증 기준: 2.1.275+ marketplace hook contract
- 실행 환경: Claude Code CLI on Linux, macOS, or Windows
- 이벤트 매핑: SessionStart → recall, Stop → checkpoint reminder, PreCompact → pending marker
- 제한사항: Install the marketplace plugin or the manual hooks, never both. The native CLI must be available on PATH and hooks remain fail-open.

### OpenAI Codex

- 최소 버전: 0.166.0
- 검증 기준: codex-cli 0.166.0
- 실행 환경: Codex CLI or desktop with local command execution
- 이벤트 매핑: SessionStart → recall, Stop → checkpoint reminder, PreCompact → pending marker
- 제한사항: The user must review and trust the hooks. Command hooks do not run in Work Cloud without local execution.

### Cursor

- 최소 버전: 1.7.0
- 검증 기준: Cursor 1.7+ official hooks contract + adapter tests
- 실행 환경: Cursor desktop or CLI with local command hooks and Python 3
- 이벤트 매핑: sessionStart → recall, stop → one bounded checkpoint follow-up, preCompact → pending marker
- 제한사항: Cursor uses its own lowercase events and response schema, so the translation adapter is required. stop loop_limit stays at 1; preCompact is observation-only.

### Muse Code

- 최소 버전: 1.3.0
- 검증 기준: Muse Code 1.3.0 official hook contract + manifest tests
- 실행 환경: Muse Code terminal or CI on Linux, macOS, or Windows
- 이벤트 매핑: SessionStart → recall, Stop → checkpoint reminder, PreCompact → pending marker
- 제한사항: Project hooks run only after workspace trust. Muse Code has no per-hook trust command; restart a session after edits and inspect startup diagnostics.

### Hermes Agent

- 최소 버전: 0.22.5 verified floor; earlier hook release not established
- 검증 기준: Hermes Agent 0.22.5 official contract + adapter tests
- 실행 환경: Hermes CLI, Gateway, Desktop, TUI, or dashboard chat
- 이벤트 매핑: pre_llm_call → recall/next-turn checkpoint, pre_verify → coding checkpoint, post_compaction → pending marker
- 제한사항: Shell hooks require first-use consent. Non-coding final turns may checkpoint on the next prompt because on_session_end is observation-only.

### OpenClaw

- 최소 버전: 2026.10.9
- 검증 기준: OpenClaw 2026.10.9 isolated runtime load + adapter tests
- 실행 환경: OpenClaw Gateway with native plugins enabled
- 이벤트 매핑: before_prompt_build → recall, before_agent_finalize → checkpoint revision, before_compaction → pending marker
- 제한사항: Conversation access and prompt injection must be explicitly allowed. A harness that does not emit before_agent_finalize cannot force the checkpoint pass.

## 상태 기준

- **지원됨**: 배포 어댑터와 회귀 테스트가 있으며 공식 확장 지점에 매핑됨.
- **개발 중**: 구현은 있으나 수용 테스트가 끝나지 않음.
- **예정**: 설계 또는 백로그만 존재함.
- **미지원**: 현재 제품 확장 지점으로 제공할 수 없음.
- **미검증**: 구현 또는 공식 계약을 현재 버전에서 확인하지 못함.

Hook은 대화 원문을 저장하지 않습니다. 연결된 에이전트가 현재 맥락에서 durable delta를 선별하고 기존 CLI/MCP 요청으로 저장합니다. 상세 설치·제거·복구는 [Agent lifecycle hooks](agent-hooks.md)를 참고하세요.

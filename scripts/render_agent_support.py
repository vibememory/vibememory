#!/usr/bin/env python3
"""Render the documentation support matrix from the landing's shared data."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "landing" / "data" / "agent-support.json"
TARGET = ROOT / "docs" / "agent-support.md"

STATUS = {
    "supported": "지원됨",
    "in_progress": "개발 중",
    "planned": "예정",
    "unsupported": "미지원",
    "unverified": "미검증",
}


def render(data: dict) -> str:
    lines = [
        "# 에이전트 지원 현황",
        "",
        "> 이 문서는 `landing/data/agent-support.json`에서 생성됩니다. 직접 수정하지 마세요.",
        "",
        f"최종 검증: **{data['verified_at']}** ({data['time_basis']})",
        f"이 기능에 SSE 필요: **{'예' if data['sse_required'] else '아니요'}**",
        "",
        "| 에이전트 | Skill | MCP | Hook 불러오기 | Hook 체크포인트 | 상태 | 설치 |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for agent in data["agents"]:
        capability = agent["capabilities"]
        installation_url = agent["installation_url"]
        if installation_url.startswith("/"):
            installation_url = f"https://vibememory.io{installation_url}"
        lines.append(
            "| {name} | {skill} | {mcp} | {recall} | {checkpoint} | {overall} | [가이드]({url}) |".format(
                name=agent["name"],
                skill=STATUS[capability["skill"]],
                mcp=STATUS[capability["mcp"]],
                recall=STATUS[capability["recall_hook"]],
                checkpoint=STATUS[capability["checkpoint_hook"]],
                overall=STATUS[agent["overall_status"]],
                url=installation_url,
            )
        )
    lines.extend(["", "## 세부 검증 정보", ""])
    for agent in data["agents"]:
        lines.extend(
            [
                f"### {agent['name']}",
                "",
                f"- 최소 버전: {agent['minimum_version']}",
                f"- 검증 기준: {agent['verified_version']}",
                f"- 실행 환경: {agent['environment']}",
                f"- 이벤트 매핑: {agent['hook_mapping']}",
                f"- 제한사항: {agent['limitations']}",
                "",
            ]
        )
    lines.extend(
        [
            "## 상태 기준",
            "",
            "- **지원됨**: 배포 어댑터와 회귀 테스트가 있으며 공식 확장 지점에 매핑됨.",
            "- **개발 중**: 구현은 있으나 수용 테스트가 끝나지 않음.",
            "- **예정**: 설계 또는 백로그만 존재함.",
            "- **미지원**: 현재 제품 확장 지점으로 제공할 수 없음.",
            "- **미검증**: 구현 또는 공식 계약을 현재 버전에서 확인하지 못함.",
            "",
            "Hook은 대화 원문을 저장하지 않습니다. 연결된 에이전트가 현재 맥락에서 durable delta를 선별하고 기존 CLI/MCP 요청으로 저장합니다. 상세 설치·제거·복구는 [Agent lifecycle hooks](agent-hooks.md)를 참고하세요.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    data = json.loads(SOURCE.read_text())
    output = render(data)
    if args.check:
        if not TARGET.exists() or TARGET.read_text() != output:
            raise SystemExit("docs/agent-support.md is not synchronized with agent-support.json")
        return 0
    TARGET.write_text(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

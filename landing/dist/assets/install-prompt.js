'use strict';
window.vibeMemoryInstallPrompt = function vibeMemoryInstallPrompt() {
  const base = location.origin;
  return `Vibe Memory를 이 에이전트에 설치하고 내 계정에 연결해줘.

서비스 URL: ${base}
Skill 다운로드: ${base}/downloads/vibe-memory-skill.zip
최신 지침: ${base}/skills/vibe-memory/SKILL.md

진행 방법:
1. 지금 로드된 기존 vibe-memory Skill의 지침이나 전역 vibe-memory 명령을 먼저 실행하지 마. 위 ZIP 최신판을 내려받아 기존에 설치된 vibe-memory Skill 폴더만 완전히 교체하고, 새 SKILL.md 전체를 다시 읽어. 다른 Skill이나 사용자 프로젝트 파일은 건드리지 마.
2. 새 SKILL.md가 있는 설치 폴더의 절대 경로를 구해. 현재 프로젝트 폴더로 추측하지 말고 전역 vibe-memory 명령도 사용하지 마. Linux/macOS에서는 VM_SKILL_DIR="설치된 vibe-memory 폴더의 절대 경로"를 작업 로컬 변수로 둔 뒤 MEMORY_URL="${base}" python3 "$VM_SKILL_DIR/scripts/memory.py" sync를 실행하고 VM_CLI="$VM_SKILL_DIR/bin/vibe-memory"를 사용해. Windows PowerShell에서는 $VmSkillDir에 그 절대 경로를 넣고 $env:MEMORY_URL="${base}"를 설정한 뒤 py (Join-Path $VmSkillDir "scripts\\memory.py") sync를 실행하고 $VmCli = Join-Path $VmSkillDir "bin\\vibe-memory.exe"로 사용해.
3. sync가 Skill을 갱신했다면 새 SKILL.md를 다시 읽어. 호환 설치기가 서비스 매니페스트의 현재 플랫폼용 Rust 바이너리를 내려받고 SHA-256을 검증하게 하며, 직접 컴파일하거나 curl·직접 API 호출로 우회하지 마.
4. 위 절대 경로의 Rust CLI로 브라우저 승인 연결을 login --url ${base} --vault-access --no-browser --name "현재 에이전트 이름"으로 시작해. 승인 화면에 기억 접근과 별도로 Vault 사용 권한이 표시되는지 확인하게 해.
5. 출력된 승인 URL과 확인 코드를 클릭 가능한 링크로 나에게 보여줘. 비밀번호나 API 키를 요청하거나 채팅에 노출하지 말고, 연결 프로세스를 유지한 채 내가 웹에서 승인할 때까지 기다려.
6. 승인 후 같은 절대 경로 CLI의 status로 연결을 확인해. 이후 작업부터 새 SKILL.md 지침에 따라 Vibe Memory를 적극 사용하고, API 요청을 직접 조립하지 말고 Rust CLI를 사용해.
7. 각 대화에서 관련 프로젝트 기억을 먼저 조회하고, 결정·수정·검증 완료·블로커·다음 작업이 바뀌면 전체 대화 대신 짧은 session checkpoint를 저장해. 인계, 컨텍스트 압축 또는 종료 전에는 아직 저장하지 않은 변경분을 체크포인트로 남기고, 이전 체크포인트와 달라진 내용이 없으면 중복 저장하지 마.
8. 서비스 비밀값은 채팅, 로컬 .env 또는 지속 환경변수로 복사하지 마. 필요한 경우 vault list로 이름만 확인하고 vault exec로 해당 프로세스에만 일시 전달하며, 비밀값 자체를 출력하거나 로그에 남기지 마.`;
};

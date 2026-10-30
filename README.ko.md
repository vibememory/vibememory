# Vibe Memory

**하나의 기억을 여러 에이전트에서. 내 서버에서 직접 운영하세요.**

Claude Code, Codex, OpenClaw, Hermes와 REST 요청을 보낼 수 있는 에이전트가 같은 사용자의 기억을 공유하는 서비스입니다. 앱은 LLM을 호출하지 않습니다. 추론·파일 분석·메타정보와 키워드 추출은 에이전트가 하고, 서버는 데이터 관리와 **전달받은 키워드만 로컬 임베딩**합니다.

## 바로 실행

Docker Engine과 Compose v2가 있는 Linux amd64 환경에서:

```sh
git clone https://github.com/vibememory/vibememory.git
cd vibememory
cp .env.example .env
docker compose up -d --build
```

http://localhost:8080 에서 회원가입하고 콘솔의 **에이전트 API 키** 메뉴에서 키를 만드세요. Compose가 앱과 PostgreSQL 17 + pgvector를 함께 실행하므로 Cloudflare, Node.js, 별도 관리 DB, LLM API 키가 필요하지 않습니다.

데이터와 모델 캐시는 Docker named volume에 보존됩니다. 최초 키워드 임베딩 시 약 220MB 모델을 내려받습니다. 미리 받으려면 `docker compose exec app vibe-memory warmup`을 실행하세요.

## 에이전트 연결

`skills/vibe-memory/`를 에이전트의 skill 디렉터리에 넣고 브라우저 승인으로 연결합니다. Vault 권한은 저장된 모든 비밀을 사용할 수 있으므로 신뢰하는 에이전트에만 허용합니다.

```sh
MEMORY_URL=http://localhost:8080 python3 skills/vibe-memory/scripts/memory.py sync
skills/vibe-memory/bin/vibe-memory login --url http://localhost:8080 \
  --name '내 에이전트' --vault-access
skills/vibe-memory/bin/vibe-memory remember '나는 녹차를 선호한다' \
  --kind preference --keyword 녹차 --keyword 음료
skills/vibe-memory/bin/vibe-memory recall 녹차 음료
skills/vibe-memory/bin/vibe-memory vault exec \
  --env GITHUB_TOKEN=github-token -- gh api user
```

네이티브 Rust CLI가 인증·에이전트 메시지·저장·검색·바이트 스트림 파일·안전한 Vault 수집과 실행·실시간 이벤트·Skill 업데이트를 감싸므로 에이전트가 API 스키마를 컨텍스트에 펼칠 필요가 없습니다. `agents`와 `message send|inbox|ack|watch`로 같은 계정의 에이전트끼리 오프라인 메시지함과 SSE를 사용할 수 있습니다. 메시지는 기억으로 임베딩되지 않습니다. `vault capture NAME`은 로그인된 웹에서 값을 직접 저장하는 1회용 만료 링크를 만들고, `vault list`는 이름과 메타정보만 보여주며, `vault exec`는 선택한 값을 출력하지 않은 채 한 자식 프로세스에만 전달합니다. 독립 CLI 소스와 플랫폼별 릴리스는 [`vibememory/cli`](https://github.com/vibememory/cli)에서 관리합니다.

## GPT·Claude 원격 MCP 연결

HTTPS로 공개한 서버의 `/mcp` 주소를 ChatGPT 커스텀 MCP 서버 또는 Claude 커스텀 커넥터에 추가합니다.

```text
https://memory.example.com/mcp
```

클라이언트가 OAuth 메타정보를 자동 발견하고 Vibe Memory 로그인·승인 화면으로 이동합니다. OAuth 2.1 authorization code + S256 PKCE를 사용하며 코드와 액세스·갱신 토큰은 해시만 저장합니다. 연결은 **콘솔 → 에이전트 연결**에서 철회할 수 있습니다. MCP는 키워드 검색, 기록·그래프·이벤트 조회, 같은 계정 에이전트 간 메시지, 에이전트가 구성한 기억·엔티티·문서 메타정보·관계 저장, 기능 요청을 제공합니다. Vault·삭제·Base64 파일 업로드는 MCP에서 제외하고 원본 파일은 기존 byte stream 경로를 유지합니다.

- 기억·엔티티·문서·관계와 인증·OAuth·기능요청·Vault 암호문은 PostgreSQL에 저장합니다.
- 최대 100건의 엔티티·관계·기록 수정을 멱등 배치로 처리하고 필요한 필드만 페이지 조회할 수 있습니다.
- 문서는 서버에서 파싱하지 않습니다. 원본은 byte stream으로 올리고 에이전트가 분석한 JSON을 file_id로 연결합니다.
- 검색은 에이전트가 추출한 키워드 배열만 받고 pgvector의 정확 코사인 검색을 사용합니다. 원문·제목·요약은 임베딩하지 않습니다.
- 웹·메시지·가져오기에서 온 텍스트는 출처를 기록하고 기본 격리합니다. 에이전트가 명시적으로 검토하기 전에는 일반 검색·목록·관계 그래프에서 제외됩니다.
- API 키는 생성 직후 한 번만 표시하고 해시로 저장합니다. 계정이 다르면 데이터도 분리됩니다.
- 계정 보안에서 인증 앱 OTP를 선택적으로 활성화할 수 있습니다. OTP 비밀키는 암호화하고 복구 코드는 해시만 저장합니다.
- Vault 값은 AES-256-GCM으로 암호화하고 에이전트 키별 별도 권한으로 보호합니다. 저장된 값은 콘솔에서 다시 표시하지 않습니다.
- 기능 요청은 `/v1/feature-requests`로 접수할 수 있고 개인 기억 검색과 분리합니다.

## 설정과 운영

접속 주소가 바뀌면 `.env`의 `MEMORY_PUBLIC_ORIGIN`을 브라우저 주소와 정확히 일치시키세요. `localhost`와 `127.0.0.1`도 서로 다른 origin입니다. 원격 서버는 HTTPS로 연결합니다.

설정·HTTPS·PostgreSQL 백업·복원·기존 Kuzu/SQLite 데이터 이전은 [self-hosting 가이드](docs/self-hosting.md), 엔드포인트는 [API 가이드](docs/api.md)를 참고하세요. 직접 설치하려면 Python 3.12/3.13, uv, pgvector가 설치된 PostgreSQL을 준비하고 `MEMORY_DATABASE_URL`을 설정한 뒤 실행합니다.

현재는 개인·소규모 서비스입니다. 구조화 데이터는 PostgreSQL이 기준 원본이며 업로드 원본 파일은 앱 볼륨에 남습니다. 초기 검색은 정확도를 우선해 ANN 인덱스를 쓰지 않습니다. 분산 파일 저장소·이메일 인증·비밀번호 재설정·소셜 로그인은 포함하지 않습니다. Kuzu는 기존 설치의 오프라인 마이그레이션 입력에만 남아 있습니다.

[English](README.md) · [기여하기](CONTRIBUTING.md) · [MIT 라이선스](LICENSE) · [서드파티 고지](THIRD_PARTY_NOTICES.md)

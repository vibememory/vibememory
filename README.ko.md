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

http://localhost:8080 에서 회원가입하고 콘솔의 **에이전트 API 키** 메뉴에서 키를 만드세요. 웹 화면·로그인·콘솔·API가 하나의 컨테이너에서 실행됩니다. Cloudflare, Node.js, 외부 DB, LLM API 키가 필요하지 않습니다.

데이터와 모델 캐시는 Docker named volume에 보존됩니다. 최초 키워드 임베딩 시 약 220MB 모델을 내려받습니다. 미리 받으려면 `docker compose exec app vibe-memory warmup`을 실행하세요.

## 에이전트 연결

`skills/vibe-memory/`를 에이전트의 skill 디렉터리에 넣고 콘솔에서 발급한 키를 설정합니다.

```sh
export MEMORY_URL=http://localhost:8080
export MEMORY_API_KEY='콘솔에서-발급한-키'
python3 skills/vibe-memory/scripts/memory.py remember '나는 녹차를 선호한다' \
  --kind preference --keyword 녹차 --keyword 음료
python3 skills/vibe-memory/scripts/memory.py recall 녹차 음료
```

- 기억·엔티티·문서·관계는 그래프 DB에 저장합니다.
- 문서는 서버에서 파싱하지 않습니다. 원본은 byte stream으로 올리고 에이전트가 분석한 JSON을 file_id로 연결합니다.
- 검색은 에이전트가 추출한 키워드 배열만 받습니다. 원문·제목·요약은 임베딩하지 않습니다.
- API 키는 생성 직후 한 번만 표시하고 해시로 저장합니다. 계정이 다르면 데이터도 분리됩니다.
- 기능 요청은 `/v1/feature-requests`로 접수할 수 있고 개인 기억 검색과 분리합니다.

## 설정과 운영

접속 주소가 바뀌면 `.env`의 `MEMORY_PUBLIC_ORIGIN`을 브라우저 주소와 정확히 일치시키세요. `localhost`와 `127.0.0.1`도 서로 다른 origin입니다. 원격 서버는 HTTPS로 연결합니다.

설정·HTTPS·백업·복원·업데이트는 [self-hosting 가이드](docs/self-hosting.md), 엔드포인트는 [API 가이드](docs/api.md)를 참고하세요. 직접 설치하려면 Python 3.12/3.13과 uv를 준비하고 `uv sync --frozen`, `uv run vibe-memory serve`를 실행합니다.

현재는 단일 프로세스의 개인·소규모 서비스입니다. 다중 워커·분산 DB·ANN 인덱스·이메일 인증·비밀번호 재설정·소셜 로그인은 포함하지 않습니다. Kuzu upstream이 보관 상태이므로 장기 운영 시 DB 유지보수 계획을 고려해야 합니다.

[English](README.md) · [기여하기](CONTRIBUTING.md) · [MIT 라이선스](LICENSE) · [서드파티 고지](THIRD_PARTY_NOTICES.md)

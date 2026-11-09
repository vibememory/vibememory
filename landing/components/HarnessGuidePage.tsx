import guides from "@/data/harness-guides.json";
import { HarnessGuideActions } from "@/components/HarnessGuideActions";
import { PublicHeaderControls } from "@/components/PublicHeaderControls";

export type HarnessGuide = (typeof guides.guides)[number];

function UiIcon({ name }: { name: string }) {
  return <svg className="svg-icon" aria-hidden="true"><use href={`/assets/icons.svg#${name}`} /></svg>;
}

function CommandBlock({ commands }: { commands: readonly string[] }) {
  return <pre><code>{commands.join("\n")}</code></pre>;
}

export function findHarnessGuide(slug: string) {
  return guides.guides.find((guide) => guide.slug === slug);
}

export function HarnessGuidePage({ guide }: { guide: HarnessGuide }) {
  return (
    <>
      <link rel="stylesheet" href="/assets/guide.css?v=20261109-v039-3" />
      <link rel="stylesheet" href="/assets/harness-guide.css?v=20261109-v039-3" />
      <a className="skip" href="#main">본문으로 바로가기</a>
      <header className="header wrap">
        <a href="/" className="brand" aria-label="Vibe Memory home">
          <svg viewBox="0 0 32 32" aria-hidden="true"><path d="m7 9 9-4 9 8-6 13-13-6L7 9Zm0 0 12 17M16 5 6 20l19-7"/><circle cx="7" cy="9" r="3"/><circle cx="16" cy="5" r="3"/><circle cx="25" cy="13" r="3"/><circle cx="19" cy="26" r="3"/><circle cx="6" cy="20" r="3"/></svg>
          <span>vibe<span className="brand-light">memory</span></span>
        </a>
        <div className="header-actions public-header-actions">
          <PublicHeaderControls />
          <a className="nav-cta" href="/guide/harnesses">모든 제품 가이드 <UiIcon name="arrow-right" /></a>
        </div>
      </header>
      <main className="harness-guide wrap" id="main">
        <nav className="harness-breadcrumb" aria-label="Breadcrumb">
          <a href="/guide">연결 가이드</a><UiIcon name="arrow-right" /><a href="/guide/harnesses">하네스</a><UiIcon name="arrow-right" /><span>{guide.name}</span>
        </nav>

        <section className="harness-hero">
          <div className="harness-hero-copy">
            <div className="harness-product-heading">
              <span className={`harness-product-icon is-large ${["codex", "cursor", "hermes"].includes(guide.id) ? "is-dark" : ""}`}><img src={guide.icon} alt="" width="40" height="40" /></span>
              <div><p className="eyebrow">VIBE MEMORY × AGENT HARNESS</p><span className="support-status is-supported"><UiIcon name="check" /> 지원됨</span></div>
            </div>
            <h1>{guide.name}<br />연결 가이드</h1>
            <p>{guide.summary}</p>
            <HarnessGuideActions name={guide.name} slug={guide.slug} />
          </div>
          <aside className="harness-facts" aria-label={`${guide.name} 지원 정보`}>
            <p className="eyebrow">VERIFIED · UTC {guides.verified_at.slice(0, 10)}</p>
            <dl>
              <div><dt>최소 버전</dt><dd>{guide.minimum_version}</dd></div>
              <div><dt>검증 환경</dt><dd>{guide.environment}</dd></div>
              <div><dt>연결 방식</dt><dd>{guide.install_method}</dd></div>
              <div><dt>SSE 필요</dt><dd>아니요</dd></div>
            </dl>
          </aside>
        </section>

        <section className="harness-layers" aria-labelledby="harness-layers-title">
          <div className="harness-section-heading"><p className="eyebrow">THREE CONNECTION LAYERS</p><h2 id="harness-layers-title">각 연결은 역할이 다릅니다.</h2></div>
          <div className="harness-layer-grid">
            <article><span>01</span><h3>Skill</h3><p>언제 기억을 찾고 무엇을 저장할지 에이전트에 알려주는 작업 지침입니다.</p></article>
            <article><span>02</span><h3>Remote MCP</h3><p>OAuth 웹 승인으로 기억, 문서 메타정보, 관계와 메시지 도구를 제공합니다.</p></article>
            <article><span>03</span><h3>Lifecycle Hook</h3><p>세션 시작, 종료와 압축 시점에 CLI를 호출하는 로컬 자동화입니다.</p></article>
          </div>
        </section>

        <div className="harness-body">
          <aside className="harness-toc">
            <p className="eyebrow">ON THIS PAGE</p>
            <a href="#prepare">01 · 설치 준비</a>
            <a href="#skill">02 · Skill과 CLI</a>
            <a href="#mcp">03 · 원격 MCP</a>
            <a href="#hooks">04 · 자동 Hook</a>
            <a href="#verify">05 · 검증</a>
            <a href="#manage">업데이트와 제거</a>
            <a href="#limits">제약과 보안</a>
          </aside>
          <article className="harness-content">
            <section id="prepare">
              <p className="harness-step">STEP 01</p><h2>설치 준비</h2>
              <p>현재 제품과 버전을 먼저 확인하고, 이 페이지의 설정만 적용하세요. 기존 설정 파일을 통째로 교체하지 말고 Vibe Memory 항목의 diff를 검토합니다.</p>
              <div className="harness-note"><UiIcon name="info" /><span>{guide.install_note}</span></div>
            </section>
            <section id="skill">
              <p className="harness-step">STEP 02</p><h2>Skill과 CLI 연결</h2>
              <p>콘솔의 설치 프롬프트 또는 Skill ZIP으로 최신 지침을 설치합니다. CLI 인증은 브라우저 승인 링크로 진행하며 API 키를 채팅에 붙여넣지 않습니다.</p>
              <CommandBlock commands={guide.install_commands} />
              <CommandBlock commands={[
                'VM_SKILL_DIR="/absolute/path/to/installed/vibe-memory"',
                'MEMORY_URL=https://vibememory.io python3 "$VM_SKILL_DIR/scripts/memory.py" sync',
                '"$VM_SKILL_DIR/bin/vibe-memory" login --url https://vibememory.io --no-browser --name "' + guide.name + '"'
              ]} />
            </section>
            <section id="mcp">
              <p className="harness-step">STEP 03</p><h2>원격 MCP 연결</h2>
              <p>원격 MCP는 Skill이나 Hook과 독립적으로 사용할 수 있습니다. 연결 시 Vibe Memory 로그인과 권한 승인 화면에서 요청된 범위를 직접 확인합니다.</p>
              <CommandBlock commands={guide.mcp_commands} />
            </section>
            <section id="hooks">
              <p className="harness-step">STEP 04</p><h2>자동 Hook 설치</h2>
              <p>Hook은 로컬에서 프로젝트명과 Git 상태 지문만 CLI에 전달합니다. 대화 원문, 모델 응답, 파일 내용, 환경변수와 Vault 값은 전달하지 않습니다.</p>
              <div className="harness-config-paths"><span>어댑터</span><code>{guide.hook_adapter}</code><span>설정 위치</span><div>{guide.config_paths.map((path) => <code key={path}>{path}</code>)}</div></div>
              <div className="harness-event-map">
                {guide.events.map((event) => <div key={event.host}><code>{event.host}</code><UiIcon name="arrow-right" /><span>{event.vibe_memory}</span></div>)}
              </div>
            </section>
            <section id="verify">
              <p className="harness-step">STEP 05</p><h2>검증</h2>
              <p>설치 완료 메시지만 믿지 말고 제품 자체의 목록, 진단 또는 설정 화면에서 실제 로드를 확인합니다.</p>
              <CommandBlock commands={guide.verify_commands} />
            </section>
            <section id="manage">
              <h2>업데이트와 제거</h2>
              <div className="harness-manage-grid">
                <div><h3>업데이트</h3><CommandBlock commands={guide.update_commands} /></div>
                <div><h3>제거</h3><CommandBlock commands={guide.uninstall_commands} /></div>
              </div>
            </section>
            <section id="limits">
              <h2>제약과 보안 경계</h2>
              <div className="harness-warning"><UiIcon name="alert" /><p>{guide.limitation}</p></div>
              <p>Vibe Memory 서버는 저장, 조회, 권한과 결정론적 데이터 관리를 담당합니다. 파일 분석, 키워드 추출, 엔티티·관계 추론과 실제 외부 작업은 이 에이전트가 수행합니다.</p>
              <div className="harness-official-links">
                <strong>공식 문서</strong>
                {guide.official_docs.map((document) => <a href={document.url} target="_blank" rel="noopener" key={document.url}>{document.label}<UiIcon name="external-link" /></a>)}
                <a href="https://github.com/vibememory/vibememory/blob/main/docs/agent-hooks.md" target="_blank" rel="noopener">Vibe Memory Hook reference<UiIcon name="external-link" /></a>
              </div>
            </section>
          </article>
        </div>
        <nav className="harness-next-guides" aria-label="다른 제품 가이드">
          <span>다른 제품 가이드</span>
          <div>{guides.guides.filter((item) => item.id !== guide.id).map((item) => <a href={`/guide/${item.slug}`} key={item.id}><img src={item.icon} alt="" width="18" height="18" />{item.name}</a>)}</div>
        </nav>
      </main>
    </>
  );
}

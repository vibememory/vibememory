import guides from "@/data/chat-guides.json";
import { ChatGuideActions } from "@/components/ChatGuideActions";
import { PublicHeaderControls } from "@/components/PublicHeaderControls";

export type ChatGuide = (typeof guides.guides)[number];

function UiIcon({ name }: { name: string }) {
  return <svg className="svg-icon" aria-hidden="true"><use href={`/assets/icons.svg#${name}`} /></svg>;
}

export function findChatGuide(slug: string) {
  return guides.guides.find((guide) => guide.slug === slug);
}

export function ChatGuidePage({ guide }: { guide: ChatGuide }) {
  const securityDescription = `Vibe Memory는 저장·조회와 권한 관리를 담당합니다. 답변 생성, 키워드 추출, 엔티티·관계 판단은 ${guide.name}가 수행합니다. Vault는 별도 승인된 항목만 조회할 수 있습니다.`;
  return (
    <>
      <link rel="stylesheet" href="/assets/guide.css?v=20261109-v039-4" />
      <link rel="stylesheet" href="/assets/chat-guide.css?v=20261109-v039-4" />
      <a className="skip" href="#main">본문으로 바로가기</a>
      <header className="header wrap chat-public-header">
        <a href="/" className="brand" aria-label="Vibe Memory home">
          <svg viewBox="0 0 32 32" aria-hidden="true"><path d="m7 9 9-4 9 8-6 13-13-6L7 9Zm0 0 12 17M16 5 6 20l19-7"/><circle cx="7" cy="9" r="3"/><circle cx="16" cy="5" r="3"/><circle cx="25" cy="13" r="3"/><circle cx="19" cy="26" r="3"/><circle cx="6" cy="20" r="3"/></svg>
          <span>vibe<span className="brand-light">memory</span></span>
        </a>
        <div className="header-actions public-header-actions"><PublicHeaderControls /><a className="nav-cta" href="/guide/chat">일반 채팅 가이드 <UiIcon name="arrow-right" /></a></div>
      </header>
      <main className="chat-guide wrap" id="main">
        <nav className="harness-breadcrumb" aria-label="Breadcrumb"><a href="/guide">연결 가이드</a><UiIcon name="arrow-right" /><a href="/guide/chat">일반 채팅</a><UiIcon name="arrow-right" /><span>{guide.name}</span></nav>
        <section className="chat-guide-hero">
          <div className="chat-guide-hero-copy">
            <div className="chat-product-heading"><span className={`harness-product-icon is-large ${guide.id === "chatgpt" ? "is-dark" : ""}`}><img src={guide.icon} alt="" width="40" height="40" /></span><div><p className="eyebrow">VIBE MEMORY × GENERAL CHAT</p><span className="support-status is-supported"><UiIcon name="check" /> 지원됨</span></div></div>
            <h1>{guide.name}<br />일반 채팅 가이드</h1>
            <p>{guide.summary}</p>
            <ChatGuideActions product={guide.name} connectUrl={guide.connect_url} />
          </div>
          <aside className="chat-guide-facts">
            <p className="eyebrow">VERIFIED · UTC {guides.verified_at.slice(0, 10)}</p>
            <dl><div><dt>사용 화면</dt><dd>{guide.surfaces}</dd></div><div><dt>연결 형태</dt><dd>{guide.connection_type}</dd></div><div><dt>로컬 설치</dt><dd>필요 없음</dd></div><div><dt>자동 Hook</dt><dd>일반 채팅 미지원</dd></div></dl>
          </aside>
        </section>

        <section className="chat-guide-steps" aria-labelledby="chat-steps-title">
          <div className="chat-section-heading"><p className="eyebrow">CONNECT IN FOUR STEPS</p><h2 id="chat-steps-title">터미널 없이, 대화 화면에서 연결합니다.</h2><p>API 키를 복사하지 않고 웹 로그인과 OAuth 승인으로 연결합니다.</p></div>
          <div className="chat-step-grid">{guide.steps.map((step, index) => <article key={step.title}><span>0{index + 1}</span><h3>{step.title}</h3><p>{step.body}</p></article>)}</div>
        </section>

        <section className="chat-capability-section">
          <div className="chat-section-heading"><p className="eyebrow">CAPABILITY BOUNDARY</p><h2>가능한 것과 자동화되지 않는 것</h2></div>
          <div className="chat-capability-grid">
            <article className="is-works"><div><UiIcon name="check" /><h3>일반 채팅에서 가능</h3></div><ul>{guide.works.map((item) => <li key={item}>{item}</li>)}</ul></article>
            <article className="is-limits"><div><UiIcon name="alert" /><h3>일반 채팅의 제한</h3></div><ul>{guide.limits.map((item) => <li key={item}>{item}</li>)}</ul></article>
          </div>
        </section>

        <section className="chat-starter-section">
          <div className="chat-section-heading"><p className="eyebrow">FIRST CONVERSATION</p><h2>첫 대화에서 이렇게 요청하세요.</h2><p>Hook이 없는 일반 채팅에서도 기억 조회와 체크포인트 저장을 자연스럽게 유도하는 시작 지침입니다.</p></div>
          <blockquote>{guide.starter_prompt}</blockquote>
          <ChatGuideActions product={guide.name} connectUrl={guide.connect_url} />
          <div className="chat-verify"><strong>연결 검증 문장</strong>{guide.verify_prompts.map((prompt) => <span key={prompt}>{prompt}</span>)}</div>
        </section>

        <section className="chat-security-section">
          <div><p className="eyebrow">PERMISSIONS & RECOVERY</p><h2>권한은 연결별로 검토하고 철회하세요.</h2><p>{securityDescription}</p></div>
          <div className="chat-remove-card"><strong>연결 제거</strong><ol>{guide.remove_steps.map((step) => <li key={step}>{step}</li>)}</ol></div>
        </section>

        <footer className="chat-guide-footer">
          <a href={guide.coding_guide}><span>코딩 에이전트가 필요하다면</span><strong>{guide.coding_label}</strong><UiIcon name="arrow-right" /></a>
          <div><strong>공식 문서</strong>{guide.official_docs.map((doc) => <a href={doc.url} target="_blank" rel="noopener" key={doc.url}>{doc.label}<UiIcon name="external-link" /></a>)}</div>
        </footer>
      </main>
    </>
  );
}

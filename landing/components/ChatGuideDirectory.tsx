import guides from "@/data/chat-guides.json";

function UiIcon({ name }: { name: string }) {
  return <svg className="svg-icon" aria-hidden="true"><use href={`/assets/icons.svg#${name}`} /></svg>;
}

export function ChatGuideDirectory() {
  return (
    <section className="chat-directory" aria-labelledby="chat-directory-title">
      <div className="chat-directory-heading"><div><p className="eyebrow">GENERAL CHAT GUIDES · UTC {guides.verified_at.slice(0, 10)}</p><h1 id="chat-directory-title">코딩 모드가 아니어도,<br />기억을 이어가세요.</h1></div><p>터미널과 Hook 없이 ChatGPT 또는 Claude의 일반 대화에서 원격 MCP로 기억을 찾고 저장하는 방법을 안내합니다.</p></div>
      <div className="chat-directory-grid">{guides.guides.map((guide) => <a href={`/guide/${guide.slug}`} className={`chat-directory-card is-${guide.id}`} key={guide.id}><div className="chat-directory-card-top"><span className={`harness-product-icon ${guide.id === "chatgpt" ? "is-dark" : ""}`}><img src={guide.icon} alt="" width="30" height="30" /></span><span className="support-status is-supported"><UiIcon name="check" /> 지원됨</span></div><h2>{guide.name}</h2><p>{guide.summary}</p><dl><div><dt>사용 화면</dt><dd>{guide.surfaces}</dd></div><div><dt>연결 형태</dt><dd>{guide.connection_type}</dd></div></dl><span>일반 채팅 가이드 열기 <UiIcon name="arrow-right" /></span></a>)}</div>
      <div className="chat-directory-note"><UiIcon name="info" /><p><strong>일반 채팅에는 세션 Hook이 없습니다.</strong> 설치한 Plugin 또는 Connector를 대화에서 활성화하고, 시작 프롬프트로 필요한 순간에 기억을 검색·저장하도록 유도합니다.</p></div>
    </section>
  );
}

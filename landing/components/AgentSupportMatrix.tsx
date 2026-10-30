import support from "@/data/agent-support.json";

const labels = {
  skill: "Skill",
  mcp: "MCP",
  recall_hook: "자동 불러오기",
  checkpoint_hook: "체크포인트",
} as const;

const statusLabels: Record<string, string> = {
  supported: "지원됨",
  in_progress: "개발 중",
  planned: "예정",
  unsupported: "미지원",
  unverified: "미검증",
};

function UiIcon({ name, className = "" }: { name: string; className?: string }) {
  return <svg className={`svg-icon ${className}`} aria-hidden="true"><use href={`/assets/icons.svg#${name}`} /></svg>;
}

export function AgentSupportMatrix() {
  return (
    <section className="agent-support-section section wrap" id="agent-support">
      <div className="agent-support-heading">
        <div>
          <p className="eyebrow">VERIFIED AGENT SUPPORT · UTC {support.verified_at.slice(0, 10)}</p>
          <h2>어디까지 자동으로<br />이어지는지, 정확하게.</h2>
        </div>
        <p>공식 생명주기 확장점과 배포 어댑터를 기준으로 표시합니다.<br />이 연동에 SSE 연결은 필요하지 않습니다.</p>
      </div>
      <div className="agent-support-grid">
        {support.agents.map((agent) => (
          <article className="agent-support-card" key={agent.id}>
            <div className="agent-support-card-top">
              <span className={`agent-support-icon ${agent.id === "codex" || agent.id === "hermes" ? "is-dark" : ""}`}>
                <img src={agent.icon} alt="" width="28" height="28" />
              </span>
              <div><h3>{agent.name}</h3><span className={`support-status is-${agent.overall_status}`}>{statusLabels[agent.overall_status]}</span></div>
            </div>
            <dl className="agent-capabilities">
              {Object.entries(labels).map(([key, label]) => {
                const status = agent.capabilities[key as keyof typeof labels];
                return <div key={key}><dt>{label}</dt><dd className={`is-${status}`}><UiIcon name={status === "supported" ? "check" : "alert"} />{statusLabels[status]}</dd></div>;
              })}
            </dl>
            <p className="agent-hook-map">{agent.hook_mapping}</p>
            <div className="agent-support-meta"><span>{agent.verified_version}</span><span>{agent.environment}</span></div>
            <a href={agent.installation_url}>설치·제한사항 보기 <UiIcon name="arrow-right" /></a>
          </article>
        ))}
      </div>
    </section>
  );
}

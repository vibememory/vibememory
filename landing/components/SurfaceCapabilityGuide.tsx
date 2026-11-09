import support from "@/data/surface-support.json";

const statusLabels: Record<string, string> = {
  supported: "지원됨",
  limited: "제한됨",
  unsupported: "미지원",
};

function UiIcon({ name }: { name: string }) {
  return <svg className="svg-icon" aria-hidden="true"><use href={`/assets/icons.svg#${name}`} /></svg>;
}

export function SurfaceCapabilityGuide({ compact = false }: { compact?: boolean }) {
  return (
    <section className={`surface-support-section${compact ? " is-compact" : " section wrap"}`} id="surface-support">
      <div className="surface-support-heading">
        <div>
          <p className="eyebrow">CHOOSE YOUR AI SURFACE · UTC {support.verified_at.slice(0, 10)}</p>
          <h2>같은 AI라도,<br />연결 범위는 다릅니다.</h2>
        </div>
        <p>사용 중인 화면을 먼저 고르세요. 가능한 기능과 호스트가 제공하지 않는 기능을 구분해 가장 짧은 설치 경로를 안내합니다.</p>
      </div>
      <div className="surface-provider-list">
        {support.providers.map((provider) => (
          <section className={`surface-provider is-${provider.id}`} key={provider.id} aria-labelledby={`surface-provider-${provider.id}`}>
            <header className="surface-provider-heading">
              <div>
                <span className="surface-provider-mark" aria-hidden="true">
                  <img src={provider.id === "openai" ? "/assets/brands/codex.png" : "/assets/brands/claude-code.png"} alt="" width="28" height="28" />
                </span>
                <div><span>PLATFORM</span><h3 id={`surface-provider-${provider.id}`}>{provider.name}</h3></div>
              </div>
              <a href={provider.source_url} target="_blank" rel="noopener">공식 지원 기준 <UiIcon name="external-link" /></a>
            </header>
            <div className="surface-card-grid">
              {provider.surfaces.map((surface) => (
                <article className={`surface-card is-${surface.id}`} key={surface.id}>
                  <div className="surface-card-title">
                    <div><h4>{surface.name}</h4><p>{surface.recommended_for}</p></div>
                    {(surface.id === "codex-local" || surface.id === "claude-code") ? <span className="surface-best">자동화 권장</span> : null}
                  </div>
                  <dl className="surface-capabilities">
                    {support.capabilities.map((capability) => {
                      const status = surface.capabilities[capability.id as keyof typeof surface.capabilities];
                      return (
                        <div key={capability.id}>
                          <dt>{capability.label}</dt>
                          <dd className={`is-${status}`}><UiIcon name={status === "supported" ? "check" : "alert"} />{statusLabels[status]}</dd>
                        </div>
                      );
                    })}
                  </dl>
                  <p className="surface-note">{surface.note}</p>
                  <a className="surface-connect-link" href={surface.connection_url} target={surface.connection_url.startsWith("http") ? "_blank" : undefined} rel={surface.connection_url.startsWith("http") ? "noopener" : undefined}>
                    <span><small>권장 연결</small>{surface.connection}</span><UiIcon name="arrow-right" />
                  </a>
                </article>
              ))}
            </div>
          </section>
        ))}
      </div>
      <p className="surface-support-footnote"><UiIcon name="info" /> 자동 Hook은 호스트의 생명주기 기능입니다. 지원하지 않는 화면에서도 Skill과 MCP를 통해 에이전트가 대화 중 기억을 조회하고 저장할 수 있습니다.</p>
    </section>
  );
}

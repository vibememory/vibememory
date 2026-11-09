import support from "@/data/agent-support.json";
import guides from "@/data/harness-guides.json";

function UiIcon({ name }: { name: string }) {
  return <svg className="svg-icon" aria-hidden="true"><use href={`/assets/icons.svg#${name}`} /></svg>;
}

export function HarnessGuideDirectory() {
  return (
    <section className="harness-directory" aria-labelledby="harness-directory-title">
      <div className="harness-directory-heading">
        <div>
          <p className="eyebrow">PRODUCT-SPECIFIC HARNESS GUIDES · UTC {guides.verified_at.slice(0, 10)}</p>
          <h1 id="harness-directory-title">내 도구에 맞는 설정만,<br />정확하게 적용하세요.</h1>
        </div>
        <p>제품마다 Skill 경로, MCP 설정, Hook 이벤트와 승인 방식이 다릅니다. 다른 하네스의 설정을 변환하지 않고 전용 가이드를 사용합니다.</p>
      </div>
      <div className="harness-directory-grid">
        {guides.guides.map((guide) => {
          const agent = support.agents.find((item) => item.id === guide.id);
          return (
            <a className="harness-directory-card" href={`/guide/${guide.slug}`} key={guide.id}>
              <div className="harness-directory-card-top">
                <span className={`harness-product-icon ${["codex", "cursor", "hermes"].includes(guide.id) ? "is-dark" : ""}`}>
                  <img src={guide.icon} alt="" width="30" height="30" />
                </span>
                <span className="support-status is-supported"><UiIcon name="check" /> 지원됨</span>
              </div>
              <h2>{guide.name}</h2>
              <p>{guide.summary}</p>
              <dl>
                <div><dt>최소 버전</dt><dd>{guide.minimum_version}</dd></div>
                <div><dt>연결 방식</dt><dd>{guide.install_method}</dd></div>
              </dl>
              <span className="harness-directory-link">제품별 가이드 열기 <UiIcon name="arrow-right" /></span>
              <small>{agent?.hook_mapping}</small>
            </a>
          );
        })}
      </div>
    </section>
  );
}

"use client";

import { useState } from "react";

type Locale = "ko" | "en" | "zh" | "ja" | "es" | "vi" | "th";

const starterPrompts: Record<Locale, (product: string) => string> = {
  ko: (product) => `이 대화에서는 Vibe Memory${product === "Claude" ? " Connector" : ""}를 적극 사용해줘. 답변 전에 관련 기억이 도움이 되면 핵심 키워드만 추출해 검색하고, 사용자 정정·결정·선호·다음 작업처럼 나중에도 유용한 맥락은 답변 후 간결하게 저장해. 서버가 추론한다고 가정하지 말고 네가 엔티티와 관계를 판단해 구조화해. 매 메시지마다 기계적으로 호출하지 말고 실제 연속성에 도움이 될 때 사용해.`,
  en: (product) => `Use Vibe Memory${product === "Claude" ? " Connector" : ""} proactively in this conversation. Before answering, search with a few extracted keywords when prior context would help. After answering, save concise durable context such as user corrections, decisions, preferences, and next actions. Do not assume the server infers entities or relationships; structure them yourself. Do not call it mechanically on every message—use it when it improves continuity.`,
  zh: (product) => `请在本次对话中主动使用 Vibe Memory${product === "Claude" ? " Connector" : ""}。回答前，如历史上下文有帮助，请提取少量核心关键词进行搜索；回答后，将用户更正、决定、偏好和后续任务等持久信息简洁保存。不要假设服务器会推断实体或关系，请自行判断并结构化。不要每条消息都机械调用，只在确实有助于连续性时使用。`,
  ja: (product) => `この会話ではVibe Memory${product === "Claude" ? " Connector" : ""}を積極的に使ってください。過去の文脈が役立つ場合は、回答前に少数の重要キーワードで検索し、回答後にユーザー訂正・決定・好み・次の作業など長期的に有用な文脈を簡潔に保存してください。サーバーがエンティティや関係を推論するとは考えず、自分で判断して構造化してください。毎回機械的に呼ばず、連続性に役立つ場合に使ってください。`,
  es: (product) => `Usa Vibe Memory${product === "Claude" ? " Connector" : ""} de forma proactiva en esta conversación. Antes de responder, busca con pocas palabras clave cuando el contexto previo sea útil. Después, guarda de forma concisa correcciones, decisiones, preferencias y próximos pasos duraderos. No supongas que el servidor infiere entidades o relaciones: estructúralas tú. No lo llames en cada mensaje; úsalo cuando mejore la continuidad.`,
  vi: (product) => `Hãy chủ động dùng Vibe Memory${product === "Claude" ? " Connector" : ""} trong cuộc trò chuyện này. Trước khi trả lời, chỉ tìm bằng vài từ khóa cốt lõi khi ngữ cảnh trước đó hữu ích. Sau khi trả lời, lưu ngắn gọn các chỉnh sửa, quyết định, sở thích và việc tiếp theo có giá trị lâu dài. Không giả định máy chủ tự suy luận thực thể hay quan hệ; hãy tự cấu trúc chúng. Không gọi máy móc ở mọi tin nhắn, chỉ dùng khi giúp duy trì ngữ cảnh.`,
  th: (product) => `ใช้ Vibe Memory${product === "Claude" ? " Connector" : ""} อย่างกระตือรือร้นในการสนทนานี้ ก่อนตอบให้ค้นด้วยคีย์เวิร์ดสำคัญไม่กี่คำเมื่อบริบทเดิมมีประโยชน์ หลังตอบให้บันทึกการแก้ไข การตัดสินใจ ความชอบ และงานถัดไปที่ควรใช้ต่ออย่างกระชับ อย่าคิดว่าเซิร์ฟเวอร์อนุมานเอนทิตีหรือความสัมพันธ์เอง ให้จัดโครงสร้างด้วยตัวเอง และไม่ต้องเรียกทุกข้อความ ใช้เมื่อช่วยให้บริบทต่อเนื่องจริง`,
};

function UiIcon({ name }: { name: string }) {
  return <svg className="svg-icon" aria-hidden="true"><use href={`/assets/icons.svg#${name}`} /></svg>;
}

export function ChatGuideActions({ product, connectUrl }: { product: string; connectUrl: string }) {
  const [copied, setCopied] = useState<"prompt" | "mcp" | null>(null);

  async function copyPrompt() {
    const locale = (window.vmCurrentLocale?.() as Locale | undefined) || "ko";
    await navigator.clipboard.writeText(starterPrompts[locale](product));
    setCopied("prompt");
    window.setTimeout(() => setCopied(null), 1800);
  }

  async function copyMcp() {
    await navigator.clipboard.writeText("https://vibememory.io/mcp");
    setCopied("mcp");
    window.setTimeout(() => setCopied(null), 1800);
  }

  return (
    <div className="chat-guide-actions">
      <a className="button primary" href={connectUrl} target="_blank" rel="noopener"><UiIcon name="external-link" /> 연결 화면 열기</a>
      <button className="button button-outline" type="button" onClick={copyPrompt}><UiIcon name={copied === "prompt" ? "check" : "copy"} />{copied === "prompt" ? "시작 프롬프트를 복사했습니다" : "시작 프롬프트 복사"}</button>
      <button className="chat-copy-mcp" type="button" onClick={copyMcp}><code>https://vibememory.io/mcp</code><span><UiIcon name={copied === "mcp" ? "check" : "copy"} />{copied === "mcp" ? "복사됨" : "MCP 주소 복사"}</span></button>
    </div>
  );
}

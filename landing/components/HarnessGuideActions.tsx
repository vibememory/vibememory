"use client";

import { useState } from "react";

type Locale = "ko" | "en" | "zh" | "ja" | "es" | "vi" | "th";

declare global {
  interface Window {
    vmCurrentLocale?: () => Locale;
  }
}

const promptTemplates: Record<Locale, (name: string, url: string) => string> = {
  ko: (name, url) => `Vibe Memory를 ${name}에 연결해줘. 다른 하네스 설정을 변환해서 쓰지 말고 ${url}의 제품 전용 가이드를 먼저 읽어. 현재 설치 상태와 버전을 확인하고 Skill, 원격 MCP, 자동 Hook을 각각 설명한 뒤 필요한 변경 diff와 권한 범위를 보여줘. 내가 검토하기 전에는 Hook이나 설정 파일을 수정하지 말고, 승인 후 설치·웹 인증·검증까지 진행해.`,
  en: (name, url) => `Connect Vibe Memory to ${name}. Read the product-specific guide at ${url} first and do not reuse another harness's configuration. Inspect the current installation and version, explain Skill, remote MCP, and lifecycle Hooks separately, and show the exact diff and permission scope. Do not change Hook or configuration files before I review them. After approval, complete installation, web authorization, and verification.`,
  zh: (name, url) => `请将 Vibe Memory 连接到 ${name}。先阅读 ${url} 的产品专用指南，不要转换或复用其他智能体框架的配置。检查当前安装状态和版本，分别说明 Skill、远程 MCP 与自动 Hook，并展示准确的差异和权限范围。在我审核前不要修改 Hook 或配置文件；批准后再完成安装、网页授权与验证。`,
  ja: (name, url) => `Vibe Memoryを${name}に接続してください。別のハーネス設定を流用せず、まず${url}の製品別ガイドを読んでください。現在のインストール状態とバージョンを確認し、Skill・リモートMCP・自動Hookを個別に説明して、正確な差分と権限範囲を示してください。確認前にHookや設定ファイルを変更せず、承認後にインストール・Web認証・検証まで進めてください。`,
  es: (name, url) => `Conecta Vibe Memory con ${name}. Lee primero la guía específica de ${url} y no reutilices la configuración de otro agente. Revisa la instalación y la versión actuales, explica por separado Skill, MCP remoto y Hooks automáticos, y muestra el diff exacto y el alcance de permisos. No modifiques Hooks ni archivos de configuración antes de mi revisión. Tras aprobarlo, completa la instalación, la autorización web y la verificación.`,
  vi: (name, url) => `Kết nối Vibe Memory với ${name}. Trước tiên hãy đọc hướng dẫn riêng tại ${url}, không chuyển đổi cấu hình của harness khác. Kiểm tra trạng thái cài đặt và phiên bản, giải thích riêng Skill, MCP từ xa và Hook tự động, rồi hiển thị diff chính xác cùng phạm vi quyền. Không sửa Hook hoặc tệp cấu hình trước khi tôi xem xét. Sau khi phê duyệt, hoàn tất cài đặt, xác thực web và kiểm tra.`,
  th: (name, url) => `เชื่อม Vibe Memory กับ ${name} โดยอ่านคู่มือเฉพาะผลิตภัณฑ์ที่ ${url} ก่อน และอย่านำการตั้งค่าของ harness อื่นมาแปลงใช้ ตรวจสอบสถานะการติดตั้งและเวอร์ชัน อธิบาย Skill, MCP ระยะไกล และ Hook อัตโนมัติแยกกัน พร้อมแสดง diff และขอบเขตสิทธิ์ที่แน่นอน ห้ามแก้ Hook หรือไฟล์ตั้งค่าก่อนที่ฉันจะตรวจสอบ หลังอนุมัติแล้วจึงติดตั้ง ยืนยันผ่านเว็บ และตรวจสอบให้เสร็จ`,
};

function UiIcon({ name }: { name: string }) {
  return <svg className="svg-icon" aria-hidden="true"><use href={`/assets/icons.svg#${name}`} /></svg>;
}

export function HarnessGuideActions({ name, slug }: { name: string; slug: string }) {
  const [copied, setCopied] = useState(false);

  async function copyPrompt() {
    const locale = window.vmCurrentLocale?.() || "ko";
    const url = `https://vibememory.io/guide/${slug}`;
    await navigator.clipboard.writeText(promptTemplates[locale](name, url));
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1800);
  }

  return (
    <div className="harness-hero-actions">
      <button className="button primary" type="button" onClick={copyPrompt}>
        <UiIcon name={copied ? "check" : "copy"} />
        {copied ? "설치 프롬프트를 복사했습니다" : "제품별 설치 프롬프트 복사"}
      </button>
      <a className="button button-outline" href="/downloads/vibe-memory-skill.zip" download>
        <UiIcon name="download" /> Skill 내려받기
      </a>
    </div>
  );
}

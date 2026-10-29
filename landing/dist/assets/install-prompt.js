'use strict';
window.vibeMemoryInstallPrompt = function vibeMemoryInstallPrompt() {
  const base = location.origin;
  const locale = window.vmCurrentLocale?.() || 'en';
  const prompts = {
    ko: `Vibe Memory를 이 에이전트에 설치하고 내 계정에 연결해줘.

서비스 URL: ${base}
Skill 다운로드: ${base}/downloads/vibe-memory-skill.zip
최신 지침: ${base}/skills/vibe-memory/SKILL.md

진행 방법:
1. 위 ZIP 최신판으로 기존 vibe-memory Skill 폴더만 교체하고 새 SKILL.md 전체를 다시 읽어. 다른 Skill이나 프로젝트 파일은 건드리지 마.
2. 설치된 Skill 폴더의 절대 경로를 구한 뒤 scripts/memory.py sync를 실행해 현재 플랫폼용 Rust CLI를 내려받고 SHA-256을 검증해. 직접 컴파일하거나 curl·직접 API 호출로 우회하지 마.
3. 절대 경로의 CLI로 login --url ${base} --vault-access --no-browser --name "현재 에이전트 이름"을 실행해. 나온 승인 URL과 코드를 클릭 가능하게 보여주고 내가 웹에서 승인할 때까지 기다려. 비밀번호나 API 키를 채팅에 요청하지 마.
4. 승인 후 status로 연결을 확인하고 이후 모든 데이터 작업은 Rust CLI와 최신 Skill 지침을 사용해.
5. Vibe Memory를 선택 기능이 아니라 기본 맥락 계층으로 적극 사용해. 내가 매번 "기억해", "기억을 조회해"라고 다시 말할 때까지 기다리지 마. 맥락이 필요한 비단순 작업은 계획 전에 관련 기억과 최신 session checkpoint를 자동 조회하고, 승인된 결정·수정·선호·제약·검증된 결과·블로커·다음 작업이 바뀌면 즉시 짧게 저장해. 새 대화에서는 최신 checkpoint에서 이어가.
6. 저장 전 recall로 중복과 최신 상태를 확인해. 변경이 없으면 다시 저장하지 말고, 전체 대화·임시 상태·추측·도구 로그·비밀값은 저장하지 마. 현재 사용자의 지시가 기억보다 우선이며, 수정된 내용은 오래된 맥락이 반복되지 않도록 새 checkpoint에 반영해.
7. Vibe Memory의 기준 시간은 UTC야. 저장할 시간은 명확한 경우 UTC로 정규화하고 원래 현지 시간대가 중요하면 메타정보에 보존해. 시간대가 없으면 추측하지 마.
8. 비밀값은 채팅, .env 또는 지속 환경변수로 복사하지 말고 vault capture, vault list와 vault exec만 사용해.`,
    en: `Install Vibe Memory for this agent and connect it to my account.

Service URL: ${base}
Skill download: ${base}/downloads/vibe-memory-skill.zip
Latest instructions: ${base}/skills/vibe-memory/SKILL.md

Steps:
1. Replace only the existing vibe-memory Skill folder with the ZIP above, then read the entire new SKILL.md. Do not alter other Skills or project files.
2. Resolve the installed Skill folder's absolute path and run scripts/memory.py sync to download the released Rust CLI for this platform and verify its SHA-256. Do not compile it or fall back to curl or direct API calls.
3. Run the absolute CLI with login --url ${base} --vault-access --no-browser --name "CURRENT AGENT NAME". Show me the approval URL and code as a clickable flow, then wait for browser approval. Never ask for a password or API key in chat.
4. After approval, verify the connection with status. Use the Rust CLI and latest Skill instructions for every data operation.
5. Treat Vibe Memory as the default continuity layer, not an optional command. Do not wait for me to repeat "remember this" or "check memory." For every non-trivial task where context can matter, automatically recall relevant memories and the latest session checkpoint before planning; promptly save compact updates when accepted decisions, corrections, preferences, constraints, verified outcomes, blockers, or next actions change. Resume from the latest checkpoint in a new conversation.
6. Recall before writing to avoid duplicates and stale state. If there is no durable change, do not write again. Never save full transcripts, transient status, speculation, tool logs, or secrets. Current user instructions override memory; preserve accepted corrections so stale context is not repeated.
7. Vibe Memory's canonical time basis is UTC. Normalize unambiguous saved times to UTC, preserve a meaningful original local zone in metadata, and never guess a missing time zone.
8. Never copy secrets into chat, .env files, or persistent environment variables. Use only vault capture, vault list, and vault exec.`,
    zh: `为此智能体安装 Vibe Memory，并连接到我的账户。

服务地址：${base}
Skill 下载：${base}/downloads/vibe-memory-skill.zip
最新说明：${base}/skills/vibe-memory/SKILL.md

步骤：
1. 仅用上述 ZIP 替换现有 vibe-memory Skill 文件夹，然后完整阅读新的 SKILL.md。不要修改其他 Skill 或项目文件。
2. 找到已安装 Skill 文件夹的绝对路径，运行 scripts/memory.py sync，下载当前平台的 Rust CLI 并验证 SHA-256。不要自行编译，也不要改用 curl 或直接调用 API。
3. 使用绝对路径 CLI 执行 login --url ${base} --vault-access --no-browser --name "当前智能体名称"。以可点击方式显示授权链接和确认码，并等待我在网页中批准。不要在聊天中索取密码或 API 密钥。
4. 批准后用 status 确认连接。此后所有数据操作都使用 Rust CLI 和最新 Skill 说明。
5. 把 Vibe Memory 作为默认上下文层积极使用，而不是可选命令。不要等我再次说“记住这个”或“查询记忆”。对任何可能需要上下文的非简单任务，在规划前自动检索相关记忆和最新 session checkpoint；当已确认的决策、修正、偏好、约束、验证结果、阻塞或下一步发生变化时，立即保存简短更新。新对话从最新 checkpoint 继续。
6. 保存前先 recall，避免重复和过期状态；没有持久变化时不要重复写入。不要保存完整对话、临时状态、推测、工具日志或秘密。当前用户指令优先于记忆，并把已确认的修正写入新 checkpoint，避免再次使用旧上下文。
7. Vibe Memory 的标准时间为 UTC。明确的时间在保存前转换为 UTC；原始本地时区有意义时保留在元数据中；缺少时区时不要猜测。
8. 不要把秘密复制到聊天、.env 或持久环境变量中，只使用 vault capture、vault list 和 vault exec。`,
    ja: `このエージェントに Vibe Memory をインストールし、私のアカウントへ接続して。

サービスURL: ${base}
Skillダウンロード: ${base}/downloads/vibe-memory-skill.zip
最新の手順: ${base}/skills/vibe-memory/SKILL.md

手順:
1. 上記ZIPで既存の vibe-memory Skill フォルダーだけを置き換え、新しい SKILL.md を最後まで読んで。他のSkillやプロジェクトファイルは変更しないで。
2. インストール済みSkillフォルダーの絶対パスを取得し、scripts/memory.py sync を実行して現在のプラットフォーム用Rust CLIをダウンロードし、SHA-256を検証して。自前でコンパイルせず、curlやAPI直接呼び出しに切り替えないで。
3. 絶対パスのCLIで login --url ${base} --vault-access --no-browser --name "現在のエージェント名" を実行して。承認URLとコードをクリック可能な形で表示し、私がWebで承認するまで待って。パスワードやAPIキーをチャットで求めないで。
4. 承認後は status で接続を確認し、以降の全データ操作にRust CLIと最新Skillを使用して。
5. Vibe Memoryを任意のコマンドではなく、標準のコンテキスト層として積極的に使って。私が毎回「覚えて」「記憶を検索して」と言うまで待たないで。文脈が重要な非単純タスクでは、計画前に関連記憶と最新の session checkpoint を自動検索し、確定した決定・修正・好み・制約・検証結果・ブロッカー・次の作業が変わったら短く保存して。新しい会話では最新 checkpoint から再開して。
6. 保存前に recall して重複と古い状態を避け、永続的な変更がなければ再保存しないで。会話全文、一時状態、推測、ツールログ、秘密値は保存しないで。現在のユーザー指示を記憶より優先し、確定した修正は古い文脈を繰り返さないよう新しい checkpoint に反映して。
7. Vibe Memoryの基準時刻はUTC。明確な時刻はUTCに正規化し、元のローカル時刻帯が重要ならメタデータに残し、時刻帯がなければ推測しないで。
8. 秘密値をチャット、.env、永続環境変数へコピーせず、vault capture、vault list、vault exec だけを使って。`,
    es: `Instala Vibe Memory para este agente y conéctalo con mi cuenta.

URL del servicio: ${base}
Descarga del Skill: ${base}/downloads/vibe-memory-skill.zip
Instrucciones actuales: ${base}/skills/vibe-memory/SKILL.md

Pasos:
1. Sustituye únicamente la carpeta existente del Skill vibe-memory con el ZIP anterior y lee el nuevo SKILL.md completo. No modifiques otros Skills ni archivos del proyecto.
2. Obtén la ruta absoluta de la carpeta instalada y ejecuta scripts/memory.py sync para descargar el CLI de Rust publicado para esta plataforma y verificar su SHA-256. No lo compiles ni uses curl o llamadas directas a la API.
3. Ejecuta el CLI por su ruta absoluta con login --url ${base} --vault-access --no-browser --name "NOMBRE DEL AGENTE ACTUAL". Muéstrame el enlace de aprobación y el código de forma que pueda abrirlos, y espera mi aprobación web. No pidas contraseñas ni claves API en el chat.
4. Tras aprobarlo, confirma la conexión con status. Usa el CLI de Rust y las instrucciones más recientes del Skill para todas las operaciones de datos.
5. Usa Vibe Memory activamente como la capa de contexto predeterminada, no como un comando opcional. No esperes a que repita «recuérdalo» o «consulta la memoria». En cada tarea no trivial donde el contexto pueda importar, recupera automáticamente las memorias pertinentes y el último session checkpoint antes de planificar; guarda actualizaciones breves cuando cambien decisiones aceptadas, correcciones, preferencias, restricciones, resultados verificados, bloqueos o próximos pasos. Reanuda una conversación nueva desde el checkpoint más reciente.
6. Ejecuta recall antes de guardar para evitar duplicados y estados obsoletos; si no hay un cambio duradero, no vuelvas a escribir. No guardes conversaciones completas, estados transitorios, especulaciones, registros de herramientas ni secretos. Las instrucciones actuales del usuario prevalecen sobre la memoria; conserva las correcciones aceptadas para no repetir contexto obsoleto.
7. La base temporal canónica de Vibe Memory es UTC. Normaliza a UTC las horas inequívocas, conserva en los metadatos la zona local original cuando importe y nunca adivines una zona horaria ausente.
8. No copies secretos al chat, archivos .env ni variables persistentes. Usa únicamente vault capture, vault list y vault exec.`,
    vi: `Cài đặt Vibe Memory cho tác nhân này và kết nối với tài khoản của tôi.

URL dịch vụ: ${base}
Tải Skill: ${base}/downloads/vibe-memory-skill.zip
Hướng dẫn mới nhất: ${base}/skills/vibe-memory/SKILL.md

Các bước:
1. Chỉ thay thế thư mục Skill vibe-memory hiện có bằng tệp ZIP trên, sau đó đọc toàn bộ SKILL.md mới. Không thay đổi Skill khác hoặc tệp dự án.
2. Xác định đường dẫn tuyệt đối của thư mục Skill đã cài đặt và chạy scripts/memory.py sync để tải Rust CLI đã phát hành cho nền tảng này và xác minh SHA-256. Không tự biên dịch, không dùng curl hoặc gọi API trực tiếp.
3. Chạy CLI bằng đường dẫn tuyệt đối với login --url ${base} --vault-access --no-browser --name "TÊN TÁC NHÂN HIỆN TẠI". Hiển thị URL phê duyệt và mã dưới dạng có thể nhấp, rồi chờ tôi phê duyệt trên web. Không yêu cầu mật khẩu hoặc khóa API trong cuộc trò chuyện.
4. Sau khi phê duyệt, kiểm tra kết nối bằng status. Dùng Rust CLI và hướng dẫn Skill mới nhất cho mọi thao tác dữ liệu.
5. Chủ động dùng Vibe Memory như lớp ngữ cảnh mặc định, không phải một lệnh tùy chọn. Đừng chờ tôi lặp lại “hãy nhớ điều này” hoặc “hãy kiểm tra bộ nhớ”. Với mọi tác vụ không đơn giản mà ngữ cảnh có thể quan trọng, tự động gọi lại ký ức liên quan và session checkpoint mới nhất trước khi lập kế hoạch; lưu ngay bản cập nhật ngắn khi quyết định đã chấp nhận, sửa đổi, sở thích, ràng buộc, kết quả đã xác minh, trở ngại hoặc bước tiếp theo thay đổi. Trong cuộc trò chuyện mới, tiếp tục từ checkpoint mới nhất.
6. Chạy recall trước khi lưu để tránh trùng lặp và trạng thái cũ; nếu không có thay đổi lâu dài thì không ghi lại. Không lưu toàn bộ cuộc trò chuyện, trạng thái tạm thời, suy đoán, log công cụ hoặc bí mật. Chỉ dẫn hiện tại của người dùng ưu tiên hơn ký ức; lưu các sửa đổi đã được chấp nhận để không lặp lại ngữ cảnh cũ.
7. Mốc thời gian chuẩn của Vibe Memory là UTC. Chuẩn hóa thời gian rõ ràng sang UTC, giữ múi giờ địa phương ban đầu trong metadata khi cần và không bao giờ đoán múi giờ bị thiếu.
8. Không sao chép bí mật vào cuộc trò chuyện, tệp .env hoặc biến môi trường lâu dài. Chỉ dùng vault capture, vault list và vault exec.`,
    th: `ติดตั้ง Vibe Memory ให้เอเจนต์นี้และเชื่อมต่อกับบัญชีของฉัน

URL บริการ: ${base}
ดาวน์โหลด Skill: ${base}/downloads/vibe-memory-skill.zip
คำแนะนำล่าสุด: ${base}/skills/vibe-memory/SKILL.md

ขั้นตอน:
1. แทนที่เฉพาะโฟลเดอร์ Skill vibe-memory เดิมด้วย ZIP ด้านบน แล้วอ่าน SKILL.md ใหม่ทั้งหมด ห้ามแก้ไข Skill อื่นหรือไฟล์โครงการ
2. หาเส้นทางแบบสัมบูรณ์ของโฟลเดอร์ Skill ที่ติดตั้ง แล้วรัน scripts/memory.py sync เพื่อดาวน์โหลด Rust CLI ที่เผยแพร่สำหรับแพลตฟอร์มนี้และตรวจสอบ SHA-256 ห้ามคอมไพล์เอง ใช้ curl หรือเรียก API โดยตรง
3. เรียก CLI ด้วยเส้นทางแบบสัมบูรณ์โดยใช้ login --url ${base} --vault-access --no-browser --name "ชื่อเอเจนต์ปัจจุบัน" แสดง URL อนุมัติและรหัสเป็นลิงก์ที่คลิกได้ แล้วรอฉันอนุมัติบนเว็บ ห้ามขอรหัสผ่านหรือคีย์ API ในแชต
4. หลังอนุมัติ ให้ตรวจสอบการเชื่อมต่อด้วย status ใช้ Rust CLI และคำแนะนำ Skill ล่าสุดสำหรับทุกการทำงานกับข้อมูล
5. ใช้ Vibe Memory อย่างสม่ำเสมอเป็นชั้นบริบทเริ่มต้น ไม่ใช่คำสั่งเสริม อย่ารอให้ฉันพูดซ้ำว่า “จำสิ่งนี้” หรือ “ค้นความทรงจำ” สำหรับงานที่ไม่ธรรมดาและบริบทอาจสำคัญ ให้เรียกคืนความทรงจำที่เกี่ยวข้องและ session checkpoint ล่าสุดโดยอัตโนมัติก่อนวางแผน และบันทึกการเปลี่ยนแปลงแบบสั้นทันทีเมื่อการตัดสินใจที่ยอมรับแล้ว การแก้ไข ความชอบ ข้อจำกัด ผลลัพธ์ที่ตรวจสอบแล้ว อุปสรรค หรือขั้นตอนถัดไปเปลี่ยน ในบทสนทนาใหม่ให้ทำต่อจาก checkpoint ล่าสุด
6. เรียก recall ก่อนบันทึกเพื่อหลีกเลี่ยงข้อมูลซ้ำและสถานะเก่า หากไม่มีการเปลี่ยนแปลงที่คงทนก็ไม่ต้องเขียนซ้ำ ห้ามบันทึกบทสนทนาทั้งหมด สถานะชั่วคราว การคาดเดา log ของเครื่องมือ หรือข้อมูลลับ คำสั่งปัจจุบันของผู้ใช้มีความสำคัญกว่าความทรงจำ และให้บันทึกการแก้ไขที่ยอมรับแล้วเพื่อไม่ใช้บริบทเก่าซ้ำ
7. เวลามาตรฐานของ Vibe Memory คือ UTC ปรับเวลาที่ชัดเจนเป็น UTC เก็บเขตเวลาท้องถิ่นเดิมไว้ใน metadata เมื่อมีความสำคัญ และห้ามเดาเขตเวลาที่หายไป
8. ห้ามคัดลอกข้อมูลลับไปยังแชต ไฟล์ .env หรือตัวแปรสภาพแวดล้อมถาวร ใช้เฉพาะ vault capture, vault list และ vault exec เท่านั้น`
  };
  return prompts[locale] || prompts.en;
};

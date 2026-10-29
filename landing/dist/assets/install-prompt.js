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
5. 각 대화 시작에 관련 기억을 조회하고 결정·수정·검증·블로커·다음 작업의 변경을 짧은 session checkpoint로 저장해. 중복이나 전체 대화는 저장하지 마.
6. Vibe Memory의 기준 시간은 UTC야. 저장할 시간은 명확한 경우 UTC로 정규화하고 원래 현지 시간대가 중요하면 메타정보에 보존해. 시간대가 없으면 추측하지 마.
7. 비밀값은 채팅, .env 또는 지속 환경변수로 복사하지 말고 vault list와 vault exec만 사용해.`,
    en: `Install Vibe Memory for this agent and connect it to my account.

Service URL: ${base}
Skill download: ${base}/downloads/vibe-memory-skill.zip
Latest instructions: ${base}/skills/vibe-memory/SKILL.md

Steps:
1. Replace only the existing vibe-memory Skill folder with the ZIP above, then read the entire new SKILL.md. Do not alter other Skills or project files.
2. Resolve the installed Skill folder's absolute path and run scripts/memory.py sync to download the released Rust CLI for this platform and verify its SHA-256. Do not compile it or fall back to curl or direct API calls.
3. Run the absolute CLI with login --url ${base} --vault-access --no-browser --name "CURRENT AGENT NAME". Show me the approval URL and code as a clickable flow, then wait for browser approval. Never ask for a password or API key in chat.
4. After approval, verify the connection with status. Use the Rust CLI and latest Skill instructions for every data operation.
5. Recall relevant memories at the start of each conversation. Save compact session checkpoints when decisions, corrections, verification, blockers, or next actions change; never save duplicates or full transcripts.
6. Vibe Memory's canonical time basis is UTC. Normalize unambiguous saved times to UTC, preserve a meaningful original local zone in metadata, and never guess a missing time zone.
7. Never copy secrets into chat, .env files, or persistent environment variables. Use only vault list and vault exec.`,
    zh: `为此智能体安装 Vibe Memory，并连接到我的账户。

服务地址：${base}
Skill 下载：${base}/downloads/vibe-memory-skill.zip
最新说明：${base}/skills/vibe-memory/SKILL.md

步骤：
1. 仅用上述 ZIP 替换现有 vibe-memory Skill 文件夹，然后完整阅读新的 SKILL.md。不要修改其他 Skill 或项目文件。
2. 找到已安装 Skill 文件夹的绝对路径，运行 scripts/memory.py sync，下载当前平台的 Rust CLI 并验证 SHA-256。不要自行编译，也不要改用 curl 或直接调用 API。
3. 使用绝对路径 CLI 执行 login --url ${base} --vault-access --no-browser --name "当前智能体名称"。以可点击方式显示授权链接和确认码，并等待我在网页中批准。不要在聊天中索取密码或 API 密钥。
4. 批准后用 status 确认连接。此后所有数据操作都使用 Rust CLI 和最新 Skill 说明。
5. 每次对话开始时检索相关记忆；当决策、修正、验证结果、阻塞或下一步发生变化时，保存简短的 session checkpoint。不要保存重复内容或完整对话。
6. Vibe Memory 的标准时间为 UTC。明确的时间在保存前转换为 UTC；原始本地时区有意义时保留在元数据中；缺少时区时不要猜测。
7. 不要把秘密复制到聊天、.env 或持久环境变量中，只使用 vault list 和 vault exec。`,
    ja: `このエージェントに Vibe Memory をインストールし、私のアカウントへ接続して。

サービスURL: ${base}
Skillダウンロード: ${base}/downloads/vibe-memory-skill.zip
最新の手順: ${base}/skills/vibe-memory/SKILL.md

手順:
1. 上記ZIPで既存の vibe-memory Skill フォルダーだけを置き換え、新しい SKILL.md を最後まで読んで。他のSkillやプロジェクトファイルは変更しないで。
2. インストール済みSkillフォルダーの絶対パスを取得し、scripts/memory.py sync を実行して現在のプラットフォーム用Rust CLIをダウンロードし、SHA-256を検証して。自前でコンパイルせず、curlやAPI直接呼び出しに切り替えないで。
3. 絶対パスのCLIで login --url ${base} --vault-access --no-browser --name "現在のエージェント名" を実行して。承認URLとコードをクリック可能な形で表示し、私がWebで承認するまで待って。パスワードやAPIキーをチャットで求めないで。
4. 承認後は status で接続を確認し、以降の全データ操作にRust CLIと最新Skillを使用して。
5. 各会話の開始時に関連記憶を検索し、決定・修正・検証・ブロッカー・次の作業が変わったときだけ短い session checkpoint を保存して。重複や会話全文は保存しないで。
6. Vibe Memoryの基準時刻はUTC。明確な時刻はUTCに正規化し、元のローカル時刻帯が重要ならメタデータに残し、時刻帯がなければ推測しないで。
7. 秘密値をチャット、.env、永続環境変数へコピーせず、vault list と vault exec だけを使って。`,
    es: `Instala Vibe Memory para este agente y conéctalo con mi cuenta.

URL del servicio: ${base}
Descarga del Skill: ${base}/downloads/vibe-memory-skill.zip
Instrucciones actuales: ${base}/skills/vibe-memory/SKILL.md

Pasos:
1. Sustituye únicamente la carpeta existente del Skill vibe-memory con el ZIP anterior y lee el nuevo SKILL.md completo. No modifiques otros Skills ni archivos del proyecto.
2. Obtén la ruta absoluta de la carpeta instalada y ejecuta scripts/memory.py sync para descargar el CLI de Rust publicado para esta plataforma y verificar su SHA-256. No lo compiles ni uses curl o llamadas directas a la API.
3. Ejecuta el CLI por su ruta absoluta con login --url ${base} --vault-access --no-browser --name "NOMBRE DEL AGENTE ACTUAL". Muéstrame el enlace de aprobación y el código de forma que pueda abrirlos, y espera mi aprobación web. No pidas contraseñas ni claves API en el chat.
4. Tras aprobarlo, confirma la conexión con status. Usa el CLI de Rust y las instrucciones más recientes del Skill para todas las operaciones de datos.
5. Al iniciar cada conversación, recupera las memorias pertinentes. Guarda checkpoints breves cuando cambien decisiones, correcciones, verificaciones, bloqueos o próximos pasos; no guardes duplicados ni conversaciones completas.
6. La base temporal canónica de Vibe Memory es UTC. Normaliza a UTC las horas inequívocas, conserva en los metadatos la zona local original cuando importe y nunca adivines una zona horaria ausente.
7. No copies secretos al chat, archivos .env ni variables persistentes. Usa únicamente vault list y vault exec.`,
    vi: `Cài đặt Vibe Memory cho tác nhân này và kết nối với tài khoản của tôi.

URL dịch vụ: ${base}
Tải Skill: ${base}/downloads/vibe-memory-skill.zip
Hướng dẫn mới nhất: ${base}/skills/vibe-memory/SKILL.md

Các bước:
1. Chỉ thay thế thư mục Skill vibe-memory hiện có bằng tệp ZIP trên, sau đó đọc toàn bộ SKILL.md mới. Không thay đổi Skill khác hoặc tệp dự án.
2. Xác định đường dẫn tuyệt đối của thư mục Skill đã cài đặt và chạy scripts/memory.py sync để tải Rust CLI đã phát hành cho nền tảng này và xác minh SHA-256. Không tự biên dịch, không dùng curl hoặc gọi API trực tiếp.
3. Chạy CLI bằng đường dẫn tuyệt đối với login --url ${base} --vault-access --no-browser --name "TÊN TÁC NHÂN HIỆN TẠI". Hiển thị URL phê duyệt và mã dưới dạng có thể nhấp, rồi chờ tôi phê duyệt trên web. Không yêu cầu mật khẩu hoặc khóa API trong cuộc trò chuyện.
4. Sau khi phê duyệt, kiểm tra kết nối bằng status. Dùng Rust CLI và hướng dẫn Skill mới nhất cho mọi thao tác dữ liệu.
5. Khi bắt đầu mỗi cuộc trò chuyện, hãy gọi lại những ký ức liên quan. Chỉ lưu session checkpoint ngắn khi quyết định, sửa đổi, xác minh, trở ngại hoặc bước tiếp theo thay đổi; không lưu nội dung trùng lặp hay toàn bộ cuộc trò chuyện.
6. Mốc thời gian chuẩn của Vibe Memory là UTC. Chuẩn hóa thời gian rõ ràng sang UTC, giữ múi giờ địa phương ban đầu trong metadata khi cần và không bao giờ đoán múi giờ bị thiếu.
7. Không sao chép bí mật vào cuộc trò chuyện, tệp .env hoặc biến môi trường lâu dài. Chỉ dùng vault list và vault exec.`,
    th: `ติดตั้ง Vibe Memory ให้เอเจนต์นี้และเชื่อมต่อกับบัญชีของฉัน

URL บริการ: ${base}
ดาวน์โหลด Skill: ${base}/downloads/vibe-memory-skill.zip
คำแนะนำล่าสุด: ${base}/skills/vibe-memory/SKILL.md

ขั้นตอน:
1. แทนที่เฉพาะโฟลเดอร์ Skill vibe-memory เดิมด้วย ZIP ด้านบน แล้วอ่าน SKILL.md ใหม่ทั้งหมด ห้ามแก้ไข Skill อื่นหรือไฟล์โครงการ
2. หาเส้นทางแบบสัมบูรณ์ของโฟลเดอร์ Skill ที่ติดตั้ง แล้วรัน scripts/memory.py sync เพื่อดาวน์โหลด Rust CLI ที่เผยแพร่สำหรับแพลตฟอร์มนี้และตรวจสอบ SHA-256 ห้ามคอมไพล์เอง ใช้ curl หรือเรียก API โดยตรง
3. เรียก CLI ด้วยเส้นทางแบบสัมบูรณ์โดยใช้ login --url ${base} --vault-access --no-browser --name "ชื่อเอเจนต์ปัจจุบัน" แสดง URL อนุมัติและรหัสเป็นลิงก์ที่คลิกได้ แล้วรอฉันอนุมัติบนเว็บ ห้ามขอรหัสผ่านหรือคีย์ API ในแชต
4. หลังอนุมัติ ให้ตรวจสอบการเชื่อมต่อด้วย status ใช้ Rust CLI และคำแนะนำ Skill ล่าสุดสำหรับทุกการทำงานกับข้อมูล
5. เมื่อเริ่มแต่ละบทสนทนา ให้เรียกคืนความทรงจำที่เกี่ยวข้อง บันทึก session checkpoint แบบสั้นเมื่อการตัดสินใจ การแก้ไข การตรวจสอบ อุปสรรค หรือขั้นตอนถัดไปเปลี่ยนเท่านั้น ห้ามบันทึกซ้ำหรือบันทึกบทสนทนาทั้งหมด
6. เวลามาตรฐานของ Vibe Memory คือ UTC ปรับเวลาที่ชัดเจนเป็น UTC เก็บเขตเวลาท้องถิ่นเดิมไว้ใน metadata เมื่อมีความสำคัญ และห้ามเดาเขตเวลาที่หายไป
7. ห้ามคัดลอกข้อมูลลับไปยังแชต ไฟล์ .env หรือตัวแปรสภาพแวดล้อมถาวร ใช้เฉพาะ vault list และ vault exec เท่านั้น`
  };
  return prompts[locale] || prompts.en;
};

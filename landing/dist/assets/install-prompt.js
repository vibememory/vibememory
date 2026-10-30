'use strict';
window.vibeMemoryInstallPrompt = function vibeMemoryInstallPrompt() {
  const base = location.origin;
  const agentArchive = 'https://github.com/vibememory/vibememory/releases/latest/download/vibe-memory-skill.zip';
  const agentSkill = 'https://github.com/vibememory/vibememory/releases/latest/download/SKILL.md';
  const hookGuide = `${base}/guide.html#agent-hooks`;
  const adapterRoot = 'https://github.com/vibememory/vibememory/tree/main/agent-adapters';
  const locale = window.vmCurrentLocale?.() || 'en';
  const prompts = {
    ko: `Vibe Memory를 이 에이전트에 설치하고 내 계정에 연결해줘.

서비스 URL: ${base}
Skill 다운로드: ${agentArchive}
최신 지침: ${agentSkill}

진행 방법:
1. 위 ZIP 최신판으로 기존 vibe-memory Skill 폴더만 교체하고 새 SKILL.md 전체를 다시 읽어. 다른 Skill이나 프로젝트 파일은 건드리지 마.
2. 설치된 Skill 폴더의 절대 경로를 구한 뒤 scripts/memory.py sync를 실행해 현재 플랫폼용 Rust CLI를 내려받고 SHA-256을 검증해. 직접 컴파일하거나 curl·직접 API 호출로 우회하지 마.
3. 절대 경로의 CLI로 login --url ${base} --vault-access --no-browser --name "현재 에이전트 이름"을 실행해. 나온 승인 URL과 코드를 클릭 가능하게 보여주고 내가 웹에서 승인할 때까지 기다려. 비밀번호나 API 키를 채팅에 요청하지 마.
4. 승인 후 status로 연결을 확인하고 이후 모든 데이터 작업은 Rust CLI와 최신 Skill 지침을 사용해.
5. Vibe Memory를 선택 기능이 아니라 기본 맥락 계층으로 적극 사용해. 내가 매번 "기억해", "기억을 조회해"라고 다시 말할 때까지 기다리지 마. 맥락이 필요한 비단순 작업은 계획 전에 관련 기억과 최신 session checkpoint를 자동 조회하고, 승인된 결정·수정·선호·제약·검증된 결과·블로커·다음 작업이 바뀌면 즉시 짧게 저장해. 새 대화에서는 최신 checkpoint에서 이어가.
6. 저장 전 recall로 중복과 최신 상태를 확인해. 변경이 없으면 다시 저장하지 말고, 전체 대화·임시 상태·추측·도구 로그·비밀값은 저장하지 마. 현재 사용자의 지시가 기억보다 우선이며, 수정된 내용은 오래된 맥락이 반복되지 않도록 새 checkpoint에 반영해.
7. Vibe Memory의 기준 시간은 UTC야. 저장할 시간은 명확한 경우 UTC로 정규화하고 원래 현지 시간대가 중요하면 메타정보에 보존해. 시간대가 없으면 추측하지 마.
8. 비밀값은 채팅, .env 또는 지속 환경변수로 복사하지 말고 vault capture, vault list와 vault exec만 사용해.
9. 현재 에이전트 도구를 먼저 식별하고 아래 분기 중 정확히 하나만 적용해. 공통 훅 설정을 만들거나 다른 도구의 이벤트명을 재사용하지 마. 기존 설정을 덮어쓰지 말고 변경 diff와 범위를 먼저 보여준 뒤 내가 승인하면 병합해. 상세 안내: ${hookGuide}
   - Claude Code: 검증된 CLI를 vibe-memory 이름으로 PATH에서 실행 가능하게 한 뒤 /plugin install vibe-memory --marketplace vibememory/vibememory 를 열어 사용자·프로젝트·로컬 범위를 내가 선택하게 해. 플러그인과 수동 SessionStart·Stop·PreCompact 훅은 중복 설치하지 마.
   - OpenAI Codex: ${adapterRoot}/codex 의 hooks.json에서 Vibe Memory 그룹만 ~/.codex/hooks.json 또는 프로젝트의 .codex/hooks.json에 병합할 diff를 보여줘. 승인 후 /hooks에서 세 정의를 검토·신뢰하고 동작을 확인해. 로컬 명령 실행이 없는 Work Cloud에서는 설치하지 말고 지원되지 않는다고 알려줘.
   - Hermes Agent: ${adapterRoot}/hermes 의 vibe_memory_hook.py를 검토된 절대 경로에 두고 config.example.yaml의 네 이벤트만 활성 프로필에 병합할 diff를 보여줘. hooks_auto_accept: false를 유지하고 승인 후 hermes hooks list, hermes hooks doctor와 각 이벤트 test로 확인해.
   - OpenClaw: ${adapterRoot}/openclaw 를 검토한 뒤 openclaw plugins install --link ./agent-adapters/openclaw --force --accept-capabilities 와 openclaw plugins enable vibe-memory-hooks 를 사용해. openclaw.json의 allowConversationAccess·allowPromptInjection 및 projectRoots는 별도로 설명하고 내가 승인한 값만 병합한 뒤 openclaw plugins inspect vibe-memory-hooks --runtime --json 으로 확인해.
   - 위 네 도구가 아니거나 검증된 어댑터를 실행할 수 없으면 훅을 만들지 말고 Skill의 기본 recall/checkpoint 루프를 사용해.`,
    en: `Install Vibe Memory for this agent and connect it to my account.

Service URL: ${base}
Skill download: ${agentArchive}
Latest instructions: ${agentSkill}

Steps:
1. Replace only the existing vibe-memory Skill folder with the ZIP above, then read the entire new SKILL.md. Do not alter other Skills or project files.
2. Resolve the installed Skill folder's absolute path and run scripts/memory.py sync to download the released Rust CLI for this platform and verify its SHA-256. Do not compile it or fall back to curl or direct API calls.
3. Run the absolute CLI with login --url ${base} --vault-access --no-browser --name "CURRENT AGENT NAME". Show me the approval URL and code as a clickable flow, then wait for browser approval. Never ask for a password or API key in chat.
4. After approval, verify the connection with status. Use the Rust CLI and latest Skill instructions for every data operation.
5. Treat Vibe Memory as the default continuity layer, not an optional command. Do not wait for me to repeat "remember this" or "check memory." For every non-trivial task where context can matter, automatically recall relevant memories and the latest session checkpoint before planning; promptly save compact updates when accepted decisions, corrections, preferences, constraints, verified outcomes, blockers, or next actions change. Resume from the latest checkpoint in a new conversation.
6. Recall before writing to avoid duplicates and stale state. If there is no durable change, do not write again. Never save full transcripts, transient status, speculation, tool logs, or secrets. Current user instructions override memory; preserve accepted corrections so stale context is not repeated.
7. Vibe Memory's canonical time basis is UTC. Normalize unambiguous saved times to UTC, preserve a meaningful original local zone in metadata, and never guess a missing time zone.
8. Never copy secrets into chat, .env files, or persistent environment variables. Use only vault capture, vault list, and vault exec.
9. Identify the current agent host first and apply exactly one branch below. Do not invent a shared hook configuration or reuse another host's event names. Never overwrite existing configuration: show the exact diff and scope first, then merge it only after I approve. Full guide: ${hookGuide}
   - Claude Code: make the verified CLI available on PATH as vibe-memory, then open /plugin install vibe-memory --marketplace vibememory/vibememory so I can choose user, project, or local scope. Do not enable both the plugin and manual SessionStart, Stop, and PreCompact hooks.
   - OpenAI Codex: review ${adapterRoot}/codex and use only its hooks.json Vibe Memory groups. Show a merge into ~/.codex/hooks.json or project .codex/hooks.json, then after approval review and trust all three definitions in /hooks. If this is Work Cloud without local command execution, do not install hooks and report that limitation.
   - Hermes Agent: review ${adapterRoot}/hermes, place its vibe_memory_hook.py at an operator-reviewed absolute path, and show a merge of the four config.example.yaml events into the active profile. Keep hooks_auto_accept: false. After approval run hermes hooks list, hermes hooks doctor, and test each event.
   - OpenClaw: review ${adapterRoot}/openclaw, then use openclaw plugins install --link ./agent-adapters/openclaw --force --accept-capabilities and openclaw plugins enable vibe-memory-hooks. Explain allowConversationAccess, allowPromptInjection, and projectRoots separately; merge only approved values into openclaw.json, then verify with openclaw plugins inspect vibe-memory-hooks --runtime --json.
   - For any other host, or when its verified adapter cannot run, do not create hooks. Use the Skill's normal recall/checkpoint loop instead.`,
    zh: `为此智能体安装 Vibe Memory，并连接到我的账户。

服务地址：${base}
Skill 下载：${agentArchive}
最新说明：${agentSkill}

步骤：
1. 仅用上述 ZIP 替换现有 vibe-memory Skill 文件夹，然后完整阅读新的 SKILL.md。不要修改其他 Skill 或项目文件。
2. 找到已安装 Skill 文件夹的绝对路径，运行 scripts/memory.py sync，下载当前平台的 Rust CLI 并验证 SHA-256。不要自行编译，也不要改用 curl 或直接调用 API。
3. 使用绝对路径 CLI 执行 login --url ${base} --vault-access --no-browser --name "当前智能体名称"。以可点击方式显示授权链接和确认码，并等待我在网页中批准。不要在聊天中索取密码或 API 密钥。
4. 批准后用 status 确认连接。此后所有数据操作都使用 Rust CLI 和最新 Skill 说明。
5. 把 Vibe Memory 作为默认上下文层积极使用，而不是可选命令。不要等我再次说“记住这个”或“查询记忆”。对任何可能需要上下文的非简单任务，在规划前自动检索相关记忆和最新 session checkpoint；当已确认的决策、修正、偏好、约束、验证结果、阻塞或下一步发生变化时，立即保存简短更新。新对话从最新 checkpoint 继续。
6. 保存前先 recall，避免重复和过期状态；没有持久变化时不要重复写入。不要保存完整对话、临时状态、推测、工具日志或秘密。当前用户指令优先于记忆，并把已确认的修正写入新 checkpoint，避免再次使用旧上下文。
7. Vibe Memory 的标准时间为 UTC。明确的时间在保存前转换为 UTC；原始本地时区有意义时保留在元数据中；缺少时区时不要猜测。
8. 不要把秘密复制到聊天、.env 或持久环境变量中，只使用 vault capture、vault list 和 vault exec。
9. 先识别当前智能体宿主，并且只应用下面一个对应分支。不要创建通用 Hook 配置，也不要复用其他宿主的事件名。不要覆盖现有配置：先显示准确的差异和范围，得到我批准后再合并。完整指南：${hookGuide}
   - Claude Code：让已验证的 CLI 能以 vibe-memory 从 PATH 运行，然后打开 /plugin install vibe-memory --marketplace vibememory/vibememory，由我选择用户、项目或本地范围。不要同时启用插件和手动 SessionStart、Stop、PreCompact Hook。
   - OpenAI Codex：审核 ${adapterRoot}/codex，并且仅使用其中 hooks.json 的 Vibe Memory 组。先显示合并到 ~/.codex/hooks.json 或项目 .codex/hooks.json 的差异；批准后在 /hooks 中审核并信任三个定义。没有本地命令执行能力的 Work Cloud 不要安装 Hook，并说明此限制。
   - Hermes Agent：审核 ${adapterRoot}/hermes，把其中的 vibe_memory_hook.py 放到操作者审核过的绝对路径，显示把 config.example.yaml 的四个事件合并到活动配置的差异，并保持 hooks_auto_accept: false。批准后运行 hermes hooks list、hermes hooks doctor，并测试每个事件。
   - OpenClaw：审核 ${adapterRoot}/openclaw 后，执行 openclaw plugins install --link ./agent-adapters/openclaw --force --accept-capabilities 和 openclaw plugins enable vibe-memory-hooks。单独说明 allowConversationAccess、allowPromptInjection 与 projectRoots，只把批准的值合并到 openclaw.json，最后运行 openclaw plugins inspect vibe-memory-hooks --runtime --json 验证。
   - 如果不是上述宿主，或无法运行其已验证适配器，不要创建 Hook，改用 Skill 的常规 recall/checkpoint 循环。`,
    ja: `このエージェントに Vibe Memory をインストールし、私のアカウントへ接続して。

サービスURL: ${base}
Skillダウンロード: ${agentArchive}
最新の手順: ${agentSkill}

手順:
1. 上記ZIPで既存の vibe-memory Skill フォルダーだけを置き換え、新しい SKILL.md を最後まで読んで。他のSkillやプロジェクトファイルは変更しないで。
2. インストール済みSkillフォルダーの絶対パスを取得し、scripts/memory.py sync を実行して現在のプラットフォーム用Rust CLIをダウンロードし、SHA-256を検証して。自前でコンパイルせず、curlやAPI直接呼び出しに切り替えないで。
3. 絶対パスのCLIで login --url ${base} --vault-access --no-browser --name "現在のエージェント名" を実行して。承認URLとコードをクリック可能な形で表示し、私がWebで承認するまで待って。パスワードやAPIキーをチャットで求めないで。
4. 承認後は status で接続を確認し、以降の全データ操作にRust CLIと最新Skillを使用して。
5. Vibe Memoryを任意のコマンドではなく、標準のコンテキスト層として積極的に使って。私が毎回「覚えて」「記憶を検索して」と言うまで待たないで。文脈が重要な非単純タスクでは、計画前に関連記憶と最新の session checkpoint を自動検索し、確定した決定・修正・好み・制約・検証結果・ブロッカー・次の作業が変わったら短く保存して。新しい会話では最新 checkpoint から再開して。
6. 保存前に recall して重複と古い状態を避け、永続的な変更がなければ再保存しないで。会話全文、一時状態、推測、ツールログ、秘密値は保存しないで。現在のユーザー指示を記憶より優先し、確定した修正は古い文脈を繰り返さないよう新しい checkpoint に反映して。
7. Vibe Memoryの基準時刻はUTC。明確な時刻はUTCに正規化し、元のローカル時刻帯が重要ならメタデータに残し、時刻帯がなければ推測しないで。
8. 秘密値をチャット、.env、永続環境変数へコピーせず、vault capture、vault list、vault exec だけを使って。
9. まず現在のエージェントホストを判定し、次のうち該当する分岐を1つだけ適用して。共通Hook設定を作ったり、別ホストのイベント名を流用したりしないで。既存設定は上書きせず、正確な差分と適用範囲を先に示し、私の承認後にだけマージして。詳細: ${hookGuide}
   - Claude Code: 検証済みCLIをvibe-memoryとしてPATHから実行可能にし、/plugin install vibe-memory --marketplace vibememory/vibememory を開いて、ユーザー・プロジェクト・ローカル範囲を私に選ばせて。プラグインと手動SessionStart・Stop・PreCompact Hookを同時に有効化しないで。
   - OpenAI Codex: ${adapterRoot}/codex を確認し、そのhooks.jsonのVibe Memoryグループだけを使って、~/.codex/hooks.json またはプロジェクトの .codex/hooks.json へのマージ差分を示して。承認後、/hooks で3つの定義を確認・信頼して。ローカルコマンドを実行できないWork Cloudではインストールせず、制約を知らせて。
   - Hermes Agent: ${adapterRoot}/hermes を確認し、そのvibe_memory_hook.pyを運用者が確認した絶対パスに置き、config.example.yaml の4イベントを有効プロファイルへ追加する差分を示して。hooks_auto_accept: falseを維持し、承認後に hermes hooks list、hermes hooks doctor と各イベントのtestを実行して。
   - OpenClaw: ${adapterRoot}/openclaw を確認後、openclaw plugins install --link ./agent-adapters/openclaw --force --accept-capabilities と openclaw plugins enable vibe-memory-hooks を使って。allowConversationAccess、allowPromptInjection、projectRootsを個別に説明し、承認済みの値だけをopenclaw.jsonへマージしてから openclaw plugins inspect vibe-memory-hooks --runtime --json で確認して。
   - 上記以外、または検証済みアダプターを実行できない場合はHookを作らず、Skillの通常のrecall/checkpointループを使って。`,
    es: `Instala Vibe Memory para este agente y conéctalo con mi cuenta.

URL del servicio: ${base}
Descarga del Skill: ${agentArchive}
Instrucciones actuales: ${agentSkill}

Pasos:
1. Sustituye únicamente la carpeta existente del Skill vibe-memory con el ZIP anterior y lee el nuevo SKILL.md completo. No modifiques otros Skills ni archivos del proyecto.
2. Obtén la ruta absoluta de la carpeta instalada y ejecuta scripts/memory.py sync para descargar el CLI de Rust publicado para esta plataforma y verificar su SHA-256. No lo compiles ni uses curl o llamadas directas a la API.
3. Ejecuta el CLI por su ruta absoluta con login --url ${base} --vault-access --no-browser --name "NOMBRE DEL AGENTE ACTUAL". Muéstrame el enlace de aprobación y el código de forma que pueda abrirlos, y espera mi aprobación web. No pidas contraseñas ni claves API en el chat.
4. Tras aprobarlo, confirma la conexión con status. Usa el CLI de Rust y las instrucciones más recientes del Skill para todas las operaciones de datos.
5. Usa Vibe Memory activamente como la capa de contexto predeterminada, no como un comando opcional. No esperes a que repita «recuérdalo» o «consulta la memoria». En cada tarea no trivial donde el contexto pueda importar, recupera automáticamente las memorias pertinentes y el último session checkpoint antes de planificar; guarda actualizaciones breves cuando cambien decisiones aceptadas, correcciones, preferencias, restricciones, resultados verificados, bloqueos o próximos pasos. Reanuda una conversación nueva desde el checkpoint más reciente.
6. Ejecuta recall antes de guardar para evitar duplicados y estados obsoletos; si no hay un cambio duradero, no vuelvas a escribir. No guardes conversaciones completas, estados transitorios, especulaciones, registros de herramientas ni secretos. Las instrucciones actuales del usuario prevalecen sobre la memoria; conserva las correcciones aceptadas para no repetir contexto obsoleto.
7. La base temporal canónica de Vibe Memory es UTC. Normaliza a UTC las horas inequívocas, conserva en los metadatos la zona local original cuando importe y nunca adivines una zona horaria ausente.
8. No copies secretos al chat, archivos .env ni variables persistentes. Usa únicamente vault capture, vault list y vault exec.
9. Identifica primero el host del agente y aplica exactamente una de las ramas siguientes. No inventes una configuración común ni reutilices eventos de otro host. No sobrescribas la configuración existente: muestra antes el diff exacto y el alcance, y fusiónalo solo después de mi aprobación. Guía completa: ${hookGuide}
   - Claude Code: deja el CLI verificado en PATH como vibe-memory y abre /plugin install vibe-memory --marketplace vibememory/vibememory para que elija el alcance de usuario, proyecto o local. No actives a la vez el plugin y los hooks manuales SessionStart, Stop y PreCompact.
   - OpenAI Codex: revisa ${adapterRoot}/codex y usa solo los grupos de Vibe Memory de su hooks.json. Muestra el diff para ~/.codex/hooks.json o .codex/hooks.json del proyecto y, tras aprobarlo, revisa y confía en las tres definiciones desde /hooks. En Work Cloud sin ejecución local no instales hooks e informa de la limitación.
   - Hermes Agent: revisa ${adapterRoot}/hermes, coloca su vibe_memory_hook.py en una ruta absoluta revisada y muestra la fusión de los cuatro eventos de config.example.yaml en el perfil activo. Mantén hooks_auto_accept: false. Tras aprobarlo, ejecuta hermes hooks list, hermes hooks doctor y prueba cada evento.
   - OpenClaw: revisa ${adapterRoot}/openclaw y usa openclaw plugins install --link ./agent-adapters/openclaw --force --accept-capabilities y openclaw plugins enable vibe-memory-hooks. Explica por separado allowConversationAccess, allowPromptInjection y projectRoots; fusiona solo los valores aprobados en openclaw.json y verifica con openclaw plugins inspect vibe-memory-hooks --runtime --json.
   - Para cualquier otro host, o si su adaptador verificado no puede ejecutarse, no crees hooks. Usa el ciclo normal de recall/checkpoint del Skill.`,
    vi: `Cài đặt Vibe Memory cho tác nhân này và kết nối với tài khoản của tôi.

URL dịch vụ: ${base}
Tải Skill: ${agentArchive}
Hướng dẫn mới nhất: ${agentSkill}

Các bước:
1. Chỉ thay thế thư mục Skill vibe-memory hiện có bằng tệp ZIP trên, sau đó đọc toàn bộ SKILL.md mới. Không thay đổi Skill khác hoặc tệp dự án.
2. Xác định đường dẫn tuyệt đối của thư mục Skill đã cài đặt và chạy scripts/memory.py sync để tải Rust CLI đã phát hành cho nền tảng này và xác minh SHA-256. Không tự biên dịch, không dùng curl hoặc gọi API trực tiếp.
3. Chạy CLI bằng đường dẫn tuyệt đối với login --url ${base} --vault-access --no-browser --name "TÊN TÁC NHÂN HIỆN TẠI". Hiển thị URL phê duyệt và mã dưới dạng có thể nhấp, rồi chờ tôi phê duyệt trên web. Không yêu cầu mật khẩu hoặc khóa API trong cuộc trò chuyện.
4. Sau khi phê duyệt, kiểm tra kết nối bằng status. Dùng Rust CLI và hướng dẫn Skill mới nhất cho mọi thao tác dữ liệu.
5. Chủ động dùng Vibe Memory như lớp ngữ cảnh mặc định, không phải một lệnh tùy chọn. Đừng chờ tôi lặp lại “hãy nhớ điều này” hoặc “hãy kiểm tra bộ nhớ”. Với mọi tác vụ không đơn giản mà ngữ cảnh có thể quan trọng, tự động gọi lại ký ức liên quan và session checkpoint mới nhất trước khi lập kế hoạch; lưu ngay bản cập nhật ngắn khi quyết định đã chấp nhận, sửa đổi, sở thích, ràng buộc, kết quả đã xác minh, trở ngại hoặc bước tiếp theo thay đổi. Trong cuộc trò chuyện mới, tiếp tục từ checkpoint mới nhất.
6. Chạy recall trước khi lưu để tránh trùng lặp và trạng thái cũ; nếu không có thay đổi lâu dài thì không ghi lại. Không lưu toàn bộ cuộc trò chuyện, trạng thái tạm thời, suy đoán, log công cụ hoặc bí mật. Chỉ dẫn hiện tại của người dùng ưu tiên hơn ký ức; lưu các sửa đổi đã được chấp nhận để không lặp lại ngữ cảnh cũ.
7. Mốc thời gian chuẩn của Vibe Memory là UTC. Chuẩn hóa thời gian rõ ràng sang UTC, giữ múi giờ địa phương ban đầu trong metadata khi cần và không bao giờ đoán múi giờ bị thiếu.
8. Không sao chép bí mật vào cuộc trò chuyện, tệp .env hoặc biến môi trường lâu dài. Chỉ dùng vault capture, vault list và vault exec.
9. Trước tiên hãy xác định host của tác nhân hiện tại và chỉ áp dụng đúng một nhánh bên dưới. Không tạo cấu hình hook dùng chung hoặc dùng lại tên sự kiện của host khác. Không ghi đè cấu hình hiện có: hiển thị diff chính xác và phạm vi trước, chỉ hợp nhất sau khi tôi phê duyệt. Hướng dẫn đầy đủ: ${hookGuide}
   - Claude Code: đưa CLI đã xác minh vào PATH với tên vibe-memory, rồi mở /plugin install vibe-memory --marketplace vibememory/vibememory để tôi chọn phạm vi user, project hoặc local. Không bật đồng thời plugin và hook SessionStart, Stop, PreCompact thủ công.
   - OpenAI Codex: xem xét ${adapterRoot}/codex và chỉ dùng các nhóm Vibe Memory trong hooks.json của nó. Hiển thị diff hợp nhất vào ~/.codex/hooks.json hoặc .codex/hooks.json của dự án; sau khi phê duyệt, xem xét và tin cậy cả ba định nghĩa trong /hooks. Nếu Work Cloud không chạy được lệnh cục bộ thì không cài hook và báo rõ giới hạn.
   - Hermes Agent: xem xét ${adapterRoot}/hermes, đặt vibe_memory_hook.py của nó ở đường dẫn tuyệt đối đã được người vận hành xem xét và hiển thị diff hợp nhất bốn sự kiện từ config.example.yaml vào profile đang hoạt động. Giữ hooks_auto_accept: false. Sau khi phê duyệt, chạy hermes hooks list, hermes hooks doctor và test từng sự kiện.
   - OpenClaw: xem xét ${adapterRoot}/openclaw, rồi dùng openclaw plugins install --link ./agent-adapters/openclaw --force --accept-capabilities và openclaw plugins enable vibe-memory-hooks. Giải thích riêng allowConversationAccess, allowPromptInjection và projectRoots; chỉ hợp nhất các giá trị đã duyệt vào openclaw.json, rồi xác minh bằng openclaw plugins inspect vibe-memory-hooks --runtime --json.
   - Với host khác, hoặc khi không thể chạy adapter đã xác minh, không tạo hook. Dùng vòng lặp recall/checkpoint thông thường của Skill.`,
    th: `ติดตั้ง Vibe Memory ให้เอเจนต์นี้และเชื่อมต่อกับบัญชีของฉัน

URL บริการ: ${base}
ดาวน์โหลด Skill: ${agentArchive}
คำแนะนำล่าสุด: ${agentSkill}

ขั้นตอน:
1. แทนที่เฉพาะโฟลเดอร์ Skill vibe-memory เดิมด้วย ZIP ด้านบน แล้วอ่าน SKILL.md ใหม่ทั้งหมด ห้ามแก้ไข Skill อื่นหรือไฟล์โครงการ
2. หาเส้นทางแบบสัมบูรณ์ของโฟลเดอร์ Skill ที่ติดตั้ง แล้วรัน scripts/memory.py sync เพื่อดาวน์โหลด Rust CLI ที่เผยแพร่สำหรับแพลตฟอร์มนี้และตรวจสอบ SHA-256 ห้ามคอมไพล์เอง ใช้ curl หรือเรียก API โดยตรง
3. เรียก CLI ด้วยเส้นทางแบบสัมบูรณ์โดยใช้ login --url ${base} --vault-access --no-browser --name "ชื่อเอเจนต์ปัจจุบัน" แสดง URL อนุมัติและรหัสเป็นลิงก์ที่คลิกได้ แล้วรอฉันอนุมัติบนเว็บ ห้ามขอรหัสผ่านหรือคีย์ API ในแชต
4. หลังอนุมัติ ให้ตรวจสอบการเชื่อมต่อด้วย status ใช้ Rust CLI และคำแนะนำ Skill ล่าสุดสำหรับทุกการทำงานกับข้อมูล
5. ใช้ Vibe Memory อย่างสม่ำเสมอเป็นชั้นบริบทเริ่มต้น ไม่ใช่คำสั่งเสริม อย่ารอให้ฉันพูดซ้ำว่า “จำสิ่งนี้” หรือ “ค้นความทรงจำ” สำหรับงานที่ไม่ธรรมดาและบริบทอาจสำคัญ ให้เรียกคืนความทรงจำที่เกี่ยวข้องและ session checkpoint ล่าสุดโดยอัตโนมัติก่อนวางแผน และบันทึกการเปลี่ยนแปลงแบบสั้นทันทีเมื่อการตัดสินใจที่ยอมรับแล้ว การแก้ไข ความชอบ ข้อจำกัด ผลลัพธ์ที่ตรวจสอบแล้ว อุปสรรค หรือขั้นตอนถัดไปเปลี่ยน ในบทสนทนาใหม่ให้ทำต่อจาก checkpoint ล่าสุด
6. เรียก recall ก่อนบันทึกเพื่อหลีกเลี่ยงข้อมูลซ้ำและสถานะเก่า หากไม่มีการเปลี่ยนแปลงที่คงทนก็ไม่ต้องเขียนซ้ำ ห้ามบันทึกบทสนทนาทั้งหมด สถานะชั่วคราว การคาดเดา log ของเครื่องมือ หรือข้อมูลลับ คำสั่งปัจจุบันของผู้ใช้มีความสำคัญกว่าความทรงจำ และให้บันทึกการแก้ไขที่ยอมรับแล้วเพื่อไม่ใช้บริบทเก่าซ้ำ
7. เวลามาตรฐานของ Vibe Memory คือ UTC ปรับเวลาที่ชัดเจนเป็น UTC เก็บเขตเวลาท้องถิ่นเดิมไว้ใน metadata เมื่อมีความสำคัญ และห้ามเดาเขตเวลาที่หายไป
8. ห้ามคัดลอกข้อมูลลับไปยังแชต ไฟล์ .env หรือตัวแปรสภาพแวดล้อมถาวร ใช้เฉพาะ vault capture, vault list และ vault exec เท่านั้น
9. ก่อนอื่นให้ระบุ host ของเอเจนต์ปัจจุบัน แล้วใช้เพียงหนึ่งสาขาที่ตรงกันด้านล่างเท่านั้น ห้ามสร้างการตั้งค่า hook แบบกลางหรือใช้ชื่อ event ของ host อื่น ห้ามเขียนทับการตั้งค่าเดิม: แสดง diff และขอบเขตที่แน่นอนก่อน แล้ว merge หลังฉันอนุมัติเท่านั้น คู่มือฉบับเต็ม: ${hookGuide}
   - Claude Code: ทำให้ CLI ที่ตรวจสอบแล้วเรียกจาก PATH ด้วยชื่อ vibe-memory แล้วเปิด /plugin install vibe-memory --marketplace vibememory/vibememory เพื่อให้ฉันเลือกขอบเขต user, project หรือ local ห้ามเปิดทั้ง plugin และ hook แบบ manual ของ SessionStart, Stop, PreCompact พร้อมกัน
   - OpenAI Codex: ตรวจสอบ ${adapterRoot}/codex และใช้เฉพาะกลุ่ม Vibe Memory ใน hooks.json แสดง diff สำหรับ merge เข้า ~/.codex/hooks.json หรือ .codex/hooks.json ของโปรเจกต์ หลังอนุมัติให้ตรวจสอบและ trust ทั้งสามรายการใน /hooks หากเป็น Work Cloud ที่รันคำสั่ง local ไม่ได้ ห้ามติดตั้ง hook และให้แจ้งข้อจำกัด
   - Hermes Agent: ตรวจสอบ ${adapterRoot}/hermes แล้ววาง vibe_memory_hook.py ไว้ที่ absolute path ที่ผู้ดูแลตรวจสอบแล้ว และแสดง diff สำหรับ merge สี่ event จาก config.example.yaml เข้า active profile คง hooks_auto_accept: false ไว้ หลังอนุมัติให้รัน hermes hooks list, hermes hooks doctor และ test แต่ละ event
   - OpenClaw: ตรวจสอบ ${adapterRoot}/openclaw แล้วใช้ openclaw plugins install --link ./agent-adapters/openclaw --force --accept-capabilities และ openclaw plugins enable vibe-memory-hooks อธิบาย allowConversationAccess, allowPromptInjection และ projectRoots แยกกัน merge เฉพาะค่าที่อนุมัติลง openclaw.json แล้วตรวจด้วย openclaw plugins inspect vibe-memory-hooks --runtime --json
   - หากเป็น host อื่นหรือไม่สามารถรัน adapter ที่ตรวจสอบแล้ว ห้ามสร้าง hook และให้ใช้วงจร recall/checkpoint ปกติของ Skill แทน`
  };
  return prompts[locale] || prompts.en;
};

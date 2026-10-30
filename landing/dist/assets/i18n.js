'use strict';
(() => {
  const supported = ['ko', 'en', 'zh', 'ja', 'es', 'vi', 'th'];
  const localeTags = {ko:'ko-KR',en:'en-US',zh:'zh-CN',ja:'ja-JP',es:'es-ES',vi:'vi-VN',th:'th-TH'};
  const labels = {ko:'한국어',en:'English',zh:'中文',ja:'日本語',es:'Español',vi:'Tiếng Việt',th:'ไทย'};
  const pageTitles = {
    '/': {ko:'에이전트가 바뀌어도, 기억은 이어지도록 — Vibe Memory',en:'One memory for every agent — Vibe Memory',zh:'让记忆跨越每个智能体 — Vibe Memory',ja:'エージェントが変わっても、記憶は続く — Vibe Memory',es:'Una memoria para todos tus agentes — Vibe Memory',vi:'Một bộ nhớ cho mọi tác nhân — Vibe Memory',th:'หนึ่งความทรงจำสำหรับทุกเอเจนต์ — Vibe Memory'},
    '/login': {ko:'로그인 — Vibe Memory',en:'Log in — Vibe Memory',zh:'登录 — Vibe Memory',ja:'ログイン — Vibe Memory',es:'Iniciar sesión — Vibe Memory',vi:'Đăng nhập — Vibe Memory',th:'เข้าสู่ระบบ — Vibe Memory'},
    '/connect': {ko:'에이전트 연결 — Vibe Memory',en:'Connect agent — Vibe Memory',zh:'连接智能体 — Vibe Memory',ja:'エージェント接続 — Vibe Memory',es:'Conectar agente — Vibe Memory',vi:'Kết nối tác nhân — Vibe Memory',th:'เชื่อมต่อเอเจนต์ — Vibe Memory'},
    '/console': {ko:'워크스페이스 — Vibe Memory',en:'Workspace — Vibe Memory',zh:'工作区 — Vibe Memory',ja:'ワークスペース — Vibe Memory',es:'Espacio de trabajo — Vibe Memory',vi:'Không gian làm việc — Vibe Memory',th:'พื้นที่ทำงาน — Vibe Memory'},
    '/guide': {ko:'연결 가이드 — Vibe Memory',en:'Connection guide — Vibe Memory',zh:'连接指南 — Vibe Memory',ja:'接続ガイド — Vibe Memory',es:'Guía de conexión — Vibe Memory',vi:'Hướng dẫn kết nối — Vibe Memory',th:'คู่มือการเชื่อมต่อ — Vibe Memory'},
    '/admin': {ko:'관리자 — Vibe Memory',en:'Admin — Vibe Memory',zh:'管理控制台 — Vibe Memory',ja:'管理コンソール — Vibe Memory',es:'Administración — Vibe Memory',vi:'Quản trị — Vibe Memory',th:'ผู้ดูแล — Vibe Memory'},
    '/capture': {ko:'Vault 보안 입력 — Vibe Memory',en:'Secure Vault input — Vibe Memory',zh:'Vault 安全输入 — Vibe Memory',ja:'Vault安全入力 — Vibe Memory',es:'Entrada segura de Vault — Vibe Memory',vi:'Nhập Vault an toàn — Vibe Memory',th:'ป้อนข้อมูล Vault อย่างปลอดภัย — Vibe Memory'},
    '/404': {ko:'페이지를 찾을 수 없습니다 — Vibe Memory',en:'Page not found — Vibe Memory',zh:'未找到页面 — Vibe Memory',ja:'ページが見つかりません — Vibe Memory',es:'Página no encontrada — Vibe Memory',vi:'Không tìm thấy trang — Vibe Memory',th:'ไม่พบหน้า — Vibe Memory'}
  };
  const pageMetadata = {
    '/': {
      description:{ko:'흩어진 에이전트에 하나의 기억을 연결하세요. 에이전트가 이해하고, Vibe Memory가 기억과 관계를 관리합니다. 키워드 검색과 compact CLI Skill로 시작하는 개인 기억 서비스.',en:'Connect every agent to one personal memory. Agents understand; Vibe Memory manages memories and relationships with keyword search and a compact CLI Skill.',zh:'将所有智能体连接到同一份个人记忆。智能体负责理解，Vibe Memory 通过关键词搜索与紧凑 CLI Skill 管理记忆和关系。',ja:'すべてのエージェントをひとつの個人記憶へ。理解はエージェント、記憶と関係の管理はVibe Memory。キーワード検索とcompact CLI Skillですぐ始められます。',es:'Conecta todos tus agentes a una memoria personal. Los agentes comprenden; Vibe Memory gestiona recuerdos y relaciones con búsqueda por palabras y un CLI Skill compacto.',vi:'Kết nối mọi tác nhân vào một bộ nhớ cá nhân. Tác nhân hiểu; Vibe Memory quản lý ký ức và quan hệ bằng tìm kiếm từ khóa và CLI Skill gọn nhẹ.',th:'เชื่อมทุกเอเจนต์เข้ากับความทรงจำส่วนบุคคลเดียว เอเจนต์ทำความเข้าใจ ส่วน Vibe Memory จัดการความทรงจำและความสัมพันธ์ด้วยการค้นหาคีย์เวิร์ดและ CLI Skill แบบกระชับ'},
      ogTitle:{ko:'Vibe Memory — 하나의 기억, 모든 에이전트',en:'Vibe Memory — One memory, every agent',zh:'Vibe Memory — 一份记忆，所有智能体',ja:'Vibe Memory — ひとつの記憶を、すべてのエージェントへ',es:'Vibe Memory — Una memoria para todos tus agentes',vi:'Vibe Memory — Một bộ nhớ cho mọi tác nhân',th:'Vibe Memory — หนึ่งความทรงจำสำหรับทุกเอเจนต์'},
      ogDescription:{ko:'에이전트가 생각하고, 기억은 연결됩니다. 개인 기억 그래프와 키워드 검색을 compact CLI Skill로 연결하세요.',en:'Agents think; memory stays connected. Link a personal memory graph and keyword search through a compact CLI Skill.',zh:'智能体负责思考，记忆持续相连。通过紧凑 CLI Skill 连接个人记忆图谱与关键词搜索。',ja:'考えるのはエージェント、つながるのは記憶。個人記憶グラフとキーワード検索をcompact CLI Skillで接続します。',es:'Los agentes piensan; la memoria permanece conectada. Conecta un grafo personal y búsqueda por palabras mediante un CLI Skill compacto.',vi:'Tác nhân suy nghĩ; ký ức luôn kết nối. Liên kết đồ thị ký ức cá nhân và tìm kiếm từ khóa qua CLI Skill gọn nhẹ.',th:'เอเจนต์คิด ความทรงจำเชื่อมต่ออยู่เสมอ เชื่อมกราฟความทรงจำส่วนบุคคลและการค้นหาคีย์เวิร์ดผ่าน CLI Skill แบบกระชับ'}
    },
    '/guide': {
      description:{ko:'Vibe Memory CLI Skill 연결, 키워드 검색, byte stream 파일 업로드 가이드.',en:'Guide to Vibe Memory CLI Skill connections, keyword search, and byte-stream file uploads.',zh:'Vibe Memory CLI Skill 连接、关键词搜索与字节流文件上传指南。',ja:'Vibe Memory CLI Skill接続、キーワード検索、バイトストリームアップロードのガイド。',es:'Guía de conexión del CLI Skill, búsqueda por palabras y carga de archivos como bytes.',vi:'Hướng dẫn kết nối CLI Skill, tìm kiếm từ khóa và tải tệp dạng byte stream.',th:'คู่มือเชื่อมต่อ CLI Skill การค้นหาคีย์เวิร์ด และการอัปโหลดไฟล์แบบ byte stream'}
    }
  };
  const detected = (navigator.language || 'ko').toLowerCase().split('-')[0];
  function readStoredLocale() {
    try { return localStorage.getItem('vm-language'); } catch { return null; }
  }
  function storeLocale(value) {
    try { localStorage.setItem('vm-language', value); } catch { /* Language switching must still work. */ }
  }
  let locale = readStoredLocale() || (supported.includes(detected) ? detected : 'en');
  if (!supported.includes(locale)) locale = 'en';

  const rows = [
    ['작동 방식','How it works','工作原理','仕組み','Cómo funciona'],
    ['직접 살펴보기','Explore','亲自体验','試してみる','Explorar'],
    ['문서','Docs','文档','ドキュメント','Documentación'],
    ['로그인','Log in','登录','ログイン','Iniciar sesión'],
    ['콘솔로 이동','Open console','打开控制台','コンソールへ','Abrir consola'],
    ['설치 프롬프트 복사하기','Copy install prompt','复制安装提示词','インストールプロンプトをコピー','Copiar prompt de instalación'],
    ['GitHub에서 self-host','Self-host on GitHub','在 GitHub 上自托管','GitHubでセルフホスト','Autoalojar desde GitHub'],
    ['에이전트가 바뀌어도,','Even when agents change,','即使更换智能体，','エージェントが変わっても、','Aunque cambies de agente,'],
    ['기억은 ','your memory ','记忆仍会','記憶は','tu memoria '],
    ['이어지도록.','continues.','延续。','つながり続ける。','continúa.'],
    ['매번 나를 처음부터 설명하지 마세요.','Stop explaining yourself from scratch.','不必每次都从头介绍自己。','毎回ゼロから説明する必要はありません。','No vuelvas a explicarte desde cero.'],
    ['취향부터 프로젝트의 맥락까지, 흩어진 에이전트를','From preferences to project context, connect scattered agents','从偏好到项目上下文，将分散的智能体','好みからプロジェクトの文脈まで、散らばったエージェントを','Desde tus preferencias hasta el contexto del proyecto, conecta tus agentes'],
    [' 하나의 기억으로 연결합니다.','to one shared memory.','连接到同一份记忆。','ひとつの記憶につなぎます。','a una memoria compartida.'],
    ['대화가 달라도','Across conversations','跨对话','会話が変わっても','Entre conversaciones'],
    ['도구가 달라도','Across tools','跨工具','ツールが変わっても','Entre herramientas'],
    ['기억은 하나로','One shared memory','一份共享记忆','記憶はひとつ','Una sola memoria'],
    ['생각은 에이전트가.','Agents do the thinking.','智能体负责思考。','考えるのはエージェント。','Los agentes piensan.'],
    ['기억의 관리는 Vibe Memory가.','Vibe Memory manages the memory.','Vibe Memory 管理记忆。','記憶の管理はVibe Memory。','Vibe Memory gestiona la memoria.'],
    ['이미 똑똑한 에이전트에, 기억할 공간을 더합니다.','Give capable agents a place to remember.','为智能体增加可持续的记忆空间。','賢いエージェントに、記憶する場所を。','Da a tus agentes un lugar donde recordar.'],
    ['앱이 다시 추론하지 않아도 맥락은 이어집니다.','Context continues without another model pass.','无需应用再次推理，上下文也能延续。','アプリが再推論しなくても文脈は続きます。','El contexto continúa sin otra inferencia.'],
    ['에이전트가 이해하고','The agent understands','智能体理解','エージェントが理解','El agente entiende'],
    ['앱이 연결해 보관하고','The app stores connections','应用保存连接','アプリがつないで保存','La app guarda conexiones'],
    ['어디서든 다시 꺼내요','Recall it anywhere','随处取回','どこでも呼び出す','Recupéralo en cualquier lugar'],
    ['기억이 오가는 순간을','See memory in motion','查看记忆如何流动','記憶が行き交う瞬間を','Mira la memoria en movimiento'],
    ['직접 살펴보세요.','for yourself.','亲自体验。','実際に見てみましょう。','por ti mismo.'],
    ['기억 저장','Save memory','保存记忆','記憶を保存','Guardar memoria'],
    ['파일 등록','Register file','登记文件','ファイル登録','Registrar archivo'],
    ['키워드 검색','Keyword search','关键词搜索','キーワード検索','Buscar por palabras clave'],
    ['복사','Copy','复制','コピー','Copiar'],
    ['단편적인 기록을 넘어,','Beyond isolated notes,','超越零散记录，','断片的な記録を超えて、','Más allá de notas aisladas,'],
    ['연결된 나의 맥락으로.','build connected context.','构建相连的上下文。','つながる自分の文脈へ。','crea un contexto conectado.'],
    ['기억 사이에도','Connect memories','连接记忆','記憶どうしにも','Conecta memorias'],
    ['이유 있는 연결을.','with evidence.','并保留依据。','根拠あるつながりを。','con evidencia.'],
    ['필요한 키워드만, 가볍게.','Only the keywords you need.','只处理必要的关键词。','必要なキーワードだけ。','Solo las palabras clave necesarias.'],
    ['도구는 달라도, 같은 나.','Different tools, the same you.','工具不同，仍是同一个你。','ツールが違っても、同じ自分。','Distintas herramientas, el mismo tú.'],
    ['다음 대화는,','Let the next conversation','让下一次对话','次の会話は、','Haz que la próxima conversación'],
    ['이미 알고 있는 사이로.','start with context.','从已知上下文开始。','もう知っている関係から。','empiece con contexto.'],
    ['Skill 내려받기','Download Skill','下载 Skill','Skillをダウンロード','Descargar Skill'],
    ['연결 가이드 읽기','Read connection guide','阅读连接指南','接続ガイドを読む','Leer guía de conexión'],
    ['궁금할 수 있는 것들.','Things you may wonder.','你可能想了解的问题。','よくある質問。','Preguntas frecuentes.'],
    ['Vibe Memory가 직접 LLM을 호출하나요?','Does Vibe Memory call an LLM?','Vibe Memory 会调用 LLM 吗？','Vibe MemoryはLLMを呼び出しますか？','¿Vibe Memory llama a un LLM?'],
    ['아니요. 엔티티·관계 추론, 파일 분석, 키워드 추출과 답변 생성은 연결된 에이전트가 담당합니다. 앱은 전달받은 데이터를 관리하고 키워드만 로컬에서 임베딩합니다.','No. Connected agents infer entities and relationships, analyze files, extract keywords, and compose answers. The app manages supplied data and embeds only keywords locally.','不会。实体与关系推理、文件分析、关键词提取和回答生成均由连接的智能体完成。应用仅管理提交的数据并在本地嵌入关键词。','いいえ。エンティティ・関係推論、ファイル分析、キーワード抽出、回答生成は接続したエージェントが行います。アプリは受け取ったデータを管理し、キーワードだけをローカルで埋め込みます。','No. Los agentes conectados infieren entidades y relaciones, analizan archivos, extraen palabras clave y redactan respuestas. La app gestiona los datos enviados y solo vectoriza palabras clave localmente.'],
    ['어떤 에이전트에 연결할 수 있나요?','Which agents can connect?','可以连接哪些智能体？','どのエージェントに接続できますか？','¿Qué agentes se pueden conectar?'],
    ['파일은 어떻게 저장하나요?','How are files stored?','文件如何存储？','ファイルはどう保存されますか？','¿Cómo se almacenan los archivos?'],
    ['지금 바로 사용할 수 있나요?','Can I use it now?','现在可以使用吗？','今すぐ使えますか？','¿Puedo usarlo ahora?'],
    ['서비스 소개로 돌아가기','Back to overview','返回产品介绍','サービス紹介に戻る','Volver a la presentación'],
    ['다음 대화도,','Let every conversation','让每次对话','次の会話も、','Haz que cada conversación'],
    ['이어지는 나의 기억.','continue your memory.','延续你的记忆。','記憶を引き継ぐ。','continúe tu memoria.'],
    ['하나의 계정으로 기억을 관리하고,','Manage memory with one account,','用一个账户管理记忆，','ひとつのアカウントで記憶を管理し、','Gestiona la memoria con una cuenta,'],
    ['내 에이전트에게 같은 맥락을 연결하세요.','and connect the same context to every agent.','并将同一上下文连接到所有智能体。','同じ文脈をすべてのエージェントへ。','y conecta el mismo contexto a todos tus agentes.'],
    ['다시 만나 반가워요.','Welcome back.','欢迎回来。','おかえりなさい。','Te damos la bienvenida.'],
    ['로그인하고 나의 기억을 이어가세요.','Log in to continue your memory.','登录以继续你的记忆。','ログインして記憶を続けましょう。','Inicia sesión para continuar tu memoria.'],
    ['회원가입','Sign up','注册','新規登録','Registrarse'],
    ['이름','Name','姓名','名前','Nombre'],
    ['어떻게 불러드릴까요?','What should we call you?','我们该如何称呼你？','何とお呼びしますか？','¿Cómo te llamamos?'],
    ['이메일','Email','邮箱','メール','Correo'],
    ['비밀번호','Password','密码','パスワード','Contraseña'],
    ['10자 이상 입력해주세요','Enter at least 10 characters','请输入至少 10 个字符','10文字以上で入力してください','Introduce al menos 10 caracteres'],
    ['보기','Show','显示','表示','Mostrar'],
    ['숨기기','Hide','隐藏','非表示','Ocultar'],
    ['내 계정에 저장된 기억만 볼 수 있습니다.','Only memories stored in your account are visible.','只有你账户中的记忆可见。','自分のアカウントに保存された記憶だけが表示されます。','Solo puedes ver las memorias de tu cuenta.'],
    ['계정 만들고 시작하기','Create account and start','创建账户并开始','アカウントを作成','Crear cuenta y empezar'],
    ['나의 기억을 시작해요.','Start your memory.','开始你的记忆。','記憶を始めましょう。','Empieza tu memoria.'],
    ['계정을 만들고 에이전트에 기억을 연결하세요.','Create an account and connect memory to your agents.','创建账户并将记忆连接到智能体。','アカウントを作成して記憶をエージェントにつなぎましょう。','Crea una cuenta y conecta la memoria a tus agentes.'],
    ['에이전트 연결','Agent connections','智能体连接','エージェント接続','Conexiones de agentes'],
    ['연결 요청을 확인하고 있습니다.','Checking the connection request.','正在检查连接请求。','接続リクエストを確認しています。','Comprobando la solicitud de conexión.'],
    ['계정:','Account:','账户：','アカウント：','Cuenta:'],
    ['에이전트:','Agent:','智能体：','エージェント：','Agente:'],
    ['확인 코드:','Confirmation code:','确认码：','確認コード：','Código de confirmación:'],
    ['연결 승인','Approve connection','批准连接','接続を承認','Aprobar conexión'],
    ['거절','Deny','拒绝','拒否','Rechazar'],
    ['대시보드','Dashboard','仪表板','ダッシュボード','Panel'],
    ['기억','Memories','记忆','記憶','Memorias'],
    ['문서 · 파일','Documents · Files','文档 · 文件','文書 · ファイル','Documentos · Archivos'],
    ['관계 그래프','Relationship graph','关系图谱','関係グラフ','Grafo de relaciones'],
    ['기능 요청','Feature requests','功能请求','機能リクエスト','Solicitudes de funciones'],
    ['도움이 필요하신가요?','Need help?','需要帮助？','お困りですか？','¿Necesitas ayuda?'],
    ['연결 가이드 보기','View connection guide','查看连接指南','接続ガイドを見る','Ver guía de conexión'],
    ['로그인 확인 중…','Checking session…','正在检查登录状态…','ログインを確認中…','Comprobando sesión…'],
    ['서비스 홈','Service home','服务首页','サービスホーム','Inicio'],
    ['로그아웃','Log out','退出登录','ログアウト','Cerrar sesión'],
    ['기억 검색','Search memories','搜索记忆','記憶を検索','Buscar memorias'],
    ['API 정상','API healthy','API 正常','API 正常','API operativa'],
    ['에이전트와 함께 쌓아가는 기억을 한곳에서 관리하세요.','Manage memories created with your agents in one place.','在一处管理与智能体共同积累的记忆。','エージェントと積み重ねた記憶を一か所で管理します。','Gestiona en un solo lugar las memorias creadas con tus agentes.'],
    ['워크스페이스를 불러오는 중입니다…','Loading workspace…','正在加载工作区…','ワークスペースを読み込み中…','Cargando espacio de trabajo…'],
    ['취소','Cancel','取消','キャンセル','Cancelar'],
    ['저장','Save','保存','保存','Guardar'],
    ['상세 정보','Details','详细信息','詳細','Detalles'],
    ['닫기','Close','关闭','閉じる','Cerrar'],
    ['삭제','Delete','删除','削除','Eliminar'],
    ['다운로드','Download','下载','ダウンロード','Descargar'],
    ['키워드 없음','No keywords','无关键词','キーワードなし','Sin palabras clave'],
    ['불러오는 중…','Loading…','加载中…','読み込み中…','Cargando…'],
    ['이전','Previous','上一页','前へ','Anterior'],
    ['다음','Next','下一页','次へ','Siguiente'],
    ['검색','Search','搜索','検索','Buscar'],
    ['기억 추가','Add memory','添加记忆','記憶を追加','Añadir memoria'],
    ['파일 업로드','Upload file','上传文件','ファイルをアップロード','Subir archivo'],
    ['API 키 만들기','Create API key','创建 API 密钥','APIキーを作成','Crear clave API'],
    ['비밀 추가','Add secret','添加密钥','シークレットを追加','Añadir secreto'],
    ['기능 요청 남기기','Submit feature request','提交功能请求','機能リクエストを送信','Enviar solicitud'],
    ['설치·최신화 프롬프트 복사','Copy install/update prompt','复制安装/更新提示词','インストール・更新プロンプトをコピー','Copiar prompt de instalación/actualización'],
    ['활성 연결','Active connections','活跃连接','有効な接続','Conexiones activas'],
    ['에이전트 이름','Agent name','智能体名称','エージェント名','Nombre del agente'],
    ['키 식별자','Key identifier','密钥标识','キー識別子','Identificador'],
    ['연결일','Connected','连接日期','接続日','Conectado'],
    ['허용됨','Allowed','已允许','許可済み','Permitido'],
    ['차단됨','Blocked','已阻止','ブロック済み','Bloqueado'],
    ['연결 해제','Disconnect','断开连接','接続解除','Desconectar'],
    ['접수됨','Received','已接收','受付済み','Recibida'],
    ['등록일','Created','创建日期','登録日','Creada'],
    ['이름 · 내용','Name · Content','名称 · 内容','名前 · 内容','Nombre · Contenido'],
    ['키워드','Keywords','关键词','キーワード','Palabras clave'],
    ['사용 횟수','Uses','使用次数','使用回数','Usos'],
    ['마지막 사용','Last used','上次使用','最終使用','Último uso'],
    ['교체','Rotate','轮换','更新','Rotar'],
    ['연결 준비','Prepare connection','连接准备','接続準備','Preparar conexión'],
    ['Skill 연결','Connect Skill','连接 Skill','Skill接続','Conectar Skill'],
    ['기억 저장과 검색','Save and search memories','保存和搜索记忆','記憶の保存と検索','Guardar y buscar memorias'],
    ['파일 업로드','File upload','文件上传','ファイルアップロード','Carga de archivos'],
    ['엔티티와 관계','Entities and relationships','实体与关系','エンティティと関係','Entidades y relaciones'],
    ['API 참조','API reference','API 参考','APIリファレンス','Referencia API'],
    ['랜딩 페이지로 돌아가기','Back to landing page','返回落地页','ランディングページに戻る','Volver a la página principal'],
    ['하나의 기억을,','One memory,','一份记忆，','ひとつの記憶を、','Una memoria,'],
    ['나의 에이전트에.','for every agent.','连接到我的智能体。','自分のエージェントへ。','para todos mis agentes.'],
    ['Vibe Memory 홈','Vibe Memory home','Vibe Memory 首页','Vibe Memoryホーム','Inicio de Vibe Memory'],
    ['언어 선택','Select language','选择语言','言語を選択','Seleccionar idioma'],
    ['잠시만 기다려주세요…','Please wait…','请稍候…','しばらくお待ちください…','Espera un momento…'],
    ['서버에 연결할 수 없습니다. 잠시 후 다시 시도해주세요.','Cannot reach the server. Please try again shortly.','无法连接服务器，请稍后重试。','サーバーに接続できません。しばらくしてから再試行してください。','No se puede conectar al servidor. Inténtalo de nuevo en breve.'],
    ['로그인이 필요합니다.','Please log in.','请先登录。','ログインが必要です。','Inicia sesión.'],
    ['입력한 내용을 확인해주세요.','Check the information you entered.','请检查输入内容。','入力内容を確認してください。','Revisa la información introducida.'],
    ['설치·최신화 프롬프트를 복사했습니다. 에이전트 대화에 붙여넣으세요.','Install/update prompt copied. Paste it into your agent chat.','已复制安装/更新提示词，请粘贴到智能体对话中。','インストール・更新プロンプトをコピーしました。エージェントのチャットに貼り付けてください。','Prompt de instalación/actualización copiado. Pégalo en el chat del agente.'],
    ['사용할 서비스들에','Connect the services you use','将常用服务','使いたいサービスに','Conecta tus servicios'],
    ['바로 연결하세요.','right away.','立即连接。','すぐ接続。','al instante.'],
    ['대화형 에이전트는 MCP로, 코딩 에이전트는 Skill로 연결할 수 있습니다.','Connect conversational agents with MCP and coding agents with a Skill.','通过 MCP 连接对话智能体，通过 Skill 连接编程智能体。','会話エージェントはMCP、コーディングエージェントはSkillで接続できます。','Conecta agentes conversacionales con MCP y agentes de código con un Skill.'],
    ['ChatGPT Work에 설치하거나 Claude에서 연결','Install in ChatGPT Work or connect Claude','安装到 ChatGPT Work 或连接 Claude','ChatGPT Workにインストール、またはClaudeに接続','Instala en ChatGPT Work o conecta Claude'],
    ['ChatGPT Work는 Vibe Memory Plugin 설치 화면으로 바로 이동합니다. Claude는 MCP 주소를 복사한 뒤 커넥터 화면을 엽니다.','ChatGPT Work opens the Vibe Memory Plugin install page directly. Claude copies the MCP URL and opens its connector page.','ChatGPT Work 会直接打开 Vibe Memory 插件安装页面。Claude 会复制 MCP 地址并打开连接器页面。','ChatGPT WorkはVibe Memory Pluginのインストール画面を直接開きます。ClaudeはMCP URLをコピーしてコネクター画面を開きます。','ChatGPT Work abre directamente la instalación del Plugin de Vibe Memory. Claude copia la URL de MCP y abre la página del conector.'],
    ['ChatGPT Work에 바로 설치','Install in ChatGPT Work','安装到 ChatGPT Work','ChatGPT Workにインストール','Instalar en ChatGPT Work'],
    ['Claude에서 사용','Use with Claude','在 Claude 中使用','Claudeで使用','Usar con Claude'],
    ['에이전트에 Skill 설치','Install the Skill in your agent','在智能体中安装 Skill','エージェントにSkillをインストール','Instalar el Skill en tu agente'],
    ['설치·최신화·웹 인증까지 에이전트가 진행하도록 현재 언어의 프롬프트를 복사합니다.','Copy a prompt in your language so the agent handles installation, updates, and web authorization.','复制当前语言的提示词，让智能体完成安装、更新和网页授权。','インストール・更新・Web認証までエージェントが進める、現在の言語のプロンプトをコピーします。','Copia un prompt en tu idioma para que el agente gestione la instalación, las actualizaciones y la autorización web.'],
    ['스킬 설치 프롬프트 복사','Copy Skill install prompt','复制 Skill 安装提示词','Skillインストールプロンプトをコピー','Copiar prompt de instalación del Skill'],
    ['MCP 주소를 복사했습니다. 열린 서비스의 커넥터에 붙여넣으세요.','MCP address copied. Paste it into the connector page that opened.','MCP 地址已复制，请粘贴到打开的连接器页面。','MCPアドレスをコピーしました。開いたサービスのコネクターに貼り付けてください。','Dirección MCP copiada. Pégala en la página de conectores que se abrió.'],
    ['MCP 주소를 복사하지 못했습니다. vibememory.io/mcp를 직접 입력해주세요.','Could not copy the MCP address. Enter vibememory.io/mcp manually.','无法复制 MCP 地址，请手动输入 vibememory.io/mcp。','MCPアドレスをコピーできませんでした。vibememory.io/mcpを直接入力してください。','No se pudo copiar la dirección MCP. Introduce vibememory.io/mcp manualmente.'],
    ['생활 속 기억 관계 예시','Everyday memory relationships','日常记忆关系示例','日常の記憶関係の例','Ejemplo de relaciones de memoria cotidianas'],
    ['나','Me','我','自分','Yo'],
    ['4개의 연결','4 connections','4 个连接','4つのつながり','4 conexiones'],
    ['여름 여행','Summer trip','夏日旅行','夏の旅行','Viaje de verano'],
    ['8월 · 오사카','August · Osaka','八月 · 大阪','8月 · 大阪','Agosto · Osaka'],
    ['아이스 아메리카노','Iced Americano','冰美式','アイスアメリカーノ','Americano con hielo'],
    ['자주 마셔요','A frequent choice','经常喝','よく飲む','Lo toma a menudo'],
    ['사이드 프로젝트','Side project','个人项目','サイドプロジェクト','Proyecto personal'],
    ['이번 주 진행 중','In progress this week','本周进行中','今週進行中','En curso esta semana'],
    ['저녁 러닝','Evening run','夜间跑步','夜のランニング','Carrera nocturna'],
    ['주 3회','3 times a week','每周 3 次','週3回','3 veces por semana']
  ];

  const viRows = [
    'Cách hoạt động',
    'Khám phá',
    'Tài liệu',
    'Đăng nhập',
    'Mở bảng điều khiển',
    'Sao chép lời nhắc cài đặt',
    'Tự lưu trữ trên GitHub',
    'Ngay cả khi đổi tác nhân,',
    'ký ức của bạn ',
    'vẫn tiếp tục.',
    'Đừng phải giải thích lại bản thân từ đầu.',
    'Từ sở thích đến bối cảnh dự án, kết nối các tác nhân rời rạc',
    'vào một bộ nhớ dùng chung.',
    'Xuyên suốt các cuộc trò chuyện',
    'Xuyên suốt các công cụ',
    'Một bộ nhớ dùng chung',
    'Tác nhân đảm nhiệm việc suy luận.',
    'Vibe Memory quản lý bộ nhớ.',
    'Cho các tác nhân thông minh một nơi để ghi nhớ.',
    'Bối cảnh được tiếp nối mà không cần thêm một lượt suy luận.',
    'Tác nhân thấu hiểu',
    'Ứng dụng lưu các kết nối',
    'Gọi lại ở bất cứ đâu',
    'Xem ký ức vận hành',
    'bằng chính bạn.',
    'Lưu ký ức',
    'Đăng ký tệp',
    'Tìm kiếm từ khóa',
    'Sao chép',
    'Vượt ra ngoài những ghi chú rời rạc,',
    'xây dựng bối cảnh được kết nối.',
    'Kết nối các ký ức',
    'bằng bằng chứng.',
    'Chỉ những từ khóa bạn cần.',
    'Công cụ khác nhau, vẫn là bạn.',
    'Để cuộc trò chuyện tiếp theo',
    'bắt đầu với bối cảnh.',
    'Tải Skill',
    'Đọc hướng dẫn kết nối',
    'Những điều bạn có thể thắc mắc.',
    'Vibe Memory có trực tiếp gọi LLM không?',
    'Không. Các tác nhân được kết nối suy luận thực thể và quan hệ, phân tích tệp, trích xuất từ khóa và soạn câu trả lời. Ứng dụng quản lý dữ liệu được gửi và chỉ nhúng từ khóa cục bộ.',
    'Có thể kết nối những tác nhân nào?',
    'Tệp được lưu như thế nào?',
    'Tôi có thể dùng ngay bây giờ không?',
    'Quay lại phần giới thiệu',
    'Để mọi cuộc trò chuyện',
    'tiếp nối ký ức của bạn.',
    'Quản lý ký ức bằng một tài khoản,',
    'và kết nối cùng bối cảnh với mọi tác nhân.',
    'Chào mừng bạn quay lại.',
    'Đăng nhập để tiếp tục ký ức của bạn.',
    'Đăng ký',
    'Tên',
    'Chúng tôi nên gọi bạn là gì?',
    'Email',
    'Mật khẩu',
    'Nhập ít nhất 10 ký tự',
    'Hiện',
    'Ẩn',
    'Chỉ những ký ức trong tài khoản của bạn mới hiển thị.',
    'Tạo tài khoản và bắt đầu',
    'Bắt đầu ký ức của bạn.',
    'Tạo tài khoản và kết nối ký ức với các tác nhân.',
    'Kết nối tác nhân',
    'Đang kiểm tra yêu cầu kết nối.',
    'Tài khoản:',
    'Tác nhân:',
    'Mã xác nhận:',
    'Phê duyệt kết nối',
    'Từ chối',
    'Bảng điều khiển',
    'Ký ức',
    'Tài liệu · Tệp',
    'Đồ thị quan hệ',
    'Yêu cầu tính năng',
    'Cần trợ giúp?',
    'Xem hướng dẫn kết nối',
    'Đang kiểm tra phiên…',
    'Trang chủ dịch vụ',
    'Đăng xuất',
    'Tìm kiếm ký ức',
    'API hoạt động',
    'Quản lý ký ức được tạo cùng các tác nhân ở một nơi.',
    'Đang tải không gian làm việc…',
    'Hủy',
    'Lưu',
    'Chi tiết',
    'Đóng',
    'Xóa',
    'Tải xuống',
    'Không có từ khóa',
    'Đang tải…',
    'Trước',
    'Tiếp',
    'Tìm kiếm',
    'Thêm ký ức',
    'Tải tệp lên',
    'Tạo khóa API',
    'Thêm bí mật',
    'Gửi yêu cầu tính năng',
    'Sao chép lời nhắc cài đặt/cập nhật',
    'Kết nối đang hoạt động',
    'Tên tác nhân',
    'Mã định danh khóa',
    'Đã kết nối',
    'Được phép',
    'Đã chặn',
    'Ngắt kết nối',
    'Đã tiếp nhận',
    'Ngày tạo',
    'Tên · Nội dung',
    'Từ khóa',
    'Lượt dùng',
    'Lần dùng cuối',
    'Thay mới',
    'Chuẩn bị kết nối',
    'Kết nối Skill',
    'Lưu và tìm kiếm ký ức',
    'Tải tệp lên',
    'Thực thể và quan hệ',
    'Tham chiếu API',
    'Quay lại trang giới thiệu',
    'Một bộ nhớ,',
    'cho mọi tác nhân.',
    'Trang chủ Vibe Memory',
    'Chọn ngôn ngữ',
    'Vui lòng chờ…',
    'Không thể kết nối máy chủ. Vui lòng thử lại sau.',
    'Vui lòng đăng nhập.',
    'Kiểm tra thông tin bạn đã nhập.',
    'Đã sao chép lời nhắc cài đặt/cập nhật. Hãy dán vào cuộc trò chuyện với tác nhân.',
    'Kết nối các dịch vụ bạn dùng',
    'ngay lập tức.',
    'Kết nối tác nhân hội thoại bằng MCP và tác nhân lập trình bằng Skill.',
    'Cài trong ChatGPT Work hoặc kết nối Claude',
    'ChatGPT Work mở thẳng trang cài Vibe Memory Plugin. Claude sao chép URL MCP và mở trang trình kết nối.',
    'Cài trong ChatGPT Work',
    'Dùng với Claude',
    'Cài Skill cho tác nhân',
    'Sao chép lời nhắc bằng ngôn ngữ hiện tại để tác nhân tự cài đặt, cập nhật và xác thực trên web.',
    'Sao chép lời nhắc cài Skill',
    'Đã sao chép địa chỉ MCP. Hãy dán vào trang trình kết nối vừa mở.',
    'Không thể sao chép địa chỉ MCP. Hãy nhập thủ công vibememory.io/mcp.',
    'Ví dụ về các mối quan hệ ký ức đời thường',
    'Tôi',
    '4 kết nối',
    'Chuyến đi mùa hè',
    'Tháng 8 · Osaka',
    'Americano đá',
    'Thường xuyên lựa chọn',
    'Dự án cá nhân',
    'Đang tiến hành tuần này',
    'Chạy bộ buổi tối',
    '3 lần mỗi tuần'
  ];

  const thRows = [
    'วิธีการทำงาน',
    'สำรวจ',
    'เอกสาร',
    'เข้าสู่ระบบ',
    'เปิดคอนโซล',
    'คัดลอกพรอมต์ติดตั้ง',
    'โฮสต์เองบน GitHub',
    'แม้จะเปลี่ยนเอเจนต์',
    'ความทรงจำของคุณ ',
    'ก็ยังต่อเนื่อง',
    'ไม่ต้องอธิบายตัวเองใหม่ตั้งแต่ต้นทุกครั้ง',
    'ตั้งแต่ความชอบถึงบริบทโครงการ เชื่อมเอเจนต์ที่กระจัดกระจาย',
    'เข้ากับหน่วยความจำเดียวกัน',
    'ข้ามบทสนทนา',
    'ข้ามเครื่องมือ',
    'หน่วยความจำเดียวกัน',
    'เอเจนต์เป็นผู้คิด',
    'Vibe Memory เป็นผู้จัดการความทรงจำ',
    'เพิ่มพื้นที่จดจำให้เอเจนต์ที่ฉลาดอยู่แล้ว',
    'บริบทยังคงต่อเนื่องโดยไม่ต้องอนุมานซ้ำ',
    'เอเจนต์เข้าใจ',
    'แอปจัดเก็บการเชื่อมโยง',
    'เรียกคืนได้ทุกที่',
    'ดูความทรงจำเคลื่อนไหว',
    'ด้วยตัวคุณเอง',
    'บันทึกความทรงจำ',
    'ลงทะเบียนไฟล์',
    'ค้นหาด้วยคำสำคัญ',
    'คัดลอก',
    'มากกว่าบันทึกที่แยกส่วน',
    'สร้างบริบทที่เชื่อมโยงกัน',
    'เชื่อมความทรงจำ',
    'พร้อมหลักฐาน',
    'เฉพาะคำสำคัญที่ต้องใช้',
    'เครื่องมือต่างกัน แต่ยังเป็นคุณคนเดิม',
    'ให้บทสนทนาครั้งถัดไป',
    'เริ่มต้นด้วยบริบท',
    'ดาวน์โหลด Skill',
    'อ่านคู่มือการเชื่อมต่อ',
    'สิ่งที่คุณอาจสงสัย',
    'Vibe Memory เรียก LLM โดยตรงหรือไม่?',
    'ไม่ เอเจนต์ที่เชื่อมต่อจะอนุมานเอนทิตีและความสัมพันธ์ วิเคราะห์ไฟล์ สกัดคำสำคัญ และสร้างคำตอบ แอปจัดการข้อมูลที่ได้รับและฝังเฉพาะคำสำคัญในเครื่อง',
    'เชื่อมต่อกับเอเจนต์ใดได้บ้าง?',
    'ไฟล์ถูกจัดเก็บอย่างไร?',
    'ใช้งานได้ทันทีหรือไม่?',
    'กลับไปหน้าภาพรวม',
    'ให้ทุกบทสนทนา',
    'สานต่อความทรงจำของคุณ',
    'จัดการความทรงจำด้วยบัญชีเดียว',
    'และเชื่อมบริบทเดียวกันกับทุกเอเจนต์',
    'ยินดีต้อนรับกลับมา',
    'เข้าสู่ระบบเพื่อสานต่อความทรงจำของคุณ',
    'สมัครสมาชิก',
    'ชื่อ',
    'ให้เราเรียกคุณว่าอะไร?',
    'อีเมล',
    'รหัสผ่าน',
    'กรอกอย่างน้อย 10 ตัวอักษร',
    'แสดง',
    'ซ่อน',
    'จะแสดงเฉพาะความทรงจำที่บันทึกในบัญชีของคุณ',
    'สร้างบัญชีและเริ่มต้น',
    'เริ่มต้นความทรงจำของคุณ',
    'สร้างบัญชีและเชื่อมความทรงจำกับเอเจนต์',
    'การเชื่อมต่อเอเจนต์',
    'กำลังตรวจสอบคำขอเชื่อมต่อ',
    'บัญชี:',
    'เอเจนต์:',
    'รหัสยืนยัน:',
    'อนุมัติการเชื่อมต่อ',
    'ปฏิเสธ',
    'แดชบอร์ด',
    'ความทรงจำ',
    'เอกสาร · ไฟล์',
    'กราฟความสัมพันธ์',
    'คำขอฟีเจอร์',
    'ต้องการความช่วยเหลือ?',
    'ดูคู่มือการเชื่อมต่อ',
    'กำลังตรวจสอบเซสชัน…',
    'หน้าหลักบริการ',
    'ออกจากระบบ',
    'ค้นหาความทรงจำ',
    'API ปกติ',
    'จัดการความทรงจำที่สร้างร่วมกับเอเจนต์ได้ในที่เดียว',
    'กำลังโหลดพื้นที่ทำงาน…',
    'ยกเลิก',
    'บันทึก',
    'รายละเอียด',
    'ปิด',
    'ลบ',
    'ดาวน์โหลด',
    'ไม่มีคำสำคัญ',
    'กำลังโหลด…',
    'ก่อนหน้า',
    'ถัดไป',
    'ค้นหา',
    'เพิ่มความทรงจำ',
    'อัปโหลดไฟล์',
    'สร้างคีย์ API',
    'เพิ่มข้อมูลลับ',
    'ส่งคำขอฟีเจอร์',
    'คัดลอกพรอมต์ติดตั้ง/อัปเดต',
    'การเชื่อมต่อที่ใช้งานอยู่',
    'ชื่อเอเจนต์',
    'ตัวระบุคีย์',
    'เชื่อมต่อแล้ว',
    'อนุญาต',
    'บล็อกแล้ว',
    'ยกเลิกการเชื่อมต่อ',
    'รับแล้ว',
    'วันที่สร้าง',
    'ชื่อ · เนื้อหา',
    'คำสำคัญ',
    'จำนวนครั้งที่ใช้',
    'ใช้ล่าสุด',
    'เปลี่ยนใหม่',
    'เตรียมการเชื่อมต่อ',
    'เชื่อมต่อ Skill',
    'บันทึกและค้นหาความทรงจำ',
    'อัปโหลดไฟล์',
    'เอนทิตีและความสัมพันธ์',
    'ข้อมูลอ้างอิง API',
    'กลับไปหน้าแรก',
    'หนึ่งความทรงจำ',
    'สำหรับทุกเอเจนต์',
    'หน้าหลัก Vibe Memory',
    'เลือกภาษา',
    'โปรดรอสักครู่…',
    'ไม่สามารถเชื่อมต่อเซิร์ฟเวอร์ โปรดลองอีกครั้งในภายหลัง',
    'กรุณาเข้าสู่ระบบ',
    'ตรวจสอบข้อมูลที่กรอก',
    'คัดลอกพรอมต์ติดตั้ง/อัปเดตแล้ว ให้วางในแชตของเอเจนต์',
    'เชื่อมต่อบริการที่คุณใช้',
    'ได้ทันที',
    'เชื่อมเอเจนต์สนทนาด้วย MCP และเอเจนต์เขียนโค้ดด้วย Skill',
    'ติดตั้งใน ChatGPT Work หรือเชื่อมต่อ Claude',
    'ChatGPT Work จะเปิดหน้าติดตั้ง Vibe Memory Plugin โดยตรง ส่วน Claude จะคัดลอก URL MCP และเปิดหน้าตัวเชื่อมต่อ',
    'ติดตั้งใน ChatGPT Work',
    'ใช้กับ Claude',
    'ติดตั้ง Skill ในเอเจนต์',
    'คัดลอกพรอมต์ในภาษาปัจจุบันเพื่อให้เอเจนต์ดำเนินการติดตั้ง อัปเดต และยืนยันผ่านเว็บ',
    'คัดลอกพรอมต์ติดตั้ง Skill',
    'คัดลอกที่อยู่ MCP แล้ว ให้วางในหน้าตัวเชื่อมต่อที่เปิดขึ้น',
    'คัดลอกที่อยู่ MCP ไม่สำเร็จ โปรดป้อน vibememory.io/mcp ด้วยตนเอง',
    'ตัวอย่างความสัมพันธ์ของความทรงจำในชีวิตประจำวัน',
    'ฉัน',
    '4 ความเชื่อมโยง',
    'ทริปฤดูร้อน',
    'สิงหาคม · โอซาก้า',
    'อเมริกาโนเย็น',
    'เลือกดื่มบ่อย',
    'โปรเจกต์ส่วนตัว',
    'กำลังดำเนินการสัปดาห์นี้',
    'วิ่งช่วงเย็น',
    '3 ครั้งต่อสัปดาห์'
  ];

  if (viRows.length !== rows.length || thRows.length !== rows.length) throw new Error('Locale rows are incomplete');
  const translations = new Map(rows.map((row, index) => [row[0].trim(), {ko:row[0].trim(),en:row[1].trim(),zh:row[2].trim(),ja:row[3].trim(),es:row[4].trim(),vi:viRows[index].trim(),th:thRows[index].trim()}]));
  const extraRows = [
    ['본문으로 바로가기','Skip to content','跳到正文','本文へ移動','Ir al contenido','Đi tới nội dung','ข้ามไปยังเนื้อหา'],
    ['주 메뉴','Main menu','主菜单','メインメニュー','Menú principal','Menu chính','เมนูหลัก'],
    ['연결 가이드','Connection guide','连接指南','接続ガイド','Guía de conexión','Hướng dẫn kết nối','คู่มือการเชื่อมต่อ'],
    ['로컬 키워드 임베딩','Local keyword embeddings','本地关键词嵌入','ローカルキーワード埋め込み','Embeddings locales de palabras clave','Nhúng từ khóa cục bộ','การฝังคีย์เวิร์ดในเครื่อง'],
    ['설치·최신화·웹 인증 후, 다시 말하지 않아도 에이전트가 관련 기억을 조회하고 중요한 맥락을 이어가도록 프롬프트를 복사합니다.','Copy a prompt that installs, updates, authorizes, and keeps agents using relevant memory without repeated requests.','复制提示词，让智能体完成安装、更新和网页授权，并在无需重复请求时继续使用相关记忆。','インストール・更新・Web認証を行い、毎回頼まなくても関連記憶を使い続けるプロンプトをコピーします。','Copia un prompt para instalar, actualizar, autorizar y mantener la memoria relevante sin repetir la petición.','Sao chép lời nhắc để cài đặt, cập nhật, xác thực và tiếp tục dùng ký ức liên quan mà không cần nhắc lại.','คัดลอกพรอมต์เพื่อติดตั้ง อัปเดต อนุมัติ และใช้ความทรงจำที่เกี่ยวข้องต่อไปโดยไม่ต้องสั่งซ้ำ'],
    ['하나의 기억을 공유하는 에이전트 예시','Example of agents sharing one memory','智能体共享同一份记忆的示例','ひとつの記憶を共有するエージェントの例','Ejemplo de agentes que comparten una memoria','Ví dụ các tác nhân dùng chung một bộ nhớ','ตัวอย่างเอเจนต์ที่ใช้ความทรงจำเดียวกัน'],
    ['여러 에이전트가 하나의 기억을 공유하는 인터랙티브 예시','Interactive example of agents sharing one memory','多个智能体共享同一份记忆的交互示例','複数エージェントがひとつの記憶を共有する操作例','Ejemplo interactivo de agentes compartiendo una memoria','Ví dụ tương tác về nhiều tác nhân dùng chung một bộ nhớ','ตัวอย่างแบบโต้ตอบของเอเจนต์หลายตัวที่ใช้ความทรงจำเดียวกัน'],
    ['나의 기억','My memory','我的记忆','自分の記憶','Mi memoria','Ký ức của tôi','ความทรงจำของฉัน'],
    ['Python을 선호해요','Prefers Python','偏好 Python','Pythonを好みます','Prefiere Python','Ưu tiên Python','ชอบ Python'],
    ['진행 중인 프로젝트','Active project','进行中的项目','進行中のプロジェクト','Proyecto activo','Dự án đang thực hiện','โปรเจกต์ที่กำลังทำ'],
    ['예시','Example','示例','例','Ejemplo','Ví dụ','ตัวอย่าง'],
    ['대화와 파일에서 키워드, 엔티티,','Extracts keywords and entities from conversations and files,','从对话和文件中提取关键词与实体，','会話とファイルからキーワードとエンティティを抽出し、','Extrae palabras clave y entidades de conversaciones y archivos,','Trích xuất từ khóa và thực thể từ cuộc trò chuyện và tệp,','สกัดคีย์เวิร์ดและเอนทิตีจากบทสนทนาและไฟล์'],
    ['관계와 메타정보를 추출합니다.','along with relationships and metadata.','以及关系和元数据。','関係とメタデータも抽出します。','además de relaciones y metadatos.','cùng quan hệ và metadata.','รวมถึงความสัมพันธ์และเมทาดาทา'],
    ['구조화된 기억과 관계를 저장하고,','Stores structured memories and relationships,','保存结构化记忆与关系，','構造化した記憶と関係を保存し、','Guarda memorias y relaciones estructuradas,','Lưu ký ức và quan hệ có cấu trúc,','บันทึกความทรงจำและความสัมพันธ์แบบมีโครงสร้าง'],
    ['전달받은 키워드만 임베딩합니다.','and embeds only supplied keywords.','仅嵌入收到的关键词。','受け取ったキーワードだけを埋め込みます。','y vectoriza solo las palabras clave recibidas.','và chỉ nhúng các từ khóa được gửi tới.','และฝังเฉพาะคีย์เวิร์ดที่ได้รับ'],
    ['다른 에이전트도 같은 기억을 찾고,','Other agents find the same memory,','其他智能体也能找到同一份记忆，','別のエージェントも同じ記憶を見つけ、','Otros agentes encuentran la misma memoria,','Tác nhân khác cũng tìm thấy cùng ký ức,','เอเจนต์อื่นก็พบความทรงจำเดียวกัน'],
    ['필요한 맥락을 구성해 답합니다.','build the needed context, and respond.','构建所需上下文并回答。','必要な文脈を組み立てて回答します。','construyen el contexto necesario y responden.','tạo ngữ cảnh cần thiết và trả lời.','สร้างบริบทที่จำเป็นแล้วตอบกลับ'],
    ['저장, 파일 등록, 검색까지.','From saving and file registration to search.','从保存、文件登记到搜索。','保存・ファイル登録・検索まで。','Desde guardar y registrar archivos hasta buscar.','Từ lưu, đăng ký tệp đến tìm kiếm.','ตั้งแต่บันทึก ลงทะเบียนไฟล์ ไปจนถึงค้นหา'],
    ['미리 구성한 요청 예시로 흐름을 확인하세요.','Follow the flow with prepared request examples.','通过预设请求示例了解流程。','用意されたリクエスト例で流れを確認できます。','Sigue el flujo con ejemplos de solicitud preparados.','Theo dõi quy trình bằng các yêu cầu mẫu.','ดูขั้นตอนผ่านตัวอย่างคำขอที่เตรียมไว้'],
    ['사람, 프로젝트, 취향을 관계로 묶으세요.','Connect people, projects, and preferences as relationships.','用关系连接人物、项目与偏好。','人・プロジェクト・好みを関係で結びます。','Conecta personas, proyectos y preferencias mediante relaciones.','Kết nối con người, dự án và sở thích bằng quan hệ.','เชื่อมคน โปรเจกต์ และความชอบด้วยความสัมพันธ์'],
    ['에이전트가 정의한 관계와 근거를 보관하고,','Keep agent-defined relationships and their evidence,','保存智能体定义的关系及其依据，','エージェントが定義した関係と根拠を保存し、','Conserva las relaciones definidas por agentes y sus pruebas,','Lưu quan hệ do tác nhân xác định cùng bằng chứng,','เก็บความสัมพันธ์ที่เอเจนต์กำหนดพร้อมหลักฐาน'],
    ['변경 이력까지 함께 관리합니다.','including their change history.','并管理变更历史。','変更履歴も一緒に管理します。','incluido su historial de cambios.','bao gồm cả lịch sử thay đổi.','รวมถึงประวัติการเปลี่ยนแปลง'],
    ['어디까지 자동으로','Exactly how far','自动化能延续到何处，','どこまで自動で','Hasta dónde llega','Tự động hóa đến đâu,','ทำงานอัตโนมัติได้แค่ไหน'],
    ['이어지는지, 정확하게.','continuity is automated.','一目了然。','つながるか、正確に。','la continuidad automática.','một cách chính xác.','อย่างชัดเจน'],
    ['공식 생명주기 확장점과 배포 어댑터를 기준으로 표시합니다.','Status is based on official lifecycle extension points and shipped adapters.','状态依据官方生命周期扩展点和已发布适配器。','公式ライフサイクル拡張点と配布アダプターに基づく表示です。','El estado se basa en extensiones oficiales del ciclo de vida y adaptadores publicados.','Trạng thái dựa trên điểm mở rộng vòng đời chính thức và adapter đã phát hành.','สถานะอ้างอิงจุดขยายวงจรชีวิตอย่างเป็นทางการและอะแดปเตอร์ที่เผยแพร่'],
    ['이 연동에 SSE 연결은 필요하지 않습니다.','These integrations do not require SSE.','这些集成不需要 SSE。','これらの連携にSSEは不要です。','Estas integraciones no requieren SSE.','Các tích hợp này không cần SSE.','การเชื่อมต่อเหล่านี้ไม่ต้องใช้ SSE'],
    ['자동 불러오기','Automatic recall','自动读取','自動呼び出し','Recuperación automática','Tự động gọi lại','เรียกคืนอัตโนมัติ'],
    ['체크포인트','Checkpoint','检查点','チェックポイント','Punto de control','Điểm kiểm tra','เช็กพอยต์'],
    ['지원됨','Supported','支持','対応','Compatible','Được hỗ trợ','รองรับ'],
    ['개발 중','In progress','开发中','開発中','En desarrollo','Đang phát triển','กำลังพัฒนา'],
    ['예정','Planned','计划中','予定','Planificado','Đã lên kế hoạch','วางแผนแล้ว'],
    ['미지원','Unsupported','不支持','未対応','No compatible','Không hỗ trợ','ไม่รองรับ'],
    ['미검증','Unverified','未验证','未検証','Sin verificar','Chưa xác minh','ยังไม่ตรวจสอบ'],
    ['설치·제한사항 보기','View setup and limitations','查看安装与限制','設定と制限を見る','Ver instalación y limitaciones','Xem cài đặt và giới hạn','ดูการติดตั้งและข้อจำกัด'],
    ['나의 워크스페이스','My workspace','我的工作区','自分のワークスペース','Mi espacio de trabajo','Không gian làm việc của tôi','พื้นที่ทำงานของฉัน'],
    ['워크스페이스 메뉴','Workspace menu','工作区菜单','ワークスペースメニュー','Menú del espacio de trabajo','Menu không gian làm việc','เมนูพื้นที่ทำงาน'],
    ['콘솔 메뉴','Console menu','控制台菜单','コンソールメニュー','Menú de consola','Menu bảng điều khiển','เมนูคอนโซล'],
    ['메뉴 열기','Open menu','打开菜单','メニューを開く','Abrir menú','Mở menu','เปิดเมนู'],
    ['메뉴 닫기','Close menu','关闭菜单','メニューを閉じる','Cerrar menú','Đóng menu','ปิดเมนู'],
    ['에이전트 연결','Agent connections','智能体连接','エージェント接続','Conexiones de agentes','Kết nối tác nhân','การเชื่อมต่อเอเจนต์'],
    ['계정 보안','Account security','账户安全','アカウントセキュリティ','Seguridad de la cuenta','Bảo mật tài khoản','ความปลอดภัยบัญชี'],
    ['관리자 페이지','Admin console','管理控制台','管理コンソール','Consola de administración','Bảng quản trị','คอนโซลผู้ดูแล'],
    ['Skill 다운로드','Download Skill','下载 Skill','Skillをダウンロード','Descargar Skill','Tải Skill','ดาวน์โหลด Skill'],
    ['워크스페이스 데이터 · 연결 상태 · 최근 활동','Workspace data · connections · recent activity','工作区数据 · 连接状态 · 最近活动','ワークスペースデータ · 接続状態 · 最近のアクティビティ','Datos · conexiones · actividad reciente','Dữ liệu · kết nối · hoạt động gần đây','ข้อมูล · การเชื่อมต่อ · กิจกรรมล่าสุด'],
    ['내가 남긴 사실과 취향, 에이전트가 구성한 엔티티를 확인하세요.','Review your facts, preferences, and agent-created entities.','查看你的事实、偏好以及智能体创建的实体。','自分の事実・好み・エージェントが構成したエンティティを確認します。','Revisa tus datos, preferencias y entidades creadas por agentes.','Xem sự kiện, sở thích và thực thể do tác nhân tạo.','ดูข้อเท็จจริง ความชอบ และเอนทิตีที่เอเจนต์สร้าง'],
    ['원본과 에이전트가 분석한 문서 메타정보를 관리하세요.','Manage originals and agent-prepared document metadata.','管理原文件和智能体分析的文档元数据。','原本とエージェントが分析した文書メタデータを管理します。','Gestiona originales y metadatos preparados por agentes.','Quản lý tệp gốc và metadata tài liệu do tác nhân chuẩn bị.','จัดการไฟล์ต้นฉบับและเมทาดาทาเอกสารที่เอเจนต์เตรียม'],
    ['에이전트가 구성한 기억의 연결과 근거를 살펴보세요.','Explore agent-created memory connections and evidence.','查看智能体创建的记忆连接及依据。','エージェントが構成した記憶のつながりと根拠を確認します。','Explora conexiones de memoria y pruebas creadas por agentes.','Khám phá kết nối ký ức và bằng chứng do tác nhân tạo.','สำรวจการเชื่อมโยงความทรงจำและหลักฐานที่เอเจนต์สร้าง'],
    ['연결된 에이전트를 확인하고 접근 권한을 관리하세요.','Review connected agents and manage access.','查看已连接的智能体并管理访问权限。','接続済みエージェントとアクセス権を管理します。','Revisa agentes conectados y gestiona el acceso.','Xem tác nhân đã kết nối và quản lý quyền truy cập.','ดูเอเจนต์ที่เชื่อมต่อและจัดการสิทธิ์'],
    ['에이전트가 로컬 설정 파일 없이 사용할 비밀값을 암호화해 관리하세요.','Encrypt and manage secrets agents can use without local config files.','加密管理智能体无需本地配置文件即可使用的秘密。','ローカル設定ファイルなしで使う秘密を暗号化して管理します。','Cifra y gestiona secretos sin archivos de configuración locales.','Mã hóa và quản lý bí mật mà tác nhân dùng không cần tệp cấu hình cục bộ.','เข้ารหัสและจัดการความลับที่เอเจนต์ใช้ได้โดยไม่ต้องมีไฟล์ตั้งค่าในเครื่อง'],
    ['필요한 기능과 실제 사용 사례를 남겨주세요.','Share needed features and real use cases.','提交所需功能和真实使用场景。','必要な機能と実際のユースケースを共有してください。','Comparte funciones necesarias y casos de uso reales.','Chia sẻ tính năng cần thiết và trường hợp sử dụng thực tế.','ส่งฟีเจอร์ที่ต้องการและกรณีใช้งานจริง'],
    ['로그인 보호와 복구 수단을 관리하세요.','Manage login protection and recovery methods.','管理登录保护与恢复方式。','ログイン保護と復旧手段を管理します。','Gestiona la protección de acceso y recuperación.','Quản lý bảo vệ đăng nhập và phương thức khôi phục.','จัดการการป้องกันการเข้าสู่ระบบและวิธีกู้คืน'],
    ['원본 업로드','Upload original','上传原文件','原本をアップロード','Subir original','Tải tệp gốc lên','อัปโหลดต้นฉบับ'],
    ['최근 기록','Recent records','最近记录','最近の記録','Registros recientes','Bản ghi gần đây','รายการล่าสุด'],
    ['최근 저장된 워크스페이스 데이터','Recently saved workspace data','最近保存的工作区数据','最近保存されたワークスペースデータ','Datos guardados recientemente','Dữ liệu không gian làm việc vừa lưu','ข้อมูลพื้นที่ทำงานที่บันทึกล่าสุด'],
    ['전체 보기','View all','查看全部','すべて見る','Ver todo','Xem tất cả','ดูทั้งหมด'],
    ['연결 상태','Connection status','连接状态','接続状態','Estado de conexión','Trạng thái kết nối','สถานะการเชื่อมต่อ'],
    ['내 기억 용량','My memory usage','我的记忆用量','記憶の使用量','Uso de memoria','Dung lượng ký ức','การใช้พื้นที่ความทรงจำ'],
    ['현재 논리 사용량 · 휴지통 포함','Current logical usage · includes trash','当前逻辑用量 · 包含回收站','現在の論理使用量 · ゴミ箱を含む','Uso lógico actual · incluye papelera','Mức dùng logic hiện tại · gồm thùng rác','การใช้งานเชิงตรรกะปัจจุบัน · รวมถังขยะ'],
    ['기억 데이터','Memory data','记忆数据','記憶データ','Datos de memoria','Dữ liệu ký ức','ข้อมูลความทรงจำ'],
    ['원본 파일','Original files','原文件','原本ファイル','Archivos originales','Tệp gốc','ไฟล์ต้นฉบับ'],
    ['앱 저장 한도 미설정','No app storage limit set','未设置应用存储上限','アプリの保存上限未設定','Sin límite de almacenamiento configurado','Chưa đặt giới hạn lưu trữ','ยังไม่ได้กำหนดขีดจำกัดพื้นที่'],
    ['빠른 시작','Quick start','快速开始','クイックスタート','Inicio rápido','Bắt đầu nhanh','เริ่มต้นด่วน'],
    ['워크스페이스 빠른 작업','Workspace quick actions','工作区快捷操作','ワークスペースのクイック操作','Acciones rápidas','Thao tác nhanh','การทำงานด่วน'],
    ['다시 보지 않기','Do not show again','不再显示','今後表示しない','No volver a mostrar','Không hiển thị lại','ไม่ต้องแสดงอีก'],
    ['기록 없음','No records','暂无记录','記録なし','Sin registros','Không có bản ghi','ไม่มีรายการ'],
    ['저장된 워크스페이스 데이터가 없습니다.','No workspace data has been saved.','尚未保存工作区数据。','保存済みワークスペースデータはありません。','No hay datos guardados.','Chưa có dữ liệu nào được lưu.','ยังไม่มีข้อมูลที่บันทึก'],
    ['검색 결과가 없어요.','No search results.','没有搜索结果。','検索結果がありません。','No hay resultados.','Không có kết quả tìm kiếm.','ไม่พบผลการค้นหา'],
    ['다른 키워드로 검색해보세요.','Try different keywords.','请尝试其他关键词。','別のキーワードをお試しください。','Prueba otras palabras clave.','Hãy thử từ khóa khác.','ลองใช้คีย์เวิร์ดอื่น'],
    ['기록 상세','Record details','记录详情','記録の詳細','Detalles del registro','Chi tiết bản ghi','รายละเอียดรายการ'],
    ['이름 없는 기록','Untitled record','无标题记录','無題の記録','Registro sin título','Bản ghi không tên','รายการไม่มีชื่อ'],
    ['그래프 엔진 파일을 불러오지 못했습니다. 페이지를 새로고침해주세요.','Could not load the graph engine. Refresh the page.','无法加载图谱引擎，请刷新页面。','グラフエンジンを読み込めません。ページを再読み込みしてください。','No se pudo cargar el motor del grafo. Actualiza la página.','Không thể tải bộ máy đồ thị. Hãy tải lại trang.','โหลดเอนจินกราฟไม่ได้ โปรดรีเฟรชหน้า'],
    ['노드나 관계를 선택하면 상세 정보를 확인할 수 있습니다.','Select a node or relationship to view details.','选择节点或关系即可查看详情。','ノードまたは関係を選ぶと詳細を確認できます。','Selecciona un nodo o relación para ver detalles.','Chọn nút hoặc quan hệ để xem chi tiết.','เลือกโหนดหรือความสัมพันธ์เพื่อดูรายละเอียด'],
    ['관계 근거','Relationship evidence','关系依据','関係の根拠','Prueba de la relación','Bằng chứng quan hệ','หลักฐานความสัมพันธ์'],
    ['에이전트가 등록한 근거','Evidence submitted by the agent','智能体提交的依据','エージェントが登録した根拠','Prueba enviada por el agente','Bằng chứng do tác nhân gửi','หลักฐานที่เอเจนต์ส่ง'],
    ['연결된 기억','Connected memories','关联记忆','つながった記憶','Memorias conectadas','Ký ức được kết nối','ความทรงจำที่เชื่อมโยง'],
    ['한 번 연결하고, 다음 대화부터 이어가세요.','Connect once and continue in every new conversation.','连接一次，让后续对话延续上下文。','一度接続して、次の会話から続けましょう。','Conecta una vez y continúa en cada conversación.','Kết nối một lần và tiếp tục trong mọi cuộc trò chuyện mới.','เชื่อมต่อครั้งเดียว แล้วต่อเนื่องในทุกบทสนทนาใหม่'],
    ['자동 복사가 차단됐습니다. 아래 내용을 선택해 복사하세요.','Automatic copy was blocked. Select and copy the text below.','自动复制被阻止，请选择并复制下方内容。','自動コピーがブロックされました。下の内容を選択してコピーしてください。','La copia automática fue bloqueada. Copia el texto siguiente.','Sao chép tự động bị chặn. Hãy chọn và sao chép nội dung bên dưới.','การคัดลอกอัตโนมัติถูกบล็อก โปรดเลือกและคัดลอกข้อความด้านล่าง'],
    ['다시 만나 반가워요.','Welcome back.','欢迎回来。','おかえりなさい。','Te damos la bienvenida.','Chào mừng bạn quay lại.','ยินดีต้อนรับกลับมา'],
    ['이메일은 로그인 식별자로 사용됩니다. 비밀번호는 10자 이상으로 설정해주세요.','Email is used to sign in. Use a password of at least 10 characters.','邮箱用于登录，请设置至少 10 个字符的密码。','メールはログインIDとして使います。パスワードは10文字以上にしてください。','El correo se usa para iniciar sesión. Usa al menos 10 caracteres.','Email được dùng để đăng nhập. Mật khẩu phải có ít nhất 10 ký tự.','ใช้อีเมลเพื่อเข้าสู่ระบบ และตั้งรหัสผ่านอย่างน้อย 10 ตัวอักษร'],
    ['한 단계만 더 확인할게요.','One more verification step.','还需完成一步验证。','あと一段階確認します。','Queda un paso de verificación.','Còn một bước xác minh.','เหลือการยืนยันอีกหนึ่งขั้นตอน'],
    ['인증 앱의 6자리 코드 또는 복구 코드를 입력하세요.','Enter the six-digit authenticator or recovery code.','请输入身份验证器的六位代码或恢复代码。','認証アプリの6桁コードまたは復旧コードを入力してください。','Introduce el código de seis dígitos o uno de recuperación.','Nhập mã xác thực sáu chữ số hoặc mã khôi phục.','กรอกรหัสหกหลักจากแอปยืนยันตัวตนหรือรหัสกู้คืน'],
    ['인증 코드는 한 번만 사용할 수 있으며 5분 후 로그인이 만료됩니다.','The code can be used once and this sign-in expires in five minutes.','验证码仅可使用一次，本次登录将在五分钟后过期。','コードは一度だけ使用でき、ログインは5分で期限切れになります。','El código se usa una vez y el acceso caduca en cinco minutos.','Mã chỉ dùng một lần và đăng nhập hết hạn sau năm phút.','รหัสใช้ได้ครั้งเดียวและการเข้าสู่ระบบจะหมดอายุในห้านาที'],
    ['인증하고 로그인','Verify and log in','验证并登录','認証してログイン','Verificar e iniciar sesión','Xác minh và đăng nhập','ยืนยันและเข้าสู่ระบบ'],
    ['비밀번호 표시','Show password','显示密码','パスワードを表示','Mostrar contraseña','Hiện mật khẩu','แสดงรหัสผ่าน'],
    ['비밀번호 숨기기','Hide password','隐藏密码','パスワードを隠す','Ocultar contraseña','Ẩn mật khẩu','ซ่อนรหัสผ่าน'],
    ['민감한 권한','Sensitive permission','敏感权限','機密権限','Permiso sensible','Quyền nhạy cảm','สิทธิ์ที่ละเอียดอ่อน'],
    ['Vault 사용 권한 승인','Approve Vault access','批准 Vault 访问','Vaultアクセスを承認','Aprobar acceso a Vault','Phê duyệt quyền truy cập Vault','อนุมัติการเข้าถึง Vault'],
    ['저장된 비밀값을 실행할 프로세스에 전달할 수 있습니다. 요청한 에이전트를 신뢰할 때만 허용하세요.','This can pass saved secrets to a process. Allow it only for a trusted agent.','这可将已保存的秘密传给进程，仅对可信智能体授权。','保存済みの秘密をプロセスに渡せます。信頼できるエージェントだけに許可してください。','Puede pasar secretos guardados a un proceso. Permítelo solo a un agente de confianza.','Quyền này có thể chuyển bí mật đã lưu cho tiến trình. Chỉ cho phép tác nhân đáng tin cậy.','สิทธิ์นี้ส่งความลับที่บันทึกไว้ให้โปรเซสได้ อนุญาตเฉพาะเอเจนต์ที่เชื่อถือ'],
    ['비밀값을 안전하게 저장하세요.','Save your secret securely.','安全保存秘密。','秘密を安全に保存します。','Guarda tu secreto de forma segura.','Lưu bí mật an toàn.','บันทึกความลับอย่างปลอดภัย'],
    ['일회용 요청을 확인하고 있습니다…','Checking the one-time request…','正在检查一次性请求…','一回限りのリクエストを確認中…','Comprobando la solicitud de un solo uso…','Đang kiểm tra yêu cầu dùng một lần…','กำลังตรวจสอบคำขอแบบใช้ครั้งเดียว…'],
    ['입력값은 암호화되어 Vault에 직접 저장되며 에이전트·채팅·응답에는 표시되지 않습니다.','The value is encrypted directly into Vault and is never shown to the agent, chat, or response.','输入值会加密后直接存入 Vault，不会显示给智能体、聊天或响应。','入力値は暗号化してVaultへ直接保存され、エージェント・チャット・応答には表示されません。','El valor se cifra directamente en Vault y no se muestra al agente, chat ni respuesta.','Giá trị được mã hóa trực tiếp vào Vault và không hiển thị cho tác nhân, chat hay phản hồi.','ค่าจะถูกเข้ารหัสลง Vault โดยตรงและไม่แสดงแก่เอเจนต์ แชต หรือคำตอบ'],
    ['요청한 에이전트','Requesting agent','请求方智能体','リクエスト元エージェント','Agente solicitante','Tác nhân yêu cầu','เอเจนต์ที่ร้องขอ'],
    ['저장 위치','Save location','保存位置','保存先','Ubicación','Vị trí lưu','ตำแหน่งบันทึก'],
    ['만료 시각','Expires at','过期时间','有効期限','Caduca','Hết hạn lúc','หมดอายุเวลา'],
    ['API 키 또는 토큰을 붙여넣으세요','Paste an API key or token','粘贴 API 密钥或令牌','APIキーまたはトークンを貼り付け','Pega una clave API o token','Dán khóa API hoặc token','วาง API key หรือโทเค็น'],
    ['Vault에 안전하게 저장','Save securely to Vault','安全存入 Vault','Vaultへ安全に保存','Guardar en Vault','Lưu an toàn vào Vault','บันทึกอย่างปลอดภัยใน Vault'],
    ['저장했습니다.','Saved.','已保存。','保存しました。','Guardado.','Đã lưu.','บันทึกแล้ว'],
    ['전체 상태','All statuses','全部状态','すべての状態','Todos los estados','Mọi trạng thái','ทุกสถานะ'],
    ['검토 중','Reviewing','审核中','レビュー中','En revisión','Đang xem xét','กำลังตรวจสอบ'],
    ['계획됨','Planned','已计划','計画済み','Planificada','Đã lên kế hoạch','วางแผนแล้ว'],
    ['처리 중','In progress','处理中','処理中','En curso','Đang xử lý','กำลังดำเนินการ'],
    ['완료','Completed','已完成','完了','Completada','Hoàn tất','เสร็จสิ้น'],
    ['보류','Deferred','暂缓','保留','Aplazada','Tạm hoãn','พักไว้'],
    ['높음','High','高','高','Alta','Cao','สูง'],
    ['보통','Medium','中','中','Media','Trung bình','ปานกลาง'],
    ['낮음','Low','低','低','Baja','Thấp','ต่ำ'],
    ['기능 요청 관리','Feature request management','功能请求管理','機能リクエスト管理','Gestión de solicitudes','Quản lý yêu cầu tính năng','จัดการคำขอฟีเจอร์'],
    ['모든 워크스페이스의 요청을 검토하고 처리 결과를 공개합니다.','Review requests from every workspace and publish outcomes.','审核所有工作区的请求并发布处理结果。','すべてのワークスペースのリクエストを確認し、結果を公開します。','Revisa solicitudes de todos los espacios y publica resultados.','Xem yêu cầu từ mọi không gian và công bố kết quả.','ตรวจสอบคำขอจากทุกพื้นที่และเผยแพร่ผลลัพธ์'],
    ['기능 요청 현황','Feature request overview','功能请求概览','機能リクエスト概要','Resumen de solicitudes','Tổng quan yêu cầu tính năng','ภาพรวมคำขอฟีเจอร์'],
    ['처리 큐','Processing queue','处理队列','処理キュー','Cola de procesamiento','Hàng đợi xử lý','คิวดำเนินการ'],
    ['사용자','User','用户','ユーザー','Usuario','Người dùng','ผู้ใช้'],
    ['요청자','Requester','请求者','リクエスト元','Solicitante','Người yêu cầu','ผู้ร้องขอ'],
    ['우선순위','Priority','优先级','優先度','Prioridad','Ưu tiên','ลำดับความสำคัญ'],
    ['처리 결과','Outcome','处理结果','処理結果','Resultado','Kết quả','ผลลัพธ์'],
    ['최종 갱신','Last updated','最后更新','最終更新','Última actualización','Cập nhật lần cuối','อัปเดตล่าสุด'],
    ['사용자 목록','User list','用户列表','ユーザー一覧','Lista de usuarios','Danh sách người dùng','รายชื่อผู้ใช้'],
    ['운영 에이전트','Operator agents','运营智能体','運用エージェント','Agentes operadores','Tác nhân vận hành','เอเจนต์ปฏิบัติการ'],
    ['새로고침','Refresh','刷新','再読み込み','Actualizar','Làm mới','รีเฟรช'],
    ['내 콘솔','My console','我的控制台','自分のコンソール','Mi consola','Bảng điều khiển của tôi','คอนโซลของฉัน'],
    ['요청 편집 및 처리','Edit and resolve request','编辑并处理请求','リクエストの編集と処理','Editar y resolver solicitud','Chỉnh sửa và xử lý yêu cầu','แก้ไขและดำเนินการคำขอ'],
    ['요청 변경사항 저장','Save request changes','保存请求更改','変更を保存','Guardar cambios','Lưu thay đổi','บันทึกการเปลี่ยนแปลง'],
    ['권한 확인 중…','Checking permissions…','正在检查权限…','権限を確認中…','Comprobando permisos…','Đang kiểm tra quyền…','กำลังตรวจสอบสิทธิ์…'],
    ['Claude Code가 나의 개발 언어 선호를 참고하는 예시입니다.','Claude Code uses my programming-language preference in this example.','此示例中 Claude Code 会参考我的编程语言偏好。','Claude Codeが開発言語の好みを参照する例です。','Claude Code usa mi preferencia de lenguaje en este ejemplo.','Ví dụ Claude Code dùng sở thích ngôn ngữ lập trình của tôi.','ตัวอย่าง Claude Code ใช้ความชอบด้านภาษาเขียนโปรแกรมของฉัน'],
    ['Codex가 이전 작업의 맥락을 이어받는 예시입니다.','Codex continues context from earlier work in this example.','此示例中 Codex 会延续之前工作的上下文。','Codexが以前の作業文脈を引き継ぐ例です。','Codex continúa el contexto del trabajo anterior.','Ví dụ Codex tiếp tục ngữ cảnh từ công việc trước.','ตัวอย่าง Codex สานต่อบริบทจากงานก่อนหน้า'],
    ['OpenClaw가 프로젝트와 연결된 기억을 찾는 예시입니다.','OpenClaw finds project-related memories in this example.','此示例中 OpenClaw 会查找与项目相关的记忆。','OpenClawがプロジェクト関連の記憶を探す例です。','OpenClaw encuentra memorias relacionadas con el proyecto.','Ví dụ OpenClaw tìm ký ức liên quan đến dự án.','ตัวอย่าง OpenClaw ค้นหาความทรงจำที่เกี่ยวกับโปรเจกต์'],
    ['Hermes가 다른 에이전트에 남긴 취향을 참고하는 예시입니다.','Hermes uses a preference saved by another agent in this example.','此示例中 Hermes 会参考其他智能体保存的偏好。','Hermesが別エージェントの保存した好みを参照する例です。','Hermes usa una preferencia guardada por otro agente.','Ví dụ Hermes dùng sở thích do tác nhân khác lưu.','ตัวอย่าง Hermes ใช้ความชอบที่เอเจนต์อื่นบันทึกไว้'],
    ['에이전트가 추출한 기억','Memory extracted by the agent','智能体提取的记忆','エージェントが抽出した記憶','Memoria extraída por el agente','Ký ức do tác nhân trích xuất','ความทรงจำที่เอเจนต์สกัด'],
    ['에이전트가 선호를 이해하고, 저장할 키워드를 구성합니다.','The agent understands the preference and prepares keywords to save.','智能体理解偏好并准备要保存的关键词。','エージェントが好みを理解し、保存するキーワードを構成します。','El agente entiende la preferencia y prepara las palabras clave.','Tác nhân hiểu sở thích và chuẩn bị từ khóa để lưu.','เอเจนต์เข้าใจความชอบและเตรียมคีย์เวิร์ดที่จะบันทึก'],
    ['앱은 keywords만 로컬에서 임베딩합니다.','The app embeds only keywords locally.','应用仅在本地嵌入关键词。','アプリはキーワードだけをローカルで埋め込みます。','La app solo vectoriza las palabras clave localmente.','Ứng dụng chỉ nhúng từ khóa cục bộ.','แอปฝังเฉพาะคีย์เวิร์ดในเครื่อง'],
    ['에이전트가 분석한 파일','File analyzed by the agent','智能体分析的文件','エージェントが分析したファイル','Archivo analizado por el agente','Tệp do tác nhân phân tích','ไฟล์ที่เอเจนต์วิเคราะห์'],
    ['에이전트가 추출한 검색 키워드','Search keywords extracted by the agent','智能体提取的搜索关键词','エージェントが抽出した検索キーワード','Palabras de búsqueda extraídas por el agente','Từ khóa tìm kiếm do tác nhân trích xuất','คีย์เวิร์ดค้นหาที่เอเจนต์สกัด'],
    ['자동 복사가 차단됐습니다. 콘솔에서 프롬프트를 복사해주세요.','Automatic copy was blocked. Copy the prompt from the console.','自动复制被阻止，请从控制台复制提示词。','自動コピーがブロックされました。コンソールからコピーしてください。','La copia automática fue bloqueada. Copia el prompt desde la consola.','Sao chép tự động bị chặn. Hãy sao chép lời nhắc từ bảng điều khiển.','การคัดลอกอัตโนมัติถูกบล็อก โปรดคัดลอกพรอมต์จากคอนโซล'],
    ['요청 JSON을 복사했습니다.','Request JSON copied.','已复制请求 JSON。','リクエストJSONをコピーしました。','JSON de solicitud copiado.','Đã sao chép JSON yêu cầu.','คัดลอก JSON คำขอแล้ว'],
    ['코드를 선택했습니다. 복사 단축키를 사용하세요.','Code selected. Use the copy shortcut.','已选择代码，请使用复制快捷键。','コードを選択しました。コピーのショートカットを使ってください。','Código seleccionado. Usa el atajo de copiar.','Đã chọn mã. Hãy dùng phím tắt sao chép.','เลือกโค้ดแล้ว โปรดใช้ปุ่มลัดคัดลอก'],
    ['올바른 연결 링크로 다시 시작해주세요.','Restart with a valid connection link.','请使用有效连接链接重新开始。','正しい接続リンクからやり直してください。','Vuelve a empezar con un enlace válido.','Hãy bắt đầu lại bằng liên kết kết nối hợp lệ.','โปรดเริ่มใหม่ด้วยลิงก์เชื่อมต่อที่ถูกต้อง'],
    ['계정을 확인할 수 없습니다.','Could not verify the account.','无法验证账户。','アカウントを確認できません。','No se pudo verificar la cuenta.','Không thể xác minh tài khoản.','ตรวจสอบบัญชีไม่ได้'],
    ['연결 요청을 확인할 수 없습니다.','Could not verify the connection request.','无法验证连接请求。','接続リクエストを確認できません。','No se pudo verificar la solicitud de conexión.','Không thể xác minh yêu cầu kết nối.','ตรวจสอบคำขอเชื่อมต่อไม่ได้'],
    ['이미 처리된 연결 요청입니다. 에이전트에서 연결 결과를 확인하세요.','This request was already handled. Check the result in your agent.','该连接请求已处理，请在智能体中查看结果。','処理済みの接続リクエストです。エージェントで結果を確認してください。','Esta solicitud ya fue procesada. Comprueba el resultado en el agente.','Yêu cầu đã được xử lý. Hãy kiểm tra kết quả trong tác nhân.','คำขอนี้ดำเนินการแล้ว โปรดตรวจผลในเอเจนต์'],
    ['기존 에이전트의 Vault 권한 변경을 승인할까요?','Approve this Vault permission change for the existing agent?','批准现有智能体的 Vault 权限变更吗？','既存エージェントのVault権限変更を承認しますか？','¿Aprobar el cambio de acceso a Vault para el agente?','Phê duyệt thay đổi quyền Vault cho tác nhân hiện có?','อนุมัติการเปลี่ยนสิทธิ์ Vault ของเอเจนต์เดิมหรือไม่'],
    ['이 에이전트의 연결을 승인할까요?','Approve this agent connection?','批准此智能体连接吗？','このエージェントの接続を承認しますか？','¿Aprobar la conexión de este agente?','Phê duyệt kết nối tác nhân này?','อนุมัติการเชื่อมต่อเอเจนต์นี้หรือไม่'],
    ['연결을 처리할 수 없습니다.','Could not process the connection.','无法处理连接。','接続を処理できません。','No se pudo procesar la conexión.','Không thể xử lý kết nối.','ดำเนินการเชื่อมต่อไม่ได้'],
    ['연결 요청을 거절했습니다.','Connection request denied.','已拒绝连接请求。','接続リクエストを拒否しました。','Solicitud de conexión rechazada.','Đã từ chối yêu cầu kết nối.','ปฏิเสธคำขอเชื่อมต่อแล้ว'],
    ['올바르지 않은 Vault 입력 링크입니다.','This Vault input link is invalid.','Vault 输入链接无效。','Vault入力リンクが無効です。','El enlace de entrada de Vault no es válido.','Liên kết nhập Vault không hợp lệ.','ลิงก์ป้อนข้อมูล Vault ไม่ถูกต้อง'],
    ['요청 내용과 저장 위치를 확인한 뒤 값을 입력하세요.','Review the request and save location, then enter the value.','确认请求内容和保存位置后输入值。','リクエスト内容と保存先を確認して値を入力してください。','Revisa la solicitud y la ubicación antes de introducir el valor.','Kiểm tra yêu cầu và vị trí lưu rồi nhập giá trị.','ตรวจสอบคำขอและตำแหน่งบันทึกก่อนกรอกค่า'],
    ['암호화하여 저장 중…','Encrypting and saving…','正在加密并保存…','暗号化して保存中…','Cifrando y guardando…','Đang mã hóa và lưu…','กำลังเข้ารหัสและบันทึก…'],
    ['서버에 연결할 수 없습니다.','Cannot reach the server.','无法连接服务器。','サーバーに接続できません。','No se puede conectar con el servidor.','Không thể kết nối máy chủ.','เชื่อมต่อเซิร์ฟเวอร์ไม่ได้'],
    ['요청을 처리할 수 없습니다.','Could not process the request.','无法处理请求。','リクエストを処理できません。','No se pudo procesar la solicitud.','Không thể xử lý yêu cầu.','ดำเนินการคำขอไม่ได้'],
    ['입력한 내용을 다시 확인해주세요.','Check the information you entered.','请重新检查输入内容。','入力内容をもう一度確認してください。','Revisa la información introducida.','Hãy kiểm tra lại thông tin đã nhập.','โปรดตรวจสอบข้อมูลที่กรอกอีกครั้ง'],
    ['조회 성공','Read succeeded','读取成功','取得成功','Consulta correcta','Truy xuất thành công','เรียกดูสำเร็จ'],
    ['목록 조회','List read','读取列表','一覧取得','Consulta de lista','Truy xuất danh sách','เรียกดูรายการ'],
    ['Vault 권한 없음','No Vault permission','无 Vault 权限','Vault権限なし','Sin permiso de Vault','Không có quyền Vault','ไม่มีสิทธิ์ Vault'],
    ['항목 미승인','Entry not approved','条目未批准','項目未承認','Entrada no aprobada','Mục chưa được phê duyệt','รายการยังไม่อนุมัติ'],
    ['항목 없음','Entry not found','未找到条目','項目なし','Entrada no encontrada','Không tìm thấy mục','ไม่พบรายการ'],
    ['무결성 오류','Integrity error','完整性错误','整合性エラー','Error de integridad','Lỗi toàn vẹn','ข้อผิดพลาดความสมบูรณ์'],
    ['알 수 없음','Unknown','未知','不明','Desconocido','Không rõ','ไม่ทราบ'],
    ['아직 등록된 처리 결과가 없습니다.','No outcome has been posted yet.','尚未发布处理结果。','処理結果はまだ登録されていません。','Aún no hay resultado publicado.','Chưa có kết quả xử lý.','ยังไม่มีผลลัพธ์ที่เผยแพร่'],
    ['관련 결과 보기','View related result','查看相关结果','関連結果を見る','Ver resultado relacionado','Xem kết quả liên quan','ดูผลลัพธ์ที่เกี่ยวข้อง'],
    ['요청 내용','Request details','请求内容','リクエスト内容','Detalles de la solicitud','Nội dung yêu cầu','รายละเอียดคำขอ'],
    ['사용 사례','Use case','使用场景','ユースケース','Caso de uso','Trường hợp sử dụng','กรณีใช้งาน'],
    ['요청 에이전트','Requesting agent','请求方智能体','リクエスト元エージェント','Agente solicitante','Tác nhân yêu cầu','เอเจนต์ที่ร้องขอ'],
    ['접수일','Received at','接收时间','受付日','Recibida','Ngày tiếp nhận','วันที่รับ'],
    ['처리일','Resolved at','处理时间','処理日','Resuelta','Ngày xử lý','วันที่ดำเนินการ'],
    ['등록일','Created at','创建时间','登録日','Creada','Ngày tạo','วันที่สร้าง'],
    ['다운로드','Download','下载','ダウンロード','Descargar','Tải xuống','ดาวน์โหลด'],
    ['삭제','Delete','删除','削除','Eliminar','Xóa','ลบ'],
    ['엔티티','Entity','实体','エンティティ','Entidad','Thực thể','เอนทิตี'],
    ['문서 메타정보','Document metadata','文档元数据','文書メタデータ','Metadatos del documento','Metadata tài liệu','เมทาดาทาเอกสาร'],
    ['파일','File','文件','ファイル','Archivo','Tệp','ไฟล์'],
    ['기록','Record','记录','記録','Registro','Bản ghi','รายการ'],
    ['확대','Zoom in','放大','拡大','Acercar','Phóng to','ซูมเข้า'],
    ['축소','Zoom out','缩小','縮小','Alejar','Thu nhỏ','ซูมออก'],
    ['그래프 전체 보기','Fit graph','显示完整图谱','グラフ全体を表示','Ajustar grafo','Vừa toàn bộ đồ thị','พอดีกราฟ'],
    ['그래프 화면 조절','Graph controls','图谱控制','グラフ操作','Controles del grafo','Điều khiển đồ thị','ตัวควบคุมกราฟ'],
    ['기억 관계 그래프. 드래그하여 이동하고 휠로 확대할 수 있습니다.','Memory relationship graph. Drag to pan and use the wheel to zoom.','记忆关系图谱，可拖动平移并用滚轮缩放。','記憶関係グラフ。ドラッグで移動し、ホイールで拡大できます。','Grafo de memoria. Arrastra para mover y usa la rueda para ampliar.','Đồ thị quan hệ ký ức. Kéo để di chuyển và cuộn để thu phóng.','กราฟความสัมพันธ์ความทรงจำ ลากเพื่อเลื่อนและใช้ล้อเพื่อซูม'],
    ['대시보드 안내를 숨겼습니다.','Dashboard guide hidden.','已隐藏仪表板指南。','ダッシュボード案内を非表示にしました。','Guía del panel ocultada.','Đã ẩn hướng dẫn bảng điều khiển.','ซ่อนคำแนะนำแดชบอร์ดแล้ว'],
    ['MCP 서버 주소를 복사했습니다.','MCP server address copied.','已复制 MCP 服务器地址。','MCPサーバーアドレスをコピーしました。','Dirección del servidor MCP copiada.','Đã sao chép địa chỉ máy chủ MCP.','คัดลอกที่อยู่เซิร์ฟเวอร์ MCP แล้ว'],
    ['기억을 저장했습니다.','Memory saved.','记忆已保存。','記憶を保存しました。','Memoria guardada.','Đã lưu ký ức.','บันทึกความทรงจำแล้ว'],
    ['원본 파일을 업로드했습니다.','Original file uploaded.','原文件已上传。','原本ファイルをアップロードしました。','Archivo original subido.','Đã tải tệp gốc lên.','อัปโหลดไฟล์ต้นฉบับแล้ว'],
    ['기능 요청을 접수했습니다.','Feature request received.','功能请求已接收。','機能リクエストを受け付けました。','Solicitud de función recibida.','Đã tiếp nhận yêu cầu tính năng.','รับคำขอฟีเจอร์แล้ว'],
    ['요청 보내기','Send request','发送请求','送信','Enviar solicitud','Gửi yêu cầu','ส่งคำขอ'],
    ['업로드','Upload','上传','アップロード','Subir','Tải lên','อัปโหลด'],
    ['새 기억 남기기','Add a memory','新增记忆','新しい記憶を残す','Añadir memoria','Thêm ký ức','เพิ่มความทรงจำ'],
    ['원본 파일 업로드','Upload original file','上传原文件','原本ファイルをアップロード','Subir archivo original','Tải tệp gốc lên','อัปโหลดไฟล์ต้นฉบับ'],
    ['기능 요청 남기기','Submit feature request','提交功能请求','機能リクエストを送信','Enviar solicitud de función','Gửi yêu cầu tính năng','ส่งคำขอฟีเจอร์'],
    ['확인','Confirm','确认','確認','Confirmar','Xác nhận','ยืนยัน'],
    ['계속할까요?','Continue?','继续吗？','続けますか？','¿Continuar?','Tiếp tục?','ดำเนินการต่อหรือไม่'],
    ['API 요청 예시','API request examples','API 请求示例','APIリクエスト例','Ejemplos de solicitudes API','Ví dụ yêu cầu API','ตัวอย่างคำขอ API'],
    ['요청 예시 복사','Copy request example','复制请求示例','リクエスト例をコピー','Copiar ejemplo','Sao chép ví dụ yêu cầu','คัดลอกตัวอย่างคำขอ'],
    ['원문','Original text','原文','原文','Texto original','Văn bản gốc','ข้อความต้นฉบับ'],
    ['요약','Summary','摘要','要約','Resumen','Tóm tắt','สรุป'],
    ['추출한 키워드','Extracted keywords','提取的关键词','抽出したキーワード','Palabras extraídas','Từ khóa đã trích xuất','คีย์เวิร์ดที่สกัด'],
    ['개발 언어','Programming language','编程语言','開発言語','Lenguaje de programación','Ngôn ngữ lập trình','ภาษาเขียนโปรแกรม'],
    ['코드 예제','Code example','代码示例','コード例','Ejemplo de código','Ví dụ mã','ตัวอย่างโค้ด'],
    ['“앞으로 개발 예제는 Python으로 보여줘.”','“Show future development examples in Python.”','“以后用 Python 展示开发示例。”','「今後の開発例はPythonで見せて。」','«Muestra los próximos ejemplos en Python».','“Từ giờ hãy dùng Python cho ví dụ lập trình.”','“ต่อไปแสดงตัวอย่างการพัฒนาด้วย Python”'],
    ['원문 전체를 임베딩하지 않습니다.','The full source text is not embedded.','不会嵌入完整原文。','原文全体は埋め込みません。','No se vectoriza el texto completo.','Không nhúng toàn bộ văn bản gốc.','ไม่ฝังข้อความต้นฉบับทั้งหมด'],
    ['에이전트가 추출한 키워드로 인덱스를 만들고,','Build an index from agent-extracted keywords,','用智能体提取的关键词建立索引，','エージェントが抽出したキーワードでインデックスを作り、','Crea un índice con palabras extraídas por el agente,','Tạo chỉ mục từ khóa do tác nhân trích xuất,','สร้างดัชนีจากคีย์เวิร์ดที่เอเจนต์สกัด'],
    ['검색 요청의 키워드만 벡터로 비교합니다.','and compare only search keywords as vectors.','并仅对搜索请求中的关键词进行向量比较。','検索リクエストのキーワードだけをベクトル比較します。','y compara como vectores solo las palabras de búsqueda.','và chỉ so sánh vector của từ khóa tìm kiếm.','และเปรียบเทียบเวกเตอร์เฉพาะคีย์เวิร์ดค้นหา'],
    ['에이전트별 키를 같은 사용자에 연결하세요.','Connect each agent key to the same user.','将每个智能体密钥连接到同一用户。','エージェントごとのキーを同じユーザーにつなぎます。','Conecta las claves de agente al mismo usuario.','Kết nối khóa của từng tác nhân với cùng người dùng.','เชื่อมคีย์ของแต่ละเอเจนต์กับผู้ใช้เดียวกัน'],
    ['기억은 공유하고, 다른 사용자의 데이터는','Share memory while keeping other users’ data','共享记忆，同时将其他用户的数据','記憶は共有し、別ユーザーのデータは','Comparte la memoria y mantén los datos de otros usuarios','Chia sẻ ký ức nhưng giữ dữ liệu người dùng khác','แชร์ความทรงจำและแยกข้อมูลผู้ใช้อื่น'],
    ['API 키로 분리합니다.','isolated by API key.','通过 API 密钥隔离。','APIキーで分離します。','aislados mediante claves API.','tách biệt bằng khóa API.','ด้วย API key'],
    ['하나의 사용자, 공유된 기억','One user, shared memory','一个用户，共享记忆','ひとりのユーザー、共有された記憶','Un usuario, memoria compartida','Một người dùng, ký ức dùng chung','ผู้ใช้หนึ่งคน ความทรงจำร่วมกัน'],
    ['Skill을 에이전트에 더하고,','Add the Skill to your agent,','将 Skill 添加到智能体，','エージェントにSkillを追加し、','Añade el Skill a tu agente,','Thêm Skill vào tác nhân,','เพิ่ม Skill ให้เอเจนต์'],
    ['나의 기억 엔드포인트를 연결하세요.','and connect your memory endpoint.','并连接你的记忆端点。','記憶エンドポイントを接続してください。','y conecta tu endpoint de memoria.','và kết nối endpoint ký ức.','และเชื่อมต่อ endpoint ความทรงจำ'],
    ['Linux, macOS 또는 Windows에서 네이티브 Rust CLI를 실행할 수 있는 에이전트에 연결할 수 있습니다. 제공되는 Skill과 CLI가 저장·검색·파일 등록·관계 구성·인증·업데이트를 감싸므로 에이전트가 API 스키마를 컨텍스트에 펼칠 필요가 없습니다.','Connect any agent that can run the native Rust CLI on Linux, macOS, or Windows. The Skill and CLI wrap storage, search, files, relationships, authentication, and updates without expanding the API schema in context.','可连接任何能在 Linux、macOS 或 Windows 运行原生 Rust CLI 的智能体。Skill 与 CLI 封装存储、搜索、文件、关系、认证和更新，无需在上下文中展开 API 架构。','Linux、macOS、WindowsでネイティブRust CLIを実行できるエージェントに接続できます。SkillとCLIが保存・検索・ファイル・関係・認証・更新を包むため、APIスキーマを文脈に展開する必要はありません。','Conecta cualquier agente que ejecute el CLI nativo de Rust en Linux, macOS o Windows. El Skill y el CLI cubren almacenamiento, búsqueda, archivos, relaciones, autenticación y actualizaciones sin expandir el esquema API en el contexto.','Kết nối tác nhân có thể chạy Rust CLI gốc trên Linux, macOS hoặc Windows. Skill và CLI bao bọc lưu trữ, tìm kiếm, tệp, quan hệ, xác thực và cập nhật mà không cần đưa schema API vào ngữ cảnh.','เชื่อมต่อเอเจนต์ที่รัน Rust CLI แบบเนทีฟบน Linux, macOS หรือ Windows ได้ โดย Skill และ CLI ครอบการจัดเก็บ ค้นหา ไฟล์ ความสัมพันธ์ การยืนยัน และอัปเดตโดยไม่ต้องใส่ API schema ในบริบท'],
    ['원본은 application/octet-stream 바이트 스트림으로 업로드합니다. 에이전트가 분석한 키워드와 메타정보는 별도 JSON으로 등록하고 file_id로 연결합니다. 서버는 파일을 분석하거나 청크로 나누지 않습니다.','Upload originals as application/octet-stream bytes. Register agent-prepared keywords and metadata separately as JSON linked by file_id. The server never analyzes or chunks files.','原文件以 application/octet-stream 字节流上传。智能体分析的关键词和元数据作为独立 JSON 注册，并通过 file_id 关联。服务器不会分析或分块文件。','原本はapplication/octet-streamのバイトストリームでアップロードします。エージェントが分析したキーワードとメタデータは別JSONで登録し、file_idで関連付けます。サーバーはファイルを分析・分割しません。','Sube originales como bytes application/octet-stream. Registra aparte las palabras y metadatos preparados por el agente en JSON enlazado por file_id. El servidor no analiza ni fragmenta archivos.','Tải tệp gốc dưới dạng byte application/octet-stream. Đăng ký riêng từ khóa và metadata do tác nhân chuẩn bị trong JSON liên kết bằng file_id. Máy chủ không phân tích hay chia nhỏ tệp.','อัปโหลดไฟล์ต้นฉบับเป็นไบต์ application/octet-stream ลงทะเบียนคีย์เวิร์ดและเมทาดาทาที่เอเจนต์เตรียมเป็น JSON แยกและเชื่อมด้วย file_id เซิร์ฟเวอร์ไม่วิเคราะห์หรือแบ่งไฟล์'],
    ['회원가입 후 콘솔에서 에이전트용 API 키를 발급하면 바로 연결할 수 있습니다. 콘솔에서는 기억, 문서, 관계와 기능 요청을 관리할 수 있습니다. 추론과 파일 분석은 연결된 에이전트가 담당합니다.','After signing up, create an agent API key in the console to connect immediately. The console manages memories, documents, relationships, and feature requests; connected agents handle reasoning and file analysis.','注册后可在控制台创建智能体 API 密钥并立即连接。控制台管理记忆、文档、关系与功能请求；推理和文件分析由已连接的智能体完成。','登録後、コンソールでエージェントAPIキーを発行すればすぐ接続できます。記憶・文書・関係・機能リクエストはコンソールで管理し、推論とファイル分析は接続エージェントが担当します。','Tras registrarte, crea una clave API de agente en la consola. La consola gestiona memorias, documentos, relaciones y solicitudes; los agentes realizan el razonamiento y análisis.','Sau khi đăng ký, tạo khóa API tác nhân trong bảng điều khiển để kết nối. Bảng điều khiển quản lý ký ức, tài liệu, quan hệ và yêu cầu; tác nhân xử lý suy luận và phân tích tệp.','หลังสมัคร ให้สร้าง API key สำหรับเอเจนต์ในคอนโซลเพื่อเชื่อมต่อ คอนโซลจัดการความทรงจำ เอกสาร ความสัมพันธ์ และคำขอ ส่วนเอเจนต์ทำการอนุมานและวิเคราะห์ไฟล์'],
    ['계정','Account','账户','アカウント','Cuenta','Tài khoản','บัญชี'],
    ['인증 코드','Verification code','验证码','認証コード','Código de verificación','Mã xác minh','รหัสยืนยัน'],
    ['6자리 코드 또는 복구 코드','Six-digit or recovery code','六位代码或恢复代码','6桁コードまたは復旧コード','Código de seis dígitos o recuperación','Mã sáu chữ số hoặc mã khôi phục','รหัสหกหลักหรือรหัสกู้คืน'],
    ['에이전트가 안내한 코드와 같은지 확인하세요. 승인하면 이 에이전트가 내 기억을 조회·저장·삭제할 수 있습니다. 직접 시작한 요청만 승인하세요.','Confirm that this matches the code shown by your agent. Approval lets this agent read, save, and delete your memories. Approve only requests you started.','确认此代码与智能体显示的代码一致。批准后该智能体可读取、保存和删除你的记忆。仅批准你主动发起的请求。','エージェントが示したコードと一致するか確認してください。承認すると、このエージェントは記憶の取得・保存・削除ができます。自分で開始したリクエストだけ承認してください。','Confirma que coincide con el código del agente. Al aprobar, podrá leer, guardar y eliminar tus memorias. Aprueba solo solicitudes iniciadas por ti.','Xác nhận mã khớp với mã tác nhân hiển thị. Phê duyệt cho phép tác nhân đọc, lưu và xóa ký ức. Chỉ phê duyệt yêu cầu do bạn bắt đầu.','ยืนยันว่ารหัสตรงกับที่เอเจนต์แสดง การอนุมัติให้เอเจนต์อ่าน บันทึก และลบความทรงจำได้ อนุมัติเฉพาะคำขอที่คุณเริ่มเอง'],
    ['비밀값','Secret value','秘密值','秘密値','Valor secreto','Giá trị bí mật','ค่าความลับ'],
    ['이 링크는 사용 완료되어 다시 열 수 없습니다. 이제 이 창을 닫아도 됩니다.','This link has been used and cannot be opened again. You can close this window.','此链接已使用，无法再次打开。现在可以关闭窗口。','このリンクは使用済みで再度開けません。このウィンドウを閉じて構いません。','Este enlace ya se usó y no puede abrirse de nuevo. Puedes cerrar la ventana.','Liên kết đã được dùng và không thể mở lại. Bạn có thể đóng cửa sổ.','ลิงก์นี้ถูกใช้แล้วและเปิดซ้ำไม่ได้ คุณปิดหน้าต่างได้'],
    ['계정 메뉴','Account menu','账户菜单','アカウントメニュー','Menú de cuenta','Menu tài khoản','เมนูบัญชี'],
    ['계정 메뉴 열기','Open account menu','打开账户菜单','アカウントメニューを開く','Abrir menú de cuenta','Mở menu tài khoản','เปิดเมนูบัญชี'],
    ['상세 패널 닫기','Close details panel','关闭详情面板','詳細パネルを閉じる','Cerrar panel de detalles','Đóng bảng chi tiết','ปิดแผงรายละเอียด'],
    ['Vibe Memory 관리자 홈','Vibe Memory admin home','Vibe Memory 管理首页','Vibe Memory管理ホーム','Inicio de administración','Trang quản trị Vibe Memory','หน้าผู้ดูแล Vibe Memory'],
    ['기능 요청 전용 권한','Feature-request-only permission','仅功能请求权限','機能リクエスト専用権限','Permiso solo para solicitudes','Quyền chỉ dành cho yêu cầu tính năng','สิทธิ์เฉพาะคำขอฟีเจอร์'],
    ['선택한 에이전트만 모든 사용자의 기능 요청을 조회하고 처리 결과를 수정할 수 있습니다.','Only selected agents can view every user’s feature requests and edit outcomes.','仅选定智能体可查看所有用户的功能请求并编辑处理结果。','選択したエージェントだけが全ユーザーの機能リクエストを閲覧し、結果を編集できます。','Solo los agentes seleccionados pueden ver solicitudes de todos los usuarios y editar resultados.','Chỉ tác nhân được chọn mới xem yêu cầu của mọi người dùng và sửa kết quả.','เฉพาะเอเจนต์ที่เลือกเท่านั้นที่ดูคำขอของผู้ใช้ทั้งหมดและแก้ผลลัพธ์ได้'],
    ['사용자 기억·문서·관계·Vault·사용자 목록에는 관리자 권한이 확대되지 않습니다. 필요할 때만 승인하고 작업 후 회수하세요.','This does not grant admin access to memories, documents, relationships, Vault, or users. Approve only when needed and revoke afterward.','此权限不会扩展到记忆、文档、关系、Vault 或用户列表。仅在需要时批准，完成后撤销。','記憶・文書・関係・Vault・ユーザー一覧への管理権限は付与されません。必要なときだけ承認し、作業後に回収してください。','No concede acceso administrativo a memorias, documentos, relaciones, Vault ni usuarios. Apruébalo solo cuando sea necesario y revócalo después.','Quyền này không mở rộng sang ký ức, tài liệu, quan hệ, Vault hay người dùng. Chỉ cấp khi cần và thu hồi sau.','สิทธิ์นี้ไม่ครอบคลุมความทรงจำ เอกสาร ความสัมพันธ์ Vault หรือรายชื่อผู้ใช้ อนุมัติเมื่อจำเป็นและถอนหลังเสร็จ'],
    ['에이전트 연결을 불러오는 중…','Loading agent connections…','正在加载智能体连接…','エージェント接続を読み込み中…','Cargando conexiones de agentes…','Đang tải kết nối tác nhân…','กำลังโหลดการเชื่อมต่อเอเจนต์…'],
    ['요청을 불러오는 중입니다.','Loading requests…','正在加载请求…','リクエストを読み込み中…','Cargando solicitudes…','Đang tải yêu cầu…','กำลังโหลดคำขอ…'],
    ['제목·사용자·결과 검색','Search title, user, or result','搜索标题、用户或结果','タイトル・ユーザー・結果を検索','Buscar título, usuario o resultado','Tìm tiêu đề, người dùng hoặc kết quả','ค้นหาชื่อ ผู้ใช้ หรือผลลัพธ์'],
    ['사용자 목록을 불러오는 중입니다.','Loading users…','正在加载用户…','ユーザー一覧を読み込み中…','Cargando usuarios…','Đang tải người dùng…','กำลังโหลดผู้ใช้…'],
    ['사용자 검색','Search users','搜索用户','ユーザー検索','Buscar usuarios','Tìm người dùng','ค้นหาผู้ใช้'],
    ['이름·이메일 검색','Search name or email','搜索姓名或邮箱','名前・メールを検索','Buscar nombre o correo','Tìm tên hoặc email','ค้นหาชื่อหรืออีเมล'],
    ['권한','Role','权限','権限','Rol','Quyền','สิทธิ์'],
    ['보안','Security','安全','セキュリティ','Seguridad','Bảo mật','ความปลอดภัย'],
    ['가입 시각','Joined at','注册时间','登録日時','Registro','Thời gian đăng ký','เวลาสมัคร'],
    ['연결','Connections','连接','接続','Conexiones','Kết nối','การเชื่อมต่อ'],
    ['저장 용량','Storage','存储用量','保存容量','Almacenamiento','Dung lượng lưu trữ','พื้นที่จัดเก็บ'],
    ['등록 에이전트','Registered agent','注册智能体','登録エージェント','Agente registrado','Tác nhân đã đăng ký','เอเจนต์ที่ลงทะเบียน'],
    ['요청 제목','Request title','请求标题','リクエスト名','Título de la solicitud','Tiêu đề yêu cầu','ชื่อคำขอ'],
    ['처리 상태','Processing status','处理状态','処理状態','Estado de procesamiento','Trạng thái xử lý','สถานะการดำเนินการ'],
    ['사용자에게 공개할 처리 내용과 남은 작업을 적어주세요.','Describe the public outcome and remaining work.','填写向用户公开的处理结果和剩余工作。','ユーザーに公開する結果と残作業を入力してください。','Describe el resultado público y el trabajo restante.','Mô tả kết quả công khai và công việc còn lại.','อธิบายผลลัพธ์ที่เปิดเผยและงานที่เหลือ'],
    ['관련 결과 링크','Related result link','相关结果链接','関連結果リンク','Enlace del resultado','Liên kết kết quả','ลิงก์ผลลัพธ์ที่เกี่ยวข้อง'],
    ['이 기능이 필요한 실제 상황을 적어주세요.','Describe the real situation where this feature is needed.','请描述需要此功能的实际场景。','この機能が必要な実際の状況を入力してください。','Describe la situación real donde necesitas esta función.','Mô tả tình huống thực tế cần tính năng này.','อธิบายสถานการณ์จริงที่ต้องใช้ฟีเจอร์นี้'],
    ['기억은','your memory','记忆仍会','記憶は','tu memoria','ký ức của bạn','ความทรงจำของคุณ'],
    ['하나의 기억으로 연결합니다.','to one shared memory.','连接到同一份记忆。','ひとつの記憶につなぎます。','a una memoria compartida.','vào một bộ nhớ dùng chung.','เข้ากับหน่วยความจำเดียวกัน'],
    ['Vibe Memory 연결 방법','Ways to connect Vibe Memory','Vibe Memory 连接方式','Vibe Memoryの接続方法','Formas de conectar Vibe Memory','Cách kết nối Vibe Memory','วิธีเชื่อมต่อ Vibe Memory'],
    ['Native Rust CLI skill · compact JSON · 별도 LLM 호출 없음','Native Rust CLI Skill · compact JSON · no extra LLM calls','原生 Rust CLI Skill · 紧凑 JSON · 无额外 LLM 调用','ネイティブRust CLI Skill · compact JSON · 追加LLM呼び出しなし','Skill CLI nativo de Rust · JSON compacto · sin llamadas LLM extra','Skill Rust CLI gốc · JSON gọn · không gọi LLM bổ sung','Skill Rust CLI แบบเนทีฟ · JSON กระชับ · ไม่เรียก LLM เพิ่ม'],
    ['상태','Status','状态','状態','Estado','Trạng thái','สถานะ'],
    ['요청','Request','请求','リクエスト','Solicitud','Yêu cầu','คำขอ'],
    ['ChatGPT Work 설치 화면을 열었습니다. 연결이 필요하면 복사된 MCP 주소를 사용하세요.','Opened the ChatGPT Work installation page. Use the copied MCP address if needed.','已打开 ChatGPT Work 安装页面。如需连接，请使用已复制的 MCP 地址。','ChatGPT Workのインストール画面を開きました。必要ならコピーしたMCPアドレスを使ってください。','Se abrió la instalación de ChatGPT Work. Usa la dirección MCP copiada si hace falta.','Đã mở trang cài ChatGPT Work. Dùng địa chỉ MCP đã sao chép nếu cần.','เปิดหน้าติดตั้ง ChatGPT Work แล้ว ใช้ที่อยู่ MCP ที่คัดลอกไว้หากจำเป็น'],
    ['원본은 바이트 스트림으로 업로드하고, 분석한 메타정보는 별도 JSON으로 연결합니다.','Upload the original as a byte stream and link analyzed metadata as separate JSON.','以字节流上传原文件，并用独立 JSON 关联分析后的元数据。','原本はバイトストリームでアップロードし、分析したメタデータは別JSONで関連付けます。','Sube el original como bytes y enlaza los metadatos analizados en un JSON aparte.','Tải bản gốc dưới dạng byte stream và liên kết metadata đã phân tích bằng JSON riêng.','อัปโหลดต้นฉบับเป็น byte stream และเชื่อมเมทาดาทาที่วิเคราะห์แล้วด้วย JSON แยก'],
    ['파일 분석은 에이전트가, 원본 보관은 앱이 담당합니다.','The agent analyzes files; the app stores originals.','智能体分析文件，应用保存原文件。','ファイル分析はエージェント、原本保管はアプリが担当します。','El agente analiza los archivos; la app guarda los originales.','Tác nhân phân tích tệp; ứng dụng lưu bản gốc.','เอเจนต์วิเคราะห์ไฟล์ ส่วนแอปเก็บต้นฉบับ'],
    ['질문은 에이전트가 이해합니다. 앱에는 추출한 검색 키워드만 전달합니다.','The agent understands the question. Only extracted search keywords reach the app.','问题由智能体理解，应用仅接收提取的搜索关键词。','質問はエージェントが理解し、アプリには抽出した検索キーワードだけを渡します。','El agente entiende la pregunta; la app solo recibe las palabras extraídas.','Tác nhân hiểu câu hỏi; ứng dụng chỉ nhận từ khóa tìm kiếm đã trích xuất.','เอเจนต์เข้าใจคำถาม แอปรับเฉพาะคีย์เวิร์ดค้นหาที่สกัดแล้ว'],
    ['키워드로 검색한 뒤, 에이전트가 근거를 구성합니다.','After keyword search, the agent assembles the evidence.','关键词搜索后，智能体会组织依据。','キーワード検索後、エージェントが根拠を構成します。','Tras buscar por palabras clave, el agente reúne las pruebas.','Sau khi tìm bằng từ khóa, tác nhân tổng hợp bằng chứng.','หลังค้นด้วยคีย์เวิร์ด เอเจนต์จะรวบรวมหลักฐาน'],
    ['MCP 연결','MCP connection','MCP 连接','MCP接続','Conexión MCP','Kết nối MCP','การเชื่อมต่อ MCP'],
    ['브라우저','Browser','浏览器','ブラウザ','Navegador','Trình duyệt','เบราว์เซอร์'],
    ['연결 해제됨','Disconnected','已断开','切断済み','Desconectado','Đã ngắt kết nối','ยกเลิกการเชื่อมต่อแล้ว'],
    ['에이전트','Agent','智能体','エージェント','Agente','Tác nhân','เอเจนต์'],
    ['결과 대기 중','Awaiting result','等待结果','結果待ち','Esperando resultado','Đang chờ kết quả','รอผลลัพธ์'],
    ['권한 저장','Save permissions','保存权限','権限を保存','Guardar permisos','Lưu quyền','บันทึกสิทธิ์'],
    ['권한 허용','Allow permission','允许权限','権限を許可','Permitir','Cho phép','อนุญาตสิทธิ์'],
    ['설치 프롬프트 복사','Copy install prompt','复制安装提示词','インストールプロンプトをコピー','Copiar prompt de instalación','Sao chép lời nhắc cài đặt','คัดลอกพรอมต์ติดตั้ง'],
    ['검색 키워드','Search keywords','搜索关键词','検索キーワード','Palabras de búsqueda','Từ khóa tìm kiếm','คีย์เวิร์ดค้นหา'],
    ['검색 키워드를 쉼표로 구분','Separate search keywords with commas','用逗号分隔搜索关键词','検索キーワードをカンマで区切る','Separa las palabras con comas','Phân tách từ khóa bằng dấu phẩy','คั่นคีย์เวิร์ดด้วยจุลภาค'],
    ['검색할 키워드를 입력해주세요.','Enter keywords to search.','请输入搜索关键词。','検索キーワードを入力してください。','Introduce palabras para buscar.','Nhập từ khóa cần tìm.','กรอกคีย์เวิร์ดที่จะค้นหา'],
    ['기록 종류','Record type','记录类型','記録の種類','Tipo de registro','Loại bản ghi','ประเภทรายการ'],
    ['기억 조회','Read memories','读取记忆','記憶を取得','Consultar memorias','Truy xuất ký ức','เรียกดูความทรงจำ'],
    ['기억 사이의 연결','Memory relationships','记忆关系','記憶のつながり','Relaciones de memoria','Quan hệ ký ức','ความสัมพันธ์ของความทรงจำ'],
    ['저장된 사실과 선호','Saved facts and preferences','已保存的事实与偏好','保存された事実と好み','Datos y preferencias guardados','Sự kiện và sở thích đã lưu','ข้อเท็จจริงและความชอบที่บันทึก'],
    ['식별된 사람과 대상','Identified people and entities','已识别的人物与对象','識別された人と対象','Personas y entidades identificadas','Người và đối tượng đã xác định','บุคคลและสิ่งที่ระบุแล้ว'],
    ['연결된 지식 자료','Connected knowledge','关联知识资料','つながった知識資料','Conocimiento conectado','Tri thức được kết nối','ข้อมูลความรู้ที่เชื่อมโยง'],
    ['활성 관계','Active relationships','活跃关系','有効な関係','Relaciones activas','Quan hệ đang hoạt động','ความสัมพันธ์ที่ใช้งาน'],
    ['지원하는 에이전트','Supported agents','支持的智能体','対応エージェント','Agentes compatibles','Tác nhân được hỗ trợ','เอเจนต์ที่รองรับ'],
    ['아직 기록이 없어요.','No records yet.','暂无记录。','まだ記録がありません。','Aún no hay registros.','Chưa có bản ghi.','ยังไม่มีรายการ'],
    ['기억을 직접 남기거나 에이전트에서 데이터를 보내보세요.','Add a memory or send data from an agent.','添加记忆或从智能体发送数据。','記憶を追加するか、エージェントからデータを送ってください。','Añade una memoria o envía datos desde un agente.','Thêm ký ức hoặc gửi dữ liệu từ tác nhân.','เพิ่มความทรงจำหรือส่งข้อมูลจากเอเจนต์'],
    ['연결된 에이전트가 없어요.','No connected agents.','暂无已连接智能体。','接続済みエージェントはありません。','No hay agentes conectados.','Chưa có tác nhân kết nối.','ยังไม่มีเอเจนต์ที่เชื่อมต่อ'],
    ['에이전트에게 Vibe Memory 연결을 요청하면 웹 승인 링크를 안내합니다.','Ask an agent to connect Vibe Memory and it will provide a web approval link.','让智能体连接 Vibe Memory 后，它会提供网页授权链接。','エージェントにVibe Memory接続を頼むとWeb承認リンクを案内します。','Pide a un agente conectar Vibe Memory y mostrará un enlace de aprobación.','Yêu cầu tác nhân kết nối Vibe Memory để nhận liên kết phê duyệt web.','ขอให้เอเจนต์เชื่อม Vibe Memory แล้วจะได้รับลิงก์อนุมัติบนเว็บ'],
    ['저장된 비밀값이 없어요.','No saved secrets.','暂无已保存秘密。','保存済みの秘密はありません。','No hay secretos guardados.','Chưa có bí mật đã lưu.','ยังไม่มีความลับที่บันทึก'],
    ['더 나은 기억을 위한 아이디어가 있나요?','Have an idea for better memory?','有改进记忆功能的想法吗？','より良い記憶のアイデアはありますか？','¿Tienes una idea para mejorar la memoria?','Có ý tưởng để cải thiện ký ức?','มีไอเดียเพื่อปรับปรุงความทรงจำไหม'],
    ['에이전트에서 요청을 보내거나 콘솔에서 필요한 기능과 사용 사례를 남겨주세요.','Send a request from an agent or share the feature and use case here.','可从智能体提交请求，或在控制台填写所需功能与场景。','エージェントから送るか、必要な機能とユースケースをここに残してください。','Envía una solicitud desde un agente o comparte aquí la función y el caso de uso.','Gửi yêu cầu từ tác nhân hoặc chia sẻ tính năng và trường hợp sử dụng tại đây.','ส่งคำขอจากเอเจนต์หรือระบุฟีเจอร์และกรณีใช้งานที่นี่'],
    ['서버 응답을 확인할 수 없습니다. 잠시 후 다시 시도해주세요.','Could not read the server response. Try again shortly.','无法读取服务器响应，请稍后重试。','サーバー応答を確認できません。しばらくして再試行してください。','No se pudo leer la respuesta del servidor. Inténtalo de nuevo.','Không thể đọc phản hồi máy chủ. Hãy thử lại sau.','อ่านการตอบกลับจากเซิร์ฟเวอร์ไม่ได้ โปรดลองใหม่'],
    ['에이전트 API 키 만들기','Create agent API key','创建智能体 API 密钥','エージェントAPIキーを作成','Crear clave API de agente','Tạo khóa API tác nhân','สร้าง API key เอเจนต์'],
    ['새 API 키가 만들어졌어요.','New API key created.','已创建新 API 密钥。','新しいAPIキーを作成しました。','Nueva clave API creada.','Đã tạo khóa API mới.','สร้าง API key ใหม่แล้ว'],
    ['API 키를 복사했습니다.','API key copied.','已复制 API 密钥。','APIキーをコピーしました。','Clave API copiada.','Đã sao chép khóa API.','คัดลอก API key แล้ว'],
    ['표시된 키를 선택해 복사해주세요.','Select and copy the displayed key.','请选择并复制显示的密钥。','表示されたキーを選択してコピーしてください。','Selecciona y copia la clave mostrada.','Chọn và sao chép khóa hiển thị.','เลือกและคัดลอกคีย์ที่แสดง'],
    ['키 만들기','Create key','创建密钥','キーを作成','Crear clave','Tạo khóa','สร้างคีย์'],
    ['에이전트 키를 삭제할까요?','Delete this agent key?','删除此智能体密钥吗？','このエージェントキーを削除しますか？','¿Eliminar esta clave de agente?','Xóa khóa tác nhân này?','ลบคีย์เอเจนต์นี้หรือไม่'],
    ['키 삭제','Delete key','删除密钥','キーを削除','Eliminar clave','Xóa khóa','ลบคีย์'],
    ['연결된 에이전트는 즉시 Vibe Memory를 사용할 수 없게 됩니다.','The connected agent will immediately lose access to Vibe Memory.','已连接智能体将立即失去 Vibe Memory 访问权限。','接続エージェントは直ちにVibe Memoryを使えなくなります。','El agente perderá acceso inmediatamente.','Tác nhân sẽ mất quyền truy cập ngay lập tức.','เอเจนต์จะเสียสิทธิ์เข้าถึงทันที'],
    ['API 키를 삭제했습니다.','API key deleted.','API 密钥已删除。','APIキーを削除しました。','Clave API eliminada.','Đã xóa khóa API.','ลบ API key แล้ว'],
    ['MCP 연결을 해제할까요?','Disconnect this MCP connection?','断开此 MCP 连接吗？','このMCP接続を解除しますか？','¿Desconectar esta conexión MCP?','Ngắt kết nối MCP này?','ยกเลิกการเชื่อมต่อ MCP นี้หรือไม่'],
    ['MCP 연결을 해제했습니다.','MCP connection disconnected.','MCP 连接已断开。','MCP接続を解除しました。','Conexión MCP desconectada.','Đã ngắt kết nối MCP.','ยกเลิกการเชื่อมต่อ MCP แล้ว'],
    ['이 기록을 삭제할까요?','Delete this record?','删除此记录吗？','この記録を削除しますか？','¿Eliminar este registro?','Xóa bản ghi này?','ลบรายการนี้หรือไม่'],
    ['연결된 키워드와 관계도 함께 삭제됩니다. 이 작업은 되돌릴 수 없습니다.','Linked keywords and relationships will also be deleted. This cannot be undone.','关联关键词和关系也会被删除，且无法撤销。','関連キーワードと関係も削除され、元に戻せません。','También se eliminarán palabras y relaciones. No se puede deshacer.','Từ khóa và quan hệ liên kết cũng bị xóa. Không thể hoàn tác.','คีย์เวิร์ดและความสัมพันธ์ที่เชื่อมโยงจะถูกลบและกู้คืนไม่ได้'],
    ['기록 삭제','Delete record','删除记录','記録を削除','Eliminar registro','Xóa bản ghi','ลบรายการ'],
    ['기록을 삭제했습니다.','Record deleted.','记录已删除。','記録を削除しました。','Registro eliminado.','Đã xóa bản ghi.','ลบรายการแล้ว'],
    ['설명 없음','No description','无说明','説明なし','Sin descripción','Không có mô tả','ไม่มีคำอธิบาย'],
    ['값을 붙여넣으세요','Paste the value','粘贴值','値を貼り付けてください','Pega el valor','Dán giá trị','วางค่า'],
    ['어디에 사용하는 비밀값인지','What this secret is used for','此秘密的用途','この秘密の用途','Para qué se usa este secreto','Bí mật này dùng cho việc gì','ความลับนี้ใช้ทำอะไร'],
    ['Vault 비밀값 추가','Add Vault secret','添加 Vault 秘密','Vault秘密を追加','Añadir secreto de Vault','Thêm bí mật Vault','เพิ่มความลับ Vault'],
    ['Vault 비밀값 교체','Replace Vault secret','替换 Vault 秘密','Vault秘密を置換','Reemplazar secreto de Vault','Thay bí mật Vault','เปลี่ยนความลับ Vault'],
    ['암호화 저장','Encrypt and save','加密保存','暗号化して保存','Cifrar y guardar','Mã hóa và lưu','เข้ารหัสและบันทึก'],
    ['비밀값을 암호화해 저장했습니다.','Secret encrypted and saved.','秘密已加密保存。','秘密を暗号化して保存しました。','Secreto cifrado y guardado.','Đã mã hóa và lưu bí mật.','เข้ารหัสและบันทึกความลับแล้ว'],
    ['비밀값을 안전하게 교체했습니다.','Secret safely replaced.','秘密已安全替换。','秘密を安全に置換しました。','Secreto reemplazado de forma segura.','Đã thay bí mật an toàn.','เปลี่ยนความลับอย่างปลอดภัยแล้ว'],
    ['비밀값을 영구 삭제할까요?','Permanently delete this secret?','永久删除此秘密吗？','この秘密を完全に削除しますか？','¿Eliminar este secreto permanentemente?','Xóa vĩnh viễn bí mật này?','ลบความลับนี้ถาวรหรือไม่'],
    ['비밀값 삭제','Delete secret','删除秘密','秘密を削除','Eliminar secreto','Xóa bí mật','ลบความลับ'],
    ['Vault 비밀값을 삭제했습니다.','Vault secret deleted.','Vault 秘密已删除。','Vault秘密を削除しました。','Secreto de Vault eliminado.','Đã xóa bí mật Vault.','ลบความลับ Vault แล้ว'],
    ['Vault 권한을 허용할까요?','Allow Vault access?','允许 Vault 访问吗？','Vaultアクセスを許可しますか？','¿Permitir acceso a Vault?','Cho phép truy cập Vault?','อนุญาตการเข้าถึง Vault หรือไม่'],
    ['Vault 권한을 허용했습니다.','Vault access allowed.','已允许 Vault 访问。','Vaultアクセスを許可しました。','Acceso a Vault permitido.','Đã cho phép truy cập Vault.','อนุญาตการเข้าถึง Vault แล้ว'],
    ['Vault 권한을 차단했습니다.','Vault access blocked.','已阻止 Vault 访问。','Vaultアクセスをブロックしました。','Acceso a Vault bloqueado.','Đã chặn truy cập Vault.','บล็อกการเข้าถึง Vault แล้ว'],
    ['MCP Vault 항목 권한을 저장했습니다.','MCP Vault item permissions saved.','MCP Vault 条目权限已保存。','MCP Vault項目権限を保存しました。','Permisos de Vault MCP guardados.','Đã lưu quyền mục MCP Vault.','บันทึกสิทธิ์รายการ MCP Vault แล้ว'],
    ['복구 코드를 안전하게 보관하세요.','Store recovery codes securely.','请安全保存恢复代码。','復旧コードを安全に保管してください。','Guarda los códigos de recuperación.','Lưu mã khôi phục an toàn.','เก็บรหัสกู้คืนอย่างปลอดภัย'],
    ['복구 코드를 복사했습니다.','Recovery codes copied.','已复制恢复代码。','復旧コードをコピーしました。','Códigos de recuperación copiados.','Đã sao chép mã khôi phục.','คัดลอกรหัสกู้คืนแล้ว'],
    ['코드를 선택해 복사해주세요.','Select and copy the codes.','请选择并复制代码。','コードを選択してコピーしてください。','Selecciona y copia los códigos.','Chọn và sao chép mã.','เลือกและคัดลอกรหัส'],
    ['인증 앱 연결','Connect authenticator','连接身份验证器','認証アプリを接続','Conectar autenticador','Kết nối ứng dụng xác thực','เชื่อมต่อแอปยืนยันตัวตน'],
    ['OTP 설정 시작','Start OTP setup','开始 OTP 设置','OTP設定を開始','Iniciar configuración OTP','Bắt đầu thiết lập OTP','เริ่มตั้งค่า OTP'],
    ['OTP 활성화','Enable OTP','启用 OTP','OTPを有効化','Activar OTP','Bật OTP','เปิดใช้ OTP'],
    ['OTP 로그인을 활성화했습니다.','OTP login enabled.','OTP 登录已启用。','OTPログインを有効にしました。','Inicio con OTP activado.','Đã bật đăng nhập OTP.','เปิดใช้การเข้าสู่ระบบ OTP แล้ว'],
    ['복구 코드 재발급','Regenerate recovery codes','重新生成恢复代码','復旧コードを再発行','Regenerar códigos','Tạo lại mã khôi phục','สร้างรหัสกู้คืนใหม่'],
    ['새 코드 발급','Issue new codes','生成新代码','新しいコードを発行','Emitir códigos nuevos','Cấp mã mới','ออกรหัสใหม่'],
    ['새 복구 코드를 발급했습니다.','New recovery codes issued.','已生成新的恢复代码。','新しい復旧コードを発行しました。','Nuevos códigos emitidos.','Đã cấp mã khôi phục mới.','ออกรหัสกู้คืนใหม่แล้ว'],
    ['OTP 로그인 해제','Disable OTP login','停用 OTP 登录','OTPログインを無効化','Desactivar acceso OTP','Tắt đăng nhập OTP','ปิดการเข้าสู่ระบบ OTP'],
    ['OTP 해제','Disable OTP','停用 OTP','OTPを無効化','Desactivar OTP','Tắt OTP','ปิด OTP'],
    ['OTP 로그인을 해제했습니다.','OTP login disabled.','OTP 登录已停用。','OTPログインを無効にしました。','Inicio con OTP desactivado.','Đã tắt đăng nhập OTP.','ปิดการเข้าสู่ระบบ OTP แล้ว'],
    ['관리자','Administrator','管理员','管理者','Administrador','Quản trị viên','ผู้ดูแล'],
    ['관리자 권한이 필요합니다.','Administrator permission required.','需要管理员权限。','管理者権限が必要です。','Se requiere permiso de administrador.','Cần quyền quản trị viên.','ต้องมีสิทธิ์ผู้ดูแล'],
    ['OTP 사용','OTP enabled','已启用 OTP','OTP使用中','OTP activado','Đã bật OTP','เปิดใช้ OTP'],
    ['전체','All','全部','すべて','Todo','Tất cả','ทั้งหมด'],
    ['운영 권한 활성','Operator access active','运营权限已启用','運用権限有効','Acceso de operador activo','Quyền vận hành đang bật','เปิดสิทธิ์ปฏิบัติการ'],
    ['일반 에이전트','Standard agent','普通智能体','一般エージェント','Agente estándar','Tác nhân thường','เอเจนต์ทั่วไป'],
    ['별도 허용됨','Allowed separately','单独允许','個別に許可','Permitido por separado','Được cho phép riêng','อนุญาตแยกต่างหาก'],
    ['차단','Blocked','已阻止','ブロック','Bloqueado','Đã chặn','บล็อก'],
    ['허용','Allowed','已允许','許可','Permitido','Được phép','อนุญาต'],
    ['출처 미지정','Source unspecified','未指定来源','出典未指定','Fuente no indicada','Chưa chỉ định nguồn','ไม่ระบุแหล่งที่มา'],
    ['운영 에이전트로 승인','Approve as operator','批准为运营智能体','運用エージェントとして承認','Aprobar como operador','Phê duyệt làm tác nhân vận hành','อนุมัติเป็นเอเจนต์ปฏิบัติการ'],
    ['운영 권한 회수','Revoke operator access','撤销运营权限','運用権限を回収','Revocar acceso de operador','Thu hồi quyền vận hành','ถอนสิทธิ์ปฏิบัติการ'],
    ['운영 권한을 회수할까요?','Revoke operator access?','撤销运营权限吗？','運用権限を回収しますか？','¿Revocar el acceso de operador?','Thu hồi quyền vận hành?','ถอนสิทธิ์ปฏิบัติการหรือไม่'],
    ['운영 에이전트로 승인할까요?','Approve as an operator agent?','批准为运营智能体吗？','運用エージェントとして承認しますか？','¿Aprobar como agente operador?','Phê duyệt làm tác nhân vận hành?','อนุมัติเป็นเอเจนต์ปฏิบัติการหรือไม่'],
    ['이 에이전트는 즉시 모든 사용자의 기능 요청 조회와 처리를 할 수 없게 됩니다.','This agent will immediately lose access to all users’ feature requests.','该智能体将立即无法查看和处理所有用户的功能请求。','このエージェントは全ユーザーの機能リクエストを直ちに閲覧・処理できなくなります。','Este agente perderá acceso inmediato a las solicitudes de todos los usuarios.','Tác nhân sẽ mất ngay quyền xem và xử lý yêu cầu của mọi người dùng.','เอเจนต์นี้จะเสียสิทธิ์ดูและดำเนินการคำขอของผู้ใช้ทั้งหมดทันที'],
    ['이 에이전트는 모든 사용자의 기능 요청 내용을 조회하고 처리 상태와 공개 결과를 수정할 수 있습니다. 기억·사용자·Vault 권한은 부여되지 않습니다.','This agent can view all users’ feature requests and edit status and public outcomes. It receives no memory, user, or Vault permissions.','该智能体可查看所有用户的功能请求并编辑状态与公开结果，但不会获得记忆、用户或 Vault 权限。','このエージェントは全ユーザーの機能リクエストを閲覧し、状態と公開結果を編集できます。記憶・ユーザー・Vault権限は付与されません。','Este agente puede ver solicitudes de todos los usuarios y editar estado y resultados públicos. No recibe permisos de memoria, usuarios ni Vault.','Tác nhân có thể xem yêu cầu của mọi người dùng và sửa trạng thái cùng kết quả công khai, nhưng không có quyền ký ức, người dùng hay Vault.','เอเจนต์นี้ดูคำขอของผู้ใช้ทั้งหมดและแก้สถานะกับผลลัพธ์สาธารณะได้ แต่ไม่ได้สิทธิ์ความทรงจำ ผู้ใช้ หรือ Vault'],
    ['운영 에이전트 권한을 승인했습니다.','Operator access approved.','运营权限已批准。','運用エージェント権限を承認しました。','Acceso de operador aprobado.','Đã phê duyệt quyền vận hành.','อนุมัติสิทธิ์ปฏิบัติการแล้ว'],
    ['운영 에이전트 권한을 회수했습니다.','Operator access revoked.','运营权限已撤销。','運用エージェント権限を回収しました。','Acceso de operador revocado.','Đã thu hồi quyền vận hành.','ถอนสิทธิ์ปฏิบัติการแล้ว'],
    ['요청과 처리 결과를 저장했습니다.','Request and outcome saved.','请求与处理结果已保存。','リクエストと処理結果を保存しました。','Solicitud y resultado guardados.','Đã lưu yêu cầu và kết quả.','บันทึกคำขอและผลลัพธ์แล้ว'],
    ['서버 응답을 확인할 수 없습니다.','Could not read the server response.','无法读取服务器响应。','サーバー応答を確認できません。','No se pudo leer la respuesta del servidor.','Không thể đọc phản hồi máy chủ.','อ่านการตอบกลับจากเซิร์ฟเวอร์ไม่ได้'],
    ['요청을 처리하지 못했습니다.','Could not process the request.','无法处理请求。','リクエストを処理できませんでした。','No se pudo procesar la solicitud.','Không thể xử lý yêu cầu.','ดำเนินการคำขอไม่ได้'],
    ['“프로젝트 문서의 맥락도 기억해줘.”','“Remember the context from the project documents too.”','“也请记住项目文档的上下文。”','「プロジェクト文書の文脈も覚えて。」','«Recuerda también el contexto de los documentos del proyecto».','“Hãy nhớ cả ngữ cảnh từ tài liệu dự án.”','“จำบริบทจากเอกสารโปรเจกต์ด้วย”'],
    ['“내가 선호하는 개발 언어가 뭐였지?”','“Which programming language did I prefer?”','“我偏好的编程语言是什么？”','「私が好む開発言語は何だっけ？」','«¿Qué lenguaje de programación prefería?»','“Tôi thích ngôn ngữ lập trình nào?”','“ฉันชอบภาษาเขียนโปรแกรมอะไรนะ”'],
    ['API 토큰과 자동화 자격 증명을 암호화해 저장하고 허용한 에이전트에서 사용하세요.','Encrypt API tokens and automation credentials for approved agents.','加密保存 API 令牌和自动化凭据，供已授权智能体使用。','APIトークンと自動化資格情報を暗号化し、許可したエージェントで使います。','Cifra tokens API y credenciales para agentes autorizados.','Mã hóa token API và thông tin tự động hóa cho tác nhân được phép.','เข้ารหัส API token และข้อมูลรับรองอัตโนมัติสำหรับเอเจนต์ที่อนุญาต'],
    ['Vault 목록','Vault list','Vault 列表','Vault一覧','Lista de Vault','Danh sách Vault','รายการ Vault'],
    ['Vault 항목 조회','Read Vault item','读取 Vault 条目','Vault項目を取得','Leer elemento de Vault','Đọc mục Vault','เรียกดูรายการ Vault'],
    ['Vibe Memory MCP 주소','Vibe Memory MCP address','Vibe Memory MCP 地址','Vibe Memory MCPアドレス','Dirección MCP de Vibe Memory','Địa chỉ MCP Vibe Memory','ที่อยู่ MCP ของ Vibe Memory'],
    ['Vibe Memory OTP 설정 QR 코드','Vibe Memory OTP setup QR code','Vibe Memory OTP 设置二维码','Vibe Memory OTP設定QRコード','Código QR de configuración OTP','Mã QR thiết lập OTP Vibe Memory','QR code ตั้งค่า OTP ของ Vibe Memory'],
    ['기억 사이의 연결을 기다리고 있어요.','Waiting for memory relationships.','正在等待记忆关系。','記憶どうしのつながりを待っています。','Esperando relaciones de memoria.','Đang chờ quan hệ ký ức.','กำลังรอความสัมพันธ์ของความทรงจำ'],
    ['기억할 사실이나 선호를 입력하세요.','Enter a fact or preference to remember.','输入要记住的事实或偏好。','覚えておく事実や好みを入力してください。','Introduce un dato o preferencia para recordar.','Nhập sự kiện hoặc sở thích cần nhớ.','กรอกข้อเท็จจริงหรือความชอบที่จะจำ'],
    ['설정 키를 복사했습니다.','Setup key copied.','已复制设置密钥。','設定キーをコピーしました。','Clave de configuración copiada.','Đã sao chép khóa thiết lập.','คัดลอกคีย์ตั้งค่าแล้ว'],
    ['설정 키를 선택해 복사해주세요.','Select and copy the setup key.','请选择并复制设置密钥。','設定キーを選択してコピーしてください。','Selecciona y copia la clave de configuración.','Chọn và sao chép khóa thiết lập.','เลือกและคัดลอกคีย์ตั้งค่า'],
    ['아직 조회 내역이 없어요.','No access history yet.','暂无访问记录。','まだ取得履歴はありません。','Aún no hay historial de acceso.','Chưa có lịch sử truy cập.','ยังไม่มีประวัติการเข้าถึง'],
    ['어떤 기능이 필요한가요?','What feature do you need?','需要什么功能？','どんな機能が必要ですか？','¿Qué función necesitas?','Bạn cần tính năng gì?','ต้องการฟีเจอร์อะไร'],
    ['에이전트 설치·최신화 프롬프트','Agent install and update prompt','智能体安装与更新提示词','エージェントのインストール・更新プロンプト','Prompt de instalación y actualización','Lời nhắc cài đặt và cập nhật tác nhân','พรอมต์ติดตั้งและอัปเดตเอเจนต์'],
    ['에이전트가 Vault 항목을 조회하거나 권한 없는 조회를 시도하면 여기에 기록됩니다.','Vault reads and denied attempts by agents are recorded here.','智能体读取 Vault 条目或尝试未授权访问时会记录在此。','エージェントのVault取得と権限なしの試行をここに記録します。','Aquí se registran las lecturas de Vault y los intentos denegados.','Lượt đọc Vault và thử truy cập bị từ chối được ghi tại đây.','การอ่าน Vault และความพยายามที่ถูกปฏิเสธจะบันทึกที่นี่'],
    ['에이전트가 엔티티와 관계를 구성해 등록하면 여기에 표시됩니다.','Agent-created entities and relationships appear here.','智能体创建并登记的实体和关系会显示在此。','エージェントが登録したエンティティと関係をここに表示します。','Aquí aparecen entidades y relaciones creadas por agentes.','Thực thể và quan hệ do tác nhân tạo hiển thị tại đây.','เอนทิตีและความสัมพันธ์ที่เอเจนต์สร้างจะแสดงที่นี่'],
    ['에이전트에서 파일을 등록하거나 원본을 업로드해보세요. 분석과 키워드 추출은 에이전트가 담당합니다.','Register a file from an agent or upload an original. Agents handle analysis and keyword extraction.','从智能体登记文件或上传原文件。分析与关键词提取由智能体完成。','エージェントからファイルを登録するか原本をアップロードしてください。分析とキーワード抽出はエージェントが担当します。','Registra un archivo desde un agente o sube un original. El agente analiza y extrae palabras.','Đăng ký tệp từ tác nhân hoặc tải bản gốc. Tác nhân phân tích và trích xuất từ khóa.','ลงทะเบียนไฟล์จากเอเจนต์หรืออัปโหลดต้นฉบับ เอเจนต์จะวิเคราะห์และสกัดคีย์เวิร์ด'],
    ['예: Claude Code, Codex, Cursor, Muse Code','e.g. Claude Code, Codex, Cursor, Muse Code','例如 Claude Code、Codex、Cursor、Muse Code','例: Claude Code、Codex、Cursor、Muse Code','p. ej. Claude Code, Codex, Cursor, Muse Code','VD: Claude Code, Codex, Cursor, Muse Code','เช่น Claude Code, Codex, Cursor, Muse Code'],
    ['예: GITHUB_TOKEN','e.g. GITHUB_TOKEN','例如 GITHUB_TOKEN','例: GITHUB_TOKEN','p. ej. GITHUB_TOKEN','VD: GITHUB_TOKEN','เช่น GITHUB_TOKEN'],
    ['예: Python, 개발 언어','e.g. Python, programming language','例如 Python、编程语言','例: Python、開発言語','p. ej. Python, lenguaje de programación','VD: Python, ngôn ngữ lập trình','เช่น Python, ภาษาเขียนโปรแกรม'],
    ['이 GPT·Claude 연결은 즉시 기억과 Vault에 접근할 수 없게 됩니다.','This GPT or Claude connection will immediately lose memory and Vault access.','此 GPT 或 Claude 连接将立即失去记忆和 Vault 访问权限。','このGPT・Claude接続は記憶とVaultへ直ちにアクセスできなくなります。','Esta conexión de GPT o Claude perderá acceso a memoria y Vault.','Kết nối GPT hoặc Claude sẽ mất ngay quyền truy cập ký ức và Vault.','การเชื่อมต่อ GPT หรือ Claude นี้จะเสียสิทธิ์เข้าถึงความทรงจำและ Vault ทันที'],
    ['이 기능이 어떤 작업에 도움이 되나요?','What work would this feature help with?','此功能能帮助完成什么工作？','この機能はどんな作業に役立ちますか？','¿En qué trabajo ayudaría esta función?','Tính năng này giúp công việc nào?','ฟีเจอร์นี้ช่วยงานอะไร'],
    ['이 에이전트는 저장된 모든 비밀값을 실행 프로세스에 전달할 수 있습니다. 신뢰하는 에이전트인지 확인하세요.','This agent can pass all saved secrets to a process. Verify that you trust it.','该智能体可将所有已保存的秘密传给进程，请确认其可信。','このエージェントは保存済みの全秘密をプロセスに渡せます。信頼できるか確認してください。','Este agente puede pasar todos los secretos guardados a un proceso. Verifica que sea de confianza.','Tác nhân có thể chuyển mọi bí mật đã lưu cho tiến trình. Hãy xác minh độ tin cậy.','เอเจนต์นี้ส่งความลับทั้งหมดให้โปรเซสได้ โปรดยืนยันว่าเชื่อถือได้'],
    ['권한 회수','Revoke access','撤销权限','権限を回収','Revocar acceso','Thu hồi quyền','ถอนสิทธิ์']
  ];
  const coreSupplementRows = [
    ['이 페이지는','This page is','此页面','このページは','Esta página','Trang này','หน้านี้'],
    ['기억에 없네요.','not in memory.','不在记忆中。','記憶にありません。','no está en la memoria.','không có trong ký ức.','ไม่อยู่ในความทรงจำ'],
    ['주소를 확인하거나 Vibe Memory 홈에서 다시 시작하세요.','Check the address or start again from the Vibe Memory home page.','请检查地址，或从 Vibe Memory 首页重新开始。','アドレスを確認するか、Vibe Memoryホームからやり直してください。','Comprueba la dirección o vuelve a empezar desde el inicio de Vibe Memory.','Kiểm tra địa chỉ hoặc bắt đầu lại từ trang chủ Vibe Memory.','ตรวจสอบที่อยู่หรือเริ่มใหม่จากหน้าแรก Vibe Memory'],
    ['홈으로 돌아가기','Return home','返回首页','ホームに戻る','Volver al inicio','Về trang chủ','กลับหน้าแรก'],
    ['프롬프트를 Claude Code, Codex, Cursor, Muse Code, OpenClaw 또는 Hermes에 붙여넣으면 설치·웹 승인 후 별도 요청 없이 관련 기억을 조회하고 중요한 맥락을 체크포인트로 이어갑니다.','Paste the prompt into Claude Code, Codex, Cursor, Muse Code, OpenClaw, or Hermes. After installation and web approval, the agent recalls relevant memories and checkpoints important context without another request.','将提示词粘贴到 Claude Code、Codex、Cursor、Muse Code、OpenClaw 或 Hermes。安装并网页授权后，智能体会主动检索相关记忆并以检查点延续重要上下文。','プロンプトをClaude Code、Codex、Cursor、Muse Code、OpenClaw、Hermesに貼り付けます。インストールとWeb承認後は、追加依頼なしで関連記憶を取得し、重要な文脈をチェックポイントで引き継ぎます。','Pega el prompt en Claude Code, Codex, Cursor, Muse Code, OpenClaw o Hermes. Tras instalar y aprobar en la web, el agente recupera recuerdos relevantes y conserva el contexto importante sin otra petición.','Dán lời nhắc vào Claude Code, Codex, Cursor, Muse Code, OpenClaw hoặc Hermes. Sau khi cài đặt và phê duyệt trên web, tác nhân chủ động truy xuất ký ức liên quan và lưu ngữ cảnh quan trọng.','วางพรอมต์ใน Claude Code, Codex, Cursor, Muse Code, OpenClaw หรือ Hermes หลังติดตั้งและอนุมัติผ่านเว็บ เอเจนต์จะเรียกคืนความทรงจำที่เกี่ยวข้องและบันทึกบริบทสำคัญโดยไม่ต้องสั่งซ้ำ'],
    ['관련 결과 보기','View related result','查看相关结果','関連結果を見る','Ver resultado relacionado','Xem kết quả liên quan','ดูผลลัพธ์ที่เกี่ยวข้อง'],
    ['처리 결과','Outcome','处理结果','処理結果','Resultado','Kết quả','ผลลัพธ์'],
    ['아직 등록된 처리 결과가 없습니다.','No outcome has been posted yet.','尚未发布处理结果。','処理結果はまだ登録されていません。','Aún no se ha publicado ningún resultado.','Chưa có kết quả xử lý.','ยังไม่มีผลลัพธ์ที่เผยแพร่'],
    ['요청 내용','Request details','请求内容','リクエスト内容','Detalles de la solicitud','Nội dung yêu cầu','รายละเอียดคำขอ'],
    ['사용 사례','Use case','使用场景','ユースケース','Caso de uso','Trường hợp sử dụng','กรณีใช้งาน'],
    ['요청 에이전트','Requesting agent','请求智能体','リクエスト元エージェント','Agente solicitante','Tác nhân yêu cầu','เอเจนต์ผู้ขอ'],
    ['우선순위','Priority','优先级','優先度','Prioridad','Ưu tiên','ลำดับความสำคัญ'],
    ['접수일','Received','接收日期','受付日','Fecha de recepción','Ngày tiếp nhận','วันที่รับ'],
    ['처리일','Resolved','处理日期','処理日','Fecha de resolución','Ngày xử lý','วันที่ดำเนินการ'],
    ['이름 없는 기록','Untitled record','无标题记录','名前のない記録','Registro sin título','Bản ghi chưa đặt tên','รายการไม่มีชื่อ'],
    ['원본 파일','Original file','原文件','原本ファイル','Archivo original','Tệp gốc','ไฟล์ต้นฉบับ'],
    ['기록','Record','记录','記録','Registro','Bản ghi','รายการ'],
    ['관계 그래프.','Relationship graph.','关系图谱。','関係グラフ。','Grafo de relaciones.','Đồ thị quan hệ.','กราฟความสัมพันธ์'],
    ['노드나 관계를 선택하면 상세 정보를 확인할 수 있습니다.','Select a node or relationship to view details.','选择节点或关系以查看详情。','ノードまたは関係を選ぶと詳細を確認できます。','Selecciona un nodo o relación para ver detalles.','Chọn nút hoặc quan hệ để xem chi tiết.','เลือกโหนดหรือความสัมพันธ์เพื่อดูรายละเอียด'],
    ['그래프 화면 조절','Graph controls','图谱控制','グラフ操作','Controles del grafo','Điều khiển đồ thị','ตัวควบคุมกราฟ'],
    ['확대','Zoom in','放大','拡大','Acercar','Phóng to','ซูมเข้า'],
    ['축소','Zoom out','缩小','縮小','Alejar','Thu nhỏ','ซูมออก'],
    ['그래프 전체 보기','Fit graph','适应图谱','グラフ全体を表示','Ajustar grafo','Vừa toàn bộ đồ thị','แสดงกราฟทั้งหมด'],
    ['연결된 기억','Connected memories','关联记忆','つながる記憶','Memorias conectadas','Ký ức được kết nối','ความทรงจำที่เชื่อมโยง'],
    ['관계 근거','Relationship evidence','关系依据','関係の根拠','Evidencia de la relación','Bằng chứng quan hệ','หลักฐานความสัมพันธ์'],
    ['에이전트가 등록한 근거','Evidence submitted by the agent','智能体提交的依据','エージェントが登録した根拠','Evidencia registrada por el agente','Bằng chứng do tác nhân đăng ký','หลักฐานที่เอเจนต์บันทึก'],
    ['빠른 시작','Quick start','快速开始','クイックスタート','Inicio rápido','Bắt đầu nhanh','เริ่มต้นด่วน'],
    ['워크스페이스 빠른 작업','Workspace quick actions','工作区快捷操作','ワークスペースのクイック操作','Acciones rápidas del espacio','Thao tác nhanh trong không gian','การทำงานด่วนในพื้นที่ทำงาน'],
    ['다시 보지 않기','Do not show again','不再显示','今後表示しない','No volver a mostrar','Không hiển thị lại','ไม่ต้องแสดงอีก'],
    ['내 기억 용량','My memory storage','我的记忆用量','記憶の使用量','Mi almacenamiento','Dung lượng ký ức','พื้นที่ความทรงจำของฉัน'],
    ['현재 논리 사용량 · 휴지통 포함','Current logical usage · includes trash','当前逻辑用量 · 含回收站','現在の論理使用量 · ゴミ箱を含む','Uso lógico actual · incluye papelera','Dung lượng logic hiện tại · gồm thùng rác','การใช้งานเชิงตรรกะปัจจุบัน · รวมถังขยะ'],
    ['기억 데이터','Memory data','记忆数据','記憶データ','Datos de memoria','Dữ liệu ký ức','ข้อมูลความทรงจำ'],
    ['앱 저장 한도 미설정','No app storage limit set','未设置应用存储上限','アプリの保存上限未設定','Sin límite de almacenamiento configurado','Chưa đặt giới hạn lưu trữ','ยังไม่ได้ตั้งขีดจำกัดพื้นที่'],
    ['저장된 사실과 선호','Saved facts and preferences','已保存的事实与偏好','保存した事実と好み','Datos y preferencias guardados','Sự kiện và sở thích đã lưu','ข้อเท็จจริงและความชอบที่บันทึก'],
    ['연결된 지식 자료','Connected knowledge sources','已连接的知识资料','つながる知識資料','Fuentes de conocimiento conectadas','Nguồn tri thức đã kết nối','แหล่งความรู้ที่เชื่อมโยง'],
    ['식별된 사람과 대상','Identified people and entities','已识别的人物与对象','識別された人物と対象','Personas y entidades identificadas','Người và đối tượng đã nhận diện','บุคคลและสิ่งที่ระบุแล้ว'],
    ['기억 사이의 연결','Connections between memories','记忆之间的连接','記憶どうしのつながり','Conexiones entre recuerdos','Kết nối giữa các ký ức','การเชื่อมโยงระหว่างความทรงจำ'],
    ['최근 기록','Recent records','最近记录','最近の記録','Registros recientes','Bản ghi gần đây','รายการล่าสุด'],
    ['최근 저장된 워크스페이스 데이터','Recently saved workspace data','最近保存的工作区数据','最近保存されたワークスペースデータ','Datos guardados recientemente','Dữ liệu không gian vừa lưu','ข้อมูลพื้นที่ทำงานที่บันทึกล่าสุด'],
    ['전체 보기','View all','查看全部','すべて見る','Ver todo','Xem tất cả','ดูทั้งหมด'],
    ['기록 없음','No records','无记录','記録なし','Sin registros','Không có bản ghi','ไม่มีรายการ'],
    ['저장된 워크스페이스 데이터가 없습니다.','No workspace data has been saved.','尚未保存工作区数据。','保存されたワークスペースデータはありません。','No hay datos guardados en el espacio.','Chưa có dữ liệu không gian được lưu.','ยังไม่มีข้อมูลพื้นที่ทำงานที่บันทึก'],
    ['연결 상태','Connection status','连接状态','接続状態','Estado de conexión','Trạng thái kết nối','สถานะการเชื่อมต่อ'],
    ['정상','Healthy','正常','正常','Correcto','Bình thường','ปกติ'],
    ['에이전트 키','Agent keys','智能体密钥','エージェントキー','Claves de agente','Khóa tác nhân','คีย์เอเจนต์'],
    ['전체 기록','Total records','记录总数','全記録','Registros totales','Tổng bản ghi','รายการทั้งหมด'],
    ['초기화','Reset','重置','リセット','Restablecer','Đặt lại','รีเซ็ต'],
    ['기록 종류','Record type','记录类型','記録の種類','Tipo de registro','Loại bản ghi','ประเภทรายการ'],
    ['문서 메타정보','Document metadata','文档元数据','文書メタデータ','Metadatos del documento','Metadata tài liệu','เมทาดาทาเอกสาร'],
    ['아직 기록이 없어요.','No records yet.','暂无记录。','まだ記録がありません。','Aún no hay registros.','Chưa có bản ghi.','ยังไม่มีรายการ'],
    ['기억을 직접 남기거나 에이전트에서 데이터를 보내보세요.','Add a memory or send data from an agent.','请直接添加记忆或从智能体发送数据。','記憶を追加するか、エージェントからデータを送信してください。','Añade una memoria o envía datos desde un agente.','Thêm ký ức hoặc gửi dữ liệu từ tác nhân.','เพิ่มความทรงจำหรือส่งข้อมูลจากเอเจนต์'],
    ['검색 결과가 없어요.','No search results.','没有搜索结果。','検索結果がありません。','No hay resultados.','Không có kết quả tìm kiếm.','ไม่พบผลการค้นหา'],
    ['다른 키워드로 검색해보세요.','Try different keywords.','请尝试其他关键词。','別のキーワードで検索してください。','Prueba con otras palabras.','Thử từ khóa khác.','ลองใช้คีย์เวิร์ดอื่น'],
    ['비밀값 원문은 감사 기록에 저장되지 않습니다.','Secret values are never stored in the audit log.','秘密原文不会存入审计日志。','秘密値の原文は監査ログに保存されません。','Los valores secretos no se guardan en el registro de auditoría.','Giá trị bí mật không được lưu trong nhật ký kiểm tra.','ค่าความลับจะไม่ถูกเก็บในบันทึกตรวจสอบ'],
    ['값은 저장 후 다시 표시되지 않습니다.','Values are not shown again after saving.','保存后不会再次显示值。','保存後、値は再表示されません。','Los valores no se vuelven a mostrar tras guardarlos.','Giá trị không hiển thị lại sau khi lưu.','ค่าจะไม่แสดงอีกหลังบันทึก'],
    ['비밀값은 AES-256-GCM으로 암호화되며, Vault 권한을 따로 허용한 에이전트만','Secrets are encrypted with AES-256-GCM. Only agents granted separate Vault access can','秘密使用 AES-256-GCM 加密。只有单独获得 Vault 权限的智能体可以','秘密値はAES-256-GCMで暗号化され、Vault権限を個別に許可したエージェントだけが','Los secretos se cifran con AES-256-GCM. Solo los agentes con permiso Vault pueden','Bí mật được mã hóa bằng AES-256-GCM. Chỉ tác nhân được cấp quyền Vault mới có thể','ความลับเข้ารหัสด้วย AES-256-GCM เฉพาะเอเจนต์ที่ได้รับสิทธิ์ Vault เท่านั้นที่สามารถ'],
    ['로 프로세스에 전달할 수 있습니다. 조회 내역에는 값이 아닌 항목명·에이전트·결과·UTC 시각만 남습니다.','to pass them to a process. Access history stores only the item name, agent, outcome, and UTC time—not the value.','将其传递给进程。访问记录仅保留条目名、智能体、结果和 UTC 时间，不保留值。','でプロセスへ渡せます。取得履歴には値ではなく、項目名・エージェント・結果・UTC時刻だけが残ります。','para pasarlos a un proceso. El historial guarda solo nombre, agente, resultado y hora UTC, nunca el valor.','để chuyển chúng cho tiến trình. Lịch sử chỉ lưu tên mục, tác nhân, kết quả và giờ UTC, không lưu giá trị.','เพื่อส่งไปยังกระบวนการ ประวัติจะเก็บเฉพาะชื่อรายการ เอเจนต์ ผลลัพธ์ และเวลา UTC ไม่เก็บค่า'],
    ['암호화된 비밀','Encrypted secrets','加密秘密','暗号化された秘密','Secretos cifrados','Bí mật đã mã hóa','ความลับที่เข้ารหัส'],
    ['비밀키 조회 내역','Secret access history','秘密访问记录','秘密値の取得履歴','Historial de acceso a secretos','Lịch sử truy cập bí mật','ประวัติการเข้าถึงความลับ'],
    ['값 미포함','Values excluded','不含值','値は含まれません','Sin valores','Không gồm giá trị','ไม่รวมค่า'],
    ['조회 항목','Accessed item','访问条目','取得項目','Elemento consultado','Mục đã truy cập','รายการที่เข้าถึง'],
    ['결과','Outcome','结果','結果','Resultado','Kết quả','ผลลัพธ์'],
    ['조회 시각','Accessed at','访问时间','取得時刻','Hora de acceso','Thời gian truy cập','เวลาเข้าถึง'],
    ['조회 성공','Read succeeded','读取成功','取得成功','Lectura correcta','Đọc thành công','อ่านสำเร็จ'],
    ['목록 조회','List read','列表读取','一覧取得','Lectura de lista','Đọc danh sách','อ่านรายการ'],
    ['Vault 권한 없음','No Vault access','无 Vault 权限','Vault権限なし','Sin acceso a Vault','Không có quyền Vault','ไม่มีสิทธิ์ Vault'],
    ['항목 미승인','Item not approved','条目未获批准','項目未承認','Elemento no aprobado','Mục chưa được duyệt','รายการไม่ได้รับอนุมัติ'],
    ['항목 없음','Item not found','条目不存在','項目なし','Elemento no encontrado','Không tìm thấy mục','ไม่พบรายการ'],
    ['무결성 오류','Integrity error','完整性错误','整合性エラー','Error de integridad','Lỗi toàn vẹn','ข้อผิดพลาดความสมบูรณ์'],
    ['알 수 없음','Unknown','未知','不明','Desconocido','Không rõ','ไม่ทราบ'],
    ['아직 연결된 원격 MCP 클라이언트가 없습니다.','No remote MCP clients are connected yet.','尚未连接远程 MCP 客户端。','接続されたリモートMCPクライアントはまだありません。','Aún no hay clientes MCP remotos conectados.','Chưa có ứng dụng MCP từ xa được kết nối.','ยังไม่มีไคลเอนต์ MCP ระยะไกลที่เชื่อมต่อ'],
    ['Plugin을 설치하면 Vibe Memory 로그인과 권한 승인이 이어집니다. Claude나 다른 MCP 클라이언트는 아래 주소로 연결할 수 있습니다.','Installing the plugin continues to Vibe Memory login and permission approval. Connect Claude or another MCP client with the address below.','安装插件后将继续登录 Vibe Memory 并批准权限。Claude 或其他 MCP 客户端可使用下方地址连接。','プラグインをインストールすると、Vibe Memoryへのログインと権限承認へ進みます。ClaudeなどのMCPクライアントは下のアドレスで接続できます。','Al instalar el plugin continuarás con el inicio de sesión y la aprobación. Conecta Claude u otro cliente MCP con la dirección siguiente.','Cài plugin để tiếp tục đăng nhập và phê duyệt Vibe Memory. Kết nối Claude hoặc ứng dụng MCP khác bằng địa chỉ dưới đây.','เมื่อติดตั้งปลั๊กอิน ระบบจะไปยังการเข้าสู่ระบบและอนุมัติสิทธิ์ เชื่อม Claude หรือไคลเอนต์ MCP อื่นด้วยที่อยู่ด้านล่าง'],
    ['다른 MCP용 주소 복사','Copy address for another MCP client','复制其他 MCP 客户端地址','他のMCP用アドレスをコピー','Copiar dirección para otro MCP','Sao chép địa chỉ cho MCP khác','คัดลอกที่อยู่สำหรับ MCP อื่น'],
    ['연결 방법 보기','View connection guide','查看连接方法','接続方法を見る','Ver guía de conexión','Xem cách kết nối','ดูวิธีเชื่อมต่อ'],
    ['원격 MCP 연결','Remote MCP connections','远程 MCP 连接','リモートMCP接続','Conexiones MCP remotas','Kết nối MCP từ xa','การเชื่อมต่อ MCP ระยะไกล'],
    ['허용 범위','Granted scopes','授权范围','許可スコープ','Ámbitos permitidos','Phạm vi được phép','ขอบเขตที่อนุญาต'],
    ['OAuth · 웹 승인 연결','OAuth · web-approved connection','OAuth · 网页授权连接','OAuth · Web承認接続','OAuth · conexión aprobada en la web','OAuth · kết nối phê duyệt trên web','OAuth · การเชื่อมต่อที่อนุมัติผ่านเว็บ'],
    ['Vault 항목','Vault items','Vault 条目','Vault項目','Elementos de Vault','Mục Vault','รายการ Vault'],
    ['Vault 재연결 필요','Reconnect to enable Vault','需重新连接以启用 Vault','Vault利用には再接続が必要','Reconecta para activar Vault','Kết nối lại để dùng Vault','เชื่อมต่อใหม่เพื่อใช้ Vault'],
    ['수동 키는 고급 설정용입니다. 새로 연결할 때는 에이전트가 만드는 웹 승인 링크를 권장합니다.','Manual keys are for advanced setup. For new connections, use the web approval link created by the agent.','手动密钥用于高级设置。新连接建议使用智能体生成的网页授权链接。','手動キーは高度な設定用です。新規接続にはエージェントが作成するWeb承認リンクを推奨します。','Las claves manuales son para configuración avanzada. Para conexiones nuevas, usa el enlace web creado por el agente.','Khóa thủ công dành cho thiết lập nâng cao. Với kết nối mới, hãy dùng liên kết web do tác nhân tạo.','คีย์แบบกำหนดเองมีไว้สำหรับการตั้งค่าขั้นสูง การเชื่อมต่อใหม่ควรใช้ลิงก์อนุมัติที่เอเจนต์สร้าง'],
    ['지원하는 에이전트','Supported agents','支持的智能体','対応エージェント','Agentes compatibles','Tác nhân được hỗ trợ','เอเจนต์ที่รองรับ'],
    ['OTP 사용 중','OTP enabled','OTP 已启用','OTP使用中','OTP activado','OTP đang bật','เปิดใช้ OTP'],
    ['OTP 사용 안 함','OTP disabled','OTP 未启用','OTP未使用','OTP desactivado','OTP đang tắt','ปิด OTP'],
    ['인증 방식','Authentication method','验证方式','認証方式','Método de autenticación','Phương thức xác thực','วิธียืนยันตัวตน'],
    ['표준 TOTP 인증 앱','Standard TOTP authenticator','标准 TOTP 验证器','標準TOTP認証アプリ','Aplicación TOTP estándar','Ứng dụng TOTP tiêu chuẩn','แอปยืนยันตัวตน TOTP มาตรฐาน'],
    ['활성화','Enabled at','启用时间','有効化','Activado','Đã bật lúc','เปิดใช้เมื่อ'],
    ['남은 복구 코드','Recovery codes remaining','剩余恢复代码','残りの復旧コード','Códigos de recuperación restantes','Mã khôi phục còn lại','รหัสกู้คืนที่เหลือ'],
    ['Google Authenticator, Microsoft Authenticator, 1Password 등 표준 TOTP 앱을 연결할 수 있습니다. 활성화하면 이메일과 비밀번호 입력 후 일회용 코드가 있어야 로그인됩니다.','Connect a standard TOTP app such as Google Authenticator, Microsoft Authenticator, or 1Password. Once enabled, login requires a one-time code after your email and password.','可连接 Google Authenticator、Microsoft Authenticator、1Password 等标准 TOTP 应用。启用后，输入邮箱和密码后还需一次性验证码。','Google Authenticator、Microsoft Authenticator、1Passwordなどの標準TOTPアプリを接続できます。有効化後はメールとパスワードに加えてワンタイムコードが必要です。','Conecta una aplicación TOTP como Google Authenticator, Microsoft Authenticator o 1Password. Al activarla, necesitarás un código de un solo uso tras el correo y la contraseña.','Kết nối ứng dụng TOTP như Google Authenticator, Microsoft Authenticator hoặc 1Password. Khi bật, đăng nhập cần mã dùng một lần sau email và mật khẩu.','เชื่อมแอป TOTP เช่น Google Authenticator, Microsoft Authenticator หรือ 1Password เมื่อเปิดใช้ ต้องกรอกรหัสครั้งเดียวหลังอีเมลและรหัสผ่าน'],
    ['인증 앱 OTP','Authenticator OTP','验证器 OTP','認証アプリOTP','OTP de autenticador','OTP ứng dụng xác thực','OTP จากแอปยืนยันตัวตน'],
    ['에이전트 연결은 그대로 유지됩니다.','Agent connections remain active.','智能体连接保持不变。','エージェント接続はそのまま維持されます。','Las conexiones de agentes siguen activas.','Kết nối tác nhân vẫn được duy trì.','การเชื่อมต่อเอเจนต์ยังคงอยู่'],
    ['OTP는 브라우저 로그인만 보호합니다. 기존 CLI·MCP 연결은 중단되지 않으며 에이전트 키와 연결 권한은 에이전트 연결 화면에서 별도로 철회할 수 있습니다.','OTP protects browser login only. Existing CLI and MCP connections continue; revoke agent keys and connection permissions separately on the Agent connections page.','OTP 仅保护浏览器登录。现有 CLI 和 MCP 连接不会中断；可在智能体连接页面单独撤销密钥和连接权限。','OTPが保護するのはブラウザログインだけです。既存のCLI・MCP接続は継続し、エージェントキーと接続権限は接続画面で個別に取り消せます。','OTP solo protege el inicio de sesión del navegador. Las conexiones CLI y MCP siguen activas; revoca sus permisos por separado en Conexiones de agentes.','OTP chỉ bảo vệ đăng nhập trình duyệt. Kết nối CLI và MCP hiện có vẫn hoạt động; thu hồi khóa và quyền riêng trong trang kết nối tác nhân.','OTP ปกป้องเฉพาะการเข้าสู่ระบบเบราว์เซอร์ การเชื่อมต่อ CLI และ MCP เดิมยังทำงาน ถอนคีย์และสิทธิ์ได้แยกในหน้าการเชื่อมต่อเอเจนต์'],
    ['접수된 기능 요청','Submitted feature requests','已提交的功能请求','受付済みの機能リクエスト','Solicitudes enviadas','Yêu cầu tính năng đã gửi','คำขอฟีเจอร์ที่ส่งแล้ว'],
    ['에이전트와 콘솔에서 남긴 요청의 진행 상태와 처리 결과입니다.','Progress and outcomes for requests submitted by agents and the console.','查看智能体和控制台提交请求的进度与处理结果。','エージェントとコンソールから送ったリクエストの進捗と処理結果です。','Progreso y resultados de las solicitudes enviadas por agentes y la consola.','Tiến độ và kết quả yêu cầu gửi từ tác nhân và bảng điều khiển.','ความคืบหน้าและผลลัพธ์ของคำขอจากเอเจนต์และคอนโซล'],
    ['더 나은 기억을 위한 아이디어가 있나요?','Have an idea for better memory?','有改善记忆功能的想法吗？','より良い記憶のアイデアはありますか？','¿Tienes una idea para mejorar la memoria?','Có ý tưởng cải thiện ký ức?','มีไอเดียเพื่อความทรงจำที่ดีขึ้นไหม'],
    ['에이전트에서 요청을 보내거나 콘솔에서 필요한 기능과 사용 사례를 남겨주세요.','Send a request from an agent or describe the feature and use case in the console.','从智能体发送请求，或在控制台描述所需功能与使用场景。','エージェントから送信するか、コンソールで必要な機能とユースケースを入力してください。','Envía una solicitud desde un agente o describe la función y el caso de uso en la consola.','Gửi yêu cầu từ tác nhân hoặc mô tả tính năng và trường hợp sử dụng trong bảng điều khiển.','ส่งคำขอจากเอเจนต์หรืออธิบายฟีเจอร์และกรณีใช้งานในคอนโซล'],
    ['검토 중','Reviewing','审核中','検討中','En revisión','Đang xem xét','กำลังตรวจสอบ'],
    ['계획됨','Planned','已计划','計画済み','Planificada','Đã lên kế hoạch','วางแผนแล้ว'],
    ['처리 중','In progress','处理中','対応中','En curso','Đang xử lý','กำลังดำเนินการ'],
    ['완료','Completed','已完成','完了','Completada','Hoàn thành','เสร็จแล้ว'],
    ['보류','Deferred','暂缓','保留','Aplazada','Tạm hoãn','เลื่อนออกไป'],
    ['각 코드는 한 번만 사용할 수 있습니다. 인증 앱을 사용할 수 없을 때 로그인 코드 대신 입력하세요. 이 화면을 닫으면 다시 볼 수 없습니다.','Each code can be used once. Use one instead of a login code when your authenticator is unavailable. You cannot view them again after closing this screen.','每个代码只能使用一次。无法使用验证器时，可代替登录验证码输入。关闭此页面后将无法再次查看。','各コードは1回だけ使えます。認証アプリを使えないときにログインコードの代わりに入力してください。この画面を閉じると再表示できません。','Cada código se usa una vez. Úsalo en lugar del código de inicio si no tienes el autenticador. No podrás verlos de nuevo tras cerrar esta pantalla.','Mỗi mã chỉ dùng một lần. Dùng thay mã đăng nhập khi không thể dùng ứng dụng xác thực. Đóng màn hình sẽ không xem lại được.','แต่ละรหัสใช้ได้ครั้งเดียว ใช้แทนรหัสเข้าสู่ระบบเมื่อแอปยืนยันตัวตนใช้ไม่ได้ ปิดหน้านี้แล้วจะดูอีกไม่ได้'],
    ['복구 코드 모두 복사','Copy all recovery codes','复制所有恢复代码','復旧コードをすべてコピー','Copiar todos los códigos','Sao chép mọi mã khôi phục','คัดลอกรหัสกู้คืนทั้งหมด'],
    ['인증 앱에서 QR 코드를 스캔하세요. 모바일에서는 아래 버튼으로 바로 열 수 있고, 열리지 않으면 설정 키를 직접 입력할 수 있습니다.','Scan the QR code with your authenticator. On mobile, use the button below; if it does not open, enter the setup key manually.','请使用验证器扫描二维码。移动端可使用下方按钮直接打开；若无法打开，请手动输入设置密钥。','認証アプリでQRコードを読み取ってください。モバイルでは下のボタンで開き、開けない場合は設定キーを直接入力できます。','Escanea el QR con tu autenticador. En móvil usa el botón; si no se abre, introduce la clave de configuración manualmente.','Quét mã QR bằng ứng dụng xác thực. Trên di động, dùng nút bên dưới; nếu không mở được, nhập khóa thiết lập thủ công.','สแกน QR ด้วยแอปยืนยันตัวตน บนมือถือใช้ปุ่มด้านล่าง หากเปิดไม่ได้ให้กรอกคีย์ตั้งค่าด้วยตนเอง'],
    ['인증 앱에서 열기','Open in authenticator','在验证器中打开','認証アプリで開く','Abrir en autenticador','Mở trong ứng dụng xác thực','เปิดในแอปยืนยันตัวตน'],
    ['수동 설정 키','Manual setup key','手动设置密钥','手動設定キー','Clave de configuración manual','Khóa thiết lập thủ công','คีย์ตั้งค่าด้วยตนเอง'],
    ['키 복사','Copy key','复制密钥','キーをコピー','Copiar clave','Sao chép khóa','คัดลอกคีย์'],
    ['인증 앱의 6자리 코드','Six-digit authenticator code','验证器六位代码','認証アプリの6桁コード','Código de seis dígitos','Mã sáu chữ số','รหัสหกหลักจากแอป'],
    ['설정은 10분 후 만료됩니다.','Setup expires in 10 minutes.','设置将在 10 分钟后过期。','設定は10分後に期限切れになります。','La configuración caduca en 10 minutos.','Thiết lập hết hạn sau 10 phút.','การตั้งค่าหมดอายุใน 10 นาที'],
    ['본인 확인을 위해 현재 비밀번호를 입력해주세요.','Enter your current password to verify your identity.','请输入当前密码以验证身份。','本人確認のため現在のパスワードを入力してください。','Introduce tu contraseña actual para verificar tu identidad.','Nhập mật khẩu hiện tại để xác minh danh tính.','กรอกรหัสผ่านปัจจุบันเพื่อยืนยันตัวตน'],
    ['현재 비밀번호','Current password','当前密码','現在のパスワード','Contraseña actual','Mật khẩu hiện tại','รหัสผ่านปัจจุบัน'],
    ['기존 복구 코드는 모두 폐기됩니다. 현재 비밀번호와 인증 앱 코드 또는 남아 있는 복구 코드를 입력하세요.','All existing recovery codes will be revoked. Enter your current password and an authenticator code or remaining recovery code.','所有现有恢复代码都将失效。请输入当前密码以及验证器代码或剩余恢复代码。','既存の復旧コードはすべて無効になります。現在のパスワードと認証アプリのコード、または残りの復旧コードを入力してください。','Se revocarán todos los códigos actuales. Introduce la contraseña y un código del autenticador o de recuperación.','Mọi mã khôi phục hiện có sẽ bị hủy. Nhập mật khẩu hiện tại và mã ứng dụng xác thực hoặc mã khôi phục còn lại.','รหัสกู้คืนเดิมทั้งหมดจะถูกยกเลิก กรอกรหัสผ่านปัจจุบันและรหัสจากแอปหรือรหัสกู้คืนที่เหลือ'],
    ['OTP 또는 복구 코드','OTP or recovery code','OTP 或恢复代码','OTPまたは復旧コード','OTP o código de recuperación','OTP hoặc mã khôi phục','OTP หรือรหัสกู้คืน'],
    ['해제하면 비밀번호만으로 로그인할 수 있습니다. 현재 비밀번호와 인증 앱 코드 또는 복구 코드를 입력하세요.','Disabling OTP allows password-only login. Enter your current password and authenticator or recovery code.','停用后仅凭密码即可登录。请输入当前密码以及验证器代码或恢复代码。','解除するとパスワードだけでログインできます。現在のパスワードと認証アプリのコードまたは復旧コードを入力してください。','Al desactivar OTP se podrá iniciar sesión solo con contraseña. Introduce la contraseña y el código del autenticador o recuperación.','Tắt OTP cho phép đăng nhập chỉ bằng mật khẩu. Nhập mật khẩu hiện tại và mã xác thực hoặc khôi phục.','เมื่อปิด OTP จะเข้าสู่ระบบด้วยรหัสผ่านอย่างเดียวได้ กรอกรหัสผ่านปัจจุบันและรหัสจากแอปหรือรหัสกู้คืน'],
    ['어떤 에이전트에 사용할 키인지 이름을 붙여주세요.','Name the agent that will use this key.','请为使用此密钥的智能体命名。','このキーを使うエージェントの名前を付けてください。','Pon un nombre al agente que usará esta clave.','Đặt tên tác nhân sẽ dùng khóa này.','ตั้งชื่อเอเจนต์ที่จะใช้คีย์นี้'],
    ['이 키에 Vault 비밀값 사용 권한 허용','Allow this key to use Vault secrets','允许此密钥使用 Vault 秘密','このキーにVault秘密値の利用を許可','Permitir que esta clave use secretos de Vault','Cho phép khóa này dùng bí mật Vault','อนุญาตให้คีย์นี้ใช้ความลับ Vault'],
    ['Vault 권한은 저장된 모든 비밀값을 실행 프로세스에 전달할 수 있는 민감한 권한입니다.','Vault access is sensitive: it can pass every stored secret to a process.','Vault 权限十分敏感，可将所有已保存秘密传递给进程。','Vault権限は保存済みのすべての秘密値をプロセスへ渡せる機密性の高い権限です。','El acceso a Vault es sensible: puede pasar todos los secretos guardados a un proceso.','Quyền Vault rất nhạy cảm: có thể chuyển mọi bí mật đã lưu cho tiến trình.','สิทธิ์ Vault มีความละเอียดอ่อน สามารถส่งความลับที่บันทึกทั้งหมดให้กระบวนการได้'],
    ['지금 한 번만 확인할 수 있어요. 에이전트에서 설치된 Skill 안의 Rust CLI를 절대 경로로 실행하고','You can view this only once. In the agent, run the Rust CLI inside the installed Skill by absolute path and save it through the hidden input of','只能查看一次。在智能体中，以绝对路径运行已安装 Skill 内的 Rust CLI，并通过以下命令的隐藏输入保存：','表示できるのは今だけです。エージェントでインストール済みSkill内のRust CLIを絶対パスで実行し、次の隠し入力で保存してください：','Solo puedes verlo una vez. En el agente, ejecuta por ruta absoluta el CLI de Rust del Skill y guárdalo mediante la entrada oculta de','Bạn chỉ xem được một lần. Trong tác nhân, chạy Rust CLI trong Skill bằng đường dẫn tuyệt đối và lưu qua đầu vào ẩn của','ดูได้เพียงครั้งเดียว ในเอเจนต์ให้เรียก Rust CLI ใน Skill ด้วยพาธแบบเต็มและบันทึกผ่านช่องซ่อนของ'],
    ['의 숨김 입력으로 저장하세요. 채팅이나 환경변수에 붙여넣지 마세요.','Do not paste it into chat or environment variables.','请勿粘贴到聊天或环境变量中。','チャットや環境変数には貼り付けないでください。','No la pegues en el chat ni en variables de entorno.','Không dán vào chat hoặc biến môi trường.','อย่าวางในแชตหรือตัวแปรสภาพแวดล้อม'],
    ['값은 전송 후 이 화면에 다시 표시되지 않습니다. 이름에는 영문자, 숫자, 점, 밑줄, 하이픈만 사용할 수 있습니다.','The value is not shown again after submission. Names may contain letters, numbers, dots, underscores, and hyphens.','提交后不会再次显示此值。名称只能包含英文字母、数字、点、下划线和连字符。','送信後、この値は再表示されません。名前には英字・数字・ピリオド・アンダースコア・ハイフンだけを使えます。','El valor no se mostrará tras enviarlo. El nombre admite letras, números, puntos, guiones bajos y guiones.','Giá trị không hiển thị lại sau khi gửi. Tên chỉ gồm chữ cái, số, dấu chấm, gạch dưới và gạch ngang.','ค่าจะไม่แสดงอีกหลังส่ง ชื่อใช้ได้เฉพาะตัวอักษร ตัวเลข จุด ขีดล่าง และขีดกลาง'],
    ['설명','Description','说明','説明','Descripción','Mô tả','คำอธิบาย'],
    ['선택한 항목은 이 MCP 연결이','This MCP connection can read the selected items in plaintext with','此 MCP 连接可使用以下工具读取所选条目的明文：','選択した項目は、このMCP接続が次のツールで原文を取得できます：','Esta conexión MCP puede leer los elementos seleccionados en texto mediante','Kết nối MCP này có thể đọc giá trị gốc của mục đã chọn bằng','การเชื่อมต่อ MCP นี้สามารถอ่านค่าจริงของรายการที่เลือกด้วย'],
    ['으로 원문을 읽을 수 있습니다. 조회된 값은 MCP 클라이언트와 모델 문맥·기록에 들어갈 수 있습니다. Vibe Memory 서버는 외부 API를 실행하지 않습니다.','Read values may enter the MCP client and model context or logs. The Vibe Memory server does not call external APIs.','读取的值可能进入 MCP 客户端、模型上下文或日志。Vibe Memory 服务器不会调用外部 API。','取得した値はMCPクライアントやモデルの文脈・ログに入る場合があります。Vibe Memoryサーバーは外部APIを実行しません。','Los valores leídos pueden entrar en el cliente MCP y en el contexto o registros del modelo. Vibe Memory no llama a API externas.','Giá trị đã đọc có thể vào ứng dụng MCP và ngữ cảnh hoặc nhật ký mô hình. Máy chủ Vibe Memory không gọi API bên ngoài.','ค่าที่อ่านอาจเข้าสู่ไคลเอนต์ MCP และบริบทหรือบันทึกของโมเดล เซิร์ฟเวอร์ Vibe Memory ไม่เรียก API ภายนอก'],
    ['기억할 내용','Content to remember','要记住的内容','記憶する内容','Contenido para recordar','Nội dung cần nhớ','เนื้อหาที่จะจำ'],
    ['종류','Type','类型','種類','Tipo','Loại','ประเภท'],
    ['사실','Fact','事实','事実','Dato','Sự kiện','ข้อเท็จจริง'],
    ['선호','Preference','偏好','好み','Preferencia','Sở thích','ความชอบ'],
    ['이벤트','Event','事件','イベント','Evento','Sự kiện','เหตุการณ์'],
    ['지침','Instruction','指令','指示','Instrucción','Chỉ dẫn','คำแนะนำ'],
    ['키워드를 쉼표로 구분해주세요. 입력한 키워드만 임베딩하며, 원문은 분석하지 않습니다.','Separate keywords with commas. Only those keywords are embedded; the original content is not analyzed.','请用逗号分隔关键词。仅嵌入输入的关键词，不分析原文。','キーワードをカンマで区切ってください。入力したキーワードだけを埋め込み、原文は分析しません。','Separa las palabras con comas. Solo se vectorizan esas palabras; no se analiza el texto original.','Phân tách từ khóa bằng dấu phẩy. Chỉ nhúng các từ khóa đó; không phân tích nội dung gốc.','คั่นคีย์เวิร์ดด้วยจุลภาค ระบบฝังเฉพาะคีย์เวิร์ดและไม่วิเคราะห์เนื้อหาต้นฉบับ'],
    ['원본 바이트만 저장합니다. 분석·키워드·문서 메타정보 등록은 연결된 에이전트가 수행합니다. 최대 100 MiB까지 업로드할 수 있습니다.','Only the original bytes are stored. The connected agent handles analysis, keywords, and document metadata. Maximum upload size is 100 MiB.','仅保存原始字节。分析、关键词和文档元数据由已连接智能体处理。最大上传 100 MiB。','原本のバイトだけを保存します。分析・キーワード・文書メタデータは接続エージェントが登録します。最大100 MiBです。','Solo se guardan los bytes originales. El agente gestiona análisis, palabras y metadatos. Tamaño máximo: 100 MiB.','Chỉ lưu byte gốc. Tác nhân kết nối xử lý phân tích, từ khóa và metadata. Tối đa 100 MiB.','เก็บเฉพาะไบต์ต้นฉบับ เอเจนต์ที่เชื่อมต่อจัดการการวิเคราะห์ คีย์เวิร์ด และเมทาดาทา อัปโหลดสูงสุด 100 MiB'],
    ['제목','Title','标题','タイトル','Título','Tiêu đề','ชื่อ'],
    ['상세 설명','Detailed description','详细说明','詳しい説明','Descripción detallada','Mô tả chi tiết','คำอธิบายโดยละเอียด'],
    ['처리','Process','处理','処理','Procesar','Xử lý','ดำเนินการ'],
    ['조건에 맞는 기능 요청이 없습니다.','No feature requests match these filters.','没有符合条件的功能请求。','条件に一致する機能リクエストはありません。','No hay solicitudes que coincidan con los filtros.','Không có yêu cầu phù hợp bộ lọc.','ไม่มีคำขอฟีเจอร์ที่ตรงเงื่อนไข'],
    ['조건에 맞는 사용자가 없습니다.','No users match these filters.','没有符合条件的用户。','条件に一致するユーザーはいません。','No hay usuarios que coincidan con los filtros.','Không có người dùng phù hợp bộ lọc.','ไม่มีผู้ใช้ที่ตรงเงื่อนไข'],
    ['관계','Relationships','关系','関係','Relaciones','Quan hệ','ความสัมพันธ์'],
    ['이름 · 설명','Name · Description','名称 · 说明','名前 · 説明','Nombre · Descripción','Tên · Mô tả','ชื่อ · คำอธิบาย'],
    ['먼저 Vault에 비밀값을 저장해주세요.','Save a secret in Vault first.','请先在 Vault 中保存秘密。','先にVaultへ秘密値を保存してください。','Guarda primero un secreto en Vault.','Hãy lưu bí mật trong Vault trước.','โปรดบันทึกความลับใน Vault ก่อน'],
    ['허용하지 않음','Not allowed','不允许','許可しない','No permitido','Không cho phép','ไม่อนุญาต'],
    ['기억 관계 그래프. 드래그하여 이동하고 휠로 확대할 수 있습니다.','Memory relationship graph. Drag to move and use the wheel to zoom.','记忆关系图谱。拖动以移动，滚轮可缩放。','記憶関係グラフ。ドラッグで移動し、ホイールで拡大できます。','Grafo de relaciones. Arrastra para mover y usa la rueda para ampliar.','Đồ thị quan hệ ký ức. Kéo để di chuyển và cuộn để thu phóng.','กราฟความสัมพันธ์ของความทรงจำ ลากเพื่อย้ายและใช้ล้อเพื่อซูม'],
    ['사용자는 Python 예제를 선호한다','The user prefers Python examples','用户偏好 Python 示例','ユーザーはPythonの例を好む','El usuario prefiere ejemplos en Python','Người dùng thích ví dụ Python','ผู้ใช้ชอบตัวอย่าง Python'],
    ['프로젝트','Project','项目','プロジェクト','Proyecto','Dự án','โปรเจกต์'],
    ['기억 공유','Memory sharing','记忆共享','記憶共有','Memoria compartida','Chia sẻ ký ức','แชร์ความทรงจำ'],
    ['그래프 DB','Graph database','图数据库','グラフDB','Base de datos de grafos','Cơ sở dữ liệu đồ thị','ฐานข้อมูลกราฟ'],
    ['에이전트가 분석한 프로젝트 개요','Project overview analyzed by the agent','智能体分析的项目概览','エージェントが分析したプロジェクト概要','Resumen del proyecto analizado por el agente','Tổng quan dự án do tác nhân phân tích','ภาพรวมโปรเจกต์ที่เอเจนต์วิเคราะห์'],
    ['기능 요청 전체 조회','View all feature requests','查看所有功能请求','全機能リクエストを表示','Ver todas las solicitudes','Xem mọi yêu cầu tính năng','ดูคำขอฟีเจอร์ทั้งหมด'],
    ['기능 요청 처리·수정','Process and edit feature requests','处理并编辑功能请求','機能リクエストの処理・編集','Procesar y editar solicitudes','Xử lý và sửa yêu cầu','ดำเนินการและแก้ไขคำขอฟีเจอร์'],
    ['연결된 에이전트가 없습니다. 콘솔에서 에이전트를 먼저 연결하세요.','No agents are connected. Connect an agent in the console first.','没有已连接的智能体。请先在控制台连接智能体。','接続済みエージェントがありません。先にコンソールで接続してください。','No hay agentes conectados. Conecta uno primero en la consola.','Chưa có tác nhân kết nối. Hãy kết nối trong bảng điều khiển trước.','ยังไม่มีเอเจนต์ที่เชื่อมต่อ โปรดเชื่อมต่อในคอนโซลก่อน']
  ];
  const guideSupplementRows = [
    ['01 · 연결 준비','01 · Prepare connection','01 · 连接准备','01 · 接続準備','01 · Preparar conexión','01 · Chuẩn bị kết nối','01 · เตรียมการเชื่อมต่อ'],
    ['02 · Skill 연결','02 · Connect Skill','02 · 连接 Skill','02 · Skill接続','02 · Conectar Skill','02 · Kết nối Skill','02 · เชื่อมต่อ Skill'],
    ['Agent Hook 자동화','Agent Hook automation','Agent Hook 自动化','Agent Hook自動化','Automatización de Hooks','Tự động hóa Agent Hook','ระบบอัตโนมัติ Agent Hook'],
    ['03 · 기억 저장과 검색','03 · Save and search memories','03 · 保存和搜索记忆','03 · 記憶の保存と検索','03 · Guardar y buscar memorias','03 · Lưu và tìm kiếm ký ức','03 · บันทึกและค้นหาความทรงจำ'],
    ['04 · 파일 업로드','04 · Upload files','04 · 上传文件','04 · ファイルアップロード','04 · Subir archivos','04 · Tải tệp lên','04 · อัปโหลดไฟล์'],
    ['05 · 엔티티와 관계','05 · Entities and relationships','05 · 实体与关系','05 · エンティティと関係','05 · Entidades y relaciones','05 · Thực thể và quan hệ','05 · เอนทิตีและความสัมพันธ์'],
    ['06 · 에이전트 메시지','06 · Agent messages','06 · 智能体消息','06 · エージェントメッセージ','06 · Mensajes entre agentes','06 · Tin nhắn tác nhân','06 · ข้อความเอเจนต์'],
    ['07 · 기능 요청','07 · Feature requests','07 · 功能请求','07 · 機能リクエスト','07 · Solicitudes de funciones','07 · Yêu cầu tính năng','07 · คำขอฟีเจอร์'],
    ['08 · API 참조','08 · API reference','08 · API 参考','08 · APIリファレンス','08 · Referencia API','08 · Tham chiếu API','08 · อ้างอิง API'],
    ['이해와 추론은 에이전트가, 데이터 관리는 Vibe Memory가 담당합니다.','Agents handle understanding and reasoning; Vibe Memory manages the data.','智能体负责理解和推理，Vibe Memory 负责数据管理。','理解と推論はエージェント、データ管理はVibe Memoryが担当します。','Los agentes comprenden y razonan; Vibe Memory gestiona los datos.','Tác nhân xử lý hiểu và suy luận; Vibe Memory quản lý dữ liệu.','เอเจนต์ทำความเข้าใจและอนุมาน ส่วน Vibe Memory จัดการข้อมูล'],
    ['자신의 서버 엔드포인트와 에이전트를 연결하는 방법을 안내합니다.','This guide explains how to connect your server endpoint and agents.','本指南介绍如何连接服务器端点和智能体。','自分のサーバーエンドポイントとエージェントを接続する方法を説明します。','Esta guía explica cómo conectar tu endpoint y tus agentes.','Hướng dẫn cách kết nối endpoint máy chủ và tác nhân.','คู่มือนี้อธิบายวิธีเชื่อมต่อ endpoint ของเซิร์ฟเวอร์และเอเจนต์'],
    ['01. 연결 준비','01. Prepare connection','01. 连接准备','01. 接続準備','01. Preparar conexión','01. Chuẩn bị kết nối','01. เตรียมการเชื่อมต่อ'],
    ['직접 서버를 실행하려면 아래 자체 호스팅 방법을 사용하세요.','To run your own server, use the self-hosting steps below.','如需运行自己的服务器，请使用下方自托管步骤。','自分でサーバーを動かす場合は、以下のセルフホスト手順を使ってください。','Para ejecutar tu servidor, sigue los pasos de autoalojamiento.','Để chạy máy chủ riêng, dùng các bước self-host bên dưới.','หากต้องการรันเซิร์ฟเวอร์เอง ให้ทำตามขั้นตอน self-host ด้านล่าง'],
    ['이미 Vibe Memory 서버가 실행 중이라면 서버 URL과 API 키를 준비하세요. 소스 프로젝트에서 처음 실행한다면 Python 3.12/3.13과 uv를 준비한 뒤 아래 명령을 실행합니다.','If a Vibe Memory server is already running, prepare its URL and API key. For a first run from source, install Python 3.12 or 3.13 and uv, then run the commands below.','若 Vibe Memory 服务器已运行，请准备服务器 URL 和 API 密钥。首次从源码运行时，请安装 Python 3.12/3.13 与 uv，然后执行下方命令。','Vibe Memoryサーバーがすでに動いている場合はURLとAPIキーを用意してください。ソースから初めて動かす場合はPython 3.12/3.13とuvを用意し、次のコマンドを実行します。','Si el servidor ya está activo, prepara su URL y clave API. Para ejecutarlo desde el código, instala Python 3.12/3.13 y uv, y ejecuta estos comandos.','Nếu máy chủ đã chạy, chuẩn bị URL và khóa API. Khi chạy từ mã nguồn lần đầu, cài Python 3.12/3.13 và uv rồi chạy lệnh dưới đây.','หากเซิร์ฟเวอร์ทำงานอยู่แล้ว ให้เตรียม URL และ API key หากรันจากซอร์สครั้งแรก ให้ติดตั้ง Python 3.12/3.13 และ uv แล้วรันคำสั่งด้านล่าง'],
    ['02. Skill 연결','02. Connect Skill','02. 连接 Skill','02. Skill接続','02. Conectar Skill','02. Kết nối Skill','02. เชื่อมต่อ Skill'],
    ['CLI 소스','CLI source','CLI 源码','CLIソース','Código fuente del CLI','Mã nguồn CLI','ซอร์ส CLI'],
    ['에이전트별 Hook 자동화','Hook automation by agent','按智能体配置 Hook 自动化','エージェント別Hook自動化','Automatización de Hooks por agente','Tự động hóa Hook theo tác nhân','ระบบ Hook อัตโนมัติแยกตามเอเจนต์'],
    ['먼저 현재 에이전트 도구를 확인하고 아래 분기 중 하나만 적용하세요. 도구마다 이벤트명·설정 위치·승인 방식이 다르므로 한 도구의 Hook을 다른 도구 설정으로 변환하지 않습니다. 기존 설정을 통째로 교체하지 말고 Vibe Memory 항목의 정확한 diff와 적용 범위를 검토한 뒤 병합하세요.','Identify the current agent tool and apply only its matching section below. Event names, settings locations, and approval flows differ by tool. Review the exact Vibe Memory diff and scope, then merge it without replacing existing settings wholesale.','先确认当前智能体工具，仅应用下方对应分支。各工具的事件名、设置位置和批准方式不同，不要互相转换 Hook。请检查 Vibe Memory 的准确差异与作用范围后合并，不要整体覆盖现有设置。','現在のエージェントツールを確認し、該当する分岐だけを適用してください。イベント名・設定場所・承認方法はツールごとに異なります。既存設定全体を置き換えず、Vibe Memory項目の差分と範囲を確認してマージします。','Identifica la herramienta actual y aplica solo su sección. Los eventos, ubicaciones y aprobaciones cambian según la herramienta. Revisa el diff y el alcance de Vibe Memory y combínalo sin sustituir toda la configuración.','Xác định công cụ tác nhân hiện tại và chỉ áp dụng phần tương ứng. Tên sự kiện, vị trí cài đặt và cách phê duyệt khác nhau. Kiểm tra diff cùng phạm vi Vibe Memory rồi hợp nhất, không thay toàn bộ cấu hình.','ตรวจสอบเครื่องมือเอเจนต์ปัจจุบันและใช้เฉพาะส่วนที่ตรงกัน ชื่อเหตุการณ์ ตำแหน่งตั้งค่า และการอนุมัติแตกต่างกัน ตรวจสอบ diff และขอบเขตของ Vibe Memory แล้วผสานโดยไม่แทนที่การตั้งค่าทั้งหมด'],
    ['Claude Code 2.1.275 이상에서 설치 범위를 검토하세요. 기존 수동 Hook과 플러그인을 동시에 켜면 이벤트가 두 번 실행되므로 하나만 사용합니다.','On Claude Code 2.1.275 or later, review the installation scope. Use either the existing manual Hook or the plugin, not both, to avoid duplicate events.','在 Claude Code 2.1.275 或更高版本中检查安装范围。现有手动 Hook 与插件同时启用会重复触发事件，请只使用一种。','Claude Code 2.1.275以降でインストール範囲を確認してください。既存の手動Hookとプラグインを同時に有効にすると二重実行されるため、片方だけを使います。','En Claude Code 2.1.275 o posterior, revisa el alcance. Usa el Hook manual o el plugin, no ambos, para evitar eventos duplicados.','Trên Claude Code 2.1.275 trở lên, kiểm tra phạm vi cài đặt. Chỉ dùng Hook thủ công hoặc plugin để tránh chạy sự kiện hai lần.','บน Claude Code 2.1.275 ขึ้นไป ให้ตรวจสอบขอบเขตการติดตั้ง ใช้ Hook แบบกำหนดเองหรือปลั๊กอินอย่างใดอย่างหนึ่งเพื่อไม่ให้เหตุการณ์ทำงานซ้ำ'],
    ['GPT·Claude 원격 MCP 연결','Remote MCP connection for GPT and Claude','GPT 与 Claude 远程 MCP 连接','GPT・ClaudeのリモートMCP接続','Conexión MCP remota para GPT y Claude','Kết nối MCP từ xa cho GPT và Claude','การเชื่อมต่อ MCP ระยะไกลสำหรับ GPT และ Claude'],
    ['ChatGPT Work에 Vibe Memory 설치','Install Vibe Memory in ChatGPT Work','在 ChatGPT Work 中安装 Vibe Memory','ChatGPT WorkにVibe Memoryをインストール','Instalar Vibe Memory en ChatGPT Work','Cài Vibe Memory trong ChatGPT Work','ติดตั้ง Vibe Memory ใน ChatGPT Work'],
    ['ChatGPT의 커스텀 MCP 서버 또는 Claude의 커스텀 커넥터에 아래 주소를 추가하세요.','Add the address below as a custom MCP server in ChatGPT or a custom connector in Claude.','将下方地址添加为 ChatGPT 的自定义 MCP 服务器或 Claude 的自定义连接器。','下のアドレスをChatGPTのカスタムMCPサーバー、またはClaudeのカスタムコネクタに追加してください。','Añade la dirección como servidor MCP personalizado en ChatGPT o conector personalizado en Claude.','Thêm địa chỉ bên dưới làm máy chủ MCP tùy chỉnh trong ChatGPT hoặc connector tùy chỉnh trong Claude.','เพิ่มที่อยู่ด้านล่างเป็นเซิร์ฟเวอร์ MCP แบบกำหนดเองใน ChatGPT หรือ connector แบบกำหนดเองใน Claude'],
    ['03. 기억 저장과 검색','03. Save and search memories','03. 保存和搜索记忆','03. 記憶の保存と検索','03. Guardar y buscar memorias','03. Lưu và tìm kiếm ký ức','03. บันทึกและค้นหาความทรงจำ'],
    ['에이전트가 원문에서 사실·선호와 키워드를 추출한 뒤 저장합니다. 아래 명령은 위에서 설정한 절대 CLI 경로를 사용하는 예시입니다.','The agent extracts facts, preferences, and keywords from the source, then saves them. The command below uses the absolute CLI path configured above.','智能体从原文提取事实、偏好与关键词后保存。下方命令使用上面配置的 CLI 绝对路径。','エージェントが原文から事実・好み・キーワードを抽出して保存します。次の例は上で設定したCLIの絶対パスを使います。','El agente extrae datos, preferencias y palabras del original y los guarda. El comando usa la ruta absoluta del CLI configurada arriba.','Tác nhân trích xuất sự kiện, sở thích và từ khóa từ nội dung gốc rồi lưu. Lệnh dưới dùng đường dẫn CLI tuyệt đối đã thiết lập.','เอเจนต์สกัดข้อเท็จจริง ความชอบ และคีย์เวิร์ดจากต้นฉบับแล้วบันทึก คำสั่งด้านล่างใช้พาธ CLI แบบเต็มที่ตั้งไว้'],
    ['검색도 질문을 그대로 보내지 않고 에이전트가 추출한 키워드를 보냅니다.','For search, the agent sends extracted keywords rather than the original question.','搜索时，智能体发送提取的关键词，而不是原始问题。','検索でも質問をそのまま送らず、エージェントが抽出したキーワードを送ります。','Para buscar, el agente envía las palabras extraídas, no la pregunta original.','Khi tìm kiếm, tác nhân gửi từ khóa đã trích xuất thay vì câu hỏi gốc.','การค้นหาจะส่งคีย์เวิร์ดที่เอเจนต์สกัด ไม่ส่งคำถามต้นฉบับ'],
    ['응답에는 기록 ID, 출처, 메타정보, 일치한 키워드와 점수가 포함됩니다. 에이전트는 ID로 원문과 관계를 조회한 뒤 근거를 선택하고 답변을 구성합니다. 앱은 원문·제목·요약을 임베딩하거나 RAG 컨텍스트를 조립하지 않습니다.','Responses include record IDs, sources, metadata, matched keywords, and scores. The agent retrieves source records and relationships by ID, selects evidence, and composes the answer. The app never embeds source text, titles, or summaries or assembles RAG context.','响应包含记录 ID、来源、元数据、匹配关键词与分数。智能体通过 ID 查询原文和关系，选择依据并生成回答。应用不会嵌入原文、标题或摘要，也不会组装 RAG 上下文。','応答には記録ID・出典・メタデータ・一致キーワード・スコアが含まれます。エージェントはIDで原文と関係を取得し、根拠を選んで回答を構成します。アプリは原文・タイトル・要約を埋め込まず、RAG文脈も組み立てません。','Las respuestas incluyen ID, fuente, metadatos, palabras coincidentes y puntuación. El agente recupera el original y las relaciones, elige evidencia y redacta la respuesta. La app no vectoriza textos, títulos ni resúmenes, ni monta contexto RAG.','Phản hồi gồm ID, nguồn, metadata, từ khóa khớp và điểm. Tác nhân truy xuất nội dung gốc cùng quan hệ, chọn bằng chứng và soạn câu trả lời. Ứng dụng không nhúng nội dung, tiêu đề, tóm tắt hay lắp ghép RAG.','การตอบกลับมี ID แหล่งที่มา เมทาดาทา คีย์เวิร์ดที่ตรง และคะแนน เอเจนต์ดึงต้นฉบับกับความสัมพันธ์ เลือกหลักฐาน และสร้างคำตอบ แอปไม่ฝังต้นฉบับ ชื่อเรื่อง หรือสรุป และไม่ประกอบบริบท RAG'],
    ['04. 파일은 바이트 스트림으로','04. Files as byte streams','04. 以字节流上传文件','04. ファイルはバイトストリームで','04. Archivos como flujo de bytes','04. Tệp dưới dạng byte stream','04. ไฟล์แบบ byte stream'],
    ['05. 엔티티와 관계 구성','05. Build entities and relationships','05. 构建实体与关系','05. エンティティと関係の構成','05. Crear entidades y relaciones','05. Xây dựng thực thể và quan hệ','05. สร้างเอนทิตีและความสัมพันธ์'],
    ['06. 에이전트끼리 메시지 보내기','06. Send messages between agents','06. 智能体间消息','06. エージェント間メッセージ','06. Enviar mensajes entre agentes','06. Gửi tin nhắn giữa tác nhân','06. ส่งข้อความระหว่างเอเจนต์'],
    ['각 API 키와 MCP 연결은 서버가 만든 고유 에이전트 ID를 가집니다. 같은 계정의 연결만 서로 찾고 메시지를 보낼 수 있으며, 꺼진 에이전트의 메시지는 PostgreSQL 수신함에 남아 다음 접속 때 전달됩니다.','Each API key and MCP connection has a unique server-issued agent ID. Only connections on the same account can discover and message one another. Messages for offline agents remain in the PostgreSQL inbox until the next connection.','每个 API 密钥和 MCP 连接都有服务器生成的唯一智能体 ID。只有同一账户的连接可互相发现并发送消息；离线智能体的消息会保留在 PostgreSQL 收件箱，待下次连接时投递。','各APIキーとMCP接続にはサーバー発行の固有エージェントIDがあります。同じアカウントの接続だけが互いを見つけてメッセージでき、停止中のエージェント宛てはPostgreSQL受信箱に残り、次回接続時に届きます。','Cada clave API y conexión MCP tiene un ID de agente único. Solo las conexiones de la misma cuenta pueden encontrarse y enviarse mensajes. Los mensajes de agentes desconectados quedan en PostgreSQL hasta la próxima conexión.','Mỗi khóa API và kết nối MCP có ID tác nhân riêng do máy chủ cấp. Chỉ kết nối cùng tài khoản mới tìm và nhắn cho nhau. Tin nhắn cho tác nhân ngoại tuyến nằm trong hộp thư PostgreSQL đến lần kết nối sau.','API key และการเชื่อมต่อ MCP แต่ละรายการมี ID เอเจนต์เฉพาะจากเซิร์ฟเวอร์ เฉพาะการเชื่อมต่อในบัญชีเดียวกันที่ค้นหาและส่งข้อความหากันได้ ข้อความของเอเจนต์ออฟไลน์จะอยู่ในกล่อง PostgreSQL จนเชื่อมต่อครั้งถัดไป'],
    ['07. 필요한 기능 요청하기','07. Request needed features','07. 请求所需功能','07. 必要な機能をリクエスト','07. Solicitar funciones necesarias','07. Yêu cầu tính năng cần thiết','07. ขอฟีเจอร์ที่ต้องการ'],
    ['에이전트가 서비스의 부족한 기능을 발견하면 필요한 기능과 사용 사례를 구성해 제출할 수 있습니다. 요청은 기억 검색과 분리해 보관하며 별도 임베딩을 수행하지 않습니다.','When an agent finds a missing capability, it can submit the needed feature and use case. Requests are stored separately from memory search and are not embedded.','当智能体发现缺少功能时，可提交所需功能与使用场景。请求与记忆搜索分开存储，不进行嵌入。','エージェントが不足機能を見つけたら、必要な機能とユースケースを構成して送信できます。リクエストは記憶検索と分けて保存し、埋め込みません。','Cuando un agente detecta una carencia, puede enviar la función y su caso de uso. Las solicitudes se guardan aparte de la memoria y no se vectorizan.','Khi tác nhân phát hiện thiếu tính năng, nó có thể gửi tính năng cần thiết và trường hợp sử dụng. Yêu cầu được lưu riêng, không nhúng.','เมื่อเอเจนต์พบฟังก์ชันที่ขาด สามารถส่งฟีเจอร์และกรณีใช้งาน คำขอเก็บแยกจากการค้นหาความทรงจำและไม่ถูกฝัง'],
    ['08. API 참조','08. API reference','08. API 参考','08. APIリファレンス','08. Referencia API','08. Tham chiếu API','08. อ้างอิง API'],
    ['기능','Purpose','功能','機能','Función','Chức năng','หน้าที่'],
    ['GPT·Claude용 Streamable HTTP MCP','Streamable HTTP MCP for GPT and Claude','用于 GPT 与 Claude 的 Streamable HTTP MCP','GPT・Claude用Streamable HTTP MCP','MCP HTTP Streamable para GPT y Claude','Streamable HTTP MCP cho GPT và Claude','Streamable HTTP MCP สำหรับ GPT และ Claude'],
    ['같은 계정의 연결된 에이전트 조회','List connected agents on the same account','查询同一账户的已连接智能体','同じアカウントの接続エージェントを取得','Listar agentes conectados de la misma cuenta','Liệt kê tác nhân cùng tài khoản','ดูเอเจนต์ที่เชื่อมต่อในบัญชีเดียวกัน'],
    ['메시지 전송·수신함·ACK·SSE','Message send, inbox, ACK, and SSE','消息发送、收件箱、ACK 与 SSE','メッセージ送信・受信箱・ACK・SSE','Envío, bandeja, ACK y SSE','Gửi tin, hộp thư, ACK và SSE','ส่งข้อความ กล่องรับ ACK และ SSE'],
    ['에이전트가 구성한 기억 저장','Save agent-composed memories','保存智能体构建的记忆','エージェントが構成した記憶を保存','Guardar memorias creadas por el agente','Lưu ký ức do tác nhân tạo','บันทึกความทรงจำที่เอเจนต์สร้าง'],
    ['에이전트가 식별한 엔티티 저장','Save agent-identified entities','保存智能体识别的实体','エージェントが識別したエンティティを保存','Guardar entidades identificadas','Lưu thực thể đã nhận diện','บันทึกเอนทิตีที่เอเจนต์ระบุ'],
    ['분석된 문서 메타정보 등록','Register analyzed document metadata','登记已分析的文档元数据','分析済み文書メタデータを登録','Registrar metadatos analizados','Đăng ký metadata tài liệu','ลงทะเบียนเมทาดาทาเอกสารที่วิเคราะห์แล้ว'],
    ['원본 byte stream 업로드','Upload original byte stream','上传原始字节流','原本バイトストリームをアップロード','Subir flujo de bytes original','Tải byte stream gốc','อัปโหลด byte stream ต้นฉบับ'],
    ['원본 다운로드·삭제','Download or delete original','下载或删除原文件','原本のダウンロード・削除','Descargar o eliminar original','Tải xuống hoặc xóa bản gốc','ดาวน์โหลดหรือลบต้นฉบับ'],
    ['기능 요청 접수·목록 조회','Submit and list feature requests','提交并列出功能请求','機能リクエストの受付・一覧','Enviar y listar solicitudes','Gửi và liệt kê yêu cầu','ส่งและดูรายการคำขอฟีเจอร์'],
    ['기능 요청 개별 조회','Get one feature request','查询单个功能请求','機能リクエストを個別取得','Obtener una solicitud','Lấy một yêu cầu','ดูคำขอฟีเจอร์หนึ่งรายการ'],
    ['요청 키워드만 임베딩·검색','Embed and search request keywords only','仅嵌入并搜索请求关键词','リクエストされたキーワードだけを埋め込み・検索','Vectorizar y buscar solo palabras solicitadas','Chỉ nhúng và tìm từ khóa yêu cầu','ฝังและค้นเฉพาะคีย์เวิร์ดที่ขอ'],
    ['원문·메타정보 조회·삭제','Get or delete source and metadata','查询或删除原文与元数据','原文・メタデータの取得・削除','Obtener o eliminar original y metadatos','Lấy hoặc xóa nội dung và metadata','ดูหรือลบต้นฉบับและเมทาดาทา'],
    ['키워드 인덱스 교체','Replace keyword index','替换关键词索引','キーワードインデックスを置換','Sustituir índice de palabras','Thay chỉ mục từ khóa','แทนที่ดัชนีคีย์เวิร์ด'],
    ['관계 저장·조회','Save and retrieve relationships','保存并查询关系','関係の保存・取得','Guardar y consultar relaciones','Lưu và truy xuất quan hệ','บันทึกและเรียกดูความสัมพันธ์'],
    ['관계 철회·복원과 버전 검사','Revoke or restore relationships and check versions','撤销或恢复关系并检查版本','関係の撤回・復元とバージョン検査','Revocar o restaurar relaciones y comprobar versiones','Thu hồi hoặc khôi phục quan hệ và kiểm tra phiên bản','ถอนหรือกู้คืนความสัมพันธ์และตรวจสอบเวอร์ชัน'],
    ['0–2홉 그래프 탐색','Traverse graph 0–2 hops','遍历 0–2 跳图谱','0–2ホップのグラフ探索','Recorrer grafo de 0 a 2 saltos','Duyệt đồ thị 0–2 bước','สำรวจกราฟ 0–2 hop'],
    ['Vibe Memory 홈으로','Vibe Memory home','返回 Vibe Memory 首页','Vibe Memoryホームへ','Inicio de Vibe Memory','Về trang chủ Vibe Memory','กลับหน้าแรก Vibe Memory']
  ];
  for (const row of [...extraRows, ...coreSupplementRows, ...guideSupplementRows]) {
    if (row.length !== supported.length) throw new Error(`Incomplete locale row: ${row[0]}`);
    translations.set(row[0], Object.fromEntries(supported.map((code, index) => [code, row[index]])));
  }
  const guideHtmlRows = [
    {
      selector:'.guide-note',
      en:'Start by <a href="/login">signing up or logging in</a>. GPT and Claude connect through remote MCP web approval; CLI and Skill agents start from the connection instructions in the console. The public API address is <code>https://vibememory.io</code>.',
      zh:'请先<a href="/login">注册或登录</a>。GPT 与 Claude 通过远程 MCP 网页授权连接；CLI 与 Skill 智能体从控制台的连接指引开始。公共 API 地址为 <code>https://vibememory.io</code>。',
      ja:'まず<a href="/login">登録・ログイン</a>してください。GPTとClaudeはリモートMCPのWeb承認、CLI・Skillエージェントはコンソールの接続案内から始めます。公開APIアドレスは<code>https://vibememory.io</code>です。',
      es:'Empieza por <a href="/login">registrarte o iniciar sesión</a>. GPT y Claude se conectan mediante aprobación web MCP; los agentes CLI y Skill siguen la guía de la consola. La API pública es <code>https://vibememory.io</code>.',
      vi:'Bắt đầu bằng cách <a href="/login">đăng ký hoặc đăng nhập</a>. GPT và Claude kết nối qua phê duyệt web MCP; tác nhân CLI và Skill bắt đầu từ hướng dẫn trong bảng điều khiển. API công khai là <code>https://vibememory.io</code>.',
      th:'เริ่มด้วยการ<a href="/login">สมัครหรือเข้าสู่ระบบ</a> GPT และ Claude เชื่อมต่อผ่านการอนุมัติ MCP บนเว็บ ส่วนเอเจนต์ CLI และ Skill เริ่มจากคำแนะนำในคอนโซล ที่อยู่ API สาธารณะคือ <code>https://vibememory.io</code>'
    },
    {
      selector:'#setup p:nth-of-type(1)',
      en:'<a href="/login">Log in to Vibe Memory</a>, then create a key under <strong>Agent API keys</strong> in the console. A key is shown only once and can be issued and revoked separately for each agent.',
      zh:'<a href="/login">登录 Vibe Memory</a>，然后在控制台的<strong>智能体 API 密钥</strong>中创建新密钥。密钥仅显示一次，可为每个智能体单独签发和撤销。',
      ja:'<a href="/login">Vibe Memoryにログイン</a>し、コンソールの<strong>エージェントAPIキー</strong>で新しいキーを作成します。キーの表示は一度だけで、エージェントごとに発行・取り消しできます。',
      es:'<a href="/login">Inicia sesión en Vibe Memory</a> y crea una clave en <strong>Claves API de agente</strong>. La clave se muestra una sola vez y puede emitirse y revocarse por agente.',
      vi:'<a href="/login">Đăng nhập Vibe Memory</a>, rồi tạo khóa trong <strong>Khóa API tác nhân</strong> ở bảng điều khiển. Khóa chỉ hiển thị một lần và có thể cấp hoặc thu hồi riêng cho từng tác nhân.',
      th:'<a href="/login">เข้าสู่ระบบ Vibe Memory</a> แล้วสร้างคีย์ใน <strong>API key ของเอเจนต์</strong> บนคอนโซล คีย์จะแสดงเพียงครั้งเดียวและออกหรือถอนได้แยกตามเอเจนต์'
    },
    {
      selector:'#setup p:nth-of-type(4)',
      en:'Put the generated JSON in the project <code>.env</code> file. Never commit real secrets to the repository.',
      zh:'将生成的 JSON 写入项目的 <code>.env</code> 文件。不要把真实秘密提交到仓库。',
      ja:'生成したJSONをプロジェクトの<code>.env</code>ファイルに設定します。実際の秘密をリポジトリへコミットしないでください。',
      es:'Guarda el JSON generado en el archivo <code>.env</code> del proyecto. No confirmes secretos reales en el repositorio.',
      vi:'Đặt JSON đã tạo vào tệp <code>.env</code> của dự án. Không commit bí mật thật vào kho mã.',
      th:'ใส่ JSON ที่สร้างในไฟล์ <code>.env</code> ของโปรเจกต์ อย่า commit ความลับจริงลง repository'
    },
    {
      selector:'#setup p:nth-of-type(5)',
      en:'The local default is <code>http://127.0.0.1:8080</code>. View the API schema and request forms at <code>/docs</code>. Remote connections must use HTTPS. The server currently targets personal and small-scale single-process deployments.',
      zh:'本地默认地址为 <code>http://127.0.0.1:8080</code>。可在 <code>/docs</code> 查看 API 架构与请求表单。远程连接须使用 HTTPS。当前服务器适用于个人和小规模单进程部署。',
      ja:'ローカル既定アドレスは<code>http://127.0.0.1:8080</code>です。<code>/docs</code>でAPIスキーマとリクエストフォームを確認できます。リモート接続にはHTTPSを使います。現在は個人・小規模向けの単一プロセス構成です。',
      es:'La dirección local es <code>http://127.0.0.1:8080</code>. Consulta el esquema y los formularios en <code>/docs</code>. Las conexiones remotas requieren HTTPS. El servidor está pensado para despliegues personales o pequeños de un solo proceso.',
      vi:'Địa chỉ local mặc định là <code>http://127.0.0.1:8080</code>. Xem schema API và biểu mẫu tại <code>/docs</code>. Kết nối từ xa phải dùng HTTPS. Máy chủ hiện phù hợp triển khai cá nhân hoặc quy mô nhỏ một tiến trình.',
      th:'ที่อยู่ local เริ่มต้นคือ <code>http://127.0.0.1:8080</code> ดู schema API และแบบฟอร์มได้ที่ <code>/docs</code> การเชื่อมต่อระยะไกลต้องใช้ HTTPS เซิร์ฟเวอร์เหมาะกับการใช้งานส่วนบุคคลหรือขนาดเล็กแบบโปรเซสเดียว'
    },
    {
      selector:'#skill p:nth-of-type(1)',
      en:'Paste <strong>Copy install/update prompt</strong> from the console into the agent conversation. It replaces an outdated Skill with the latest ZIP, guides web approval, and makes relevant recall and important context checkpoints the default without repeated requests. A global <code>vibe-memory</code> command is not required.',
      zh:'将控制台的<strong>复制安装/更新提示词</strong>粘贴到智能体对话中。提示词会用最新 ZIP 替换旧 Skill、引导网页授权，并默认主动检索相关记忆与保存重要上下文检查点，无需反复提醒。不需要全局安装 <code>vibe-memory</code> 命令。',
      ja:'コンソールの<strong>インストール・更新プロンプトをコピー</strong>をエージェントの会話へ貼り付けます。古いSkillを最新ZIPに置き換え、Web承認を案内し、関連記憶の取得と重要文脈のチェックポイントを既定動作にします。グローバルな<code>vibe-memory</code>コマンドは不要です。',
      es:'Pega <strong>Copiar prompt de instalación/actualización</strong> en la conversación del agente. Sustituye un Skill antiguo, guía la aprobación web y activa por defecto el recuerdo relevante y los checkpoints de contexto. No hace falta instalar globalmente <code>vibe-memory</code>.',
      vi:'Dán <strong>Sao chép lời nhắc cài đặt/cập nhật</strong> từ bảng điều khiển vào cuộc trò chuyện. Lời nhắc thay Skill cũ bằng ZIP mới, hướng dẫn phê duyệt web và mặc định truy xuất ký ức cùng checkpoint ngữ cảnh. Không cần cài lệnh <code>vibe-memory</code> toàn cục.',
      th:'วาง <strong>คัดลอกพรอมต์ติดตั้ง/อัปเดต</strong> จากคอนโซลในบทสนทนาของเอเจนต์ พรอมต์จะแทน Skill เก่าด้วย ZIP ล่าสุด แนะนำการอนุมัติบนเว็บ และให้การเรียกคืนกับ checkpoint บริบทเป็นค่าเริ่มต้น ไม่ต้องติดตั้งคำสั่ง <code>vibe-memory</code> แบบ global'
    },
    {
      selector:'#skill p:nth-of-type(3)',
      en:'For manual installation, extract the ZIP as a <code>vibe-memory</code> folder inside the agent skill directory. Use the <strong>absolute path</strong> of the folder containing the loaded <code>SKILL.md</code>; do not run it relative to the current project.',
      zh:'手动安装时，将 ZIP 解压为智能体 skill 目录中的 <code>vibe-memory</code> 文件夹。请使用包含已加载 <code>SKILL.md</code> 的文件夹<strong>绝对路径</strong>，不要相对当前项目执行。',
      ja:'手動インストールではZIPをエージェントのskillディレクトリ内の<code>vibe-memory</code>フォルダへ展開します。読み込まれた<code>SKILL.md</code>があるフォルダの<strong>絶対パス</strong>を使い、現在のプロジェクトからの相対パスで実行しないでください。',
      es:'Para instalar manualmente, extrae el ZIP como carpeta <code>vibe-memory</code> en el directorio de skills. Usa la <strong>ruta absoluta</strong> de la carpeta que contiene el <code>SKILL.md</code> cargado; no la ejecutes relativa al proyecto.',
      vi:'Khi cài thủ công, giải nén ZIP thành thư mục <code>vibe-memory</code> trong thư mục skill. Dùng <strong>đường dẫn tuyệt đối</strong> đến thư mục chứa <code>SKILL.md</code> đã nạp; không chạy tương đối theo dự án hiện tại.',
      th:'เมื่อติดตั้งเอง ให้แตก ZIP เป็นโฟลเดอร์ <code>vibe-memory</code> ในไดเรกทอรี skill ของเอเจนต์ ใช้ <strong>พาธแบบเต็ม</strong> ของโฟลเดอร์ที่มี <code>SKILL.md</code> ที่โหลดแล้ว และอย่ารันโดยอิงโปรเจกต์ปัจจุบัน'
    },
    {
      selector:'#skill p:nth-of-type(4)',
      en:'On Windows PowerShell, put the same absolute path in <code>$VmSkillDir</code>, run <code>py (Join-Path $VmSkillDir "scripts\\memory.py") sync</code>, then use <code>$VmCli = Join-Path $VmSkillDir "bin\\vibe-memory.exe"</code>. When sync updates the Skill, read the new <code>SKILL.md</code> again.',
      zh:'在 Windows PowerShell 中，将相同绝对路径写入 <code>$VmSkillDir</code>，运行 <code>py (Join-Path $VmSkillDir "scripts\\memory.py") sync</code>，再使用 <code>$VmCli = Join-Path $VmSkillDir "bin\\vibe-memory.exe"</code>。sync 更新 Skill 后，请重新读取新的 <code>SKILL.md</code>。',
      ja:'Windows PowerShellでは同じ絶対パスを<code>$VmSkillDir</code>に設定し、<code>py (Join-Path $VmSkillDir "scripts\\memory.py") sync</code>を実行してから<code>$VmCli = Join-Path $VmSkillDir "bin\\vibe-memory.exe"</code>を使います。syncでSkillが更新されたら、新しい<code>SKILL.md</code>を再度読みます。',
      es:'En PowerShell, asigna la ruta absoluta a <code>$VmSkillDir</code>, ejecuta <code>py (Join-Path $VmSkillDir "scripts\\memory.py") sync</code> y usa <code>$VmCli = Join-Path $VmSkillDir "bin\\vibe-memory.exe"</code>. Si sync actualiza el Skill, vuelve a leer <code>SKILL.md</code>.',
      vi:'Trên PowerShell, đặt đường dẫn tuyệt đối vào <code>$VmSkillDir</code>, chạy <code>py (Join-Path $VmSkillDir "scripts\\memory.py") sync</code>, rồi dùng <code>$VmCli = Join-Path $VmSkillDir "bin\\vibe-memory.exe"</code>. Khi sync cập nhật Skill, hãy đọc lại <code>SKILL.md</code> mới.',
      th:'ใน PowerShell ให้ใส่พาธแบบเต็มใน <code>$VmSkillDir</code> รัน <code>py (Join-Path $VmSkillDir "scripts\\memory.py") sync</code> แล้วใช้ <code>$VmCli = Join-Path $VmSkillDir "bin\\vibe-memory.exe"</code> เมื่อ sync อัปเดต Skill ให้อ่าน <code>SKILL.md</code> ใหม่อีกครั้ง'
    },
    {
      selector:'#skill p:nth-of-type(5)',
      en:'Open the link, log in on the web, verify the code and agent name, then select <strong>Approve connection</strong>. If Vault access was requested, its separate checkbox is selected by default and can be cleared. The CLI reports the actual granted permissions. No API key copy or terminal entry is needed. Approval lasts five minutes by default and can be set with <code>--approval-timeout 60..900</code>. An already connected agent can run <code>login --vault-access</code> to approve Vault access without a new key. The agent then checks the latest Rust CLI and Skill before work. Self-hosted instances use the Skill manifest served by that instance.',
      zh:'打开链接并在网页登录，核对代码与智能体名称后选择<strong>批准连接</strong>。若请求 Vault 权限，独立复选框默认选中且可取消；CLI 会明确显示实际授权。无需复制 API 密钥或在终端输入。批准默认有效五分钟，可用 <code>--approval-timeout 60..900</code> 调整。已连接智能体可运行 <code>login --vault-access</code>，无需新密钥即可批准 Vault 权限。之后智能体会在工作前检查最新 Rust CLI 与 Skill。自托管实例使用该实例提供的 Skill 清单。',
      ja:'リンクを開いてWebでログインし、コードとエージェント名を確認して<strong>接続を承認</strong>します。Vaultを要求した場合は別のチェックが既定で選択され、解除できます。CLIには実際の許可が表示されます。APIキーのコピーや端末入力は不要です。承認は既定5分で、<code>--approval-timeout 60..900</code>で変更できます。接続済みエージェントは<code>login --vault-access</code>で新しいキーなしにVault権限だけを承認できます。その後、作業前に最新Rust CLIとSkillを確認します。セルフホストではそのサーバーのSkillマニフェストを使います。',
      es:'Abre el enlace, inicia sesión, verifica el código y el agente, y pulsa <strong>Aprobar conexión</strong>. Si se solicita Vault, su casilla separada viene marcada y puede desmarcarse. El CLI muestra los permisos reales. No necesitas copiar claves ni escribirlas en la terminal. La aprobación dura cinco minutos y se ajusta con <code>--approval-timeout 60..900</code>. Un agente conectado puede ejecutar <code>login --vault-access</code> para aprobar Vault sin una clave nueva. Después comprueba el CLI de Rust y el Skill antes de trabajar. El autoalojamiento usa el manifiesto servido por esa instancia.',
      vi:'Mở liên kết, đăng nhập trên web, kiểm tra mã và tên tác nhân rồi chọn <strong>Phê duyệt kết nối</strong>. Nếu yêu cầu Vault, ô riêng được chọn mặc định và có thể bỏ chọn. CLI hiển thị đúng quyền đã cấp. Không cần sao chép API key hay nhập vào terminal. Phê duyệt mặc định kéo dài năm phút và chỉnh bằng <code>--approval-timeout 60..900</code>. Tác nhân đã kết nối có thể chạy <code>login --vault-access</code> để duyệt Vault mà không cần khóa mới. Sau đó tác nhân kiểm tra Rust CLI và Skill mới nhất trước khi làm việc. Self-host dùng manifest do máy chủ đó cung cấp.',
      th:'เปิดลิงก์ เข้าสู่ระบบบนเว็บ ตรวจสอบรหัสและชื่อเอเจนต์ แล้วเลือก <strong>อนุมัติการเชื่อมต่อ</strong> หากขอสิทธิ์ Vault ช่องแยกจะถูกเลือกไว้และยกเลิกได้ CLI จะแสดงสิทธิ์ที่ได้รับจริง ไม่ต้องคัดลอก API key หรือกรอกในเทอร์มินัล การอนุมัติมีอายุห้านาทีและปรับด้วย <code>--approval-timeout 60..900</code> เอเจนต์ที่เชื่อมแล้วรัน <code>login --vault-access</code> เพื่ออนุมัติ Vault โดยไม่สร้างคีย์ใหม่ จากนั้นเอเจนต์ตรวจ Rust CLI และ Skill ล่าสุดก่อนทำงาน Self-host ใช้ manifest ที่เซิร์ฟเวอร์นั้นให้บริการ'
    },
    {
      selector:'#skill p:nth-of-type(6)',
      en:'Manual API key connection is for advanced setup. Server-side <code>MEMORY_API_KEYS</code> is a JSON object; client-side <code>MEMORY_API_KEY</code> is one key string.',
      zh:'手动 API 密钥连接用于高级设置。服务器端 <code>MEMORY_API_KEYS</code> 是 JSON 对象；客户端 <code>MEMORY_API_KEY</code> 是单个密钥字符串。',
      ja:'手動APIキー接続は高度な設定用です。サーバー側の<code>MEMORY_API_KEYS</code>はJSONオブジェクト、クライアント側の<code>MEMORY_API_KEY</code>は単一のキー文字列です。',
      es:'La conexión manual con clave API es avanzada. <code>MEMORY_API_KEYS</code> del servidor es un objeto JSON; <code>MEMORY_API_KEY</code> del cliente es una sola cadena.',
      vi:'Kết nối API key thủ công dành cho thiết lập nâng cao. <code>MEMORY_API_KEYS</code> phía máy chủ là đối tượng JSON; <code>MEMORY_API_KEY</code> phía máy khách là một chuỗi khóa.',
      th:'การเชื่อมต่อด้วย API key แบบกำหนดเองมีไว้สำหรับการตั้งค่าขั้นสูง <code>MEMORY_API_KEYS</code> ฝั่งเซิร์ฟเวอร์เป็นออบเจ็กต์ JSON ส่วน <code>MEMORY_API_KEY</code> ฝั่งไคลเอนต์เป็นสตริงคีย์เดียว'
    },
    {
      selector:'#skill p:nth-of-type(7)',
      en:'Agent keys issued from your console share the same user memory. Data belonging to different user IDs stays isolated. Data commands run in the native Rust CLI and return token-efficient compact JSON by default. The small Python compatibility bootstrap only downloads the platform binary and verifies its SHA-256 checksum.',
      zh:'控制台签发的智能体密钥共享同一用户记忆。不同用户 ID 的数据相互隔离。数据命令由原生 Rust CLI 执行，默认返回节省 token 的紧凑 JSON。小型 Python 兼容引导程序只负责下载平台二进制文件并验证 SHA-256。',
      ja:'コンソールで発行したエージェントキーは同じユーザー記憶を共有します。異なるユーザーIDのデータは分離されます。データコマンドはネイティブRust CLIで実行され、既定でトークン効率の良いcompact JSONを返します。小さなPython互換ブートストラップはプラットフォーム用バイナリの取得とSHA-256検証だけを行います。',
      es:'Las claves emitidas en tu consola comparten la misma memoria de usuario. Los datos de distintos usuarios permanecen aislados. Los comandos se ejecutan en el CLI nativo de Rust y devuelven JSON compacto para ahorrar tokens. El pequeño bootstrap de Python solo descarga el binario y verifica SHA-256.',
      vi:'Các khóa tác nhân cấp từ bảng điều khiển dùng chung ký ức người dùng. Dữ liệu của ID người dùng khác được tách biệt. Lệnh dữ liệu chạy trong Rust CLI native và mặc định trả compact JSON tiết kiệm token. Bootstrap Python nhỏ chỉ tải binary cho nền tảng và xác minh SHA-256.',
      th:'คีย์เอเจนต์ที่ออกจากคอนโซลแชร์ความทรงจำผู้ใช้เดียวกัน ข้อมูลของ user ID ต่างกันจะแยกกัน คำสั่งข้อมูลทำงานใน Rust CLI แบบ native และคืน compact JSON ที่ประหยัด token โดยค่าเริ่มต้น bootstrap Python ขนาดเล็กมีหน้าที่ดาวน์โหลดไบนารีของแพลตฟอร์มและตรวจ SHA-256 เท่านั้น'
    },
    {
      selector:'#agent-hooks p:nth-of-type(1)',
      en:'Hooks send only session identifiers and the working folder to the Vibe Memory CLI. Locally, the CLI reads the project name, branch, abbreviated commit, and clean or dirty state—not file contents. Checkpoint guidance states that uncommitted work cannot be recovered from Git. Conversation text, model responses, tool output, environment variables, and Vault values are never sent. Failures and timeouts do not block the agent, and SSE is not required. Current support is maintained from the same data in the landing-page <a href="/#agent-support">agent support matrix</a> and the repository <a href="https://github.com/vibememory/vibememory/blob/main/docs/agent-support.md" target="_blank" rel="noopener">support document</a>.',
      zh:'Hook 仅向 Vibe Memory CLI 传递会话标识与工作目录。CLI 在本地只读取项目名、分支、缩写提交以及 clean/dirty 状态，不读取文件内容。检查点提示会注明未提交内容无法从 Git 恢复。对话原文、模型响应、工具输出、环境变量与 Vault 值都不会发送。失败和超时不会阻塞智能体，也不需要 SSE。最新支持状态由落地页的<a href="/#agent-support">智能体支持表</a>与仓库<a href="https://github.com/vibememory/vibememory/blob/main/docs/agent-support.md" target="_blank" rel="noopener">支持文档</a>共享同一数据维护。',
      ja:'HookがVibe Memory CLIへ渡すのはセッション識別情報と作業フォルダだけです。CLIはローカルでプロジェクト名・ブランチ・短縮コミット・clean/dirty状態だけを確認し、ファイル内容は読みません。チェックポイント案内には未コミット内容をGitから復元できない境界を含めます。会話本文、モデル応答、ツール出力、環境変数、Vault値は送信しません。失敗やタイムアウトはエージェントを止めず、SSEも不要です。対応状況はランディングの<a href="/#agent-support">エージェント対応表</a>とリポジトリの<a href="https://github.com/vibememory/vibememory/blob/main/docs/agent-support.md" target="_blank" rel="noopener">対応文書</a>で同じデータから管理します。',
      es:'Los Hooks envían al CLI solo identificadores de sesión y la carpeta de trabajo. El CLI lee localmente proyecto, rama, commit abreviado y estado clean/dirty, nunca el contenido. La guía avisa que Git no recupera trabajo no confirmado. No se envían conversación, respuestas, salida de herramientas, variables ni valores Vault. Fallos y tiempos de espera no bloquean al agente; no hace falta SSE. El estado se mantiene con los mismos datos en la <a href="/#agent-support">matriz de agentes</a> y el <a href="https://github.com/vibememory/vibememory/blob/main/docs/agent-support.md" target="_blank" rel="noopener">documento de soporte</a>.',
      vi:'Hook chỉ gửi mã phiên và thư mục làm việc cho Vibe Memory CLI. CLI chỉ đọc cục bộ tên dự án, nhánh, commit rút gọn và trạng thái clean/dirty, không đọc nội dung tệp. Hướng dẫn checkpoint nêu rõ thay đổi chưa commit không thể khôi phục từ Git. Nội dung hội thoại, phản hồi mô hình, output công cụ, biến môi trường và giá trị Vault không được gửi. Lỗi hoặc timeout không chặn tác nhân và không cần SSE. Trạng thái hỗ trợ dùng chung dữ liệu giữa <a href="/#agent-support">bảng hỗ trợ tác nhân</a> và <a href="https://github.com/vibememory/vibememory/blob/main/docs/agent-support.md" target="_blank" rel="noopener">tài liệu hỗ trợ</a>.',
      th:'Hook ส่งเฉพาะตัวระบุเซสชันและโฟลเดอร์ทำงานให้ Vibe Memory CLI โดย CLI อ่านชื่อโปรเจกต์ branch commit แบบย่อ และสถานะ clean/dirty ในเครื่อง ไม่อ่านเนื้อหาไฟล์ คำแนะนำ checkpoint ระบุว่างานที่ยังไม่ commit กู้จาก Git ไม่ได้ ข้อความสนทนา คำตอบโมเดล ผลลัพธ์เครื่องมือ ตัวแปรสภาพแวดล้อม และค่า Vault จะไม่ถูกส่ง ความล้มเหลวหรือ timeout ไม่ขวางเอเจนต์และไม่ต้องใช้ SSE สถานะรองรับใช้ข้อมูลเดียวกันใน<a href="/#agent-support">ตารางรองรับเอเจนต์</a>และ<a href="https://github.com/vibememory/vibememory/blob/main/docs/agent-support.md" target="_blank" rel="noopener">เอกสารรองรับ</a>'
    },
    {
      selector:'#agent-hooks p:nth-of-type(4)',
      en:'Merge <code>agent-adapters/codex/hooks.json</code> into user-level <code>~/.codex/hooks.json</code> or project-level <code>.codex/hooks.json</code>. Review and trust the definitions in Codex <code>/hooks</code>. Command hooks do not run in Work Cloud without local execution.',
      zh:'将 <code>agent-adapters/codex/hooks.json</code> 合并到用户级 <code>~/.codex/hooks.json</code> 或项目级 <code>.codex/hooks.json</code>。在 Codex <code>/hooks</code> 中检查并信任这些定义。没有本地执行的 Work Cloud 不会运行 command hook。',
      ja:'<code>agent-adapters/codex/hooks.json</code>をユーザー範囲の<code>~/.codex/hooks.json</code>またはプロジェクト範囲の<code>.codex/hooks.json</code>へマージします。Codexの<code>/hooks</code>で定義を確認し、信頼してください。ローカル実行のないWork Cloudではcommand hookは動きません。',
      es:'Combina <code>agent-adapters/codex/hooks.json</code> con <code>~/.codex/hooks.json</code> o <code>.codex/hooks.json</code>. Revisa y confía en las definiciones desde <code>/hooks</code>. Los command hooks no se ejecutan en Work Cloud sin ejecución local.',
      vi:'Hợp nhất <code>agent-adapters/codex/hooks.json</code> vào <code>~/.codex/hooks.json</code> cấp người dùng hoặc <code>.codex/hooks.json</code> cấp dự án. Kiểm tra và tin cậy định nghĩa trong Codex <code>/hooks</code>. Command hook không chạy trên Work Cloud nếu không có thực thi local.',
      th:'ผสาน <code>agent-adapters/codex/hooks.json</code> เข้ากับ <code>~/.codex/hooks.json</code> ระดับผู้ใช้หรือ <code>.codex/hooks.json</code> ระดับโปรเจกต์ ตรวจสอบและเชื่อถือคำจำกัดความใน Codex <code>/hooks</code> command hook ไม่ทำงานใน Work Cloud ที่ไม่มีการรันในเครื่อง'
    },
    {
      selector:'#agent-hooks p:nth-of-type(5)',
      en:'Place <code>agent-adapters/cursor/vibe_memory_hook.py</code> at a reviewed absolute path and merge the three entries from <code>hooks.example.json</code> into user-level <code>~/.cursor/hooks.json</code> or project-level <code>.cursor/hooks.json</code>. Replace <code>/ABSOLUTE/PATH</code> first; on Windows use <code>py</code> instead of <code>python3</code>. Verify execution in <strong>Customize → Hooks</strong> and the Hooks output channel, and keep <code>loop_limit: 1</code> for <code>stop</code>.',
      zh:'将 <code>agent-adapters/cursor/vibe_memory_hook.py</code> 放在已审核的绝对路径，并把 <code>hooks.example.json</code> 的三项合并到用户级 <code>~/.cursor/hooks.json</code> 或项目级 <code>.cursor/hooks.json</code>。先替换 <code>/ABSOLUTE/PATH</code>；Windows 使用 <code>py</code> 而非 <code>python3</code>。在 <strong>Customize → Hooks</strong> 与 Hooks 输出频道确认执行，并保留 <code>stop</code> 的 <code>loop_limit: 1</code>。',
      ja:'<code>agent-adapters/cursor/vibe_memory_hook.py</code>を確認済みの絶対パスに置き、<code>hooks.example.json</code>の3項目を<code>~/.cursor/hooks.json</code>または<code>.cursor/hooks.json</code>へマージします。先に<code>/ABSOLUTE/PATH</code>を置き換え、Windowsでは<code>python3</code>の代わりに<code>py</code>を使います。<strong>Customize → Hooks</strong>とHooks出力で実行を確認し、<code>stop</code>の<code>loop_limit: 1</code>を維持してください。',
      es:'Coloca <code>agent-adapters/cursor/vibe_memory_hook.py</code> en una ruta absoluta revisada y combina las tres entradas de <code>hooks.example.json</code> con <code>~/.cursor/hooks.json</code> o <code>.cursor/hooks.json</code>. Sustituye <code>/ABSOLUTE/PATH</code>; en Windows usa <code>py</code>. Verifica en <strong>Customize → Hooks</strong> y mantén <code>loop_limit: 1</code> en <code>stop</code>.',
      vi:'Đặt <code>agent-adapters/cursor/vibe_memory_hook.py</code> tại đường dẫn tuyệt đối đã kiểm tra và hợp nhất ba mục từ <code>hooks.example.json</code> vào <code>~/.cursor/hooks.json</code> hoặc <code>.cursor/hooks.json</code>. Thay <code>/ABSOLUTE/PATH</code> trước; trên Windows dùng <code>py</code>. Kiểm tra trong <strong>Customize → Hooks</strong> và giữ <code>loop_limit: 1</code> cho <code>stop</code>.',
      th:'วาง <code>agent-adapters/cursor/vibe_memory_hook.py</code> ที่พาธแบบเต็มที่ตรวจสอบแล้ว และผสานสามรายการจาก <code>hooks.example.json</code> ลงใน <code>~/.cursor/hooks.json</code> หรือ <code>.cursor/hooks.json</code> เปลี่ยน <code>/ABSOLUTE/PATH</code> ก่อน และใช้ <code>py</code> บน Windows ตรวจสอบใน <strong>Customize → Hooks</strong> และคง <code>loop_limit: 1</code> สำหรับ <code>stop</code>'
    },
    {
      selector:'#agent-hooks p:nth-of-type(6)',
      en:'On Muse Code 1.3.0 or later, merge the three groups from <code>agent-adapters/muse/hooks.json</code> into project-level <code>.muse/hooks.json</code> or the top-level <code>hooks</code> in <code>~/.config/muse/settings.json</code>. Project Hooks run after workspace trust. Muse has no separate <code>muse hooks</code> command; open a new session and verify that all three load without warnings in startup diagnostics.',
      zh:'在 Muse Code 1.3.0 或更高版本中，将 <code>agent-adapters/muse/hooks.json</code> 的三组配置合并到项目级 <code>.muse/hooks.json</code>，或 <code>~/.config/muse/settings.json</code> 顶层的 <code>hooks</code>。项目 Hook 会在信任工作区后运行。Muse 没有独立的 <code>muse hooks</code> 命令；修改后请新开会话，并在启动诊断中确认三个 Hook 均无警告加载。',
      ja:'Muse Code 1.3.0以降で<code>agent-adapters/muse/hooks.json</code>の3グループを、プロジェクトの<code>.muse/hooks.json</code>または<code>~/.config/muse/settings.json</code>最上位の<code>hooks</code>へマージします。プロジェクトHookはworkspace trust後に動きます。Museに<code>muse hooks</code>コマンドはないため、新しいセッションを開き、起動診断で3つが警告なく読み込まれることを確認します。',
      es:'En Muse Code 1.3.0 o posterior, combina los tres grupos de <code>agent-adapters/muse/hooks.json</code> con <code>.muse/hooks.json</code> o con <code>hooks</code> en <code>~/.config/muse/settings.json</code>. Los Hooks de proyecto se ejecutan tras confiar en el workspace. No existe <code>muse hooks</code>; abre una sesión nueva y comprueba los tres en el diagnóstico inicial.',
      vi:'Trên Muse Code 1.3.0 trở lên, hợp nhất ba nhóm từ <code>agent-adapters/muse/hooks.json</code> vào <code>.muse/hooks.json</code> hoặc <code>hooks</code> cấp cao nhất trong <code>~/.config/muse/settings.json</code>. Hook dự án chạy sau khi tin cậy workspace. Muse không có lệnh <code>muse hooks</code>; mở phiên mới và kiểm tra cả ba được nạp không cảnh báo.',
      th:'บน Muse Code 1.3.0 ขึ้นไป ให้ผสานสามกลุ่มจาก <code>agent-adapters/muse/hooks.json</code> ลงใน <code>.muse/hooks.json</code> หรือ <code>hooks</code> ระดับบนสุดใน <code>~/.config/muse/settings.json</code> Hook ของโปรเจกต์ทำงานหลัง workspace trust Muse ไม่มีคำสั่ง <code>muse hooks</code> ให้เปิดเซสชันใหม่และตรวจว่าทั้งสามโหลดโดยไม่มีคำเตือน'
    },
    {
      selector:'#agent-hooks p:nth-of-type(7)',
      en:'Merge the four entries from <code>agent-adapters/hermes/config.example.yaml</code> into the active profile and set the adapter absolute path. Keep the first-run approval prompt and check status with <code>hermes hooks doctor</code>. Optionally limit project roots with <code>VIBE_MEMORY_PROJECT_ROOTS</code>.',
      zh:'将 <code>agent-adapters/hermes/config.example.yaml</code> 的四项合并到当前配置，并设置适配器绝对路径。保留首次运行批准界面，用 <code>hermes hooks doctor</code> 检查状态。可用 <code>VIBE_MEMORY_PROJECT_ROOTS</code> 限制项目根目录。',
      ja:'<code>agent-adapters/hermes/config.example.yaml</code>の4項目を有効プロファイルへマージし、アダプターの絶対パスを設定します。初回実行の承認画面を維持し、<code>hermes hooks doctor</code>で状態を確認します。必要なら<code>VIBE_MEMORY_PROJECT_ROOTS</code>でプロジェクトルートを制限します。',
      es:'Combina las cuatro entradas de <code>agent-adapters/hermes/config.example.yaml</code> con el perfil activo y define la ruta absoluta. Conserva la aprobación inicial y revisa con <code>hermes hooks doctor</code>. Limita raíces con <code>VIBE_MEMORY_PROJECT_ROOTS</code> si hace falta.',
      vi:'Hợp nhất bốn mục từ <code>agent-adapters/hermes/config.example.yaml</code> vào profile hiện tại và đặt đường dẫn tuyệt đối của adapter. Giữ màn hình phê duyệt lần đầu và kiểm tra bằng <code>hermes hooks doctor</code>. Có thể giới hạn thư mục dự án bằng <code>VIBE_MEMORY_PROJECT_ROOTS</code>.',
      th:'ผสานสี่รายการจาก <code>agent-adapters/hermes/config.example.yaml</code> ในโปรไฟล์ที่ใช้งานและตั้งพาธแบบเต็มของอะแดปเตอร์ คงหน้าจออนุมัติครั้งแรกและตรวจด้วย <code>hermes hooks doctor</code> จำกัดรากโปรเจกต์ได้ด้วย <code>VIBE_MEMORY_PROJECT_ROOTS</code>'
    },
    {
      selector:'#agent-hooks p:nth-of-type(8)',
      en:'<code>--accept-capabilities</code> approves that the reviewed local plugin registers Hooks. Then explicitly allow <code>allowConversationAccess</code> and <code>allowPromptInjection</code> for the plugin in <code>openclaw.json</code>, and restrict scope with <code>projectRoots</code>. See the <a href="https://github.com/vibememory/vibememory/blob/main/docs/agent-hooks.md" target="_blank" rel="noopener">Agent lifecycle hooks guide</a> for update, removal, and recovery.',
      zh:'<code>--accept-capabilities</code> 表示批准已审核的本地插件注册 Hook。随后在 <code>openclaw.json</code> 中明确允许该插件的 <code>allowConversationAccess</code> 与 <code>allowPromptInjection</code>，并用 <code>projectRoots</code> 限制范围。更新、删除与恢复请参阅<a href="https://github.com/vibememory/vibememory/blob/main/docs/agent-hooks.md" target="_blank" rel="noopener">Agent lifecycle hooks 指南</a>。',
      ja:'<code>--accept-capabilities</code>は確認済みローカルプラグインがHookを登録することを承認します。続いて<code>openclaw.json</code>で<code>allowConversationAccess</code>と<code>allowPromptInjection</code>を明示的に許可し、<code>projectRoots</code>で範囲を制限します。更新・削除・復旧は<a href="https://github.com/vibememory/vibememory/blob/main/docs/agent-hooks.md" target="_blank" rel="noopener">Agent lifecycle hooksガイド</a>を参照してください。',
      es:'<code>--accept-capabilities</code> aprueba que el plugin local revisado registre Hooks. Después permite explícitamente <code>allowConversationAccess</code> y <code>allowPromptInjection</code> en <code>openclaw.json</code> y limita con <code>projectRoots</code>. Consulta la <a href="https://github.com/vibememory/vibememory/blob/main/docs/agent-hooks.md" target="_blank" rel="noopener">guía de lifecycle hooks</a>.',
      vi:'<code>--accept-capabilities</code> xác nhận plugin local đã kiểm tra được đăng ký Hook. Sau đó cho phép rõ <code>allowConversationAccess</code> và <code>allowPromptInjection</code> trong <code>openclaw.json</code>, giới hạn bằng <code>projectRoots</code>. Xem <a href="https://github.com/vibememory/vibememory/blob/main/docs/agent-hooks.md" target="_blank" rel="noopener">hướng dẫn lifecycle hooks</a>.',
      th:'<code>--accept-capabilities</code> อนุมัติให้ปลั๊กอิน local ที่ตรวจสอบแล้วลงทะเบียน Hook จากนั้นอนุญาต <code>allowConversationAccess</code> และ <code>allowPromptInjection</code> อย่างชัดเจนใน <code>openclaw.json</code> และจำกัดขอบเขตด้วย <code>projectRoots</code> ดู<a href="https://github.com/vibememory/vibememory/blob/main/docs/agent-hooks.md" target="_blank" rel="noopener">คู่มือ lifecycle hooks</a>'
    },
    {
      selector:'#mcp p:nth-of-type(3)',
      en:'Connecting redirects you to Vibe Memory login and permission approval. Never paste API keys or passwords into chat. The flow uses OAuth 2.1, dynamic client registration, and PKCE; revoke it anytime from <strong>Agent connections</strong> in the console.',
      zh:'连接后会自动跳转到 Vibe Memory 登录与权限批准页面。不要把 API 密钥或密码粘贴到聊天中。流程使用 OAuth 2.1、动态客户端注册与 PKCE；可随时在控制台的<strong>智能体连接</strong>中撤销。',
      ja:'接続するとVibe Memoryのログインと権限承認へ自動で移動します。APIキーやパスワードをチャットへ貼り付けないでください。OAuth 2.1、動的クライアント登録、PKCEを使い、コンソールの<strong>エージェント接続</strong>からいつでも取り消せます。',
      es:'Al conectar irás al inicio de sesión y aprobación de Vibe Memory. No pegues claves ni contraseñas en el chat. Se usan OAuth 2.1, registro dinámico y PKCE; revoca desde <strong>Conexiones de agentes</strong>.',
      vi:'Khi kết nối, bạn được chuyển đến đăng nhập và phê duyệt Vibe Memory. Không dán API key hoặc mật khẩu vào chat. Luồng dùng OAuth 2.1, đăng ký client động và PKCE; có thể thu hồi trong <strong>Kết nối tác nhân</strong>.',
      th:'เมื่อเชื่อมต่อ ระบบจะพาไปยังการเข้าสู่ระบบและอนุมัติสิทธิ์ Vibe Memory อย่าวาง API key หรือรหัสผ่านในแชต กระบวนการใช้ OAuth 2.1 การลงทะเบียนไคลเอนต์แบบไดนามิก และ PKCE ถอนสิทธิ์ได้ใน <strong>การเชื่อมต่อเอเจนต์</strong>'
    },
    {
      selector:'#mcp p:nth-of-type(4)',
      en:'In ChatGPT Plugins, enter the address under <strong>Add custom MCP server</strong>. In Claude, use <strong>Customize → Connectors → Add custom connector</strong>. The same address can be used as <code>server_url</code> in the OpenAI Responses API.',
      zh:'在 ChatGPT Plugins 的 <strong>Add custom MCP server</strong> 中输入地址。Claude 使用 <strong>Customize → Connectors → Add custom connector</strong>。OpenAI Responses API 的 <code>server_url</code> 也可使用同一地址。',
      ja:'ChatGPTのPluginsでは<strong>Add custom MCP server</strong>にアドレスを入力します。Claudeでは<strong>Customize → Connectors → Add custom connector</strong>を使います。OpenAI Responses APIの<code>server_url</code>にも同じアドレスを指定できます。',
      es:'En Plugins de ChatGPT, introduce la dirección en <strong>Add custom MCP server</strong>. En Claude, usa <strong>Customize → Connectors → Add custom connector</strong>. La misma dirección sirve como <code>server_url</code> en Responses API.',
      vi:'Trong ChatGPT Plugins, nhập địa chỉ ở <strong>Add custom MCP server</strong>. Trong Claude, dùng <strong>Customize → Connectors → Add custom connector</strong>. Cùng địa chỉ dùng được làm <code>server_url</code> trong Responses API.',
      th:'ใน ChatGPT Plugins ให้กรอกที่อยู่ใน <strong>Add custom MCP server</strong> ใน Claude ใช้ <strong>Customize → Connectors → Add custom connector</strong> ที่อยู่เดียวกันใช้เป็น <code>server_url</code> ใน Responses API ได้'
    },
    {
      selector:'#mcp p:nth-of-type(5)',
      en:'MCP provides memory search, read and write; entity, document metadata, and relationship creation; same-account agent messaging; change events; and feature requests. Original files still use byte-stream upload, and Vault is not exposed through MCP. For self-hosting, append <code>/mcp</code> to your HTTPS server address.',
      zh:'MCP 提供记忆搜索、读取与保存；实体、文档元数据与关系构建；同账户智能体消息；变更事件与功能请求。原文件仍使用字节流上传，Vault 不会通过 MCP 暴露。自托管时，在 HTTPS 服务器地址后加 <code>/mcp</code>。',
      ja:'MCPは記憶の検索・取得・保存、エンティティ・文書メタデータ・関係の作成、同一アカウントのエージェント間メッセージ、変更イベント、機能リクエストを提供します。原本ファイルは従来どおりバイトストリームでアップロードし、VaultはMCPに公開しません。セルフホストではHTTPSアドレスに<code>/mcp</code>を付けます。',
      es:'MCP ofrece búsqueda, lectura y guardado de memoria; entidades, metadatos y relaciones; mensajes entre agentes; eventos y solicitudes. Los originales se suben como bytes y Vault no se expone por MCP. En autoalojamiento, añade <code>/mcp</code> a tu servidor HTTPS.',
      vi:'MCP cung cấp tìm, đọc và lưu ký ức; tạo thực thể, metadata tài liệu và quan hệ; nhắn tin giữa tác nhân cùng tài khoản; sự kiện thay đổi và yêu cầu tính năng. Tệp gốc vẫn tải dạng byte stream và Vault không lộ qua MCP. Self-host thêm <code>/mcp</code> vào địa chỉ HTTPS.',
      th:'MCP รองรับค้นหา อ่าน และบันทึกความทรงจำ สร้างเอนทิตี เมทาดาทาเอกสาร และความสัมพันธ์ ส่งข้อความระหว่างเอเจนต์บัญชีเดียวกัน เหตุการณ์เปลี่ยนแปลง และคำขอฟีเจอร์ ไฟล์ต้นฉบับยังอัปโหลดแบบ byte stream และไม่เปิด Vault ผ่าน MCP สำหรับ self-host ให้ต่อ <code>/mcp</code> ท้ายที่อยู่ HTTPS'
    },
    {
      selector:'#remember p:nth-of-type(4)',
      en:'Provide 1–32 keywords, each 1–100 characters. Whitespace and case duplicates are normalized. Sending only source text without keywords, or sending <code>query</code> to search, returns 422.',
      zh:'提供 1–32 个关键词，每个 1–100 个字符。系统会规范空白并去除大小写重复。仅发送原文而不含关键词，或搜索时发送 <code>query</code>，会返回 422。',
      ja:'キーワードは1～32個、各1～100文字です。空白と大文字小文字の重複を正規化します。キーワードなしで原文だけを送る、または検索に<code>query</code>を送ると422を返します。',
      es:'Envía de 1 a 32 palabras, de 1 a 100 caracteres. Se normalizan espacios y duplicados por mayúsculas. Enviar solo texto sin palabras o usar <code>query</code> devuelve 422.',
      vi:'Gửi 1–32 từ khóa, mỗi từ 1–100 ký tự. Khoảng trắng và trùng lặp hoa thường được chuẩn hóa. Chỉ gửi nội dung gốc không có từ khóa hoặc gửi <code>query</code> khi tìm sẽ trả 422.',
      th:'ส่งคีย์เวิร์ด 1–32 รายการ รายการละ 1–100 ตัวอักษร ระบบปรับช่องว่างและรายการซ้ำต่างตัวพิมพ์ การส่งเฉพาะต้นฉบับโดยไม่มีคีย์เวิร์ดหรือส่ง <code>query</code> เพื่อค้นหาจะได้ 422'
    },
    {
      selector:'#files p:nth-of-type(1)',
      en:'Send the original file as an <code>application/octet-stream</code> request body, not multipart form data. The app stores it unchanged and does not parse it.',
      zh:'原文件应作为 <code>application/octet-stream</code> 请求正文发送，而非 multipart form。应用不会解析文件，只按原样保存。',
      ja:'原本ファイルはmultipart formではなく<code>application/octet-stream</code>のリクエスト本文で送信します。アプリは解析せず、そのまま保存します。',
      es:'Envía el archivo original en el cuerpo <code>application/octet-stream</code>, no como multipart. La app no lo analiza y lo guarda sin cambios.',
      vi:'Gửi tệp gốc trong request body <code>application/octet-stream</code>, không dùng multipart form. Ứng dụng không phân tích và lưu nguyên trạng.',
      th:'ส่งไฟล์ต้นฉบับใน request body แบบ <code>application/octet-stream</code> ไม่ใช่ multipart form แอปไม่แยกวิเคราะห์และเก็บไฟล์ตามเดิม'
    },
    {
      selector:'#files p:nth-of-type(2)',
      en:'The agent reads the file and analyzes its metadata, then builds JSON that links the upload response ID as <code>file_id</code>.',
      zh:'智能体读取文件并分析元数据，然后构建 JSON，将上传响应的 ID 作为 <code>file_id</code> 关联。',
      ja:'エージェントがファイルを読み、メタデータを分析して、アップロード応答のIDを<code>file_id</code>として関連付けるJSONを作ります。',
      es:'El agente lee el archivo, analiza sus metadatos y crea un JSON que enlaza el ID de subida como <code>file_id</code>.',
      vi:'Tác nhân đọc tệp, phân tích metadata rồi tạo JSON liên kết ID của phản hồi tải lên dưới dạng <code>file_id</code>.',
      th:'เอเจนต์อ่านไฟล์ วิเคราะห์เมทาดาทา แล้วสร้าง JSON ที่เชื่อม ID จากการอัปโหลดเป็น <code>file_id</code>'
    },
    {
      selector:'#files p:nth-of-type(3)',
      en:'<code>from-json document</code> passes a prepared object to the CLI; the agent does not build API paths or authentication headers. The app does not analyze the original. If the original is stored elsewhere, omit <code>file_id</code> and use a <code>source</code> reference. The default upload limit is 100 MiB. Download originals with <code>GET /v1/files/{id}</code>; deleting a file referenced by a document returns 409.',
      zh:'<code>from-json document</code> 将准备好的对象交给 CLI；智能体无需自行构建 API 路径或认证头。应用不会分析原文件。若原文件存于外部，可省略 <code>file_id</code> 并使用 <code>source</code> 引用。默认上传上限为 100 MiB。使用 <code>GET /v1/files/{id}</code> 下载原文件；删除仍被文档引用的文件会返回 409。',
      ja:'<code>from-json document</code>は準備済みオブジェクトをCLIへ渡し、エージェントはAPIパスや認証ヘッダーを組み立てません。アプリは原本を分析しません。外部保存なら<code>file_id</code>を省略して<code>source</code>参照を使えます。既定上限は100 MiBです。<code>GET /v1/files/{id}</code>でダウンロードし、文書が参照中のファイル削除は409です。',
      es:'<code>from-json document</code> pasa el objeto preparado al CLI; el agente no construye rutas ni cabeceras. La app no analiza el original. Si se guarda fuera, omite <code>file_id</code> y usa <code>source</code>. El límite es 100 MiB. Descarga con <code>GET /v1/files/{id}</code>; eliminar un archivo referenciado devuelve 409.',
      vi:'<code>from-json document</code> chuyển đối tượng đã chuẩn bị cho CLI; tác nhân không tự tạo đường dẫn API hay header xác thực. Ứng dụng không phân tích bản gốc. Nếu lưu bên ngoài, bỏ <code>file_id</code> và dùng tham chiếu <code>source</code>. Giới hạn mặc định 100 MiB. Tải bằng <code>GET /v1/files/{id}</code>; xóa tệp đang được tài liệu tham chiếu trả 409.',
      th:'<code>from-json document</code> ส่งออบเจ็กต์ที่เตรียมให้ CLI เอเจนต์ไม่ต้องสร้างพาธ API หรือ header ยืนยันตัวตน แอปไม่วิเคราะห์ต้นฉบับ หากเก็บภายนอกให้ตัด <code>file_id</code> และใช้ <code>source</code> ขีดจำกัดเริ่มต้น 100 MiB ดาวน์โหลดด้วย <code>GET /v1/files/{id}</code> การลบไฟล์ที่เอกสารอ้างอยู่จะได้ 409'
    },
    {
      selector:'#graph p:nth-of-type(1)',
      en:'The agent first searches existing entities to decide whether the target is the same. For a new entity, it prepares <code>name</code>, <code>entity_type</code>, <code>keywords</code>, optional <code>description</code> and <code>metadata</code>, and registers it with <code>POST /v1/entities</code>.',
      zh:'智能体先搜索现有实体以判断是否为同一对象。新实体需准备 <code>name</code>、<code>entity_type</code>、<code>keywords</code>，以及可选的 <code>description</code> 与 <code>metadata</code>，再通过 <code>POST /v1/entities</code> 登记。',
      ja:'エージェントはまず既存エンティティを検索して同じ対象か判断します。新規なら<code>name</code>、<code>entity_type</code>、<code>keywords</code>、任意の<code>description</code>・<code>metadata</code>を構成し、<code>POST /v1/entities</code>で登録します。',
      es:'El agente busca primero entidades existentes para decidir si es el mismo objeto. Para una nueva prepara <code>name</code>, <code>entity_type</code>, <code>keywords</code> y opcionalmente <code>description</code> y <code>metadata</code>, y la registra con <code>POST /v1/entities</code>.',
      vi:'Tác nhân tìm thực thể hiện có trước để xác định cùng đối tượng hay không. Với thực thể mới, chuẩn bị <code>name</code>, <code>entity_type</code>, <code>keywords</code>, tùy chọn <code>description</code> và <code>metadata</code>, rồi đăng ký bằng <code>POST /v1/entities</code>.',
      th:'เอเจนต์ค้นหาเอนทิตีเดิมก่อนเพื่อตัดสินว่าเป็นสิ่งเดียวกันหรือไม่ เอนทิตีใหม่ต้องเตรียม <code>name</code> <code>entity_type</code> <code>keywords</code> และ <code>description</code> กับ <code>metadata</code> แบบเลือกได้ แล้วลงทะเบียนด้วย <code>POST /v1/entities</code>'
    },
    {
      selector:'#graph p:nth-of-type(2)',
      en:'Relationships use uppercase identifiers chosen by the agent, such as <code>WORKS_ON</code>, <code>PREFERS</code>, or <code>MENTIONED_IN</code>; <code>KEYWORD_OF</code> and <code>CHUNK_OF</code> are reserved. For important claims, pin the selected record <code>record_id</code>, <code>version</code>, <code>content_hash</code>, UTC <code>observed_at</code>, and selected location in <code>evidence</code>. Review scope is <code>selected</code>, <code>partial</code>, or <code>unknown</code>—never infer a full review automatically. If needed, save a short input manifest record and link it through <code>input_manifest_id</code>. <code>evidence_status</code> compares the original coordinates with current version, hash, lifecycle state, and current/changed/unavailable status. Prefer archiving because permanent deletion cannot restore old source text. Never store source prompts, private reasoning, or secrets in a manifest. The app validates ownership and format and stores the relationship; it does not infer it.',
      zh:'关系使用智能体选择的大写标识符，例如 <code>WORKS_ON</code>、<code>PREFERS</code> 或 <code>MENTIONED_IN</code>；<code>KEYWORD_OF</code> 与 <code>CHUNK_OF</code> 为保留项。重要主张应在 <code>evidence</code> 中固定所选记录的 <code>record_id</code>、<code>version</code>、<code>content_hash</code>、UTC <code>observed_at</code> 与选中位置。审查范围只能是 <code>selected</code>、<code>partial</code> 或 <code>unknown</code>，不要自动推断为完整审查。必要时保存简短输入清单记录并通过 <code>input_manifest_id</code> 关联。<code>evidence_status</code> 会比较原坐标与当前版本、哈希、生命周期状态以及 current/changed/unavailable。永久删除无法恢复旧原文，通常应优先归档。不要把原始提示词、私有推理或秘密写入清单。应用只验证所有权与格式并保存关系，不会推断关系。',
      ja:'関係にはエージェントが選ぶ大文字識別子を使います。例は<code>WORKS_ON</code>、<code>PREFERS</code>、<code>MENTIONED_IN</code>で、<code>KEYWORD_OF</code>と<code>CHUNK_OF</code>は予約済みです。重要な主張は選択した記録の<code>record_id</code>、<code>version</code>、<code>content_hash</code>、UTCの<code>observed_at</code>、選択位置を<code>evidence</code>へ固定します。確認範囲は<code>selected</code>、<code>partial</code>、<code>unknown</code>のいずれかで、完全確認を自動推論しません。必要なら短い入力マニフェスト記録を保存し、<code>input_manifest_id</code>で関連付けます。<code>evidence_status</code>は当時の座標と現在のバージョン・ハッシュ・状態、current/changed/unavailableを比較します。完全削除では過去原文を戻せないため、通常は保管を優先します。原文プロンプト・内部推論・秘密値はマニフェストへ入れません。アプリは所有権と形式を検証して保存するだけで、関係を推論しません。',
      es:'Las relaciones usan identificadores en mayúsculas elegidos por el agente, como <code>WORKS_ON</code>, <code>PREFERS</code> o <code>MENTIONED_IN</code>; <code>KEYWORD_OF</code> y <code>CHUNK_OF</code> están reservados. Para afirmaciones importantes, fija <code>record_id</code>, <code>version</code>, <code>content_hash</code>, <code>observed_at</code> UTC y la ubicación en <code>evidence</code>. El alcance es <code>selected</code>, <code>partial</code> o <code>unknown</code>; no se infiere una revisión completa. Si hace falta, guarda un manifiesto breve y enlázalo con <code>input_manifest_id</code>. <code>evidence_status</code> compara coordenadas, versión, hash, ciclo de vida y current/changed/unavailable. Prefiere archivar porque el borrado permanente no recupera el original. No guardes prompts, razonamiento privado ni secretos. La app valida propiedad y formato y guarda la relación; no la infiere.',
      vi:'Quan hệ dùng định danh chữ hoa do tác nhân chọn như <code>WORKS_ON</code>, <code>PREFERS</code> hoặc <code>MENTIONED_IN</code>; <code>KEYWORD_OF</code> và <code>CHUNK_OF</code> được dành riêng. Với claim quan trọng, ghim <code>record_id</code>, <code>version</code>, <code>content_hash</code>, <code>observed_at</code> UTC và vị trí đã chọn trong <code>evidence</code>. Phạm vi xem xét là <code>selected</code>, <code>partial</code> hoặc <code>unknown</code>, không tự suy ra đã xem toàn bộ. Khi cần, lưu bản ghi manifest ngắn và liên kết bằng <code>input_manifest_id</code>. <code>evidence_status</code> so sánh tọa độ ban đầu với phiên bản, hash, trạng thái vòng đời và current/changed/unavailable hiện tại. Nên lưu trữ thay vì xóa vĩnh viễn vì không thể khôi phục nội dung cũ. Không đưa prompt gốc, suy luận riêng hay bí mật vào manifest. Ứng dụng chỉ xác minh quyền sở hữu, định dạng và lưu quan hệ, không suy luận quan hệ.',
      th:'ความสัมพันธ์ใช้ตัวระบุอักษรใหญ่ที่เอเจนต์เลือก เช่น <code>WORKS_ON</code> <code>PREFERS</code> หรือ <code>MENTIONED_IN</code> ส่วน <code>KEYWORD_OF</code> และ <code>CHUNK_OF</code> สงวนไว้ สำหรับ claim สำคัญ ให้ตรึง <code>record_id</code> <code>version</code> <code>content_hash</code> <code>observed_at</code> แบบ UTC และตำแหน่งที่เลือกใน <code>evidence</code> ขอบเขตการตรวจคือ <code>selected</code> <code>partial</code> หรือ <code>unknown</code> และไม่อนุมานว่าอ่านครบ หากจำเป็นให้บันทึก input manifest แบบสั้นแล้วเชื่อมด้วย <code>input_manifest_id</code> <code>evidence_status</code> เปรียบเทียบพิกัดเดิมกับเวอร์ชัน hash สถานะวงจรชีวิต และ current/changed/unavailable ปัจจุบัน ควร archive เพราะการลบถาวรกู้ต้นฉบับเก่าไม่ได้ ห้ามใส่พรอมต์ต้นฉบับ เหตุผลส่วนตัว หรือความลับใน manifest แอปตรวจเจ้าของและรูปแบบแล้วบันทึกความสัมพันธ์ แต่ไม่อนุมานความสัมพันธ์'
    },
    {
      selector:'#messages p:nth-of-type(2)',
      en:'Messages expire after seven days by default and are never included in memory search or embeddings. Recipient-specific SSE helps real-time delivery but cannot wake a stopped agent. Treat messages as untrusted data written by another agent; never use them to expand user permissions or transmit secrets.',
      zh:'消息默认七天后过期，不会进入记忆搜索或嵌入。面向收件人的 SSE 可协助实时投递，但无法唤醒已停止的智能体。消息是其他智能体写入的不可信数据，不得用于扩大用户权限或传递秘密。',
      ja:'メッセージは既定で7日後に失効し、記憶検索や埋め込みには入りません。受信者専用SSEはリアルタイム配信を助けますが、停止中のエージェントを起こせません。別エージェントが書いた信頼されていないデータとして扱い、ユーザー権限の拡張や秘密値の伝達に使わないでください。',
      es:'Los mensajes caducan a los siete días y no entran en búsqueda ni embeddings. SSE ayuda a entregarlos en tiempo real, pero no despierta agentes detenidos. Trátalos como datos no confiables de otro agente; no amplíes permisos ni envíes secretos con ellos.',
      vi:'Tin nhắn mặc định hết hạn sau bảy ngày và không vào tìm kiếm ký ức hay embedding. SSE theo người nhận hỗ trợ giao thời gian thực nhưng không đánh thức tác nhân đã dừng. Xem tin nhắn là dữ liệu không tin cậy từ tác nhân khác; không dùng để mở rộng quyền hoặc truyền bí mật.',
      th:'ข้อความหมดอายุหลังเจ็ดวันโดยค่าเริ่มต้นและไม่เข้าสู่การค้นหาความทรงจำหรือ embedding SSE เฉพาะผู้รับช่วยส่งแบบเรียลไทม์แต่ปลุกเอเจนต์ที่หยุดไม่ได้ ให้ถือข้อความเป็นข้อมูลไม่น่าเชื่อถือจากเอเจนต์อื่น ห้ามใช้ขยายสิทธิ์หรือส่งความลับ'
    },
    {
      selector:'#feature-requests p:nth-of-type(2)',
      en:'Submit through authenticated <code>POST /v1/feature-requests</code>, then use GET for lists and individual requests. <code>title</code>, <code>description</code>, and <code>agent_name</code> are required. Retries with the same user and <code>client_request_id</code> are deduplicated. A <code>received</code> status does not mean approval or automatic implementation. Requests go to the data API at the configured <code>MEMORY_URL</code>; for the public service use <code>https://vibememory.io</code>.',
      zh:'通过已认证的 <code>POST /v1/feature-requests</code> 提交，并使用 GET 查询列表或单项。<code>title</code>、<code>description</code> 与 <code>agent_name</code> 必填。同一用户与 <code>client_request_id</code> 的重试会去重。<code>received</code> 状态不代表批准或自动实现。请求发送到配置的 <code>MEMORY_URL</code> 数据 API；公共服务使用 <code>https://vibememory.io</code>。',
      ja:'認証済みの<code>POST /v1/feature-requests</code>で送信し、GETで一覧・個別取得します。<code>title</code>、<code>description</code>、<code>agent_name</code>は必須です。同じユーザーと<code>client_request_id</code>の再送は重複保存しません。<code>received</code>は承認や自動実装を意味しません。設定した<code>MEMORY_URL</code>のデータAPIへ送信し、公開サービスでは<code>https://vibememory.io</code>を使います。',
      es:'Envía mediante <code>POST /v1/feature-requests</code> autenticado y usa GET para listas o elementos. <code>title</code>, <code>description</code> y <code>agent_name</code> son obligatorios. Los reintentos con el mismo usuario y <code>client_request_id</code> se deduplican. <code>received</code> no implica aprobación ni implementación. Se envía a <code>MEMORY_URL</code>; el servicio público usa <code>https://vibememory.io</code>.',
      vi:'Gửi qua <code>POST /v1/feature-requests</code> đã xác thực và dùng GET cho danh sách hoặc từng yêu cầu. Bắt buộc <code>title</code>, <code>description</code> và <code>agent_name</code>. Gửi lại cùng người dùng và <code>client_request_id</code> được loại trùng. Trạng thái <code>received</code> không có nghĩa được duyệt hay tự triển khai. Yêu cầu gửi đến API tại <code>MEMORY_URL</code>; dịch vụ công khai dùng <code>https://vibememory.io</code>.',
      th:'ส่งผ่าน <code>POST /v1/feature-requests</code> ที่ยืนยันตัวตนและใช้ GET สำหรับรายการหรือคำขอเดี่ยว ต้องมี <code>title</code> <code>description</code> และ <code>agent_name</code> การส่งซ้ำด้วยผู้ใช้และ <code>client_request_id</code> เดิมจะไม่บันทึกซ้ำ สถานะ <code>received</code> ไม่ได้หมายถึงอนุมัติหรือทำให้อัตโนมัติ คำขอส่งไปยัง data API ที่ <code>MEMORY_URL</code> บริการสาธารณะใช้ <code>https://vibememory.io</code>'
    },
    {
      selector:'#api p:nth-of-type(1)',
      en:'Every <code>/v1</code> request requires Bearer authentication. View the full schema at <code>/openapi.json</code> and interactive documentation at <code>/docs</code> on the running server.',
      zh:'所有 <code>/v1</code> 请求都需要 Bearer 认证。可在运行中的服务器通过 <code>/openapi.json</code> 查看完整架构，通过 <code>/docs</code> 查看交互式文档。',
      ja:'すべての<code>/v1</code>リクエストにBearer認証が必要です。実行中サーバーの<code>/openapi.json</code>で全スキーマ、<code>/docs</code>で対話型文書を確認できます。',
      es:'Todas las solicitudes <code>/v1</code> requieren autenticación Bearer. Consulta el esquema en <code>/openapi.json</code> y la documentación interactiva en <code>/docs</code>.',
      vi:'Mọi yêu cầu <code>/v1</code> cần xác thực Bearer. Xem schema đầy đủ tại <code>/openapi.json</code> và tài liệu tương tác tại <code>/docs</code> trên máy chủ.',
      th:'คำขอ <code>/v1</code> ทุกคำขอต้องยืนยันตัวตนแบบ Bearer ดู schema ทั้งหมดที่ <code>/openapi.json</code> และเอกสารโต้ตอบที่ <code>/docs</code> บนเซิร์ฟเวอร์'
    }
  ];
  const guideOriginalHtml = new WeakMap();
  const textOriginal = new WeakMap();
  const textApplied = new WeakMap();
  const attributeOriginal = new WeakMap();
  const attributeApplied = new WeakMap();

  function currentLocale() { return locale; }
  function localeTag() { return localeTags[locale]; }
  function translateText(value) {
    if (!value || locale === 'ko') return value;
    const direct = translations.get(value);
    if (direct) return direct[locale] || direct.en;
    const count = value.match(/^(\d+)개의 에이전트 키가 이 워크스페이스에 접근할 수 있습니다\.$/);
    if (count) return {
      en:`${count[1]} agent keys can access this workspace.`,zh:`${count[1]} 个智能体密钥可访问此工作区。`,ja:`${count[1]}個のエージェントキーがこのワークスペースにアクセスできます。`,es:`${count[1]} claves de agente pueden acceder a este espacio.`,vi:`${count[1]} khóa tác nhân có thể truy cập không gian này.`,th:`คีย์เอเจนต์ ${count[1]} รายการเข้าถึงพื้นที่ทำงานนี้ได้`
    }[locale];
    const greeting = value.match(/^(.+)님, 기억이 이어지고 있어요\.$/);
    if (greeting) return {
      en:`${greeting[1]}, your memory is continuing.`,zh:`${greeting[1]}，你的记忆正在延续。`,ja:`${greeting[1]}さん、記憶がつながっています。`,es:`${greeting[1]}, tu memoria continúa.`,vi:`${greeting[1]}, ký ức của bạn đang được tiếp nối.`,th:`${greeting[1]} ความทรงจำของคุณกำลังต่อเนื่อง`
    }[locale];
    const workspace = value.match(/^(.+)의 기억$/);
    if (workspace) return {
      en:`${workspace[1]}'s memory`,zh:`${workspace[1]}的记忆`,ja:`${workspace[1]}の記憶`,es:`Memoria de ${workspace[1]}`,vi:`Ký ức của ${workspace[1]}`,th:`ความทรงจำของ ${workspace[1]}`
    }[locale];
    const page = value.match(/^(\d+) 페이지$/);
    if (page) return {en:`Page ${page[1]}`,zh:`第 ${page[1]} 页`,ja:`${page[1]}ページ`,es:`Página ${page[1]}`,vi:`Trang ${page[1]}`,th:`หน้า ${page[1]}`}[locale];
    const requests = value.match(/^(\d+)개 요청 중 (\d+)개를 표시합니다\.$/);
    if (requests) return {
      en:`Showing ${requests[2]} of ${requests[1]} requests.`,zh:`显示 ${requests[1]} 个请求中的 ${requests[2]} 个。`,ja:`${requests[1]}件中${requests[2]}件のリクエストを表示します。`,es:`Mostrando ${requests[2]} de ${requests[1]} solicitudes.`,vi:`Hiển thị ${requests[2]} trong ${requests[1]} yêu cầu.`,th:`แสดง ${requests[2]} จาก ${requests[1]} คำขอ`
    }[locale];
    const users = value.match(/^(\d+)명의 사용자 중 (\d+)명을 표시합니다\.$/);
    if (users) return {
      en:`Showing ${users[2]} of ${users[1]} users.`,zh:`显示 ${users[1]} 位用户中的 ${users[2]} 位。`,ja:`${users[1]}人中${users[2]}人のユーザーを表示します。`,es:`Mostrando ${users[2]} de ${users[1]} usuarios.`,vi:`Hiển thị ${users[2]} trong ${users[1]} người dùng.`,th:`แสดง ${users[2]} จากผู้ใช้ ${users[1]} คน`
    }[locale];
    const graph = value.match(/^(\d+)개 노드와 (\d+)개 관계를 표시합니다\.$/);
    if (graph) return {
      en:`Showing ${graph[1]} nodes and ${graph[2]} relationships.`,zh:`显示 ${graph[1]} 个节点和 ${graph[2]} 条关系。`,ja:`${graph[1]}ノードと${graph[2]}件の関係を表示します。`,es:`Mostrando ${graph[1]} nodos y ${graph[2]} relaciones.`,vi:`Hiển thị ${graph[1]} nút và ${graph[2]} quan hệ.`,th:`แสดง ${graph[1]} โหนดและ ${graph[2]} ความสัมพันธ์`
    }[locale];
    const graphTruncated = value.match(/^전체 (\d+)개 노드와 (\d+)개 관계 중 연결 중심으로 표시합니다\.$/);
    if (graphTruncated) return {
      en:`Showing the most connected items from ${graphTruncated[1]} nodes and ${graphTruncated[2]} relationships.`,zh:`从 ${graphTruncated[1]} 个节点和 ${graphTruncated[2]} 条关系中优先显示连接中心。`,ja:`全${graphTruncated[1]}ノード・${graphTruncated[2]}関係から接続中心で表示します。`,es:`Mostrando los elementos más conectados de ${graphTruncated[1]} nodos y ${graphTruncated[2]} relaciones.`,vi:`Hiển thị các mục kết nối nhiều nhất trong ${graphTruncated[1]} nút và ${graphTruncated[2]} quan hệ.`,th:`แสดงรายการที่เชื่อมโยงมากที่สุดจาก ${graphTruncated[1]} โหนดและ ${graphTruncated[2]} ความสัมพันธ์`
    }[locale];
    const updated = value.match(/^최종 갱신 (.+)$/);
    if (updated) return {en:`Last updated ${updated[1]}`,zh:`最后更新 ${updated[1]}`,ja:`最終更新 ${updated[1]}`,es:`Última actualización ${updated[1]}`,vi:`Cập nhật lần cuối ${updated[1]}`,th:`อัปเดตล่าสุด ${updated[1]}`}[locale];
    const recent = value.match(/^최근 (\d+)건 · 최대 100건 · UTC 기준$/);
    if (recent) return {en:`Latest ${recent[1]} · up to 100 · UTC`,zh:`最近 ${recent[1]} 条 · 最多 100 条 · UTC`,ja:`直近${recent[1]}件 · 最大100件 · UTC`,es:`Últimos ${recent[1]} · máximo 100 · UTC`,vi:`${recent[1]} mục gần nhất · tối đa 100 · UTC`,th:`ล่าสุด ${recent[1]} รายการ · สูงสุด 100 · UTC`}[locale];
    const connections = value.match(/^(\d+)개의 연결$/);
    if (connections) return {en:`${connections[1]} connections`,zh:`${connections[1]} 个连接`,ja:`${connections[1]}つのつながり`,es:`${connections[1]} conexiones`,vi:`${connections[1]} kết nối`,th:`${connections[1]} ความเชื่อมโยง`}[locale];
    const secrets = value.match(/^(\d+)개의 비밀값이 저장되어 있습니다\.$/);
    if (secrets) return {en:`${secrets[1]} secrets stored.`,zh:`已保存 ${secrets[1]} 个秘密。`,ja:`${secrets[1]}件の秘密値を保存しています。`,es:`${secrets[1]} secretos guardados.`,vi:`Đã lưu ${secrets[1]} bí mật.`,th:`บันทึกความลับ ${secrets[1]} รายการ`}[locale];
    const mcpConnections = value.match(/^(\d+)개의 GPT·Claude 연결이 활성 상태입니다\.$/);
    if (mcpConnections) return {en:`${mcpConnections[1]} GPT or Claude connections active.`,zh:`${mcpConnections[1]} 个 GPT 或 Claude 连接处于活动状态。`,ja:`${mcpConnections[1]}件のGPT・Claude接続が有効です。`,es:`${mcpConnections[1]} conexiones de GPT o Claude activas.`,vi:`${mcpConnections[1]} kết nối GPT hoặc Claude đang hoạt động.`,th:`การเชื่อมต่อ GPT หรือ Claude ${mcpConnections[1]} รายการกำลังทำงาน`}[locale];
    const displayed = value.match(/^(\d+)개 표시$/);
    if (displayed) return {en:`${displayed[1]} shown`,zh:`显示 ${displayed[1]} 个`,ja:`${displayed[1]}件表示`,es:`${displayed[1]} mostradas`,vi:`Hiển thị ${displayed[1]}`,th:`แสดง ${displayed[1]} รายการ`}[locale];
    const itemCount = value.match(/^(\d+)개$/);
    if (itemCount) return {en:`${itemCount[1]}`,zh:`${itemCount[1]} 个`,ja:`${itemCount[1]}個`,es:`${itemCount[1]}`,vi:`${itemCount[1]}`,th:`${itemCount[1]} รายการ`}[locale];
    const adminRelations = value.match(/^관계 (\d+) · Vault (\d+)$/);
    if (adminRelations) return {en:`Relationships ${adminRelations[1]} · Vault ${adminRelations[2]}`,zh:`关系 ${adminRelations[1]} · Vault ${adminRelations[2]}`,ja:`関係 ${adminRelations[1]} · Vault ${adminRelations[2]}`,es:`Relaciones ${adminRelations[1]} · Vault ${adminRelations[2]}`,vi:`Quan hệ ${adminRelations[1]} · Vault ${adminRelations[2]}`,th:`ความสัมพันธ์ ${adminRelations[1]} · Vault ${adminRelations[2]}`}[locale];
    const adminStorage = value.match(/^기억 (.+) · 파일 (.+)$/);
    if (adminStorage) return {en:`Memory ${adminStorage[1]} · Files ${adminStorage[2]}`,zh:`记忆 ${adminStorage[1]} · 文件 ${adminStorage[2]}`,ja:`記憶 ${adminStorage[1]} · ファイル ${adminStorage[2]}`,es:`Memoria ${adminStorage[1]} · Archivos ${adminStorage[2]}`,vi:`Ký ức ${adminStorage[1]} · Tệp ${adminStorage[2]}`,th:`ความทรงจำ ${adminStorage[1]} · ไฟล์ ${adminStorage[2]}`}[locale];
    const agentConnected = value.match(/^(.+) · 연결 (.+)$/);
    if (agentConnected) return {en:`${agentConnected[1]} · connected ${agentConnected[2]}`,zh:`${agentConnected[1]} · 连接于 ${agentConnected[2]}`,ja:`${agentConnected[1]} · 接続 ${agentConnected[2]}`,es:`${agentConnected[1]} · conexión ${agentConnected[2]}`,vi:`${agentConnected[1]} · kết nối ${agentConnected[2]}`,th:`${agentConnected[1]} · เชื่อมต่อ ${agentConnected[2]}`}[locale];
    const deleteVaultItem = value.match(/^(.+) 항목은 복구할 수 없으며 연결된 에이전트에서 즉시 사용할 수 없게 됩니다\.$/);
    if (deleteVaultItem) return {en:`${deleteVaultItem[1]} cannot be recovered and will immediately become unavailable to connected agents.`,zh:`${deleteVaultItem[1]} 无法恢复，并将立即对已连接智能体不可用。`,ja:`${deleteVaultItem[1]}は復元できず、接続エージェントですぐに利用できなくなります。`,es:`${deleteVaultItem[1]} no se puede recuperar y dejará de estar disponible inmediatamente.`,vi:`Không thể khôi phục ${deleteVaultItem[1]} và tác nhân kết nối sẽ mất quyền dùng ngay.`,th:`${deleteVaultItem[1]} กู้คืนไม่ได้และเอเจนต์ที่เชื่อมต่อจะใช้งานไม่ได้ทันที`}[locale];
    const vaultEditor = value.match(/^(.+) Vault 항목 권한$/);
    if (vaultEditor) return {en:`${vaultEditor[1]} Vault item access`,zh:`${vaultEditor[1]} Vault 条目权限`,ja:`${vaultEditor[1]} Vault項目権限`,es:`Acceso a elementos de Vault para ${vaultEditor[1]}`,vi:`Quyền mục Vault cho ${vaultEditor[1]}`,th:`สิทธิ์รายการ Vault สำหรับ ${vaultEditor[1]}`}[locale];
    const relationLabel = value.match(/^(.+) 관계$/);
    if (relationLabel) return {en:`${relationLabel[1]} relationship`,zh:`${relationLabel[1]} 关系`,ja:`${relationLabel[1]} 関係`,es:`Relación ${relationLabel[1]}`,vi:`Quan hệ ${relationLabel[1]}`,th:`ความสัมพันธ์ ${relationLabel[1]}`}[locale];
    const approved = value.match(/^승인했습니다\. Vault 권한: (허용|허용하지 않음)\. 에이전트가 자동으로 결과를 확인합니다\.$/);
    if (approved) {
      const allowed = approved[1] === '허용';
      return {
        en:`Approved. Vault access: ${allowed ? 'allowed' : 'not allowed'}. The agent will automatically check the result.`,
        zh:`已批准。Vault 权限：${allowed ? '允许' : '不允许'}。智能体将自动检查结果。`,
        ja:`承認しました。Vault権限：${allowed ? '許可' : '不許可'}。エージェントが自動で結果を確認します。`,
        es:`Aprobado. Acceso a Vault: ${allowed ? 'permitido' : 'no permitido'}. El agente comprobará el resultado automáticamente.`,
        vi:`Đã phê duyệt. Quyền Vault: ${allowed ? 'được phép' : 'không được phép'}. Tác nhân sẽ tự kiểm tra kết quả.`,
        th:`อนุมัติแล้ว สิทธิ์ Vault: ${allowed ? 'อนุญาต' : 'ไม่อนุญาต'} เอเจนต์จะตรวจสอบผลลัพธ์อัตโนมัติ`
      }[locale];
    }
    return value;
  }

  function translateNode(node) {
    if (node.parentElement?.closest('script,style,code,pre')) return;
    const current = node.nodeValue || '';
    if (!textOriginal.has(node) || (textApplied.has(node) && current !== textApplied.get(node))) {
      textOriginal.set(node, current);
    }
    const original = textOriginal.get(node);
    const match = original.match(/^(\s*)([\s\S]*?)(\s*)$/);
    if (!match || !match[2]) return;
    const translated = match[1] + translateText(match[2]) + match[3];
    if (node.nodeValue !== translated) node.nodeValue = translated;
    textApplied.set(node, translated);
  }

  function translateElement(element) {
    const names = ['placeholder','aria-label','title'];
    let originals = attributeOriginal.get(element);
    if (!originals) { originals = {}; attributeOriginal.set(element, originals); }
    let applied = attributeApplied.get(element);
    if (!applied) { applied = {}; attributeApplied.set(element, applied); }
    for (const name of names) {
      if (!element.hasAttribute(name)) continue;
      const current = element.getAttribute(name);
      if (!(name in originals) || (name in applied && current !== applied[name])) originals[name] = current;
      const translated = translateText(originals[name]);
      if (current !== translated) element.setAttribute(name, translated);
      applied[name] = translated;
    }
  }

  function applyGuideContent() {
    if (typeof document.querySelector !== 'function') return;
    for (const row of guideHtmlRows) {
      const element = document.querySelector(row.selector);
      if (!element) continue;
      if (!guideOriginalHtml.has(element)) guideOriginalHtml.set(element, element.innerHTML);
      const next = locale === 'ko' ? guideOriginalHtml.get(element) : (row[locale] || row.en);
      if (element.innerHTML !== next) element.innerHTML = next;
    }
  }

  function apply(root = document.body) {
    if (!root) return;
    applyGuideContent();
    if (root.nodeType === Node.TEXT_NODE) translateNode(root);
    if (root.nodeType === Node.ELEMENT_NODE) translateElement(root);
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_ELEMENT | NodeFilter.SHOW_TEXT);
    let node;
    while ((node = walker.nextNode())) {
      if (node.nodeType === Node.TEXT_NODE) translateNode(node); else translateElement(node);
    }
    document.documentElement.lang = localeTags[locale].split('-')[0];
    const path = location.pathname.replace(/\.html$/, '') || '/';
    if (pageTitles[path]) document.title = pageTitles[path][locale];
    const metadata = pageMetadata[path];
    if (metadata) {
      const description = document.querySelector?.('meta[name="description"]');
      const ogTitle = document.querySelector?.('meta[property="og:title"]');
      const ogDescription = document.querySelector?.('meta[property="og:description"]');
      if (description && metadata.description) description.content = metadata.description[locale] || metadata.description.en;
      if (ogTitle && metadata.ogTitle) ogTitle.content = metadata.ogTitle[locale] || metadata.ogTitle.en;
      if (ogDescription && metadata.ogDescription) ogDescription.content = metadata.ogDescription[locale] || metadata.ogDescription.en;
    }
  }

  function mountSwitcher() {
    if (document.querySelector('[data-vm-language]')) return;
    const wrapper = document.createElement('label');
    wrapper.className = 'vm-language-switcher'; wrapper.dataset.vmLanguage = '';
    const languageIcon = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    languageIcon.setAttribute('class', 'vm-language-icon');
    languageIcon.setAttribute('aria-hidden', 'true');
    const languageIconUse = document.createElementNS('http://www.w3.org/2000/svg', 'use');
    languageIconUse.setAttribute('href', '/assets/icons.svg#language');
    languageIcon.append(languageIconUse);
    const select = document.createElement('select');
    select.setAttribute('aria-label', '언어 선택');
    for (const code of supported) {
      const option = document.createElement('option'); option.value = code; option.textContent = labels[code]; select.append(option);
    }
    select.value = locale;
    select.addEventListener('change', () => {
      setLocale(select.value);
    });
    wrapper.append(languageIcon, select);
    const mount = document.querySelector('.header-actions') || document.querySelector('.console-header .topbar-actions') || document.querySelector('.admin-header nav');
    if (mount) mount.prepend(wrapper); else { wrapper.classList.add('vm-language-floating'); document.body.append(wrapper); }
  }

  function setLocale(nextLocale, persist = true) {
    if (!supported.includes(nextLocale)) return false;
    locale = nextLocale;
    if (persist) storeLocale(locale);
    apply();
    document.querySelectorAll('[data-vm-language] select').forEach(peer => { peer.value = locale; });
    window.dispatchEvent(new CustomEvent('vm-language-change', {detail:{locale,tag:localeTag()}}));
    return true;
  }

  window.vmCurrentLocale = currentLocale;
  window.vmLocaleTag = localeTag;
  window.vmTranslateText = translateText;
  window.vmApplyTranslations = apply;
  window.vmSetLocale = setLocale;
  const nativeConfirm = window.confirm.bind(window);
  window.confirm = message => nativeConfirm(translateText(String(message)));

  document.addEventListener('DOMContentLoaded', () => {
    mountSwitcher(); apply();
    new MutationObserver(mutations => {
      for (const mutation of mutations) {
        if (mutation.type === 'characterData') translateNode(mutation.target);
        if (mutation.type === 'attributes') translateElement(mutation.target);
        for (const node of mutation.addedNodes) apply(node);
      }
    }).observe(document.body, {subtree:true,childList:true,characterData:true,attributes:true,attributeFilter:['placeholder','aria-label','title']});
  });
})();

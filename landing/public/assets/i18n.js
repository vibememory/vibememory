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
    '/guide': {ko:'연결 가이드 — Vibe Memory',en:'Connection guide — Vibe Memory',zh:'连接指南 — Vibe Memory',ja:'接続ガイド — Vibe Memory',es:'Guía de conexión — Vibe Memory',vi:'Hướng dẫn kết nối — Vibe Memory',th:'คู่มือการเชื่อมต่อ — Vibe Memory'}
  };
  const detected = (navigator.language || 'ko').toLowerCase().split('-')[0];
  let locale = localStorage.getItem('vm-language') || (supported.includes(detected) ? detected : 'en');
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
    ['ChatGPT 또는 Claude에서 사용','Use with ChatGPT or Claude','在 ChatGPT 或 Claude 中使用','ChatGPTまたはClaudeで使用','Usar con ChatGPT o Claude'],
    ['버튼을 누르면 MCP 주소를 복사하고 각 서비스의 커넥터 화면을 엽니다. 로그인 후 Vibe Memory 연결을 승인하세요.','The button copies the MCP address and opens the connector page. Log in and approve Vibe Memory.','点击按钮会复制 MCP 地址并打开连接器页面。登录后批准 Vibe Memory 连接。','ボタンを押すとMCPアドレスをコピーし、コネクター画面を開きます。ログイン後、Vibe Memoryを承認してください。','El botón copia la dirección MCP y abre la página de conectores. Inicia sesión y autoriza Vibe Memory.'],
    ['ChatGPT에서 사용','Use with ChatGPT','在 ChatGPT 中使用','ChatGPTで使用','Usar con ChatGPT'],
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
    'Dùng với ChatGPT hoặc Claude',
    'Nút này sao chép địa chỉ MCP và mở trang trình kết nối. Hãy đăng nhập và phê duyệt Vibe Memory.',
    'Dùng với ChatGPT',
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
    'ใช้กับ ChatGPT หรือ Claude',
    'ปุ่มนี้จะคัดลอกที่อยู่ MCP และเปิดหน้าตัวเชื่อมต่อ เข้าสู่ระบบแล้วอนุมัติ Vibe Memory',
    'ใช้กับ ChatGPT',
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
  const translations = new Map(rows.map((row, index) => [row[0], {ko:row[0],en:row[1],zh:row[2],ja:row[3],es:row[4],vi:viRows[index],th:thRows[index]}]));
  const textOriginal = new WeakMap();
  const attributeOriginal = new WeakMap();

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
    return value;
  }

  function translateNode(node) {
    if (node.parentElement?.closest('script,style,code,pre')) return;
    if (!textOriginal.has(node)) textOriginal.set(node, node.nodeValue || '');
    const original = textOriginal.get(node);
    const match = original.match(/^(\s*)([\s\S]*?)(\s*)$/);
    if (!match || !match[2]) return;
    const translated = match[1] + translateText(match[2]) + match[3];
    if (node.nodeValue !== translated) node.nodeValue = translated;
  }

  function translateElement(element) {
    const names = ['placeholder','aria-label','title'];
    let originals = attributeOriginal.get(element);
    if (!originals) { originals = {}; attributeOriginal.set(element, originals); }
    for (const name of names) {
      if (!element.hasAttribute(name)) continue;
      if (!(name in originals)) originals[name] = element.getAttribute(name);
      element.setAttribute(name, translateText(originals[name]));
    }
  }

  function apply(root = document.body) {
    if (!root) return;
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
  }

  function mountSwitcher() {
    if (document.querySelector('[data-vm-language]')) return;
    const wrapper = document.createElement('label');
    wrapper.className = 'vm-language-switcher'; wrapper.dataset.vmLanguage = '';
    const select = document.createElement('select');
    select.setAttribute('aria-label', translateText('언어 선택'));
    for (const code of supported) {
      const option = document.createElement('option'); option.value = code; option.textContent = labels[code]; select.append(option);
    }
    select.value = locale;
    select.addEventListener('change', () => {
      locale = select.value; localStorage.setItem('vm-language', locale); apply();
      document.querySelectorAll('[data-vm-language] select').forEach(peer => { peer.value = locale; });
      window.dispatchEvent(new CustomEvent('vm-language-change', {detail:{locale,tag:localeTag()}}));
    });
    wrapper.append(select);
    const mount = document.querySelector('.header-actions') || document.querySelector('.console-header .topbar-actions');
    if (mount) mount.prepend(wrapper); else { wrapper.classList.add('vm-language-floating'); document.body.append(wrapper); }
  }

  window.vmCurrentLocale = currentLocale;
  window.vmLocaleTag = localeTag;
  window.vmTranslateText = translateText;
  const nativeConfirm = window.confirm.bind(window);
  window.confirm = message => nativeConfirm(translateText(String(message)));

  document.addEventListener('DOMContentLoaded', () => {
    mountSwitcher(); apply();
    new MutationObserver(mutations => {
      for (const mutation of mutations) {
        if (mutation.type === 'characterData') translateNode(mutation.target);
        for (const node of mutation.addedNodes) apply(node);
      }
    }).observe(document.body, {subtree:true,childList:true,characterData:true});
  });
})();

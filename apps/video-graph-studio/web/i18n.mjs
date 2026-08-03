export const UI_LOCALES = ["zh-CN", "en-US", "ru-RU"];

const COPY = {
  completionEyebrow: {"zh-CN":"任务结果", "en-US":"RESULTS", "ru-RU":"РЕЗУЛЬТАТЫ"},
  completionTitle: {"zh-CN":"成片已经保存。", "en-US":"Your videos are ready.", "ru-RU":"Видео готовы."},
  completionCopy: {"zh-CN":"在浏览器中检查成片，下载文件，或复制真实保存位置。", "en-US":"Preview the finished videos, download a file, or copy its real local location.", "ru-RU":"Просмотрите готовые видео, скачайте файл или скопируйте путь сохранения."},
  elapsed: {"zh-CN":"总耗时", "en-US":"Elapsed", "ru-RU":"Время"},
  size: {"zh-CN":"成片大小", "en-US":"Output size", "ru-RU":"Размер"},
  tokens: {"zh-CN":"翻译 Token", "en-US":"Translation tokens", "ru-RU":"Токены перевода"},
  videos: {"zh-CN":"可预览成片", "en-US":"Previewable videos", "ru-RU":"Доступно видео"},
  outputFolder: {"zh-CN":"保存文件夹", "en-US":"Output folder", "ru-RU":"Папка сохранения"},
  copyPath: {"zh-CN":"复制路径", "en-US":"Copy path", "ru-RU":"Копировать путь"},
  preview: {"zh-CN":"预览", "en-US":"Preview", "ru-RU":"Просмотр"},
  download: {"zh-CN":"下载", "en-US":"Download", "ru-RU":"Скачать"},
  copied: {"zh-CN":"保存路径已复制。", "en-US":"Output path copied.", "ru-RU":"Путь скопирован."},
  unavailable: {"zh-CN":"文件校验失败", "en-US":"File unavailable", "ru-RU":"Файл недоступен"},
  localeLabel: {"zh-CN":"界面语言", "en-US":"Interface language", "ru-RU":"Язык интерфейса"},
  connectionReady: {"zh-CN":"已连接 · 仅私密", "en-US":"Connected · private only", "ru-RU":"Подключено · только приватно"},
  connectionRequired: {"zh-CN":"需要连接账户", "en-US":"Account connection required", "ru-RU":"Требуется подключить аккаунт"},
  adapterMissing: {"zh-CN":"上传组件未安装", "en-US":"Uploader not installed", "ru-RU":"Загрузчик не установлен"},
  noAccounts: {"zh-CN":"没有可用账户", "en-US":"No available accounts", "ru-RU":"Нет доступных аккаунтов"},
  connectedAccounts: {"zh-CN":"个已连接", "en-US":"connected", "ru-RU":"подключено"},
  verifiedPrivate: {"zh-CN":"选择已验证账户；当前只允许私密上传。", "en-US":"Choose a verified account. Publishing is currently private only.", "ru-RU":"Выберите подтверждённый аккаунт. Сейчас доступна только приватная публикация."},
  youtubeConnected: {"zh-CN":"YouTube 账户已连接，可以选择私密上传。", "en-US":"YouTube is connected and ready for private publishing.", "ru-RU":"YouTube подключён и готов к приватной публикации."},
};

const PAGE_COPY = {
  "新建本地视频项目": ["New local video project", "Новый локальный видеопроект"], "只在电脑上处理 · 尚未开始": ["Local processing · not started", "Локальная обработка · не запущено"],
  "正在连接": ["Connecting", "Подключение"],
  "来源": ["Source", "Источник"], "账号或本地文件夹": ["Account or local folder", "Аккаунт или локальная папка"],
  "视频": ["Videos", "Видео"], "确认完整清单": ["Confirm the complete list", "Проверка полного списка"],
  "翻译": ["Translation", "Перевод"], "语言与翻译引擎": ["Languages and translation engine", "Языки и движок перевода"],
  "配音": ["Voice", "Озвучка"], "Edge / Qwen3 / 原声": ["Edge / Qwen3 / original", "Edge / Qwen3 / оригинал"],
  "输出": ["Output", "Результат"], "本地保存，可选上传": ["Local save, optional publishing", "Локально, публикация по желанию"],
  "检查": ["Review", "Проверка"], "确认实际工作量": ["Confirm the exact workload", "Проверка точного объёма"],
  "进度": ["Activity", "Ход работы"], "可恢复的执行记录": ["Recoverable execution record", "Восстанавливаемый журнал"],
  "串行安全执行": ["Safe serial execution", "Безопасное последовательное выполнение"],
  "完成一项保存一项，失败后可继续": ["Each result is saved and failed work can resume", "Каждый результат сохраняется, сбой можно продолжить"],
  "选择来源": ["CHOOSE SOURCE", "ВЫБОР ИСТОЧНИКА"], "视频从哪里来？": ["Where are the videos?", "Откуда взять видео?"],
  "粘贴账号主页或单条视频链接，系统会自动识别；也可以直接使用电脑里的视频文件。": ["Paste a creator profile or single video URL, or use video files already on this computer.", "Вставьте ссылку на автора или одно видео либо выберите файлы на компьютере."],
  "只在本机处理": ["Local processing", "Локальная обработка"], "粘贴视频链接": ["Paste a video URL", "Вставить ссылку"],
  "自动识别账号或单个视频": ["Detect an account or a single video", "Определить аккаунт или одно видео"],
  "本地视频文件夹": ["Local video folder", "Локальная папка с видео"], "直接使用电脑上的 MP4 / MOV / MKV": ["Use MP4 / MOV / MKV files on this computer", "Использовать MP4 / MOV / MKV с компьютера"],
  "账号主页或视频链接": ["Creator profile or video URL", "Ссылка на автора или видео"], "识别链接": ["Inspect URL", "Проверить ссылку"],
  "高级：限制数量与登录 Cookie": ["Advanced: item limit and login cookie", "Дополнительно: лимит и cookie входа"],
  "还没有识别链接": ["No link inspected yet", "Ссылка ещё не проверена"], "账号链接会列出作品，单条链接只加入该视频。": ["A creator link lists its videos; a video link adds only that item.", "Ссылка на автора покажет все видео; ссылка на видео добавит только его."],
  "原视频语言": ["Source language", "Язык оригинала"], "自动识别": ["Auto detect", "Определить автоматически"],
  "语音识别模型": ["Speech recognition model", "Модель распознавания речи"],
  "中文": ["Chinese", "Китайский"], "英语": ["English", "Английский"], "俄语": ["Russian", "Русский"],
  "Small · 平衡": ["Small · balanced", "Small · сбалансировано"], "Large v3 · 质量": ["Large v3 · quality", "Large v3 · качество"], "Tiny · 快速": ["Tiny · fast", "Tiny · быстро"],
  "确认视频": ["CONFIRM VIDEOS", "ПРОВЕРКА ВИДЕО"], "哪些视频需要处理？": ["Which videos should be processed?", "Какие видео обработать?"],
  "选择当前任务真正需要的视频。搜索只过滤视图，不会取消已经选择的内容。": ["Select the exact videos for this job. Search filters the view without clearing existing selections.", "Выберите точные видео для задачи. Поиск фильтрует список, не снимая выбор."],
  "已选择": ["Selected", "Выбрано"], "选择当前全部": ["Select visible", "Выбрать видимые"], "清空": ["Clear", "Очистить"],
  "已有字幕": ["Subtitles found", "Субтитры найдены"], "需要 ASR": ["ASR required", "Нужно распознавание"], "下载后检查": ["Check after download", "Проверить после загрузки"],
  "设置翻译": ["SET TRANSLATION", "НАСТРОЙКА ПЕРЕВОДА"], "要生成哪些语言？": ["Which languages should be generated?", "Какие языки создать?"],
  "先选择翻译引擎，再选择一种或多种目标语言。每种语言都会生成独立的本地成片。": ["Choose a translation engine and one or more target languages. Each language produces its own local video.", "Выберите движок и один или несколько языков. Для каждого языка создаётся отдельное локальное видео."],
  "俄语 + 英语": ["Russian + English", "Русский + английский"],
  "在本机运行；模型安装后可离线。": ["Runs locally and works offline after the model is installed.", "Работает локально и офлайн после установки модели."], "点此配置": ["Configure", "Настроить"],
  "质量优先的云端翻译；可直接在下方保存 API Key。": ["Cloud translation focused on quality; configure its API key below.", "Облачный перевод с упором на качество; API-ключ настраивается ниже."],
  "DEEPSEEK 设置": ["DEEPSEEK SETUP", "НАСТРОЙКА DEEPSEEK"], "连接 DeepSeek": ["Connect DeepSeek", "Подключить DeepSeek"],
  "输入 API Key 后保存在这台电脑的 Windows 加密凭据库。任务和日志不会记录密钥。": ["The API key is encrypted for the current Windows user and never written to jobs or logs.", "API-ключ шифруется для текущего пользователя Windows и не записывается в задачи или журналы."],
  "保存并启用": ["Save and enable", "Сохранить и включить"], "尚未配置": ["Not configured", "Не настроено"],
  "先选择至少一种目标语言。": ["Select at least one target language.", "Выберите хотя бы один целевой язык."], "选择配音": ["Choose voice", "Выбрать голос"],
  "设置声音": ["SET VOICE", "НАСТРОЙКА ГОЛОСА"], "译文使用什么声音？": ["Which voice should read the translation?", "Каким голосом озвучить перевод?"],
  "Edge TTS 速度快，Qwen3-TTS 在本机运行，也可以保留原声并只覆盖翻译字幕。": ["Edge TTS is fast, Qwen3-TTS runs locally, and original audio can be kept with translated subtitles only.", "Edge TTS работает быстро, Qwen3-TTS локально; можно сохранить оригинальный звук и заменить только субтитры."],
  "保留原视频声音": ["Keep source audio", "Сохранить исходный звук"],
  "设置输出": ["SET OUTPUT", "НАСТРОЙКА РЕЗУЛЬТАТА"], "成片保存到哪里？": ["Where should finished videos be saved?", "Куда сохранить готовые видео?"],
  "发布账户": ["PUBLISHING ACCOUNTS", "АККАУНТЫ ПУБЛИКАЦИИ"], "先连接账户，再选择上传目标。": ["Connect an account before choosing a publishing destination.", "Сначала подключите аккаунт, затем выберите площадку."],
  "连接一个 YouTube 账户": ["Connect a YouTube account", "Подключить аккаунт YouTube"], "账户名称": ["Account label", "Название аккаунта"], "本地账户 ID": ["Local account ID", "Локальный ID аккаунта"],
  "打开 Google 登录": ["Open Google sign-in", "Открыть вход Google"], "凭据由 Windows 当前用户加密保存；网页和日志不会显示 Token。": ["Windows encrypts the credential for the current user; tokens never appear in the page or logs.", "Windows шифрует данные для текущего пользователя; токены не отображаются на странице или в журнале."],
  "本地 MP4 就是完整结果。上传平台是附加选项，不选择任何平台也可以正常完成任务。": ["A local MP4 is a complete result. Publishing is optional and no platform is required.", "Локальный MP4 является готовым результатом. Публикация необязательна."],
  "本地输出必选": ["Local output required", "Локальный результат обязателен"], "本地输出文件夹": ["Local output folder", "Папка результата"], "检查路径": ["Check path", "Проверить путь"],
  "每次运行会在这个目录下创建独立运行文件夹，不覆盖原视频。": ["Each run gets its own folder here; source videos are never overwritten.", "Для каждого запуска создаётся отдельная папка; исходные видео не перезаписываются."],
  "另外准备上传计划（可选）": ["Also prepare publishing plans (optional)", "Также подготовить публикацию (необязательно)"],
  "0 条路线": ["0 routes", "0 маршрутов"], "真实边界": ["Verified boundary", "Проверенная граница"], "YouTube 可准备私密上传；Bilibili、抖音和 TikTok 当前只保存计划，不会假装已经发布。": ["YouTube can prepare private publishing. Bilibili, Douyin and TikTok remain disabled until their upload adapters are verified.", "YouTube поддерживает приватную публикацию. Bilibili, Douyin и TikTok отключены до проверки загрузчиков."],
  "检查任务": ["REVIEW JOB", "ПРОВЕРКА ЗАДАЧИ"], "确认这次要完成的工作。": ["Confirm this job.", "Подтвердите задачу."],
  "核对视频数量、语言、声音和保存位置。系统只会执行这里列出的内容。": ["Review video count, languages, voices and output location. Only the listed work will run.", "Проверьте количество видео, языки, голоса и папку. Будет выполнено только указанное."],
  "来源视频": ["Source videos", "Исходные видео"], "本地成片": ["Local videos", "Готовые видео"], "上传任务": ["Publishing jobs", "Публикации"],
  "修改": ["Edit", "Изменить"], "本地输出": ["Local output", "Локальный результат"], "开始前检查": ["PREFLIGHT", "ПРОВЕРКА"],
  "任务进度": ["JOB ACTIVITY", "ХОД ЗАДАЧИ"], "现在正在处理什么？": ["What is happening now?", "Что происходит сейчас?"],
  "查看当前步骤、失败原因、持久日志和最终文件位置。关闭页面不会删除已经完成的结果。": ["See the current phase, failures, durable logs and final file location. Closing the page does not remove completed results.", "Следите за этапом, ошибками, журналом и расположением файлов. Закрытие страницы не удаляет результаты."],
  "执行日志": ["Execution log", "Журнал выполнения"], "原始诊断信息": ["Raw diagnostics", "Исходная диагностика"], "复制日志": ["Copy log", "Копировать журнал"], "清空视图": ["Clear view", "Очистить вид"],
  "查看系统校验步骤": ["Show verification steps", "Показать этапы проверки"], "← 上一步": ["← Back", "← Назад"],
  "粘贴账号或视频链接，或者选择本地视频文件夹。": ["Paste an account or video URL, or choose a local video folder.", "Вставьте ссылку на аккаунт или видео либо выберите локальную папку."], "查看视频": ["Review videos", "Просмотреть видео"],
};

const ATTRIBUTE_COPY = {
  "粘贴 YouTube、Bilibili、抖音或 TikTok 链接": ["Paste a YouTube, Bilibili, Douyin or TikTok URL", "Вставьте ссылку YouTube, Bilibili, Douyin или TikTok"],
  "搜索标题或视频 ID": ["Search title or video ID", "Поиск по названию или ID"],
  "搜索语言或 locale": ["Search language or locale", "Поиск языка или locale"],
  "搜索 20 种语言": ["Search 20 languages", "Поиск по 20 языкам"],
};

const pageKey = new Map();
for (const [source, values] of Object.entries(PAGE_COPY)) {
  pageKey.set(source, source);
  values.forEach((value) => pageKey.set(value, source));
}

export function translatePage(locale = "zh-CN", root = document.body) {
  const selected = normalizeLocale(locale);
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  for (let node = walker.nextNode(); node; node = walker.nextNode()) {
    const raw = node.nodeValue || "";
    const value = raw.trim();
    const key = pageKey.get(value);
    let translated = key ? (selected === "zh-CN" ? key : PAGE_COPY[key][selected === "en-US" ? 0 : 1]) : null;
    const outputMatch = value.match(/^成片将保存到 (.+)，上传平台仍为可选。$/);
    if (!translated && outputMatch && selected !== "zh-CN") translated = selected === "en-US" ? `Finished videos will be saved to ${outputMatch[1]}; publishing remains optional.` : `Готовые видео будут сохранены в ${outputMatch[1]}; публикация остаётся необязательной.`;
    if (!translated) continue;
    node.nodeValue = `${raw.slice(0, raw.indexOf(value))}${translated}${raw.slice(raw.indexOf(value) + value.length)}`;
  }
  for (const element of root.querySelectorAll("[placeholder]")) {
    const source = Object.entries(ATTRIBUTE_COPY).find(([key, values]) => key === element.placeholder || values.includes(element.placeholder));
    if (!source) continue;
    element.placeholder = selected === "zh-CN" ? source[0] : source[1][selected === "en-US" ? 0 : 1];
  }
}

export function normalizeLocale(value) {
  return UI_LOCALES.includes(value) ? value : "zh-CN";
}

export function tr(key, locale = "zh-CN") {
  const row = COPY[key];
  return row?.[normalizeLocale(locale)] || row?.["zh-CN"] || key;
}

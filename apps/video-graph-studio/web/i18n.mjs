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
};

export function normalizeLocale(value) {
  return UI_LOCALES.includes(value) ? value : "zh-CN";
}

export function tr(key, locale = "zh-CN") {
  const row = COPY[key];
  return row?.[normalizeLocale(locale)] || row?.["zh-CN"] || key;
}

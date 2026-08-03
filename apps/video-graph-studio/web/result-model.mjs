const NOT_REPORTED = {
  "zh-CN": "未报告",
  "en-US": "Not reported",
  "ru-RU": "Не предоставлено",
};

export function formatBytes(value, locale = "zh-CN") {
  const bytes = Number(value);
  if (!Number.isFinite(bytes) || bytes < 0) return NOT_REPORTED[locale] || NOT_REPORTED["en-US"];
  if (bytes < 1024) return `${bytes} B`;
  const units = ["KB", "MB", "GB", "TB"];
  let amount = bytes / 1024;
  let unit = units[0];
  for (let index = 1; index < units.length && amount >= 1024; index += 1) {
    amount /= 1024;
    unit = units[index];
  }
  return `${new Intl.NumberFormat(locale, {maximumFractionDigits: 1}).format(amount)} ${unit}`;
}

export function formatDuration(value, locale = "zh-CN") {
  const total = Math.max(0, Math.round(Number(value)));
  if (!Number.isFinite(total)) return NOT_REPORTED[locale] || NOT_REPORTED["en-US"];
  const hours = Math.floor(total / 3600);
  const minutes = Math.floor((total % 3600) / 60);
  const seconds = total % 60;
  const labels = {
    "zh-CN": ["小时", "分", "秒"],
    "en-US": ["h", "m", "s"],
    "ru-RU": ["ч", "мин", "с"],
  }[locale] || ["h", "m", "s"];
  const unit = (amount, label) => locale === "ru-RU" ? `${amount} ${label}` : `${amount}${label}`;
  return [hours ? unit(hours, labels[0]) : "", minutes ? unit(minutes, labels[1]) : "", unit(seconds, labels[2])].filter(Boolean).join(" ");
}

export function formatTokens(usage, locale = "zh-CN") {
  const value = usage?.totalTokens;
  if (!Number.isInteger(value) || value < 0) return NOT_REPORTED[locale] || NOT_REPORTED["en-US"];
  return new Intl.NumberFormat(locale).format(value);
}

export function presentResult(result, locale = "zh-CN") {
  const videos = Array.isArray(result?.videos) ? result.videos : [];
  return {
    metrics: {
      elapsed: formatDuration(result?.elapsedSeconds, locale),
      bytes: formatBytes(result?.totalBytes, locale),
      tokens: formatTokens(result?.reportedUsage, locale),
      videos: new Intl.NumberFormat(locale).format(videos.filter((row) => row.available).length),
    },
    outputRoot: String(result?.outputRoot || ""),
    videos,
    previewableIds: videos.filter((row) => row.available).map((row) => row.id),
  };
}

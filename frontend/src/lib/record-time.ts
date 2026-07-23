const EXPLICIT_MINUTE_PATTERN = /(?:\d{1,2}\s*[:\uFF1A]\s*\d{1,2}|(?:\d{1,2}|[\u96F6\u3007\u4E00\u4E8C\u4E24\u4E09\u56DB\u4E94\u516D\u4E03\u516B\u4E5D\u5341]{1,3})\s*[\u70B9\u65F6]\s*(?:(?:\d{1,2}|[\u96F6\u3007\u4E00\u4E8C\u4E24\u4E09\u56DB\u4E94\u516D\u4E03\u516B\u4E5D\u5341]{1,3})\s*\u5206?|\u534A|\u4E00\u523B|\u4E09\u523B))/u;

const EXPLICIT_TIME_OF_DAY_PATTERN = /\u65e9\u4e0a|\u4e0a\u5348|\u4e2d\u5348|\u4e0b\u5348|\u508d\u665a|\u665a\u4e0a|\u591c\u91cc|\u65e9\u9910|\u5348\u9910|\u665a\u9910/u;

type RecordTimeOptions = {
  loggedAt: string;
  createdAt?: string;
  sourceText?: string;
  preferCreatedAtForRoundedAiTime?: boolean;
};

export function getRecordDisplayTimestamp({
  loggedAt,
  createdAt,
  sourceText = "",
  preferCreatedAtForRoundedAiTime = false,
}: RecordTimeOptions): number {
  const loggedDate = new Date(loggedAt);
  const createdDate = createdAt ? new Date(createdAt) : null;
  const shouldUseCreatedAt =
    preferCreatedAtForRoundedAiTime &&
    createdDate !== null &&
    !Number.isNaN(createdDate.getTime()) &&
    loggedDate.getMinutes() === 0 &&
    !EXPLICIT_MINUTE_PATTERN.test(sourceText) &&
    !EXPLICIT_TIME_OF_DAY_PATTERN.test(sourceText);
  return (shouldUseCreatedAt ? createdDate : loggedDate).getTime();
}

export function formatRecordTime(options: RecordTimeOptions): string {
  return new Intl.DateTimeFormat("zh-CN", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(new Date(getRecordDisplayTimestamp(options)));
}

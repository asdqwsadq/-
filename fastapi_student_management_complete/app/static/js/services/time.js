let targetTimezone = "Asia/Shanghai";
let synced = false;

const timeSources = [
  "https://worldtimeapi.org/api/timezone/Etc/UTC",
  "https://timeapi.io/api/Time/current/zone?timeZone=UTC",
];

function parseTimezone(payload) {
  if (typeof payload?.timezone === "string" && payload.timezone.trim()) return payload.timezone;
  if (typeof payload?.timeZone === "string" && payload.timeZone.trim()) return payload.timeZone;
  return "Asia/Shanghai";
}

export async function syncNetworkTime() {
  for (const url of timeSources) {
    try {
      const res = await fetch(url, { cache: "no-store" });
      if (!res.ok) continue;
      const data = await res.json();
      targetTimezone = parseTimezone(data);
      synced = true;
      return true;
    } catch (_) {
      // ignore and fallback to next source
    }
  }
  synced = false;
  targetTimezone = "Asia/Shanghai";
  return false;
}

function normalizeIsoText(isoText) {
  if (!isoText) return "";
  const raw = String(isoText).trim();
  if (!raw) return "";
  if (/z$|[+-]\d{2}:\d{2}$/i.test(raw)) return raw;
  if (raw.includes("T")) return `${raw}Z`;
  return `${raw.replace(" ", "T")}Z`;
}

export function formatLogTime(isoText) {
  const normalized = normalizeIsoText(isoText);
  const base = new Date(normalized).getTime();
  if (!Number.isFinite(base)) return isoText || "-";
  return new Date(base).toLocaleString("zh-CN", {
    hour12: false,
    timeZone: synced ? targetTimezone : "Asia/Shanghai",
  });
}

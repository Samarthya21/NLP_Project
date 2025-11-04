export function parseBookingCommand(original) {
  const text = original.trim().toLowerCase();
  let intent = "fallback";
  if (/reserve|book/.test(text)) intent = "book";
  else if (/cancel|delete|remove/.test(text)) intent = "cancel";
  else if (/modify|change|update/.test(text)) intent = "modify";
  else if (/available|free|check/.test(text)) intent = "check_availability";
  else if (/hello|hi|hey/.test(text)) intent = "greet";

  const roomMatch = text.match(/\b([A-Za-z]{2,}\s?\d{2,3})\b/);
  const room = roomMatch ? roomMatch[1].toUpperCase().replace(/\s+/, " ") : null;

  const dateMatch = text.match(/\b(\d{1,2}\s?(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*)\b/);
  const dateString = dateMatch ? dateMatch[1] : null;
  const normalizedDate = dateString ? normalizeDate(dateString) : null;

  const timeMatch = text.match(/(\d{1,2}[:.]?\d{0,2}\s?(?:am|pm)?)\s*(?:to|-)\s*(\d{1,2}[:.]?\d{0,2}\s?(?:am|pm)?)/);
  let start = null, end = null;
  if (timeMatch) {
    start = normalizeTime(timeMatch[1]);
    end = normalizeTime(timeMatch[2]);
  }

  const parsed = {
    intent,
    room,
    building: null,
    date: dateString ? capitalize(dateString) : null,
    start,
    end,
    booking_id: null
  };

  return {
    original,
    now: new Date().toISOString(),
    tz: "Asia/Kolkata",
    parsed
  };
}

function normalizeDate(dateStr) {
  const months = {
    jan: "01", feb: "02", mar: "03", apr: "04", may: "05", jun: "06",
    jul: "07", aug: "08", sep: "09", sept: "09", oct: "10", nov: "11", dec: "12"
  };
  const match = dateStr.match(/(\d{1,2})\s*([a-z]+)/i);
  if (!match) return null;
  const day = String(match[1]).padStart(2, "0");
  const month = months[match[2].slice(0, 3)];
  if (!month) return null;
  const now = new Date();
  const currentYear = now.getFullYear();
  const candidate = new Date(`${currentYear}-${month}-${day}`);
  const finalYear = candidate < now ? currentYear + 1 : currentYear;
  return `${finalYear}-${month}-${day}`;
}

function normalizeTime(t) {
  if (!t) return null;
  let time = t.trim().toLowerCase();
  if (/^\d{1,2}$/.test(time)) time += ":00";
  const isPM = time.includes("pm");
  const isAM = time.includes("am");
  time = time.replace(/(am|pm)/g, "");
  let [hours, mins] = time.split(":").map(Number);
  if (isPM && hours < 12) hours += 12;
  if (isAM && hours === 12) hours = 0;
  return `${String(hours).padStart(2, "0")}:${String(mins || 0).padStart(2, "0")}`;
}

function capitalize(str) {
  return str.split(" ").map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(" ");
}

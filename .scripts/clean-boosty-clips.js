// Чистит статьи Boosty, сохранённые Obsidian Web Clipper, и переносит их в Материалы.
// Запуск из папки «Обучение 2.0»:  node .scripts/clean-boosty-clips.js
// Берёт все .md из Clippings/, у которых source — boosty.to/escaped_ai.
// Убирает: блок иконок сайта (svg), шапку Boosty до заголовка статьи, подвал с уровнями подписки.
// Имя файла: «Название.md», без блока свойств. Существующие файлы не перезаписывает.

const fs = require("fs");
const path = require("path");

const ROOT = path.resolve(__dirname, "..");
const SRC = path.join(ROOT, "Clippings");
const DST = path.join(ROOT, "Материалы", "Сбежавшая нейросеть");
const SOURCE_MARK = "boosty.to/escaped_ai";
const FOOTER_MARKERS = [/^Уровни подписки/, /^Комментарии\s*\d*$/];
const MONTHS = { янв: 1, фев: 2, мар: 3, апр: 4, мая: 5, май: 5, июн: 6, июл: 7, авг: 8, сен: 9, окт: 10, ноя: 11, дек: 12 };

function pad(n) { return String(n).padStart(2, "0"); }

function splitFrontmatter(text) {
  const m = text.match(/^---\r?\n([\s\S]*?)\r?\n---\r?\n/);
  if (!m) return { fm: "", body: text };
  return { fm: m[1], body: text.slice(m[0].length) };
}

function fmValue(fm, key) {
  const m = fm.match(new RegExp(`^${key}:\\s*"?(.*?)"?\\s*$`, "m"));
  return m ? m[1].replace(/\\"/g, '"') : "";
}

function postDate(lines, created) {
  // строка вида «03 окт в 01:24» или «3 окт 2025 в 12:00» в шапке поста
  for (const line of lines.slice(0, 40)) {
    const m = line.trim().match(/^(\d{1,2})\s+([а-я]{3})[а-я]*\.?(?:\s+(\d{4}))?\s+в\s+\d{1,2}:\d{2}$/i);
    if (!m) continue;
    const month = MONTHS[m[2].toLowerCase()];
    if (!month) continue;
    const ref = created ? new Date(created) : new Date();
    let year = m[3] ? Number(m[3]) : ref.getFullYear();
    if (!m[3] && month > ref.getMonth() + 1) year -= 1;
    return `${year}-${pad(month)}-${pad(Number(m[1]))}`;
  }
  return created || new Date().toISOString().slice(0, 10);
}

function safeName(s) {
  return s.replace(/[\\/:*?"<>|]/g, "-").replace(/\s+/g, " ").trim().slice(0, 120);
}

function clean(text) {
  const { fm, body } = splitFrontmatter(text);
  const title = fmValue(fm, "title");
  const url = fmValue(fm, "source");
  const created = fmValue(fm, "created");
  let lines = body.split(/\r?\n/).filter((l) => !/^\s*<svg[\s>]/.test(l));

  const date = postDate(lines, created);

  // всё до заголовка статьи — шапка сайта
  const start = lines.findIndex((l) => /^#{1,3}\s/.test(l) && title && l.replace(/^#+\s*/, "").trim() === title.trim());
  if (start >= 0) lines = lines.slice(start + 1);

  // подвал с уровнями подписки и комментариями
  const end = lines.findIndex((l) => FOOTER_MARKERS.some((re) => re.test(l.trim())));
  if (end >= 0) lines = lines.slice(0, end);

  const content = lines.join("\n").replace(/\n{3,}/g, "\n\n").trim();
  // без блока свойств и без даты в имени — только заголовок и текст
  const header = `# ${title}\n\n`;
  return { name: `${safeName(title)}.md`, text: header + content + "\n", title, date, url };
}

function main() {
  if (!fs.existsSync(SRC)) { console.log("Папки Clippings нет — новых статей нет."); require("./organize-escaped-ai.js"); return; }
  fs.mkdirSync(DST, { recursive: true });
  let moved = 0, skipped = 0, other = 0;
  for (const file of fs.readdirSync(SRC).filter((f) => f.endsWith(".md"))) {
    const full = path.join(SRC, file);
    const raw = fs.readFileSync(full, "utf8");
    if (!raw.includes(SOURCE_MARK)) { other++; continue; }
    const out = clean(raw);
    const target = path.join(DST, out.name);
    if (fs.existsSync(target)) { console.log(`Уже есть, пропускаю: ${out.name}`); skipped++; continue; }
    fs.writeFileSync(target, out.text, "utf8");
    if (fs.readFileSync(target, "utf8").length < 200) { console.log(`Подозрительно короткий результат, исходник оставлен: ${file}`); continue; }
    fs.unlinkSync(full);
    console.log(`✓ ${out.name}  (${Math.round(raw.length / 1024)} КБ → ${Math.round(out.text.length / 1024)} КБ)`);
    moved++;
  }
  console.log(`Готово: перенесено ${moved}, уже было ${skipped}, не с Boosty (оставлены) ${other}.`);
  // разложить по разделам автора и обновить оглавление
  require("./organize-escaped-ai.js");
}

main();

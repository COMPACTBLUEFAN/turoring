#!/usr/bin/env node
/**
 * check-demo.mjs — приёмка интерактивного демо из хранилища.
 *
 * Что проверяет (по Шаблоны/Демо.md, разделы 4 и 6):
 *   1. страница открывается и не падает;
 *   2. в консоли нет ошибок (предупреждения показываются, но не валят проверку);
 *   3. страница полностью офлайновая: ни одного запроса не к file:// (ловит CDN и внешние шрифты);
 *   4. скриншоты в тёмной теме, светлой теме и на ширине телефона (~400 px);
 *   5. нет горизонтальной прокрутки на ширине телефона.
 *
 * Запуск:
 *   node .scripts/check-demo.mjs "Материалы/Демо/<файл>.html" [папка-для-скриншотов]
 *
 * Зависимость (playwright) стоит вне хранилища, в %LOCALAPPDATA%\dsh-tools\demo-check —
 * хранилище остаётся чистым, Obsidian не видит node_modules.
 */
import { createRequire } from "node:module";
import { mkdirSync, existsSync } from "node:fs";
import { resolve, join, basename } from "node:path";
import { pathToFileURL } from "node:url";

const TOOLS = join(process.env.LOCALAPPDATA, "dsh-tools", "demo-check");
const require = createRequire(join(TOOLS, "package.json"));
let chromium;
try {
  ({ chromium } = require("playwright"));
} catch (e) {
  console.error("Не найден playwright в " + TOOLS);
  console.error("Поставь:  cd \"" + TOOLS + "\" && npm i playwright");
  process.exit(2);
}

const target = process.argv[2];
if (!target) {
  console.error("Укажи путь к HTML-демо: node .scripts/check-demo.mjs \"Материалы/Демо/....html\"");
  process.exit(2);
}
const vault = resolve(process.cwd());
const file = resolve(vault, target);
if (!existsSync(file)) { console.error("Файла нет: " + file); process.exit(2); }

// Скриншоты по умолчанию кладём ВНЕ хранилища: это служебные доказательства приёмки,
// а не материалы обучения, и в Obsidian им делать нечего. Третий аргумент — свой путь,
// если снимки нужны именно в хранилище.
const outDir = process.argv[3]
  ? resolve(vault, process.argv[3])
  : join(process.env.LOCALAPPDATA, "dsh-tools", "demo-check", "shots", basename(file, ".html"));
mkdirSync(outDir, { recursive: true });

const problems = [];
const warnings = [];
const shots = [];

// По умолчанию — настоящий (headed) браузер: в headless-сборке Chromium
// CSS-анимации не тикают, и снимки врут (элемент с анимацией прозрачности
// выглядит невидимым). Для быстрой проверки без окна: DEMO_CHECK_HEADLESS=1.
const HEADLESS = process.env.DEMO_CHECK_HEADLESS === "1";
const browser = await chromium.launch({ headless: HEADLESS });

async function open(width, height, theme) {
  const ctx = await browser.newContext({ viewport: { width, height }, deviceScaleFactor: 1 });
  const page = await ctx.newPage();
  const consoleErrors = [];
  const consoleWarns = [];
  const external = [];
  page.on("console", m => {
    if (m.type() === "error") consoleErrors.push(m.text());
    else if (m.type() === "warning") consoleWarns.push(m.text());
  });
  page.on("pageerror", e => consoleErrors.push("pageerror: " + e.message));
  page.on("request", r => {
    const u = r.url();
    if (!u.startsWith("file://") && !u.startsWith("data:") && !u.startsWith("blob:")) external.push(u);
  });
  await page.goto(pathToFileURL(file).href, { waitUntil: "load" });
  if (theme) {
    // у страницы свой переключатель темы; жмём его, если он есть
    const btn = await page.$("#themeBtn");
    if (btn) { const want = theme === "light"; if (want) await btn.click(); }
  }
  await page.waitForTimeout(400);
  return { ctx, page, consoleErrors, consoleWarns, external };
}

// ── тёмная тема, десктоп ──
{
  const s = await open(1280, 900, "dark");
  const shot = join(outDir, "01-тёмная.png");
  await s.page.screenshot({ path: shot, fullPage: true });
  shots.push(shot);
  if (s.consoleErrors.length) problems.push("Ошибки консоли: " + s.consoleErrors.join(" | "));
  if (s.external.length) problems.push("Внешние запросы (демо должно быть офлайн): " + [...new Set(s.external)].join(" | "));
  if (s.consoleWarns.length) warnings.push("Предупреждения: " + s.consoleWarns.join(" | "));
  // есть ли вообще интерактив и главный экран
  const hasRange = await s.page.$("input[type=range]");
  if (!hasRange) problems.push("Нет ручки input[type=range] — обязательная механика «живой пересчёт»");
  await s.ctx.close();
}

// ── светлая тема ──
{
  const s = await open(1280, 900, "light");
  const shot = join(outDir, "02-светлая.png");
  await s.page.screenshot({ path: shot, fullPage: true });
  shots.push(shot);
  if (s.consoleErrors.length) problems.push("Ошибки консоли (светлая): " + s.consoleErrors.join(" | "));
  await s.ctx.close();
}

// ── телефон 400 px ──
{
  const s = await open(400, 900, "dark");
  const overflow = await s.page.evaluate(() =>
    document.documentElement.scrollWidth - document.documentElement.clientWidth);
  if (overflow > 2) problems.push("Горизонтальная прокрутка на 400 px: лишних " + overflow + " px");
  const shot = join(outDir, "03-телефон.png");
  await s.page.screenshot({ path: shot, fullPage: true });
  shots.push(shot);
  if (s.consoleErrors.length) problems.push("Ошибки консоли (телефон): " + s.consoleErrors.join(" | "));
  await s.ctx.close();
}

// ── прогон миссии: довести ручку до упора и посмотреть, что финал появляется ──
{
  const s = await open(1280, 900, "dark");
  const info = await s.page.evaluate(() => {
    const r = document.querySelector("input[type=range]");
    if (!r) return null;
    const out = {};
    const set = v => { r.value = String(v); r.dispatchEvent(new Event("input", { bubbles: true })); };
    set(r.min); out.atMin = document.body.innerText.length;
    set(r.max); out.atMax = document.body.innerText.length;
    return out;
  });
  if (info) {
    await s.page.waitForTimeout(600);   // дать анимациям и пересчёту устояться
    const shot = join(outDir, "04-ручка-в-максимуме.png");
    await s.page.screenshot({ path: shot, fullPage: true });
    shots.push(shot);
  }
  await s.ctx.close();
}

await browser.close();

console.log("Демо: " + target);
console.log("Скриншоты (" + shots.length + "):");
for (const s of shots) console.log("  " + s);
if (warnings.length) { console.log("Предупреждения:"); for (const w of warnings) console.log("  " + w); }
if (problems.length) {
  console.log("ПРОБЛЕМЫ:");
  for (const p of problems) console.log("  ✗ " + p);
  process.exit(1);
}
console.log("Проверки пройдены: консоль чистая, внешних запросов нет, прокрутки на телефоне нет.");

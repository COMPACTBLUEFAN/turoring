"""Только чтение: сверка активного расписания, трекера и сводки Фазы 0."""
from pathlib import Path
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]


def read(name):
    return (ROOT / name).read_text(encoding="utf-8")


def section(text, start, end):
    return text.split(start, 1)[1].split(end, 1)[0]


def main():
    schedule = read("Фаза 0/РАСПИСАНИЕ.md")
    tracker = read("Фаза 0/ТРЕКЕР.md")
    core = section(tracker, "### AIN", "## 📦")
    interests = section(tracker, "## 🟨 Интересы", "## 🧪 Проекты интересов")
    errors = []
    planned = {}
    week = None
    for line in schedule.splitlines():
        match = re.match(r"## Неделя (\d+)", line)
        if match:
            week = int(match[1])
        match = re.match(r"\| `(0\.[A-Z]+\.\d+)` \| ([^|]+)\|", line)
        if match and week:
            code, title = match.groups()
            if code in planned:
                errors.append(f"Дубль в расписании: {code}")
            planned[code] = (week, title.strip())
    rows = re.findall(r"^- \[([x ])\] `(0\.[A-Z]+\.\d+)` (.+)$", core, re.M)
    codes = [code for _, code, _ in rows]
    if len(set(codes)) != len(codes):
        errors.append("Дубли кодов в активном ядре трекера")
    if set(codes) != set(planned):
        errors.append(f"Состав ядра расходится: {sorted(set(codes) ^ set(planned))}")
    for status, code, description in rows:
        if status == "x":
            continue  # История прохождения не переписывается по будущему плану.
        match = re.match(r"(.*?) · нед\. (\d+)", description)
        if not match:
            errors.append(f"Не разобрана активная строка: {code}")
        elif code in planned and planned[code] != (int(match[2]), match[1]):
            errors.append(f"Название/неделя {code}: трекер ≠ расписание")
    ir = re.findall(r"^- \[([x ])\] `(0\.[A-Z]+\.\d+)` (.+)$", interests, re.M)
    current_ir = [r for r in ir if "переходит в Фазу" not in r[2]]
    interest_plan = {}
    for line in section(schedule, "## 🟨 Интересы Фазы 0", "## 🏁").splitlines():
        match = re.match(r"\| (\d+) \|", line)
        if match:
            for code in re.findall(r"`(0\.[A-Z]+\.\d+)`", line):
                if code in interest_plan:
                    errors.append(f"Дубль интереса в расписании: {code}")
                interest_plan[code] = int(match[1])
    if set(interest_plan) != {r[1] for r in current_ir}:
        errors.append("Состав интересов текущей фазы расходится")
    for status, code, description in current_ir:
        match = re.search(r"нед\. (\d+)", description)
        if status != "x" and (not match or interest_plan.get(code) != int(match[1])):
            errors.append(f"Неделя интереса расходится: {code}")
    for label, actual in [
        ("Занятий закрыто", (sum(r[0] == "x" for r in rows), len(rows))),
        ("Интересов закрыто", (sum(r[0] == "x" for r in current_ir), len(current_ir))),
    ]:
        match = re.search(rf"\| {label} \| (\d+) / (\d+)", tracker)
        if not match or tuple(map(int, match.groups())) != actual:
            errors.append(f"{label}: должно быть {actual[0]} / {actual[1]}")
    grades = []
    for path in (ROOT / "Фаза 0/Недели").glob("*/Сессия *.md"):
        matches = re.findall(r"^\*\*Оценка(?: сессии)?:\*?\*?\s*(\d+)/10", path.read_text(encoding="utf-8"), re.M)
        if len(matches) > 1:
            errors.append(f"Неоднозначна итоговая оценка: {path.name}")
        elif matches:
            grades.append(int(matches[0]))
    if grades:
        match = re.search(r"\| Средний балл \| (\d+[.,]\d+) \((\d+) сесс", tracker)
        expected = round(sum(grades) / len(grades), 1)
        if not match or float(match[1].replace(",", ".")) != expected or int(match[2]) != len(grades):
            errors.append(f"Средний балл: {expected:.1f}, проверенных сессий: {len(grades)}")
    for item in errors:
        print("ОШИБКА:", item)
    if not errors:
        print(f"OK: ядро {len(rows)}, интересы текущей фазы {len(current_ir)}, проверенные сессии {len(grades)}; состав, недели, названия и сводка согласованы.")
        print("Вручную сверить: даты текущей недели, незакрытые работы, карточку полигона и связанные заметки. Скрипт не проверяет ответы и не выставляет оценки.")
    return bool(errors)


if __name__ == "__main__":
    raise SystemExit(main())

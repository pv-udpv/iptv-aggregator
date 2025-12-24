# Automated Error Handling System

## Overview

Автоматическая система обработки ошибок с AI-анализом и предложениями по исправлению.

**Компоненты:**
1. `pullrun.sh` - запуск команд с error handling
2. `.github/workflows/error-handler.yml` - GitHub Actions workflow
3. `.github/copilot-error-handler.md` - AI агент конфигурация

**Модель:** GPT-4o-mini (бесплатная, эффективная для анализа ошибок)

---

## Как это работает?

### 1️⃣ Команда падает

```bash
./pullrun.sh python scripts/broken_script.py
# ✗ Failed (exit 1)
```

### 2️⃣ pullrun.sh автоматически:

1. **Создаёт error branch**
   ```
   error/20251224-143000-abc12345
   ```

2. **Сохраняет логи**
   - `.pullrun_logs/run-20251224-143000.log` - полный output
   - `.pullrun_logs/ERROR-20251224-143000.md` - error report

3. **Коммитит в error branch**
   ```
   error: python scripts/broken_script.py failed
   Exit code: 1
   ```

4. **Создаёт GitHub Issue**
   - Title: `[pullrun] python scripts/broken_script.py`
   - Labels: `bug`, `pullrun-error`, `automated`
   - Body: команда, exit code, последние 30 строк лога

### 3️⃣ GitHub Actions автоматически:

1. **Триггерится** при создании issue с label `pullrun-error`

2. **Анализирует ошибку** (pattern matching):
   - `ModuleNotFoundError` → нехватает пакета
   - `FileNotFoundError` → файл не найден
   - `AttributeError` → null check
   - `ValidationError` → Pydantic schema
   - `sqlite3.OperationalError` → DB issue
   - `ConnectError` → network

3. **Постит комментарий** с:
   - Root cause
   - Error type
   - Affected file
   - Suggested fix (код или команда)
   - Next steps

---

## Пример

### Input (команда падает)

```bash
./pullrun.sh python scripts/parse_epg_pydantic.py
```

**Error:**
```
ModuleNotFoundError: No module named 'pydantic_xml'
```

### Output (автоматический комментарий в issue)

```markdown
## 🤖 Error Analysis (GPT-4o-mini)

**Root Cause:** Missing Python package: pydantic_xml

**Error Type:** `ImportError`

**Affected File:** `scripts/parse_epg_pydantic.py`

**Exit Code:** 1

---

## 🔧 Recommended Fix

Install missing package:

\`\`\`bash
source .venv/bin/activate
uv pip install pydantic-xml
\`\`\`

---

## 📋 Next Steps

- [ ] Review error branch: \`git checkout error/20251224-143000-abc12345\`
- [ ] Apply suggested fix locally
- [ ] Test: \`./pullrun.sh python scripts/parse_epg_pydantic.py\`
- [ ] Merge fix: \`git checkout main && git merge error/20251224-143000-abc12345\`
- [ ] Close this issue

---

*Auto-analyzed by Copilot Error Handler Agent*
*Model: gpt-4o-mini (free tier)*
```

---

## Использование

### Обычный запуск (с error handling)

```bash
./pullrun.sh python scripts/download_epg.py
```

Если команда падает:
- ✅ Error branch created
- ✅ Logs committed
- ✅ GitHub issue created
- ✅ Automated analysis posted

### Отключить error handling

```bash
PULLRUN_NO_ERROR_HANDLING=1 ./pullrun.sh python scripts/test.py
```

### Ручной триггер анализа

Если issue уже существует, можно триггернуть анализ:

```
@copilot analyze
```

(комментарий в issue)

---

## Поддерживаемые типы ошибок

✅ **ImportError / ModuleNotFoundError**
- Нехватает пакета
- Fix: `uv pip install <package>`

✅ **FileNotFoundError**
- Файл не найден
- Fix: проверить путь, запустить prerequisite шаги

✅ **AttributeError**
- Обращение к None
- Fix: добавить null check

✅ **ValidationError (Pydantic)**
- Неверная схема данных
- Fix: проверить модель, добавить Optional

✅ **sqlite3.OperationalError**
- Проблема с БД
- Fix: пересоздать БД, запустить migrations

✅ **httpx.ConnectError / Network errors**
- Проблема с сетью
- Fix: проверить подключение, retry logic

---

## Файлы и структура

```
.
├── pullrun.sh                           # главный скрипт
├── .pullrun_logs/
│   ├── run-*.log                       # полные логи запусков
│   └── ERROR-*.md                      # error reports
├── .github/
│   ├── workflows/
│   │   └── error-handler.yml          # автоматический анализ
│   └── copilot-error-handler.md       # AI агент конфиг
└── ERROR_HANDLING.md                  # этот файл
```

---

## Workflow

### Автоматический (рекомендуется)

1. Запусти команду: `./pullrun.sh <command>`
2. Если падает → issue создаётся автоматически
3. GitHub Actions анализирует и постит fix
4. Примени fix локально
5. Тест: `./pullrun.sh <command>`
6. Merge: `git checkout main && git merge <error-branch>`
7. Close issue

### Ручной

1. Посмотри логи: `cat .pullrun_logs/ERROR-*.md`
2. Checkout error branch: `git checkout error/...`
3. Исправь
4. Тест
5. Merge

---

## Configuration

### Environment Variables

```bash
# Отключить error handling
export PULLRUN_NO_ERROR_HANDLING=1

# Или разово
PULLRUN_NO_ERROR_HANDLING=1 ./pullrun.sh <command>
```

### GitHub CLI

Для создания issues нужен `gh` CLI:

```bash
# Install
brew install gh
# or
apt install gh

# Auth
gh auth login
```

---

## Преимущества

✅ **Бесплатный AI** - GPT-4o-mini, не тратит premium requests  
✅ **Автоматический** - нет ручных шагов  
✅ **Трекинг** - все ошибки в issues  
✅ **Error branches** - легко исправлять  
✅ **Pattern matching** - распознаёт типичные ошибки  
✅ **Concrete fixes** - не абстрактные советы, а конкретные команды/код  

---

## Ограничения

⚠️ **Не выполняет код** - только анализ и предложения  
⚠️ **Pattern-based** - может не распознать новые типы ошибок  
⚠️ **Требует gh CLI** - для создания issues  

---

## Future Enhancements

- [ ] Авто-PR для тривиальных фиксов
- [ ] Slack/Discord уведомления
- [ ] Статистика ошибок (dashboard)
- [ ] ML-based error classification
- [ ] Интеграция с Sentry/Rollbar

---

**Last updated:** 2025-12-24

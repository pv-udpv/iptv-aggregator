# GitHub Actions Workflows

Automated CI/CD pipeline for IPTV Aggregator.

## 🔄 Workflows

### 1. Demo Run (`demo.yml`)

**Triggers:**
- Push to `main` or `feat/**` branches
- Pull requests to `main`
- Manual dispatch

**What it does:**
1. ✅ Checks out code
2. ✅ Sets up Python 3.12
3. ✅ Installs dependencies
4. ✅ Runs `demo.py`
5. ✅ Displays statistics
6. ✅ Uploads artifacts (M3U, JSON, DB)
7. ✅ Comments on PR with results

**Artifacts:**
- `iptv-demo-output` (7 days retention)
  - `demo.m3u`
  - `demo_metadata.json`
  - `demo.db`

**Manual trigger:**
```bash
gh workflow run demo.yml
```

---

### 2. Tests (`test.yml`)

**Triggers:**
- Push to `main`, `develop`, `feat/**`
- Pull requests to `main`, `develop`

**Jobs:**

#### Lint & Type Check
- Ruff linter
- Ruff formatter check
- MyPy type checking

#### Unit Tests
- Matrix: Python 3.11, 3.12
- Pytest with coverage
- Upload to Codecov

**Status:** 🚧 Tests not implemented yet (continuing on error)

---

### 3. Scheduled Refresh (`schedule.yml`)

**Triggers:**
- Cron: Every 6 hours (`0 */6 * * *`)
- Manual dispatch

**What it does:**
1. ✅ Runs `demo.py` to refresh data
2. ✅ Generates markdown report
3. ✅ Uploads artifacts (30 days retention)
4. ✅ Sends notification on failure

**Artifacts:**
- `scheduled-refresh-{run_number}`
  - `output/` directory
  - `report.md` with statistics

**Manual trigger:**
```bash
gh workflow run schedule.yml
```

---

## 📊 PR Comment Example

When a PR is created, the bot automatically comments:

```markdown
## 🎬 Demo Execution Results

✅ Successfully executed IPTV Aggregator demo!

### 📊 Statistics
- Total Channels: 50
- Version: 1.0

### 📁 Artifacts
Download generated files from the workflow artifacts:
- `demo.m3u` - M3U8 playlist
- `demo_metadata.json` - Channel metadata
- `demo.db` - SQLite database

### 🔍 Sample Channels
- BBC One (UK) - 3 stream(s)
- CNN (US) - 2 stream(s)
- Sky News (UK) - 1 stream(s)
- Al Jazeera (QA) - 2 stream(s)
- France 24 (FR) - 2 stream(s)

---
🤖 Automated by GitHub Actions
```

---

## 🔧 Setup

### Required Secrets

No secrets required for basic workflows.

**Optional for notifications:**
- `SLACK_WEBHOOK` - Slack webhook URL
- `TELEGRAM_BOT_TOKEN` - Telegram bot token
- `TELEGRAM_CHAT_ID` - Telegram chat ID

### Branch Protection

Recommended settings:
```yaml
required_status_checks:
  - Demo Run
  - Lint & Type Check
require_branches_to_be_up_to_date: true
```

---

## 💻 Local Testing

### Test workflow locally with Act

```bash
# Install act
brew install act  # macOS

# Run demo workflow
act push -W .github/workflows/demo.yml

# Run tests
act push -W .github/workflows/test.yml
```

---

## 📅 Scheduled Runs

| Workflow | Schedule | Retention |
|----------|----------|----------|
| Scheduled Refresh | Every 6h | 30 days |

**Cron expression:** `0 */6 * * *`
- 00:00 UTC
- 06:00 UTC
- 12:00 UTC
- 18:00 UTC

---

## 📈 Monitoring

### View workflow runs
```bash
gh run list
gh run view <run-id>
gh run watch
```

### Download artifacts
```bash
gh run download <run-id>
```

### Logs
```bash
gh run view <run-id> --log
```

---

## 🐛 Issue Templates

### Bug Report
Location: `.github/ISSUE_TEMPLATE/bug_report.yml`

Fields:
- Description
- Steps to reproduce
- Expected behavior
- Logs
- Python version
- Operating system

### Feature Request
Location: `.github/ISSUE_TEMPLATE/feature_request.yml`

Fields:
- Feature description
- Motivation
- Alternatives
- Additional context

---

## 🚀 Future Enhancements

- [ ] Deploy to GitHub Pages
- [ ] Publish to PyPI
- [ ] Docker image build & push
- [ ] Performance benchmarks
- [ ] Security scanning (Dependabot)
- [ ] CodeQL analysis

---

**Status:** ✅ Active | **Last Updated:** 2025-12-24
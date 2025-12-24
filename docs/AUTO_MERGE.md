# 🤖 Intelligent Auto-Merge Workflow

Automatically merges PRs when all safety checks pass.

## ✨ Features

### Multi-Stage Validation
- ✅ **CI/CD checks**: All status checks must pass
- ✅ **Code reviews**: At least 1 approval for main/master
- ✅ **Merge conflicts**: Automatic conflict detection
- ✅ **Draft status**: Blocks draft PRs
- ✅ **Change requests**: Blocks if changes requested

### Smart Merge Strategies
- **Squash** (default): Clean commit history for feature branches
- **Merge**: Preserves full commit history
- **Rebase**: Linear history without merge commits

### Safety Features
- **Dry-run mode**: Test without actual merge
- **Protected branches**: Never auto-deletes main/master/develop
- **Fork safety**: Won't delete branches from forks
- **Detailed logging**: Full audit trail in workflow runs

## 🚀 Usage

### Method 1: Auto-merge Label (Recommended)

```bash
# Enable auto-merge for a PR
gh pr edit <pr-number> --add-label "auto-merge"

# The workflow will automatically:
# 1. Wait for all CI checks to complete
# 2. Validate reviews and mergeable state
# 3. Merge when all conditions met
# 4. Delete the merged branch
# 5. Add confirmation comment
```

**Example**:
```bash
gh pr edit 4 --add-label "auto-merge"
# → PR #4 will auto-merge when:
#    - All CI checks pass (✅)
#    - At least 1 approval (✅)
#    - No merge conflicts (✅)
```

### Method 2: Manual Trigger

```bash
# Merge a specific PR immediately
gh workflow run auto-merge.yml \
  --repo pv-udpv/iptv-aggregator \
  -f pr_number=4 \
  -f dry_run=false

# Dry-run (test without merging)
gh workflow run auto-merge.yml \
  --repo pv-udpv/iptv-aggregator \
  -f pr_number=4 \
  -f dry_run=true
```

### Method 3: Automatic (Event-Driven)

Workflow triggers automatically on:
- ✅ **PR review approval** → checks if ready to merge
- ✅ **CI check completion** → validates and merges if label present
- ✅ **Label addition** → immediate validation

## 🛡️ Safety Checks

### Required Conditions

| Check | Description | Blocks Merge If |
|-------|-------------|----------------|
| **PR State** | Must be open | closed/merged |
| **Draft Status** | Must not be draft | `draft: true` |
| **Mergeable State** | No conflicts | `mergeable_state: dirty/blocked` |
| **CI Checks** | All checks pass | Any check failed/pending |
| **Reviews** | ≥1 approval (for main) | Changes requested or no approvals |
| **Auto-merge Label** | Must have label OR manual trigger | Label missing |

### Bypass Conditions

- **Owner's PRs**: Repo owner can auto-merge own PRs without approval
- **Feature branches**: Approval not required for non-main branches
- **Manual trigger**: Bypasses label requirement

## 📊 Merge Strategies

### Squash (Default)

**When to use**: Feature branches, bug fixes

```yaml
# Clean single commit in main
feat: Add dataset quality validation (#5)

Implements Phase 1 monitoring with DuckDB analytics.
```

**Pros**:
- Clean history
- Easy revert
- No WIP commits in main

**Cons**:
- Loses granular commit history

### Merge Commit

**When to use**: Important features, releases

```yaml
# Preserves all commits
Merge pull request #4 from pv-udpv/feat/master-dataset-builder
  - commit 1
  - commit 2
  - commit 3
```

**Pros**:
- Full history preservation
- Clear merge points

**Cons**:
- Cluttered history with merge commits

### Rebase

**When to use**: Linear history preference

```yaml
# Applies commits directly to base
feat: implement IPTVPortal auth
feat: add Parquet export
feat: add validation workflow
```

**Pros**:
- Linear history
- No merge commits

**Cons**:
- Rewrites history (changes SHAs)
- Harder to revert multi-commit features

## 📝 Examples

### Auto-merge PR #4 (Master Dataset Builder)

```bash
# 1. Add auto-merge label
gh pr edit 4 --add-label "auto-merge"

# 2. Workflow will:
#    - Wait for CI checks (build-dataset.yml)
#    - Validate IPTVPortal auth works
#    - Check mergeable state
#    - Squash merge to main
#    - Delete feat/master-dataset-builder branch
#    - Comment on PR with merge SHA

# 3. Monitor progress
gh run watch --repo pv-udpv/iptv-aggregator
```

### Test auto-merge (dry-run)

```bash
# Simulate merge without actual execution
gh workflow run auto-merge.yml \
  -f pr_number=4 \
  -f dry_run=true

# Check logs
gh run view <run-id> --log

# Output:
# 🧪 DRY RUN MODE - Would merge PR #4
# Strategy: squash
# Head SHA: eb1e089...
# ✅ All checks passed, merge would succeed!
```

### Batch auto-merge multiple PRs

```bash
# Add label to multiple PRs
for pr in 4 5; do
  gh pr edit $pr --add-label "auto-merge"
done

# Workflow will process each PR independently
```

## 🔧 Configuration

### Customize Merge Strategy

Edit `.github/workflows/auto-merge.yml`:

```yaml
- name: Determine merge strategy
  id: strategy
  run: |
    # Change default from squash to merge
    STRATEGY="merge"  # or "rebase"
    echo "strategy=$STRATEGY" >> $GITHUB_OUTPUT
```

### Customize Review Requirements

Edit safety checks section:

```javascript
// Require 2 approvals instead of 1
if (approvals < 2 && !isOwner) {
  core.setFailed('At least 2 approvals required');
  return;
}
```

### Add Custom Checks

```yaml
- name: Custom validation
  run: |
    # Example: Check PR title format
    if [[ ! "${{ github.event.pull_request.title }}" =~ ^(feat|fix|docs): ]]; then
      echo "❌ PR title must start with feat:|fix:|docs:"
      exit 1
    fi
```

## 🚨 Troubleshooting

### "No auto-merge label" → Workflow skips

**Solution**: Add label
```bash
gh pr edit <pr-number> --add-label "auto-merge"
```

### "Failed CI checks" → Merge blocked

**Solution**: Fix failing tests, then workflow auto-retries
```bash
# Check which checks failed
gh pr checks <pr-number>

# Re-run failed checks
gh run rerun <run-id>
```

### "No approvals found" → Merge blocked

**Solution**: Get approval OR use manual trigger
```bash
# Request review
gh pr review <pr-number> --approve

# OR manual merge (bypasses approval)
gh workflow run auto-merge.yml -f pr_number=<pr-number>
```

### "PR has merge conflicts" → Merge blocked

**Solution**: Rebase or update branch
```bash
# Update PR branch with main
gh pr update-branch <pr-number>

# OR manually rebase
git checkout feat/branch
git rebase main
git push --force
```

## 📊 Monitoring

### Check auto-merge status

```bash
# List auto-merge workflow runs
gh run list --workflow=auto-merge.yml

# View specific run
gh run view <run-id>

# Download logs
gh run view <run-id> --log > auto-merge.log
```

### Workflow notifications

**On success**:
- ✅ Comment added to PR: "Auto-merged via intelligent merge workflow"
- ✅ Branch automatically deleted
- ✅ Merge commit SHA recorded

**On failure**:
- ❌ Comment added to PR: "Auto-merge failed"
- ❌ Error details in comment
- ❌ Manual merge required

## 🔗 Integration with Other Workflows

### Chain with validation

```yaml
# In build-dataset.yml
- name: Add auto-merge label on success
  if: success()
  run: |
    gh pr edit ${{ github.event.pull_request.number }} \
      --add-label "auto-merge"
```

### Prevent auto-merge with label

```yaml
# Block auto-merge if "do-not-merge" label present
- name: Check blocking labels
  run: |
    if gh pr view ${{ github.event.pull_request.number }} \
       --json labels -q '.labels[].name' | grep -q "do-not-merge"; then
      echo "do-not-merge label present, blocking auto-merge"
      exit 1
    fi
```

## 📚 Best Practices

### When to Use Auto-Merge

✅ **Good candidates**:
- Dependency updates (Dependabot PRs)
- Automated refactoring (Copilot PRs)
- Well-tested feature branches
- Documentation updates
- CI/CD improvements

❌ **Avoid for**:
- Breaking changes without migration plan
- PRs touching critical security code
- Large architectural changes
- First-time contributor PRs (manual review recommended)

### Security Considerations

- **Token permissions**: Workflow uses `GITHUB_TOKEN` with write access
- **Branch protection**: Enable for main/master in repo settings
- **Required reviews**: Configure in branch protection rules
- **Status checks**: Mark critical checks as required

### Performance Tips

- **Batch merges**: Add label to multiple PRs at once
- **Parallel workflows**: Auto-merge runs independently per PR
- **Dry-run first**: Test with new repos before production use

## 📦 Related Workflows

- **validate-dataset.yml**: Quality checks before merge
- **build-dataset.yml**: Dataset generation (triggers on merge)
- **test.yml**: Lint and type checks

## 🔗 References

- [GitHub Actions: pull_request_review event](https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows#pull_request_review)
- [GitHub API: Merge PR](https://docs.github.com/en/rest/pulls/pulls#merge-a-pull-request)
- [Branch protection rules](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)

---

**Status**: 🚀 Production Ready | **Trigger**: Label or Manual | **Safety**: Multi-stage validation

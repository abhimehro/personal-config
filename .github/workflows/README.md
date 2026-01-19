# GitHub Actions Workflows

This repository uses several GitHub Actions workflows for automation and code quality.

## Workflows

### Core Workflows
- **label.yml** - Automatically labels pull requests based on changed files
- **stale.yml** - Manages stale issues and pull requests
- **summary.yml** - Generates PR summaries
- **crda.yml** - Security scanning for dependencies
- **code-quality.yml** - Code quality and complexity checks for shell scripts and Python files

### Gemini AI Workflows (Optional)

The following workflows use Google's Gemini AI for automated code review, issue triage, and general assistance. These workflows are **optional** and will only run if authentication is properly configured.

- **gemini-dispatch.yml** - Routes Gemini requests to appropriate workflows
- **gemini-review.yml** - Provides AI-powered code reviews on pull requests
- **gemini-invoke.yml** - General-purpose Gemini invocation
- **gemini-triage.yml** - Automated issue labeling and triage
- **gemini-scheduled-triage.yml** - Scheduled issue triage (runs hourly)

## Gemini Workflow Setup (Optional)

To enable the Gemini AI workflows, you need to configure at least one authentication method. These workflows will automatically skip if no authentication is configured.

### Option 1: Gemini API Key (Recommended for personal use)

1. Get a Gemini API key from [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Add it as a repository secret:
   - Go to repository **Settings** → **Secrets and variables** → **Actions**
   - Click **New repository secret**
   - Name: `GEMINI_API_KEY`
   - Value: Your API key

### Option 2: Google API Key (Vertex AI)

1. Create a Google Cloud project and enable Vertex AI
2. Generate an API key
3. Add repository secrets and variables:
   - Secret: `GOOGLE_API_KEY`
   - Variable: `GOOGLE_GENAI_USE_VERTEXAI` (set to `true`)
   - Variable: `GOOGLE_CLOUD_LOCATION` (e.g., `us-central1`)
   - Variable: `GOOGLE_CLOUD_PROJECT` (your GCP project ID)

### Option 3: Workload Identity Federation (Recommended for organizations)

1. Set up GCP Workload Identity Federation for GitHub Actions
2. Add repository variables:
   - `GCP_WIF_PROVIDER` - Your workload identity provider
   - `GCP_PROJECT_ID` - Your GCP project ID
   - `SERVICE_ACCOUNT_EMAIL` - Service account email
   - `GOOGLE_CLOUD_LOCATION` - GCP region

### Optional Configuration

Additional variables you can configure:

- `GEMINI_CLI_VERSION` - Specific version of Gemini CLI (default: latest)
- `GEMINI_MODEL` - Model to use (e.g., `gemini-2.0-flash-exp`)
- `GEMINI_DEBUG` - Enable debug logging (true/false)
- `UPLOAD_ARTIFACTS` - Upload workflow artifacts (true/false)

## Workflow Behavior

- **Without Authentication**: Gemini workflows will automatically skip (status: skipped)
- **With Authentication**: Gemini workflows will run automatically on:
  - New pull requests (review)
  - New/reopened issues (triage)
  - When mentioned with `@gemini-cli` in comments
  - Hourly scheduled triage (if configured)

## Testing

After configuring authentication, you can test the workflows by:

1. Opening a new pull request
2. Opening a new issue
3. Commenting `@gemini-cli /review` on a pull request
4. Commenting `@gemini-cli /triage` on an issue

## Disabling Gemini Workflows

Gemini workflows automatically skip when authentication is not configured, so no action is needed to disable them. If you want to completely remove them:

```bash
rm .github/workflows/gemini-*.yml
```

## Troubleshooting

### Workflows are skipped
This is expected behavior when authentication is not configured. The workflows will show as "skipped" rather than "failed".

### Authentication errors
Check that:
- Secrets are properly named (case-sensitive)
- API keys are valid and not expired
- GCP project has the necessary APIs enabled
- Service account has required permissions

### For more information
- [Gemini API Documentation](https://ai.google.dev/docs)
- [GitHub Actions Secrets](https://docs.github.com/en/actions/security-guides/encrypted-secrets)
- [Workload Identity Federation](https://cloud.google.com/iam/docs/workload-identity-federation)

## Code Quality Workflow

The **code-quality.yml** workflow performs automated code quality and complexity checks to prevent overly complex methods and scripts. This workflow was added to prevent issues similar to those found by CodeFactor in other repositories.

### What It Checks

#### Shell Scripts (`.sh`, `.bash`)
1. **ShellCheck Analysis** - Runs ShellCheck on all shell scripts to find bugs and potential issues
2. **Script Length** - Warns when scripts exceed 200 lines
3. **Complexity** - Encourages refactoring large scripts into smaller, more maintainable functions

#### Python Files (`.py`)
1. **Cyclomatic Complexity** - Measures code complexity using Radon
   - Threshold: Warns when function complexity > 10
   - Scale: 1-5 (simple), 6-10 (moderate), 11-20 (complex), 21+ (very complex)
2. **Maintainability Index** - Calculates how easy code is to maintain
   - Threshold: Warns when MI < 20
   - Scale: ≥20 (maintainable), 10-19 (moderate), <10 (difficult)
3. **File Length** - Warns when files exceed 300 lines
4. **Trunk Check** - Runs configured linters (ruff, bandit, black, isort)

### When It Runs

- **Pull Requests** - Automatically on PRs that modify `.sh`, `.py`, or files in `scripts/`, `tests/`, `controld-system/`, `windscribe-controld/`
- **Push to main** - On commits to main/master branch
- **Manual** - Can be triggered manually via workflow_dispatch

### Understanding Results

The workflow provides **warnings**, not errors. These are suggestions to improve code quality:

- **Green checkmark (✅)** - No issues found or only minor warnings
- **Warnings** - Code that exceeds thresholds but doesn't fail the build
- **Summary** - Each run provides a summary of all checks performed

### How to Fix Complexity Issues

#### For Shell Scripts:
```bash
# Before: Large monolithic script (300+ lines)
# After: Refactor into functions

# Extract reusable logic into functions
validate_input() {
    # Validation logic here
}

process_data() {
    # Processing logic here
}

# Main script just orchestrates
main() {
    validate_input
    process_data
}

main "$@"
```

#### For Python:
```python
# Before: Complex function (CC > 10)
def complex_function(data):
    if condition1:
        if condition2:
            if condition3:
                # Deep nesting...
                pass

# After: Extract and simplify
def validate_data(data):
    return condition1 and condition2 and condition3

def complex_function(data):
    if not validate_data(data):
        return
    # Simplified logic
```

### Thresholds

| Check | Threshold | Severity |
|-------|-----------|----------|
| Shell script length | >200 lines | Warning |
| Python cyclomatic complexity | >10 | Warning |
| Python maintainability index | <20 | Warning |
| Python file length | >300 lines | Warning |

These thresholds are based on industry best practices and can be adjusted in `.github/workflows/code-quality.yml`.

### Related Tools

- **Radon** - Python complexity analysis ([documentation](https://radon.readthedocs.io/))
- **ShellCheck** - Shell script static analysis ([documentation](https://www.shellcheck.net/))
- **Trunk** - Unified linter runner ([documentation](https://docs.trunk.io/))

### References

This workflow was added to prevent complex method issues similar to those found in CodeFactor analysis of related repositories. For more information, see:
- [CodeFactor Complex Method Detection](https://www.codefactor.io/docs/issues/complexity)
- [Cyclomatic Complexity Explanation](https://en.wikipedia.org/wiki/Cyclomatic_complexity)

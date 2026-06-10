# GitHub Auto-Push Configuration

## Repository
- **Owner**: `zuhair646-debug`
- **Repo**: `zuhair646-debug/zerax`
- **URL**: https://github.com/zuhair646-debug/zerax

## Credentials Location
All credentials are stored in `/app/backend/.env` (protected from git via `.gitignore`):
- `GITHUB_TOKEN` — Personal Access Token with `repo` scope
- `GITHUB_USER` — GitHub username
- `GITHUB_REPO` — Target repository name

## How to Push (for any agent)

### Auto-push after meaningful changes:
```bash
bash /app/scripts/push_to_github.sh "feat: short description of change"
```

### What this does:
1. Loads credentials from `backend/.env`
2. Sets up remote URL with embedded token (never logged or committed)
3. Stages all changes (`git add -A`)
4. Commits with the message you provide (or default "chore: automatic sync")
5. Pushes to `origin main`

## When to Push
**The user requested continuous auto-push.** Push to GitHub after:
- Any significant feature addition
- Any bug fix that's verified working
- Any major refactor
- Before calling the `finish` tool

## Important Rules
1. **NEVER commit the token to git** — it's protected by `.gitignore`, keep it that way
2. **NEVER print the full token** in user-facing output
3. If user gives a new token, replace it in `/app/backend/.env` (don't add duplicate lines)
4. If push fails due to expired token, ask user to regenerate at https://github.com/settings/tokens/new

## Verifying the Setup
```bash
# Check credentials are present (without revealing token)
grep -c "^GITHUB_" /app/backend/.env  # should output 3

# Check repo is reachable
TKN=$(grep GITHUB_TOKEN /app/backend/.env | cut -d= -f2)
curl -s -H "Authorization: token $TKN" https://api.github.com/user | python3 -c "import sys,json;print('OK' if 'login' in json.load(sys.stdin) else 'BAD')"
```

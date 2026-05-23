---
name: commit
description: >
  Create a git commit following unified commit format.
  Use when the user wants to commit changes, asks for a commit message,
  or types /commit. Analyzes staged changes and proposes an appropriate
  emoji + type + message.
allowed-tools:
  - Bash(git status:*)
  - Bash(git diff:*)
  - Bash(git log:*)
  - Bash(git add:*)
  - Bash(git commit:*)
argument-hint: "[all] [optional message hint]"
---

# Commit Skill

Create a git commit following the unified commit format.

## Format

```
<emoji> <type>: <message>
```

Message is lowercase, imperative mood, no trailing period.

## Type → Emoji Map

| Type       | Emoji | Use when...                                         |
|------------|-------|-----------------------------------------------------|
| `setup`    | 🏗️    | Project or module setup                             |
| `feat`     | ✨    | New feature or capability                           |
| `fix`      | 🐛    | Bug fix                                             |
| `refactor` | ♻️    | Code restructuring without behavior change          |
| `perf`     | ⚡    | Performance improvement                             |
| `test`     | 🧪    | Adding or updating tests                            |
| `docs`     | 📝    | Documentation only                                  |
| `style`    | 💄    | Formatting, whitespace, naming (no logic change)    |
| `chore`    | 🔧    | Build, tooling, dependencies, CI/CD                 |
| `ci`       | 👷    | CI/CD pipeline changes                              |
| `revert`   | ⏪    | Reverting a previous commit                         |
| `wip`      | 🚧    | Work in progress (avoid on main branch)             |

## Procedure

1. Check $ARGUMENTS: if it starts with `all`, set **auto-stage mode** and treat the remainder as a message hint; otherwise treat all of $ARGUMENTS as a message hint
2. Run `git status`, `git diff --cached`, and `git log --oneline -10` in parallel
3. **Staging:**
   - *Auto-stage mode*: scan the unstaged/untracked files for suspicious files (see list below). If any are found, list them and ask the user to confirm before proceeding. Otherwise run `git add -A` silently and continue
   - *Normal mode*: if nothing is staged, run `git diff HEAD` to see all changes, then ask the user whether to stage everything or let them choose
4. Determine the best type from the table above based on the diff
5. Write a message in imperative mood: "add", "fix", "remove", not "added", "fixes", "removing"
6. For a single-line message run `git commit -m "<message>"`; for commits that need a body (breaking changes, reverts) use a HEREDOC:
   ```
   git commit -m "$(cat <<'EOF'
   ✨ feat!: replace auth system

   BREAKING CHANGE: session tokens are no longer stored in cookies
   EOF
   )"
   ```

## Good Examples

```
✨ feat: add SSO login via Keycloak
🐛 fix: handle empty audio segments gracefully
♻️ refactor: extract token validation into middleware
🔧 chore: upgrade MailerSend SDK to v3
📝 docs: update WebSocket protocol documentation
🧪 test: add coverage for concurrent session handling
⚡ perf: reduce model inference latency on short segments
🏗️ setup: scaffold Newton Workflow service
```

## Bad Examples (never do these)

```
# ❌ No emoji
feat: add login

# ❌ Past tense
✨ feat: added SSO support

# ❌ Vague message
🔧 chore: updates

# ❌ Trailing period
🐛 fix: handle null response.

# ❌ Uppercase message
✨ feat: Add Dark Mode
```

## Suspicious Files (warn before staging)

Flag any file matching these patterns when in auto-stage mode:

- Secrets/credentials: `.env`, `.env.*`, `*.pem`, `*.key`, `*.p12`, `*.pfx`, `*secret*`, `*credential*`, `*password*`, `*token*`
- Config with likely secrets: `config/secrets.*`, `*.secret.*`
- Large binaries: files >1 MB that aren't expected build artifacts
- Known bad patterns: `id_rsa`, `id_ed25519`, `*.ovpn`, `*.sql` dumps, `*.sqlite`, `*.db`

## Edge Cases

- **Multiple unrelated changes staged**: point it out and suggest
  splitting into separate commits before proceeding
- **Revert commit**: use `⏪ revert:` and reference the original
  commit SHA in the body
- **Breaking change**: append `!` after type, e.g. `✨ feat!:`,
  and add a `BREAKING CHANGE:` footer in the commit body
- **WIP commits**: allow them but warn if the target branch is `main`
  or `master`

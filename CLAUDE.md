# linkedin-publish-agent

This repo supports Xomnia thought leaders who want to automate the creation and publication of articles on LinkedIn.
It uses Claude skills + Python execution scripts + Google Sheets.

## First time? Run the setup skill

Invoke: `/setup`

The setup skill guides you through configuring your profile, 3 content themes,
Google Sheets connection, and LinkedIn credentials.

## Available Skills

| Skill | How to invoke | What it does |
|-------|---------------|--------------|
| `setup` | `/setup` | One-time onboarding: role, themes, credentials, sheet |
| `capture-ideas` | `/capture-ideas` | Add ideas (paste a list) → Google Sheet |
| `create-articles` | `/create-articles` | Generate LinkedIn drafts from new ideas |
| `post-article` | `/post-article` | Publish a ready article to LinkedIn |
| `schedule` | `/schedule` | Schedule ready articles + set up daily auto-post |

Skills are defined in `skills/`. To invoke one, type `/skill-name` or ask Claude to use it by name.

## Workflow

```
capture-ideas → create-articles → [review in sheet] → schedule or post-article
```

The `review → ready` status change in Google Sheets is intentionally manual. Never automate this step.

## Execution Scripts

Python scripts in `execution/` are the deterministic layer. Skills call them.
Do not modify them to bypass workflow gates.

Draft creation (`create-articles`): you write drafts in-session using `build_system_prompt` rules, then `save_review_draft()` writes the sheet. `CLAUDE_API_KEY` is only for optional `generate_draft()` calls from Python.

## Config

- `config/brand_voice.md` — your LinkedIn writing style (edit freely)
- `config/themes.yaml` — your 3 content themes (set during setup)
- `config/profile.yaml` — your name, role, LinkedIn URN (set during setup)

## Routines & Scheduling

When creating any routine or scheduled task (e.g. via `/schedule`), always use cloud-based remote agents. Never create locally-running session loops. Do not ask the user to choose — go straight to cloud.

## Status Workflow

`new → review → ready → posted`

- `new`: idea captured, not yet drafted
- `review`: draft generated, awaiting your approval in the sheet
- `ready`: you approved it — eligible for scheduling and posting
- `posted`: published to LinkedIn

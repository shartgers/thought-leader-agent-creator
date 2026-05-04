# linkedin-publish-agent

A Claude-powered pipeline for Xomnia thought leaders who want to automate the creation and publication of articles on LinkedIn. Clone it, run the setup skill, and you're posting.

## What it does

1. **Captures ideas** — paste a list, they go into Google Sheets
2. **Drafts articles** — Claude writes LinkedIn posts in your voice around 3 themes you define
3. **You review** — approve drafts in Google Sheets by changing status to `ready`
4. **Auto-posts** — a daily routine publishes scheduled articles at 08:30 Netherlands time

## Prerequisites

- [Claude Code](https://claude.ai/code) installed
- Python 3.11+
- A Google account (for Sheets)
- A LinkedIn Developer app ([guide in setup skill](skills/setup.md))
- An [Anthropic API key](https://console.anthropic.com)

## Getting Started

```bash
# 1. Clone the repo
git clone https://github.com/shartgers/linkedin-publish-agent.git
cd linkedin-publish-agent

# 2. Install Python dependencies
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 3. Copy credential template
cp .env.example .env

# 4. Open Claude Code and run the setup skill
# In Claude Code, type:
/setup
```

The setup skill walks you through everything else.

## Skills

| Skill | Invoke | Purpose |
|-------|--------|---------|
| `setup` | `/setup` | One-time onboarding |
| `capture-ideas` | `/capture-ideas` | Add ideas → Sheet |
| `create-articles` | `/create-articles` | Generate drafts |
| `post-article` | `/post-article` | Publish now |
| `schedule` | `/schedule` | Schedule + auto-post |

## Workflow

```
/capture-ideas  →  /create-articles  →  [review in sheet]  →  /schedule
```

The `review → ready` step in Google Sheets is intentionally manual. You decide what gets published.

## Customization

- `config/brand_voice.md` — edit to match your writing style
- `config/themes.yaml` — your 3 content topics
- `config/profile.yaml` — your name, role, LinkedIn URN

## Running Tests

```bash
pytest -v
```

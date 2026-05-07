# AI Digest Agent

An autonomous AI agent that searches the web for the latest AI news, summarizes the top stories, and emails you a daily digest. Available in two parallel implementations — one powered by **Claude (Anthropic)**, one powered by **GPT (OpenAI)** — sharing the same Tavily, Pinecone, and Gmail integrations.

## What it does

Every day, the agent:

1. Searches the web for the most recent AI news using Tavily, with a randomized search angle (research breakthroughs, OpenAI / Anthropic / DeepMind news, etc.) so each run finds different stories
2. Pulls 5 candidate stories and checks Pinecone for duplicates against previous digests
3. Picks the first 3 non-duplicate stories
4. Writes a clean HTML summary of each
5. Emails the digest to you via Gmail (with a footer note if fewer than 3 unique stories survived deduplication)
6. Saves the chosen stories to Pinecone so they aren't repeated tomorrow

## Two versions

| File | Brain | Notes |
|------|-------|-------|
| `agent_claude.py` | Claude Haiku 4.5 (Anthropic) | Original implementation using the Anthropic SDK and Claude's tool use API |
| `agent_openai.py` | GPT 5.4 (OpenAI) | Parallel implementation using the OpenAI SDK and function calling |

Both behave identically — the differences are SDK-level (tool schema format, message structure, response parsing). The scheduled GitHub Action currently runs `agent_openai.py`.

## Tech stack

- **Claude (Anthropic)** or **GPT (OpenAI)** — agent brain, tool use, and summarization
- **Tavily** — real-time web search
- **Pinecone** — vector database for semantic deduplication
- **Gmail SMTP** — email delivery
- **GitHub Actions** — daily scheduled runs

## How it works

The agent runs an agentic loop: the model is given a set of tools and decides on its own which ones to call and when. The available tools are:

- `search_web` — searches the web for recent news
- `check_duplicate` — checks Pinecone for similar stories already sent
- `save_story` — saves a sent story's embedding to Pinecone
- `send_email` — sends the final HTML digest via Gmail

The loop continues calling tools until the model decides it has finished the task.

## Setup

### 1. Clone and install

```bash
git clone https://github.com/JonathanCSJ/ai-digest-agent.git
cd ai-digest-agent
python -m venv venv
venv/Scripts/activate    # on Windows
pip install -r requirements.txt
```

### 2. Configure environment variables

Copy `.env.example` to `.env` and fill in your keys:

```
ANTHROPIC_API_KEY=...     # only needed if running agent_claude.py
OPENAI_API_KEY=...        # only needed if running agent_openai.py
TAVILY_API_KEY=...
PINECONE_API_KEY=...
GMAIL_ADDRESS=...
GMAIL_APP_PASSWORD=...
```

For Gmail, you'll need an [App Password](https://support.google.com/accounts/answer/185833), not your regular password.

### 3. Run locally

```bash
python agent_openai.py    # OpenAI version
# or
python agent_claude.py    # Claude version
```

## Running on a schedule (GitHub Actions)

The repo includes a workflow at `.github/workflows/daily-digest.yml` that runs `agent_openai.py` daily at 8am UTC. To enable it:

1. Push the repo to GitHub
2. Go to Settings → Secrets and variables → Actions
3. Add these repository secrets: `OPENAI_API_KEY`, `TAVILY_API_KEY`, `PINECONE_API_KEY`, `GMAIL_ADDRESS`, `GMAIL_APP_PASSWORD`
4. The workflow will run automatically each day, or trigger it manually from the Actions tab

To switch the schedule to the Claude version, edit `daily-digest.yml` to use `ANTHROPIC_API_KEY` and run `python agent_claude.py`.

## Project structure

```
.
├── agent_claude.py             # Claude version of the agent loop
├── agent_openai.py             # OpenAI version of the agent loop
├── requirements.txt            # Python dependencies
├── .env.example                # template for environment variables
├── .github/workflows/
│   └── daily-digest.yml        # scheduled GitHub Action (runs OpenAI version)
└── README.md
```

## Cost

Built to run cheaply on free tiers and a small model API budget. Cost figures below are for the Claude Haiku 4.5 version; GPT pricing varies by model.

| Service | Usage per run | Cost |
|---------|---------------|------|
| Claude (Haiku 4.5) | ~11k input + ~2.3k output tokens | ~$0.022 |
| Tavily | 1 search | Free tier (1,000/mo) |
| Pinecone | ~10 small embed/query/upsert calls | Free tier (2GB) |
| Gmail SMTP | 1 email | Free |
| GitHub Actions | ~1 minute | Free tier (2,000 min/mo) |

**Total: ~$0.022 per run, ~$0.66 per month** running daily on Claude Haiku.

The agent is tuned for low token usage: it does one broad search per run, caps Tavily summaries at 300 characters, and surfaces 5 candidate stories so it can pick 3 unique ones after deduplication.

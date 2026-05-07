# AI Digest Agent

An autonomous AI agent that searches the web for the latest AI news, summarizes the top stories, and emails you a daily digest. Built with Claude, Tavily, Pinecone, and GitHub Actions.

## What it does

Every day, the agent:

1. Searches the web for the most recent AI news using Tavily
2. Checks Pinecone to make sure each story hasn't already been sent
3. Writes a clean HTML summary of the top stories
4. Emails the digest to you via Gmail
5. Saves the stories to Pinecone so they aren't repeated tomorrow

## Tech stack

- **Claude (Anthropic)** — agent brain, tool use, and summarization
- **Tavily** — real-time web search
- **Pinecone** — vector database for semantic deduplication
- **Gmail SMTP** — email delivery
- **GitHub Actions** — daily scheduled runs

## How it works

The agent runs an agentic loop: Claude is given a set of tools and decides on its own which ones to call and when. The available tools are:

- `search_web` — searches the web for recent news
- `check_duplicate` — checks Pinecone for similar stories already sent
- `save_story` — saves a sent story's embedding to Pinecone
- `send_email` — sends the final HTML digest via Gmail

The loop continues calling tools until Claude decides it has finished the task.

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
ANTHROPIC_API_KEY=...
TAVILY_API_KEY=...
PINECONE_API_KEY=...
GMAIL_ADDRESS=...
GMAIL_APP_PASSWORD=...
```

For Gmail, you'll need an [App Password](https://support.google.com/accounts/answer/185833), not your regular password.

### 3. Run locally

```bash
python agent.py
```

## Running on a schedule (GitHub Actions)

The repo includes a workflow at `.github/workflows/daily-digest.yml` that runs daily at 8am UTC. To enable it:

1. Push the repo to GitHub
2. Go to Settings → Secrets and variables → Actions
3. Add the same five keys from your `.env` as repository secrets
4. The workflow will run automatically each day, or trigger it manually from the Actions tab

## Project structure

```
.
├── agent.py                    # main agent loop and tool definitions
├── requirements.txt            # Python dependencies
├── .env.example                # template for environment variables
├── .github/workflows/
│   └── daily-digest.yml        # scheduled GitHub Action
└── README.md
```

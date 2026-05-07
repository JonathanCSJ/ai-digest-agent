from dotenv import load_dotenv
import anthropic
from tavily import TavilyClient
from pinecone import Pinecone, ServerlessSpec
import os
import sys
import random
from datetime import date
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

sys.stdout.reconfigure(encoding="utf-8")

load_dotenv()

client = anthropic.Anthropic()
tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
INDEX_NAME = "ai-digest"
if INDEX_NAME not in [i.name for i in pc.list_indexes()]:
    pc.create_index(
        name=INDEX_NAME,
        dimension=1024,
        metric="cosine",
        spec=ServerlessSpec(cloud="aws", region="us-east-1")
    )
index = pc.Index(INDEX_NAME)

today = date.today().strftime("%B %d, %Y")

tools = [
    {
        "name": "search_web",
        "description": "Search the web for current news and information. Use this to find latest AI news headlines.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query to use"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "check_duplicate",
        "description": "Check if a news story has already been sent before using semantic similarity. Call this before sending any story.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "The headline or title of the news story"
                }
            },
            "required": ["title"]
        }
    },
    {
        "name": "save_story",
        "description": "Save a news story to memory after sending it so it won't be sent again.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "The headline or title of the news story"
                },
                "url": {
                    "type": "string",
                    "description": "The URL of the news story"
                }
            },
            "required": ["title", "url"]
        }
    },
    {
        "name": "send_email",
        "description": "Send an email to yourself with the given subject and body. Useful for saving important information.",
        "input_schema": {
            "type": "object",
            "properties": {
                "subject": {
                    "type": "string",
                    "description": "The subject of the email"
                },
                "body": {
                    "type": "string",
                    "description": "The body content of the email"
                }
            },
            "required": ["subject", "body"]
        }
    }
]

ANGLES = [
    "research breakthroughs",
    "research breakthroughs",
    "research breakthroughs",
    "OpenAI news",
    "OpenAI news",
    "Anthropic news",
    "Anthropic news",
    "Google DeepMind news",
    "Google DeepMind news",
    "Meta AI news",
    "xAI news",
    "Microsoft AI news",
    "new model release",
    "AI benchmark results",
    "AI hardware advances",
    "AI startup funding",
]

def search_web(query):
    angle = random.choice(ANGLES)
    dated_query = f"{query} {angle} {today}"
    results = tavily.search(query=dated_query, max_results=5, days=1)
    formatted = []
    for r in results["results"]:
        snippet = r["content"][:300]
        formatted.append(f"Title: {r['title']}\nURL: {r['url']}\nSummary: {snippet}\n")
    return "\n---\n".join(formatted)

def check_duplicate(title):
    embedding = pc.inference.embed(
        model="multilingual-e5-large",
        inputs=[title],
        parameters={"input_type": "query"}
    )
    results = index.query(vector=embedding[0].values, top_k=1, include_metadata=True)
    if results.matches and results.matches[0].score > 0.92:
        return f"Duplicate: already sent '{results.matches[0].metadata['title']}'"
    return "Not a duplicate, safe to send"

def save_story(title, url):
    embedding = pc.inference.embed(
        model="multilingual-e5-large",
        inputs=[title],
        parameters={"input_type": "passage"}
    )
    index.upsert(vectors=[{
        "id": url,
        "values": embedding[0].values,
        "metadata": {"title": title, "url": url}
    }])
    return "Story saved to memory"

def send_email(subject, body):
    sender = os.getenv("GMAIL_ADDRESS")
    password = os.getenv("GMAIL_APP_PASSWORD")
    recipient = os.getenv("GMAIL_ADDRESS")  # sending to yourself

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = recipient

    msg.attach(MIMEText(body, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(sender, password)
        server.sendmail(sender, recipient, msg.as_string())

    return "Email sent successfully"

messages = [
    {"role": "user", "content": "Search the web for the top AI news stories from this week. Pick 3 non-duplicate stories. Write a clear summary of each and make sure to add link to the article, then send it as an email with the subject 'Your Daily AI Digest'."}
]

print("Agent is thinking...\n")

while True:
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        system=f"Today's date is {today}. Do ONE broad web search to find the top AI news stories — do not run multiple searches. The search returns up to 5 candidate stories. Call check_duplicate on each candidate and pick the first 3 non-duplicate stories to include in the email. Save each chosen story with save_story before sending. When sending emails, format the body as clean HTML. Use a white background, readable fonts, and structure each story with an <h2> headline, a short <p> summary, and an <a href> link to the article. Wrap everything in a <div> with max-width 600px and padding. If fewer than 3 unique stories were available because the rest were duplicates of stories already sent, add a short italic note at the bottom of the email explaining how many were skipped (e.g. '<p><em>Note: 2 stories were skipped because they were already included in a previous digest.</em></p>').",
        tools=tools,
        messages=messages
    )

    if response.stop_reason == "end_turn":
        final = next(block.text for block in response.content if hasattr(block, "text"))
        print("=== FINAL DIGEST ===\n")
        print(final)
        break

    if response.stop_reason == "tool_use":
        tool_use_blocks = [b for b in response.content if b.type == "tool_use"]

        # SDK accepts Pydantic response objects directly — no serialization needed
        messages.append({"role": "assistant", "content": response.content})

        tool_results = []
        for tool_block in tool_use_blocks:
            print(f"Claude is calling tool: {tool_block.name}")
            print(f"With inputs: {tool_block.input}\n")

            if tool_block.name == "search_web":
                result = search_web(tool_block.input["query"])
            elif tool_block.name == "check_duplicate":
                result = check_duplicate(tool_block.input["title"])
            elif tool_block.name == "save_story":
                result = save_story(tool_block.input["title"], tool_block.input["url"])
            elif tool_block.name == "send_email":
                result = send_email(tool_block.input["subject"], tool_block.input["body"])
            else:
                result = f"Unknown tool: {tool_block.name}"

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tool_block.id,
                "content": result
            })

        messages.append({"role": "user", "content": tool_results})
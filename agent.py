from dotenv import load_dotenv
import anthropic
from tavily import TavilyClient
import os
from datetime import date
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

load_dotenv()

client = anthropic.Anthropic()
tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

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

def search_web(query):
    results = tavily.search(query=query, max_results=5, days=3)
    formatted = []
    for r in results["results"]:
        formatted.append(f"Title: {r['title']}\nURL: {r['url']}\nSummary: {r['content']}\n")
    return "\n---\n".join(formatted)

def send_email(subject, body):
    sender = os.getenv("GMAIL_ADDRESS")
    password = os.getenv("GMAIL_APP_PASSWORD")
    recipient = os.getenv("GMAIL_ADDRESS")  # sending to yourself

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = recipient

    # Plain text version
    msg.attach(MIMEText(body, "plain"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(sender, password)
        server.sendmail(sender, recipient, msg.as_string())

    return "Email sent successfully"

messages = [
    {"role": "user", "content": "Search the web for the top 3 AI news stories from this week. Write a clear summary of each and make sure to add link to the article, then send it as an email with the subject 'Your Daily AI Digest."}
]

print("Agent is thinking...\n")

while True:
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        system=f"Today's date is {today}. Always search for the most recent news.",
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
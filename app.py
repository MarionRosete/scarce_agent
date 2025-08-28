from flask import Flask, request, send_from_directory
import requests
import os
from dotenv import load_dotenv
from openai import OpenAI
import re

load_dotenv()

VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN")
PAGE_ACCESS_TOKEN = os.environ.get("PAGE_ACCESS_TOKEN")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
BASE_URL = os.environ.get("BASE_URL")
SYSTEM_PROMPT = os.environ.get("SYSTEM_PROMPT")


client = OpenAI(api_key=OPENAI_API_KEY)
app = Flask(__name__)

# Quick Reply Titles (shown as buttons in Messenger)
QUICK_REPLIES = [
    "💬 Talk to Human",
    "👟 View Catalog",
    "📦 How to Order",
    "💰 Payment Options",
    "🚚 Shipping Info",
    
]

# Auto replies for common FAQs
AUTO_REPLIES = {
    "💬 talk to human": "Got it! We'll connect you with someone from the team asap 👍 You can continue chatting here and a real person will reply shortly.",
    "👟 view catalog": "Here’s our catalog 🔥 Check what’s available here:\n👉 https://marionrosete.github.io/ScarcePH",
    "📦 how to order": "Simple lang! 👇\n1️⃣ Browse the catalog or FB posts\n2️⃣ Message us to reserve/order\n3️⃣ We’ll confirm and send payment details\n\nKung COD/COP, ₱500 deposit is needed 😊",
    "💰 payment options": "You can pay via:\n💸 GCash\n🏦 BPI\n🚚 COD/COP (with ₱500 deposit)\n\n*Reservation deposit is non-refundable.*",
    "🚚 shipping info": "Shipping is via LBC 📦\n📍 Luzon/Visayas: 5–8 days\n📍 Mindanao: 3–5 days\n\nCOD/COP available din (with ₱500 deposit).",
    "pics": "Paki-check muna sa Facebook posts for more pics 📸\nOwner might send extra pics soon if available.",
    "reserve": "Yes, you can reserve! 🔒 Just send ₱500 deposit via GCash or BPI. Non-refundable to avoid flake buyers 😄",
    "💬 talk to human": "Got it! We'll connect you with someone from the team asap 👍 You can continue chatting here and a real person will reply shortly."
}

HUMAN_HANDOVER = set()



@app.route("/")
def index():
    return "Messenger AI bot is live!"


@app.route("/webhook", methods=["GET"])
def verify():
    if request.args.get("hub.verify_token") == VERIFY_TOKEN:
        return request.args.get("hub.challenge")
    return "Verification failed", 403

@app.route('/privacy-policy')
def privacy_policy():
    return send_from_directory('static/privacy-policy', 'index.html')

greeting_pattern = ["hi", "hello", "good day", "bossing", "good pm", "good am", "hey", "boss", "bro"] 

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    if data["object"] == "page":
        for entry in data["entry"]:
            for event in entry["messaging"]:
                sender_id = event["sender"]["id"]

                if "message" in event:
                    message = event["message"]

                    if "text" in message:
                        text = message["text"].lower().strip()
                        

                        # Show welcome menu
                        if (
                            any(re.fullmatch(rf"\b{re.escape(word)}\b", text) for word in greeting_pattern)
                            and text.count(" ") < 4 
                        ):
                                HUMAN_HANDOVER.discard(sender_id)
                                welcome_text = "Hey there! 👋 What would you like to know?"
                                send_text_message(sender_id, welcome_text, quick_replies=QUICK_REPLIES)
                                continue
                        # Check for auto reply
                        auto_reply = get_auto_reply(text, sender_id)
                        if auto_reply:
                            send_text_message(sender_id, auto_reply, quick_replies=QUICK_REPLIES)

                        # If user asked for human help, stop GPT responses
                        elif sender_id in HUMAN_HANDOVER:
                            send_text_message(sender_id, "A human team member will assist you soon 👍")

                        # Otherwise use GPT
                        else:
                            reply = get_gpt_response(text)
                            send_text_message(sender_id, reply, quick_replies=QUICK_REPLIES)

    return "ok", 200


def get_auto_reply(message, sender_id):
    for keyword, reply in AUTO_REPLIES.items():
        if keyword in message:
            if "talk to human" in keyword:
                HUMAN_HANDOVER.add(sender_id)
            return reply
    return None


def get_gpt_response(message):
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": message}
            ],
            max_tokens=100,
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"[ERROR] GPT request failed: {e}")
        return "We will get back to you shortly! - Automated Message"


def send_text_message(recipient_id, message_text, quick_replies=None):
    url = f"https://graph.facebook.com/v17.0/me/messages?access_token={PAGE_ACCESS_TOKEN}"

    message_payload = {"text": message_text}

    if quick_replies:
        message_payload["quick_replies"] = [
            {
                "content_type": "text",
                "title": reply,
                "payload": reply
            } for reply in quick_replies
        ]

    payload = {
        "recipient": {"id": recipient_id},
        "message": message_payload
    }

    response = requests.post(url, json=payload)
    if response.status_code != 200:
        print(f"[ERROR] Message send failed: {response.text}")


if __name__ == "__main__":
    app.run(debug=True)

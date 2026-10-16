import os

from openai import OpenAI

api_key = os.environ.get("GROQ_API_KEY")
if not api_key:
    raise RuntimeError("Set GROQ_API_KEY before running this interactive test.")

client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=api_key,
)

SYSTEM_PROMPT = """
You are an embedded digital health companion for this Safety and Check-Up Application.
Your ONLY purpose is to help the user with tasks relevant to this app's purpose:
1. Explaining how the app's features work (e.g., routine check-ups, background monitoring, schedule settings).
2. Guiding them on how to update their wakeup/bedtime schedule or emergency contacts.
3. Helping them locate nearby pharmacies or urgent care centers when requested.
4. Giving mental health tips when needed and acting as a therapeutic companion.

Strict Guidelines:
- If a user asks about unrelated topics (e.g., coding help, general trivia, history, recipes, or creative writing), politely decline and remind them that you are here to assist with their safety app usage and health resources.
- Always maintain a supportive, clear, and concise tone.
"""

while True:
    prompt = input("Ask a question!")
    if not prompt.strip():
        continue

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
    )
    print(response.choices[0].message.content)

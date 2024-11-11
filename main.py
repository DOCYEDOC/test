import os
from openai import OpenAI
from dotenv import load_dotenv
import pyautogui as p
import time
import re

load_dotenv()
client = OpenAI(api_key=os.environ.get('OPENAI_KEY'))
assistant = client.beta.assistants.retrieve(assistant_id=os.environ.get('ASSISTANT'))

chat_history_folder = "chat_histories"
THREAD_ID_FILE = os.path.join(chat_history_folder, "thread_id.txt")
os.makedirs(chat_history_folder, exist_ok=True)

def save_thread_id(thread_id):
    with open(THREAD_ID_FILE, "w") as f:
        f.write(thread_id)

def load_thread_id():
    if os.path.exists(THREAD_ID_FILE):
        with open(THREAD_ID_FILE, "r") as f:
            return f.read().strip()
    return None

async def create_or_load_thread():
    thread_id = load_thread_id()
    if thread_id:
        # Try to retrieve the existing thread to check if it's still valid
        try:
            thread = client.beta.threads.retrieve(thread_id=thread_id)
            if thread:
                return thread
        except:
            print("Existing thread is invalid, creating a new one.")

    # Create a new thread if the existing one is invalid or doesn't exist
    new_thread = client.beta.threads.create()
    save_thread_id(new_thread.id)
    return new_thread

async def wait_on_run(run, thread):
    while run.status == "queued" or run.status == "in_progress":
        run = client.beta.threads.runs.retrieve(
            thread_id=thread.id,
            run_id=run.id
        )
        time.sleep(0.5)
    return run

async def get_response(content, thread):
    image_path = "screenshot.png"
    p.screenshot(image_path)

    file = client.files.create(
        file=open(image_path, "rb"),
        purpose="vision"
    )
    
    message = client.beta.threads.messages.create(
        thread_id=thread.id,
        role='user',
        content=[
            {"type": "text", "text": content},
            {"type": "image_file", "image_file": {"file_id": file.id}}
        ]
    )

    run = client.beta.threads.runs.create(
        thread_id=thread.id,
        assistant_id=assistant.id,
    )

    run = await wait_on_run(run, thread)
    
    messages = client.beta.threads.messages.list(
        thread_id=thread.id, order="asc", after=message.id
    )
    response_text = ""
    for message in messages:
        for c in message.content:
            response_text += c.text.value
    clean_text = re.sub('【.*?】', '', response_text)
    return clean_text

while True:
    thread = create_or_load_thread()
    user_message = input("입력: ")
    gpt_reply = get_response(user_message, thread)
    print(f"출력: {gpt_reply}")
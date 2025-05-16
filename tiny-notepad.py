import tkinter as tk
import requests
import threading
import json
from datetime import datetime
import os
import subprocess
import time

def save_note():
    content = text.get("1.0", "end-1c")
    with open("note.txt", "w", encoding="utf-8") as f:
        f.write(content)
    os.makedirs("notes", exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = os.path.join("notes", f"notes_{timestamp}.txt")
    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)

def load_note():
    try:
        with open("note.txt", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return ""

def ensure_ollama_running():
    def check_and_start():
        try:
            response = requests.get("http://localhost:11434", timeout=1)
            if response.status_code == 200:
                update_status_label("🟢 Ollama is running")
                return
        except requests.ConnectionError:
            update_status_label("🔴 Ollama not running. Starting...")

        try:
            subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            update_status_label("🟡 Starting Ollama...")
            time.sleep(2)  # Let it boot
            # Retry once
            response = requests.get("http://localhost:11434", timeout=1)
            if response.status_code == 200:
                update_status_label("🟢 Ollama started successfully")
            else:
                update_status_label("🔴 Failed to connect to Ollama")
        except Exception as e:
            update_status_label(f"🔴 Error: {e}")

    threading.Thread(target=check_and_start, daemon=True).start()

def update_status_label(message):
    root.after(0, lambda: status_label.config(text=message))

def get_local_ollama_models():
    try:
        response = requests.get("http://localhost:11434/api/tags")
        response.raise_for_status()
        data = response.json()
        return [model["name"] for model in data.get("models", [])]
    except Exception as e:
        print(f"Error fetching models: {e}")
        return []

def generate_from_ollama():
    prompt = prompt_entry.get()
    model = selected_model.get()
    if not prompt.strip():
        return
    text.insert("end", f"\nUser: {prompt.strip()}\n")
    text.insert("end", f"Model ({model}): ")
    text.see("end")
    prompt_entry.delete(0, "end")
    threading.Thread(target=stream_ollama_response, args=(prompt, model), daemon=True).start()

def stream_ollama_response(prompt, model):
    url = "http://localhost:11434/api/generate"
    headers = {"Content-Type": "application/json"}
    payload = {"model": model, "prompt": prompt, "stream": True}
    try:
        with requests.post(url, json=payload, stream=True, headers=headers) as response:
            for line in response.iter_lines():
                if line:
                    try:
                        data = json.loads(line.decode("utf-8"))
                        text.insert("end", data.get("response", ""))
                        text.see("end")
                    except json.JSONDecodeError:
                        continue
        text.insert("end", "\n")
        text.see("end")
    except Exception as e:
        text.insert("end", f"\n[Error connecting to Ollama: {e}]\n")
        text.see("end")

# --- GUI setup ---
root = tk.Tk()
root.title("Tiny Notepad with Ollama")

# Status Label
status_label = tk.Label(root, text="Checking Ollama status...", anchor="w", fg="white", bg="black", font=("Segoe UI", 10, "bold"))
status_label.pack(fill="x", padx=8, pady=(4, 0))

# Start service check
ensure_ollama_running()

# Prompt UI
prompt_frame = tk.Frame(root)
prompt_frame.pack(fill="x", padx=8, pady=4)

tk.Label(prompt_frame, text="Model:").pack(side="left", padx=(0, 4))
models = get_local_ollama_models()
if not models:
    models = ["llama3.2"]
selected_model = tk.StringVar()
selected_model.set(models[0])
model_menu = tk.OptionMenu(prompt_frame, selected_model, *models)
model_menu.pack(side="left", padx=(0, 8))

tk.Label(prompt_frame, text="Prompt:").pack(side="left")
prompt_entry = tk.Entry(prompt_frame, width=50)
prompt_entry.pack(side="left", fill="x", expand=True, padx=4)

tk.Button(prompt_frame, text="Generate", command=generate_from_ollama).pack(side="right")

# Text widget
text = tk.Text(root, wrap="word", font=("Consolas", 12), undo=True)
text.pack(expand=True, fill="both")
text.insert("1.0", load_note())

root.protocol("WM_DELETE_WINDOW", lambda: (save_note(), root.destroy()))
root.mainloop()

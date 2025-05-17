import tkinter as tk
import requests
import threading
import json
from datetime import datetime
import os
import subprocess
import time

# Ensure notes directory exists
NOTES_DIR = "notes"
os.makedirs(NOTES_DIR, exist_ok=True)

def save_note():
    content = text.get("1.0", "end-1c")
    with open("note.txt", "w", encoding="utf-8") as f:
        f.write(content)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = os.path.join(NOTES_DIR, f"notes_{timestamp}.txt")
    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)
    refresh_note_list()  # NEW: update sidebar

def load_note():
    try:
        with open("note.txt", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return ""

def load_selected_note(event):
    selected = note_listbox.curselection()
    if selected:
        note_file = note_listbox.get(selected[0])
        with open(os.path.join(NOTES_DIR, note_file), "r", encoding="utf-8") as f:
            text.delete("1.0", "end")
            text.insert("1.0", f.read())

def refresh_note_list():
    note_listbox.delete(0, "end")
    files = sorted(os.listdir(NOTES_DIR), reverse=True)
    for f in files:
        if f.endswith(".txt"):
            note_listbox.insert("end", f)

def new_note():
    text.delete("1.0", "end")
    prompt_entry.delete(0, "end")
    
def ensure_ollama_running():
    def check_and_start():
        try:
            response = requests.get("http://localhost:11434", timeout=1)
            if response.status_code == 200:
                safe_update("🟢 Ollama is running")
                return
        except requests.ConnectionError:
            safe_update("🔴 Ollama not running. Starting...")

        try:
            subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            safe_update("🟡 Starting Ollama...")
            time.sleep(2)  # Let it boot

            # Retry once
            try:
                response = requests.get("http://localhost:11434", timeout=2)
                if response.status_code == 200:
                    safe_update("🟢 Ollama started successfully")
                else:
                    safe_update("🔴 Failed to connect to Ollama")
            except Exception as e:
                safe_update(f"🔴 Still can't connect: {e}")
        except Exception as e:
            safe_update(f"🔴 Error: {e}")

    threading.Thread(target=check_and_start, daemon=True).start()


def update_status_label(message):
    status_label.config(text=message)

def safe_update(message):
    root.after(0, lambda: update_status_label(message))


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

    try:
        temperature = float(temp_var.get())
        top_p = float(top_p_var.get())
        top_k = int(top_k_var.get())
        repeat_penalty = float(repeat_penalty_var.get())
        presence_penalty = float(presence_penalty_var.get())
        frequency_penalty = float(frequency_penalty_var.get())
        stop_input = stop_var.get().strip()
        stop_sequences = [s.strip() for s in stop_input.split(",")] if stop_input else None
    except Exception as e:
        text.insert("end", f"\n[Parameter error: {e}]\n")
        return

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": True,
        "temperature": temperature,
        "top_p": top_p,
        "top_k": top_k,
        "repeat_penalty": repeat_penalty,
        "presence_penalty": presence_penalty,
        "frequency_penalty": frequency_penalty
    }

    if stop_sequences:
        payload["stop"] = stop_sequences

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
root.geometry("1000x600")  # Optional: increase size
root.configure(bg="#1e1e1e")

BG_COLOR = "#1e1e1e"
FG_COLOR = "#ffffff"
ENTRY_BG = "#2d2d2d"
ENTRY_FG = "#ffffff"
TEXT_BG = "#1e1e1e"
TEXT_FG = "#ffffff"
HIGHLIGHT_COLOR = "#444444"

# Status label
status_label = tk.Label(root, text="Checking Ollama status...", anchor="w",
                        fg=FG_COLOR, bg=BG_COLOR, font=("Segoe UI", 10, "bold"))
status_label.pack(fill="x", padx=8, pady=(4, 0))
root.after(100, ensure_ollama_running)

# Prompt Frame
prompt_frame = tk.Frame(root, bg=BG_COLOR)
prompt_frame.pack(fill="x", padx=8, pady=4)

# --- Model parameters frame ---
param_frame = tk.Frame(root, bg=BG_COLOR)
param_frame.pack(fill="x", padx=8, pady=4)

def add_param_control(label, var, from_, to_, resolution, side="left"):
    frame = tk.Frame(param_frame, bg=BG_COLOR)
    frame.pack(side=side, padx=(8, 8))
    tk.Label(frame, text=label, fg=FG_COLOR, bg=BG_COLOR).pack()
    scale = tk.Scale(frame, from_=from_, to=to_, resolution=resolution,
                     orient="horizontal", variable=var,
                     bg=BG_COLOR, fg=FG_COLOR, highlightbackground=BG_COLOR)
    scale.pack()

# Parameter variables
temp_var = tk.DoubleVar(value=0.7)
top_p_var = tk.DoubleVar(value=0.9)
top_k_var = tk.IntVar(value=40)
repeat_penalty_var = tk.DoubleVar(value=1.0)
presence_penalty_var = tk.DoubleVar(value=0.0)
frequency_penalty_var = tk.DoubleVar(value=0.0)
stop_var = tk.StringVar(value="")  # comma-separated

# Add all sliders
add_param_control("Temperature", temp_var, 0.0, 2.0, 0.1)
add_param_control("Top-p", top_p_var, 0.0, 1.0, 0.05)
add_param_control("Top-k", top_k_var, 0, 100, 1)
add_param_control("Repeat Penalty", repeat_penalty_var, 0.5, 2.0, 0.05)
add_param_control("Presence Penalty", presence_penalty_var, -2.0, 2.0, 0.1)
add_param_control("Frequency Penalty", frequency_penalty_var, -2.0, 2.0, 0.1)

# Stop sequences entry (in a new line for better layout)
stop_frame = tk.Frame(root, bg=BG_COLOR)
stop_frame.pack(fill="x", padx=8, pady=2)
tk.Label(stop_frame, text="Stop Sequences (comma-separated):", fg=FG_COLOR, bg=BG_COLOR).pack(side="left")
stop_entry = tk.Entry(stop_frame, textvariable=stop_var, bg=ENTRY_BG, fg=ENTRY_FG, insertbackground=FG_COLOR, width=60)
stop_entry.pack(side="left", padx=8, fill="x", expand=True)


tk.Label(prompt_frame, text="Model:", fg=FG_COLOR, bg=BG_COLOR).pack(side="left", padx=(0, 4))

models = get_local_ollama_models()

if not models:
    models = ["llama3.2"]
selected_model = tk.StringVar()
selected_model.set(models[0])
model_menu = tk.OptionMenu(prompt_frame, selected_model, *models)
model_menu.configure(bg=ENTRY_BG, fg=ENTRY_FG, highlightbackground=HIGHLIGHT_COLOR, activebackground="#3e3e3e")
model_menu["menu"].configure(bg=ENTRY_BG, fg=ENTRY_FG)
model_menu.pack(side="left", padx=(0, 8))

tk.Label(prompt_frame, text="Prompt:", fg=FG_COLOR, bg=BG_COLOR).pack(side="left")
prompt_entry = tk.Entry(prompt_frame, width=50, bg=ENTRY_BG, fg=ENTRY_FG, insertbackground=FG_COLOR)
prompt_entry.pack(side="left", fill="x", expand=True, padx=4)

tk.Button(prompt_frame, text="Generate", command=generate_from_ollama,
          bg="#3a3a3a", fg="#ffffff", activebackground="#555555").pack(side="right")

# --- NEW: Main layout frame ---
main_frame = tk.Frame(root, bg=BG_COLOR)
main_frame.pack(fill="both", expand=True)

# --- NEW: Sidebar for notes ---
sidebar = tk.Frame(main_frame, width=200, bg="#2a2a2a")
sidebar.pack(side="left", fill="y")

tk.Label(sidebar, text="📂 Saved Notes", fg=FG_COLOR, bg="#2a2a2a", font=("Segoe UI", 10, "bold")).pack(pady=(8, 4))
note_listbox = tk.Listbox(sidebar, bg="#333333", fg="#ffffff", selectbackground="#555555", height=30)
note_listbox.pack(fill="both", expand=True, padx=8, pady=(0, 8))
note_listbox.bind("<<ListboxSelect>>", load_selected_note)

tk.Button(sidebar, text="📝 New Note", command=new_note, bg="#444444", fg="#ffffff").pack(fill="x", padx=8, pady=(0, 8))

# --- Text area for notes ---
text = tk.Text(main_frame, wrap="word", font=("Consolas", 12), undo=True,
               bg=TEXT_BG, fg=TEXT_FG, insertbackground=FG_COLOR)
text.pack(side="right", expand=True, fill="both")

# Initial content
text.insert("1.0", load_note())
refresh_note_list()

# Exit save hook
root.protocol("WM_DELETE_WINDOW", lambda: (save_note(), root.destroy()))
root.mainloop()

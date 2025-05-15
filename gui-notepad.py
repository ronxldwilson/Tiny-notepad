
import tkinter as tk
import requests
import threading
import json

def save_note():
    with open("note.txt", "w", encoding="utf-8") as f:
        f.write(text.get("1.0", "end-1c"))

def load_note():
    try:
        with open("note.txt", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return ""


def generate_from_ollama():
    prompt = prompt_entry.get()
    model = selected_model.get()
    if not prompt.strip():
        return
    
    # Insert the prompt with User label
    text.insert("end", f"\nUser: {prompt.strip()}\n")
    text.insert("end", f"Model ({model}): ")
    text.see("end")
    prompt_entry.delete(0, "end")  # Clear the prompt entry

    threading.Thread(target=stream_ollama_response, args=(prompt, model), daemon=True).start()


def stream_ollama_response(prompt, model):
    url = "http://localhost:11434/api/generate"
    headers = {"Content-Type": "application/json"}
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": True
    }

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


# GUI
root = tk.Tk()
root.title("Tiny Notepad with Ollama")

# Model selector variable
selected_model = tk.StringVar()
selected_model.set("llama3.2")  # default model

# Prompt input
prompt_frame = tk.Frame(root)

# Model selector
models = ["llama3", "llama3.2", "mistral", "deepseek", "gemma", "codellama"]
tk.Label(prompt_frame, text="Model:").pack(side="left", padx=(0, 4))
model_menu = tk.OptionMenu(prompt_frame, selected_model, *models)
model_menu.pack(side="left", padx=(0, 8))

prompt_frame.pack(fill="x", padx=8, pady=4)

tk.Label(prompt_frame, text="Prompt:").pack(side="left")
prompt_entry = tk.Entry(prompt_frame, width=50)
prompt_entry.pack(side="left", fill="x", expand=True, padx=4)

tk.Button(prompt_frame, text="Generate", command=generate_from_ollama).pack(side="right")

# Text area
text = tk.Text(root, wrap="word", font=("Consolas", 12), undo=True)
text.pack(expand=True, fill="both")

# Load previous note
text.insert("1.0", load_note())

# Save on exit
root.protocol("WM_DELETE_WINDOW", lambda: (save_note(), root.destroy()))
root.mainloop()

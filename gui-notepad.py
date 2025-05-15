
import tkinter as tk

def save_note():
    with open("note.txt", "w", encoding="utf-8") as f:
        f.write(text.get("1.0", "end-1c"))

root = tk.Tk()
root.title("Tiny Notepad")

text = tk.Text(root, wrap="word", font=("Consolas", 12), undo=True)
text.pack(expand=True, fill="both")

text.insert("1.0", open("note.txt", encoding="utf-8").read() if open("note.txt", "a+").tell() > 0 else "")

root.protocol("WM_DELETE_WINDOW", lambda: (save_note(), root.destroy()))
root.mainloop()

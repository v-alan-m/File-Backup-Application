import os
import sys
import shutil
import filecmp
import json
from tkinter import *
from tkinter import ttk, filedialog, messagebox
from threading import Thread

# --- Resource Path Fix for PyInstaller ---
def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # When bundled by PyInstaller
        base_path = sys._MEIPASS
    except AttributeError:
        # When running from source
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

# If you want history.json to remain editable between runs, store it next to the .exe
HISTORY_FILE = os.path.join(os.path.dirname(sys.executable if getattr(sys, 'frozen', False) else __file__), "history.json")


class BackupApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Smart Folder Backup Tool")
        self.root.geometry("700x620")
        self.root.resizable(True, True)

        self.canvas = Canvas(self.root, borderwidth=0)
        self.frame = Frame(self.canvas)
        self.canvas_window = self.canvas.create_window((0, 0), window=self.frame, anchor="n")

        scrollbar = Scrollbar(self.root, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side=RIGHT, fill=Y)
        self.canvas.pack(side=LEFT, fill=BOTH, expand=True)

        self.frame.bind("<Configure>", self.on_frame_configure)
        self.canvas.bind("<Configure>", self.on_canvas_configure)
        self.canvas.bind_all("<MouseWheel>", lambda e: self.canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))

        self.folder_pairs = []
        self.previous_sources = []
        self.previous_dests = []
        self.load_history()

        Label(self.frame, text="Folder Backup Utility", font=("Helvetica", 16, "bold")).pack(pady=10)

        input_frame = Frame(self.frame)
        input_frame.pack(pady=5)

        Button(input_frame, text="Add Source", command=self.choose_source).grid(row=0, column=0, padx=5)
        self.source_var = StringVar()
        Entry(input_frame, textvariable=self.source_var, width=60).grid(row=0, column=1)

        self.source_history_frame = Frame(self.frame)
        self.source_history_frame.pack(pady=2)

        Button(input_frame, text="Add Destination", command=self.choose_destination).grid(row=1, column=0, padx=5)
        self.dest_var = StringVar()
        Entry(input_frame, textvariable=self.dest_var, width=60).grid(row=1, column=1)

        self.dest_history_frame = Frame(self.frame)
        self.dest_history_frame.pack(pady=2)

        Button(self.frame, text="Add Pair", command=self.add_pair).pack(pady=5)

        list_frame = Frame(self.frame)
        list_frame.pack()

        Label(list_frame, text="Source → Destination Pairs").pack()
        self.pair_listbox = Listbox(list_frame, width=90, height=6)
        self.pair_listbox.pack(pady=5)

        Button(list_frame, text="Remove Selected Pair", command=self.remove_selected).pack()

        self.progress = ttk.Progressbar(self.frame, orient=HORIZONTAL, length=500, mode='determinate',
                                        style="green.Horizontal.TProgressbar")
        self.progress.pack(pady=20)

        self.status_label = Label(self.frame, text="", font=("Helvetica", 10))
        self.status_label.pack()

        self.backup_btn = Button(self.frame, text="Start Backup", command=self.start_backup_thread,
                                 font=("Helvetica", 12, "bold"))
        self.backup_btn.pack(pady=10)

        style = ttk.Style()
        style.theme_use("default")
        style.configure("green.Horizontal.TProgressbar", foreground="green", background="green", thickness=20)

        self.render_history()

    def on_frame_configure(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def on_canvas_configure(self, event):
        canvas_width = event.width
        self.canvas.itemconfig(self.canvas_window, width=canvas_width)

    def choose_source(self):
        folder = filedialog.askdirectory()
        if folder:
            self.source_var.set(folder)

    def choose_destination(self):
        folder = filedialog.askdirectory()
        if folder:
            self.dest_var.set(folder)

    def add_pair(self):
        src = self.source_var.get()
        dst = self.dest_var.get()
        if os.path.isdir(src) and os.path.isdir(dst):
            self.folder_pairs.append((src, dst))
            self.pair_listbox.insert(END, f"{src}  →  {dst}")

            if src not in self.previous_sources:
                self.previous_sources.append(src)
            if dst not in self.previous_dests:
                self.previous_dests.append(dst)

            self.save_history()
            self.render_history()

            self.source_var.set("")
            self.dest_var.set("")
        else:
            messagebox.showerror("Invalid", "Please select valid source and destination directories.")

    def remove_selected(self):
        selection = self.pair_listbox.curselection()
        if selection:
            index = selection[0]
            self.pair_listbox.delete(index)
            del self.folder_pairs[index]

    def start_backup_thread(self):
        if not self.folder_pairs:
            messagebox.showwarning("No Pairs", "Please add at least one folder pair.")
            return
        self.backup_btn.config(state=DISABLED)
        Thread(target=self.run_backup).start()

    def run_backup(self):
        total_files = self.count_total_files()
        completed = 0

        def update_progress():
            nonlocal completed
            completed += 1
            percent = int((completed / total_files) * 100)
            self.progress['value'] = percent
            self.status_label.config(text=f"Progress: {percent}%")
            self.frame.update_idletasks()

        for i, (source, dest) in enumerate(self.folder_pairs):
            self.highlight_pair(i)
            self.sync_dirs(source, dest, update_progress)

        self.status_label.config(text="✅ Backup Complete!")
        self.backup_btn.config(state=NORMAL)
        self.clear_highlight()

    def highlight_pair(self, index):
        self.clear_highlight()
        self.pair_listbox.itemconfig(index, {'bg': 'lightblue'})

    def clear_highlight(self):
        for i in range(self.pair_listbox.size()):
            self.pair_listbox.itemconfig(i, {'bg': 'white'})

    def count_total_files(self):
        count = 0
        for source, _ in self.folder_pairs:
            for _, _, files in os.walk(source):
                count += len(files)
        return max(count, 1)

    def sync_dirs(self, source, dest, progress_callback):
        for root, _, files in os.walk(source):
            rel_path = os.path.relpath(root, source)
            dest_dir = os.path.join(dest, rel_path)
            os.makedirs(dest_dir, exist_ok=True)

            for file in files:
                src_file = os.path.join(root, file)
                dst_file = os.path.join(dest_dir, file)

                if not os.path.exists(dst_file) or not filecmp.cmp(src_file, dst_file, shallow=False):
                    try:
                        shutil.copy2(src_file, dst_file)
                    except Exception as e:
                        print(f"Failed to copy {src_file} → {dst_file}: {e}")
                progress_callback()

    def render_history(self):
        for widget in self.source_history_frame.winfo_children():
            widget.destroy()
        for widget in self.dest_history_frame.winfo_children():
            widget.destroy()

        if self.previous_sources:
            Label(self.source_history_frame, text="Previous Sources:").pack(anchor="w")
        for path in self.previous_sources:
            self._render_path_entry(self.source_history_frame, path, kind="source")

        if self.previous_dests:
            Label(self.dest_history_frame, text="Previous Destinations:").pack(anchor="w")
        for path in self.previous_dests:
            self._render_path_entry(self.dest_history_frame, path, kind="dest")

    def _render_path_entry(self, frame, path, kind):
        row = Frame(frame)
        row.pack(anchor="w", padx=10, pady=2)

        lbl = Label(row, text=path, bg="white", fg="black", width=60, anchor="w", relief="sunken", bd=1)
        lbl.pack(side=LEFT, fill=X)
        lbl.bind("<Button-1>", lambda e: self.set_input_from_history(kind, path))

        Button(row, text="x", command=lambda: self.delete_history(kind, path), padx=5).pack(side=RIGHT)

    def set_input_from_history(self, kind, path):
        if kind == 'source':
            self.source_var.set(path)
        else:
            self.dest_var.set(path)

    def delete_history(self, kind, path):
        if kind == 'source':
            if path in self.previous_sources:
                self.previous_sources.remove(path)
        else:
            if path in self.previous_dests:
                self.previous_dests.remove(path)
        self.save_history()
        self.render_history()

    def load_history(self):
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, "r") as f:
                    data = json.load(f)
                    self.previous_sources = data.get("sources", [])
                    self.previous_dests = data.get("destinations", [])
            except Exception as e:
                print(f"Failed to load history: {e}")

    def save_history(self):
        try:
            with open(HISTORY_FILE, "w") as f:
                json.dump({
                    "sources": self.previous_sources,
                    "destinations": self.previous_dests
                }, f, indent=4)
        except Exception as e:
            print(f"Failed to save history: {e}")


if __name__ == "__main__":
    root = Tk()
    app = BackupApp(root)
    root.mainloop()

# Create .exe from the target location by using: pyinstaller --onefile --add-data "history.json;." backup_app.py
# The .exe will be found inside the 'dist' folder.

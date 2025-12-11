
# Put this file in your project and run main.py
import ctypes
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

import tkinter as tk
from tkinter import ttk, messagebox
from thread_pool import TaskPriority
import threading
import time
import random

# sound on Windows
try:
    import winsound
    def play_sound():
        try:
            winsound.MessageBeep(winsound.MB_OK)
        except Exception:
            pass
except Exception:
    def play_sound():
        pass

# optional graphing
HAS_MPL = True
try:
    import matplotlib
    matplotlib.use("TkAgg")
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure
except Exception:
    HAS_MPL = False

class ThreadUI:
    def __init__(self, pool):
        self.pool = pool
        self.root = tk.Tk()
        self.root.title("Thread Manager — Pro")
        self.root.geometry("800x850")
        self.root.resizable(False, False)

        # Fonts & theme state
        self.title_font = ("Segoe UI", 18, "bold")
        self.label_font = ("Segoe UI", 11)
        self.value_font = ("Segoe UI", 14, "bold")
        self.small_font = ("Segoe UI", 9)
        self.dark_mode = True

        self._make_styles()
        self._build_layout()
        self._bind_hover_effects()

        # graph data
        self.queue_history = []
        self.history_t = []

        # start UI update loop
        self.update_ui()
        self.root.mainloop()

    # ---------------- styles and theme ----------------
    def _make_styles(self):
        style = ttk.Style()
        style.theme_use("clam")

        # dark theme definitions (we'll toggle)
        self.colors = {
            "dark": {
                "bg": "#121212",
                "panel": "#1E1E1E",
                "fg": "#FFFFFF",
                "muted": "#BDBDBD",
                "card": "#232323",
                "btn": "#2F2F2F",
                "entry_bg": "#2B2B2B",
                "accent": "#3E8EF7"
            },
            "light": {
                "bg": "#F4F4F6",
                "panel": "#FFFFFF",
                "fg": "#111111",
                "muted": "#333333",
                "card": "#F0F0F0",
                "btn": "#E0E0E0",
                "entry_bg": "#FFFFFF",
                "accent": "#1E88E5"
            }
        }

        self.apply_theme(self.dark_mode)

    def apply_theme(self, dark=True):
        theme = "dark" if dark else "light"
        c = self.colors[theme]
        self.root.configure(bg=c["bg"])

        style = ttk.Style()
        style.configure("Card.TFrame", background=c["panel"], relief="ridge", padding=8)
        style.configure("TLabel", background=c["bg"], foreground=c["fg"])
        style.configure("Title.TLabel", font=self.title_font, background=c["bg"], foreground=c["fg"])
        style.configure("Small.TLabel", font=self.small_font, background=c["bg"], foreground=c["muted"])
        style.configure("TButton", background=c["btn"], foreground=c["fg"], padding=6)
        style.map("TButton", background=[("active", c["card"])])
        style.configure("TEntry", fieldbackground=c["entry_bg"], foreground=c["fg"])
        style.configure("CardValue.TLabel", font=self.value_font, background=c["panel"], foreground=c["fg"])

        # Save current colors
        self._c = c

    # ---------------- layout ----------------
    def _build_layout(self):
        c = self.colors["dark"] if self.dark_mode else self.colors["light"]

        ttk.Label(self.root, text="Thread Manager", style="Title.TLabel").pack(pady=(8,4))

        # input panel
        panel = ttk.Frame(self.root, style="Card.TFrame")
        panel.pack(pady=6, padx=10, fill="x")

        ttk.Label(panel, text="Enter Task:", font=self.label_font).grid(row=0, column=0, sticky="w", padx=4)
        self.placeholder = "ENTER INPUT"
        self.input_entry = ttk.Entry(panel, width=28)
        self.input_entry.grid(row=1, column=0, pady=6, padx=4)
        self.input_entry.insert(0, self.placeholder)
        self.input_entry.bind("<FocusIn>", self._clear_placeholder)
        self.input_entry.bind("<FocusOut>", self._add_placeholder)

        self.clear_btn = ttk.Button(panel, text="❌", width=3, command=self._clear_input)
        self.clear_btn.grid(row=1, column=1, padx=6)

        ttk.Label(panel, text="Priority:", font=self.label_font).grid(row=2, column=0, sticky="w", padx=4, pady=(4,0))
        pri_frame = ttk.Frame(panel)
        pri_frame.grid(row=3, column=0, pady=4, padx=4, sticky="w")

        self.selected_priority = tk.StringVar(value="MEDIUM")
        ttk.Radiobutton(pri_frame, text="HIGH", value="HIGH", variable=self.selected_priority).grid(row=0, column=0, padx=4)
        ttk.Radiobutton(pri_frame, text="MEDIUM", value="MEDIUM", variable=self.selected_priority).grid(row=0, column=1, padx=4)
        ttk.Radiobutton(pri_frame, text="LOW", value="LOW", variable=self.selected_priority).grid(row=0, column=2, padx=4)

        add_btn = ttk.Button(panel, text="Add Task", command=self.add_task)
        add_btn.grid(row=4, column=0, pady=6)

        # top controls (batch, clear, toggle)
        top_controls = ttk.Frame(self.root)
        top_controls.pack(pady=4)
        ttk.Button(top_controls, text="Batch Add (10)", command=self.batch_add).grid(row=0, column=0, padx=6)
        ttk.Button(top_controls, text="Clear Queue", command=self.clear_queue).grid(row=0, column=1, padx=6)
        self.theme_btn = ttk.Button(top_controls, text="Toggle Theme", command=self.toggle_theme)
        self.theme_btn.grid(row=0, column=2, padx=6)

        # stats cards
        stats = ttk.Frame(self.root)
        stats.pack(pady=6)

        self.active_card = self._make_card(stats, "Active")
        self.queue_card = self._make_card(stats, "Queue")
        self.done_card = self._make_card(stats, "Completed")
        self.active_card.grid(row=0, column=0, padx=8)
        self.queue_card.grid(row=0, column=1, padx=8)
        self.done_card.grid(row=0, column=2, padx=8)

        # currently executing + progress
        self.current_label = ttk.Label(self.root, text="Currently Executing: None", font=self.label_font)
        self.current_label.pack(pady=(6,2))

        self.progress = ttk.Progressbar(self.root, mode='indeterminate', length=380)
        self.progress.pack(pady=4)

        # pending queue viewer
        ttk.Label(self.root, text="Pending Queue:", font=("Segoe UI", 12, "bold")).pack(pady=(6,2))
        self.queue_view = tk.Text(self.root, height=6, width=60, state='disabled',
                                  bg=self._c["panel"], fg=self._c["fg"], relief="flat")
        self.queue_view.pack(pady=4)

        # control buttons
        control_frame = ttk.Frame(self.root)
        control_frame.pack(pady=6)
        ttk.Button(control_frame, text="Pause", command=self.pool.pause).grid(row=0, column=0, padx=8)
        ttk.Button(control_frame, text="Resume", command=self.pool.resume).grid(row=0, column=1, padx=8)
        ttk.Button(control_frame, text="Shutdown", command=self.pool.shutdown).grid(row=0, column=2, padx=8)

        # history + graph row
        bottom = ttk.Frame(self.root)
        bottom.pack(pady=6, padx=8, fill="both")

        # left: history
        hist_frame = ttk.Frame(bottom)
        hist_frame.grid(row=0, column=0, sticky="nsew", padx=(0,8))
        ttk.Label(hist_frame, text="Task History:", font=self.small_font).pack(anchor="w")
        self.history_view = tk.Text(hist_frame, height=8, width=35, state='disabled',
                                   bg=self._c["panel"], fg=self._c["fg"], relief="flat")
        self.history_view.pack()

        # right: graph (if mpl available)
        if HAS_MPL:
            graph_frame = ttk.Frame(bottom)
            graph_frame.grid(row=0, column=1, sticky="nsew")
            self.fig = Figure(figsize=(3,1.6), dpi=80)
            self.ax = self.fig.add_subplot(111)
            self.ax.set_title("Queue Size (recent)")
            self.ax.set_ylabel("size")
            self.ax.set_xlabel("samples")
            self.line, = self.ax.plot([], [], lw=1.5)
            self.canvas = FigureCanvasTkAgg(self.fig, master=graph_frame)
            self.canvas.get_tk_widget().pack()
        else:
            ttk.Label(bottom, text="Matplotlib not installed: Graph disabled", style="Small.TLabel").grid(row=0, column=1)

        # log at bottom
        self.log = tk.Text(self.root, height=6, width=60, state='disabled',
                           bg=self._c["panel"], fg=self._c["fg"])
        self.log.pack(pady=6)

        # keyboard
        self.root.bind("<Return>", lambda e: self.add_task())

    # ---------------- helpers ----------------
    def _make_card(self, parent, title):
        f = ttk.Frame(parent, style="Card.TFrame")
        ttk.Label(f, text=title, font=self.small_font).pack()
        val = ttk.Label(f, text="0", style="CardValue.TLabel")
        val.pack()
        return f

    def _clear_placeholder(self, event):
        if self.input_entry.get() == self.placeholder:
            self.input_entry.delete(0, tk.END)

    def _add_placeholder(self, event):
        if self.input_entry.get().strip() == "":
            self.input_entry.insert(0, self.placeholder)

    def _clear_input(self):
        self.input_entry.delete(0, tk.END)
        self._add_placeholder(None)

    # ---------------- actions ----------------
    def add_task(self):
        from tasks import simulated_heavy_task
        value = self.input_entry.get().strip()
        if value == "" or value == self.placeholder:
            return
        pr_map = {"HIGH": TaskPriority.HIGH, "MEDIUM": TaskPriority.MEDIUM, "LOW": TaskPriority.LOW}
        pr = pr_map[self.selected_priority.get()]
        self.pool.submit(pr, simulated_heavy_task, value)
        self._log(f"[{pr.name}] Task Added : {value}")
        self._clear_input()

    def batch_add(self, n=10):
        from tasks import simulated_heavy_task
        for i in range(n):
            name = f"batch-{int(time.time()*1000)%10000}-{i}"
            pr = random.choice([TaskPriority.HIGH, TaskPriority.MEDIUM, TaskPriority.LOW])
            self.pool.submit(pr, simulated_heavy_task, name)
            self._log(f"[{pr.name}] Task Added : {name}")

    def clear_queue(self):
        # Drain internal priority queue (demo-friendly)
        drained = 0
        try:
            while True:
                item = self.pool.tasks.get_nowait()
                self.pool.tasks.task_done()
                drained += 1
        except Exception:
            pass
        self._log(f"Cleared {drained} pending tasks from queue.")

    def toggle_theme(self):
        self.dark_mode = not self.dark_mode
        self.apply_theme(self.dark_mode)
        # update widget colors manually where needed
        bg = self._c["panel"]
        fg = self._c["fg"]
        for w in (self.queue_view, self.history_view, self.log):
            w.configure(bg=bg, fg=fg, insertbackground=fg)

    # ---------------- logging ----------------
    def _log(self, text):
        self.log.config(state='normal')
        self.log.insert(tk.END, text + "\n")
        self.log.see(tk.END)
        self.log.config(state='disabled')

    # ---------------- hover effects ----------------
    def _bind_hover_effects(self):
        def on_enter(e):
            w = e.widget
            try:
                w.configure(style="Hover.TButton")
            except Exception:
                pass
        def on_leave(e):
            w = e.widget
            try:
                w.configure(style="TButton")
            except Exception:
                pass

        style = ttk.Style()
        style.configure("Hover.TButton", background=self._c["accent"])
        for child in self.root.winfo_children():
            # attach to direct buttons in top-level (not exhaustive)
            if isinstance(child, ttk.Frame):
                for btn in child.winfo_children():
                    if isinstance(btn, ttk.Button):
                        btn.bind("<Enter>", on_enter)
                        btn.bind("<Leave>", on_leave)

    # ---------------- UI updater ----------------
    def update_ui(self):
        # cards
        try:
            self.active_card.winfo_children()[1].config(text=str(self.pool.active_tasks))
            self.queue_card.winfo_children()[1].config(text=str(self.pool.queue_size()))
            self.done_card.winfo_children()[1].config(text=str(self.pool.completed_tasks))
        except Exception:
            pass

        # currently executing
        if getattr(self.pool, "current_task", None):
            pr, args = self.pool.current_task
            val = args[0]
            pr_name = TaskPriority(pr).name if not isinstance(pr, TaskPriority) else pr.name
            self.current_label.config(text=f"Currently Executing: {val} ({pr_name})")
            # show progress bar indeterminate
            try:
                if not getattr(self, "_progress_running", False):
                    self.progress.start(10)
                    self._progress_running = True
            except Exception:
                pass
        else:
            self.current_label.config(text="Currently Executing: None")
            try:
                if getattr(self, "_progress_running", False):
                    self.progress.stop()
                    self._progress_running = False
            except Exception:
                pass

        # queue viewer
        try:
            items = self.pool.get_queue_items()
            self.queue_view.config(state='normal')
            self.queue_view.delete("1.0", tk.END)
            for priority, fn, args in items:
                pr_name = TaskPriority(priority).name if not isinstance(priority, TaskPriority) else priority.name
                self.queue_view.insert(tk.END, f"{args[0]} ({pr_name})\n")
            self.queue_view.config(state='disabled')
        except Exception:
            pass

        # history viewer: show recent items from pool.task_history
        try:
            hist = getattr(self.pool, "task_history", [])
            self.history_view.config(state='normal')
            self.history_view.delete("1.0", tk.END)
            for rec in hist[-50:]:
                pr = rec["priority"]
                pr_name = pr.name if isinstance(pr, TaskPriority) else TaskPriority(pr).name
                line = f"{rec['value']} - {pr_name} - {rec['duration']}s\n"
                self.history_view.insert(tk.END, line)
            self.history_view.config(state='disabled')
        except Exception:
            pass

        # play sound on newly completed task detection
        try:
            completed = getattr(self, "_last_completed", 0)
            now_completed = self.pool.completed_tasks
            if now_completed > completed:
                # play sound for each new completed
                for _ in range(now_completed - completed):
                    threading.Thread(target=play_sound, daemon=True).start()
                self._last_completed = now_completed
        except Exception:
            self._last_completed = getattr(self.pool, "completed_tasks", 0)

        # graph update
        try:
            if HAS_MPL:
                qsize = self.pool.queue_size()
                self.queue_history.append(qsize)
                self.history_t.append(time.time())
                # keep last 40 samples
                self.queue_history = self.queue_history[-40:]
                self.history_t = self.history_t[-40:]
                self.ax = self.fig.axes[0]
                self.ax.clear()
                self.ax.plot(self.queue_history, color="#66c2a5")
                self.ax.set_title("Queue size (recent)")
                self.ax.set_ylim(0, max(5, max(self.queue_history)+1))
                self.canvas.draw()
        except Exception:
            pass

        # schedule next update
        self.root.after(300, self.update_ui)






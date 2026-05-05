import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import os
import json
from datetime import datetime
from converter import (convert_file, batch_convert, VIDEO_FORMATS, AUDIO_FORMATS,
                       QUALITY_PRESETS, RESOLUTION_MAP, get_file_info, get_media_type)

ALL_FORMATS = sorted(set(VIDEO_FORMATS + AUDIO_FORMATS))

class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip_window = None
        widget.bind("<Enter>", self.show_tip)
        widget.bind("<Leave>", self.hide_tip)

    def show_tip(self, event=None):
        if self.tip_window or not self.text:
            return
        x, y, _, _ = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 25
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.winfo_toplevel().wm_overrideredirect(True)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(tw, text=self.text, justify=tk.LEFT,
                         background="#ffffe0", relief=tk.SOLID, borderwidth=1,
                         font=("Arial", 9))
        label.pack(ipadx=5, ipady=3)

    def hide_tip(self, event=None):
        tw = self.tip_window
        if tw:
            tw.destroy()
            self.tip_window = None

class ModernStyle:
    DARK_BG = "#1e1e2e"
    DARK_SECONDARY = "#313244"
    DARK_SURFACE = "#45475a"
    DARK_TEXT = "#cdd6f4"
    DARK_ACCENT = "#89b4fa"
    DARK_SUCCESS = "#a6e3a1"
    DARK_WARNING = "#f9e2af"
    DARK_ERROR = "#f38ba8"

    LIGHT_BG = "#eff1f5"
    LIGHT_SECONDARY = "#ccd0da"
    LIGHT_SURFACE = "#bcc0cc"
    LIGHT_TEXT = "#4c4f69"
    LIGHT_ACCENT = "#1e66f5"
    LIGHT_SUCCESS = "#40a02b"
    LIGHT_WARNING = "#df8e1d"
    LIGHT_ERROR = "#d20f39"

    def __init__(self):
        self.is_dark = True
        self.update_colors()

    def update_colors(self):
        if self.is_dark:
            self.bg = self.DARK_BG
            self.secondary = self.DARK_SECONDARY
            self.surface = self.DARK_SURFACE
            self.text = self.DARK_TEXT
            self.accent = self.DARK_ACCENT
            self.success = self.DARK_SUCCESS
            self.warning = self.DARK_WARNING
            self.error = self.DARK_ERROR
        else:
            self.bg = self.LIGHT_BG
            self.secondary = self.LIGHT_SECONDARY
            self.surface = self.LIGHT_SURFACE
            self.text = self.LIGHT_TEXT
            self.accent = self.LIGHT_ACCENT
            self.success = self.LIGHT_SUCCESS
            self.warning = self.LIGHT_WARNING
            self.error = self.LIGHT_ERROR

    def toggle_theme(self):
        self.is_dark = not self.is_dark
        self.update_colors()

style_obj = ModernStyle()

class FileConverterGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("njFile-convertor")
        self.root.geometry("950x750")
        self.input_files = []
        self.file_infos = {}
        self.is_converting = False
        self.is_paused = False
        self.failed_files = []  # Track failed conversions for retry
        self.conversion_state = 'idle'  # idle, running, paused, stopping
        self.history_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "history.json")
        self.load_history()
        self.setup_styles()
        self.setup_ui()

    def setup_styles(self):
        self.style = ttk.Style()
        self.style.theme_use('clam')
        bg = style_obj.bg
        secondary = style_obj.secondary
        surface = style_obj.surface
        text = style_obj.text
        accent = style_obj.accent
        self.style.configure('Main.TFrame', background=bg)
        self.style.configure('Card.TFrame', background=secondary, relief='flat', borderwidth=0)
        self.style.configure('Accent.TButton', background=accent, foreground='white', padding=10, font=('Arial', 10, 'bold'))
        self.style.map('Accent.TButton', background=[('active', accent), ('disabled', surface)])
        self.style.configure('Secondary.TButton', background=surface, foreground=text, padding=8)
        self.style.configure('Danger.TButton', background=style_obj.error, foreground='white', padding=8)
        self.style.configure('TLabel', background=bg, foreground=text)
        self.style.configure('Header.TLabel', background=bg, foreground=accent, font=('Arial', 20, 'bold'))
        self.style.configure('SubHeader.TLabel', background=secondary, foreground=text, font=('Arial', 11, 'bold'))
        self.style.configure('TNotebook', background=bg, borderwidth=0)
        self.style.configure('TNotebook.Tab', background=secondary, foreground=text, padding=[15, 8], font=('Arial', 10))
        self.style.map('TNotebook.Tab', background=[('selected', accent), ('active', surface)])
        self.style.configure('TProgressbar', background=accent, troughcolor=surface)
        self.style.configure('Treeview', background=surface, foreground=text, fieldbackground=surface, rowheight=25)
        self.style.configure('Treeview.Heading', background=secondary, foreground=text, font=('Arial', 10, 'bold'))
        self.style.map('Treeview', background=[('selected', accent)])

    def setup_ui(self):
        self.root.configure(bg=style_obj.bg)
        main_container = ttk.Frame(self.root, style='Main.TFrame', padding=15)
        main_container.pack(fill=tk.BOTH, expand=True)
        main_container.columnconfigure(0, weight=1)

        # Header
        header_frame = ttk.Frame(main_container, style='Main.TFrame')
        header_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        header_frame.columnconfigure(1, weight=1)
        title_label = ttk.Label(header_frame, text="⚡ njFile-convertor", style='Header.TLabel')
        title_label.grid(row=0, column=0, sticky=tk.W)
        btn_frame = ttk.Frame(header_frame, style='Main.TFrame')
        btn_frame.grid(row=0, column=2, sticky=tk.E)
        self.theme_btn = ttk.Button(btn_frame, text="🌙", command=self.toggle_theme, style='Secondary.TButton', width=5)
        self.theme_btn.pack(side=tk.RIGHT, padx=(5, 0))
        ToolTip(self.theme_btn, "Toggle Dark/Light Theme")
        history_btn = ttk.Button(btn_frame, text="📜 History", command=lambda: self.notebook.select(1), style='Secondary.TButton')
        history_btn.pack(side=tk.RIGHT, padx=5)
        ToolTip(history_btn, "View Conversion History")

        # Notebook
        notebook = ttk.Notebook(main_container)
        notebook.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        main_container.rowconfigure(1, weight=1)
        self.notebook = notebook

        convert_tab = ttk.Frame(notebook, style='Main.TFrame', padding=10)
        notebook.add(convert_tab, text="🔄  Convert")
        self.setup_convert_tab(convert_tab)

        history_tab = ttk.Frame(notebook, style='Main.TFrame', padding=10)
        notebook.add(history_tab, text="📜  History")
        self.setup_history_tab(history_tab)

        # Watch Folder Tab
        watch_tab = ttk.Frame(notebook, style='Main.TFrame', padding=10)
        notebook.add(watch_tab, text="👁️  Watch Folder")
        self.setup_watch_tab(watch_tab)

        # Status Bar
        self.setup_status_bar(main_container)

    def setup_convert_tab(self, parent):
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(2, weight=1)

        # Drop Zone
        drop_frame = tk.Frame(parent, bg=style_obj.secondary, relief='solid', bd=2, height=80,
                              highlightbackground=style_obj.accent, highlightthickness=2)
        drop_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        drop_frame.columnconfigure(0, weight=1)
        drop_frame.bind('<Button-1>', lambda e: self.add_files())
        drop_label = tk.Label(drop_frame, text="📁  Click here or drag files to add",
                              font=('Arial', 12), bg=style_obj.secondary, fg=style_obj.text)
        drop_label.grid(row=0, column=0, pady=25)
        drop_frame.bind('<Enter>', lambda e: drop_frame.configure(highlightbackground=style_obj.success))
        drop_frame.bind('<Leave>', lambda e: drop_frame.configure(highlightbackground=style_obj.accent))
        self.drop_frame = drop_frame

        # Queue with Treeview
        queue_frame = ttk.Frame(parent, style='Card.TFrame', padding=10)
        queue_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        queue_frame.columnconfigure(0, weight=1)
        tk.Label(queue_frame, text="📋  Conversion Queue", font=('Arial', 11, 'bold'),
                bg=style_obj.secondary, fg=style_obj.text).grid(row=0, column=0, sticky=tk.W, pady=(0, 5))

        tree_frame = ttk.Frame(queue_frame)
        tree_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)

        self.queue_tree = ttk.Treeview(tree_frame, columns=('size', 'duration', 'status'), show='tree headings', height=6)
        self.queue_tree.heading('#0', text='File Name')
        self.queue_tree.heading('size', text='Size')
        self.queue_tree.heading('duration', text='Duration')
        self.queue_tree.heading('status', text='Status')
        self.queue_tree.column('#0', width=350)
        self.queue_tree.column('size', width=100, anchor=tk.CENTER)
        self.queue_tree.column('duration', width=100, anchor=tk.CENTER)
        self.queue_tree.column('status', width=100, anchor=tk.CENTER)
        self.queue_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Drag reorder bindings
        self.drag_start_item = None
        self.queue_tree.bind('<ButtonPress-1>', self.on_drag_start)
        self.queue_tree.bind('<B1-Motion>', self.on_drag_motion)
        self.queue_tree.bind('<ButtonRelease-1>', self.on_drag_release)

        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.queue_tree.yview)
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.queue_tree.config(yscrollcommand=scrollbar.set)

        btn_frame = ttk.Frame(queue_frame, style='Card.TFrame', padding=(0, 5, 0, 0))
        btn_frame.grid(row=2, column=0, sticky=(tk.W, tk.E))
        add_btn = ttk.Button(btn_frame, text="➕ Add Files", command=self.add_files, style='Secondary.TButton')
        add_btn.pack(side=tk.LEFT, padx=5)
        ToolTip(add_btn, "Add media files to queue")
        remove_btn = ttk.Button(btn_frame, text="➖ Remove", command=self.remove_files, style='Secondary.TButton')
        remove_btn.pack(side=tk.LEFT, padx=5)
        ToolTip(remove_btn, "Remove selected files from queue")
        clear_btn = ttk.Button(btn_frame, text="🗑️ Clear All", command=self.clear_files, style='Danger.TButton')
        clear_btn.pack(side=tk.LEFT, padx=5)
        ToolTip(clear_btn, "Clear all files from queue")

        parent.rowconfigure(1, weight=1)
        self.setup_settings_panel(parent)
        self.setup_output_panel(parent)

    def setup_settings_panel(self, parent):
        settings_frame = ttk.Frame(parent, style='Card.TFrame', padding=10)
        settings_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        settings_frame.columnconfigure(1, weight=1)
        settings_frame.columnconfigure(3, weight=1)

        sep = ttk.Separator(settings_frame, orient='horizontal')
        sep.grid(row=0, column=0, columnspan=4, sticky=(tk.W, tk.E), pady=(0, 5))

        tk.Label(settings_frame, text="⚙️  Settings", font=('Arial', 11, 'bold'),
                bg=style_obj.secondary, fg=style_obj.text).grid(row=1, column=0, columnspan=4, sticky=tk.W, pady=(0, 10))

        tk.Label(settings_frame, text="Quality:", bg=style_obj.secondary, fg=style_obj.text).grid(row=2, column=0, padx=(0, 10), pady=5, sticky=tk.W)
        self.quality_var = tk.StringVar(value="medium")
        quality_combo = ttk.Combobox(settings_frame, textvariable=self.quality_var,
                                     values=list(QUALITY_PRESETS.keys()), state="readonly", width=15)
        quality_combo.grid(row=2, column=1, padx=5, pady=5, sticky=tk.W)
        ToolTip(quality_combo, "Low=small file, High=best quality")

        tk.Label(settings_frame, text="Resolution:", bg=style_obj.secondary, fg=style_obj.text).grid(row=2, column=2, padx=(20, 10), pady=5, sticky=tk.W)
        self.resolution_var = tk.StringVar(value="original")
        resolution_combo = ttk.Combobox(settings_frame, textvariable=self.resolution_var,
                                        values=list(RESOLUTION_MAP.keys()), state="readonly", width=15)
        resolution_combo.grid(row=2, column=3, padx=5, pady=5, sticky=tk.W)
        ToolTip(resolution_combo, "Output video resolution")

        tk.Label(settings_frame, text="Audio Channels:", bg=style_obj.secondary, fg=style_obj.text).grid(row=3, column=0, padx=(0, 10), pady=5, sticky=tk.W)
        self.channels_var = tk.StringVar(value="original")
        channels_combo = ttk.Combobox(settings_frame, textvariable=self.channels_var,
                                      values=["original", "1", "2"], state="readonly", width=15)
        channels_combo.grid(row=3, column=1, padx=5, pady=5, sticky=tk.W)
        ToolTip(channels_combo, "1=Mono, 2=Stereo")

        tk.Label(settings_frame, text="Sample Rate:", bg=style_obj.secondary, fg=style_obj.text).grid(row=3, column=2, padx=(20, 10), pady=5, sticky=tk.W)
        self.sample_rate_var = tk.StringVar(value="original")
        sample_rate_combo = ttk.Combobox(settings_frame, textvariable=self.sample_rate_var,
                                         values=["original", "44100", "48000", "96000"], state="readonly", width=15)
        sample_rate_combo.grid(row=3, column=3, padx=5, pady=5, sticky=tk.W)
        ToolTip(sample_rate_combo, "Audio sample rate in Hz")

    def setup_output_panel(self, parent):
        output_frame = ttk.Frame(parent, style='Card.TFrame', padding=10)
        output_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        output_frame.columnconfigure(1, weight=1)

        sep = ttk.Separator(output_frame, orient='horizontal')
        sep.grid(row=0, column=0, columnspan=4, sticky=(tk.W, tk.E), pady=(0, 5))

        tk.Label(output_frame, text="💾  Output", font=('Arial', 11, 'bold'),
                bg=style_obj.secondary, fg=style_obj.text).grid(row=1, column=0, columnspan=4, sticky=tk.W, pady=(0, 10))

        tk.Label(output_frame, text="Format:", bg=style_obj.secondary, fg=style_obj.text).grid(row=2, column=0, padx=(0, 10), pady=5, sticky=tk.W)
        self.format_var = tk.StringVar(value="mp4")
        format_combo = ttk.Combobox(output_frame, textvariable=self.format_var,
                                     values=ALL_FORMATS, state="readonly", width=15)
        format_combo.grid(row=2, column=1, padx=5, pady=5, sticky=tk.W)
        ToolTip(format_combo, "Output file format")

        tk.Label(output_frame, text="Directory:", bg=style_obj.secondary, fg=style_obj.text).grid(row=3, column=0, padx=(0, 10), pady=5, sticky=tk.W)
        self.output_dir_var = tk.StringVar(value=os.getcwd())
        dir_entry = tk.Entry(output_frame, textvariable=self.output_dir_var, font=('Arial', 10),
                            bg=style_obj.surface, fg=style_obj.text, relief='flat', highlightthickness=1,
                            highlightbackground=style_obj.accent)
        dir_entry.grid(row=3, column=1, padx=5, pady=5, sticky=(tk.W, tk.E))
        browse_btn = ttk.Button(output_frame, text="Browse", command=self.browse_output_dir, style='Secondary.TButton')
        browse_btn.grid(row=3, column=2, padx=5, pady=5)
        ToolTip(browse_btn, "Select output directory")

        tk.Label(output_frame, text="Naming:", bg=style_obj.secondary, fg=style_obj.text).grid(row=4, column=0, padx=(0, 10), pady=5, sticky=tk.W)
        self.naming_var = tk.StringVar(value="Original")
        naming_combo = ttk.Combobox(output_frame, textvariable=self.naming_var,
                                     values=["Original", "Original_timestamp", "Custom"], state="readonly", width=15)
        naming_combo.grid(row=4, column=1, padx=5, pady=5, sticky=tk.W)
        ToolTip(naming_combo, "Output file naming pattern")
        self.custom_naming_var = tk.StringVar(value="{name}_converted")
        custom_entry = tk.Entry(output_frame, textvariable=self.custom_naming_var, font=('Arial', 10),
                                bg=style_obj.surface, fg=style_obj.text, relief='flat', width=20)
        custom_entry.grid(row=4, column=2, columnspan=2, padx=5, pady=5, sticky=tk.W)
        ToolTip(custom_entry, "Use {name} for original filename")

        self.overwrite_var = tk.BooleanVar(value=False)
        overwrite_check = tk.Checkbutton(output_frame, text="Overwrite existing files", variable=self.overwrite_var,
                                         bg=style_obj.secondary, fg=style_obj.text, selectcolor=style_obj.surface,
                                         activebackground=style_obj.secondary)
        overwrite_check.grid(row=5, column=0, columnspan=4, padx=(0, 10), pady=(5, 0), sticky=tk.W)

        # Control buttons frame
        control_frame = ttk.Frame(output_frame, style='Card.TFrame')
        control_frame.grid(row=6, column=0, columnspan=4, pady=(10, 0), sticky=(tk.W, tk.E))
        control_frame.columnconfigure(0, weight=1)
        control_frame.columnconfigure(1, weight=1)
        control_frame.columnconfigure(2, weight=1)
        control_frame.columnconfigure(3, weight=1)

        self.convert_btn = ttk.Button(control_frame, text="▶  Convert", command=self.start_conversion,
                                        style='Accent.TButton')
        self.convert_btn.grid(row=0, column=0, padx=5, sticky=tk.EW)
        ToolTip(self.convert_btn, "Start conversion process")

        self.pause_btn = ttk.Button(control_frame, text="⏸  Pause", command=self.toggle_pause,
                                      style='Secondary.TButton', state='disabled')
        self.pause_btn.grid(row=0, column=1, padx=5, sticky=tk.EW)
        ToolTip(self.pause_btn, "Pause/Resume conversion")

        self.stop_btn = ttk.Button(control_frame, text="⏹  Stop", command=self.stop_conversion,
                                     style='Danger.TButton', state='disabled')
        self.stop_btn.grid(row=0, column=2, padx=5, sticky=tk.EW)
        ToolTip(self.stop_btn, "Stop conversion and cancel remaining")

        self.retry_btn = ttk.Button(control_frame, text="🔄  Retry Failed", command=self.retry_failed,
                                      style='Secondary.TButton', state='disabled')
        self.retry_btn.grid(row=0, column=3, padx=5, sticky=tk.EW)
        ToolTip(self.retry_btn, "Retry all failed conversions")

    def setup_status_bar(self, parent):
        status_frame = ttk.Frame(parent, style='Main.TFrame', padding=(0, 5))
        status_frame.grid(row=2, column=0, sticky=(tk.W, tk.E))
        status_frame.columnconfigure(1, weight=1)

        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(status_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.grid(row=0, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 5))
        status_frame.columnconfigure(0, weight=1)

        self.status_label = tk.Label(status_frame, text="✅ Ready", font=('Arial', 9),
                                     bg=style_obj.bg, fg=style_obj.success)
        self.status_label.grid(row=1, column=0, sticky=tk.W)

        self.queue_count_label = tk.Label(status_frame, text="Queue: 0 files", font=('Arial', 9),
                                          bg=style_obj.bg, fg=style_obj.text)
        self.queue_count_label.grid(row=1, column=2, sticky=tk.E)

    def setup_history_tab(self, parent):
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(1, weight=1)

        tk.Label(parent, text="📜  Conversion History", font=('Arial', 14, 'bold'),
                bg=style_obj.bg, fg=style_obj.text).grid(row=0, column=0, sticky=tk.W, pady=(0, 10))

        tree_frame = ttk.Frame(parent, style='Card.TFrame', padding=10)
        tree_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)

        self.history_tree = ttk.Treeview(tree_frame, columns=('input', 'output', 'status'), show='headings', height=15)
        self.history_tree.heading('input', text='Input File')
        self.history_tree.heading('output', text='Output File')
        self.history_tree.heading('status', text='Status')
        self.history_tree.column('input', width=300)
        self.history_tree.column('output', width=300)
        self.history_tree.column('status', width=100, anchor=tk.CENTER)
        self.history_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.history_tree.yview)
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.history_tree.config(yscrollcommand=scrollbar.set)

        btn_frame = ttk.Frame(parent, style='Main.TFrame', padding=(0, 10))
        btn_frame.grid(row=2, column=0, sticky=(tk.W, tk.E))
        reconvert_btn = ttk.Button(btn_frame, text="🔄 Re-convert", command=self.reconvert_selected, style='Secondary.TButton')
        reconvert_btn.pack(side=tk.LEFT, padx=5)
        ToolTip(reconvert_btn, "Re-convert selected history entry")
        clear_hist_btn = ttk.Button(btn_frame, text="🗑️ Clear History", command=self.clear_history, style='Danger.TButton')
        clear_hist_btn.pack(side=tk.LEFT, padx=5)
        ToolTip(clear_hist_btn, "Clear all history entries")

        self.update_history_display()

    def toggle_theme(self):
        style_obj.toggle_theme()
        self.theme_btn.configure(text="🌙" if style_obj.is_dark else "☀️")
        self.setup_styles()
        self.refresh_ui()

    def refresh_ui(self):
        for widget in self.root.winfo_children():
            widget.destroy()
        self.setup_ui()
        self.update_queue_display()

    def format_size(self, size_bytes):
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024**2:
            return f"{size_bytes/1024:.1f} KB"
        elif size_bytes < 1024**3:
            return f"{size_bytes/1024**2:.1f} MB"
        else:
            return f"{size_bytes/1024**3:.1f} GB"

    def format_duration(self, seconds):
        if not seconds:
            return "N/A"
        m, s = divmod(int(seconds), 60)
        h, m = divmod(m, 60)
        if h > 0:
            return f"{h}:{m:02d}:{s:02d}"
        return f"{m}:{s:02d}"

    def add_files(self):
        files = filedialog.askopenfilenames(
            title="Select files",
            filetypes=[
                ("All Media", "*.mp4 *.avi *.mkv *.mov *.webm *.flv *.wmv *.m4v *.3gp *.mpg *.mpeg *.mp3 *.wav *.aac *.flac *.ogg *.m4a *.wma"),
                ("Video Files", "*.mp4 *.avi *.mkv *.mov *.webm *.flv *.wmv *.m4v *.3gp *.mpg *.mpeg"),
                ("Audio Files", "*.mp3 *.wav *.aac *.flac *.ogg *.m4a *.wma"),
                ("All Files", "*.*")
            ]
        )
        for f in files:
            if f not in self.input_files:
                self.input_files.append(f)
                info = get_file_info(f)
                if info:
                    self.file_infos[f] = info
        self.update_queue_display()

    def remove_files(self):
        selection = self.queue_tree.selection()
        for item in reversed(selection):
            values = self.queue_tree.item(item)['values']
            for i, f in enumerate(self.input_files):
                if os.path.basename(f) == values[0] or f == values[0]:
                    self.input_files.pop(i)
                    if f in self.file_infos:
                        del self.file_infos[f]
                    break
        self.update_queue_display()

    def clear_files(self):
        self.input_files.clear()
        self.file_infos.clear()
        self.update_queue_display()

    def update_queue_display(self):
        self.queue_tree.delete(*self.queue_tree.get_children())
        for f in self.input_files:
            info = self.file_infos.get(f, {})
            size = self.format_size(info.get('size', 0))
            duration = self.format_duration(info.get('duration', 0))
            status = "⏳ Waiting"
            self.queue_tree.insert('', tk.END, text=os.path.basename(f),
                                  values=(size, duration, status))
        self.queue_count_label.config(text=f"Queue: {len(self.input_files)} files")

    def on_drag_start(self, event):
        """Start drag operation for reordering"""
        item = self.queue_tree.identify_row(event.y)
        if item:
            self.drag_start_item = item
            self.drag_start_index = self.queue_tree.index(item)

    def on_drag_motion(self, event):
        """Handle drag motion - highlight target row"""
        if self.drag_start_item is None:
            return
        target_item = self.queue_tree.identify_row(event.y)
        if target_item and target_item != self.drag_start_item:
            # Visual feedback: change background of target row
            children = self.queue_tree.get_children()
            for child in children:
                self.queue_tree.item(child, tags=())
            self.queue_tree.item(target_item, tags=('drag_target',))
            self.queue_tree.tag_configure('drag_target', background=style_obj.accent)

    def on_drag_release(self, event):
        """Complete drag operation - reorder files"""
        if self.drag_start_item is None:
            return
        target_item = self.queue_tree.identify_row(event.y)
        if target_item and target_item != self.drag_start_item:
            # Get indices
            start_idx = self.drag_start_index
            target_idx = self.queue_tree.index(target_item)
            # Reorder input_files list
            file_to_move = self.input_files.pop(start_idx)
            self.input_files.insert(target_idx, file_to_move)
            # Update display
            self.update_queue_display()
            self.status_label.config(text=f"Reordered queue: moved file to position {target_idx+1}")
        # Reset drag state
        self.drag_start_item = None
        self.drag_start_index = None
        # Clear tag
        for child in self.queue_tree.get_children():
            self.queue_tree.item(child, tags=())

    def browse_output_dir(self):
        directory = filedialog.askdirectory(initialdir=self.output_dir_var.get())
        if directory:
            self.output_dir_var.set(directory)

    def get_settings(self):
        settings = {'quality': self.quality_var.get()}
        resolution = self.resolution_var.get()
        if resolution != 'original':
            settings['resolution'] = resolution
        channels = self.channels_var.get()
        if channels != 'original':
            settings['audio_channels'] = int(channels)
        sample_rate = self.sample_rate_var.get()
        if sample_rate != 'original':
            settings['sample_rate'] = int(sample_rate)
        return settings

    def get_output_filename(self, input_file, output_format):
        base_name = os.path.splitext(os.path.basename(input_file))[0]
        naming = self.naming_var.get()
        if naming == "Original_timestamp":
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            return f"{base_name}_{timestamp}.{output_format}"
        elif naming == "Custom":
            pattern = self.custom_naming_var.get()
            return f"{pattern.replace('{name}', base_name)}.{output_format}"
        return f"{base_name}.{output_format}"

    def start_conversion(self):
        if not self.input_files:
            messagebox.showwarning("No Files", "Please add files to convert")
            return
        if self.is_converting:
            messagebox.showinfo("Busy", "Conversion already in progress")
            return
        output_format = self.format_var.get()
        output_dir = self.output_dir_var.get()
        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
        settings = self.get_settings()
        self.is_converting = True
        self.conversion_state = 'running'
        self.failed_files = []  # Reset failed files list
        self.convert_btn.configure(state='disabled')
        self.pause_btn.configure(state='normal')
        self.stop_btn.configure(state='normal')
        self.retry_btn.configure(state='disabled')
        self.progress_var.set(0)
        # Reset stop event
        from converter import reset_stop
        reset_stop()
        thread = threading.Thread(target=self.convert_files, args=(output_format, output_dir, settings), daemon=True)
        thread.start()

    def toggle_pause(self):
        from converter import pause_conversion, resume_conversion, is_paused
        if self.conversion_state == 'running':
            pause_conversion()
            self.conversion_state = 'paused'
            self.pause_btn.configure(text="▶  Resume")
            self.status_label.configure(text="⏸ Paused", fg=style_obj.warning)
        elif self.conversion_state == 'paused':
            resume_conversion()
            self.conversion_state = 'running'
            self.pause_btn.configure(text="⏸  Pause")
            self.status_label.configure(text="Converting...", fg=style_obj.text)

    def stop_conversion(self):
        if messagebox.askyesno("Stop Conversion", "Are you sure you want to stop the conversion queue?"):
            from converter import stop_conversion
            stop_conversion()
            self.conversion_state = 'stopping'
            self.status_label.configure(text="⏹ Stopping...", fg=style_obj.error)
            self.pause_btn.configure(state='disabled')
            self.stop_btn.configure(state='disabled')

    def retry_failed(self):
        if not self.failed_files:
            messagebox.showinfo("No Failed Files", "There are no failed conversions to retry.")
            return
        # Move failed files back to input queue
        self.input_files.extend(self.failed_files)
        self.failed_files = []
        self.update_queue_display()
        self.retry_btn.configure(state='disabled')
        self.status_label.configure(text="✅ Failed files moved to queue", fg=style_obj.success)

    def convert_files(self, output_format, output_dir, settings):
        total = len(self.input_files)
        from converter import stop_event

        for i, input_file in enumerate(self.input_files[:]):  # Use slice copy
            # Check if stop was requested
            if stop_event.is_set():
                self.root.after(0, self.update_queue_status, input_file, "⏹ Stopped")
                # Mark remaining files as stopped
                for remaining in self.input_files[i:]:
                    self.root.after(0, self.update_queue_status, remaining, "⏹ Stopped")
                break

            output_file = os.path.join(output_dir, self.get_output_filename(input_file, output_format))
            if not self.overwrite_var.get() and os.path.exists(output_file):
                self.root.after(0, self.update_queue_status, input_file, "⚠️ Skipped")
                continue

            self.root.after(0, self.update_queue_status, input_file, "🔄 Converting")
            self.root.after(0, self.status_label.config, {"text": f"Converting: {os.path.basename(input_file)}"})

            def progress_callback(p):
                overall = ((i + p/100) / total) * 100
                self.root.after(0, self.progress_var.set, overall)

            success, msg = convert_file(input_file, output_file, progress_callback, settings)
            status = "✅ Done" if success else "❌ Error"
            self.root.after(0, self.update_queue_status, input_file, status)
            self.root.after(0, self.add_to_history, input_file, output_file, success, msg)

            # Track failed files for retry
            if not success and msg != "Conversion stopped by user":
                self.failed_files.append(input_file)

        self.root.after(0, self.conversion_complete)

    def update_queue_status(self, input_file, status):
        for item in self.queue_tree.get_children():
            values = list(self.queue_tree.item(item)['values'])
            if values and input_file in self.input_files:
                idx = list(self.queue_tree.get_children()).index(item)
                if idx < len(self.input_files) and self.input_files[idx] == input_file:
                    values[2] = status
                    self.queue_tree.item(item, values=values)
                    break

    def update_progress(self, value):
        self.progress_var.set(value)

    def conversion_complete(self):
        self.is_converting = False
        self.conversion_state = 'idle'
        self.convert_btn.configure(state='normal')
        self.pause_btn.configure(state='disabled', text="⏸  Pause")
        self.stop_btn.configure(state='disabled')
        self.progress_var.set(100)

        # Enable retry button if there were failures
        if self.failed_files:
            self.retry_btn.configure(state='normal')
            self.status_label.configure(text=f"⚠️ Complete with {len(self.failed_files)} failures", fg=style_obj.warning)
        else:
            self.status_label.configure(text="✅ Conversion complete!", fg=style_obj.success)
            messagebox.showinfo("Complete", "All files converted successfully!")

    def add_to_history(self, input_file, output_file, success, msg):
        entry = {
            'timestamp': datetime.now().isoformat(),
            'input': input_file,
            'output': output_file,
            'success': success,
            'message': msg
        }
        self.history.append(entry)
        self.save_history()
        self.update_history_display()

    def load_history(self):
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r') as f:
                    self.history = json.load(f)
            except:
                self.history = []
        else:
            self.history = []

    def save_history(self):
        with open(self.history_file, 'w') as f:
            json.dump(self.history, f, indent=2)

    def update_history_display(self):
        if hasattr(self, 'history_tree'):
            self.history_tree.delete(*self.history_tree.get_children())
            for entry in reversed(self.history[-100:]):
                date = datetime.fromisoformat(entry['timestamp']).strftime('%Y-%m-%d %H:%M')
                status = "✅ Success" if entry['success'] else "❌ Failed"
                self.history_tree.insert('', 0, values=(
                    os.path.basename(entry['input']),
                    os.path.basename(entry['output']),
                    status
                ))

    def setup_watch_tab(self, parent):
        """Setup the Watch Folder tab"""
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(1, weight=1)

        # Title
        tk.Label(parent, text="👁️ Watch Folder Mode", font=('Arial', 14, 'bold'),
                bg=style_obj.bg, fg=style_obj.accent).grid(row=0, column=0, sticky=tk.W, pady=(0, 10))

        # Main frame
        main_frame = ttk.Frame(parent, style='Card.TFrame', padding=10)
        main_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        main_frame.columnconfigure(1, weight=1)

        # Input folder
        tk.Label(main_frame, text="Watch Folder:", bg=style_obj.secondary, fg=style_obj.text).grid(
            row=0, column=0, sticky=tk.W, padx=(0, 10), pady=5)
        self.watch_input_var = tk.StringVar()
        tk.Entry(main_frame, textvariable=self.watch_input_var, font=('Arial', 10),
                bg=style_obj.surface, fg=style_obj.text, relief='flat').grid(
            row=0, column=1, sticky=(tk.W, tk.E), pady=5)
        ttk.Button(main_frame, text="Browse", command=self.browse_watch_input,
                   style='Secondary.TButton').grid(row=0, column=2, padx=5, pady=5)

        # Output folder
        tk.Label(main_frame, text="Output Folder:", bg=style_obj.secondary, fg=style_obj.text).grid(
            row=1, column=0, sticky=tk.W, padx=(0, 10), pady=5)
        self.watch_output_var = tk.StringVar()
        tk.Entry(main_frame, textvariable=self.watch_output_var, font=('Arial', 10),
                bg=style_obj.surface, fg=style_obj.text, relief='flat').grid(
            row=1, column=1, sticky=(tk.W, tk.E), pady=5)
        ttk.Button(main_frame, text="Browse", command=self.browse_watch_output,
                   style='Secondary.TButton').grid(row=1, column=2, padx=5, pady=5)

        # Format selection
        tk.Label(main_frame, text="Output Format:", bg=style_obj.secondary, fg=style_obj.text).grid(
            row=2, column=0, sticky=tk.W, padx=(0, 10), pady=5)
        self.watch_format_var = tk.StringVar(value="mp4")
        ttk.Combobox(main_frame, textvariable=self.watch_format_var,
                      values=ALL_FORMATS, state="readonly", width=15).grid(
            row=2, column=1, sticky=tk.W, pady=5)

        # Control buttons
        btn_frame = ttk.Frame(main_frame, style='Card.TFrame')
        btn_frame.grid(row=3, column=0, columnspan=3, pady=(10, 5))
        self.watch_btn = ttk.Button(btn_frame, text="▶ Start Watching",
                                    command=self.toggle_watch, style='Accent.TButton')
        self.watch_btn.pack(side=tk.LEFT, padx=5)
        ToolTip(self.watch_btn, "Start/Stop watching folder")

        # Status
        self.watch_status_label = tk.Label(main_frame, text="⏹ Not watching",
                                            font=('Arial', 9), bg=style_obj.secondary, fg=style_obj.text)
        self.watch_status_label.grid(row=4, column=0, columnspan=3, sticky=tk.W, pady=(10, 0))

        # Conversion log
        tk.Label(main_frame, text="Recent Activity:", bg=style_obj.secondary, fg=style_obj.text).grid(
            row=5, column=0, columnspan=3, sticky=tk.W, pady=(10, 5))
        self.watch_log = tk.Text(main_frame, height=10, font=('Arial', 9),
                                 bg=style_obj.surface, fg=style_obj.text,
                                 relief='flat', state='disabled')
        self.watch_log.grid(row=6, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S))
        main_frame.rowconfigure(6, weight=1)

    def browse_watch_input(self):
        directory = filedialog.askdirectory(title="Select folder to watch")
        if directory:
            self.watch_input_var.set(directory)

    def browse_watch_output(self):
        directory = filedialog.askdirectory(title="Select output folder")
        if directory:
            self.watch_output_var.set(directory)

    def toggle_watch(self):
        if hasattr(self, 'watching') and self.watching:
            # Stop watching
            self.watching = False
            self.watch_btn.configure(text="▶ Start Watching")
            self.watch_status_label.configure(text="⏹ Stopped watching", fg=style_obj.text)
        else:
            # Start watching
            input_dir = self.watch_input_var.get()
            output_dir = self.watch_output_var.get()
            if not input_dir or not os.path.exists(input_dir):
                messagebox.showwarning("Invalid Folder", "Please select a valid input folder to watch")
                return
            if not output_dir:
                output_dir = input_dir
            if not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)
            self.watching = True
            self.watch_btn.configure(text="⏹ Stop Watching")
            self.watch_status_label.configure(text=f"👁️ Watching: {input_dir}", fg=style_obj.success)
            # Start watch thread
            output_format = self.watch_format_var.get()
            thread = threading.Thread(target=self.watch_folder_thread,
                                     args=(input_dir, output_dir, output_format),
                                     daemon=True)
            thread.start()

    def watch_folder_thread(self, input_dir, output_dir, output_format):
        """Thread function for watch folder"""
        from converter import watch_folder

        def callback(input_file, output_file, status):
            if input_file:
                msg = f"{status}: {os.path.basename(input_file)}"
                self.root.after(0, self.add_watch_log, msg)
            else:
                self.root.after(0, self.add_watch_log, f"Error: {status}")

        def stop_check():
            return not getattr(self, 'watching', False)

        watch_folder(input_dir, output_dir, output_format,
                     settings=self.get_settings(),
                     callback=callback,
                     stop_check=stop_check)

    def add_watch_log(self, message):
        """Add message to watch log"""
        self.watch_log.config(state='normal')
        import datetime
        timestamp = datetime.datetime.now().strftime('%H:%M:%S')
        self.watch_log.insert(tk.END, f"[{timestamp}] {message}\n")
        self.watch_log.see(tk.END)
        self.watch_log.config(state='disabled')

    def reconvert_selected(self):
        selection = self.history_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select an entry from history")
            return
        item = selection[0]
        values = self.history_tree.item(item)['values']
        input_file = self.find_history_input(values[0])
        if input_file and os.path.exists(input_file):
            self.input_files = [input_file]
            self.update_queue_display()
            self.notebook.select(0)
        else:
            messagebox.showerror("File Not Found", "Original input file no longer exists")

    def find_history_input(self, basename):
        for entry in self.history:
            if os.path.basename(entry['input']) == basename:
                return entry['input']
        return None

    def clear_history(self):
        if messagebox.askyesno("Clear History", "Are you sure you want to clear all history?"):
            self.history = []
            self.save_history()
            self.update_history_display()

def main():
    root = tk.Tk()
    app = FileConverterGUI(root)
    root.mainloop()

if __name__ == '__main__':
    main()

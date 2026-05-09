import customtkinter as ctk
from tkinter import ttk, filedialog, messagebox
from tkinterdnd2 import DND_FILES, TkinterDnD
import threading
import os
import json
import subprocess
from datetime import datetime
from converter import (convert_file, batch_convert, VIDEO_FORMATS, AUDIO_FORMATS,
                       QUALITY_PRESETS, RESOLUTION_MAP, get_file_info, get_media_type)

ALL_FORMATS = sorted(set(VIDEO_FORMATS + AUDIO_FORMATS))

MEDIA_FILTERS = [
    ("All Media", "*.mp4 *.avi *.mkv *.mov *.webm *.flv *.wmv *.m4v *.3gp *.mpg *.mpeg *.mp3 *.wav *.aac *.flac *.ogg *.m4a *.wma"),
    ("Video Files", "*.mp4 *.avi *.mkv *.mov *.webm *.flv *.wmv *.m4v *.3gp *.mpg *.mpeg"),
    ("Audio Files", "*.mp3 *.wav *.aac *.flac *.ogg *.m4a *.wma"),
    ("All Files", "*.*"),
]

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SETTINGS_FILE = os.path.join(BASE_DIR, "settings.json")


class DnDCTk(ctk.CTk, TkinterDnD.DnDWrapper):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.TkdndVersion = TkinterDnD._require(self)


def native_file_dialog(title="Select files", multiple=False, directory=False, initialdir=None):
    native_ran = False

    if _check_command("zenity"):
        native_ran = True
        cmd = ["zenity", "--file-selection", "--title", title]
        if multiple:
            cmd.append("--multiple")
        if directory:
            cmd.append("--directory")
        if initialdir:
            cmd.extend(["--filename", initialdir + "/"])
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0 and result.stdout.strip():
                paths = result.stdout.strip().split("|")
                return paths if multiple else paths[0] if paths else None
            return [] if multiple else None
        except:
            native_ran = False

    if _check_command("kdialog") and not native_ran:
        native_ran = True
        if directory:
            cmd = ["kdialog", "--title", title, "--getexistingdirectory"]
            if initialdir:
                cmd.append(initialdir)
        else:
            filters = " *.".join(f[1].split(" ")[1:]) if MEDIA_FILTERS else "*"
            cmd = ["kdialog", "--title", title, "--getopenfilename", initialdir or "",
                   f"*.{filters}", title]
            if multiple:
                cmd = ["kdialog", "--title", title, "--getopenfilenames", initialdir or "",
                       f"*.{filters}", title]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0 and result.stdout.strip():
                paths = result.stdout.strip().split("\n")
                return paths if multiple else paths[0] if paths else None
            return [] if multiple else None
        except:
            native_ran = False

    if not native_ran:
        if directory:
            return filedialog.askdirectory(initialdir=initialdir, title=title)
        elif multiple:
            return filedialog.askopenfilenames(title=title, initialdir=initialdir,
                                               filetypes=MEDIA_FILTERS)
        else:
            return filedialog.askopenfilename(title=title, initialdir=initialdir,
                                              filetypes=MEDIA_FILTERS)
    return [] if multiple else None


def _check_command(cmd):
    try:
        subprocess.run(["which", cmd], capture_output=True, check=True)
        return True
    except:
        return False


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
        x = event.x_root + 15
        y = event.y_root + 15
        self.tip_window = tw = ctk.CTkToplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        tw.attributes("-topmost", True)
        tw.lift()
        label = ctk.CTkLabel(tw, text=self.text, justify="left", font=("Arial", 9))
        label.pack(ipadx=5, ipady=3)

    def hide_tip(self, event=None):
        if self.tip_window:
            self.tip_window.destroy()
            self.tip_window = None


class FileConverterGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("njFile-convertor")
        self.root.geometry("950x750")
        self.input_files = []
        self.file_infos = {}
        self.is_converting = False
        self.is_paused = False
        self.failed_files = []
        self.conversion_state = 'idle'
        self.file_overrides = {}
        self.history_file = os.path.join(BASE_DIR, "history.json")

        self.set_window_icon()
        self.root.tk.call('wm', 'class', self.root, 'njFile-convertor')
        self.load_history()
        self.load_settings()
        self.setup_treeview_style()
        self.setup_ui()
        self.bind_shortcuts()

    def set_window_icon(self):
        icon_path = os.path.join(BASE_DIR, "njfile-convertor.png")
        if os.path.exists(icon_path):
            try:
                from PIL import Image, ImageTk
                img = ImageTk.PhotoImage(Image.open(icon_path))
                self.root.iconphoto(True, img)
                self._icon_img = img
            except Exception:
                pass

    def bind_shortcuts(self):
        self.root.bind('<Control-o>', lambda e: self.add_files())
        self.root.bind('<Control-v>', lambda e: self.start_conversion())
        self.root.bind('<Delete>', lambda e: self.remove_files())
        self.root.bind('<Escape>', lambda e: self.stop_conversion() if self.is_converting else None)

    def load_settings(self):
        defaults = dict(quality='medium', resolution='original', format='mp4',
                        channels='original', sample_rate='original',
                        output_dir=os.getcwd(), naming='Original',
                        custom_naming='{name}_converted', overwrite=False,
                        theme='dark', geometry='950x750')
        self._settings = defaults.copy()
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE) as f:
                    saved = json.load(f)
                self._settings.update(saved)
            except Exception:
                pass

    def save_settings(self):
        s = self._settings
        s['quality'] = self.quality_var.get() if hasattr(self, 'quality_var') else s.get('quality', 'medium')
        s['resolution'] = self.resolution_var.get() if hasattr(self, 'resolution_var') else s.get('resolution', 'original')
        s['format'] = self.format_var.get() if hasattr(self, 'format_var') else s.get('format', 'mp4')
        s['channels'] = self.channels_var.get() if hasattr(self, 'channels_var') else s.get('channels', 'original')
        s['sample_rate'] = self.sample_rate_var.get() if hasattr(self, 'sample_rate_var') else s.get('sample_rate', 'original')
        s['output_dir'] = self.output_dir_var.get() if hasattr(self, 'output_dir_var') else s.get('output_dir', os.getcwd())
        s['naming'] = self.naming_var.get() if hasattr(self, 'naming_var') else s.get('naming', 'Original')
        s['custom_naming'] = self.custom_naming_var.get() if hasattr(self, 'custom_naming_var') else s.get('custom_naming', '{name}_converted')
        s['overwrite'] = self.overwrite_var.get() if hasattr(self, 'overwrite_var') else s.get('overwrite', False)
        s['theme'] = 'dark' if ctk.get_appearance_mode() == 'Dark' else 'light'
        s['geometry'] = self.root.geometry()
        try:
            with open(SETTINGS_FILE, 'w') as f:
                json.dump(self._settings, f, indent=2)
        except Exception:
            pass

    def on_closing(self):
        self.save_settings()
        self.save_history()
        self.root.destroy()

    def setup_treeview_style(self):
        self.tree_style = ttk.Style()
        self.tree_style.theme_use('clam')
        self.update_treeview_theme()

    def update_treeview_theme(self):
        is_dark = ctk.get_appearance_mode() == "Dark"
        if is_dark:
            self.tree_style.configure('Treeview', background='#2b2b2b', foreground='#ffffff', fieldbackground='#2b2b2b', rowheight=25)
            self.tree_style.configure('Treeview.Heading', background='#1e1e1e', foreground='#ffffff')
            self.tree_style.map('Treeview', background=[('selected', '#1f5382')])
        else:
            self.tree_style.configure('Treeview', background='#ffffff', foreground='#000000', fieldbackground='#ffffff', rowheight=25)
            self.tree_style.configure('Treeview.Heading', background='#f0f0f0', foreground='#000000')
            self.tree_style.map('Treeview', background=[('selected', '#0078d7')])

    def setup_ui(self):
        s = self._settings
        if s.get('theme') == 'light':
            ctk.set_appearance_mode("light")

        geom = s.get('geometry', '950x750')
        self.root.geometry(geom)

        main_container = ctk.CTkFrame(self.root, fg_color="transparent")
        main_container.pack(fill="both", expand=True, padx=15, pady=15)
        main_container.grid_columnconfigure(0, weight=1)

        header_frame = ctk.CTkFrame(main_container, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        header_frame.grid_columnconfigure(1, weight=1)

        title_label = ctk.CTkLabel(header_frame, text="\u26a1 njFile-convertor", font=("Arial", 20, "bold"))
        title_label.grid(row=0, column=0, sticky="w")

        btn_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        btn_frame.grid(row=0, column=2, sticky="e")

        self.theme_btn = ctk.CTkButton(btn_frame, text="\U0001f319", command=self.toggle_theme, width=40)
        self.theme_btn.pack(side="right", padx=(5, 0))
        ToolTip(self.theme_btn, "Toggle Dark/Light Theme")

        history_btn = ctk.CTkButton(btn_frame, text="\U0001f4dc History", command=lambda: self.tabview.set("\U0001f4dc  History"))
        history_btn.pack(side="right", padx=5)
        ToolTip(history_btn, "View Conversion History")

        self.tabview = ctk.CTkTabview(main_container)
        self.tabview.grid(row=1, column=0, sticky="nsew", pady=(0, 10))
        main_container.grid_rowconfigure(1, weight=1)

        convert_tab = self.tabview.add("\U0001f504  Convert")
        history_tab = self.tabview.add("\U0001f4dc  History")
        watch_tab = self.tabview.add("\U0001f441\ufe0f  Watch Folder")

        self.setup_convert_tab(convert_tab)
        self.setup_history_tab(history_tab)
        self.setup_watch_tab(watch_tab)

        self.setup_status_bar(main_container)

        # Apply saved settings to widgets
        self.quality_var.set(s.get('quality', 'medium'))
        self.resolution_var.set(s.get('resolution', 'original'))
        self.format_var.set(s.get('format', 'mp4'))
        self.channels_var.set(s.get('channels', 'original'))
        self.sample_rate_var.set(s.get('sample_rate', 'original'))
        self.output_dir_var.set(s.get('output_dir', os.getcwd()))
        self.naming_var.set(s.get('naming', 'Original'))
        self.custom_naming_var.set(s.get('custom_naming', '{name}_converted'))
        self.overwrite_var.set(s.get('overwrite', False))

    def setup_convert_tab(self, parent):
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(2, weight=1)

        drop_frame = ctk.CTkFrame(parent, fg_color="transparent", border_width=2,
                                   border_color=("deep sky blue", "royal blue"), height=80)
        drop_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        drop_frame.grid_columnconfigure(0, weight=1)
        drop_frame.bind('<Button-1>', lambda e: self.add_files())

        drop_label = ctk.CTkLabel(drop_frame, text="\U0001f4c1  Click here or drag files to add", font=("Arial", 12))
        drop_label.grid(row=0, column=0, pady=25)
        drop_label.bind('<Button-1>', lambda e: self.add_files())

        drop_frame.bind('<Enter>', lambda e: drop_frame.configure(border_color=("green", "green2")))
        drop_frame.bind('<Leave>', lambda e: drop_frame.configure(border_color=("deep sky blue", "royal blue")))

        self.root.drop_target_register(DND_FILES)
        self.root.dnd_bind('<<Drop>>', self.on_file_drop)

        self.drop_frame = drop_frame

        queue_frame = ctk.CTkFrame(parent)
        queue_frame.grid(row=1, column=0, sticky="ew", pady=(0, 5))
        queue_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(queue_frame, text="\U0001f4cb  Conversion Queue", font=("Arial", 11, "bold")).grid(
            row=0, column=0, sticky="w", pady=(0, 5), padx=10)

        tree_frame = ctk.CTkFrame(queue_frame, fg_color="transparent")
        tree_frame.grid(row=1, column=0, sticky="ewns", padx=10)
        tree_frame.grid_columnconfigure(0, weight=1)
        tree_frame.grid_rowconfigure(0, weight=1)

        self.queue_tree = ttk.Treeview(tree_frame, columns=('size', 'duration', 'status'), show='tree headings', height=6)
        self.queue_tree.heading('#0', text='File Name')
        self.queue_tree.heading('size', text='Size')
        self.queue_tree.heading('duration', text='Duration')
        self.queue_tree.heading('status', text='Status')
        self.queue_tree.column('#0', width=350)
        self.queue_tree.column('size', width=100, anchor='center')
        self.queue_tree.column('duration', width=100, anchor='center')
        self.queue_tree.column('status', width=140, anchor='center')
        self.queue_tree.grid(row=0, column=0, sticky="ewns")

        self.drag_start_item = None
        self.queue_tree.bind('<ButtonPress-1>', self.on_drag_start)
        self.queue_tree.bind('<B1-Motion>', self.on_drag_motion)
        self.queue_tree.bind('<ButtonRelease-1>', self.on_drag_release)
        self.queue_tree.bind('<<TreeviewSelect>>', self.on_queue_select)
        self.queue_tree.bind('<Double-1>', self.on_queue_double_click)

        scrollbar = ttk.Scrollbar(tree_frame, orient='vertical', command=self.queue_tree.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.queue_tree.config(yscrollcommand=scrollbar.set)

        btn_frame = ctk.CTkFrame(queue_frame, fg_color="transparent")
        btn_frame.grid(row=2, column=0, sticky="ew", pady=(5, 0), padx=10)

        add_btn = ctk.CTkButton(btn_frame, text="\u2795 Add Files", command=self.add_files)
        add_btn.pack(side="left", padx=5)
        ToolTip(add_btn, "Add media files to queue")

        remove_btn = ctk.CTkButton(btn_frame, text="\u2796 Remove", command=self.remove_files)
        remove_btn.pack(side="left", padx=5)
        ToolTip(remove_btn, "Remove selected files from queue")

        clear_btn = ctk.CTkButton(btn_frame, text="\U0001f5d1\ufe0f Clear All", command=self.clear_files,
                                   fg_color=("#d32f2f", "#b71c1c"), hover_color=("#b71c1c", "#d32f2f"))
        clear_btn.pack(side="left", padx=5)
        ToolTip(clear_btn, "Clear all files from queue")

        # Detail panel
        self.detail_frame = ctk.CTkFrame(queue_frame, fg_color="transparent", height=28)
        self.detail_frame.grid(row=3, column=0, sticky="ew", pady=(2, 0), padx=10)
        self.detail_frame.grid_columnconfigure((0, 1, 2, 3, 4, 5), weight=1)

        self.detail_labels = {}
        fields = [('codec', 'Codec'), ('resolution', 'Res'), ('bitrate', 'Bitrate'),
                  ('duration', 'Duration'), ('fps', 'FPS'), ('audio', 'Audio')]
        for i, (key, label) in enumerate(fields):
            lbl = ctk.CTkLabel(self.detail_frame, text=f"{label}: --", font=("Arial", 9))
            lbl.grid(row=0, column=i, padx=2, sticky="w")
            self.detail_labels[key] = lbl

        parent.grid_rowconfigure(1, weight=1)
        self.setup_settings_panel(parent)
        self.setup_output_panel(parent)

    def setup_settings_panel(self, parent):
        settings_frame = ctk.CTkFrame(parent)
        settings_frame.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        settings_frame.grid_columnconfigure(1, weight=1)
        settings_frame.grid_columnconfigure(3, weight=1)

        sep = ctk.CTkFrame(settings_frame, height=2, fg_color=("gray70", "gray30"))
        sep.grid(row=0, column=0, columnspan=4, sticky="ew", pady=(0, 5))

        ctk.CTkLabel(settings_frame, text="\u2699\ufe0f  Settings", font=("Arial", 11, "bold")).grid(
            row=1, column=0, columnspan=4, sticky="w", pady=(0, 10))

        ctk.CTkLabel(settings_frame, text="Quality:").grid(row=2, column=0, padx=(0, 10), pady=5, sticky="w")
        self.quality_var = ctk.StringVar()
        quality_combo = ctk.CTkComboBox(settings_frame, variable=self.quality_var,
                                         values=list(QUALITY_PRESETS.keys()), width=140)
        quality_combo.grid(row=2, column=1, padx=5, pady=5, sticky="w")
        ToolTip(quality_combo, "Low=small file, High=best quality")

        ctk.CTkLabel(settings_frame, text="Resolution:").grid(row=2, column=2, padx=(20, 10), pady=5, sticky="w")
        self.resolution_var = ctk.StringVar()
        resolution_combo = ctk.CTkComboBox(settings_frame, variable=self.resolution_var,
                                            values=list(RESOLUTION_MAP.keys()), width=140)
        resolution_combo.grid(row=2, column=3, padx=5, pady=5, sticky="w")
        ToolTip(resolution_combo, "Output video resolution")

        ctk.CTkLabel(settings_frame, text="Audio Channels:").grid(row=3, column=0, padx=(0, 10), pady=5, sticky="w")
        self.channels_var = ctk.StringVar()
        channels_combo = ctk.CTkComboBox(settings_frame, variable=self.channels_var,
                                          values=["original", "1", "2"], width=140)
        channels_combo.grid(row=3, column=1, padx=5, pady=5, sticky="w")
        ToolTip(channels_combo, "1=Mono, 2=Stereo")

        ctk.CTkLabel(settings_frame, text="Sample Rate:").grid(row=3, column=2, padx=(20, 10), pady=5, sticky="w")
        self.sample_rate_var = ctk.StringVar()
        sample_rate_combo = ctk.CTkComboBox(settings_frame, variable=self.sample_rate_var,
                                             values=["original", "44100", "48000", "96000"], width=140)
        sample_rate_combo.grid(row=3, column=3, padx=5, pady=5, sticky="w")
        ToolTip(sample_rate_combo, "Audio sample rate in Hz")

    def setup_output_panel(self, parent):
        output_frame = ctk.CTkFrame(parent)
        output_frame.grid(row=3, column=0, sticky="ew", pady=(0, 10))
        output_frame.grid_columnconfigure(1, weight=1)

        sep = ctk.CTkFrame(output_frame, height=2, fg_color=("gray70", "gray30"))
        sep.grid(row=0, column=0, columnspan=4, sticky="ew", pady=(0, 5))

        ctk.CTkLabel(output_frame, text="\U0001f4be  Output", font=("Arial", 11, "bold")).grid(
            row=1, column=0, columnspan=4, sticky="w", pady=(0, 10))

        ctk.CTkLabel(output_frame, text="Format:").grid(row=2, column=0, padx=(0, 10), pady=5, sticky="w")
        self.format_var = ctk.StringVar()
        format_combo = ctk.CTkComboBox(output_frame, variable=self.format_var,
                                        values=ALL_FORMATS, width=140)
        format_combo.grid(row=2, column=1, padx=5, pady=5, sticky="w")
        ToolTip(format_combo, "Output file format (double-click a file in queue to override per-file)")

        ctk.CTkLabel(output_frame, text="Directory:").grid(row=3, column=0, padx=(0, 10), pady=5, sticky="w")
        self.output_dir_var = ctk.StringVar()
        dir_entry = ctk.CTkEntry(output_frame, textvariable=self.output_dir_var)
        dir_entry.grid(row=3, column=1, padx=5, pady=5, sticky="ew")
        browse_btn = ctk.CTkButton(output_frame, text="Browse", command=self.browse_output_dir)
        browse_btn.grid(row=3, column=2, padx=5, pady=5)
        ToolTip(browse_btn, "Select output directory")

        ctk.CTkLabel(output_frame, text="Naming:").grid(row=4, column=0, padx=(0, 10), pady=5, sticky="w")
        self.naming_var = ctk.StringVar()
        naming_combo = ctk.CTkComboBox(output_frame, variable=self.naming_var,
                                        values=["Original", "Original_timestamp", "Custom"], width=140)
        naming_combo.grid(row=4, column=1, padx=5, pady=5, sticky="w")
        ToolTip(naming_combo, "Output file naming pattern")

        self.custom_naming_var = ctk.StringVar()
        custom_entry = ctk.CTkEntry(output_frame, textvariable=self.custom_naming_var, width=180)
        custom_entry.grid(row=4, column=2, columnspan=2, padx=5, pady=5, sticky="w")
        ToolTip(custom_entry, "Use {name} for original filename")

        self.overwrite_var = ctk.BooleanVar(value=False)
        overwrite_check = ctk.CTkCheckBox(output_frame, text="Overwrite existing files", variable=self.overwrite_var)
        overwrite_check.grid(row=5, column=0, columnspan=4, padx=(0, 10), pady=(5, 0), sticky="w")

        control_frame = ctk.CTkFrame(output_frame, fg_color="transparent")
        control_frame.grid(row=6, column=0, columnspan=4, pady=(10, 0), sticky="ew")
        control_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self.convert_btn = ctk.CTkButton(control_frame, text="\u25b6  Convert", command=self.start_conversion)
        self.convert_btn.grid(row=0, column=0, padx=5, sticky="ew")
        ToolTip(self.convert_btn, "Start conversion process")

        self.pause_btn = ctk.CTkButton(control_frame, text="\u23f8  Pause", command=self.toggle_pause, state="disabled")
        self.pause_btn.grid(row=0, column=1, padx=5, sticky="ew")
        ToolTip(self.pause_btn, "Pause/Resume conversion")

        self.stop_btn = ctk.CTkButton(control_frame, text="\u23f9  Stop", command=self.stop_conversion,
                                       fg_color=("#d32f2f", "#b71c1c"), hover_color=("#b71c1c", "#d32f2f"),
                                       state="disabled")
        self.stop_btn.grid(row=0, column=2, padx=5, sticky="ew")
        ToolTip(self.stop_btn, "Stop conversion and cancel remaining")

        self.retry_btn = ctk.CTkButton(control_frame, text="\U0001f504  Retry Failed", command=self.retry_failed,
                                        state="disabled")
        self.retry_btn.grid(row=0, column=3, padx=5, sticky="ew")
        ToolTip(self.retry_btn, "Retry all failed conversions")

    def setup_status_bar(self, parent):
        status_frame = ctk.CTkFrame(parent, fg_color="transparent")
        status_frame.grid(row=2, column=0, sticky="ew")
        status_frame.grid_columnconfigure(1, weight=1)

        self.progress_bar = ctk.CTkProgressBar(status_frame)
        self.progress_bar.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, 5))
        self.progress_bar.set(0)
        status_frame.grid_columnconfigure(0, weight=1)

        self.status_label = ctk.CTkLabel(status_frame, text="\u2705 Ready", font=("Arial", 9))
        self.status_label.grid(row=1, column=0, sticky="w")

        self.queue_count_label = ctk.CTkLabel(status_frame, text="Queue: 0 files", font=("Arial", 9))
        self.queue_count_label.grid(row=1, column=2, sticky="e")

    def setup_history_tab(self, parent):
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(parent, text="\U0001f4dc  Conversion History", font=("Arial", 14, "bold")).grid(
            row=0, column=0, sticky="w", pady=(0, 10))

        tree_frame = ctk.CTkFrame(parent)
        tree_frame.grid(row=1, column=0, sticky="ewns")
        tree_frame.grid_columnconfigure(0, weight=1)
        tree_frame.grid_rowconfigure(0, weight=1)

        self.history_tree = ttk.Treeview(tree_frame, columns=('input', 'output', 'status'), show='headings', height=15)
        self.history_tree.heading('input', text='Input File')
        self.history_tree.heading('output', text='Output File')
        self.history_tree.heading('status', text='Status')
        self.history_tree.column('input', width=300)
        self.history_tree.column('output', width=300)
        self.history_tree.column('status', width=100, anchor='center')
        self.history_tree.grid(row=0, column=0, sticky="ewns")

        scrollbar = ttk.Scrollbar(tree_frame, orient='vertical', command=self.history_tree.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.history_tree.config(yscrollcommand=scrollbar.set)

        btn_frame = ctk.CTkFrame(parent, fg_color="transparent")
        btn_frame.grid(row=2, column=0, sticky="ew")
        reconvert_btn = ctk.CTkButton(btn_frame, text="\U0001f504 Re-convert", command=self.reconvert_selected)
        reconvert_btn.pack(side="left", padx=5)
        ToolTip(reconvert_btn, "Re-convert selected history entry")

        export_btn = ctk.CTkButton(btn_frame, text="\U0001f4e4 Export CSV", command=self.export_history)
        export_btn.pack(side="left", padx=5)
        ToolTip(export_btn, "Export history to CSV file")

        clear_hist_btn = ctk.CTkButton(btn_frame, text="\U0001f5d1\ufe0f Clear History", command=self.clear_history,
                                        fg_color=("#d32f2f", "#b71c1c"), hover_color=("#b71c1c", "#d32f2f"))
        clear_hist_btn.pack(side="left", padx=5)
        ToolTip(clear_hist_btn, "Clear all history entries")

        self.update_history_display()

    def export_history(self):
        if not self.history:
            messagebox.showinfo("No History", "No conversion history to export.")
            return
        path = filedialog.asksaveasfilename(
            title="Export History",
            defaultextension=".csv",
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")],
            initialdir=os.path.expanduser("~"))
        if not path:
            return
        try:
            with open(path, 'w', newline='') as f:
                import csv
                writer = csv.writer(f)
                writer.writerow(['Timestamp', 'Input File', 'Output File', 'Success', 'Message'])
                for entry in self.history:
                    writer.writerow([
                        entry.get('timestamp', ''),
                        entry.get('input', ''),
                        entry.get('output', ''),
                        'Yes' if entry.get('success') else 'No',
                        entry.get('message', '')
                    ])
            messagebox.showinfo("Exported", f"History exported to:\n{path}")
        except Exception as e:
            messagebox.showerror("Export Failed", str(e))

    def toggle_theme(self):
        current = ctk.get_appearance_mode()
        new = "light" if current == "Dark" else "dark"
        ctk.set_appearance_mode(new)
        self.theme_btn.configure(text="\U0001f319" if new == "dark" else "\u2600\ufe0f")
        self.update_treeview_theme()

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

    def add_files(self, paths=None):
        if paths is None:
            result = native_file_dialog(title="Select files", multiple=True)
            if not result:
                return
            files = result if isinstance(result, list) else [result]
        else:
            files = paths
        for f in files:
            if os.path.isfile(f) and get_media_type(f) and f not in self.input_files:
                self.input_files.append(f)
                info = get_file_info(f)
                if info:
                    self.file_infos[f] = info
        self.update_queue_display()

    def on_file_drop(self, event):
        raw = event.data
        files = self.root.tk.splitlist(raw) if hasattr(self.root.tk, 'splitlist') else raw.split()
        parsed = []
        for f in files:
            f = f.strip('{}').strip()
            if f:
                parsed.append(f)
        self.add_files(parsed)

    def remove_files(self):
        selection = self.queue_tree.selection()
        for item in reversed(selection):
            values = self.queue_tree.item(item)['values']
            for i, f in enumerate(self.input_files):
                if os.path.basename(f) == values[0] or f == values[0]:
                    self.input_files.pop(i)
                    if f in self.file_infos:
                        del self.file_infos[f]
                    self.file_overrides.pop(f, None)
                    break
        self.update_queue_display()
        self.clear_detail_panel()

    def clear_files(self):
        self.input_files.clear()
        self.file_infos.clear()
        self.file_overrides.clear()
        self.update_queue_display()
        self.clear_detail_panel()

    def update_queue_display(self):
        self.queue_tree.delete(*self.queue_tree.get_children())
        for f in self.input_files:
            info = self.file_infos.get(f, {})
            size = self.format_size(info.get('size', 0))
            duration = self.format_duration(info.get('duration', 0))
            status = "\u23f3 Waiting"
            self.queue_tree.insert('', "end", text=os.path.basename(f),
                                   values=(size, duration, status))
        self.queue_count_label.configure(text=f"Queue: {len(self.input_files)} files")

    def on_queue_select(self, event):
        selection = self.queue_tree.selection()
        if not selection:
            self.clear_detail_panel()
            return
        item = selection[0]
        text = self.queue_tree.item(item)['text']
        for f in self.input_files:
            if os.path.basename(f) == text:
                self.update_detail_panel(self.file_infos.get(f, {}))
                return
        self.clear_detail_panel()

    def on_queue_double_click(self, event):
        selection = self.queue_tree.selection()
        if not selection or self.is_converting:
            return
        item = selection[0]
        text = self.queue_tree.item(item)['text']
        for f in self.input_files:
            if os.path.basename(f) == text:
                self.show_format_override_dialog(f)
                return

    def show_format_override_dialog(self, file_path):
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("Override Format")
        w, h = 320, 160
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        dialog.geometry(f"{w}x{h}+{x}+{y}")
        dialog.transient(self.root)
        dialog.grab_set()

        ctk.CTkLabel(dialog, text=f"File: {os.path.basename(file_path)}", font=("Arial", 11, "bold")).pack(pady=(10, 5))
        ctk.CTkLabel(dialog, text="Override output format:").pack()

        current = self.file_overrides.get(file_path, self.format_var.get())
        var = ctk.StringVar(value=current)
        combo = ctk.CTkComboBox(dialog, variable=var, values=ALL_FORMATS, width=180)
        combo.pack(pady=5)

        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(pady=10)

        def apply():
            self.file_overrides[file_path] = var.get()
            dialog.destroy()

        def use_default():
            self.file_overrides.pop(file_path, None)
            dialog.destroy()

        ctk.CTkButton(btn_frame, text="Apply", command=apply, width=90).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Use Default", command=use_default, width=90).pack(side="left", padx=5)

    def update_detail_panel(self, info):
        video = info.get('video') or {}
        audio = info.get('audio') or {}
        self.detail_labels['codec'].configure(text=f"Codec: {video.get('codec', 'N/A')}")
        res = f"{video.get('width', '?')}x{video.get('height', '?')}" if video.get('width') else 'N/A'
        self.detail_labels['resolution'].configure(text=f"Res: {res}")
        bitrate = info.get('bitrate', 0)
        self.detail_labels['bitrate'].configure(text=f"Bitrate: {bitrate//1000}k" if bitrate else "Bitrate: N/A")
        dur = info.get('duration', 0)
        self.detail_labels['duration'].configure(text=f"Dur: {self.format_duration(dur)}" if dur else "Dur: N/A")
        self.detail_labels['fps'].configure(text=f"FPS: {video.get('fps', 'N/A')}")
        ac = audio.get('codec', 'N/A')
        ch = audio.get('channels', '?')
        self.detail_labels['audio'].configure(text=f"Audio: {ac} {ch}ch")

    def clear_detail_panel(self):
        for key, lbl in self.detail_labels.items():
            lbl.configure(text=f"{key.capitalize()}: --")

    def on_drag_start(self, event):
        item = self.queue_tree.identify_row(event.y)
        if item:
            self.drag_start_item = item
            self.drag_start_index = self.queue_tree.index(item)

    def on_drag_motion(self, event):
        if self.drag_start_item is None:
            return
        target_item = self.queue_tree.identify_row(event.y)
        if target_item and target_item != self.drag_start_item:
            children = self.queue_tree.get_children()
            for child in children:
                self.queue_tree.item(child, tags=())
            self.queue_tree.item(target_item, tags=('drag_target',))
            is_dark = ctk.get_appearance_mode() == "Dark"
            bg = '#1f5382' if is_dark else '#0078d7'
            self.queue_tree.tag_configure('drag_target', background=bg)

    def on_drag_release(self, event):
        if self.drag_start_item is None:
            return
        target_item = self.queue_tree.identify_row(event.y)
        if target_item and target_item != self.drag_start_item:
            start_idx = self.drag_start_index
            target_idx = self.queue_tree.index(target_item)
            file_to_move = self.input_files.pop(start_idx)
            self.input_files.insert(target_idx, file_to_move)
            self.update_queue_display()
            self.status_label.configure(text=f"Reordered queue: moved file to position {target_idx+1}")
        self.drag_start_item = None
        self.drag_start_index = None
        for child in self.queue_tree.get_children():
            self.queue_tree.item(child, tags=())

    def browse_output_dir(self):
        directory = native_file_dialog(title="Select output directory", directory=True,
                                       initialdir=self.output_dir_var.get())
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
        self.failed_files = []
        self.convert_btn.configure(state="disabled")
        self.pause_btn.configure(state="normal")
        self.stop_btn.configure(state="normal")
        self.retry_btn.configure(state="disabled")
        self.progress_bar.set(0)
        from converter import reset_stop
        reset_stop()
        thread = threading.Thread(target=self.convert_files, args=(output_format, output_dir, settings), daemon=True)
        thread.start()

    def toggle_pause(self):
        from converter import pause_conversion, resume_conversion, is_paused
        if self.conversion_state == 'running':
            pause_conversion()
            self.conversion_state = 'paused'
            self.pause_btn.configure(text="\u25b6  Resume")
            self.status_label.configure(text="\u23f8 Paused")
        elif self.conversion_state == 'paused':
            resume_conversion()
            self.conversion_state = 'running'
            self.pause_btn.configure(text="\u23f8  Pause")
            self.status_label.configure(text="Converting...")

    def stop_conversion(self):
        if messagebox.askyesno("Stop Conversion", "Are you sure you want to stop the conversion queue?"):
            from converter import stop_conversion
            stop_conversion()
            self.conversion_state = 'stopping'
            self.status_label.configure(text="\u23f9 Stopping...")
            self.pause_btn.configure(state="disabled")
            self.stop_btn.configure(state="disabled")

    def retry_failed(self):
        if not self.failed_files:
            messagebox.showinfo("No Failed Files", "There are no failed conversions to retry.")
            return
        self.input_files.extend(self.failed_files)
        self.failed_files = []
        self.update_queue_display()
        self.retry_btn.configure(state="disabled")
        self.status_label.configure(text="\u2705 Failed files moved to queue")

    def convert_files(self, output_format, output_dir, settings):
        total = len(self.input_files)
        from converter import stop_event

        for i, input_file in enumerate(self.input_files[:]):
            if stop_event.is_set():
                self.root.after(0, self.update_queue_status, input_file, "\u23f9 Stopped")
                for remaining in self.input_files[i:]:
                    self.root.after(0, self.update_queue_status, remaining, "\u23f9 Stopped")
                break

            file_format = self.file_overrides.get(input_file, output_format)
            output_file = os.path.join(output_dir, self.get_output_filename(input_file, file_format))
            if not self.overwrite_var.get() and os.path.exists(output_file):
                self.root.after(0, self.update_queue_status, input_file, "\u26a0\ufe0f Skipped")
                continue

            self.root.after(0, self.update_queue_status, input_file, "\U0001f504 Converting")
            text = f"Converting: {os.path.basename(input_file)}"
            self.root.after(0, lambda t=text: self.status_label.configure(text=t))

            def progress_callback(p):
                overall = (i + p/100) / total
                self.root.after(0, self.progress_bar.set, overall)

            success, msg = convert_file(input_file, output_file, progress_callback, settings)
            status = "\u2705 Done" if success else f"\u274c {msg[:35]}"
            self.root.after(0, self.update_queue_status, input_file, status)
            self.root.after(0, self.add_to_history, input_file, output_file, success, msg)

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
        self.progress_bar.set(value)

    def conversion_complete(self):
        self.is_converting = False
        self.conversion_state = 'idle'
        self.convert_btn.configure(state="normal")
        self.pause_btn.configure(state="disabled", text="\u23f8  Pause")
        self.stop_btn.configure(state="disabled")
        self.progress_bar.set(1.0)

        if self.failed_files:
            self.retry_btn.configure(state="normal")
            self.status_label.configure(text=f"\u26a0\ufe0f Complete with {len(self.failed_files)} failures")
        else:
            self.status_label.configure(text="\u2705 Conversion complete!")
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
        try:
            with open(self.history_file, 'w') as f:
                json.dump(self.history, f, indent=2)
        except Exception:
            pass

    def update_history_display(self):
        if hasattr(self, 'history_tree'):
            self.history_tree.delete(*self.history_tree.get_children())
            for entry in reversed(self.history[-100:]):
                date = datetime.fromisoformat(entry['timestamp']).strftime('%Y-%m-%d %H:%M')
                status = "\u2705 Success" if entry['success'] else "\u274c Failed"
                self.history_tree.insert('', 0, values=(
                    os.path.basename(entry['input']),
                    os.path.basename(entry['output']),
                    status
                ))

    def setup_watch_tab(self, parent):
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(parent, text="\U0001f441\ufe0f Watch Folder Mode", font=("Arial", 14, "bold")).grid(
            row=0, column=0, sticky="w", pady=(0, 10))

        main_frame = ctk.CTkFrame(parent)
        main_frame.grid(row=1, column=0, sticky="ewns")
        main_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(main_frame, text="Watch Folder:").grid(row=0, column=0, sticky="w", padx=(0, 10), pady=5)
        self.watch_input_var = ctk.StringVar()
        ctk.CTkEntry(main_frame, textvariable=self.watch_input_var).grid(row=0, column=1, sticky="ew", pady=5)
        ctk.CTkButton(main_frame, text="Browse", command=self.browse_watch_input).grid(row=0, column=2, padx=5, pady=5)

        ctk.CTkLabel(main_frame, text="Output Folder:").grid(row=1, column=0, sticky="w", padx=(0, 10), pady=5)
        self.watch_output_var = ctk.StringVar()
        ctk.CTkEntry(main_frame, textvariable=self.watch_output_var).grid(row=1, column=1, sticky="ew", pady=5)
        ctk.CTkButton(main_frame, text="Browse", command=self.browse_watch_output).grid(row=1, column=2, padx=5, pady=5)

        ctk.CTkLabel(main_frame, text="Output Format:").grid(row=2, column=0, sticky="w", padx=(0, 10), pady=5)
        self.watch_format_var = ctk.StringVar(value="mp4")
        ctk.CTkComboBox(main_frame, variable=self.watch_format_var, values=ALL_FORMATS, width=140).grid(
            row=2, column=1, sticky="w", pady=5)

        btn_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        btn_frame.grid(row=3, column=0, columnspan=3, pady=(10, 5))
        self.watch_btn = ctk.CTkButton(btn_frame, text="\u25b6 Start Watching", command=self.toggle_watch)
        self.watch_btn.pack(side="left", padx=5)
        ToolTip(self.watch_btn, "Start/Stop watching folder")

        self.watch_status_label = ctk.CTkLabel(main_frame, text="\u23f9 Not watching", font=("Arial", 9))
        self.watch_status_label.grid(row=4, column=0, columnspan=3, sticky="w", pady=(10, 0))

        ctk.CTkLabel(main_frame, text="Recent Activity:").grid(row=5, column=0, columnspan=3, sticky="w", pady=(10, 5))
        self.watch_log = ctk.CTkTextbox(main_frame, height=200, font=("Arial", 9))
        self.watch_log.grid(row=6, column=0, columnspan=3, sticky="ewns")
        main_frame.grid_rowconfigure(6, weight=1)

    def browse_watch_input(self):
        directory = native_file_dialog(title="Select folder to watch", directory=True)
        if directory:
            self.watch_input_var.set(directory)

    def browse_watch_output(self):
        directory = native_file_dialog(title="Select output folder", directory=True)
        if directory:
            self.watch_output_var.set(directory)

    def toggle_watch(self):
        if hasattr(self, 'watching') and self.watching:
            self.watching = False
            self.watch_btn.configure(text="\u25b6 Start Watching")
            self.watch_status_label.configure(text="\u23f9 Stopped watching")
        else:
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
            self.watch_btn.configure(text="\u23f9 Stop Watching")
            self.watch_status_label.configure(text=f"\U0001f441\ufe0f Watching: {input_dir}")
            output_format = self.watch_format_var.get()
            thread = threading.Thread(target=self.watch_folder_thread,
                                     args=(input_dir, output_dir, output_format),
                                     daemon=True)
            thread.start()

    def watch_folder_thread(self, input_dir, output_dir, output_format):
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
        import datetime
        timestamp = datetime.datetime.now().strftime('%H:%M:%S')
        self.watch_log.configure(state="normal")
        self.watch_log.insert("end", f"[{timestamp}] {message}\n")
        self.watch_log.see("end")
        self.watch_log.configure(state="disabled")

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
            self.tabview.set("\U0001f504  Convert")
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
            self.update_history_display()
            self.save_history()


def main():
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    root = DnDCTk()
    app = FileConverterGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()


if __name__ == '__main__':
    main()

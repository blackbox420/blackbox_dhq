# gui/views/downloads_view.py
import customtkinter as ctk
from tkinter import filedialog, messagebox, StringVar, BooleanVar # Osiguraj da su StringVar i BooleanVar importani
import tkinter as tk # Ako koristiš tk.StringVar itd.
from .base_view import BaseView
from core import downloader_engine as de
from core import settings_handler as sh
import logging
import os # Dodaj os ako nije tu
import uuid # Za jedinstveni task ID

logger = logging.getLogger(__name__)

class DownloadsView(BaseView):
    def __init__(self, master, app_context: dict, **kwargs):
        super().__init__(master, "downloads", app_context, **kwargs)

    def build_ui(self):
        # ... (UI ostaje isti kao u tvom zadnjem uspješnom kodu) ...
        # Samo osiguraj da su `ctk.StringVar` itd. zamijenjeni s `StringVar` ako si tako importirao,
        # ili koristi `tk.StringVar` ako si importirao `import tkinter as tk`
        # Moj prethodni prijedlog je bio:
        # from tkinter import filedialog, messagebox, StringVar, BooleanVar
        # import tkinter as tk 
        # Ovo je malo redundantno. Bolje je:
        # from tkinter import filedialog, messagebox, StringVar, BooleanVar
        # A ako trebaš tk konstante, onda import tkinter as tk.
        # Za StringVar i BooleanVar, CustomTkinter nema svoje alternative, pa koristimo Tkinterove.

        title_frame = ctk.CTkFrame(self, fg_color="transparent")
        title_frame.pack(fill="x", padx=20, pady=(20,10))
        title_label = ctk.CTkLabel(title_frame, text="Novo Preuzimanje", font=ctk.CTkFont(size=28, weight="bold"), anchor="w")
        title_label.pack(side="left")

        url_input_frame = ctk.CTkFrame(self, fg_color="transparent")
        url_input_frame.pack(fill=ctk.X, padx=20, pady=10) # Koristi ctk.X umjesto "x"
        url_input_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(url_input_frame, text="URL Adresa:", anchor="w").grid(row=0, column=0, padx=(0,10), pady=10, sticky="w")
        self.url_entry = ctk.CTkEntry(url_input_frame, placeholder_text="https://...", height=35)
        self.url_entry.grid(row=0, column=1, padx=0, pady=10, sticky="ew")
        self.url_entry.bind("<Return>", lambda event: self._add_url_to_queue_action())
        self.url_entry.bind("<KeyRelease>", self._url_entry_changed_action)

        paste_button = ctk.CTkButton(url_input_frame, text="Zalijepi", width=100, height=35, command=self._paste_from_clipboard_action)
        paste_button.grid(row=0, column=2, padx=(10,0), pady=10)

        ctk.CTkLabel(url_input_frame, text="Profil Kvalitete:", anchor="w").grid(row=1, column=0, padx=(0,10), pady=10, sticky="w")
        self.quality_combobox = ctk.CTkComboBox(url_input_frame, values=de.QUALITY_PROFILE_KEYS, 
                                                state="readonly", height=35, width=250,
                                                command=self._quality_profile_selected)
        self.quality_combobox.set(sh.load_settings().get("default_quality", de.QUALITY_PROFILE_KEYS[0]))
        self.quality_combobox.grid(row=1, column=1, padx=0, pady=10, sticky="w")
        
        self.quality_description_label = ctk.CTkLabel(url_input_frame, text="", anchor="w", wraplength=400, justify="left",
                                                       font=ctk.CTkFont(size=11), text_color="gray60")
        self.quality_description_label.grid(row=2, column=1, padx=0, pady=(0,10), sticky="w")
        self._update_quality_description()

        add_button = ctk.CTkButton(url_input_frame, text="Dodaj u Red", height=35, command=self._add_url_to_queue_action)
        add_button.grid(row=1, column=2, rowspan=2, padx=(10,0), pady=10, sticky="ns")

    def _quality_profile_selected(self, choice):
        self._update_quality_description()

    def _update_quality_description(self):
        selected_profile_key = self.quality_combobox.get()
        profile_details = de.QUALITY_PROFILES.get(selected_profile_key)
        if profile_details and hasattr(self, 'quality_description_label'):
            self.quality_description_label.configure(text=profile_details.get("description", ""))
        elif hasattr(self, 'quality_description_label'):
            self.quality_description_label.configure(text="")

    def _url_entry_changed_action(self, event=None):
        current_url = self.url_entry.get().strip()
        if current_url:
            suggested_profile = de.determine_content_type_and_suggest_quality(current_url)
            if suggested_profile in de.QUALITY_PROFILE_KEYS:
                self.quality_combobox.set(suggested_profile)
                self._update_quality_description()
        elif hasattr(self, 'quality_combobox'):
             self.quality_combobox.set(sh.load_settings().get("default_quality", de.QUALITY_PROFILE_KEYS[0]))
             self._update_quality_description()

    def _paste_from_clipboard_action(self):
        try:
            clipboard_content = self.winfo_toplevel().clipboard_get() # Ispravljeno da koristi winfo_toplevel()
            if clipboard_content:
                if clipboard_content.startswith("http://") or clipboard_content.startswith("https://"):
                    self.url_entry.delete(0, ctk.END)
                    self.url_entry.insert(0, clipboard_content)
                    self._url_entry_changed_action() 
                    if "status_bar_var" in self.app_context: # Ažuriraj status bar
                         self.app_context["status_bar_var"].set("URL zalijepljen iz clipboarda.")
                else:
                     messagebox.showinfo("Clipboard Info", "Sadržaj clipboarda ne izgleda kao URL.", parent=self)
        except tk.TclError: # Importiraj tk ako već nije
            messagebox.showinfo("Clipboard Info", "Clipboard je prazan ili ne sadrži tekst.", parent=self)

    def _add_url_to_queue_action(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("Nema URL-a", "Molimo unesite URL.", parent=self)
            return
        
        quality_key = self.quality_combobox.get()
        download_manager = self.app_context.get("download_manager")
        settings = self.app_context.get("settings")
        main_window_select_tab_callback = self.app_context.get("main_window_select_tab_callback")

        if download_manager and settings:
            output_dir_val = settings.get("output_directory")
            # Generiraj jedinstveni ID za task (npr. koristeći UUID)
            task_item_id = f"task_{uuid.uuid4().hex[:8]}" # Jedinstveni ID za Treeview
            
            task = de.DownloadTask(url, quality_key, output_dir_val, task_item_id)
            download_manager.add_to_queue(task) # Ovo će pokrenuti callback u MainWindow
            
            self.url_entry.delete(0, ctk.END)
            logger.info(f"URL '{os.path.basename(url)}' dodan u red (ID: {task_item_id}, Kvaliteta: {quality_key})")
            
            if "status_bar_var" in self.app_context: # Ažuriraj status bar
                 self.app_context["status_bar_var"].set(f"Dodan u red: {os.path.basename(url)}")

            if main_window_select_tab_callback:
                main_window_select_tab_callback("queue")
        else:
            messagebox.showerror("Greška Aplikacije", "Download manager ili postavke nisu dostupni.", parent=self)

    def on_view_enter(self):
        super().on_view_enter()
        if hasattr(self, 'quality_combobox'):
            self.quality_combobox.set(sh.load_settings().get("default_quality", de.QUALITY_PROFILE_KEYS[0]))
            self._update_quality_description()
        if sh.load_settings().get("auto_paste_clipboard", False) and self.winfo_ismapped():
            self.after(100, self._paste_from_clipboard_action)
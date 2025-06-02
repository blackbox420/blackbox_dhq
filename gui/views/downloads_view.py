# gui/views/downloads_view.py
import customtkinter as ctk
from tkinter import filedialog, messagebox, StringVar, BooleanVar # Osiguraj importe
import tkinter as tk # Ako koristiš prefiks tk.
from .base_view import BaseView
from core import downloader_engine as de
from core import settings_handler as sh
import logging
import os
import uuid # Za jedinstveni task ID

logger = logging.getLogger(__name__)

class DownloadsView(BaseView):
    def __init__(self, master, app_context: dict, **kwargs):
        super().__init__(master, "downloads", app_context, **kwargs)

    def build_ui(self):
        theme_colors = self.app_context.get("theme_colors", {})
        entry_height = 35
        button_width = 100
        
        title_frame = ctk.CTkFrame(self, fg_color="transparent")
        title_frame.pack(fill="x", padx=20, pady=(20,15)) # Povećan donji padding
        ctk.CTkLabel(title_frame, text="Novo Preuzimanje", 
                     font=ctk.CTkFont(size=28, weight="bold"), 
                     anchor="w", text_color=theme_colors.get("TEXT_ACCENT")
                    ).pack(side="left")

        url_input_frame = ctk.CTkFrame(self, fg_color="transparent")
        url_input_frame.pack(fill=ctk.X, padx=20, pady=10, anchor="n") # Poravnaj na vrh
        url_input_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(url_input_frame, text="URL Adresa:", anchor="w", font=ctk.CTkFont(size=13)).grid(row=0, column=0, padx=(0,10), pady=10, sticky="w")
        self.url_entry = ctk.CTkEntry(url_input_frame, placeholder_text="https://www.primjer.com/video_ili_audio_link", height=entry_height,
                                      font=ctk.CTkFont(size=13))
        self.url_entry.grid(row=0, column=1, padx=0, pady=10, sticky="ew")
        self.url_entry.bind("<Return>", lambda event: self._add_url_to_queue_action())
        self.url_entry.bind("<KeyRelease>", self._url_entry_changed_action)

        paste_icon = self.app_context.get("icon_loader", lambda name, size: None)("paste_icon", (18,18)) # Primjer ikone
        paste_button = ctk.CTkButton(url_input_frame, text="Zalijepi", image=paste_icon, compound="left", 
                                     width=button_width+10, height=entry_height, 
                                     command=self._paste_from_clipboard_action)
        paste_button.grid(row=0, column=2, padx=(10,0), pady=10)

        ctk.CTkLabel(url_input_frame, text="Profil Kvalitete:", anchor="w", font=ctk.CTkFont(size=13)).grid(row=1, column=0, padx=(0,10), pady=10, sticky="w")
        self.quality_combobox = ctk.CTkComboBox(url_input_frame, values=de.QUALITY_PROFILE_KEYS, 
                                                state="readonly", height=entry_height, width=300, # Povećana širina
                                                font=ctk.CTkFont(size=12),
                                                command=self._quality_profile_selected)
        self.quality_combobox.set(sh.load_settings().get("default_quality", de.QUALITY_PROFILE_KEYS[0]))
        self.quality_combobox.grid(row=1, column=1, padx=0, pady=10, sticky="w")
        
        self.quality_description_label = ctk.CTkLabel(url_input_frame, text="", anchor="w", wraplength=450, # Povećan wraplength
                                                       justify="left", font=ctk.CTkFont(size=11), 
                                                       text_color=theme_colors.get("TEXT_SECONDARY"))
        self.quality_description_label.grid(row=2, column=1, columnspan=2, padx=0, pady=(0,15), sticky="w") # columnspan da zauzme više prostora
        self._update_quality_description()

        add_to_queue_icon = self.app_context.get("icon_loader", lambda name, size: None)("add_to_queue_icon", (20,20))
        add_button = ctk.CTkButton(url_input_frame, text="Dodaj u Red Čekanja", image=add_to_queue_icon, compound="left", 
                                   height=entry_height+5, font=ctk.CTkFont(size=13, weight="bold"),
                                   fg_color=theme_colors.get("SUCCESS"), 
                                   hover_color=theme_colors.get("ACCENT_SECONDARY"),
                                   command=self._add_url_to_queue_action)
        add_button.grid(row=3, column=1, columnspan=2, padx=0, pady=10, sticky="ew")


    def _quality_profile_selected(self, choice): # Ostaje isto
        self._update_quality_description()

    def _update_quality_description(self): # Ostaje isto
        selected_profile_key = self.quality_combobox.get()
        profile_details = de.QUALITY_PROFILES.get(selected_profile_key)
        if profile_details and hasattr(self, 'quality_description_label'):
            self.quality_description_label.configure(text=profile_details.get("description", ""))
        elif hasattr(self, 'quality_description_label'):
            self.quality_description_label.configure(text="")

    def _url_entry_changed_action(self, event=None): # Ostaje isto
        current_url = self.url_entry.get().strip()
        if current_url:
            suggested_profile = de.determine_content_type_and_suggest_quality(current_url)
            if suggested_profile in de.QUALITY_PROFILE_KEYS:
                self.quality_combobox.set(suggested_profile)
                self._update_quality_description()
        elif hasattr(self, 'quality_combobox'):
             self.quality_combobox.set(sh.load_settings().get("default_quality", de.QUALITY_PROFILE_KEYS[0]))
             self._update_quality_description()

    def _paste_from_clipboard_action(self): # Ostaje isto
        try:
            clipboard_content = self.winfo_toplevel().clipboard_get()
            if clipboard_content:
                if clipboard_content.startswith("http://") or clipboard_content.startswith("https://"):
                    self.url_entry.delete(0, ctk.END)
                    self.url_entry.insert(0, clipboard_content)
                    self._url_entry_changed_action() 
                    status_bar_var = self.app_context.get("status_bar_var")
                    if status_bar_var: status_bar_var.set("URL zalijepljen iz clipboarda.")
                else:
                     messagebox.showinfo("Clipboard Info", "Sadržaj clipboarda ne izgleda kao URL.", parent=self.winfo_toplevel())
        except tk.TclError:
            messagebox.showinfo("Clipboard Info", "Clipboard je prazan ili ne sadrži tekst.", parent=self.winfo_toplevel())

    def _add_url_to_queue_action(self): # Ostaje isto
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("Nema URL-a", "Molimo unesite URL.", parent=self.winfo_toplevel())
            return
        
        quality_key = self.quality_combobox.get()
        download_manager = self.app_context.get("download_manager")
        settings = self.app_context.get("settings")
        main_window_select_tab_callback = self.app_context.get("main_window_select_tab_callback")

        if download_manager and settings:
            output_dir_val = settings.get("output_directory")
            task_item_id = f"task_{uuid.uuid4().hex[:10]}" # Malo duži ID za manju šansu kolizije
            
            task = de.DownloadTask(url, quality_key, output_dir_val, task_item_id)
            download_manager.add_to_queue(task)
            
            self.url_entry.delete(0, ctk.END)
            self.logger.info(f"URL '{os.path.basename(url)}' dodan u red (ID: {task_item_id}, Kvaliteta: {quality_key})")
            
            status_bar_var = self.app_context.get("status_bar_var")
            if status_bar_var: status_bar_var.set(f"Dodan u red: {os.path.basename(url)}")

            if main_window_select_tab_callback:
                main_window_select_tab_callback("queue")
        else:
            messagebox.showerror("Greška Aplikacije", "Download manager ili postavke nisu dostupni.", parent=self.winfo_toplevel())

    def on_view_enter(self): # Ostaje isto
        super().on_view_enter()
        if hasattr(self, 'quality_combobox'):
            self.quality_combobox.set(sh.load_settings().get("default_quality", de.QUALITY_PROFILE_KEYS[0]))
            self._update_quality_description()
        if sh.load_settings().get("auto_paste_clipboard", False) and self.winfo_ismapped():
            self.after(100, self._paste_from_clipboard_action)
# gui/views/settings_view.py
import customtkinter as ctk
from tkinter import filedialog, messagebox, StringVar, BooleanVar # Importuj StringVar i BooleanVar direktno
# Više ne treba `import tkinter as tk` ako importiraš specifične klase
from .base_view import BaseView
from core import settings_handler as sh
from core import downloader_engine as de
import logging
import os

logger = logging.getLogger(__name__)

class SettingsView(BaseView):
    def __init__(self, master, app_context: dict, **kwargs):
        # INICIJALIZIRAJ settings_vars OVDJE, PRIJE POZIVA super().__init__()
        self.settings_vars = {} 
        super().__init__(master, "settings", app_context, **kwargs)
        # self.build_ui() se sada poziva iz BaseView.__init__() i self.settings_vars postoji

    def build_ui(self):
        title_label = ctk.CTkLabel(self, text="Postavke Aplikacije", font=ctk.CTkFont(size=28, weight="bold"), anchor="w")
        title_label.pack(pady=(10,20), padx=20, fill="x")

        scrollable_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scrollable_frame.pack(fill="both", expand=True, padx=15, pady=5)

        current_settings = self.app_context.get("settings", sh.DEFAULT_SETTINGS)

        # 1. Izlazni Direktorij
        dir_frame = ctk.CTkFrame(scrollable_frame, fg_color="transparent")
        dir_frame.pack(fill="x", pady=(0,10))
        ctk.CTkLabel(dir_frame, text="Defaultni Izlazni Direktorij:", anchor="w").pack(side="left", padx=(0,10))
        # Koristi StringVar koji si importirao
        self.settings_vars["output_directory"] = StringVar(value=current_settings.get("output_directory"))
        dir_entry = ctk.CTkEntry(dir_frame, textvariable=self.settings_vars["output_directory"], width=350, state="readonly")
        dir_entry.pack(side="left", expand=True, fill="x")
        dir_button = ctk.CTkButton(dir_frame, text="Promijeni...", width=100, command=self._select_output_directory)
        dir_button.pack(side="left", padx=(10,0))

        # 2. Defaultna Kvaliteta
        qual_frame = ctk.CTkFrame(scrollable_frame, fg_color="transparent")
        qual_frame.pack(fill="x", pady=10, anchor="w")
        ctk.CTkLabel(qual_frame, text="Defaultni Profil Kvalitete:", anchor="w").pack(side="left", padx=(0,10))
        self.settings_vars["default_quality"] = StringVar(value=current_settings.get("default_quality"))
        qual_combo = ctk.CTkComboBox(qual_frame, variable=self.settings_vars["default_quality"],
                                     values=de.QUALITY_PROFILE_KEYS, state="readonly", width=250)
        qual_combo.pack(side="left")

        # 3. Tema Aplikacije
        theme_outer_frame = ctk.CTkFrame(scrollable_frame, fg_color="transparent")
        theme_outer_frame.pack(fill="x", pady=10, anchor="w")

        appearance_frame = ctk.CTkFrame(theme_outer_frame, fg_color="transparent")
        appearance_frame.pack(side="left", padx=(0, 20))
        ctk.CTkLabel(appearance_frame, text="Mod Izgleda:", anchor="w").pack(anchor="w")
        self.settings_vars["appearance_mode"] = StringVar(value=current_settings.get("appearance_mode"))
        appearance_modes = ["light", "dark", "system"]
        appearance_combo = ctk.CTkComboBox(appearance_frame, variable=self.settings_vars["appearance_mode"],
                                          values=appearance_modes, state="readonly", width=150,
                                          command=lambda choice: ctk.set_appearance_mode(choice))
        appearance_combo.pack(anchor="w")

        color_theme_frame = ctk.CTkFrame(theme_outer_frame, fg_color="transparent")
        color_theme_frame.pack(side="left")
        ctk.CTkLabel(color_theme_frame, text="Boja Teme:", anchor="w").pack(anchor="w")
        self.settings_vars["theme"] = StringVar(value=current_settings.get("theme"))
        color_themes = ["blue", "dark-blue", "green"] 
        theme_combo = ctk.CTkComboBox(color_theme_frame, variable=self.settings_vars["theme"],
                                      values=color_themes, state="readonly", width=150,
                                      command=lambda choice: ctk.set_default_color_theme(choice))
        theme_combo.pack(anchor="w")

        # 4. Boolean Postavke
        bool_frame = ctk.CTkFrame(scrollable_frame, fg_color="transparent")
        bool_frame.pack(fill="x", pady=10, anchor="w")

        self.settings_vars["ask_open_folder"] = BooleanVar(value=current_settings.get("ask_open_folder", True))
        ctk.CTkCheckBox(bool_frame, text="Pitaj za otvaranje foldera nakon preuzimanja",
                        variable=self.settings_vars["ask_open_folder"]).pack(anchor="w", pady=3)

        self.settings_vars["auto_paste_clipboard"] = BooleanVar(value=current_settings.get("auto_paste_clipboard", False))
        ctk.CTkCheckBox(bool_frame, text="Automatski zalijepi URL iz clipboarda (pri fokusu)",
                        variable=self.settings_vars["auto_paste_clipboard"]).pack(anchor="w", pady=3)

        self.settings_vars["prefer_hw_acceleration"] = BooleanVar(value=current_settings.get("prefer_hw_acceleration", False))
        ctk.CTkCheckBox(bool_frame, text="Preferiraj hardversku akceleraciju (yt-dlp)",
                        variable=self.settings_vars["prefer_hw_acceleration"]).pack(anchor="w", pady=3)

        self.settings_vars["embed_thumbnail_audio"] = BooleanVar(value=current_settings.get("embed_thumbnail_audio", True))
        ctk.CTkCheckBox(bool_frame, text="Ugradi thumbnail u audio datoteke",
                        variable=self.settings_vars["embed_thumbnail_audio"]).pack(anchor="w", pady=3)

        self.settings_vars["add_metadata_video"] = BooleanVar(value=current_settings.get("add_metadata_video", True))
        ctk.CTkCheckBox(bool_frame, text="Dodaj metapodatke u video datoteke",
                        variable=self.settings_vars["add_metadata_video"]).pack(anchor="w", pady=3)

        save_button = ctk.CTkButton(scrollable_frame, text="Spremi Postavke", height=35, command=self._save_settings_action)
        save_button.pack(pady=20, padx=10, anchor="e")

    # Metode _select_output_directory, _save_settings_action, on_view_enter ostaju iste kao prije
    # ... (copy-paste te metode ovdje iz prethodnog odgovora) ...
    def _select_output_directory(self):
        new_dir = filedialog.askdirectory(initialdir=self.settings_vars["output_directory"].get(),
                                          title="Odaberite Defaultni Izlazni Direktorij",
                                          parent=self) 
        if new_dir:
            self.settings_vars["output_directory"].set(os.path.abspath(new_dir))

    def _save_settings_action(self):
        new_settings = {}
        for key, var in self.settings_vars.items():
            new_settings[key] = var.get()

        output_dir = new_settings["output_directory"]
        if not os.path.isdir(output_dir):
            try:
                os.makedirs(output_dir, exist_ok=True)
                logger.info(f"Kreiran izlazni direktorij: {output_dir}")
            except Exception as e:
                logger.error(f"Nije moguće kreirati izlazni direktorij '{output_dir}': {e}")
                messagebox.showerror("Greška Direktorija", f"Nije moguće kreirati izlazni direktorij:\n{output_dir}\n\n{e}", parent=self)
                return 

        sh.save_settings(new_settings)

        if "settings" in self.app_context:
            self.app_context["settings"] = new_settings 

        root_app = self.winfo_toplevel()
        if hasattr(root_app, 'settings'):
            root_app.settings = new_settings

        # Nije potrebno ponovno pozivati ctk.set_appearance_mode i ctk.set_default_color_theme ovdje
        # ako su ComboBox-ovi već direktno povezani s tim funkcijama preko `command` argumenta.
        # Ako nisu, ili ako želiš osigurati da se primijeni nakon spremanja:
        # ctk.set_appearance_mode(new_settings["appearance_mode"])
        # ctk.set_default_color_theme(new_settings["theme"])

        logger.info("Postavke spremljene.")
        messagebox.showinfo("Postavke", "Postavke su uspješno sačuvane.\nNeke promjene (npr. tema) mogu zahtijevati ponovno pokretanje aplikacije da bi bile potpuno primijenjene.", parent=self)

        dm = self.app_context.get("download_manager")
        if dm:
            dm.current_settings = new_settings


    def on_view_enter(self):
        logger.info("Ulazak u SettingsView.")
        current_settings = sh.load_settings() 
        for key, var_tk in self.settings_vars.items():
            if key in current_settings:
                var_tk.set(current_settings[key])
        self.app_context["settings"] = current_settings
        root_app = self.winfo_toplevel()
        if hasattr(root_app, 'settings'):
            root_app.settings = current_settings

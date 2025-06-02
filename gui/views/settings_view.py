# gui/views/settings_view.py
import customtkinter as ctk
from tkinter import filedialog, messagebox, StringVar, BooleanVar # Import StringVar i BooleanVar direktno
import tkinter as tk # <<<<<< DODAN OVAJ GLAVNI TKINTER IMPORT
from .base_view import BaseView
from core import settings_handler as sh
from core import downloader_engine as de # Za QUALITY_PROFILE_KEYS
import logging
import os

logger = logging.getLogger(__name__)

class SettingsView(BaseView):
    def __init__(self, master, app_context: dict, **kwargs):
        self.settings_vars = {} 
        super().__init__(master, "settings", app_context, **kwargs)
        # self.build_ui() se sada poziva iz BaseView.__init__()

    def build_ui(self):
        title_label = ctk.CTkLabel(self, text="Postavke Aplikacije", font=ctk.CTkFont(size=28, weight="bold"), anchor="w")
        title_label.pack(pady=(10,20), padx=20, fill="x")

        scrollable_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scrollable_frame.pack(fill="both", expand=True, padx=15, pady=5)

        current_settings = self.app_context.get("settings", sh.DEFAULT_SETTINGS)
        theme_colors_dict = self.app_context.get("theme_colors", {}) # Dohvati boje

        # Stilovi za labele i unose
        label_font = ctk.CTkFont(size=13)
        entry_height = 32
        button_width = 110
        
        # Boje za widgete (primjer, može se prilagoditi)
        frame_fg_color = theme_colors_dict.get("BACKGROUND_CONTENT", "transparent") # Ili neka blago drugačija nijansa
        label_text_color = theme_colors_dict.get("TEXT_PRIMARY")
        button_fg_color = theme_colors_dict.get("BUTTON_FG_COLOR")
        button_hover_color = theme_colors_dict.get("BUTTON_HOVER_COLOR")
        checkbox_hover_color = theme_colors_dict.get("ACCENT_SECONDARY")
        checkbox_fg_color = theme_colors_dict.get("ACCENT_PRIMARY")


        # 1. Izlazni Direktorij
        dir_frame = ctk.CTkFrame(scrollable_frame, fg_color=frame_fg_color)
        dir_frame.pack(fill="x", pady=5, padx=5)
        ctk.CTkLabel(dir_frame, text="Defaultni Izlazni Direktorij:", anchor="w", font=label_font, text_color=label_text_color).pack(side="left", padx=(5,10), pady=5)
        self.settings_vars["output_directory"] = StringVar(value=current_settings.get("output_directory"))
        dir_entry = ctk.CTkEntry(dir_frame, textvariable=self.settings_vars["output_directory"], width=350, state="readonly", height=entry_height)
        dir_entry.pack(side="left", expand=True, fill="x", padx=5, pady=5)
        dir_button = ctk.CTkButton(dir_frame, text="Promijeni...", width=button_width, height=entry_height, command=self._select_output_directory, fg_color=button_fg_color, hover_color=button_hover_color)
        dir_button.pack(side="left", padx=5, pady=5)
        
        # 2. Defaultna Kvaliteta
        qual_frame = ctk.CTkFrame(scrollable_frame, fg_color=frame_fg_color)
        qual_frame.pack(fill="x", pady=5, padx=5, anchor="w")
        ctk.CTkLabel(qual_frame, text="Defaultni Profil Kvalitete:", anchor="w", font=label_font, text_color=label_text_color).pack(side="left", padx=(5,10), pady=5)
        self.settings_vars["default_quality"] = StringVar(value=current_settings.get("default_quality"))
        qual_combo = ctk.CTkComboBox(qual_frame, variable=self.settings_vars["default_quality"],
                                     values=de.QUALITY_PROFILE_KEYS, state="readonly", width=280, height=entry_height,
                                     fg_color=theme_colors_dict.get("INPUT_BG"), 
                                     border_color=theme_colors_dict.get("INPUT_BORDER"),
                                     button_color=button_fg_color,
                                     button_hover_color=button_hover_color)
        qual_combo.pack(side="left", padx=5, pady=5)

        # 3. Tema Aplikacije
        theme_outer_frame = ctk.CTkFrame(scrollable_frame, fg_color=frame_fg_color)
        theme_outer_frame.pack(fill="x", pady=5, padx=5, anchor="w")

        appearance_frame = ctk.CTkFrame(theme_outer_frame, fg_color="transparent")
        appearance_frame.pack(side="left", padx=(0, 20), fill="x", expand=True)
        ctk.CTkLabel(appearance_frame, text="Mod Izgleda (Light/Dark):", anchor="w", font=label_font, text_color=label_text_color).pack(anchor="w", padx=5, pady=(5,2))
        self.settings_vars["appearance_mode"] = StringVar(value=current_settings.get("appearance_mode"))
        appearance_modes = ["light", "dark", "system"]
        appearance_combo = ctk.CTkComboBox(appearance_frame, variable=self.settings_vars["appearance_mode"],
                                          values=appearance_modes, state="readonly", width=180, height=entry_height,
                                          command=lambda choice: ctk.set_appearance_mode(choice),
                                          fg_color=theme_colors_dict.get("INPUT_BG"), 
                                          border_color=theme_colors_dict.get("INPUT_BORDER"),
                                          button_color=button_fg_color,
                                          button_hover_color=button_hover_color)
        appearance_combo.pack(anchor="w", padx=5, pady=(0,5))

        color_theme_frame = ctk.CTkFrame(theme_outer_frame, fg_color="transparent")
        color_theme_frame.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(color_theme_frame, text="Osnovna Boja Teme:", anchor="w", font=label_font, text_color=label_text_color).pack(anchor="w", padx=5, pady=(5,2))
        self.settings_vars["theme"] = StringVar(value=current_settings.get("theme"))
        color_themes = ["blue", "dark-blue", "green"] 
        theme_combo = ctk.CTkComboBox(color_theme_frame, variable=self.settings_vars["theme"],
                                      values=color_themes, state="readonly", width=180, height=entry_height,
                                      command=lambda choice: ctk.set_default_color_theme(choice),
                                      fg_color=theme_colors_dict.get("INPUT_BG"), 
                                      border_color=theme_colors_dict.get("INPUT_BORDER"),
                                      button_color=button_fg_color,
                                      button_hover_color=button_hover_color)
        theme_combo.pack(anchor="w", padx=5, pady=(0,5))
        
        # 4. Boolean Postavke
        bool_frame = ctk.CTkFrame(scrollable_frame, fg_color=frame_fg_color)
        bool_frame.pack(fill="x", pady=5, padx=5)

        self.settings_vars["ask_open_folder"] = BooleanVar(value=current_settings.get("ask_open_folder", True))
        ctk.CTkCheckBox(bool_frame, text="Pitaj za otvaranje foldera nakon preuzimanja",
                        variable=self.settings_vars["ask_open_folder"], font=label_font,
                        fg_color=checkbox_fg_color, hover_color=checkbox_hover_color).pack(anchor="w", padx=5, pady=4)

        self.settings_vars["auto_paste_clipboard"] = BooleanVar(value=current_settings.get("auto_paste_clipboard", False))
        ctk.CTkCheckBox(bool_frame, text="Automatski zalijepi URL iz clipboarda (pri fokusu na polje za unos)",
                        variable=self.settings_vars["auto_paste_clipboard"], font=label_font,
                        fg_color=checkbox_fg_color, hover_color=checkbox_hover_color).pack(anchor="w", padx=5, pady=4)
        
        self.settings_vars["prefer_hw_acceleration"] = BooleanVar(value=current_settings.get("prefer_hw_acceleration", False))
        ctk.CTkCheckBox(bool_frame, text="Preferiraj hardversku akceleraciju za yt-dlp (ako je dostupna)",
                        variable=self.settings_vars["prefer_hw_acceleration"], font=label_font,
                        fg_color=checkbox_fg_color, hover_color=checkbox_hover_color).pack(anchor="w", padx=5, pady=4)

        self.settings_vars["embed_thumbnail_audio"] = BooleanVar(value=current_settings.get("embed_thumbnail_audio", True))
        ctk.CTkCheckBox(bool_frame, text="Pokušaj ugraditi thumbnail u audio datoteke",
                        variable=self.settings_vars["embed_thumbnail_audio"], font=label_font,
                        fg_color=checkbox_fg_color, hover_color=checkbox_hover_color).pack(anchor="w", padx=5, pady=4)

        self.settings_vars["add_metadata_video"] = BooleanVar(value=current_settings.get("add_metadata_video", True))
        ctk.CTkCheckBox(bool_frame, text="Pokušaj dodati metapodatke u video datoteke",
                        variable=self.settings_vars["add_metadata_video"], font=label_font,
                        fg_color=checkbox_fg_color, hover_color=checkbox_hover_color).pack(anchor="w", padx=5, pady=4)

        # Gumb za spremanje
        save_button_frame = ctk.CTkFrame(scrollable_frame, fg_color="transparent")
        save_button_frame.pack(fill="x", pady=(20,5), padx=5)
        save_button = ctk.CTkButton(save_button_frame, text="Spremi Postavke", height=38, width=180, 
                                    command=self._save_settings_action, 
                                    fg_color=theme_colors_dict.get("SUCCESS"), 
                                    hover_color=ctk.ThemeManager.theme["CTkButton"]["hover_color"][0]) # Malo tamnija zelena
        save_button.pack(anchor="e", padx=5) # Poravnaj desno

    def _select_output_directory(self):
        new_dir = filedialog.askdirectory(initialdir=self.settings_vars["output_directory"].get(),
                                          title="Odaberite Defaultni Izlazni Direktorij",
                                          parent=self.winfo_toplevel()) # Osiguraj da je dijalog iznad glavnog prozora
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
                self.logger.info(f"Kreiran izlazni direktorij: {output_dir}")
            except Exception as e:
                self.logger.error(f"Nije moguće kreirati izlazni direktorij '{output_dir}': {e}")
                messagebox.showerror("Greška Direktorija", f"Nije moguće kreirati izlazni direktorij:\n{output_dir}\n\n{e}", parent=self)
                return 
        
        sh.save_settings(new_settings)
        
        if "settings" in self.app_context:
            self.app_context["settings"] = new_settings 
        
        root_app = self.winfo_toplevel()
        if hasattr(root_app, 'settings'): # Ažuriraj settings i u glavnoj App instanci
            root_app.settings = new_settings
        
        # Primijeni mod izgleda i temu odmah
        # Napomena: Promjena default_color_theme možda neće utjecati na već kreirane widgete
        # bez njihovog ponovnog konfiguriranja ili ponovnog pokretanja aplikacije.
        ctk.set_appearance_mode(new_settings["appearance_mode"])
        ctk.set_default_color_theme(new_settings["theme"])
        
        self.logger.info("Postavke spremljene.")
        messagebox.showinfo("Postavke", "Postavke su uspješno sačuvane.\nNeke promjene (npr. boja teme za postojeće elemente) mogu zahtijevati ponovno pokretanje aplikacije.", parent=self)
        
        dm = self.app_context.get("download_manager")
        if dm:
            dm.current_settings = new_settings # Obavijesti DownloadManager o novim postavkama

    def on_view_enter(self):
        super().on_view_enter() # Pozovi on_view_enter iz BaseView
        # Osvježi UI s trenutnim postavkama svaki put kad se uđe u view
        current_settings = sh.load_settings() 
        for key, var_tk in self.settings_vars.items():
            if key in current_settings:
                var_tk.set(current_settings[key])
        # Osiguraj da je i app_context ažuriran
        self.app_context["settings"] = current_settings
        root_app = self.winfo_toplevel()
        if hasattr(root_app, 'settings'):
            root_app.settings = current_settings
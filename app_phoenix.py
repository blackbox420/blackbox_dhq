# app_phoenix.py
import customtkinter as ctk
import tkinter as tk
import logging
import os
import datetime  # <-- Added import

from gui.main_window import MainWindow
from gui.license_activation_window import LicenseActivationWindow
from core.license_manager import LicenseManager
from core import settings_handler
from core import downloader_engine

APP_NAME = "BlackBox DHQ Phoenix v3.0 (UI Test)" # Možeš ažurirati fazu

# ... (logging setup kao prije) ...
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
os.makedirs(log_dir, exist_ok=True)
log_file_path = os.path.join(log_dir, "app_phoenix.log")

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)-8s - [%(name)s:%(lineno)d] (%(funcName)s) - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler(log_file_path, encoding='utf-8', mode='w'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class App:
    def __init__(self):
        logger.info(f"Starting application: {APP_NAME}")
        self.settings = settings_handler.load_settings()

        ctk.set_appearance_mode(self.settings.get("appearance_mode", "dark"))
        ctk.set_default_color_theme(self.settings.get("theme", "blue"))

        self.root = ctk.CTk()
        self.root.title(APP_NAME)
        self.root.geometry(self.settings.get("window_geometry", "1280x780"))
        self.root.protocol("WM_DELETE_WINDOW", self._on_app_quit)

        # --- ISPRAVLJENA KONFIGURACIJA GRID-A ZA self.root ---
        self.root.grid_rowconfigure(0, weight=1)  # Red za glavni UI (sidebar + content)
        self.root.grid_rowconfigure(1, weight=0)  # Red za statusnu traku

        self.root.grid_columnconfigure(0, weight=0, minsize=self.settings.get("sidebar_width", 240)) # Kolona za Sidebar (fiksna/min širina)
        self.root.grid_columnconfigure(1, weight=1) # Kolona za MainContentFrame (rasteže se)
        # ----------------------------------------------------

        self.status_bar_text_var = tk.StringVar(value="Spreman.")
        status_bar_fg_color = ("gray90", "gray15")
        status_bar = ctk.CTkLabel(self.root, textvariable=self.status_bar_text_var,
                                  anchor="w", height=28,
                                  font=ctk.CTkFont(size=11),
                                  fg_color=status_bar_fg_color)
        # Statusna traka zauzima obje kolone u svom redu
        status_bar.grid(row=1, column=0, columnspan=2, sticky="ew", padx=0, pady=0)

        self.download_manager = downloader_engine.Downloader(
            update_callback=self._placeholder_initial_dm_callback,
            max_concurrent_downloads=self.settings.get("max_concurrent_downloads", 1)
        )

        self.root.app_context = {
            "root": self.root,
            "settings": self.settings,
            "download_manager": self.download_manager,
            "status_bar_var": self.status_bar_text_var,
            "theme_colors": {}
        }
        try:
            from utils import theme_colors as app_theme_colors_module
            colors_dict = {
                attr: getattr(app_theme_colors_module.DarkThemeColors, attr)
                for attr in dir(app_theme_colors_module.DarkThemeColors)
                if not callable(getattr(app_theme_colors_module.DarkThemeColors, attr)) and not attr.startswith("__")
            }
            self.root.app_context["theme_colors"] = colors_dict
            logger.debug(f"Učitane boje teme: {self.root.app_context['theme_colors']}")
        except ImportError: logger.warning("Modul utils.theme_colors nije pronađen.")
        except Exception as e_colors: logger.error(f"Greška pri učitavanju boja teme: {e_colors}")

        self.license_manager = LicenseManager()
        self._check_license_and_launch()
    
    # ... (ostatak App klase: _placeholder_initial_dm_callback, _on_app_quit, 
    #      _check_license_and_launch, _show_license_activation, 
    #      _on_license_activated_successfully, _show_main_app ostaju isti) ...
    def _placeholder_initial_dm_callback(self, task, update_type, data=None):
         logger.debug(f"DM_INIT_CALLBACK: Task {task.item_id if task else 'N/A'}, Type: {update_type}, Data: {data}")

    def _on_app_quit(self):
         logger.info("Zatvaram aplikaciju...")
         current_geometry = self.root.geometry()
         self.settings["window_geometry"] = current_geometry
         settings_handler.save_settings(self.settings)
         if self.download_manager: self.download_manager.stop_worker()
         self.root.destroy()
         print(f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - INFO     - [__main__] (N/A) - Aplikacija uspješno zatvorena (konzolni ispis).")

    def _check_license_and_launch(self):
         is_valid, license_info_or_error = self.license_manager.is_license_valid()
         if is_valid:
             logger.info(f"Validna licenca pronađena: Tip {license_info_or_error.get('type')}")
             user_type = license_info_or_error.get("type", "standard")
             self.root.app_context["license_info"] = license_info_or_error
             self.root.app_context["license_manager"] = self.license_manager
             self.root.app_context["user_type"] = user_type
             self._show_main_app(user_type, license_info_or_error)
             self.root.mainloop() 
         else:
             logger.warning(f"Nema validne lokalne licence ili je istekla ({license_info_or_error}), pokrećem prozor za aktivaciju.")
             self.root.app_context["license_manager"] = self.license_manager
             self._show_license_activation()
             self.root.mainloop()

    def _show_license_activation(self):
         self.root.withdraw() 
         LicenseActivationWindow(  # Removed unused variable assignment
             self.root, self.license_manager, self._on_license_activated_successfully
         )

    def _on_license_activated_successfully(self, license_info):
         logger.info(f"Licenca uspješno aktivirana: Tip {license_info.get('type')}")
         for widget in self.root.winfo_children():
             if isinstance(widget, LicenseActivationWindow):
                  if widget.winfo_exists(): widget.destroy()
         self.root.deiconify()
         user_type = license_info.get("type", "standard")
         self.root.app_context["license_info"] = license_info
         self.root.app_context["user_type"] = user_type 
         self._show_main_app(user_type, license_info)

    def _show_main_app(self, user_type: str, license_info: dict):
         logger.info(f"Prikazujem glavni prozor aplikacije za korisnika tipa: {user_type}")
         self.main_window_instance = MainWindow(
             self.root, user_type, license_info, self.license_manager
         )
         if self.download_manager and hasattr(self.main_window_instance, 'handle_download_update'):
             self.download_manager.update_callback = self.main_window_instance.handle_download_update
         else:
             logger.error("Nije moguće postaviti DownloadManager callback na MainWindow!")

if __name__ == "__main__":
    # ... (try-except blok za pokretanje App ostaje isti) ...
    try:
        app = App()
    except Exception as e:
        logger.critical(f"Nepredviđena greška pri pokretanju aplikacije: {e}", exc_info=True)
        # Fallback Tkinter error popup
        import tkinter as tk_err_popup_fallback
        from tkinter import messagebox as tk_msg_err_popup_fallback
        try:
            root_err_popup_fallback = tk_err_popup_fallback.Tk()
            root_err_popup_fallback.withdraw()
            tk_msg_err_popup_fallback.showerror(
                "Kritična Greška Aplikacije",
                f"Došlo je do nepredviđene greške pri pokretanju:\n\n{e}\n\n"
                "Aplikacija se ne može pokrenuti. Molimo provjerite 'logs/app_phoenix.log' za detalje."
            )
            root_err_popup_fallback.destroy()
        except Exception as e_popup_fallback:
            print(f"KRITIČNO: Greška pri pokretanju, čak ni Tkinter popup nije uspio: {e_popup_fallback}")
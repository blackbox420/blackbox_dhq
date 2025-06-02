# app_phoenix.py
import customtkinter as ctk
import tkinter as tk  # Import for tk.StringVar
import logging
import os

# Pretpostavljam da su ovi importi ispravni s obzirom na tvoju strukturu foldera
from gui.main_window import MainWindow
from gui.license_activation_window import LicenseActivationWindow
from core.license_manager import LicenseManager
from core import settings_handler
from core import downloader_engine

APP_NAME = "BlackBox DHQ Phoenix v3.0 (Faza 3 Test)" # Ažuriraj verziju ako treba

# Postavljanje logging-a (preuzeto iz tvog fajla)
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
        self.root.geometry(self.settings.get("window_geometry", "1280x780")) # Koristi ažuriranu defaultnu geometriju
        self.root.protocol("WM_DELETE_WINDOW", self._on_app_quit)

        # --- IZMJENA OVDJE: Konfiguracija grid-a za self.root ---
        self.root.grid_rowconfigure(0, weight=1)  # Red za MainWindow će se rastezati
        self.root.grid_rowconfigure(1, weight=0)  # Red za statusnu traku, fiksna visina
        self.root.grid_columnconfigure(0, weight=1) # Jedna kolona koja se rasteže

        # Statusna traka - sada koristi grid
        self.status_bar_text_var = tk.StringVar(value="Spreman.")
        status_bar_fg_color = ("gray90", "gray15")
        status_bar = ctk.CTkLabel(self.root, textvariable=self.status_bar_text_var,
                                  anchor="w", height=28,
                                  font=ctk.CTkFont(size=11),
                                  fg_color=status_bar_fg_color)
        # Postavi statusnu traku u donji red (red 1)
        status_bar.grid(row=1, column=0, sticky="ew", padx=0, pady=0)

        self.download_manager = downloader_engine.Downloader(
            update_callback=self._placeholder_initial_dm_callback,
            max_concurrent_downloads=self.settings.get("max_concurrent_downloads", 1)
        )

        self.root.app_context = {
            "root": self.root,
            "settings": self.settings,
            "download_manager": self.download_manager,
            "status_bar_var": self.status_bar_text_var,
            "theme_colors": {} # Inicijaliziraj kao prazan rječnik
        }
        # Učitaj boje i spremi ih kao rječnik u app_context
        try:
            from utils import theme_colors as app_theme_colors_module
            # Pretpostavimo da želimo koristiti DarkThemeColors
            # Možeš dodati logiku za odabir Light/Dark na osnovu postavki kasnije
            
            # Kreiraj rječnik od atributa klase DarkThemeColors
            colors_dict = {
                attr: getattr(app_theme_colors_module.DarkThemeColors, attr)
                for attr in dir(app_theme_colors_module.DarkThemeColors)
                if not callable(getattr(app_theme_colors_module.DarkThemeColors, attr)) and not attr.startswith("__")
            }
            self.root.app_context["theme_colors"] = colors_dict
            logger.debug(f"Učitane boje teme: {self.root.app_context['theme_colors']}")
        except ImportError:
            logger.warning("Modul utils.theme_colors nije pronađen. Koristit će se defaultne boje widgeta.")
        except Exception as e_colors:
            logger.error(f"Greška pri učitavanju ili procesuiranju boja teme: {e_colors}")


        self.license_manager = LicenseManager()
        self._check_license_and_launch()

    def _placeholder_initial_dm_callback(self, task, update_type, data=None):
        # Ovaj callback će biti zamijenjen s onim iz MainWindow nakon inicijalizacije
        logger.debug(f"DM_INIT_CALLBACK: Task {task.item_id if task else 'N/A'}, Type: {update_type}, Data: {data}")

    def _on_app_quit(self):
        logger.info("Zatvaram aplikaciju...")
        # Spremi trenutnu geometriju prozora
        current_geometry = self.root.geometry()
        self.settings["window_geometry"] = current_geometry
        settings_handler.save_settings(self.settings)
        
        if self.download_manager:
            self.download_manager.stop_worker()

        self.root.destroy()
        logger.info("Aplikacija zatvorena.")

    def _check_license_and_launch(self):
        is_valid, license_info_or_error = self.license_manager.is_license_valid()

        if is_valid:
            logger.info(f"Validna licenca pronađena: Tip {license_info_or_error.get('type')}")
            user_type = license_info_or_error.get("type", "standard")
            self.root.app_context["license_info"] = license_info_or_error
            self.root.app_context["license_manager"] = self.license_manager # Dodaj i license_manager
            self.root.app_context["user_type"] = user_type
            self._show_main_app(user_type, license_info_or_error)
            self.root.mainloop() 
        else:
            logger.warning(f"Nema validne lokalne licence ili je istekla ({license_info_or_error}), pokrećem prozor za aktivaciju.")
            self.root.app_context["license_manager"] = self.license_manager # Osiguraj da je dostupan prozoru za aktivaciju
            self._show_license_activation()
            # Mainloop će biti pozvan nakon što aktivacijski prozor završi (ili ako se app zatvori)
            # Ako aktivacijski prozor nije striktno modalni ili ako se može zatvoriti bez aktivacije,
            # a aplikacija treba nastaviti raditi (npr. prikazati samo aktivacijski prozor),
            # onda self.root.mainloop() treba biti pozvan ovdje.
            # S obzirom da LicenseActivationWindow koristi grab_set(), trebao bi biti modalni.
            # Ako se aktivacijski prozor zatvori bez uspjeha, _on_close_attempt će ugasiti self.master (root).
            # Ako aktivacija uspije, _on_license_activated_successfully će pozvati _show_main_app
            # koji će implicitno nastaviti ili pokrenuti mainloop ako već nije.
            # Da budemo sigurni, ako _show_license_activation ne blokira do kraja aplikacije:
            if not (is_valid and self.root.winfo_exists()): # Ako licenca nije postala validna, a root još postoji
                 self.root.mainloop()


    def _show_license_activation(self):
        self.root.withdraw() 
        activation_window = LicenseActivationWindow( # Pridruživanje varijabli nije nužno ako se ne koristi kasnije
            self.root, 
            self.license_manager, 
            self._on_license_activated_successfully
        )
        # Nema potrebe za activation_window.mainloop() jer je CTkToplevel

    def _on_license_activated_successfully(self, license_info):
        logger.info(f"Licenca uspješno aktivirana: Tip {license_info.get('type')}")
        # Uništi sve postojeće prozore za aktivaciju
        # Iteriraj kroz djecu root prozora i uništi ako je instanca LicenseActivationWindow
        for widget in self.root.winfo_children():
            if isinstance(widget, LicenseActivationWindow): # Provjeri tip prozora
                 if widget.winfo_exists(): # Provjeri da li widget još postoji
                    widget.destroy()
        
        self.root.deiconify() # Pokaži glavni prozor
        user_type = license_info.get("type", "standard")
        self.root.app_context["license_info"] = license_info
        self.root.app_context["user_type"] = user_type 
        self._show_main_app(user_type, license_info)
        # Ako mainloop nije već pokrenut (npr. ako je ovo prvi put da se prikazuje glavni prozor),
        # _show_main_app ili ovaj dio bi ga trebao pokrenuti.
        # `_check_license_and_launch` već poziva `self.root.mainloop()` u oba slučaja.

    def _show_main_app(self, user_type: str, license_info: dict):
        logger.info(f"Prikazujem glavni prozor aplikacije za korisnika tipa: {user_type}")
        
        # MainWindow će biti postavljen u self.root koristeći grid interno (row=0, column=0)
        self.main_window_instance = MainWindow(
            self.root, 
            user_type, 
            license_info, 
            self.license_manager
        )
        
        # Sada kada MainWindow postoji, postavi pravi callback za DownloadManager
        if self.download_manager and hasattr(self.main_window_instance, 'handle_download_update'):
            self.download_manager.update_callback = self.main_window_instance.handle_download_update
        else:
            logger.error("Nije moguće postaviti DownloadManager callback na MainWindow!")

        # Metoda za ažuriranje statusne trake je sada dio MainWindow, koja koristi status_bar_var iz app_context
        # Nema potrebe za self.root.update_status_bar = ... ovdje


if __name__ == "__main__":
    try:
        app = App()
        # Glavni mainloop se sada poziva unutar _check_license_and_launch
        # ovisno o tome da li je licenca inicijalno validna ili nakon aktivacije.
    except Exception as e:
        logger.critical(f"Nepredviđena greška pri pokretanju aplikacije: {e}", exc_info=True)
        import tkinter as tk_err_popup
        from tkinter import messagebox as tk_msg_err_popup
        try:
            root_err_popup = tk_err_popup.Tk()
            root_err_popup.withdraw()
            tk_msg_err_popup.showerror(
                "Kritična Greška Aplikacije",
                f"Došlo je do nepredviđene greške pri pokretanju:\n\n{e}\n\n"
                "Aplikacija se ne može pokrenuti. Molimo provjerite 'logs/app_phoenix.log' za detalje."
            )
            root_err_popup.destroy()
        except Exception as e_popup:
            print(f"Kritična greška pri pokretanju, čak ni Tkinter popup nije uspio: {e_popup}")
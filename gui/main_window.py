# gui/main_window.py
import customtkinter as ctk
import tkinter as tk 
from tkinter import ttk, scrolledtext
import logging
import os

from .sidebar_frame import SidebarFrame
from .views.downloads_view import DownloadsView
from .views.queue_view import QueueView 
from .views.settings_view import SettingsView
# from .views.license_info_view import LicenseInfoView # Importat ćemo kasnije kad implementiramo
# from .views.admin_panel_view import AdminPanelView # Importat ćemo kasnije

from core import downloader_engine as de 
from utils import theme_colors

logger = logging.getLogger(__name__)

class MainWindow:
    def __init__(self, root: ctk.CTk, user_type: str, license_info: dict, license_manager_instance):
        self.root = root
        self.user_type = user_type
        self.license_info = license_info
        self.license_manager = license_manager_instance
        self.logger = logger 
        
        self.download_manager = self.root.app_context.get("download_manager")
        if self.download_manager:
            self.download_manager.update_callback = self.handle_download_update
        else:
            self.logger.error("KRITIČNO: DownloadManager nije dostupan u MainWindow!")

        self.current_view_name = None
        self.views_cache = {} # Rječnik za keširanje instanci pogleda

        self._setup_main_layout()
        self._create_views() 
        
        # Inicijalno postavi aktivni gumb u sidebar-u i prikaži defaultni pogled
        # Sidebar se kreira u _setup_main_layout, pa update_active_button treba pozvati nakon toga.
        # select_view će također pozvati update_active_button.
        self.select_view("dashboard") # Pokaži dashboard kao početni pogled

    def _setup_main_layout(self):
        # self.root (što je App.root) VEĆ IMA KONFIGURIRAN GRID (2 reda, 2 kolone)
        # Ne trebaš ponovno konfigurirati grid za self.root ovdje.
        
        sidebar_fg_color = self.root.app_context.get("theme_colors", {}).get("SIDEBAR_BACKGROUND", "#292A3D")
        sidebar_callbacks = {"select_view": self.select_view} # Proslijedi metodu direktno
        self.sidebar = SidebarFrame(master=self.root, 
                                   app_callbacks=sidebar_callbacks,
                                   user_type=self.user_type,
                                   app_context=self.root.app_context, # Proslijedi app_context
                                   width=self.root.app_context.get("settings", {}).get("sidebar_width", 240),
                                   fg_color=sidebar_fg_color,
                                   corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsw", padx=0, pady=0) 
        
        main_content_bg = self.root.app_context.get("theme_colors", {}).get("BACKGROUND_CONTENT", "#202130")
        self.main_content_frame = ctk.CTkFrame(self.root, fg_color=main_content_bg, corner_radius=0)
        self.main_content_frame.grid(row=0, column=1, sticky="nsew", padx=0, pady=0)
        
        self.main_content_frame.grid_columnconfigure(0, weight=1)
        self.main_content_frame.grid_rowconfigure(0, weight=1)

    def _create_views(self):
        app_context = self.root.app_context 
        # main_window_select_tab_callback se više ne prosljeđuje ovako, jer je select_view metoda ove klase
        # Ako pogledi trebaju mijenjati tabove, mogu pozvati self.app_context.get("main_window_select_tab_callback")("ime_taba")
        # Ali to je već riješeno jer se `select_view` prosljeđuje sidebar-u.

        theme_colors_dict = app_context.get("theme_colors", {})
        view_text_color = theme_colors_dict.get("TEXT_PRIMARY", "#FFFFFF")
        view_text_accent_color = theme_colors_dict.get("TEXT_ACCENT", view_text_color)
        view_text_secondary_color = theme_colors_dict.get("TEXT_SECONDARY", "gray")

        # Testne boje za debugiranje (ako želiš vratiti test s bojama)
        # test_colors_list = ["#FF5733", "#33FF57", "#3357FF", "#FFC300", "#FF33FB", "#00FFFB", "#C70039"]
        # current_color_index = 0
        # def get_next_test_color():
        #     nonlocal current_color_index
        #     color = test_colors_list[current_color_index % len(test_colors_list)]
        #     current_color_index += 1
        #     return color
        
        # Koristi konzistentnu pozadinsku boju za sve poglede (iz teme)
        default_view_bg_color = theme_colors_dict.get("BACKGROUND_CONTENT", "transparent")

        # Dashboard (Placeholder)
        dashboard_view = ctk.CTkFrame(self.main_content_frame, fg_color=default_view_bg_color)
        ctk.CTkLabel(dashboard_view, text="Dashboard", font=ctk.CTkFont(size=36, weight="bold"), text_color=view_text_accent_color).pack(pady=30, padx=30, anchor="nw")
        ctk.CTkLabel(dashboard_view, text="Pregled aktivnosti i statistika (uskoro).", font=ctk.CTkFont(size=16), text_color=view_text_secondary_color).pack(pady=10, padx=30, anchor="nw")
        self.views_cache["dashboard"] = dashboard_view
        
        self.views_cache["downloads"] = DownloadsView(self.main_content_frame, app_context, fg_color=default_view_bg_color) 
        self.views_cache["queue"] = QueueView(self.main_content_frame, app_context, fg_color=default_view_bg_color) 
        self.views_cache["settings"] = SettingsView(self.main_content_frame, app_context, fg_color=default_view_bg_color) 

        license_info_view = ctk.CTkFrame(self.main_content_frame, fg_color=default_view_bg_color)
        ctk.CTkLabel(license_info_view, text="Informacije o Licenci", font=ctk.CTkFont(size=36, weight="bold"), text_color=view_text_accent_color).pack(pady=30, padx=30, anchor="nw")
        current_lic_info = app_context.get("license_info", {})
        ctk.CTkLabel(license_info_view, text=f"Korisnik: {current_lic_info.get('user', 'N/A')}", font=ctk.CTkFont(size=16), text_color=view_text_color).pack(anchor="w", padx=30, pady=2)
        ctk.CTkLabel(license_info_view, text=f"Tip Licence: {current_lic_info.get('type', 'N/A')}", font=ctk.CTkFont(size=16), text_color=view_text_color).pack(anchor="w", padx=30, pady=2)
        ctk.CTkLabel(license_info_view, text=f"Status: {current_lic_info.get('status', 'N/A')}", font=ctk.CTkFont(size=16), text_color=view_text_color).pack(anchor="w", padx=30, pady=2)
        ctk.CTkLabel(license_info_view, text=f"Istječe: {current_lic_info.get('expires_at', 'N/A')}", font=ctk.CTkFont(size=16), text_color=view_text_color).pack(anchor="w", padx=30, pady=2)
        self.views_cache["license_info"] = license_info_view

        if self.user_type == "super_admin":
            admin_panel_view = ctk.CTkFrame(self.main_content_frame, fg_color=default_view_bg_color)
            ctk.CTkLabel(admin_panel_view, text="Admin Panel", font=ctk.CTkFont(size=36, weight="bold"), text_color=view_text_accent_color).pack(pady=30, padx=30, anchor="nw")
            ctk.CTkLabel(admin_panel_view, text="Dobrodošao, Harise! Ovo je tvoj administratorski panel (u izradi).", font=ctk.CTkFont(size=16), text_color=view_text_secondary_color).pack(anchor="w", padx=30)
            self.views_cache["admin_panel"] = admin_panel_view

    def select_view(self, view_name: str):
        self.logger.info(f"Pokušavam promijeniti pogled na: {view_name}")

        # Sakrij trenutno aktivni pogled
        if self.current_view_name and self.current_view_name in self.views_cache:
            current_view_instance = self.views_cache[self.current_view_name]
            if hasattr(current_view_instance, 'on_view_leave'):
                current_view_instance.on_view_leave()
            current_view_instance.grid_forget()
            self.logger.debug(f"Pogled '{self.current_view_name}' sakriven (grid_forget).")
        
        # Prikaži novi pogled
        if view_name in self.views_cache:
            self.current_view_name = view_name
            new_view_instance = self.views_cache[self.current_view_name]
            
            # Postavi pogled da zauzme cijeli main_content_frame
            new_view_instance.grid(row=0, column=0, sticky="nsew", in_=self.main_content_frame)
            # Podigni novi pogled na vrh (može pomoći ako ima preklapanja)
            new_view_instance.lift() 
            self.logger.debug(f"Pogled '{view_name}' postavljen (grid) i podignut (lift).")
            
            if hasattr(new_view_instance, 'on_view_enter'):
                new_view_instance.on_view_enter()
            
            if hasattr(self, 'sidebar'): # Osiguraj da sidebar postoji
                self.sidebar.update_active_button(view_name)
            self._update_status_bar(f"Prikazan pogled: {view_name.replace('_', ' ').capitalize()}")
        else:
            self.logger.warning(f"Pokušaj prikaza nepostojećeg pogleda: {view_name}")
            # Fallback na dashboard ako postoji, inače nemoj ništa mijenjati
            if self.current_view_name is None and "dashboard" in self.views_cache: # Ako nijedan view nije inicijalno postavljen
                self.logger.info("Fallback na 'dashboard' pogled.")
                self.select_view("dashboard") # Rekurzivni poziv, ali samo jednom
            else:
                self._update_status_bar(f"Greška: Pogled '{view_name}' nije pronađen.")


    def handle_download_update(self, task: de.DownloadTask, update_type: str, data=None):
        # Osiguraj da se GUI ažurira u glavnoj niti
        # Važno: root.after je metoda Tkinter root prozora
        if self.root and self.root.winfo_exists(): # Provjeri da li root prozor još postoji
            self.root.after(0, self._internal_handle_download_update, task, update_type, data)
        else:
            self.logger.warning("Root prozor ne postoji, ne mogu ažurirati GUI za download.")


    def _internal_handle_download_update(self, task: de.DownloadTask, update_type: str, data=None):
        # ... (ostatak _internal_handle_download_update metode kao prije) ...
        self.logger.debug(f"MainWindow (internal) primio update: Task ID {task.item_id if task else 'N/A'}, Type: {update_type}")
        queue_view_instance = self.views_cache.get("queue")
        if not isinstance(queue_view_instance, QueueView):
            self.logger.warning("QueueView nije inicijaliziran ili nije ispravnog tipa, ne mogu ažurirati GUI reda.")
            self._update_status_bar_for_task(task, update_type)
            return

        if update_type == "status_update":
            if task.status == "U redu":
                 if not queue_view_instance.queue_treeview.exists(str(task.item_id)):
                    queue_view_instance.add_task_to_view(task)
                 else: 
                    queue_view_instance.update_task_in_view(task)
            elif queue_view_instance.queue_treeview.exists(str(task.item_id)):
                 queue_view_instance.update_task_in_view(task)
        
        elif update_type == "progress_update":
            if queue_view_instance.queue_treeview.exists(str(task.item_id)):
                queue_view_instance.update_task_in_view(task)
            else:
                self.logger.warning(f"Progress update za nepostojeći task {task.item_id} u QueueView. Dodajem ga.")
                queue_view_instance.add_task_to_view(task)

        elif update_type == "download_complete" or update_type == "download_error":
            if queue_view_instance.queue_treeview.exists(str(task.item_id)):
                queue_view_instance.update_task_in_view(task)
            else:
                self.logger.warning(f"Download završen/greška za nepostojeći task {task.item_id} u QueueView. Dodajem sa završnim statusom.")
                queue_view_instance.add_task_to_view(task)

        if update_type == "log_message" and data:
            if hasattr(queue_view_instance, 'log_text_area') and \
               isinstance(queue_view_instance.log_text_area, ctk.CTkTextbox):
                try:
                    if queue_view_instance.log_text_area.winfo_exists():
                        queue_view_instance.log_text_area.configure(state="normal")
                        queue_view_instance.log_text_area.insert("end", f"{str(data)}\n")
                        queue_view_instance.log_text_area.configure(state="disabled")
                        queue_view_instance.log_text_area.see("end")
                except tk.TclError as e_log_tk:
                    self.logger.warning(f"Tkinter greška pri upisu u log panel QueueView-a (iz MainWindow): {e_log_tk}")
                except Exception as e_log:
                    self.logger.error(f"Greška pri upisu u log panel QueueView-a (iz MainWindow): {e_log}")
        
        self._update_status_bar_for_task(task, update_type)


    def _update_status_bar_for_task(self, task: de.DownloadTask | None, update_type:str):
        # ... (ostatak _update_status_bar_for_task metode kao prije) ...
        if not task: return
        task_name_for_status = os.path.basename(task.final_filename) if task.final_filename else os.path.basename(task.url)
        if len(task_name_for_status) > 70 : task_name_for_status = task_name_for_status[:67] + "..."
        message = ""
        if update_type == "status_update": message = f"{task_name_for_status}: {task.status}"
        elif update_type == "progress_update": message = f"{task_name_for_status}: {task.progress_str} @ {task.speed_str}, ETA: {task.eta_str}"
        elif update_type == "download_complete": message = f"Završeno: {task_name_for_status}"
        elif update_type == "download_error":
            error_preview = task.error_message[:50] + "..." if task.error_message and len(task.error_message) > 50 else task.error_message
            message = f"Greška: {task_name_for_status} ({error_preview if error_preview else 'Nepoznata greška'})"
        if message: self._update_status_bar(message)

    def _update_status_bar(self, message: str):
        # ... (ostatak _update_status_bar metode kao prije) ...
        status_bar_var = self.root.app_context.get("status_bar_var")
        if status_bar_var and isinstance(status_bar_var, tk.StringVar):
            status_bar_var.set(message)
            # self.logger.debug(f"Status bar ažuriran: {message}") # Smanji logiranje ovoga
        else:
            self.logger.warning(f"Pokušaj ažuriranja statusne trake, ali status_bar_var nije postavljen ili nije StringVar: '{message}'")
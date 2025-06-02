# gui/main_window.py
import customtkinter as ctk
import tkinter as tk
import logging
import os

from .sidebar_frame import SidebarFrame
from .views.downloads_view import DownloadsView
from .views.queue_view import QueueView 
from .views.settings_view import SettingsView
# from .views.license_info_view import LicenseInfoView 
# from .views.admin_panel_view import AdminPanelView 

from core import downloader_engine as de 

logger = logging.getLogger(__name__)

class MainWindow:
    def __init__(self, root: ctk.CTk, user_type: str, license_info: dict, license_manager_instance):
        self.root = root
        self.user_type = user_type
        self.license_info = license_info
        self.license_manager = license_manager_instance

        self.download_manager = self.root.app_context.get("download_manager")
        if self.download_manager:
            # Sada kada metoda postoji, ovo će raditi:
            self.download_manager.update_callback = self.handle_download_update
        else:
            logger.error("KRITIČNO: DownloadManager nije dostupan u MainWindow!")

        self.current_view_name = None
        self.views_cache = {}

        self._setup_main_layout()
        self._create_views() 

        default_initial_view = "dashboard" 
        self.sidebar.update_active_button(default_initial_view) 
        self.select_view(default_initial_view)

    # ... (_setup_main_layout i _create_views metode ostaju iste kao prije) ...
    def _setup_main_layout(self):
        sidebar_fg_color = self.root.app_context.get("theme_colors", {}).get("SIDEBAR_BACKGROUND", "#292A3D")
        sidebar_callbacks = {"select_view": self.select_view}
        self.sidebar = SidebarFrame(master=self.root, 
                                   app_callbacks=sidebar_callbacks,
                                   user_type=self.user_type,
                                   app_context=self.root.app_context,
                                   width=240,
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
        app_context["main_window_select_tab_callback"] = self.select_view 

        # --- TEST BOJE ZA POGLEDE ---
        test_colors_list = ["#FF5733", "#33FF57", "#3357FF", "#FFC300", "#FF33FB", "#00FFFB", "#C70039"]
        current_color_index = 0
        def get_next_test_color():
            nonlocal current_color_index
            color_to_return = test_colors_list[current_color_index % len(test_colors_list)]
            current_color_index += 1
            return color_to_return
        # -----------------------------

        # Dashboard (Placeholder) - ovo je CTkFrame, pa mu direktno postavljamo fg_color
        dashboard_view_color = get_next_test_color()
        self.logger.debug(f"Kreiram DashboardView s bojom: {dashboard_view_color}")
        dashboard_view = ctk.CTkFrame(self.main_content_frame, fg_color=dashboard_view_color) 
        ctk.CTkLabel(dashboard_view, text="Dashboard SADRŽAJ", font=ctk.CTkFont(size=36, weight="bold")).pack(pady=30, padx=30, anchor="nw")
        self.views_cache["dashboard"] = dashboard_view

        downloads_view_color = get_next_test_color()
        self.logger.debug(f"Kreiram DownloadsView s bojom: {downloads_view_color}")
        self.views_cache["downloads"] = DownloadsView(self.main_content_frame, app_context, fg_color=downloads_view_color) 

        queue_view_color = get_next_test_color()
        self.logger.debug(f"Kreiram QueueView s bojom: {queue_view_color}")
        self.views_cache["queue"] = QueueView(self.main_content_frame, app_context, fg_color=queue_view_color) 

        settings_view_color = get_next_test_color()
        self.logger.debug(f"Kreiram SettingsView s bojom: {settings_view_color}")
        self.views_cache["settings"] = SettingsView(self.main_content_frame, app_context, fg_color=settings_view_color) 

        license_info_color = get_next_test_color()
        self.logger.debug(f"Kreiram LicenseInfoView s bojom: {license_info_color}")
        license_info_view = ctk.CTkFrame(self.main_content_frame, fg_color=license_info_color)
        # ... (ostatak license_info_view) ...
        self.views_cache["license_info"] = license_info_view

        if self.user_type == "super_admin":
            admin_panel_color = get_next_test_color()
            self.logger.debug(f"Kreiram AdminPanelView s bojom: {admin_panel_color}")
            admin_panel_view = ctk.CTkFrame(self.main_content_frame, fg_color=admin_panel_color)
            # ... (ostatak admin_panel_view) ...
            self.views_cache["admin_panel"] = admin_panel_view

    # --- DODAJ OVU METODU ---
    def handle_download_update(self, task: de.DownloadTask, update_type: str, data=None):
        # Osiguraj da se GUI ažurira u glavnoj niti
        self.root.after(0, self._internal_handle_download_update, task, update_type, data)

    def _internal_handle_download_update(self, task: de.DownloadTask, update_type: str, data=None):
         logger.debug(f"MainWindow (internal) primio update: Task ID {task.item_id if task else 'N/A'}, Type: {update_type}, Podaci: {data if data else 'Nema'}")
         
         queue_view_instance = self.views_cache.get("queue")
         
         if isinstance(queue_view_instance, QueueView) and queue_view_instance.winfo_exists():
             if update_type == "status_update" and task.status == "U redu":
                 # Ovo je prvi put da vidimo task, ili je status resetiran na "U redu"
                 # add_task_to_view će ili dodati novi ili ažurirati postojeći
                 queue_view_instance.add_task_to_view(task)
             elif hasattr(queue_view_instance, 'queue_treeview') and queue_view_instance.queue_treeview.exists(str(task.item_id)):
                 queue_view_instance.update_task_in_view(task)
             elif update_type in ["progress_update", "download_complete", "download_error"]:
                 # Ako je ovo update za postojeći task koji iz nekog razloga nije u treeview, dodaj ga
                 logger.warning(f"Update ({update_type}) za task {task.item_id} koji nije u QueueView. Dodajem ga.")
                 queue_view_instance.add_task_to_view(task) # Ovo će ga dodati ili ažurirati

             # Logiranje u Log Panel unutar QueueView
             if update_type == "log_message" and data:
                 if hasattr(queue_view_instance, 'log_text_area') and \
                    isinstance(queue_view_instance.log_text_area, ctk.CTkTextbox):
                     try:
                         if queue_view_instance.log_text_area.winfo_exists():
                             queue_view_instance.log_text_area.configure(state="normal")
                             queue_view_instance.log_text_area.insert("end", f"{str(data)}\n")
                             queue_view_instance.log_text_area.configure(state="disabled")
                             queue_view_instance.log_text_area.see("end")
                     except tk.TclError as e_log_tk: # Uhvati grešku ako je widget uništen
                         logger.warning(f"Tkinter greška pri upisu u log panel QueueView-a (iz MainWindow): {e_log_tk}")
                     except Exception as e_log: # Općenitija greška
                         logger.error(f"Greška pri upisu u log panel QueueView-a (iz MainWindow): {e_log}")
         else:
             logger.warning("QueueView nije dostupan ili nije ispravnog tipa, ne mogu ažurirati GUI reda.")
         
         self._update_status_bar_for_task(task, update_type) # Ažuriraj statusnu traku

    def _update_status_bar_for_task(self, task: de.DownloadTask | None, update_type: str):
        """Helper metoda za ažuriranje statusne trake na osnovu taska."""
        if not task: 
            return

        task_name_for_status = os.path.basename(task.final_filename) if task.final_filename else os.path.basename(task.url)
        if len(task_name_for_status) > 70 : task_name_for_status = task_name_for_status[:67] + "..."

        message = ""
        if update_type == "status_update":
            message = f"{task_name_for_status}: {task.status}"
        elif update_type == "progress_update":
            message = f"{task_name_for_status}: {task.progress_str} @ {task.speed_str}, ETA: {task.eta_str}"
        elif update_type == "download_complete":
            message = f"Završeno: {task_name_for_status}"
        elif update_type == "download_error":
            # Skrati error_message ako je predugačak za status bar
            error_preview = task.error_message[:50] + "..." if task.error_message and len(task.error_message) > 50 else task.error_message
            message = f"Greška: {task_name_for_status} ({error_preview if error_preview else 'Nepoznata greška'})"

        if message:
            self._update_status_bar(message) # Pozovi općenitu metodu

    # --- DODAJ OVU NOVU METODU ---
    def _update_status_bar(self, message: str):
        """Općenita metoda za postavljanje teksta u statusnu traku."""
        status_bar_var = self.root.app_context.get("status_bar_var")
        if status_bar_var and isinstance(status_bar_var, tk.StringVar):
            status_bar_var.set(message)
            logger.debug(f"Status bar ažuriran: {message}")
        else:
            logger.warning(f"Pokušaj ažuriranja statusne trake, ali status_bar_var nije postavljen ili nije StringVar: '{message}'")

    # handle_download_update metoda ostaje ista, ali sada poziva self._update_status_bar_for_task
    def handle_download_update(self, task: de.DownloadTask, update_type: str, data=None):
        logger.debug(f"MainWindow primio update: Task ID {task.item_id if task else 'N/A'}, Type: {update_type}, Podaci: {data if data else 'Nema'}")

        queue_view_instance = self.views_cache.get("queue")
        if not isinstance(queue_view_instance, QueueView):
            logger.warning("QueueView nije inicijaliziran ili nije ispravnog tipa, ne mogu ažurirati GUI reda.")
            self._update_status_bar_for_task(task, update_type)
            return

        if update_type == "status_update":
            if task.status == "U redu" and not queue_view_instance.queue_treeview.exists(str(task.item_id)):
                queue_view_instance.add_task_to_view(task)
            else: 
                queue_view_instance.update_task_in_view(task)
        elif update_type == "progress_update":
            if queue_view_instance.queue_treeview.exists(str(task.item_id)):
                queue_view_instance.update_task_in_view(task)
            else:
                logger.warning(f"Progress update za nepostojeći task {task.item_id} u QueueView. Pokušavam dodati.")
                queue_view_instance.add_task_to_view(task)
        elif update_type == "download_complete" or update_type == "download_error":
            if queue_view_instance.queue_treeview.exists(str(task.item_id)):
                queue_view_instance.update_task_in_view(task)
            else:
                logger.warning(f"Download završen/greška za nepostojeći task {task.item_id} u QueueView. Dodajem sa završnim statusom.")
                queue_view_instance.add_task_to_view(task)

        if update_type == "log_message" and data:
            # Logiranje u CTkTextbox unutar QueueView
            if hasattr(queue_view_instance, 'log_text_area') and \
               isinstance(queue_view_instance.log_text_area, ctk.CTkTextbox):
                try:
                    if queue_view_instance.log_text_area.winfo_exists():
                        queue_view_instance.log_text_area.configure(state="normal")
                        queue_view_instance.log_text_area.insert("end", f"{str(data)}\n")
                        queue_view_instance.log_text_area.configure(state="disabled")
                        queue_view_instance.log_text_area.see("end")
                except tk.TclError as e_log_tk:
                    logger.warning(f"Tkinter greška pri upisu u log panel QueueView-a (iz MainWindow): {e_log_tk}")
                except Exception as e_log:
                    logger.error(f"Greška pri upisu u log panel QueueView-a (iz MainWindow): {e_log}")

        self._update_status_bar_for_task(task, update_type) # Ova metoda sada interno zove _update_status_bar

    # select_view metoda sada može sigurno pozvati self._update_status_bar
    def select_view(self, view_name: str):
        logger.info(f"Promjena pogleda na: {view_name}")
        # ... (ostatak select_view metode kao prije) ...
        if view_name in self.views_cache:
            # ... (prikazivanje novog pogleda) ...
            if hasattr(self, 'sidebar'): self.sidebar.update_active_button(view_name)
            self._update_status_bar(f"Prikazan pogled: {view_name.replace('_', ' ').capitalize()}") # Koristi novu metodu
        else:
            # ... (fallback na dashboard) ...
            self._update_status_bar(f"Pokušaj prikaza nepoznatog pogleda: {view_name}")
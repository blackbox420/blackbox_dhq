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
from .views.base_view import BaseView 

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
        self.logger.info(f"MainWindow initialized for user_type={user_type}") # Dodan log
        
        self.download_manager = self.root.app_context.get("download_manager")
        if self.download_manager:
            # Ovo će sada raditi jer handle_download_update postoji ispod
            self.download_manager.update_callback = self.handle_download_update
        else:
            self.logger.error("KRITIČNO: DownloadManager nije dostupan u MainWindow!")

        self.current_view_name = None
        self.views_cache = {}

        self._setup_main_layout()
        self._create_views() 
        
        default_initial_view = "dashboard" 
        if hasattr(self, 'sidebar'):
            self.sidebar.update_active_button(default_initial_view) 
        self.select_view(default_initial_view)

    def _setup_main_layout(self):
        self.logger.debug("Postavljam glavni layout MainWindow-a...")
        sidebar_fg_color = self.root.app_context.get("theme_colors", {}).get("SIDEBAR_BACKGROUND", "#292A3D")
        sidebar_callbacks = {"select_view": self.select_view}
        self.sidebar = SidebarFrame(master=self.root, 
                                   app_callbacks=sidebar_callbacks,
                                   user_type=self.user_type,
                                   app_context=self.root.app_context,
                                   width=self.root.app_context.get("settings", {}).get("sidebar_width", 240),
                                   fg_color=sidebar_fg_color,
                                   corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsw", padx=0, pady=0) 
        
        main_content_bg = self.root.app_context.get("theme_colors", {}).get("BACKGROUND_CONTENT", "#202130")
        self.main_content_frame = ctk.CTkFrame(self.root, fg_color=main_content_bg, corner_radius=0)
        self.main_content_frame.grid(row=0, column=1, sticky="nsew", padx=0, pady=0)
        
        self.main_content_frame.grid_columnconfigure(0, weight=1)
        self.main_content_frame.grid_rowconfigure(0, weight=1)
        self.logger.debug("Glavni layout MainWindow-a postavljen.")


    def _create_views(self):
        self.logger.debug("Kreiram poglede (views)...")
        app_context = self.root.app_context 
        
        theme_colors_dict = app_context.get("theme_colors", {})
        view_text_color = theme_colors_dict.get("TEXT_PRIMARY", "#FFFFFF")
        view_text_accent_color = theme_colors_dict.get("TEXT_ACCENT", view_text_color)
        view_text_secondary_color = theme_colors_dict.get("TEXT_SECONDARY", "gray")
        
        # Testne boje za debugiranje vidljivosti pogleda
        test_colors_list = ["#E53935", "#43A047", "#1E88E5", "#FDD835", "#8E24AA", "#00ACC1", "#FB8C00"]
        current_color_index = 0
        def get_next_test_color():
            nonlocal current_color_index
            color_to_return = test_colors_list[current_color_index % len(test_colors_list)]
            current_color_index += 1
            # self.logger.info(f"Dodjeljujem testnu boju: {color_to_return} za view_idx {current_color_index-1}") # Smanji log spam
            return color_to_return
        
        # Dashboard
        dashboard_color = get_next_test_color()
        self.logger.debug(f"Kreiram DashboardView s testnom bojom: {dashboard_color}")
        dashboard_view = ctk.CTkFrame(self.main_content_frame, fg_color=dashboard_color) 
        ctk.CTkLabel(dashboard_view, text=f"DASHBOARD ({dashboard_color})", 
                     font=ctk.CTkFont(size=30, weight="bold"), text_color="white" if dashboard_color != "yellow" else "black"
                    ).pack(padx=20, pady=20, expand=True, anchor="center")
        self.views_cache["dashboard"] = dashboard_view
        
        downloads_color = get_next_test_color()
        self.logger.debug(f"Kreiram DownloadsView s testnom bojom: {downloads_color}")
        self.views_cache["downloads"] = DownloadsView(self.main_content_frame, app_context, fg_color=downloads_color) 
        
        queue_color = get_next_test_color()
        self.logger.debug(f"Kreiram QueueView s testnom bojom: {queue_color}")
        self.views_cache["queue"] = QueueView(self.main_content_frame, app_context, fg_color=queue_color) 
        
        settings_color = get_next_test_color()
        self.logger.debug(f"Kreiram SettingsView s testnom bojom: {settings_color}")
        self.views_cache["settings"] = SettingsView(self.main_content_frame, app_context, fg_color=settings_color) 

        license_info_color = get_next_test_color()
        self.logger.debug(f"Kreiram LicenseInfoView s testnom bojom: {license_info_color}")
        license_info_view = ctk.CTkFrame(self.main_content_frame, fg_color=license_info_color)
        ctk.CTkLabel(license_info_view, text=f"LICENCA INFO ({license_info_color})", font=ctk.CTkFont(size=30, weight="bold"), text_color="white" if license_info_color != "yellow" else "black").pack(expand=True, anchor="center")
        current_lic_info = app_context.get("license_info", {})
        ctk.CTkLabel(license_info_view, text=f"Korisnik: {current_lic_info.get('user', 'N/A')}", text_color=view_text_color, fg_color=license_info_color).pack(anchor="w", padx=30, pady=2)
        ctk.CTkLabel(license_info_view, text=f"Tip Licence: {current_lic_info.get('type', 'N/A')}", text_color=view_text_color, fg_color=license_info_color).pack(anchor="w", padx=30, pady=2)
        ctk.CTkLabel(license_info_view, text=f"Status: {current_lic_info.get('status', 'N/A')}", text_color=view_text_color, fg_color=license_info_color).pack(anchor="w", padx=30, pady=2)
        ctk.CTkLabel(license_info_view, text=f"Istječe: {current_lic_info.get('expires_at', 'N/A')}", text_color=view_text_color, fg_color=license_info_color).pack(anchor="w", padx=30, pady=2)
        self.views_cache["license_info"] = license_info_view

        if self.user_type == "super_admin":
            admin_panel_color = get_next_test_color()
            self.logger.debug(f"Kreiram AdminPanelView s testnom bojom: {admin_panel_color}")
            admin_panel_view = ctk.CTkFrame(self.main_content_frame, fg_color=admin_panel_color)
            ctk.CTkLabel(admin_panel_view, text=f"ADMIN PANEL ({admin_panel_color})", font=ctk.CTkFont(size=30, weight="bold"), text_color="white" if admin_panel_color != "yellow" else "black").pack(expand=True, anchor="center")
            self.views_cache["admin_panel"] = admin_panel_view
        self.logger.debug("Svi pogledi kreirani.")

    def select_view(self, view_name: str):
        self.logger.info(f"Pokušavam promijeniti pogled na: {view_name}")
        if self.current_view_name and self.current_view_name in self.views_cache:
            current_view_instance = self.views_cache[self.current_view_name]
            if hasattr(current_view_instance, 'on_view_leave'): current_view_instance.on_view_leave()
            current_view_instance.grid_forget(); self.logger.debug(f"Pogled '{self.current_view_name}' sakriven.")
        if view_name in self.views_cache:
            self.current_view_name = view_name
            new_view_instance = self.views_cache[self.current_view_name]
            new_view_instance.grid(row=0, column=0, sticky="nsew", in_=self.main_content_frame)
            new_view_instance.lift(); self.root.update_idletasks()
            self.logger.debug(f"Pogled '{view_name}' postavljen. W: {new_view_instance.winfo_width()}, H: {new_view_instance.winfo_height()}")
            if hasattr(new_view_instance, 'on_view_enter'): new_view_instance.on_view_enter()
            if hasattr(self, 'sidebar'): self.sidebar.update_active_button(view_name)
            self._update_status_bar(f"Prikazan pogled: {view_name.replace('_', ' ').capitalize()}")
        else:
            self.logger.warning(f"Pokušaj prikaza nepostojećeg pogleda: {view_name}")
            if self.current_view_name is None and "dashboard" in self.views_cache:
                self.logger.info("Fallback na 'dashboard'."); self.select_view("dashboard")
            else: self._update_status_bar(f"Greška: Pogled '{view_name}' nije pronađen.")

    def _update_status_bar(self, message: str):
        status_bar_var = self.root.app_context.get("status_bar_var")
        if status_bar_var and isinstance(status_bar_var, tk.StringVar):
            status_bar_var.set(message)
        else: self.logger.warning(f"Status_bar_var nije postavljen: '{message}'")

    def handle_download_update(self, task: de.DownloadTask, update_type: str, data=None):
        if self.root and self.root.winfo_exists():
            self.root.after(0, self._internal_handle_download_update, task, update_type, data)
        else: self.logger.warning("Root prozor ne postoji, ne mogu ažurirati GUI za download.")

    def _internal_handle_download_update(self, task: de.DownloadTask, update_type: str, data=None):
        self.logger.debug(f"MW internal update: Task ID {task.item_id if task else 'N/A'}, Type: {update_type}")
        queue_view_instance = self.views_cache.get("queue")
        # Prvo provjeri da li je queue_view_instance ispravnog tipa i da li POSTOJI i da li IMA queue_treeview
        if not isinstance(queue_view_instance, QueueView) or \
           not hasattr(queue_view_instance, 'queue_treeview') or \
           not queue_view_instance.queue_treeview: # Dodatna provjera da nije None
            self.logger.warning("QueueView ili QueueView.queue_treeview nije inicijaliziran/dostupan.")
            self._update_status_bar_for_task(task, update_type) # Ažuriraj barem statusnu traku
            return 
        
        # Sada znamo da queue_view_instance.queue_treeview postoji

        if update_type == "status_update":
            if task.status == "U redu":
                 if not queue_view_instance.queue_treeview.exists(str(task.item_id)): queue_view_instance.add_task_to_view(task)
                 else: queue_view_instance.update_task_in_view(task)
            elif queue_view_instance.queue_treeview.exists(str(task.item_id)): queue_view_instance.update_task_in_view(task)
            elif task.status != "U redu": self.logger.warning(f"Update statusa za nepostojeći task {task.item_id} ({task.status}).")
        elif update_type == "progress_update":
            if queue_view_instance.queue_treeview.exists(str(task.item_id)): queue_view_instance.update_task_in_view(task)
            else: self.logger.warning(f"Progress update za nepostojeći task {task.item_id}. Dodajem."); queue_view_instance.add_task_to_view(task)
        elif update_type == "download_complete" or update_type == "download_error":
            if queue_view_instance.queue_treeview.exists(str(task.item_id)): queue_view_instance.update_task_in_view(task)
            else: self.logger.warning(f"Download završen/greška za nepostojeći task {task.item_id}. Dodajem."); queue_view_instance.add_task_to_view(task)
        if update_type == "log_message" and data:
            if hasattr(queue_view_instance, 'log_text_area') and isinstance(queue_view_instance.log_text_area, ctk.CTkTextbox):
                try:
                    if queue_view_instance.log_text_area.winfo_exists():
                        queue_view_instance.log_text_area.configure(state="normal")
                        queue_view_instance.log_text_area.insert("end", f"{str(data)}\n")
                        queue_view_instance.log_text_area.configure(state="disabled"); queue_view_instance.log_text_area.see("end")
                except tk.TclError as e_log_tk: self.logger.warning(f"Tkinter greška pri upisu u log ({e_log_tk})")
                except Exception as e_log: self.logger.error(f"Greška pri upisu u log ({e_log})")
        self._update_status_bar_for_task(task, update_type)

    def _update_status_bar_for_task(self, task: de.DownloadTask | None, update_type:str):
        if not task: 
            if update_type == "general_status_update" and self.root.app_context.get("status_bar_var_data"): # Provjeri da li 'data' postoji za ovaj tip
                message = self.root.app_context.get("status_bar_var_data") # 'data' je proslijeđen kao 3. argument u update_callback
                if message : self._update_status_bar(str(message))
            return
        task_name = os.path.basename(task.final_filename) if task.final_filename else os.path.basename(task.url)
        if len(task_name) > 70 : task_name = task_name[:67] + "..."
        message = ""
        if update_type == "status_update": message = f"{task_name}: {task.status}"
        elif update_type == "progress_update": message = f"{task_name}: {task.progress_str} @ {task.speed_str}, ETA: {task.eta_str}"
        elif update_type == "download_complete": message = f"Završeno: {task_name}"
        elif update_type == "download_error":
            err_preview = task.error_message[:50]+"..." if task.error_message and len(task.error_message)>50 else task.error_message
            message = f"Greška: {task_name} ({err_preview if err_preview else 'Nepoznato'})"
        if message: self._update_status_bar(message)
# gui/main_window.py
import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox  # Added for messagebox dialogs
import logging
import os

from .sidebar_frame import SidebarFrame
from .views.downloads_view import DownloadsView
from .views.queue_view import QueueView
from .views.settings_view import SettingsView

from core import downloader_engine as de

logger = logging.getLogger(__name__)

class MainWindow:
    def __init__(self, root: ctk.CTk, user_type: str, license_info: dict, license_manager_instance):
        self.root = root
        self.user_type = user_type
        self.license_info = license_info
        self.license_manager = license_manager_instance
        self.logger = logger
        self.logger.info(f"MainWindow initialized for user_type={user_type}")

        self.download_manager = self.root.app_context.get("download_manager")
        if self.download_manager:
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
        self.sidebar = SidebarFrame(
            master=self.root,
            app_callbacks=sidebar_callbacks,
            user_type=self.user_type,
            app_context=self.root.app_context,
            width=self.root.app_context.get("settings", {}).get("sidebar_width", 240),
            fg_color=sidebar_fg_color,
            corner_radius=0
        )
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
        default_view_bg_color = theme_colors_dict.get("BACKGROUND_CONTENT", "#202130")
        view_text_color = theme_colors_dict.get("TEXT_PRIMARY", "#FFFFFF")
        view_text_accent_color = theme_colors_dict.get("TEXT_ACCENT", view_text_color)
        view_text_secondary_color = theme_colors_dict.get("TEXT_SECONDARY", "gray")

        # Dashboard
        self.logger.debug(f"Kreiram DashboardView.")
        dashboard_view = ctk.CTkFrame(self.main_content_frame, fg_color=default_view_bg_color)
        ctk.CTkLabel(
            dashboard_view,
            text="Dashboard",
            font=ctk.CTkFont(size=36, weight="bold"),
            text_color=view_text_accent_color
        ).pack(pady=30, padx=30, anchor="nw")
        ctk.CTkLabel(
            dashboard_view,
            text="Pregled aktivnosti i statistika (uskoro).",
            font=ctk.CTkFont(size=16),
            text_color=view_text_secondary_color
        ).pack(pady=10, padx=30, anchor="nw")
        self.views_cache["dashboard"] = dashboard_view

        self.logger.debug(f"Kreiram DownloadsView.")
        self.views_cache["downloads"] = DownloadsView(self.main_content_frame, app_context)

        self.logger.debug(f"Kreiram QueueView.")
        self.views_cache["queue"] = QueueView(self.main_content_frame, app_context)

        self.logger.debug(f"Kreiram SettingsView.")
        self.views_cache["settings"] = SettingsView(self.main_content_frame, app_context)

        # License Info
        self.logger.debug(f"Kreiram LicenseInfoView.")
        license_info_view = ctk.CTkFrame(self.main_content_frame, fg_color=default_view_bg_color)
        ctk.CTkLabel(
            license_info_view,
            text="Informacije o Licenci",
            font=ctk.CTkFont(size=36, weight="bold"),
            text_color=view_text_accent_color
        ).pack(pady=30, padx=30, anchor="nw")
        current_lic_info = app_context.get("license_info", {})
        ctk.CTkLabel(
            license_info_view,
            text=f"Korisnik: {current_lic_info.get('user', 'N/A')}",
            font=ctk.CTkFont(size=16),
            text_color=view_text_color
        ).pack(anchor="w", padx=30, pady=2)
        ctk.CTkLabel(
            license_info_view,
            text=f"Tip Licence: {current_lic_info.get('type', 'N/A')}",
            font=ctk.CTkFont(size=16),
            text_color=view_text_color
        ).pack(anchor="w", padx=30, pady=2)
        ctk.CTkLabel(
            license_info_view,
            text=f"Status: {current_lic_info.get('status', 'N/A')}",
            font=ctk.CTkFont(size=16),
            text_color=view_text_color
        ).pack(anchor="w", padx=30, pady=2)
        ctk.CTkLabel(
            license_info_view,
            text=f"Istječe: {current_lic_info.get('expires_at', 'N/A')}",
            font=ctk.CTkFont(size=16),
            text_color=view_text_color
        ).pack(anchor="w", padx=30, pady=2)
        ctk.CTkButton(
            license_info_view,
            text="Odjavi Licencu",
            command=self._deactivate_license_action,
            fg_color=theme_colors_dict.get("ERROR"),
            hover_color=theme_colors_dict.get("WARNING")
        ).pack(pady=20, padx=30, anchor="w")
        self.views_cache["license_info"] = license_info_view

        if self.user_type == "super_admin":
            self.logger.debug(f"Kreiram AdminPanelView.")
            admin_panel_view = ctk.CTkFrame(self.main_content_frame, fg_color=default_view_bg_color)
            ctk.CTkLabel(
                admin_panel_view,
                text="Admin Panel",
                font=ctk.CTkFont(size=36, weight="bold"),
                text_color=view_text_accent_color
            ).pack(pady=30, padx=30, anchor="nw")
            ctk.CTkLabel(
                admin_panel_view,
                text="Dobrodošao, Harise! Ovo je tvoj administratorski panel (u izradi).",
                font=ctk.CTkFont(size=16),
                text_color=view_text_secondary_color
            ).pack(anchor="w", padx=30)
            self.views_cache["admin_panel"] = admin_panel_view
        self.logger.debug("Svi pogledi kreirani.")

    def _deactivate_license_action(self):
        if messagebox.askyesno(
            "Odjava Licence",
            "Jeste li sigurni da želite odjaviti trenutnu licencu?\nAplikacija će se zatvoriti i morat ćete ponovno unijeti ključ pri sljedećem pokretanju.",
            parent=self.root
        ):
            if self.license_manager:
                self.license_manager.clear_local_license()
                self.logger.info("Licenca odjavljena. Zatvaram aplikaciju.")
                if hasattr(self.root, '_on_app_quit'):
                    self.root._on_app_quit(from_logout=True)
                else:
                    self.root.destroy()
            else:
                messagebox.showerror("Greška", "LicenseManager nije dostupan.", parent=self.root)

    def select_view(self, view_name: str):
        self.logger.info(f"Pokušavam promijeniti pogled na: {view_name}")
        if self.current_view_name and self.current_view_name in self.views_cache:
            current_view_instance = self.views_cache[self.current_view_name]
            if hasattr(current_view_instance, 'on_view_leave'):
                current_view_instance.on_view_leave()
            current_view_instance.grid_forget()
            self.logger.debug(f"Pogled '{self.current_view_name}' sakriven.")
        if view_name in self.views_cache:
            self.current_view_name = view_name
            new_view_instance = self.views_cache[self.current_view_name]
            new_view_instance.grid(row=0, column=0, sticky="nsew", in_=self.main_content_frame)
            new_view_instance.lift()
            self.root.update_idletasks()
            self.logger.debug(f"Pogled '{view_name}' postavljen. W: {new_view_instance.winfo_width()}, H: {new_view_instance.winfo_height()}")
            if hasattr(new_view_instance, 'on_view_enter'):
                new_view_instance.on_view_enter()
            if hasattr(self, 'sidebar'):
                self.sidebar.update_active_button(view_name)
            self._update_status_bar(f"Prikazan pogled: {view_name.replace('_', ' ').capitalize()}")
        else:
            self.logger.warning(f"Pokušaj prikaza nepostojećeg pogleda: {view_name}")
            if self.current_view_name is None and "dashboard" in self.views_cache:
                self.logger.info("Fallback na 'dashboard'.")
                self.select_view("dashboard")
            else:
                self._update_status_bar(f"Greška: Pogled '{view_name}' nije pronađen.")

    def _update_status_bar(self, message: str):
        status_bar_var = self.root.app_context.get("status_bar_var")
        if status_bar_var and isinstance(status_bar_var, tk.StringVar):
            status_bar_var.set(message)
        else:
            self.logger.warning(f"Status_bar_var nije postavljen: '{message}'")

    def handle_download_update(self, task: de.DownloadTask, update_type: str, data=None):
        if self.root and self.root.winfo_exists():
            self.root.after(0, self._internal_handle_download_update, task, update_type, data)
        else:
            self.logger.warning("Root prozor ne postoji, ne mogu ažurirati GUI za download.")

    def _internal_handle_download_update(self, task: de.DownloadTask, update_type: str, data=None):
        self.logger.debug(f"MW internal update: Task ID {task.item_id if task else 'N/A'}, Type: {update_type}")
        queue_view_instance = self.views_cache.get("queue")
        if not isinstance(queue_view_instance, QueueView) or \
           not hasattr(queue_view_instance, 'queue_treeview') or \
           not queue_view_instance.queue_treeview:
            self.logger.warning("QueueView ili QueueView.queue_treeview nije inicijaliziran/dostupan.")
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
            elif task.status != "U redu":
                self.logger.warning(f"Update statusa za nepostojeći task {task.item_id} ({task.status}).")
        elif update_type == "progress_update":
            if queue_view_instance.queue_treeview.exists(str(task.item_id)):
                queue_view_instance.update_task_in_view(task)
            else:
                self.logger.warning(f"Progress update za nepostojeći task {task.item_id}. Dodajem.")
                queue_view_instance.add_task_to_view(task)
        elif update_type == "download_complete" or update_type == "download_error":
            if queue_view_instance.queue_treeview.exists(str(task.item_id)):
                queue_view_instance.update_task_in_view(task)
            else:
                self.logger.warning(f"Download završen/greška za nepostojeći task {task.item_id}. Dodajem.")
                queue_view_instance.add_task_to_view(task)
        if update_type == "log_message" and data:
            if hasattr(queue_view_instance, 'log_text_area') and isinstance(queue_view_instance.log_text_area, ctk.CTkTextbox):
                try:
                    if queue_view_instance.log_text_area.winfo_exists():
                        queue_view_instance.log_text_area.configure(state="normal")
                        queue_view_instance.log_text_area.insert("end", f"{str(data)}\n")
                        queue_view_instance.log_text_area.configure(state="disabled")
                        queue_view_instance.log_text_area.see("end")
                except tk.TclError as e_log_tk:
                    self.logger.warning(f"Tkinter greška pri upisu u log ({e_log_tk})")
                except Exception as e_log:
                    self.logger.error(f"Greška pri upisu u log ({e_log})")
        self._update_status_bar_for_task(task, update_type)

    def _update_status_bar_for_task(self, task: de.DownloadTask | None, update_type: str):
        if not task:
            if update_type == "general_status_update" and self.root.app_context.get("status_bar_var_data"):
                message = self.root.app_context.get("status_bar_var_data")
                if message:
                    self._update_status_bar(str(message))
            return
        task_name = os.path.basename(task.final_filename) if task.final_filename else os.path.basename(task.url)
        if len(task_name) > 70:
            task_name = task_name[:67] + "..."
        message = ""
        if update_type == "status_update":
            message = f"{task_name}: {task.status}"
        elif update_type == "progress_update":
            message = f"{task_name}: {task.progress_str} @ {task.speed_str}, ETA: {task.eta_str}"
        elif update_type == "download_complete":
            message = f"Završeno: {task_name}"
        elif update_type == "download_error":
            err_preview = task.error_message[:50] + "..." if task.error_message and len(task.error_message) > 50 else task.error_message
            message = f"Greška: {task_name} ({err_preview if err_preview else 'Nepoznato'})"
        if message:
            self._update_status_bar(message)
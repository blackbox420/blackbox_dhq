import customtkinter as ctk # <<< DODAN OVAJ IMPORT
import tkinter as tk # Za ttk.Treeview i StringVar ako se koristi
from tkinter import ttk, scrolledtext
import logging
import os

from .sidebar_frame import SidebarFrame
from .views.downloads_view import DownloadsView
from .views.queue_view import QueueView 
from .views.settings_view import SettingsView
# from .views.license_info_view import LicenseInfoView 
# from .views.admin_panel_view import AdminPanelView 

from core import downloader_engine as de 
# from core import settings_handler as sh # Nije direktno potrebno ovdje ako se sve vuče iz app_context
from utils import theme_colors

logger = logging.getLogger(__name__)

class MainWindow:
    def __init__(self, root: ctk.CTk, user_type: str, license_info: dict, license_manager_instance):
        self.root = root
        self.user_type = user_type
        self.license_info = license_info
        self.license_manager = license_manager_instance
        
        self.download_manager = self.root.app_context.get("download_manager")
        if self.download_manager:
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

    def _setup_main_layout(self):
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(0, weight=1)
        sidebar_fg_color = theme_colors.DarkThemeColors.SIDEBAR_BACKGROUND
        sidebar_callbacks = {"select_view": self.select_view}
        self.sidebar = SidebarFrame(master=self.root, 
                                   app_callbacks=sidebar_callbacks,
                                   user_type=self.user_type,
                                   app_context=self.root.app_context, # <<<<< DODAJ OVAJ ARGUMENT
                                   width=240,
                                   fg_color=sidebar_fg_color,
                                   corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew", padx=0, pady=0) # Sjever-Jug-Istok-Zapad
        # ...
        self.main_content_frame = ctk.CTkFrame(self.root, fg_color=theme_colors.DarkThemeColors.BACKGROUND_CONTENT, corner_radius=0)
        self.main_content_frame.grid(row=0, column=1, sticky="nsew", padx=0, pady=0)
        self.main_content_frame.grid_columnconfigure(0, weight=1)
        self.main_content_frame.grid_rowconfigure(0, weight=1)

    def _create_views(self):
        app_context = self.root.app_context 
        # Callbacks koji se prosljeđuju pogledima:
        app_context["main_window_select_tab_callback"] = self.select_view 
        # app_context["status_bar_update_callback"] nije više potreban ako MainWindow direktno ažurira

        # Dashboard (Placeholder)
        dashboard_view = ctk.CTkFrame(self.main_content_frame, fg_color=app_context.get("theme_colors", {}).get("BACKGROUND_CONTENT", "transparent"))
        ctk.CTkLabel(dashboard_view, text="Dashboard", font=ctk.CTkFont(size=36, weight="bold"), text_color=app_context.get("theme_colors", {}).get("TEXT_PRIMARY")).pack(pady=30, padx=30, anchor="nw")
        ctk.CTkLabel(dashboard_view, text="Pregled aktivnosti i statistika (uskoro).", font=ctk.CTkFont(size=16), text_color=app_context.get("theme_colors", {}).get("TEXT_SECONDARY")).pack(pady=10, padx=30, anchor="nw")
        self.views_cache["dashboard"] = dashboard_view
        
        self.views_cache["downloads"] = DownloadsView(self.main_content_frame, app_context)
        self.views_cache["queue"] = QueueView(self.main_content_frame, app_context)
        self.views_cache["settings"] = SettingsView(self.main_content_frame, app_context)
        
        # License Info (Placeholder)
        license_info_view = ctk.CTkFrame(self.main_content_frame, fg_color=app_context.get("theme_colors", {}).get("BACKGROUND_CONTENT", "transparent"))
        ctk.CTkLabel(license_info_view, text="Informacije o Licenci", font=ctk.CTkFont(size=36, weight="bold"), text_color=app_context.get("theme_colors", {}).get("TEXT_PRIMARY")).pack(pady=30, padx=30, anchor="nw")
        # Ovdje ćeš prikazati self.license_info
        ctk.CTkLabel(license_info_view, text=f"Korisnik: {self.license_info.get('user', 'N/A')}", font=ctk.CTkFont(size=16)).pack(anchor="w", padx=30)
        ctk.CTkLabel(license_info_view, text=f"Tip Licence: {self.license_info.get('type', 'N/A')}", font=ctk.CTkFont(size=16)).pack(anchor="w", padx=30)
        ctk.CTkLabel(license_info_view, text=f"Status: {self.license_info.get('status', 'N/A')}", font=ctk.CTkFont(size=16)).pack(anchor="w", padx=30)
        ctk.CTkLabel(license_info_view, text=f"Istječe: {self.license_info.get('expires_at', 'N/A')}", font=ctk.CTkFont(size=16)).pack(anchor="w", padx=30)
        self.views_cache["license_info"] = license_info_view

        if self.user_type == "super_admin":
            admin_panel_view = ctk.CTkFrame(self.main_content_frame, fg_color=app_context.get("theme_colors", {}).get("BACKGROUND_CONTENT", "transparent"))
            ctk.CTkLabel(admin_panel_view, text="Admin Panel", font=ctk.CTkFont(size=36, weight="bold"), text_color=app_context.get("theme_colors", {}).get("TEXT_PRIMARY")).pack(pady=30, padx=30, anchor="nw")
            ctk.CTkLabel(admin_panel_view, text="Dobrodošao, Harise! Ovo je tvoj administratorski panel (u izradi).", font=ctk.CTkFont(size=16)).pack(anchor="w", padx=30)
            self.views_cache["admin_panel"] = admin_panel_view

    def select_view(self, view_name: str):
        logger.info(f"Promjena pogleda na: {view_name}")
        if self.current_view_name and self.current_view_name in self.views_cache:
            current_view_instance = self.views_cache[self.current_view_name]
            if hasattr(current_view_instance, 'on_view_leave'): current_view_instance.on_view_leave()
            current_view_instance.grid_forget()
        
        if view_name in self.views_cache:
            self.current_view_name = view_name
            new_view_instance = self.views_cache[self.current_view_name]
            new_view_instance.grid(row=0, column=0, sticky="nsew", in_=self.main_content_frame)
            if hasattr(new_view_instance, 'on_view_enter'): new_view_instance.on_view_enter()
            if hasattr(self, 'sidebar'): self.sidebar.update_active_button(view_name)
        else:
            logger.warning(f"Pokušaj prikaza nepostojećeg pogleda: {view_name}")
            if "dashboard" in self.views_cache: self.select_view("dashboard")
        self._update_status_bar(f"Prikazan pogled: {view_name.capitalize()}")


def handle_download_update(self, task: de.DownloadTask, update_type: str, data=None):
    logger.debug(f"MainWindow primio update: Task ID {task.item_id if task else 'N/A'}, Type: {update_type}, Podaci: {data if data else 'Nema'}")
    
    queue_view_instance = self.views_cache.get("queue")
    if not isinstance(queue_view_instance, QueueView):
        logger.warning("QueueView nije inicijaliziran ili nije ispravnog tipa, ne mogu ažurirati GUI reda.")
        # Ažuriraj samo statusnu traku ako QueueView nije dostupan
        self._update_status_bar_for_task(task, update_type)
        return

    # Novi zadatak se dodaje u red ili se status ažurira
    if update_type == "status_update":
        if task.status == "U redu" and not queue_view_instance.queue_treeview.exists(task.item_id):
            queue_view_instance.add_task_to_view(task)
        else: # Ažuriraj postojeći ili ako je status nešto drugo
            queue_view_instance.update_task_in_view(task)
    
    elif update_type == "progress_update":
        if queue_view_instance.queue_treeview.exists(task.item_id):
            queue_view_instance.update_task_in_view(task) # update_task_in_view će ažurirati sve vrijednosti
        else: # Ako ne postoji, možda ga treba dodati (npr. ako je prvi update progress)
            logger.warning(f"Progress update za nepostojeći task {task.item_id} u QueueView. Dodajem ga.")
            queue_view_instance.add_task_to_view(task)

    elif update_type == "download_complete" or update_type == "download_error":
        if queue_view_instance.queue_treeview.exists(task.item_id):
            queue_view_instance.update_task_in_view(task) # Završni update statusa i eventualno imena fajla
        else: # Ako je task završen/error a nije bio u listi, dodaj ga sa završnim statusom
            logger.warning(f"Download završen/greška za nepostojeći task {task.item_id} u QueueView. Dodajem ga sa završnim statusom.")
            queue_view_instance.add_task_to_view(task) # Prikazat će Završeno/Greška

    # Logiranje u Log Panel unutar QueueView (već postoji u QueueView, poziva se iz DM)
    # Ali ako stižu logovi direktno u MainWindow, možeš ih proslijediti
    if update_type == "log_message" and data:
        if hasattr(queue_view_instance, 'log_text_area') and \
           isinstance(queue_view_instance.log_text_area, ctk.CTkTextbox): # Provjeri da je CTkTextbox
            try:
                if queue_view_instance.log_text_area.winfo_exists():
                    queue_view_instance.log_text_area.configure(state="normal")
                    queue_view_instance.log_text_area.insert("end", f"{data}\n") # data je već formatiran string
                    queue_view_instance.log_text_area.configure(state="disabled")
                    queue_view_instance.log_text_area.see("end")
            except tk.TclError as e_log_tk:
                logger.warning(f"Tkinter greška pri upisu u log panel QueueView-a (iz MainWindow): {e_log_tk}")
            except Exception as e_log:
                logger.error(f"Greška pri upisu u log panel QueueView-a (iz MainWindow): {e_log}")
    
    self._update_status_bar_for_task(task, update_type)

def _update_status_bar_for_task(self, task: de.DownloadTask, update_type:str):
     """Helper metoda za ažuriranje statusne trake na osnovu taska."""
     if not task: return
     task_name_for_status = os.path.basename(task.final_filename) if task.final_filename else os.path.basename(task.url)
     if len(task_name_for_status) > 50: task_name_for_status = task_name_for_status[:47] + "..."

     message = ""
     if update_type == "status_update":
         message = f"{task_name_for_status}: {task.status}"
     elif update_type == "progress_update":
         message = f"{task_name_for_status}: {task.progress_str} @ {task.speed_str}, ETA: {task.eta_str}"
     elif update_type == "download_complete":
         message = f"Završeno: {task_name_for_status}"
     elif update_type == "download_error":
         message = f"Greška: {task_name_for_status}"
     
     if message:
         status_bar_var = self.root.app_context.get("status_bar_var")
         if status_bar_var and isinstance(status_bar_var, tk.StringVar):
             status_bar_var.set(message)
         else:
             logger.warning(f"Pokušaj ažuriranja statusne trake, ali status_bar_var nije postavljen: {message}")
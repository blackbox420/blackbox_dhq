# gui/views/queue_view.py
import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, scrolledtext
from .base_view import BaseView
import logging
import os
from core import downloader_engine as de # <<<<<< DODAJ OVAJ IMPORT

logger = logging.getLogger(__name__)

# Custom Handler za Logging u CTkTextbox widget
class CTkTextboxHandler(logging.Handler):
    def __init__(self, textbox_widget: ctk.CTkTextbox):
        super().__init__()
        self.textbox_widget = textbox_widget

    def emit(self, record):
        msg = self.format(record)
        # Osiguraj da se GUI ažurira iz glavne niti
        # CTkTextbox nema after metodu direktno, ali njegov master (root) ima
        if self.textbox_widget.winfo_exists(): # Provjeri da li widget još postoji
             self.textbox_widget.master.after(0, self._append_text, msg)

    def _append_text(self, msg):
        if self.textbox_widget.winfo_exists():
            self.textbox_widget.configure(state="normal")
            self.textbox_widget.insert("end", msg + '\n')
            self.textbox_widget.configure(state="disabled")
            self.textbox_widget.see("end")


class QueueView(BaseView):
    def __init__(self, master, app_context: dict, **kwargs):
        super().__init__(master, "queue", app_context, **kwargs)
        self.treeview_item_map = {} 
        self.dm = self.app_context.get("download_manager") # Dohvati download manager

        # Postavi handler za logove na CTkTextbox ako log panel postoji
        if hasattr(self, 'log_text_area') and self.log_text_area:
            text_handler = CTkTextboxHandler(self.log_text_area)
            formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s', datefmt='%H:%M:%S')
            text_handler.setFormatter(formatter)
            # Dodaj handler na logger koji koristi downloader_engine (ili root logger)
            # Pretpostavimo da downloader_engine koristi logger s imenom 'core.downloader_engine'
            # Ili jednostavno dodaj na root logger za sve poruke
            logging.getLogger('core.downloader_engine').addHandler(text_handler) 
            logging.getLogger('core.downloader_engine').setLevel(logging.DEBUG) # Osiguraj da hvata DEBUG poruke
            # Ako želiš sve logove aplikacije:
            # logging.getLogger().addHandler(text_handler)
            text_handler.setLevel(logging.INFO) # Podesi koji nivo logova želiš u GUI-ju


    def build_ui(self):
        # PanedWindow za promjenu veličine
        paned_window = ctk.CTkFrame(self, fg_color="transparent") # Koristi CTkFrame kao PanedWindow
        paned_window.pack(fill="both", expand=True, padx=5, pady=5) # Smanjen padx/pady

        # Gornji dio: Red čekanja (Treeview)
        queue_frame = ctk.CTkFrame(paned_window, fg_color="transparent")
        queue_frame.pack(fill="both", expand=True, pady=(0,5)) # Malo razmaka ispod reda

        title_label = ctk.CTkLabel(queue_frame, text="Red Čekanja Preuzimanja", font=ctk.CTkFont(size=22, weight="bold"), anchor="w")
        title_label.pack(pady=(5,10), padx=10, fill="x") # Smanjen padding

        tree_container = ctk.CTkFrame(queue_frame, fg_color="transparent")
        tree_container.pack(fill="both", expand=True, padx=10)


        style = ttk.Style()
        # Uzmi boje iz app_context ili koristi default CustomTkinter boje
        theme_colors_dict = self.app_context.get("theme_colors", {})
        bg_color = theme_colors_dict.get("BACKGROUND_CONTENT", self.cget("fg_color")) # Boja pozadine treeview-a
        text_color = theme_colors_dict.get("TEXT_PRIMARY", ctk.ThemeManager.theme["CTkLabel"]["text_color"][0 if ctk.get_appearance_mode() == "Light" else 1])
        selected_color = theme_colors_dict.get("LIST_ITEM_SELECTED_BG", ctk.ThemeManager.theme["CTkButton"]["fg_color"][0 if ctk.get_appearance_mode() == "Light" else 1])
        header_bg_color = theme_colors_dict.get("BACKGROUND_SECONDARY", ctk.ThemeManager.theme["CTkFrame"]["top_fg_color"][0 if ctk.get_appearance_mode() == "Light" else 1])
        
        style.theme_use("default")
        style.configure("Custom.Treeview", background=bg_color, foreground=text_color, fieldbackground=bg_color, borderwidth=0, rowheight=28)
        style.map("Custom.Treeview", background=[('selected', selected_color)], foreground=[('selected', theme_colors_dict.get("LIST_ITEM_SELECTED_FG_TEXT", "white"))])
        style.configure("Custom.Treeview.Heading", background=header_bg_color, foreground=text_color, relief="flat", font=('Segoe UI', 10, 'bold'))
        style.map("Custom.Treeview.Heading", relief=[('active','groove'),('pressed','sunken')])

        cols = ("filename", "quality", "status", "progress", "speed_eta") # Spojeno Speed i ETA
        col_names = ("Zadatak", "Kvaliteta", "Status", "Napredak", "Brzina / ETA")
        col_widths = {"filename": 350, "quality": 180, "status": 120, "progress": 120, "speed_eta": 150}
        col_anchors = {"filename": "w", "quality": "w", "status": "w", "progress": "w", "speed_eta":"w"}

        self.queue_treeview = ttk.Treeview(tree_container, columns=cols, show="headings", style="Custom.Treeview", height=7)
        for i, col_id in enumerate(cols):
            self.queue_treeview.heading(col_id, text=col_names[i], anchor=tk.W)
            self.queue_treeview.column(col_id, width=col_widths[col_id], anchor=col_anchors[col_id], stretch=tk.YES if col_id=="filename" else tk.NO)
        
        tree_scrollbar_y = ctk.CTkScrollbar(tree_container, command=self.queue_treeview.yview)
        self.queue_treeview.configure(yscrollcommand=tree_scrollbar_y.set)
        self.queue_treeview.pack(side="left", fill="both", expand=True)
        tree_scrollbar_y.pack(side="right", fill="y")

        # Tagovi za stiliziranje
        self.queue_treeview.tag_configure('completed', background=theme_colors_dict.get("SUCCESS", "lightgreen"), foreground='black')
        self.queue_treeview.tag_configure('error', background=theme_colors_dict.get("ERROR", "pink"), foreground='black')
        # 'downloading' tag se može koristiti za npr. boldiranje teksta ili drugačiju fg boju, ali progress bar je bolji indikator

        # Donji dio: Log prozor (koristi CTkTextbox)
        log_frame = ctk.CTkFrame(paned_window, fg_color="transparent")
        log_frame.pack(fill="both", expand=True, pady=(5,0), padx=10) # Malo razmaka iznad loga

        log_label = ctk.CTkLabel(log_frame, text="Detaljni Logovi:", font=ctk.CTkFont(size=14, weight="bold"), anchor="w")
        log_label.pack(fill="x", pady=(5,5))

        self.log_text_area = ctk.CTkTextbox(log_frame, wrap="word", state="disabled", height=150,
                                            border_width=1, border_color=theme_colors_dict.get("BORDER_PRIMARY", "gray50"),
                                            font=ctk.CTkFont(family="Consolas", size=10)) # Monospace font za logove
        self.log_text_area.pack(fill="both", expand=True)
        
        # Postavljanje logging handlera nakon što je log_text_area kreiran
        self._setup_logging_handler()


        # Gumbi za akcije nad redom
        action_frame = ctk.CTkFrame(self, fg_color="transparent")
        action_frame.pack(fill="x", padx=20, pady=(10,5))
        
        self.start_all_btn = ctk.CTkButton(action_frame, text="Pokreni Sve u Redu", command=self._start_all_downloads, height=30)
        self.start_all_btn.pack(side="left", padx=5)

        self.clear_completed_btn = ctk.CTkButton(action_frame, text="Očisti Završene", command=self._clear_completed_tasks, height=30)
        self.clear_completed_btn.pack(side="left", padx=5)

        self.cancel_selected_btn = ctk.CTkButton(action_frame, text="Otkaži Odabrano", command=self._cancel_selected_task, height=30, state="disabled")
        self.cancel_selected_btn.pack(side="left", padx=5)
        
        self.queue_treeview.bind("<<TreeviewSelect>>", self._on_treeview_select)


    def _setup_logging_handler(self):
         if hasattr(self, 'log_text_area') and self.log_text_area:
             text_handler = CTkTextboxHandler(self.log_text_area)
             formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s', datefmt='%H:%M:%S')
             text_handler.setFormatter(formatter)
             
             # Dodaj handler na root logger da hvata sve logove ili na specifične loggere
             root_logger = logging.getLogger() 
             # Provjeri da li je handler već dodan da izbjegneš duple poruke
             if not any(isinstance(h, CTkTextboxHandler) and h.textbox_widget == self.log_text_area for h in root_logger.handlers):
                 root_logger.addHandler(text_handler)
                 text_handler.setLevel(logging.INFO) # Prikazuj INFO i iznad u GUI logu
                 logger.info("CTkTextboxHandler uspješno dodan na root logger.")
             else:
                 logger.info("CTkTextboxHandler je već bio dodan.")
         else:
             logger.error("Pokušaj postavljanja logging handlera, ali log_text_area nije inicijaliziran.")


    def _on_treeview_select(self, event=None):
        selected_items = self.queue_treeview.selection()
        if selected_items:
            self.cancel_selected_btn.configure(state="normal")
        else:
            self.cancel_selected_btn.configure(state="disabled")

    def _start_all_downloads(self):
        if self.dm:
            logger.info("Pokretanje svih preuzimanja u redu.")
            self.dm.start_worker() # Osiguraj da je worker pokrenut
            status_bar_var = self.app_context.get("status_bar_var")
            if status_bar_var: status_bar_var.set("Pokrećem preuzimanja iz reda...")
        else:
            logger.error("DownloadManager nije dostupan za pokretanje reda.")


    def _clear_completed_tasks(self):
        items_to_delete = []
        for item_id in self.queue_treeview.get_children():
            task = self.treeview_item_map.get(item_id)
            if task and (task.status == "Završeno" or "Greška" in task.status):
                items_to_delete.append(item_id)
        
        for item_id in items_to_delete:
            self.remove_task_from_view(item_id)
        logger.info(f"Obrisano {len(items_to_delete)} završenih/neuspjelih zadataka iz prikaza.")


    def _cancel_selected_task(self):
        selected_items = self.queue_treeview.selection()
        if not selected_items:
            messagebox.showwarning("Nema odabira", "Molimo odaberite zadatak za otkazivanje.", parent=self)
            return
        
        task_item_id = selected_items[0] # Otkaži samo prvi odabrani za sada
        task_to_cancel = self.treeview_item_map.get(task_item_id)

        if task_to_cancel and self.dm:
            if messagebox.askyesno("Potvrda Otkazivanja", f"Jeste li sigurni da želite otkazati preuzimanje za:\n{task_to_cancel.url}?", parent=self):
                # TODO: Potrebna je metoda u DownloadManageru za otkazivanje specifičnog taska
                # npr. self.dm.cancel_task(task_to_cancel)
                # Za sada, samo ga uklanjamo iz prikaza i logiramo.
                logger.info(f"Zahtjev za otkazivanje taska: {task_item_id} (URL: {task_to_cancel.url}). Implementiraj logiku u DM.")
                task_to_cancel.status = "Otkazano (korisnik)"
                task_to_cancel.progress_str = "-"
                task_to_cancel.speed_str = ""
                task_to_cancel.eta_str = ""
                self.update_task_in_view(task_to_cancel) # Ažuriraj prikaz
                # Realno otkazivanje bi zaustavilo yt-dlp proces.
                # Nakon što DownloadManager implementira otkazivanje, on bi trebao poslati update.
        self.cancel_selected_btn.configure(state="disabled")


    def add_task_to_view(self, task: de.DownloadTask): # Koristi de.DownloadTask
        if task.item_id in self.treeview_item_map:
            self.update_task_in_view(task)
            return

        display_url = task.url
        if len(display_url) > 60: display_url = display_url[:57] + "..."
        
        if not self.queue_treeview.exists(task.item_id):
             self.queue_treeview.insert("", "end", iid=task.item_id, values=(
                 display_url, task.quality_profile_key, task.status,
                 task.progress_str, f"{task.speed_str} / {task.eta_str}"
             ))
             self.treeview_item_map[task.item_id] = task
        else: 
             self.update_task_in_view(task)

    def update_task_in_view(self, task: de.DownloadTask): # Koristi de.DownloadTask
        if not self.queue_treeview.exists(task.item_id):
            logger.warning(f"Pokušaj ažuriranja nepostojećeg itema u QueueView: {task.item_id}. Dodajem ga.")
            self.add_task_to_view(task)
            return

        display_url = os.path.basename(task.final_filename) if task.final_filename else task.url
        if len(display_url) > 60: display_url = display_url[:57] + "..."

        self.queue_treeview.item(task.item_id, values=(
            display_url, task.quality_profile_key, task.status,
            task.progress_str, f"{task.speed_str} / {task.eta_str}"
        ))

        tags_to_apply = ()
        if task.status == "Završeno": tags_to_apply = ('completed',)
        elif "Greška" in task.status: tags_to_apply = ('error',)
        elif task.status == "Preuzimanje...": tags_to_apply = ('downloading',)
        self.queue_treeview.item(task.item_id, tags=tags_to_apply)

    # ... (on_view_enter, on_view_leave kao prije) ...
    def on_view_enter(self):
         super().on_view_enter()
         # Osvježi prikaz reda ako je potrebno (npr. ako su taskovi dodani dok view nije bio aktivan)
         # Ovo zahtijeva da DownloadManager čuva listu svih taskova.
         # if self.dm:
         #     all_tasks = self.dm.get_all_tasks_snapshot() # Pretpostavljena metoda
         #     for item in self.queue_treeview.get_children(): self.queue_treeview.delete(item)
         #     self.treeview_item_map.clear()
         #     for task in all_tasks: self.add_task_to_view(task)
         self.cancel_selected_btn.configure(state="disabled")
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
        self.level = logging.NOTSET # Defaultni nivo, može se promijeniti

    def emit(self, record):
        if not self.textbox_widget.winfo_exists(): # Ne radi ništa ako je widget uništen
            return
        
        msg = self.format(record)
        
        # Određivanje taga na osnovu nivoa loga
        tag = None
        if record.levelno == logging.ERROR or record.levelno == logging.CRITICAL:
            tag = "ERROR"
        elif record.levelno == logging.WARNING:
            tag = "WARNING"
        elif record.levelno == logging.INFO:
            # Poseban tretman za naše "[STATUS]" poruke
            if record.getMessage().startswith("[STATUS]"):
                 msg = record.getMessage().replace("[STATUS]", "").strip() # Ukloni prefiks
                 tag = "STATUS" # Koristi poseban tag za status
            elif "yt-dlp out" in record.name or "yt-dlp stdout_rem" in record.name or "yt-dlp stderr" in record.name:
                tag = "YTDLP_OUTPUT" # Za yt-dlp output
            else:
                tag = "INFO"
        elif record.levelno == logging.DEBUG:
            tag = "DEBUG"
        
        self.textbox_widget.master.after(0, self._append_text, msg, tag)

    def _append_text(self, msg, tag):
        if self.textbox_widget.winfo_exists():
            self.textbox_widget.configure(state="normal")
            self.textbox_widget.insert("end", msg + '\n', tags=(tag,) if tag else None)
            self.textbox_widget.configure(state="disabled")
            self.textbox_widget.see("end")


class QueueView(BaseView):
    def __init__(self, master, app_context: dict, **kwargs):
        # self.queue_treeview i self.log_text_area će biti inicijalizirani u build_ui
        self.queue_treeview: ttk.Treeview | None = None # Eksplicitna inicijalizacija na None
        self.log_text_area: ctk.CTkTextbox | None = None # Eksplicitna inicijalizacija na None
        self.treeview_item_map = {} 
        self.dm = app_context.get("download_manager")
        self.log_text_area_handler_ref = None 
        super().__init__(master, "queue", app_context, **kwargs)
        # build_ui se poziva iz super().__init__

    def build_ui(self):
        # ... (kod za title_label, queue_actions_top_frame, control_buttons_frame, tree_container, stilovi, kolone - SVE KAO PRIJE) ...
        # Samo osiguraj da su sve reference na self.queue_treeview i self.log_text_area ispravne
        # nakon što su ti widgeti kreirani.

        self.grid_rowconfigure(1, weight=3)
        self.grid_rowconfigure(3, weight=1)
        self.grid_columnconfigure(0, weight=1)

        title_label = ctk.CTkLabel(self, text="Red Čekanja i Log Preuzimanja", font=ctk.CTkFont(size=26, weight="bold"), anchor="w")
        title_label.grid(row=0, column=0, pady=(10,5), padx=20, sticky="ew") # Smanjen donji pady

        queue_actions_top_frame = ctk.CTkFrame(self, fg_color="transparent")
        queue_actions_top_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=0)
        queue_actions_top_frame.grid_columnconfigure(0, weight=1)
        queue_actions_top_frame.grid_rowconfigure(1, weight=1)

        control_buttons_frame = ctk.CTkFrame(queue_actions_top_frame, fg_color="transparent")
        control_buttons_frame.grid(row=0, column=0, sticky="ew", pady=(0,10)) # Povećan donji pady
        
        theme_colors = self.app_context.get("theme_colors", {})
        btn_fg = theme_colors.get("BUTTON_FG_COLOR")
        btn_hover = theme_colors.get("BUTTON_HOVER_COLOR")

        self.start_all_btn = ctk.CTkButton(control_buttons_frame, text="Pokreni Sve", command=self._start_all_downloads, height=30, fg_color=btn_fg, hover_color=btn_hover)
        self.start_all_btn.pack(side="left", padx=5)
        self.clear_completed_btn = ctk.CTkButton(control_buttons_frame, text="Očisti Listu", command=self._clear_finished_tasks, height=30, fg_color=btn_fg, hover_color=btn_hover)
        self.clear_completed_btn.pack(side="left", padx=5)
        self.cancel_selected_btn = ctk.CTkButton(control_buttons_frame, text="Otkaži Odabrano", command=self._cancel_selected_task, height=30, state="disabled", fg_color=btn_fg, hover_color=btn_hover)
        self.cancel_selected_btn.pack(side="left", padx=5)
        
        tree_container = ctk.CTkFrame(queue_actions_top_frame, fg_color="transparent")
        tree_container.grid(row=1, column=0, sticky="nsew")
        tree_container.grid_columnconfigure(0, weight=1)
        tree_container.grid_rowconfigure(0, weight=1)

        # --- Treeview setup (kao prije) ---
        style = ttk.Style()
        appearance_mode = ctk.get_appearance_mode()
        bg_color = theme_colors.get("TREEVIEW_BG", self.cget("fg_color")[1 if appearance_mode == "Dark" else 0])
        text_color = theme_colors.get("TREEVIEW_TEXT", "#000000" if appearance_mode == "Light" else "#FFFFFF")
        selected_color = theme_colors.get("TREEVIEW_SELECTED_BG", "#3471CD")
        selected_text_color = theme_colors.get("TREEVIEW_SELECTED_FG", "white")
        header_bg_color = theme_colors.get("TREEVIEW_HEADING_BG", "#DADADA" if appearance_mode == "Light" else "#2B2B2B")
        header_text_color = theme_colors.get("TREEVIEW_HEADING_FG", text_color)

        style.theme_use("default")
        style.configure("Custom.Treeview", background=bg_color, foreground=text_color, fieldbackground=bg_color, borderwidth=0, rowheight=28)
        style.map("Custom.Treeview", background=[('selected', selected_color)], foreground=[('selected', selected_text_color)])
        style.configure("Custom.Treeview.Heading", background=header_bg_color, foreground=header_text_color, relief="flat", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"))
        style.map("Custom.Treeview.Heading", relief=[('active','groove'),('pressed','sunken')])

        cols = ("filename", "quality", "status", "progress", "speed_eta")
        col_names = ("Zadatak", "Kvaliteta", "Status", "Napredak", "Brzina / ETA")
        col_widths = {"filename": 350, "quality": 180, "status": 120, "progress": 100, "speed_eta": 150}
        col_anchors = {"filename": "w", "quality": "w", "status": "w", "progress": "w", "speed_eta":"w"}

        self.queue_treeview = ttk.Treeview(tree_container, columns=cols, show="headings", style="Custom.Treeview", height=8) # Smanjena visina malo
        for i, col_id in enumerate(cols):
            self.queue_treeview.heading(col_id, text=col_names[i], anchor=tk.W)
            self.queue_treeview.column(col_id, width=col_widths[col_id], minwidth=col_widths[col_id]//2, anchor=col_anchors[col_id], stretch=tk.YES if col_id=="filename" else tk.NO)
        
        tree_scrollbar_y = ctk.CTkScrollbar(tree_container, command=self.queue_treeview.yview)
        self.queue_treeview.configure(yscrollcommand=tree_scrollbar_y.set)
        self.queue_treeview.grid(row=0, column=0, sticky="nsew")
        tree_scrollbar_y.grid(row=0, column=1, sticky="ns")

        self.queue_treeview.tag_configure('COMPLETED', background=theme_colors.get("SUCCESS", "lightgreen"), foreground=theme_colors.get("TEXT_PRIMARY_ON_SUCCESS", "black"))
        self.queue_treeview.tag_configure('ERROR', background=theme_colors.get("ERROR", "pink"), foreground=theme_colors.get("TEXT_PRIMARY_ON_ERROR", "black"))
        self.queue_treeview.tag_configure('DOWNLOADING', foreground=theme_colors.get("ACCENT_PRIMARY", "blue"))
        self.queue_treeview.tag_configure('WAITING', foreground=theme_colors.get("TEXT_SECONDARY", "gray"))

        # --- Log prozor ---
        log_main_frame = ctk.CTkFrame(self, fg_color="transparent")
        log_main_frame.grid(row=3, column=0, sticky="nsew", padx=5, pady=(5,0)) # row=3 za logove
        log_main_frame.grid_rowconfigure(1, weight=1)
        log_main_frame.grid_columnconfigure(0, weight=1)

        log_label = ctk.CTkLabel(log_main_frame, text="Detaljni Logovi:", font=ctk.CTkFont(size=14, weight="bold"), anchor="w")
        log_label.grid(row=0, column=0, pady=(5,5), padx=10, sticky="ew")

        self.log_text_area = ctk.CTkTextbox(log_main_frame, wrap="word", state="disabled", height=100, # Prilagodi visinu
                                            border_width=1, 
                                            border_color=theme_colors.get("BORDER_PRIMARY", "gray50"),
                                            font=ctk.CTkFont(family="Consolas", size=10))
        self.log_text_area.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0,5))
        
        self._setup_logging_handler() # Postavi handler NAKON što je log_text_area kreiran
        
        self.queue_treeview.bind("<<TreeviewSelect>>", self._on_treeview_select)
        
        # Inicijalno popuni red ako ima taskova u DM-u
        self.on_view_enter()


    def _setup_logging_handler(self): # Ostaje isto
         if hasattr(self, 'log_text_area') and self.log_text_area:
             text_handler = CTkTextboxHandler(self.log_text_area)
             formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s', datefmt='%H:%M:%S')
             text_handler.setFormatter(formatter)
             root_logger = logging.getLogger() 
             if not any(isinstance(h, CTkTextboxHandler) and h.textbox_widget == self.log_text_area for h in root_logger.handlers):
                 root_logger.addHandler(text_handler)
                 text_handler.setLevel(logging.DEBUG) # Postavi na DEBUG da vidimo više
                 logger.info("CTkTextboxHandler uspješno dodan na root logger.")
             else: logger.info("CTkTextboxHandler je već bio dodan.")
         else: logger.error("Pokušaj postavljanja logging handlera, ali log_text_area nije inicijaliziran.")

    def _on_treeview_select(self, event=None): # Ostaje isto
        selected_items = self.queue_treeview.selection()
        self.cancel_selected_btn.configure(state="normal" if selected_items else "disabled")

    def _start_all_downloads(self): # Ostaje isto
        if self.dm:
            logger.info("Pokretanje svih preuzimanja u redu."); self.dm.start_worker() 
            status_bar_var = self.app_context.get("status_bar_var")
            if status_bar_var: status_bar_var.set("Pokrećem preuzimanja iz reda...")
        else: logger.error("DownloadManager nije dostupan za pokretanje reda.")

    def _clear_finished_tasks(self): # Ostaje isto
        items_to_remove_from_dm = []; items_to_delete_from_treeview = []
        for item_id_str in list(self.treeview_item_map.keys()):
            task = self.treeview_item_map.get(item_id_str)
            if task and (task.status == "Završeno" or "Greška" in task.status or "Otkazano" in task.status):
                items_to_delete_from_treeview.append(item_id_str)
                if self.dm: items_to_remove_from_dm.append(item_id_str)
        for item_id_str in items_to_delete_from_treeview: self.remove_task_from_view(item_id_str)
        if self.dm:
            for item_id_str in items_to_remove_from_dm: self.dm.remove_task_completely(item_id_str)
        logger.info(f"Obrisano {len(items_to_delete_from_treeview)} završenih/neuspjelih/otkazanih zadataka.")
        if not self.queue_treeview.get_children():
             status_bar_var = self.app_context.get("status_bar_var")
             if status_bar_var: status_bar_var.set("Red čekanja je prazan.")

    def _cancel_selected_task(self): # Ostaje isto
         selected_items_iid = self.queue_treeview.selection()
         if not selected_items_iid:
             messagebox.showwarning("Nema odabira", "Molimo odaberite zadatak za otkazivanje.", parent=self.winfo_toplevel()); return
         task_item_id_str = selected_items_iid[0] 
         task_to_cancel = self.treeview_item_map.get(task_item_id_str)
         if task_to_cancel and self.dm:
             if task_to_cancel.status == "Preuzimanje..." or task_to_cancel.status == "U redu" or task_to_cancel.status == "Čeka" or task_to_cancel.status == "Priprema...":
                 if messagebox.askyesno("Potvrda Otkazivanja", f"Jeste li sigurni da želite otkazati preuzimanje za:\n{task_to_cancel.url}?", parent=self.winfo_toplevel()):
                     if self.dm.cancel_task(task_item_id_str): logger.info(f"Zahtjev za otkazivanje poslan za task ID: {task_item_id_str}")
                     else: logger.warning(f"Nije moguće otkazati task {task_item_id_str}."); task_to_cancel.status = "Greška otkazivanja"; self.update_task_in_view(task_to_cancel)
             else: messagebox.showinfo("Info", "Ovaj zadatak nije u stanju koje se može otkazati.", parent=self.winfo_toplevel())
         self.cancel_selected_btn.configure(state="disabled")

    def add_task_to_view(self, task: de.DownloadTask): # Ostaje isto
        item_id_str = str(task.item_id)
        if not self.winfo_exists(): return
        if not hasattr(self, 'queue_treeview') or not self.queue_treeview: self.after(100, lambda t=task: self.add_task_to_view(t)); return
        if item_id_str in self.treeview_item_map and self.queue_treeview.exists(item_id_str): self.update_task_in_view(task); return
        display_url = task.url; len_url = len(display_url)
        if len_url > 60: display_url = display_url[:28] + "..." + display_url[len_url-29:] # Skrati sredinu
        if not self.queue_treeview.exists(item_id_str):
             try:
                 self.queue_treeview.insert("", "end", iid=item_id_str, values=(display_url, task.quality_profile_key, task.status, task.progress_str, f"{task.speed_str} / {task.eta_str}"))
                 self.treeview_item_map[item_id_str] = task; logger.debug(f"Task dodan u QueueView: {item_id_str} ({task.status})")
             except tk.TclError as e_insert: logger.error(f"TclError pri insertu za iid {item_id_str}: {e_insert}. Pokušavam update."); self.update_task_in_view(task)
        else: self.update_task_in_view(task)

    def update_task_in_view(self, task: de.DownloadTask): # Ostaje isto
        item_id_str = str(task.item_id)
        if not self.winfo_exists(): return
        if not hasattr(self, 'queue_treeview') or not self.queue_treeview: self.after(100, lambda t=task: self.update_task_in_view(t)); return
        if not self.queue_treeview.exists(item_id_str): self.logger.warning(f"Pokušaj ažuriranja nepostojećeg itema {item_id_str}. Dodajem ga."); self.add_task_to_view(task); return
        
        display_name = os.path.basename(task.final_filename) if task.final_filename else task.url
        len_dn = len(display_name)
        if len_dn > 60: display_name = display_name[:28] + "..." + display_name[len_dn-29:]
        speed_eta_display = f"{task.speed_str} / {task.eta_str}" if task.speed_str or task.eta_str else "-"
        if task.status == "Preuzimanje..." and not task.speed_str and not task.eta_str and task.progress_val < 1: speed_eta_display = "Pokrećem..."
        try:
             self.queue_treeview.item(item_id_str, values=(display_name, task.quality_profile_key, task.status, task.progress_str, speed_eta_display))
             tags_to_apply = ()
             if task.status == "Završeno": tags_to_apply = ('COMPLETED',)
             elif "Greška" in task.status or task.status.startswith("Otkazano"): tags_to_apply = ('ERROR',)
             elif task.status == "Preuzimanje...": tags_to_apply = ('DOWNLOADING',)
             elif task.status == "U redu" or task.status == "Čeka": tags_to_apply = ('WAITING',)
             self.queue_treeview.item(item_id_str, tags=tags_to_apply)
             logger.debug(f"Task ažuriran u QueueView: {item_id_str}, Status: {task.status}, Progres: {task.progress_str}")
        except tk.TclError as e_update: logger.error(f"TclError pri ažuriranju itema {item_id_str}: {e_update}")
        if item_id_str in self.treeview_item_map: del self.treeview_item_map[item_id_str]

    def remove_task_from_view(self, task_item_id_str: str): # Ostaje isto
         if hasattr(self, 'queue_treeview') and self.queue_treeview and self.queue_treeview.exists(task_item_id_str):
             self.queue_treeview.delete(task_item_id_str)
         if task_item_id_str in self.treeview_item_map: del self.treeview_item_map[task_item_id_str]
         logger.info(f"Task {task_item_id_str} uklonjen iz QueueView.")

    def on_view_enter(self): # Ostaje isto
         super().on_view_enter()
         self.cancel_selected_btn.configure(state="disabled")
         if self.dm:
             all_dm_tasks = self.dm.get_all_tasks_snapshot()
             # Očisti trenutne iteme u treeview koji više ne postoje u DM-u
             current_tree_items = set(self.queue_treeview.get_children())
             dm_task_ids = {str(t.item_id) for t in all_dm_tasks}
             for item_id_str in current_tree_items - dm_task_ids: self.remove_task_from_view(item_id_str)
             # Dodaj/ažuriraj taskove iz DM-a
             for task in all_dm_tasks: self.add_task_to_view(task) # add_task_to_view će pozvati update ako već postoji
         logger.info(f"QueueView aktiviran. Prikazano {len(self.treeview_item_map)} zadataka.")
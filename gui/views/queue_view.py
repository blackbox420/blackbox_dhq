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
        self.treeview_item_map = {} 
        self.dm = app_context.get("download_manager")
        # _setup_logging_handler se poziva u build_ui nakon što je log_text_area kreiran
        super().__init__(master, "queue", app_context, **kwargs)

    def build_ui(self):
        self.grid_rowconfigure(1, weight=3)  # Treeview dobiva više prostora (red 1)
        self.grid_rowconfigure(3, weight=1)  # Log panel dobiva manje (red 3)
        self.grid_columnconfigure(0, weight=1)

        title_label = ctk.CTkLabel(self, text="Red Čekanja i Log Preuzimanja", 
                                   font=ctk.CTkFont(size=26, weight="bold"), anchor="w")
        title_label.grid(row=0, column=0, pady=(10,15), padx=20, sticky="ew")

        # --- Frame za Treeview i akcije iznad njega ---
        queue_actions_top_frame = ctk.CTkFrame(self, fg_color="transparent")
        queue_actions_top_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0,5))
        queue_actions_top_frame.grid_columnconfigure(0, weight=1) # Za Treeview kontejner
        queue_actions_top_frame.grid_rowconfigure(1, weight=1) # Treeview kontejner se širi

        # Gumbi za akcije nad cijelim redom (iznad Treeview-a)
        control_buttons_frame = ctk.CTkFrame(queue_actions_top_frame, fg_color="transparent")
        control_buttons_frame.grid(row=0, column=0, sticky="ew", pady=(0,5))
        
        self.start_all_btn = ctk.CTkButton(control_buttons_frame, text="Pokreni Sve", command=self._start_all_downloads, height=30)
        self.start_all_btn.pack(side="left", padx=5)

        self.clear_completed_btn = ctk.CTkButton(control_buttons_frame, text="Očisti Završene/Greške", command=self._clear_finished_tasks, height=30)
    def on_view_enter(self):
        super().on_view_enter()
        self.cancel_selected_btn.configure(state="disabled")
        self.logger.info("QueueView postao aktivan. Osvježavam prikaz reda.")
        
        # Obriši sve postojeće iteme da izbjegneš duplikate pri ponovnom ulasku
        for item in self.queue_treeview.get_children():
            self.queue_treeview.delete(item)
        self.treeview_item_map.clear() # Očisti i mapu

        if self.dm:
            all_dm_tasks = self.dm.get_all_tasks_snapshot()
            self.logger.debug(f"Dohvaćeno {len(all_dm_tasks)} zadataka iz DownloadManagera za prikaz.")
            # Sortiraj taskove, npr. po vremenu dodavanja ili statusu (ako želiš)
            # sorted_tasks = sorted(all_dm_tasks, key=lambda t: t.added_time, reverse=True) # Najnoviji na vrhu
            for task in all_dm_tasks: # Koristi originalni redoslijed za sada
                self.add_task_to_view(task) # Ponovno dodaj sve u Treeview
        else:
            self.logger.warning("DownloadManager nije dostupan u QueueView pri on_view_enter.")

    def _clear_finished_tasks(self):
        items_to_remove_from_dm = []
        items_to_delete_from_treeview = []

        for item_id_str in list(self.treeview_item_map.keys()): # Iteriraj preko kopije ključeva
            task = self.treeview_item_map.get(item_id_str)
            if task and (task.status == "Završeno" or "Greška" in task.status or "Otkazano" in task.status):
                items_to_delete_from_treeview.append(item_id_str)
                if self.dm: # Ako postoji DM, zabilježi za brisanje iz njega
                    items_to_remove_from_dm.append(item_id_str)
        
        for item_id_str in items_to_delete_from_treeview:
            self.remove_task_from_view(item_id_str) # Ukloni iz GUI-ja

        if self.dm:
            for item_id_str in items_to_remove_from_dm:
                self.dm.remove_task_completely(item_id_str) # Ukloni iz DM-a
        
        self.logger.info(f"Obrisano {len(items_to_delete_from_treeview)} završenih/neuspjelih/otkazanih zadataka.")
        if not self.queue_treeview.get_children(): # Ako je lista prazna
             status_bar_var = self.app_context.get("status_bar_var")
             if status_bar_var: status_bar_var.set("Red čekanja je prazan.")


    def _cancel_selected_task(self):
         selected_items_iid = self.queue_treeview.selection()
         if not selected_items_iid:
             messagebox.showwarning("Nema odabira", "Molimo odaberite zadatak za otkazivanje.", parent=self.winfo_toplevel())
             return
         
         task_item_id_str = selected_items_iid[0] 
         task_to_cancel = self.treeview_item_map.get(task_item_id_str)

         if task_to_cancel and self.dm:
             if task_to_cancel.status == "Preuzimanje..." or task_to_cancel.status == "U redu" or task_to_cancel.status == "Čeka":
                 if messagebox.askyesno("Potvrda Otkazivanja", f"Jeste li sigurni da želite otkazati preuzimanje za:\n{task_to_cancel.url}?", parent=self.winfo_toplevel()):
                     success = self.dm.cancel_task(task_item_id_str)
                     if success:
                         self.logger.info(f"Zahtjev za otkazivanje poslan za task ID: {task_item_id_str}")
                         # DownloadManager će poslati update_callback s novim statusom "Otkazano"
                         # Nema potrebe za _finalize_cancel_gui ako DM to radi
                     else:
                         self.logger.warning(f"Nije moguće otkazati task {task_item_id_str} (možda nije aktivan ili u redu).")
                         # Ažuriraj GUI svejedno ako DM nije uspio poslati update
                         task_to_cancel.status = "Greška otkazivanja" 
                         self.update_task_in_view(task_to_cancel)
             else:
                 messagebox.showinfo("Info", "Ovaj zadatak nije u stanju koje se može otkazati (npr. već je završen ili ima grešku).", parent=self.winfo_toplevel())
         self.cancel_selected_btn.configure(state="disabled")

    # add_task_to_view i update_task_in_view ostaju skoro isti,
    # samo osiguraj da koriste str(task.item_id) konzistentno kao iid.
    # I u update_task_in_view, provjeri da li task.item_id postoji u self.treeview_item_map prije nego što ga ažuriraš.

    def add_task_to_view(self, task: de.DownloadTask):
        item_id_str = str(task.item_id)
        if not self.winfo_exists(): return # Ako je view uništen

        if item_id_str in self.treeview_item_map and self.queue_treeview.exists(item_id_str):
            # Ako već postoji, samo ga ažuriraj (npr. status se promijenio brzo)
            self.update_task_in_view(task)
            return

        display_url = task.url
        if len(display_url) > 60: display_url = display_url[:57] + "..."
        
        # Provjeri da item_id ne postoji prije inserta (Treeview ne voli duple iid)
        if not self.queue_treeview.exists(item_id_str):
             try:
                 self.queue_treeview.insert("", "end", iid=item_id_str, values=(
                     display_url, task.quality_profile_key, task.status,
                     task.progress_str, f"{task.speed_str} / {task.eta_str}"
                 ))
                 self.treeview_item_map[item_id_str] = task # Spremi referencu na task
                 self.logger.debug(f"Task dodan u QueueView: {item_id_str} sa statusom {task.status}")
             except tk.TclError as e_insert: # Uhvati grešku ako iid već postoji
                 self.logger.error(f"TclError pri insertu u Treeview za iid {item_id_str}: {e_insert}. Pokušavam update.")
                 self.update_task_in_view(task) # Pokušaj update umjesto toga
        else: 
             self.update_task_in_view(task) # Ako već postoji, samo ažuriraj


    def update_task_in_view(self, task: de.DownloadTask):
        item_id_str = str(task.item_id)
        if not self.winfo_exists(): return

        if not self.queue_treeview.exists(item_id_str):
            # Ako item ne postoji, a trebao bi biti ažuriran, možda ga je DM tek dodao
            # ili je došlo do desinkronizacije. Pokušaj ga dodati.
            self.logger.warning(f"Pokušaj ažuriranja nepostojećeg itema {item_id_str} u QueueView. Dodajem ga.")
            self.add_task_to_view(task)
            return

        display_name = os.path.basename(task.final_filename) if task.final_filename else task.url
        if len(display_name) > 60: display_name = display_name[:57] + "..."
        
        speed_eta_display = f"{task.speed_str} / {task.eta_str}" if task.speed_str or task.eta_str else "-"
        if task.status == "Preuzimanje..." and not task.speed_str and not task.eta_str:
            speed_eta_display = "Pokrećem..."


        try:
             self.queue_treeview.item(item_id_str, values=(
                 display_name, task.quality_profile_key, task.status,
                 task.progress_str, speed_eta_display
             ))

             tags_to_apply = ()
             if task.status == "Završeno": tags_to_apply = ('COMPLETED',)
             elif "Greška" in task.status or "Otkazano" in task.status : tags_to_apply = ('ERROR',)
             elif task.status == "Preuzimanje...": tags_to_apply = ('DOWNLOADING',)
             elif task.status == "U redu" or task.status == "Čeka": tags_to_apply = ('WAITING',)
             self.queue_treeview.item(item_id_str, tags=tags_to_apply)
             self.logger.debug(f"Task ažuriran u QueueView: {item_id_str}, Status: {task.status}, Progres: {task.progress_str}")
        except tk.TclError as e_update: # Ako item ne postoji iz nekog razloga
             self.logger.error(f"TclError pri ažuriranju itema {item_id_str} u Treeview: {e_update}")
             # Možda ukloniti iz mape ako je Treeview item nasilno obrisan
             if item_id_str in self.treeview_item_map:
                 del self.treeview_item_map[item_id_str]

        

        self.cancel_selected_btn = ctk.CTkButton(control_buttons_frame, text="Otkaži Odabrano", command=self._cancel_selected_task, height=30, state="disabled")
        self.cancel_selected_btn.pack(side="left", padx=5)
        
        # Treeview kontejner
        tree_container = ctk.CTkFrame(queue_actions_top_frame, fg_color="transparent")
        tree_container.grid(row=1, column=0, sticky="nsew")
        tree_container.grid_columnconfigure(0, weight=1)
        tree_container.grid_rowconfigure(0, weight=1)

        style = ttk.Style()
        theme_colors_dict = self.app_context.get("theme_colors", {})
        appearance_mode = ctk.get_appearance_mode() # "Light" or "Dark"
        
        # Prilagodi boje na osnovu trenutnog CTk appearance moda
        bg_color = theme_colors_dict.get("BACKGROUND_CONTENT") if appearance_mode == "Dark" else "#EAEAEA" # Svjetlija za light
        text_color = theme_colors_dict.get("TEXT_PRIMARY") if appearance_mode == "Dark" else "#101010"
        selected_color = theme_colors_dict.get("LIST_ITEM_SELECTED_BG") if appearance_mode == "Dark" else "#C0E0FF"
        selected_text_color = theme_colors_dict.get("LIST_ITEM_SELECTED_FG_TEXT") if appearance_mode == "Dark" else "#000000"
        header_bg_color = theme_colors_dict.get("BACKGROUND_SECONDARY") if appearance_mode == "Dark" else "#DADADA"
        
        style.theme_use("default")
        style.configure("Custom.Treeview", background=bg_color, foreground=text_color, fieldbackground=bg_color, borderwidth=0, rowheight=28)
        style.map("Custom.Treeview", background=[('selected', selected_color)], foreground=[('selected', selected_text_color)])
        style.configure("Custom.Treeview.Heading", background=header_bg_color, foreground=text_color, relief="flat", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"))
        style.map("Custom.Treeview.Heading", relief=[('active','groove'),('pressed','sunken')])

        cols = ("filename", "quality", "status", "progress", "speed_eta")
        col_names = ("Zadatak", "Kvaliteta", "Status", "Napredak", "Brzina / ETA")
        col_widths = {"filename": 350, "quality": 180, "status": 120, "progress": 100, "speed_eta": 150}
        col_anchors = {"filename": "w", "quality": "w", "status": "w", "progress": "w", "speed_eta":"w"}

        self.queue_treeview = ttk.Treeview(tree_container, columns=cols, show="headings", style="Custom.Treeview", height=10) # Visina u broju redova
        for i, col_id in enumerate(cols):
            self.queue_treeview.heading(col_id, text=col_names[i], anchor=tk.W)
            self.queue_treeview.column(col_id, width=col_widths[col_id], minwidth=col_widths[col_id]//2, anchor=col_anchors[col_id], stretch=tk.YES if col_id=="filename" else tk.NO)
        
        tree_scrollbar_y = ctk.CTkScrollbar(tree_container, command=self.queue_treeview.yview)
        self.queue_treeview.configure(yscrollcommand=tree_scrollbar_y.set)
        self.queue_treeview.grid(row=0, column=0, sticky="nsew")
        tree_scrollbar_y.grid(row=0, column=1, sticky="ns")

        # Tagovi za stiliziranje redova
        self.queue_treeview.tag_configure('COMPLETED', background=theme_colors_dict.get("SUCCESS", "lightgreen"), foreground=theme_colors_dict.get("TEXT_PRIMARY_ON_SUCCESS", "black"))
        self.queue_treeview.tag_configure('ERROR', background=theme_colors_dict.get("ERROR", "pink"), foreground=theme_colors_dict.get("TEXT_PRIMARY_ON_ERROR", "black"))
        self.queue_treeview.tag_configure('DOWNLOADING', foreground=theme_colors_dict.get("ACCENT_PRIMARY", "blue"))
        self.queue_treeview.tag_configure('WAITING', foreground=theme_colors_dict.get("TEXT_SECONDARY", "gray"))


        # --- Log prozor ---
        log_main_frame = ctk.CTkFrame(self, fg_color="transparent")
        log_main_frame.grid(row=3, column=0, sticky="nsew", padx=5, pady=(5,0))
        log_main_frame.grid_rowconfigure(1, weight=1)
        log_main_frame.grid_columnconfigure(0, weight=1)

        log_label = ctk.CTkLabel(log_main_frame, text="Detaljni Logovi:", font=ctk.CTkFont(size=14, weight="bold"), anchor="w")
        log_label.grid(row=0, column=0, pady=(5,5), padx=10, sticky="ew")

        self.log_text_area = ctk.CTkTextbox(log_main_frame, wrap="word", state="disabled", height=120,
                                            border_width=1, 
                                            border_color=theme_colors_dict.get("BORDER_PRIMARY", "gray50"),
                                            font=ctk.CTkFont(family="Consolas", size=10))
        self.log_text_area.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0,5))
        
        self._setup_logging_handler()
        
        self.queue_treeview.bind("<<TreeviewSelect>>", self._on_treeview_select)

    def _setup_logging_handler(self):
         if hasattr(self, 'log_text_area') and self.log_text_area:
             text_handler = CTkTextboxHandler(self.log_text_area)
             # Koristi format koji ne uključuje ime loggera, jer je već jasno da je iz aplikacije
             formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s', datefmt='%H:%M:%S')
             text_handler.setFormatter(formatter)
             
             root_logger = logging.getLogger() 
             # Provjeri da li je handler već dodan da izbjegneš duple poruke
             # Ova provjera je malo kompleksnija jer ne želimo dodavati više istih handlera
             # Jednostavniji pristup je da se ovo pozove samo jednom pri inicijalizaciji pogleda
             # ili da se handler ukloni u on_view_leave pa ponovno doda u on_view_enter.
             # Za sada, pretpostavimo da se build_ui poziva samo jednom.
             
             # Ako želimo samo logove iz naše aplikacije, a ne npr. iz urllib3:
             # logger_to_attach_to = logging.getLogger("core") # Ili __main__ ako je app_phoenix.py logger
             # Ako želimo sve:
             logger_to_attach_to = root_logger

             # Ukloni stare handlere istog tipa za ovaj textbox, ako postoje
             for handler in list(logger_to_attach_to.handlers): # Iteriraj preko kopije liste
                 if isinstance(handler, CTkTextboxHandler) and handler.textbox_widget == self.log_text_area:
                     logger_to_attach_to.removeHandler(handler)
                     logger.debug("Uklonjen stari CTkTextboxHandler.")
             
             logger_to_attach_to.addHandler(text_handler)
             text_handler.setLevel(logging.INFO) # Prikazuj INFO i iznad u GUI logu
             logger.info("CTkTextboxHandler uspješno (ponovno) dodan na logger.")
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
            self.dm.start_worker() 
            status_bar_var = self.app_context.get("status_bar_var")
            if status_bar_var: status_bar_var.set("Pokrećem preuzimanja iz reda...")
        else:
            logger.error("DownloadManager nije dostupan za pokretanje reda.")


    def _clear_finished_tasks(self):
        items_to_delete = []
        for item_id_str in self.queue_treeview.get_children():
            task = self.treeview_item_map.get(item_id_str) # item_id je string
            if task and (task.status == "Završeno" or "Greška" in task.status or task.status == "Otkazano (korisnik)"):
                items_to_delete.append(item_id_str)
        
        for item_id_str in items_to_delete:
            self.remove_task_from_view(item_id_str)
        logger.info(f"Obrisano {len(items_to_delete)} završenih/neuspjelih/otkazanih zadataka iz prikaza.")


    def _cancel_selected_task(self):
         selected_items_iid = self.queue_treeview.selection()
         if not selected_items_iid:
             messagebox.showwarning("Nema odabira", "Molimo odaberite zadatak za otkazivanje.", parent=self.winfo_toplevel())
             return
         
         task_item_id_str = selected_items_iid[0] 
         task_to_cancel = self.treeview_item_map.get(task_item_id_str)

         if task_to_cancel and self.dm:
             if task_to_cancel.status == "Preuzimanje..." or task_to_cancel.status == "U redu" or task_to_cancel.status == "Čeka":
                 if messagebox.askyesno("Potvrda Otkazivanja", f"Jeste li sigurni da želite otkazati preuzimanje za:\n{task_to_cancel.url}?", parent=self.winfo_toplevel()):
                     logger.info(f"Zahtjev za otkazivanje taska ID: {task_item_id_str} (URL: {task_to_cancel.url}).")
                     # TODO: Implementirati self.dm.cancel_task(task_item_id_str)
                     # DownloadManager bi trebao zaustaviti yt-dlp proces i poslati update_callback
                     # s novim statusom "Otkazano". Za sada, samo mijenjamo status u GUI-ju.
                     task_to_cancel.status = "Otkazivanje..." # Privremeni status
                     self.update_task_in_view(task_to_cancel)
                     self.logger.warning("Funkcija otkazivanja u DownloadManageru još nije implementirana!")
                     # Privremeno rješenje dok se ne implementira u DM:
                     self.after(1000, lambda t=task_to_cancel: self._finalize_cancel_gui(t))
             else:
                 messagebox.showinfo("Info", "Ovaj zadatak nije u stanju koje se može otkazati.", parent=self.winfo_toplevel())
         self.cancel_selected_btn.configure(state="disabled")
         
    def _finalize_cancel_gui(self, task): # Privremena metoda
         task.status = "Otkazano (korisnik)"
         task.progress_str = "-"
         task.progress_val = 0.0
         task.speed_str = ""
         task.eta_str = ""
         self.update_task_in_view(task)


    def add_task_to_view(self, task: de.DownloadTask):
        item_id_str = str(task.item_id) # Osiguraj da je iid string
        if item_id_str in self.treeview_item_map:
            self.update_task_in_view(task)
            return

        display_url = task.url
        if len(display_url) > 60: display_url = display_url[:57] + "..."
        
        if not self.queue_treeview.exists(item_id_str):
             self.queue_treeview.insert("", "end", iid=item_id_str, values=(
                 display_url, task.quality_profile_key, task.status,
                 task.progress_str, f"{task.speed_str} / {task.eta_str}"
             ))
             self.treeview_item_map[item_id_str] = task
             self.logger.debug(f"Task dodan u QueueView: {item_id_str}")
        else: 
             self.update_task_in_view(task)

    def update_task_in_view(self, task: de.DownloadTask):
        item_id_str = str(task.item_id)
        if not self.queue_treeview.exists(item_id_str):
            self.logger.warning(f"Pokušaj ažuriranja nepostojećeg itema {item_id_str} u QueueView. Dodajem ga.")
            self.add_task_to_view(task)
            return

        display_name = os.path.basename(task.final_filename) if task.final_filename else task.url
        if len(display_name) > 60: display_name = display_name[:57] + "..."
        
        speed_eta_display = f"{task.speed_str} / {task.eta_str}" if task.speed_str or task.eta_str else "-"

        self.queue_treeview.item(item_id_str, values=(
            display_name, task.quality_profile_key, task.status,
            task.progress_str, speed_eta_display
        ))

        tags_to_apply = ()
        if task.status == "Završeno": tags_to_apply = ('COMPLETED',) # Velika slova za tagove
        elif "Greška" in task.status or "Otkazano" in task.status : tags_to_apply = ('ERROR',)
        elif task.status == "Preuzimanje...": tags_to_apply = ('DOWNLOADING',)
        elif task.status == "U redu" or task.status == "Čeka": tags_to_apply = ('WAITING',)
        self.queue_treeview.item(item_id_str, tags=tags_to_apply)
        self.logger.debug(f"Task ažuriran u QueueView: {item_id_str}, Status: {task.status}, Progres: {task.progress_str}")


    def remove_task_from_view(self, task_item_id_str: str):
         if self.queue_treeview.exists(task_item_id_str):
             self.queue_treeview.delete(task_item_id_str)
         if task_item_id_str in self.treeview_item_map:
             del self.treeview_item_map[task_item_id_str]
             self.logger.info(f"Task {task_item_id_str} uklonjen iz QueueView.")

    def on_view_enter(self):
         super().on_view_enter()
         self.cancel_selected_btn.configure(state="disabled")
         # Opcionalno: Osvježi cijeli red iz DownloadManagera ako čuva stanje svih taskova
         # if self.dm:
         #     all_dm_tasks = self.dm.get_all_tasks_snapshot() # Potrebna metoda u DM
         #     # Usporedi s self.treeview_item_map i ažuriraj/dodaj/obriši
         #     # Ovo je kompleksnije i zahtijeva da DM čuva kompletnu listu.
         #     # Za sada, novi taskovi se dodaju, a postojeći ažuriraju preko callbacka.
         logger.info("QueueView aktiviran.")
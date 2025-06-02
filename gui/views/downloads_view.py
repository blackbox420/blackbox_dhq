# gui/views/downloads_view.py
import customtkinter as ctk
from .base_view import BaseView # Koristimo osnovnu klasu
from core import downloader_engine as de # Za QUALITY_PROFILE_KEYS
from core import settings_handler as sh # Za default kvalitetu

class DownloadsView(BaseView):
    def __init__(self, master, app_context: dict, **kwargs):
        super().__init__(master, "downloads", app_context, **kwargs)
        # self.configure(fg_color="red") # Za testiranje vidljivosti

    def build_ui(self):
        # Naslov Pogleda (uzeto iz slike kao "Overview", ali ovdje je "Preuzimanja")
        title_frame = ctk.CTkFrame(self, fg_color="transparent")
        title_frame.pack(fill="x", padx=20, pady=(20,10))

        title_label = ctk.CTkLabel(title_frame, text="Novo Preuzimanje", 
                                   font=ctk.CTkFont(size=28, weight="bold"), 
                                   anchor="w")
        title_label.pack(side="left")

        # Ovdje će doći UI za unos URL-a, odabir kvalitete, dodavanje u red, itd.
        # Slično kao što je bilo u `_create_download_tab` u prethodnoj verziji `MainWindow`
        # ali sada kao dio ovog specifičnog pogleda.

        # URL unos sekcija
        url_input_frame = ctk.CTkFrame(self, fg_color="transparent") # Ili boja pozadine sadržaja
        url_input_frame.pack(fill="x", padx=20, pady=10) # Promijeni X u "x"
        url_input_frame.grid_columnconfigure(1, weight=1) # Ovo je za grid unutar url_input_frame, ne za pack

        ctk.CTkLabel(url_input_frame, text="URL Adresa:", anchor="w").grid(row=0, column=0, padx=(0,10), pady=10, sticky="w")
        self.url_entry = ctk.CTkEntry(url_input_frame, placeholder_text="https://...", height=35)
        self.url_entry.grid(row=0, column=1, padx=0, pady=10, sticky="ew")
        self.url_entry.bind("<Return>", lambda event: self._add_url_to_queue_action())
        self.url_entry.bind("<KeyRelease>", self._url_entry_changed_action)

        paste_button = ctk.CTkButton(url_input_frame, text="Zalijepi", width=100, height=35,
                                     command=self._paste_from_clipboard_action)
        paste_button.grid(row=0, column=2, padx=(10,0), pady=10)

        # Odabir kvalitete
        ctk.CTkLabel(url_input_frame, text="Profil Kvalitete:", anchor="w").grid(row=1, column=0, padx=(0,10), pady=10, sticky="w")
        self.quality_combobox = ctk.CTkComboBox(url_input_frame, values=de.QUALITY_PROFILE_KEYS, 
                                                state="readonly", height=35, width=250,
                                                command=self._quality_profile_selected) # Ako treba akcija na promjenu
        self.quality_combobox.set(sh.load_settings().get("default_quality", de.QUALITY_PROFILE_KEYS[0]))
        self.quality_combobox.grid(row=1, column=1, padx=0, pady=10, sticky="w")
        
        # Opis profila kvalitete
        self.quality_description_label = ctk.CTkLabel(url_input_frame, text="", anchor="w", wraplength=400, justify="left",
                                                       font=ctk.CTkFont(size=11), text_color="gray60")
        self.quality_description_label.grid(row=2, column=1, padx=0, pady=(0,10), sticky="w")
        self._update_quality_description() # Inicijalni opis

        # Gumb za dodavanje u red
        add_button = ctk.CTkButton(url_input_frame, text="Dodaj u Red", height=35, 
                                   command=self._add_url_to_queue_action)
                                   # fg_color=theme_colors.DarkThemeColors.ACCENT_PRIMARY) # Primjer boje
        add_button.grid(row=1, column=2, rowspan=2, padx=(10,0), pady=10, sticky="ns")


    def _quality_profile_selected(self, choice):
        """Poziva se kada se promijeni odabir u comboboxu za kvalitetu."""
        self._update_quality_description()

    def _update_quality_description(self):
        selected_profile_key = self.quality_combobox.get()
        profile_details = de.QUALITY_PROFILES.get(selected_profile_key)
        if profile_details and hasattr(self, 'quality_description_label'):
            self.quality_description_label.configure(text=profile_details.get("description", ""))
        elif hasattr(self, 'quality_description_label'):
            self.quality_description_label.configure(text="")


    def _url_entry_changed_action(self, event=None):
        current_url = self.url_entry.get().strip()
        if current_url:
            suggested_profile = de.determine_content_type_and_suggest_quality(current_url)
            if suggested_profile in de.QUALITY_PROFILE_KEYS:
                self.quality_combobox.set(suggested_profile)
                self._update_quality_description()
        elif hasattr(self, 'quality_combobox'): # Ako je polje prazno
             self.quality_combobox.set(sh.load_settings().get("default_quality", de.QUALITY_PROFILE_KEYS[0]))
             self._update_quality_description()

    def _paste_from_clipboard_action(self):
        try:
            clipboard_content = self.master.winfo_toplevel().clipboard_get() # Dohvati iz root prozora
            if clipboard_content:
                if clipboard_content.startswith("http://") or clipboard_content.startswith("https://"):
                    self.url_entry.delete(0, ctk.END)
                    self.url_entry.insert(0, clipboard_content)
                    self._url_entry_changed_action() 
                    # self.app_context.get("logger", print)("URL zalijepljen iz clipboarda.") # Primjer korištenja app_context
                else:
                     messagebox.showinfo("Clipboard Info", "Sadržaj clipboarda ne izgleda kao URL.", parent=self)
        except tk.TclError:
            messagebox.showinfo("Clipboard Info", "Clipboard je prazan ili ne sadrži tekst.", parent=self)


    def _add_url_to_queue_action(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("Nema URL-a", "Molimo unesite URL.", parent=self)
            return
        
        quality_key = self.quality_combobox.get()
        
        # Koristi app_context za pristup download_manageru i drugim dijelovima aplikacije
        download_manager = self.app_context.get("download_manager")
        settings = self.app_context.get("settings")
        main_window_select_tab_callback = self.app_context.get("main_window_select_tab_callback")


        if download_manager and settings:
            output_dir_val = settings.get("output_directory")
            
            # Za dodavanje u Treeview, trebat će nam referenca na njega ili callback
            # Za sada, samo logiramo i prosljeđujemo download_manageru
            # Kasnije će QueueView imati Treeview i metode za dodavanje.
            
            # Ovo je placeholder za ID itema u Treeview-u. Pravi ID će doći iz QueueView-a.
            placeholder_item_id = f"task_{hash(url)}" 
            
            task = de.DownloadTask(url, quality_key, output_dir_val, placeholder_item_id)
            download_manager.add_to_queue(task)
            
            self.url_entry.delete(0, ctk.END)
            logger.info(f"URL dodan u red: {url} (Kvaliteta: {quality_key})") # Logiraj
            # self.app_context.get("status_bar_update_callback", lambda msg:None)(f"URL dodan: {os.path.basename(url)}")

            # Automatski prebaci na tab "Red Čekanja" ako postoji callback
            if main_window_select_tab_callback:
                main_window_select_tab_callback("queue") # "queue" je ime view-a za red čekanja

        else:
            messagebox.showerror("Greška Aplikacije", "Download manager ili postavke nisu dostupni.", parent=self)

    def on_view_enter(self):
        logger.info("Ulazak u DownloadsView.")
        # Ovdje možeš osvježiti npr. default kvalitetu ako se promijenila u postavkama
        if hasattr(self, 'quality_combobox'):
            self.quality_combobox.set(sh.load_settings().get("default_quality", de.QUALITY_PROFILE_KEYS[0]))
            self._update_quality_description()
        # Automatsko lijepljenje ako je omogućeno i ako je prozor aktivan
        if sh.load_settings().get("auto_paste_clipboard", False) and self.winfo_ismapped(): # provjeri da li je view vidljiv
            self.after(100, self._paste_from_clipboard_action) # Malo odgodi da se UI iscrta
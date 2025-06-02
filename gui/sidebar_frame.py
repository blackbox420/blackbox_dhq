# gui/sidebar_frame.py
import customtkinter as ctk
from utils import icon_loader 
# from utils import theme_colors # Ne treba direktan import ako app_context prosljeđuje boje

class SidebarFrame(ctk.CTkFrame):
    def __init__(self, master, app_callbacks: dict, user_type: str, app_context: dict, **kwargs):
        # Dohvati fg_color iz kwargs ako je proslijeđen, inače koristi default iz teme
        # Ovo osigurava da se fg_color postavi samo jednom.
        self.app_context = app_context 
        self.theme_colors = self.app_context.get("theme_colors", {})

        # Ako fg_color nije specificiran pri kreiranju instance SidebarFrame,
        # onda koristi defaultnu boju iz theme_colors.
        # Ako JEST specificiran (kao što radiš u MainWindow), taj će se koristiti.
        final_fg_color = kwargs.pop("fg_color", self.theme_colors.get("SIDEBAR_BACKGROUND", "#292A3D")) 
        super().__init__(master, fg_color=final_fg_color, **kwargs)

        self.app_callbacks = app_callbacks
        self.user_type = user_type

        self.grid_rowconfigure(5, weight=1) 
        self.grid_columnconfigure(0, weight=1)

        # Logo / Naziv Aplikacije
        app_logo_label = ctk.CTkLabel(self, text="BlackBox DHQ\nPhoenix",
                                      font=ctk.CTkFont(size=22, weight="bold"),
                                      text_color=self.theme_colors.get("TEXT_ACCENT", "#A082F6"))
        app_logo_label.grid(row=0, column=0, padx=20, pady=(20, 25))

        button_common_config = {
            "corner_radius": 8,
            "height": 40,
            "border_spacing": 10,
            "text_color": self.theme_colors.get("SIDEBAR_TEXT", "#D0D0E0"),
            "fg_color": "transparent", 
            "hover_color": self.theme_colors.get("SIDEBAR_HOVER_BACKGROUND", "#3A3B5A"),
            "anchor": "w"
        }

        # Navigacijski gumbi
        self.dashboard_icon = icon_loader.load_icon("dashboard_icon")
        self.btn_dashboard = ctk.CTkButton(self, text="Dashboard", image=self.dashboard_icon, **button_common_config,
                                           command=lambda: self.app_callbacks.get("select_view", lambda name: None)("dashboard"))
        self.btn_dashboard.grid(row=1, column=0, padx=15, pady=8, sticky="ew")

        self.downloads_icon = icon_loader.load_icon("downloads_icon")
        self.btn_downloads = ctk.CTkButton(self, text="Preuzimanja", image=self.downloads_icon, **button_common_config,
                                           command=lambda: self.app_callbacks.get("select_view", lambda name: None)("downloads"))
        self.btn_downloads.grid(row=2, column=0, padx=15, pady=8, sticky="ew")

        self.queue_icon = icon_loader.load_icon("queue_icon")
        self.btn_queue = ctk.CTkButton(self, text="Red Čekanja", image=self.queue_icon, **button_common_config,
                                       command=lambda: self.app_callbacks.get("select_view", lambda name: None)("queue"))
        self.btn_queue.grid(row=3, column=0, padx=15, pady=8, sticky="ew")

        # Admin gumb (ako je super_admin)
        self.btn_admin_panel = None # Inicijaliziraj kao None
        if self.user_type == "super_admin":
            self.admin_icon = icon_loader.load_icon("admin_icon")
            self.btn_admin_panel = ctk.CTkButton(self, text="Admin Panel", image=self.admin_icon, 
                                                 **button_common_config,
                                                 command=lambda: self.app_callbacks.get("select_view", lambda name: None)("admin_panel"))
            self.btn_admin_panel.grid(row=4, column=0, padx=15, pady=8, sticky="ew")

        # Gumbi na dnu sidebar-a (red 6 i 7)
        self.settings_icon = icon_loader.load_icon("settings_icon")
        self.btn_settings = ctk.CTkButton(self, text="Postavke", image=self.settings_icon, **button_common_config,
                                          command=lambda: self.app_callbacks.get("select_view", lambda name: None)("settings"))
        self.btn_settings.grid(row=6, column=0, padx=15, pady=(10,8), sticky="sew") 

        self.license_icon = icon_loader.load_icon("license_icon")
        self.btn_license = ctk.CTkButton(self, text="Licenca Info", image=self.license_icon, **button_common_config,
                                          command=lambda: self.app_callbacks.get("select_view", lambda name: None)("license_info"))
        self.btn_license.grid(row=7, column=0, padx=15, pady=(0,20), sticky="sew")

        self.navigation_buttons = {
            "dashboard": self.btn_dashboard,
            "downloads": self.btn_downloads,
            "queue": self.btn_queue,
            "settings": self.btn_settings,
            "license_info": self.btn_license,
        }
        if self.btn_admin_panel: # Dodaj samo ako je kreiran
            self.navigation_buttons["admin_panel"] = self.btn_admin_panel

    # update_active_button metoda ostaje ista
    def update_active_button(self, active_view_name: str):
        for name, btn_widget in self.navigation_buttons.items():
            if btn_widget is None: continue 
            if name == active_view_name:
                btn_widget.configure(fg_color=self.theme_colors.get("SIDEBAR_ACTIVE_BACKGROUND", "#7A52F4"),
                                     text_color=self.theme_colors.get("SIDEBAR_ACTIVE_TEXT", "#FFFFFF"))
            else:
                btn_widget.configure(fg_color="transparent", 
                                     text_color=self.theme_colors.get("SIDEBAR_TEXT", "#D0D0E0"))
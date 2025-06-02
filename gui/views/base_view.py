# gui/views/base_view.py
import customtkinter as ctk
import logging

logger = logging.getLogger(__name__)

class BaseView(ctk.CTkFrame):
    def __init__(self, master, view_name:str, app_context: dict, **kwargs):
        # Dohvati fg_color iz kwargs ako je proslijeđen od strane potklase (npr. DownloadsView).
        # Ako nije proslijeđen, koristi defaultnu boju pozadine sadržaja iz teme,
        # ili 'transparent' kao krajnji fallback.
        default_bg = app_context.get("theme_colors", {}).get("BACKGROUND_CONTENT", "transparent")
        final_fg_color = kwargs.pop('fg_color', default_bg) # Uzmi fg_color iz kwargs, ako postoji, inače default

        super().__init__(master, fg_color=final_fg_color, **kwargs) # Proslijedi očišćene kwargs

        self.view_name = view_name
        self.app_context = app_context
        self.logger = logger 
        self.build_ui()

    def build_ui(self):
        pass 

    def on_view_enter(self):
        self.logger.debug(f"Ulazak u pogled: {self.view_name}")
        pass 

    def on_view_leave(self):
        self.logger.debug(f"Napuštanje pogleda: {self.view_name}")
        pass
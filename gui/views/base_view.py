# gui/views/base_view.py
import customtkinter as ctk
import logging

logger = logging.getLogger(__name__)

class BaseView(ctk.CTkFrame):
    def __init__(self, master, view_name: str, app_context: dict, **kwargs):
        # Dohvati theme_colors iz app_contexta
        theme_colors = app_context.get("theme_colors", {})
        # Odredi defaultnu pozadinsku boju za pogled
        default_bg = theme_colors.get("BACKGROUND_CONTENT", "transparent")
        
        # Uzmi fg_color iz kwargs ako je specificiran.
        # kwargs.pop() će uzeti vrijednost I UKLONITI 'fg_color' iz kwargs.
        final_fg_color = kwargs.pop('fg_color', default_bg) 

        super().__init__(master, fg_color=final_fg_color, **kwargs) # Koristi final_fg_color
        
        self.view_name = view_name
        self.app_context = app_context
        self.logger = logger 
        self.build_ui()

    def build_ui(self):
        """Potklase trebaju implementirati ovu metodu za kreiranje svog UI-ja."""
        # Za testiranje, čak i ako potklasa ne implementira build_ui, dodajmo labelu ovdje
        # da vidimo da li se BaseView uopće iscrtava s bojom.
        # Ako potklase imaju svoj build_ui, ova labela se neće vidjeti ako je prekriju.
        # Ako je potklasa samo placeholder CTkFrame, ova labela se također neće vidjeti
        # jer će taj CTkFrame (koji je BaseView) biti master za ovu labelu, ali sam
        # CTkFrame koji je placeholder neće imati ovu labelu.
        # Ovo je bolje staviti u build_ui placeholder pogleda.
        pass

    def on_view_enter(self):
        self.logger.debug(f"Ulazak u pogled: {self.view_name}")
        # Možeš privremeno dodati da pogled podigne sebe na vrh, iako grid_forget/grid bi to trebao raditi
        # self.lift() 
        pass

    def on_view_leave(self):
        self.logger.debug(f"Napuštanje pogleda: {self.view_name}")
        pass
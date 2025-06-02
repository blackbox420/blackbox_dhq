# gui/views/base_view.py
import customtkinter as ctk
import logging # Dodaj import za logging

logger = logging.getLogger(__name__) # Inicijaliziraj logger za ovaj modul

class BaseView(ctk.CTkFrame):
    def __init__(self, master, view_name: str, app_context: dict, **kwargs):
        # Dohvati theme_colors iz app_contexta
        theme_colors = app_context.get("theme_colors", {})
        # Odredi defaultnu pozadinsku boju za pogled
        default_bg = theme_colors.get("BACKGROUND_CONTENT", "transparent") # Boja pozadine za sadržaj
        
        # Uzmi fg_color iz kwargs ako je specificiran prilikom kreiranja instance BaseView (ili njegove potklase).
        # Ako nije, koristi default_bg.
        # kwargs.pop() će uzeti vrijednost I UKLONITI 'fg_color' iz kwargs rječnika,
        # tako da se ne proslijedi dvaput u super().__init__().
        final_fg_color = kwargs.pop('fg_color', default_bg) 

        super().__init__(master, fg_color=final_fg_color, **kwargs) # Koristi final_fg_color, proslijedi očišćene kwargs
        
        self.view_name = view_name
        self.app_context = app_context
        self.logger = logger # Koristi logger definiran u ovom modulu
        self.build_ui()

    def build_ui(self):
        """Potklase trebaju implementirati ovu metodu za kreiranje svog UI-ja."""
        # Možeš čak dodati placeholder labelu ovdje za debugiranje ako potklasa ne implementira build_ui
        # ctk.CTkLabel(self, text=f"Ovo je {self.view_name} (iz BaseView)", 
        #              font=ctk.CTkFont(size=12)).pack(padx=5, pady=5)
        pass

    def on_view_enter(self):
        """Poziva se kada ovaj pogled postane aktivan."""
        self.logger.debug(f"Ulazak u pogled: {self.view_name}")
        # Npr. za osvježavanje podataka
        pass

    def on_view_leave(self):
        """Poziva se kada se napušta ovaj pogled."""
        self.logger.debug(f"Napuštanje pogleda: {self.view_name}")
        pass
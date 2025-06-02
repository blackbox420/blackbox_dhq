# gui/views/base_view.py
import customtkinter as ctk
import logging

logger = logging.getLogger(__name__)

class BaseView(ctk.CTkFrame):
    def __init__(self, master, view_name: str, app_context: dict, **kwargs):
        theme_colors = app_context.get("theme_colors", {})
        default_bg = theme_colors.get("BACKGROUND_CONTENT", "transparent")
        
        final_fg_color = kwargs.pop('fg_color', default_bg) 
        self.logger = logger # Inicijaliziraj logger prije super().__init__ ako ga koristiš odmah
        self.logger.debug(f"BaseView '{view_name}' inicijaliziran s fg_color: {final_fg_color}")

        super().__init__(master, fg_color=final_fg_color, **kwargs)
        
        self.view_name = view_name
        self.app_context = app_context
        # self.logger je već postavljen
        self.build_ui()

    def build_ui(self):
        """Potklase trebaju implementirati ovu metodu za kreiranje svog UI-ja."""
        # Dodajemo vidljivu labelu u BaseView SAMO ako potklasa ne nadjača build_ui
        # Ovo će pomoći da vidimo da li se BaseView (i njegova pozadinska boja) uopće prikazuju.
        # Ako potklase imaju svoj build_ui, ova labela neće biti vidljiva osim ako je pozovu.
        # Bolje je da svaka potklasa (ili placeholder u MainWindow) ima svoj sadržaj.
        # Ovdje nećemo dodavati labelu, neka to rade potklase ili placeholderi.
        pass

    def on_view_enter(self):
        self.logger.debug(f"Ulazak u pogled: {self.view_name}. Dimenzije: {self.winfo_width()}x{self.winfo_height()}")
        self.lift() 
        pass

    def on_view_leave(self):
        self.logger.debug(f"Napuštanje pogleda: {self.view_name}")
        pass
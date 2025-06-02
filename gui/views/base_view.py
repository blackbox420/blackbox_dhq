# gui/views/base_view.py
import customtkinter as ctk

class BaseView(ctk.CTkFrame):
    def __init__(self, master, view_name:str, app_context: dict, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs) # Prozirna pozadina da se vidi pozadina main_view_frame
        self.view_name = view_name
        self.app_context = app_context # Rječnik s referencama na npr. download_manager, settings, itd.
        self.build_ui()

    def build_ui(self):
        """Potklase trebaju implementirati ovu metodu za kreiranje svog UI-ja."""
        # Primjer:
        # title_label = ctk.CTkLabel(self, text=f"Ovo je {self.view_name} pogled", font=ctk.CTkFont(size=24, weight="bold"))
        # title_label.pack(pady=20, padx=20, anchor="nw")
        pass

    def on_view_enter(self):
        """Poziva se kada ovaj pogled postane aktivan."""
        # Npr. za osvježavanje podataka
        pass

    def on_view_leave(self):
        """Poziva se kada se napušta ovaj pogled."""
        pass
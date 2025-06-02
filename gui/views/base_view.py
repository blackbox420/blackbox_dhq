# gui/views/base_view.py
import customtkinter as ctk
import logging

class BaseView(ctk.CTkFrame):
    def __init__(self, master, view_name:str, app_context: dict, **kwargs):
        # Explicitly set fg_color to "transparent"
        super().__init__(master, fg_color="transparent", **kwargs)
        self.view_name = view_name
        self.app_context = app_context
        self.logger = logging.getLogger(view_name) # logger defined here
        self.build_ui()

    def build_ui(self):
        """Subclasses should implement this method to create their UI."""
        pass # Each subclass (DownloadsView, QueueView, etc.) will define its own widgets here

    def on_view_enter(self):
        """Called when this view becomes active."""
        self.logger.debug(f"Entering view: {self.view_name}")
        # For example, to refresh data
        pass

    def on_view_leave(self):
        """Called when leaving this view."""
        self.logger.debug(f"Leaving view: {self.view_name}")
        pass
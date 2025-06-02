import customtkinter as ctk

class LicenseActivationWindow(ctk.CTkToplevel): # Koristi CTkToplevel za dodatne prozore
    def __init__(self, master, license_manager, activation_callback):
        super().__init__(master)
        self.license_manager = license_manager
        self.activation_callback = activation_callback # Funkcija koja se poziva nakon uspješne aktivacije

        self.title("Aktivacija Licence")
        self.geometry("400x250")
        self.transient(master)  # Postavi da bude iznad glavnog prozora
        self.grab_set()         # Onemogući interakciju s glavnim prozorom dok je ovaj otvoren (modalno ponašanje)
        #master.eval(f'tk::PlaceWindow {str(self)} center') # Centriraj u odnosu na master
        self.lift() # Podigni iznad mastera

        self.label = ctk.CTkLabel(self, text="Molimo unesite vaš licencni ključ:")
        self.label.pack(pady=10)

        self.license_key_entry = ctk.CTkEntry(self, width=300, placeholder_text="Licencni Ključ")
        self.license_key_entry.pack(pady=10)

        self.activate_button = ctk.CTkButton(self, text="Aktiviraj", command=self._attempt_activation)
        self.activate_button.pack(pady=10)

        self.status_label = ctk.CTkLabel(self, text="")
        self.status_label.pack(pady=10)
        
        self.protocol("WM_DELETE_WINDOW", self._on_close_attempt) # Što ako korisnik zatvori ovaj prozor?

    def _on_close_attempt(self):
        # Ako korisnik zatvori prozor za aktivaciju, a nema licence, aplikacija se ne može koristiti.
        # Ovdje bi trebala biti logika da se ili zatvori cijela aplikacija
        # ili da se ponudi ponovni pokušaj ili izlaz.
        if not self.license_manager.is_license_valid()[0]:
            self.master.destroy() # Zatvori glavnu aplikaciju ako se odustane od aktivacije
        else:
            self.destroy()


    def _attempt_activation(self):
        license_key = self.license_key_entry.get().strip()
        if not license_key:
            self.status_label.configure(text="Polje za ključ ne može biti prazno.", text_color="orange")
            return

        self.status_label.configure(text="Provjeravam licencu...", text_color="gray")
        # Ovdje bi išla komunikacija s license_manager.activate_license_online(license_key)
        # ili lokalna provjera ako je to implementirano.
        # Ovo je SIMULACIJA:
        # Pretpostavimo da activate_license vraća (True/False, license_info_dict)
        is_activated, license_info = self.license_manager.activate_license(license_key) # Ova metoda treba biti implementirana

        if is_activated:
            self.status_label.configure(text="Licenca uspješno aktivirana!", text_color="green")
            # Pozovi callback da obavijesti glavnu aplikaciju
            self.activation_callback(license_info)
            self.destroy() # Zatvori ovaj prozor
        else:
            error_msg = license_info.get("error", "Neispravan ili istekao licencni ključ.")
            self.status_label.configure(text=f"Greška: {error_msg}", text_color="red")
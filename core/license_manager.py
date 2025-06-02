# core/license_manager.py
import os
import json
import datetime
import hashlib
import platform
import uuid
import requests
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
import base64
import logging

logger = logging.getLogger(__name__)

# --- KONFIGURACIJA ---
LICENSE_SERVER_SIMULATOR_URL = "https://pastebin.com/raw/ndbdvnsV" # TVOJ ISPRAVAN RAW LINK

CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".blackbox_dhq_phoenix_v3")
LICENSE_FILE = os.path.join(CONFIG_DIR, "license_info.dat")
SALT_FILE = os.path.join(CONFIG_DIR, "app.salt")

class LicenseManager:
    def __init__(self):
        os.makedirs(CONFIG_DIR, exist_ok=True)
        self.hwid = self._get_hardware_id()
        self.fernet_key = self._get_or_create_fernet_key()
        if self.fernet_key:
            self.cipher_suite = Fernet(self.fernet_key)
        else:
            self.cipher_suite = None
            logger.critical("KRITIČNO: Cipher suite nije inicijaliziran! Enkripcija/dekripcija licence neće raditi.")

    def _get_hardware_id(self):
        try:
            data_sources = [
                platform.system(), platform.machine(), platform.processor(),
                str(uuid.getnode()),
            ]
            data_sources = [str(s) for s in data_sources if s is not None]
            combined_data = "-".join(data_sources)
            return hashlib.sha256(combined_data.encode('utf-8', 'ignore')).hexdigest()
        except Exception as e:
            logger.error(f"Greška pri dohvaćanju HWID: {e}")
            return str(uuid.uuid4())

    def _get_or_create_salt(self):
        if os.path.exists(SALT_FILE):
            with open(SALT_FILE, "rb") as f:
                return f.read()
        else:
            salt = os.urandom(16)
            with open(SALT_FILE, "wb") as f:
                f.write(salt)
            return salt

    def _get_or_create_fernet_key(self):
        try:
            salt = self._get_or_create_salt()
            app_pepper = b"BlackBoxPhoenixSecretPepper_v3!@#SecureDev" # Malo drugačiji za ovu verziju
            password = (self.hwid + app_pepper.decode()).encode('utf-8')
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(), length=32, salt=salt,
                iterations=100000, backend=default_backend()
            )
            key = base64.urlsafe_b64encode(kdf.derive(password))
            return key
        except Exception as e:
            logger.error(f"Greška pri generiranju Fernet ključa: {e}")
            return None

    def _save_license_local(self, license_data: dict):
        if not self.cipher_suite:
            logger.error("Cipher suite nije inicijaliziran, ne mogu spremiti licencu.")
            return False
        try:
            json_data = json.dumps(license_data).encode('utf-8')
            encrypted_data = self.cipher_suite.encrypt(json_data)
            with open(LICENSE_FILE, "wb") as f:
                f.write(encrypted_data)
            logger.info(f"Licenca spremljena lokalno za korisnika: {license_data.get('user', 'Nepoznat')}")
            return True
        except Exception as e:
            logger.error(f"Greška pri spremanju enkriptirane licence lokalno: {e}")
            return False

    def _load_license_local(self) -> dict | None:
        if not self.cipher_suite:
            logger.error("Cipher suite nije inicijaliziran, ne mogu učitati licencu.")
            return None
        if not os.path.exists(LICENSE_FILE):
            return None
        try:
            with open(LICENSE_FILE, "rb") as f:
                encrypted_data = f.read()
            decrypted_data = self.cipher_suite.decrypt(encrypted_data)
            license_data = json.loads(decrypted_data.decode('utf-8'))
            logger.info(f"Licenca uspješno učitana lokalno za: {license_data.get('user', 'Nepoznat')}")
            return license_data
        except InvalidToken:
            logger.error("Greška dekripcije lokalne licence: Invalid token. Brišem fajl.")
            try: os.remove(LICENSE_FILE)
            except OSError: pass
            return None
        except Exception as e:
            logger.error(f"Greška pri učitavanju/dekripciji lokalne licence: {e}")
            try: os.remove(LICENSE_FILE)
            except OSError: pass
            return None
       
    def _fetch_license_from_remote(self, license_key_to_find: str) -> dict | None:
        # Ova provjera osigurava da URL nije placeholder i da počinje ispravno.
        if LICENSE_SERVER_SIMULATOR_URL == "https://pastebin.com/raw/XXXXXXXX" or \
           not str(LICENSE_SERVER_SIMULATOR_URL).startswith("https://pastebin.com/raw/"):
            logger.error("PASTEBIN RAW URL NIJE ISPRAVNO POSTAVLJEN U license_manager.py!")
            return {"error": "Server za licence nije konfiguriran."}

        remote_data_content = None # Inicijalizacija prije try bloka

        try:
            logger.info(f"Dohvaćam licencu s: {LICENSE_SERVER_SIMULATOR_URL}")
            response = requests.get(LICENSE_SERVER_SIMULATOR_URL, timeout=15)
            
            logger.debug(f"Konačni URL nakon redirekcija: {response.url}")
            logger.debug(f"Statusni kod: {response.status_code}")
            content_type = response.headers.get('content-type', '').lower()
            logger.debug(f"Tip sadržaja: {content_type}")
            # Ispis dijela odgovora za debugiranje
            response_text_snippet = response.text[:1000] if response and hasattr(response, 'text') else "Nema tekstualnog odgovora"
            logger.debug(f"Odgovor (prvih 1000):\n{response_text_snippet}")

            response.raise_for_status() 

            if not ('text/plain' in content_type or 'application/json' in content_type):
                logger.error(f"Neočekivani tip sadržaja '{content_type}' s Pastebina. Očekivano text/plain ili application/json.")
                return {"error": f"Neočekivani tip sadržaja sa servera: {content_type}. Provjerite da li je RAW link ispravan."}

            remote_data_content = response.json() 
            
            if isinstance(remote_data_content, dict) and remote_data_content.get("license_key") == license_key_to_find:
                logger.info(f"Pronađena direktna licenca za ključ: {license_key_to_find}")
                return remote_data_content
            elif isinstance(remote_data_content, dict) and "licenses" in remote_data_content:
                for lic_info in remote_data_content.get("licenses", []):
                    if lic_info.get("key") == license_key_to_find:
                        logger.info(f"Licenca pronađena u listi na 'serveru' za ključ: {license_key_to_find}")
                        if lic_info.get("hwid_lock") and lic_info.get("hwid_lock") != self.hwid and lic_info.get("type") != "super_admin":
                            logger.warning(f"HWID se ne poklapa za licencu {license_key_to_find}.")
                            return {"error": "Licenca je vezana za drugi uređaj."}
                        return lic_info
                logger.warning(f"Licencni ključ {license_key_to_find} nije pronađen u listi licenci na 'serveru'.")
                return {"error": "Licencni ključ nije pronađen u listi."}
            else: 
                 logger.error(f"Format podataka s Pastebina nije prepoznat ili ključ nije nađen. Dobiveno: {remote_data_content}")
                 return {"error": "Neočekivani format podataka ili ključ nije pronađen."}

        except requests.exceptions.HTTPError as http_err:
            response_text_snippet_err = response.text[:500] if 'response' in locals() and response and hasattr(response, 'text') else 'Nema tekstualnog odgovora'
            logger.error(f"HTTP greška pri dohvaćanju licence: {http_err}. Odgovor: {response_text_snippet_err}")
            return {"error": f"HTTP greška: {http_err}."}
        except requests.exceptions.Timeout:
            logger.error("Timeout pri dohvaćanju licence s 'servera'.")
            return {"error": "Server za licence nije odgovorio na vrijeme."}
        except requests.exceptions.RequestException as e:
            logger.error(f"Mrežna greška pri dohvaćanju licence s 'servera': {e}")
            return {"error": f"Mrežna greška: {e}."}
        except json.JSONDecodeError as json_err:
            response_text_snippet_json_err = response.text[:100] if 'response' in locals() and response and hasattr(response, 'text') else 'Nema tekstualnog odgovora'
            logger.error(f"Greška pri parsiranju JSON odgovora s 'servera' (Pastebina): {json_err}. Sadržaj počinje s: {response_text_snippet_json_err}")
            return {"error": "Neispravan JSON format na serveru licenci. Provjerite da li RAW link vraća čist JSON."}
        except Exception as e:
            logger.error(f"Neočekivana greška pri dohvaćanju licence: {e}", exc_info=True)
            return {"error": f"Neočekivana greška: {e}."}

    def activate_license(self, license_key: str) -> tuple[bool, dict]:
        logger.info(f"Pokušaj aktivacije licence s ključem: {license_key}")
        
        remote_license_data = self._fetch_license_from_remote(license_key)

        if not remote_license_data or "error" in remote_license_data:
            error_msg = remote_license_data.get("error", "Nepoznata greška pri aktivaciji.") if remote_license_data else "Nije moguće dohvatiti licencu."
            logger.error(f"Aktivacija neuspješna: {error_msg}")
            return False, {"error": error_msg}
        
        # Provjera da li je licenca uspješno dohvaćena i da li je to traženi ključ
        if remote_license_data.get("license_key") != license_key:
            logger.error(f"Dohvaćena licenca s ključem '{remote_license_data.get('license_key')}' ne odgovara traženom ključu '{license_key}'.")
            return False, {"error": "Dohvaćeni podaci o licenci ne odgovaraju traženom ključu."}

        if remote_license_data.get("type") == "super_admin":
            logger.info("SuperAdmin licenca potvrđena od strane 'servera'.")
            remote_license_data["user"] = remote_license_data.get("user", "Haris (Super Admin)")
            remote_license_data["expires_at"] = "never"
            remote_license_data["hwid_lock"] = None # Admin licenca ne bi trebala biti vezana za HWID
            remote_license_data["status"] = "active" # Osiguraj da je status aktivan

        # Za obične korisnike, server bi trebao vratiti 'issued_at', 'expires_at', 'status', 'type', 'user'
        # i eventualno 'hwid_lock' ako je licenca vezana.
        # Za ovu simulaciju, pretpostavljamo da server vraća ispravne podatke.
        if "status" not in remote_license_data: # Osnovna provjera
            remote_license_data["status"] = "active" # Pretpostavi active ako nije specificirano

        if self._save_license_local(remote_license_data):
            logger.info(f"Licenca {license_key} uspješno aktivirana i spremljena.")
            return True, remote_license_data
        else:
            logger.error(f"Aktivacija neuspješna: Greška pri spremanju licence {license_key} lokalno.")
            return False, {"error": "Greška pri lokalnom spremanju licence."}

    def is_license_valid(self) -> tuple[bool, dict | None]:
        license_data = self._load_license_local()
        if not license_data:
            logger.info("Lokalna licenca nije pronađena ili je neispravna.")
            return False, None

        if license_data.get("status") != "active":
            logger.warning(f"Status lokalne licence nije 'active': {license_data.get('status')}")
            return False, license_data

        if license_data.get("type") != "super_admin" and \
           license_data.get("hwid_lock") and \
           license_data.get("hwid_lock") != self.hwid:
            logger.error(f"HWID se ne poklapa za licencu {license_data.get('license_key')}. Lokalni: {self.hwid}, Licenca: {license_data.get('hwid_lock')}.")
            return False, {"error": "Licenca je vezana za drugi uređaj.", **license_data}

        expires_at_str = license_data.get("expires_at")
        current_time_utc = datetime.datetime.now(datetime.timezone.utc)

        if expires_at_str == "never":
            logger.info(f"Doživotna licenca ({license_data.get('type')}) je aktivna.")
            return True, license_data
        
        if expires_at_str:
            try:
                expires_at_date = datetime.datetime.fromisoformat(str(expires_at_str).replace("Z", "+00:00"))
                if expires_at_date.tzinfo is None:
                    expires_at_date = expires_at_date.replace(tzinfo=datetime.timezone.utc)
                if expires_at_date > current_time_utc:
                    logger.info(f"Licenca validna do: {expires_at_date.strftime('%Y-%m-%d %H:%M:%S %Z')}")
                    return True, license_data
                else:
                    logger.info(f"Licenca istekla: {expires_at_date.strftime('%Y-%m-%d %H:%M:%S %Z')}")
                    license_data["status"] = "expired"
                    self._save_license_local(license_data)
                    return False, license_data
            except ValueError as e:
                logger.error(f"Greška pri parsiranju datuma isteka '{expires_at_str}': {e}")
                return False, {"error": "Neispravan format datuma isteka u licenci.", **license_data}

        logger.warning(f"Licenca ({license_data.get('license_key')}) nema validan status ili datum isteka.")
        return False, license_data

    def get_current_license_info(self) -> dict | None:
         return self._load_license_local()

    def clear_local_license(self):
        try:
            if os.path.exists(LICENSE_FILE):
                os.remove(LICENSE_FILE)
                logger.info("Lokalna licenca obrisana.")
                return True
        except Exception as e:
            logger.error(f"Greška pri brisanju lokalne licence: {e}")
        return False
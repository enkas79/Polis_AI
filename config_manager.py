import json
import os

class ConfigManager:
    """Classe responsabile della gestione e persistenza della configurazione locale."""
    CONFIG_FILE: str = "polis_ai_config.json"

    @classmethod
    def load_api_key(cls) -> str:
        """Carica la chiave API dal file di configurazione se esiste."""
        if os.path.exists(cls.CONFIG_FILE):
            try:
                with open(cls.CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("gemini_api_key", "")
            except Exception:
                return ""
        return ""

    @classmethod
    def save_api_key(cls, api_key: str) -> None:
        """Salva la chiave API nel file di configurazione."""
        try:
            with open(cls.CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump({"gemini_api_key": api_key}, f, indent=4)
        except Exception as e:
            print(f"Errore nel salvataggio della configurazione: {e}")
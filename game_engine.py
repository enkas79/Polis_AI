import datetime
import json
import re
import os
from typing import Optional, Dict, Any, List
from config_manager import ConfigManager

try:
    from google import genai

    GEMINI_AVAILABLE: bool = True
except ImportError:
    GEMINI_AVAILABLE: bool = False


class GameEngine:
    def __init__(self) -> None:
        self.api_key: str = ConfigManager.load_api_key()
        self.gemini_client: Optional[Any] = None
        self.game_state: Dict[str, Any] = {}
        self.scenario_context: str = ""
        self.preloaded_nations: Dict[str, Any] = {}
        self.current_scenario_filename: Optional[str] = None

        if not os.path.exists("scenarios"):
            os.makedirs("scenarios")

        self.reset_game()
        self._init_gemini()

    def _init_gemini(self) -> None:
        if self.api_key and GEMINI_AVAILABLE:
            try:
                self.gemini_client = genai.Client(api_key=self.api_key)
            except Exception as e:
                print(f"Errore inizializzazione GenAI: {e}")
                self.gemini_client = None

    def set_api_key(self, api_key: str) -> None:
        self.api_key = api_key
        ConfigManager.save_api_key(api_key)
        self._init_gemini()

    def _format_api_error(self, exception: Exception) -> str:
        """Ammortizzatore Globale per gli errori di Gemini (incluso il 429)"""
        error_msg = str(exception)
        if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
            return "⚠️ SERVER INTELLIGENCE SOVRACCARICHI ⚠️\nHai inviato troppe richieste in poco tempo al Comando Centrale di Google.\n\nPer favore, attendi circa 60 secondi prima di inviare un nuovo ordine o censire una nazione."
        return f"Errore di comunicazione con il Comando Centrale:\n{error_msg}"

    def get_available_scenarios(self) -> List[Dict[str, str]]:
        scenarios = []
        if os.path.exists("scenarios"):
            for filename in os.listdir("scenarios"):
                if filename.endswith(".json"):
                    try:
                        with open(os.path.join("scenarios", filename), "r", encoding="utf-8") as f:
                            data = json.load(f)
                            scenarios.append({
                                "filename": filename,
                                "name": data.get("name", "Scenario Sconosciuto"),
                                "year": data.get("start_year", 2024)
                            })
                    except Exception:
                        pass
        return scenarios

    def load_scenario(self, filename: str) -> None:
        filepath = os.path.join("scenarios", filename)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)

            self.current_scenario_filename = filename
            self.game_state["current_date"] = datetime.date(data.get("start_year", 2024), 1, 1)
            self.scenario_context = data.get("global_context", "")

            raw_nations = data.get("nations_data", {})
            self.preloaded_nations = {k.upper(): v for k, v in raw_nations.items()}

        except Exception as e:
            print(f"Errore caricamento scenario: {e}")

    def reset_game(self) -> None:
        self.game_state = {
            "current_date": datetime.date(2024, 1, 1),
            "selected_country": None,
            "history_log": [],
            "relations": {},
            "stats": {
                "stability": 60, "economy": 60, "reputation": 50,
                "treasury_billions": 0, "public_debt_billions": 0, "population_millions": 0.0
            },
            "game_over": False,
            "game_over_reason": ""
        }
        self.scenario_context = ""
        self.preloaded_nations = {}
        self.current_scenario_filename = None

    def set_country(self, country_name: str) -> bool:
        if self.game_state["selected_country"] is not None:
            return False
        self.game_state["selected_country"] = country_name
        self._calibrate_initial_stats()
        return True

    def _calibrate_initial_stats(self) -> None:
        country = self.game_state["selected_country"]

        if country.upper() in self.preloaded_nations:
            data = self.preloaded_nations[country.upper()]
            self.game_state["stats"]["treasury_billions"] = data.get("treasury_billions", 100)
            self.game_state["stats"]["public_debt_billions"] = data.get("public_debt_billions", 50)
            self.game_state["stats"]["population_millions"] = data.get("population_millions", 10.0)
            self.game_state["stats"]["stability"] = data.get("stability", 60)
            self.game_state["stats"]["economy"] = data.get("economy", 60)
            self.game_state["stats"]["reputation"] = data.get("reputation", 50)

            initial_rels = data.get("initial_relations", {})
            self.game_state["relations"] = {k.upper(): v for k, v in initial_rels.items()}
            return

        if not self.gemini_client: return
        year = self.game_state["current_date"].year

        prompt = (
            f"Fornisci stime per '{country}' nell'anno {year}.\n"
            f"Rispondi SOLO con:\n[INIT] TESORO:<int> | DEBITO:<int> | POP:<decimale>"
        )
        try:
            response = self.gemini_client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
            match = re.search(r'\[INIT\]\s*TESORO:\s*(-?[\d\.,]+)\s*\|\s*DEBITO:\s*([\d\.,]+)\s*\|\s*POP:\s*([\d\.,]+)',
                              response.text, re.IGNORECASE)
            if match:
                self.game_state["stats"]["treasury_billions"] = int(match.group(1).replace('.', '').replace(',', ''))
                self.game_state["stats"]["public_debt_billions"] = int(match.group(2).replace('.', '').replace(',', ''))
                self.game_state["stats"]["population_millions"] = float(match.group(3).replace(',', '.'))
            else:
                self._apply_fallback_stats()
        except Exception:
            self._apply_fallback_stats()

    def _apply_fallback_stats(self) -> None:
        self.game_state["stats"]["treasury_billions"] = 100
        self.game_state["stats"]["public_debt_billions"] = 50
        self.game_state["stats"]["population_millions"] = 10.0

    def get_current_country(self) -> Optional[str]:
        return self.game_state.get("selected_country")

    def get_current_date_str(self) -> str:
        return self.game_state["current_date"].strftime("%d %B %Y")

    def get_stats(self) -> Dict[str, Any]:
        return self.game_state["stats"]

    def get_history(self) -> list:
        return self.game_state["history_log"]

    def get_relations(self) -> Dict[str, int]:
        return self.game_state.get("relations", {})

    def is_game_over(self) -> bool:
        return self.game_state.get("game_over", False)

    def get_country_intel(self, target_country: str) -> Dict[str, Any]:
        target_upper = target_country.upper()
        relation = self.game_state.get("relations", {}).get(target_upper, 0)
        is_preloaded = target_upper in self.preloaded_nations

        data = self.preloaded_nations.get(target_upper, {})
        resources = data.get("resources", "Dati classificati (Nazione non censita nel database).")
        factions = data.get("factions", [])

        return {
            "relation": relation,
            "resources": resources,
            "factions": factions,
            "is_preloaded": is_preloaded,
            "is_player": target_country == self.game_state.get("selected_country")
        }

    def expand_scenario_with_ai(self, country_name: str) -> Dict[str, Any]:
        if not self.current_scenario_filename: return {"status": "error", "message": "Nessuno scenario caricato."}
        if not self.gemini_client: return {"status": "error", "message": "API Gemini non configurata."}

        year = self.game_state["current_date"].year
        prompt = (
            f"Agisci come database geopolitico. Censisci '{country_name}' nell'anno {year}.\n"
            f"Rispondi ESATTAMENTE con questo formato JSON:\n"
            f'{{"treasury_billions": 100, "public_debt_billions": 50, "population_millions": 10.5, "stability": 60, "economy": 60, "reputation": 50, "resources": "3 risorse con %", "factions": ["Alleanza1", "Alleanza2"]}}'
        )

        try:
            response = self.gemini_client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
            clean_json_str = response.text.replace('```json', '').replace('```', '').strip()
            new_data = json.loads(clean_json_str)

            filepath = os.path.join("scenarios", self.current_scenario_filename)
            with open(filepath, "r", encoding="utf-8") as f:
                scenario_data = json.load(f)
            if "nations_data" not in scenario_data: scenario_data["nations_data"] = {}
            scenario_data["nations_data"][country_name.title()] = new_data
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(scenario_data, f, indent=4)
            self.preloaded_nations[country_name.upper()] = new_data
            return {"status": "success", "message": f"{country_name} è stato censito!"}
        except Exception as e:
            # Usciamo con l'ammortizzatore se il censimento sbatte sul limite 429
            return {"status": "error", "message": self._format_api_error(e)}

    def save_game(self, filepath: str) -> None:
        try:
            state_to_save = self.game_state.copy()
            state_to_save["current_date"] = state_to_save["current_date"].isoformat()
            state_to_save["scenario_context"] = self.scenario_context
            state_to_save["preloaded_nations"] = self.preloaded_nations
            state_to_save["current_scenario_filename"] = self.current_scenario_filename
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(state_to_save, f, indent=4)
        except Exception as e:
            raise IOError(f"Impossibile salvare: {str(e)}")

    def load_game(self, filepath: str) -> None:
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                loaded_state = json.load(f)
            if "current_date" not in loaded_state: raise ValueError("Salvataggio corrotto.")
            loaded_state["current_date"] = datetime.date.fromisoformat(loaded_state["current_date"])

            if "stats" not in loaded_state:
                loaded_state["stats"] = {"stability": 60, "economy": 60, "reputation": 50, "treasury_billions": 100,
                                         "public_debt_billions": 50, "population_millions": 10.0}
            if "population_millions" not in loaded_state["stats"]: loaded_state["stats"]["population_millions"] = 10.0
            if "public_debt_billions" not in loaded_state["stats"]: loaded_state["stats"]["public_debt_billions"] = 50
            if "history_log" not in loaded_state: loaded_state["history_log"] = loaded_state.get("history", [])
            if "relations" not in loaded_state: loaded_state["relations"] = {}
            if "game_over" not in loaded_state: loaded_state["game_over"] = False

            self.scenario_context = loaded_state.get("scenario_context", "")
            self.preloaded_nations = loaded_state.get("preloaded_nations", {})
            self.current_scenario_filename = loaded_state.get("current_scenario_filename")
            self.game_state = loaded_state
        except json.JSONDecodeError:
            raise ValueError("File non valido.")
        except Exception as e:
            raise IOError(f"Impossibile caricare: {str(e)}")

    def _parse_and_update_engine_data(self, ai_response: str) -> str:
        stats_pattern = r'\[DATI\]\s*STAB:(\d+)\s*\|\s*ECO:(\d+)\s*\|\s*REP:(\d+)\s*\|\s*TESORO:(-?\d+)\s*\|\s*DEBITO:([\d\.,]+)\s*\|\s*POP:([\d\.,]+)'
        stats_match = re.search(stats_pattern, ai_response, re.IGNORECASE)
        if stats_match:
            try:
                self.game_state["stats"]["stability"] = max(0, min(100, int(stats_match.group(1))))
                self.game_state["stats"]["economy"] = max(0, min(100, int(stats_match.group(2))))
                self.game_state["stats"]["reputation"] = max(0, min(100, int(stats_match.group(3))))
                self.game_state["stats"]["treasury_billions"] = int(
                    stats_match.group(4).replace('.', '').replace(',', ''))
                self.game_state["stats"]["public_debt_billions"] = int(
                    stats_match.group(5).replace('.', '').replace(',', ''))
                self.game_state["stats"]["population_millions"] = float(stats_match.group(6).replace(',', '.'))
            except ValueError:
                pass
            ai_response = re.sub(stats_pattern, '', ai_response, flags=re.IGNORECASE)

        dip_pattern = r'\[DIPLOMAZIA\]\s*(.*)'
        dip_match = re.search(dip_pattern, ai_response, re.IGNORECASE)
        if dip_match:
            dip_str = dip_match.group(1).strip()
            if dip_str.upper() != "NESSUNA:0":
                pairs = dip_str.split('|')
                for pair in pairs:
                    if ':' in pair:
                        country_name, val = pair.split(':')
                        try:
                            val = int(val.strip())
                            current_val = self.game_state["relations"].get(country_name.strip().upper(), 0)
                            self.game_state["relations"][country_name.strip().upper()] = max(-100, min(100,
                                                                                                       current_val + val))
                        except ValueError:
                            pass
            ai_response = re.sub(dip_pattern, '', ai_response, flags=re.IGNORECASE)

        return ai_response.strip()

    def _check_game_over_conditions(self) -> Optional[str]:
        stats = self.game_state["stats"]
        if stats["stability"] <= 0:
            return "COLLASSO DELLO STATO: La stabilità è crollata a zero. Una rivoluzione armata ha rovesciato il tuo governo. Sei stato deposto."

        tesoro = stats["treasury_billions"]
        debito = stats["public_debt_billions"]
        safe_tesoro = max(1, tesoro)
        if debito > 1000 and debito > (safe_tesoro * 20):
            return "DEFAULT SOVRANO: Il debito pubblico è fuori controllo. I mercati internazionali si rifiutano di acquistare i tuoi titoli. Lo stato è in bancarotta."
        return None

    def trigger_game_over(self, reason: str) -> Dict[str, Any]:
        self.game_state["game_over"] = True
        self.game_state["game_over_reason"] = reason
        country = self.game_state["selected_country"]

        prompt = (
            f"Agisci come uno storico contemporaneo.\n"
            f"Il governo di '{country}' è appena caduto per questo motivo: '{reason}'.\n"
            f"Scrivi un drammatico e solenne resoconto finale che descrive la caduta del leader (il giocatore) e le conseguenze immediate sul paese e sul mondo.\n"
            f"Formattazione: Usa titoli drammatici e grassetti. Sii spietato ma epico."
        )
        try:
            response = self.gemini_client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
            return {"status": "game_over", "response": response.text, "new_date": self.get_current_date_str()}
        except Exception as e:
            # Usciamo con l'ammortizzatore se il game over sbatte sul limite 429
            return {"status": "game_over", "response": f"GAME OVER.\nMotivo: {reason}\n({self._format_api_error(e)})",
                    "new_date": self.get_current_date_str()}

    def process_action(self, action_internal: str, action_economy: str, action_diplomacy: str, time_jump_text: str) -> \
    Dict[str, Any]:
        if self.game_state.get("game_over"):
            return {"status": "error",
                    "message": "GAME OVER. Il tuo governo è caduto. Inizia una nuova partita dal menu."}

        if not GEMINI_AVAILABLE: return {"status": "error", "message": "google-genai non installato."}
        if not self.gemini_client: return {"status": "error", "message": "Nessuna API Key configurata."}

        country = self.game_state.get("selected_country")
        if not country: return {"status": "error", "message": "Nessuna nazione selezionata."}

        if time_jump_text == "1 Giorno":
            delta = datetime.timedelta(days=1)
        elif time_jump_text == "1 Settimana":
            delta = datetime.timedelta(weeks=1)
        elif time_jump_text == "1 Mese":
            delta = datetime.timedelta(days=30)
        else:
            delta = datetime.timedelta(days=1)

        old_date_str = self.get_current_date_str()
        self.game_state["current_date"] += delta
        new_date_str = self.get_current_date_str()

        player_data = self.preloaded_nations.get(country.upper(), {})
        player_factions = player_data.get("factions", [])
        faction_context = f"Appartiene a: {', '.join(player_factions)}." if player_factions else "Nazione non allineata."

        relations_list = [f"{k}({v})" for k, v in self.game_state["relations"].items() if v != 0]
        relations_context = "Relazioni diplomatiche: " + (
            ", ".join(relations_list) if relations_list else "Neutre con tutti.")

        if action_internal or action_economy or action_diplomacy:
            action_phrase = (
                f"Direttive di '{country}':\n"
                f"- Interno: {action_internal if action_internal else 'Nessuna.'}\n"
                f"- Economia: {action_economy if action_economy else 'Nessuna.'}\n"
                f"- Esteri/Difesa: {action_diplomacy if action_diplomacy else 'Nessuna.'}"
            )
            log_parts = []
            if action_internal: log_parts.append("Interni")
            if action_economy: log_parts.append("Economia")
            if action_diplomacy: log_parts.append("Esteri")
            log_entry = f"[{old_date_str}] Direttive per: {', '.join(log_parts)}"
        else:
            action_phrase = f"'{country}' non ha emanato direttive, limitandosi all'ordinaria amministrazione."
            log_entry = f"[{old_date_str}] Normale scorrere del tempo."

        curr_stats = self.game_state["stats"]
        stats_context = (
            f"Statistiche: Stabilità: {curr_stats['stability']}/100, Economia: {curr_stats['economy']}/100, "
            f"Reputazione: {curr_stats['reputation']}/100, Tesoro: {curr_stats['treasury_billions']} Mld $, "
            f"Debito Pubblico: {curr_stats['public_debt_billions']} Mld $, Popolazione: {curr_stats['population_millions']} Mln.")

        scenario_prompt = f"CONTESTO GLOBALE DELLO SCENARIO: {self.scenario_context}\n" if self.scenario_context else ""

        prompt = (
            f"Agisci come il Game Master del simulatore geopolitico 'Polis_AI'.\n"
            f"Data attuale: {new_date_str}. È trascorso: '{time_jump_text}'.\n"
            f"{scenario_prompt}"
            f"STATO DEL PAESE:\n- {stats_context}\n- {faction_context}\n- {relations_context}\n\n"
            f"{action_phrase}\n\n"
            f"REGOLE TASSATIVE PER LA RISPOSTA:\n"
            f"1. BREVITÀ E FORMATTAZIONE: Sii conciso. Usa paragrafi brevi e grassetti.\n"
            f"2. CONSEGUENZE GEOPOLITICHE: Reagisci alle azioni e usa le alleanze di appartenenza per calcolare le ripercussioni.\n"
            f"3. MONDO VIVO (Globale): Descrivi cosa è successo nel resto del mondo.\n\n"
            f"REGOLE PER CALCOLO DATI E DIPLOMAZIA (FONDAMENTALE):\n"
            f"Alla fine esatta della tua risposta, aggiungi QUESTE DUE RIGHE esatte:\n"
            f"[DATI] STAB:X | ECO:Y | REP:Z | TESORO:W | DEBITO:D | POP:V\n"
            f"[DIPLOMAZIA] NOME_PAESE:VARIAZIONE | ALTRO_PAESE:VARIAZIONE\n"
            f"(Sostituisci le lettere coi nuovi valori calcolati. W è tesoro in Mld $, D è debito in Mld $. V è popolazione usando il punto. Per DIPLOMAZIA: metti i nomi e variazione da -50 a +50. Se nessuna variazione scrivi [DIPLOMAZIA] NESSUNA:0)"
        )

        try:
            response = self.gemini_client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
            clean_text = self._parse_and_update_engine_data(response.text)
            self.game_state["history_log"].insert(0, log_entry)
            if len(self.game_state["history_log"]) > 15: self.game_state["history_log"].pop()

            game_over_reason = self._check_game_over_conditions()
            if game_over_reason:
                return self.trigger_game_over(game_over_reason)

            return {"status": "success", "response": clean_text, "new_date": new_date_str}

        except Exception as e:
            self.game_state["current_date"] -= delta
            # Usa il nuovo ammortizzatore globale!
            return {"status": "error", "message": self._format_api_error(e)}
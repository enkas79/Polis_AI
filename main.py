import sys
import os
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTextEdit, QLabel, QMessageBox, QFrame,
    QComboBox, QFileDialog, QGroupBox, QProgressBar, QListWidget, QListWidgetItem, QDialog
)
from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot, QTimer, QThread
from PyQt6.QtGui import QColor

# Previene lo schermo bianco su Linux
os.environ["QTWEBENGINE_DISABLE_HARDWARE_ACCELERATION"] = "1"

try:
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    from PyQt6.QtWebEngineCore import QWebEnginePage

    WEB_ENGINE_AVAILABLE: bool = True
except ImportError:
    WEB_ENGINE_AVAILABLE: bool = False


    class QWebEnginePage:
        pass

from game_engine import GameEngine
from map_manager import MapManager
from ui_components import ReportDialog, ApiDialog, ScenarioSelectionDialog, CountryIntelDialog, AdvancedStatsDialog
from ui_menu import setup_menu_bar
from auto_updater import AutoUpdater


# =========================================================
# CLASSI WORKER (MULTI-THREADING PER L'AI)
# =========================================================

class TurnWorker(QThread):
    finished_signal = pyqtSignal(dict)

    def __init__(self, engine, internal, economy, diplomacy, time_jump):
        super().__init__()
        self.engine = engine
        self.internal = internal
        self.economy = economy
        self.diplomacy = diplomacy
        self.time_jump = time_jump

    def run(self):
        result = self.engine.process_action(self.internal, self.economy, self.diplomacy, self.time_jump)
        self.finished_signal.emit(result)


class CensusWorker(QThread):
    finished_signal = pyqtSignal(dict)

    def __init__(self, engine, country_name):
        super().__init__()
        self.engine = engine
        self.country_name = country_name

    def run(self):
        result = self.engine.expand_scenario_with_ai(self.country_name)
        self.finished_signal.emit(result)


# =========================================================
# FINESTRA PRINCIPALE
# =========================================================

if WEB_ENGINE_AVAILABLE:
    class MapWebPage(QWebEnginePage):
        country_selected_signal = pyqtSignal(str)
        country_right_clicked_signal = pyqtSignal(str)

        def javaScriptConsoleMessage(self, level: int, message: str, lineNumber: int, sourceID: str) -> None:
            if message.startswith("COUNTRY_SELECTED:"):
                country_name = message.replace("COUNTRY_SELECTED:", "")
                self.country_selected_signal.emit(country_name)
            elif message.startswith("COUNTRY_RIGHT_CLICKED:"):
                country_name = message.replace("COUNTRY_RIGHT_CLICKED:", "")
                self.country_right_clicked_signal.emit(country_name)
            else:
                super().javaScriptConsoleMessage(level, message, lineNumber, sourceID)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.engine: GameEngine = GameEngine()
        self.init_ui()
        self._check_api_on_startup()
        self.update_ui_from_state()

        QTimer.singleShot(500, self.show_startup_scenario_dialog)
        QTimer.singleShot(2000, self.check_updates)

    def init_ui(self) -> None:
        current_version = AutoUpdater.get_local_version()
        self.setWindowTitle(f"Polis_AI - Geopolitical Simulator (v{current_version})")
        self.resize(1400, 900)
        self.setup_menu()

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Layout Radice (Contiene Top Bar e Contenuto Mappa/Sidebar)
        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # =========================================================
        # 1. TOP BAR (CRUSCOTTO NAZIONALE SUPERIORE)
        # =========================================================
        top_bar_frame = QFrame()
        top_bar_frame.setStyleSheet("background-color: #2c3e50; color: white;")
        top_bar_frame.setMinimumHeight(45)
        top_bar_frame.setMaximumHeight(45)

        top_layout = QHBoxLayout(top_bar_frame)
        top_layout.setContentsMargins(15, 0, 15, 0)

        # Valori Finanziari e Demografici
        self.lbl_treasury = QLabel("💰 Tesoro: --")
        self.lbl_treasury.setStyleSheet("color: #2ecc71; font-weight: bold; font-size: 13px;")
        top_layout.addWidget(self.lbl_treasury)

        self.lbl_debt = QLabel("📉 Debito: --")
        self.lbl_debt.setStyleSheet("color: #e74c3c; font-weight: bold; font-size: 13px;")
        top_layout.addWidget(self.lbl_debt)

        self.lbl_population = QLabel("👥 Pop: -- Mln")
        self.lbl_population.setStyleSheet("color: white; font-weight: bold; font-size: 13px;")
        top_layout.addWidget(self.lbl_population)

        top_layout.addSpacing(30)

        # Barre di Progresso
        lbl_stab = QLabel("👑 Stabilità:")
        lbl_stab.setStyleSheet("font-size: 12px; font-weight: bold;")
        top_layout.addWidget(lbl_stab)

        self.bar_stability = self.create_progress_bar("Stabilità Interna (Ordine pubblico, Consenso)", "#3498db")
        self.bar_stability.setFixedSize(120, 14)
        top_layout.addWidget(self.bar_stability)

        top_layout.addSpacing(15)

        lbl_eco = QLabel("📈 Economia:")
        lbl_eco.setStyleSheet("font-size: 12px; font-weight: bold;")
        top_layout.addWidget(lbl_eco)

        self.bar_economy = self.create_progress_bar("Salute Economica (PIL, Occupazione, Industria)", "#f1c40f")
        self.bar_economy.setFixedSize(120, 14)
        top_layout.addWidget(self.bar_economy)

        top_layout.addStretch()

        # Pulsante Statistiche Complete a destra
        self.btn_adv_stats = QPushButton("📊 Archivio di Stato")
        self.btn_adv_stats.setStyleSheet(
            "background-color: #ecf0f1; color: #2c3e50; font-weight: bold; padding: 4px 10px; border-radius: 3px;")
        self.btn_adv_stats.clicked.connect(self.show_advanced_stats)
        top_layout.addWidget(self.btn_adv_stats)

        root_layout.addWidget(top_bar_frame)

        # =========================================================
        # 2. CONTENUTO PRINCIPALE (Mappa a sx, Pannello a dx)
        # =========================================================
        content_widget = QWidget()
        main_layout = QHBoxLayout(content_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.addWidget(content_widget)

        # Mappa WebEngine
        if WEB_ENGINE_AVAILABLE:
            try:
                self.web_view = QWebEngineView()
                self.web_page = MapWebPage(self.web_view)
                self.web_page.country_selected_signal.connect(self.handle_country_selection)
                self.web_page.country_right_clicked_signal.connect(self.handle_country_right_click)
                self.web_view.setPage(self.web_page)
                self.web_view.setHtml(MapManager.get_map_html())
                main_layout.addWidget(self.web_view, stretch=7)
            except Exception as e:
                self.render_fallback_map(main_layout, f"Errore WebEngine: {e}")
        else:
            self.render_fallback_map(main_layout, "Modulo 'PyQt6-WebEngine' mancante.")

        # Pannello Laterale
        side_container = QWidget()
        side_container.setMaximumWidth(380)
        side_panel = QVBoxLayout(side_container)
        side_panel.setContentsMargins(15, 10, 15, 10)

        # Nazione e Data
        status_frame = QFrame()
        status_frame.setStyleSheet("background-color: #ecf0f1; border-radius: 6px; border: 1px solid #bdc3c7;")
        status_layout = QVBoxLayout(status_frame)
        status_layout.setContentsMargins(10, 8, 10, 8)

        self.lbl_active_country = QLabel("Nazione: <b>NESSUNA</b>")
        self.lbl_active_country.setStyleSheet("font-size: 15px; color: #c0392b;")
        self.lbl_active_country.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.lbl_date = QLabel(f"Data Corrente: <b>{self.engine.get_current_date_str()}</b>")
        self.lbl_date.setStyleSheet("font-size: 14px; color: #2c3e50; margin-top: 2px;")
        self.lbl_date.setAlignment(Qt.AlignmentFlag.AlignCenter)

        status_layout.addWidget(self.lbl_active_country)
        status_layout.addWidget(self.lbl_date)
        side_panel.addWidget(status_frame)

        # Banner Game Over
        self.lbl_game_over = QLabel("<b>IL TUO GOVERNO È CADUTO</b>")
        self.lbl_game_over.setStyleSheet(
            "background-color: #c0392b; color: white; padding: 10px; font-size: 16px; border-radius: 5px;")
        self.lbl_game_over.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_game_over.setVisible(False)
        side_panel.addWidget(self.lbl_game_over)

        # ---------------------------------------------------------
        # Direttive Ministeriali con TOOLTIPS
        # ---------------------------------------------------------
        side_panel.addSpacing(10)

        # Helper function per creare label con punto di domanda
        def create_help_label(testo: str, tooltip_html: str) -> QLabel:
            lbl = QLabel(f"<b>{testo}</b> <span style='color:#2980b9; cursor:help;'>(?)</span>")
            lbl.setToolTip(f"<div style='font-size: 12px; padding: 3px;'>{tooltip_html}</div>")
            return lbl

        lbl_int = create_help_label(
            "Politica Interna",
            "<b>Cosa scrivere qui:</b><br>• Riforme della Giustizia e Polizia<br>• Sanità e Istruzione<br>• Diritti civili e Costituzione<br>• Gestione proteste e scioperi"
        )
        side_panel.addWidget(lbl_int)
        self.input_internal = QTextEdit()
        self.input_internal.setStyleSheet(
            "font-size: 13px; padding: 4px; border: 1px solid #95a5a6; border-radius: 4px;")
        self.input_internal.setMinimumHeight(65)
        self.input_internal.setMaximumHeight(85)
        side_panel.addWidget(self.input_internal)

        lbl_eco = create_help_label(
            "Economia e Finanze",
            "<b>Cosa scrivere qui:</b><br>• Tasse (Aumento/Taglio)<br>• Sussidi alle aziende<br>• Grandi opere e Infrastrutture<br>• Accordi commerciali (Import/Export)<br>• Nazionalizzazioni/Privatizzazioni"
        )
        side_panel.addWidget(lbl_eco)
        self.input_economy = QTextEdit()
        self.input_economy.setStyleSheet(
            "font-size: 13px; padding: 4px; border: 1px solid #95a5a6; border-radius: 4px;")
        self.input_economy.setMinimumHeight(65)
        self.input_economy.setMaximumHeight(85)
        side_panel.addWidget(self.input_economy)

        lbl_dip = create_help_label(
            "Difesa ed Esteri",
            "<b>Cosa scrivere qui:</b><br>• Spostamento o reclutamento Truppe<br>• Proposte di Alleanza<br>• Dichiarazioni di Guerra<br>• Spionaggio ed Embarghi<br>• Aiuti militari ad altre nazioni"
        )
        side_panel.addWidget(lbl_dip)
        self.input_diplomacy = QTextEdit()
        self.input_diplomacy.setStyleSheet(
            "font-size: 13px; padding: 4px; border: 1px solid #95a5a6; border-radius: 4px;")
        self.input_diplomacy.setMinimumHeight(65)
        self.input_diplomacy.setMaximumHeight(85)
        side_panel.addWidget(self.input_diplomacy)

        # Avanzamento e Esecuzione
        action_bar_layout = QHBoxLayout()
        self.combo_time = QComboBox()
        self.combo_time.addItems(["1 Giorno", "1 Settimana", "1 Mese"])
        self.combo_time.setStyleSheet("font-size: 13px; padding: 3px;")
        action_bar_layout.addWidget(self.combo_time)

        self.btn_send = QPushButton("Esegui Turno")
        self.btn_send.setMinimumHeight(38)
        self.btn_send.setStyleSheet(
            "font-weight: bold; font-size: 14px; background-color: #27ae60; color: white; border-radius: 4px;")
        self.btn_send.clicked.connect(self.handle_action)
        action_bar_layout.addWidget(self.btn_send, stretch=1)
        side_panel.addLayout(action_bar_layout)
        side_panel.addSpacing(10)

        # Relazioni Estere (Ora ha più spazio!)
        diplomacy_group = QGroupBox("Relazioni Estere e Alleanze")
        diplomacy_group.setStyleSheet("font-weight: bold; font-size: 12px;")
        diplomacy_layout = QVBoxLayout()
        diplomacy_layout.setContentsMargins(5, 5, 5, 5)

        self.list_diplomacy = QListWidget()
        self.list_diplomacy.setStyleSheet(
            "font-weight: normal; font-size: 11px; background-color: #fdfdfd; border: 1px solid #dcdde1;")
        self.list_diplomacy.setMinimumHeight(80)
        diplomacy_layout.addWidget(self.list_diplomacy)
        diplomacy_group.setLayout(diplomacy_layout)
        side_panel.addWidget(diplomacy_group, stretch=1)

        # Cronologia Eventi (Ora ha più spazio!)
        history_group = QGroupBox("Archivio Storico (Doppio clic per leggere)")
        history_group.setStyleSheet("font-weight: bold; font-size: 12px;")
        history_layout = QVBoxLayout()
        history_layout.setContentsMargins(5, 5, 5, 5)

        self.list_history = QListWidget()
        self.list_history.setStyleSheet(
            "font-weight: normal; font-size: 11px; background-color: #fdfdfd; border: 1px solid #dcdde1;")
        self.list_history.setMinimumHeight(100)
        self.list_history.itemDoubleClicked.connect(self.handle_history_click)
        history_layout.addWidget(self.list_history)
        history_group.setLayout(history_layout)
        side_panel.addWidget(history_group, stretch=2)

        # Barra di caricamento asincrona
        self.loading_layout = QVBoxLayout()
        self.lbl_loading = QLabel("Ricezione dispacci in corso...")
        self.lbl_loading.setStyleSheet("color: #2980b9; font-weight: bold; font-size: 12px; font-style: italic;")
        self.lbl_loading.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.progress_loading = QProgressBar()
        self.progress_loading.setRange(0, 0)
        self.progress_loading.setFixedHeight(10)
        self.loading_layout.addWidget(self.lbl_loading)
        self.loading_layout.addWidget(self.progress_loading)
        self.lbl_loading.setVisible(False)
        self.progress_loading.setVisible(False)
        side_panel.addLayout(self.loading_layout)

        # Tasto Uscita
        self.btn_exit = QPushButton("Esci dal Gioco")
        self.btn_exit.setMinimumHeight(35)
        self.btn_exit.setStyleSheet("background-color: #c0392b; color: white; font-weight: bold; border-radius: 4px;")
        self.btn_exit.clicked.connect(self.close)
        side_panel.addWidget(self.btn_exit)

        main_layout.addWidget(side_container)

    def create_progress_bar(self, tooltip: str, color_hex: str) -> QProgressBar:
        bar = QProgressBar()
        bar.setRange(0, 100)
        bar.setValue(50)
        bar.setTextVisible(False)
        bar.setToolTip(tooltip)
        bar.setStyleSheet(f"""
            QProgressBar {{ border: 1px solid #7f8c8d; border-radius: 3px; background-color: #34495e; }}
            QProgressBar::chunk {{ background-color: {color_hex}; border-radius: 2px; }}
        """)
        return bar

    def setup_menu(self) -> None:
        setup_menu_bar(self)

    @pyqtSlot()
    def check_updates(self) -> None:
        AutoUpdater.check_for_updates(self)

    def _check_api_on_startup(self) -> None:
        if not self.engine.api_key:
            QMessageBox.warning(self, "API Mancante", "API Key Gemini non trovata. Inseriscila dal menu Impostazioni.")

    def show_api_dialog(self) -> None:
        dialog = ApiDialog(current_key=self.engine.api_key, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.new_key is not None:
            self.engine.set_api_key(dialog.new_key)
            QMessageBox.information(self, "Successo", "API Key aggiornata e salvata con successo!")

    @pyqtSlot()
    def show_startup_scenario_dialog(self) -> None:
        scenarios = self.engine.get_available_scenarios()
        dialog = ScenarioSelectionDialog(scenarios, self)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.selected_filename:
            try:
                self.engine.load_scenario(dialog.selected_filename)
                self.update_ui_from_state()
                if WEB_ENGINE_AVAILABLE:
                    self.web_view.page().runJavaScript("window.unlockCountryUI();")
            except Exception as e:
                QMessageBox.critical(self, "Errore", f"Impossibile caricare lo scenario: {str(e)}")

    @pyqtSlot()
    def start_new_game_dialog(self) -> None:
        reply = QMessageBox.question(
            self, 'Nuova Partita',
            "Sei sicuro di voler iniziare una nuova partita?\nTutti i progressi andranno persi.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.engine.reset_game()
            self.input_internal.clear()
            self.input_economy.clear()
            self.input_diplomacy.clear()
            self.update_ui_from_state()
            self.show_startup_scenario_dialog()

    def save_game_dialog(self) -> None:
        if not self.engine.get_current_country():
            QMessageBox.warning(self, "Attenzione", "Nessuna nazione selezionata.")
            return
        filepath, _ = QFileDialog.getSaveFileName(self, "Salva Partita", "saves", "Polis_AI Save Files (*.json)")
        if filepath:
            if not filepath.endswith('.json'): filepath += '.json'
            try:
                self.engine.save_game(filepath)
                QMessageBox.information(self, "Salvataggio Compiuto", "La partita è stata salvata.")
            except Exception as e:
                QMessageBox.critical(self, "Errore di Salvataggio", str(e))

    def load_game_dialog(self) -> None:
        filepath, _ = QFileDialog.getOpenFileName(self, "Carica Partita", "saves", "Polis_AI Save Files (*.json)")
        if filepath:
            try:
                self.engine.load_game(filepath)
                self.update_ui_from_state()
                QMessageBox.information(self, "Caricamento Compiuto", "Partita ripristinata con successo.")
            except Exception as e:
                QMessageBox.critical(self, "Errore di Caricamento", str(e))

    def update_ui_from_state(self) -> None:
        country = self.engine.get_current_country()
        is_game_over = self.engine.is_game_over()

        self.lbl_game_over.setVisible(is_game_over)
        self.btn_send.setEnabled(not is_game_over)
        self.input_internal.setEnabled(not is_game_over)
        self.input_economy.setEnabled(not is_game_over)
        self.input_diplomacy.setEnabled(not is_game_over)

        if is_game_over:
            self.lbl_active_country.setText(f"Nazione: <b>DEPOSTO</b>")
            return

        if country:
            self.lbl_active_country.setText(f"Nazione: <b>{country.upper()}</b> 🔒")
            self.lbl_active_country.setStyleSheet("font-size: 15px; color: #8e44ad;")
            if WEB_ENGINE_AVAILABLE:
                self.web_view.page().runJavaScript(f"window.lockCountryUI('{country}');")
        else:
            self.lbl_active_country.setText("Nazione: <b>NESSUNA</b>")
            self.lbl_active_country.setStyleSheet("font-size: 15px; color: #c0392b;")

        self.lbl_date.setText(f"Data Corrente: <b>{self.engine.get_current_date_str()}</b>")

        # AGGIORNAMENTO TOP BAR
        stats = self.engine.get_stats()
        self.bar_stability.setValue(stats["stability"])
        self.bar_economy.setValue(stats["economy"])

        treasury = stats.get("treasury_billions", 0)
        t_color = "#2ecc71" if treasury >= 0 else "#e74c3c"
        self.lbl_treasury.setText(f"💰 Tesoro: <span style='color:{t_color};'>$ {treasury} Mld</span>")

        debt = stats.get("public_debt_billions", 0)
        self.lbl_debt.setText(f"📉 Debito: <span style='color:#e74c3c;'>$ {debt} Mld</span>")

        pop = stats.get("population_millions", 0.0)
        self.lbl_population.setText(f"👥 Popolazione: {pop} Mln")

        # STORIA E DIPLOMAZIA
        self.list_history.clear()
        for item in self.engine.get_history():
            if isinstance(item, str):
                self.list_history.addItem(item)
            else:
                list_item = QListWidgetItem(item["summary"])
                list_item.setData(Qt.ItemDataRole.UserRole, item)
                self.list_history.addItem(list_item)

        self.list_diplomacy.clear()
        if country:
            player_data = self.engine.preloaded_nations.get(country.upper(), {})
            factions = player_data.get("factions", [])
            if factions:
                fac_item = QListWidgetItem(f"★ Organizzazioni: {', '.join(factions)}")
                fac_item.setForeground(QColor("#2980b9"))
                self.list_diplomacy.addItem(fac_item)

        relations = self.engine.get_relations()
        if not relations or all(v == 0 for v in relations.values()):
            if self.list_diplomacy.count() == 0:
                self.list_diplomacy.addItem("Nessun legame diplomatico.")
        else:
            sorted_rel = sorted(relations.items(), key=lambda item: item[1], reverse=True)
            for c_name, val in sorted_rel:
                if val == 0: continue
                status = "Alleato" if val >= 50 else "Amichevole" if val > 10 else "Ostilità" if val <= -50 else "Tensioni" if val < -10 else "Neutrale"
                item = QListWidgetItem(f"{c_name.capitalize()}: {val} [{status}]")
                if val > 10:
                    item.setForeground(QColor("#27ae60"))
                elif val < -10:
                    item.setForeground(QColor("#c0392b"))
                else:
                    item.setForeground(QColor("#34495e"))
                self.list_diplomacy.addItem(item)

    def handle_country_selection(self, country_name: str) -> None:
        current_country = self.engine.get_current_country()
        if current_country == country_name: return
        if current_country is not None:
            QMessageBox.warning(self, "Nazione Bloccata", f"Stai già guidando: {current_country}.")
            return

        reply = QMessageBox.question(
            self, 'Conferma Nazione',
            f"Vuoi assumere la leadership di: {country_name}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            success = self.engine.set_country(country_name)
            QApplication.restoreOverrideCursor()
            if success:
                self.update_ui_from_state()

    @pyqtSlot(str)
    def handle_country_right_click(self, country_name: str) -> None:
        intel_data = self.engine.get_country_intel(country_name)
        dialog = CountryIntelDialog(country_name, intel_data, self)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            if dialog.selected_action:
                if dialog.selected_action == "[CENSISCI]":
                    self.lbl_loading.setText(f"Censimento di {country_name} in corso...")
                    self.lbl_loading.setVisible(True)
                    self.progress_loading.setVisible(True)
                    self.btn_send.setEnabled(False)

                    self.census_worker = CensusWorker(self.engine, country_name)
                    self.census_worker.finished_signal.connect(self.on_census_finished)
                    self.census_worker.start()
                    return

                if not self.engine.get_current_country():
                    QMessageBox.warning(self, "Attenzione",
                                        "Seleziona prima la tua nazione con il tasto SINISTRO per poter inviare direttive!")
                    return
                self.input_diplomacy.setText(dialog.selected_action)

    def render_fallback_map(self, layout: QHBoxLayout, message: str) -> None:
        error_frame = QFrame()
        error_frame.setStyleSheet("background-color: #ecf0f1; border: 2px solid #bdc3c7;")
        error_layout = QVBoxLayout(error_frame)
        error_label = QLabel(message)
        error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        error_layout.addWidget(error_label)
        layout.addWidget(error_frame, stretch=7)

    @pyqtSlot(dict)
    def on_census_finished(self, result: dict) -> None:
        self.lbl_loading.setVisible(False)
        self.progress_loading.setVisible(False)
        self.btn_send.setEnabled(True)

        if result["status"] == "success":
            QMessageBox.information(self, "Censimento Completato", result["message"])
        else:
            QMessageBox.warning(self, "Errore", result["message"])

    def handle_action(self) -> None:
        internal_text: str = self.input_internal.toPlainText().strip()
        economy_text: str = self.input_economy.toPlainText().strip()
        diplomacy_text: str = self.input_diplomacy.toPlainText().strip()
        time_jump_text: str = self.combo_time.currentText()

        if not self.engine.get_current_country():
            QMessageBox.warning(self, "Azione Negata", "Seleziona prima una nazione dalla mappa.")
            return

        self.btn_send.setEnabled(False)
        self.lbl_loading.setText("Ricezione dispacci diplomatici in corso...")
        self.lbl_loading.setVisible(True)
        self.progress_loading.setVisible(True)

        self.turn_worker = TurnWorker(self.engine, internal_text, economy_text, diplomacy_text, time_jump_text)
        self.turn_worker.finished_signal.connect(self.on_turn_finished)
        self.turn_worker.start()

    @pyqtSlot(dict)
    def on_turn_finished(self, result: dict) -> None:
        self.lbl_loading.setVisible(False)
        self.progress_loading.setVisible(False)
        self.btn_send.setEnabled(True)

        if result.get("status") == "success":
            self.input_internal.clear()
            self.input_economy.clear()
            self.input_diplomacy.clear()
            self.update_ui_from_state()

            report_dialog = ReportDialog(result['new_date'], result['response'], self)
            report_dialog.exec()

        elif result.get("status") == "game_over":
            self.update_ui_from_state()
            report_dialog = ReportDialog(result['new_date'], result['response'], self)
            report_dialog.setWindowTitle("REPORT FINALE - GOVERNO CADUTO")
            report_dialog.exec()
            QMessageBox.critical(self, "GAME OVER",
                                 "Il tuo governo è caduto. Clicca su 'Nuova Partita' nel menu in alto per ricominciare.")
        else:
            QMessageBox.warning(self, "Errore Operativo", result.get("message", "Errore sconosciuto"))

    @pyqtSlot()
    def show_advanced_stats(self) -> None:
        country = self.engine.get_current_country()
        if not country:
            QMessageBox.information(self, "Attenzione", "Seleziona prima una nazione!")
            return
        stats = self.engine.get_stats()
        intel = self.engine.get_country_intel(country)
        dialog = AdvancedStatsDialog(country, stats, intel, self)
        dialog.exec()

    @pyqtSlot(QListWidgetItem)
    def handle_history_click(self, item: QListWidgetItem) -> None:
        data = item.data(Qt.ItemDataRole.UserRole)
        if data and isinstance(data, dict):
            dialog = ReportDialog(data["date"], data["report"], self)
            dialog.setWindowTitle(f"Rapporto di Archivio - {data['date']}")
            dialog.exec()
        else:
            QMessageBox.information(self, "Archivio", "Questo è un vecchio evento di sistema.")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow()
    window.showFullScreen()
    sys.exit(app.exec())
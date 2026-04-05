import sys
import os
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTextEdit, QLabel, QMessageBox, QFrame,
    QComboBox, QFileDialog, QGroupBox, QProgressBar, QListWidget, QListWidgetItem, QDialog
)
from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot, QTimer
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
from ui_components import ReportDialog, ApiDialog, ScenarioSelectionDialog, CountryIntelDialog
from ui_menu import setup_menu_bar
from auto_updater import AutoUpdater  # L'Auto Updater di GitHub!

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

    def init_ui(self) -> None:
        current_version = AutoUpdater.get_local_version()
        self.setWindowTitle(f"Polis_AI - Geopolitical Simulator (v{current_version})")
        self.resize(1400, 900)

        self.setup_menu()

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

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
            self.render_fallback_map(main_layout,
                                     "Modulo 'PyQt6-WebEngine' mancante. Installa con: pip install PyQt6-WebEngine")

        side_container = QWidget()
        side_container.setMaximumWidth(380)

        side_panel = QVBoxLayout(side_container)
        side_panel.setContentsMargins(15, 10, 15, 10)

        # 1. Info Paese Base
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

        # 🛑 GAME OVER BANNER (Nascosto di default)
        self.lbl_game_over = QLabel("<b>IL TUO GOVERNO È CADUTO</b>")
        self.lbl_game_over.setStyleSheet(
            "background-color: #c0392b; color: white; padding: 10px; font-size: 16px; border-radius: 5px;")
        self.lbl_game_over.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_game_over.setVisible(False)
        side_panel.addWidget(self.lbl_game_over)

        # 2. Input Comandi a Ministeri
        side_panel.addSpacing(5)
        lbl_direttive = QLabel("<b>Direttive Ministeriali:</b>")
        side_panel.addWidget(lbl_direttive)

        self.input_internal = QTextEdit()
        self.input_internal.setPlaceholderText("Politica Interna (es: riforme, polizia...)")
        self.input_internal.setStyleSheet(
            "font-size: 13px; padding: 4px; border: 1px solid #95a5a6; border-radius: 4px;")
        self.input_internal.setMaximumHeight(42)
        side_panel.addWidget(self.input_internal)

        self.input_economy = QTextEdit()
        self.input_economy.setPlaceholderText("Economia (es: tasse, infrastrutture...)")
        self.input_economy.setStyleSheet(
            "font-size: 13px; padding: 4px; border: 1px solid #95a5a6; border-radius: 4px;")
        self.input_economy.setMaximumHeight(42)
        side_panel.addWidget(self.input_economy)

        self.input_diplomacy = QTextEdit()
        self.input_diplomacy.setPlaceholderText("Difesa & Esteri (es: truppe, alleanze...)")
        self.input_diplomacy.setStyleSheet(
            "font-size: 13px; padding: 4px; border: 1px solid #95a5a6; border-radius: 4px;")
        self.input_diplomacy.setMaximumHeight(42)
        side_panel.addWidget(self.input_diplomacy)

        # 3. Avanzamento e Esecuzione
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

        side_panel.addSpacing(5)

        # 4. Cruscotto (Stats)
        stats_group = QGroupBox("Cruscotto Nazionale")
        stats_group.setStyleSheet("font-weight: bold; font-size: 12px;")
        stats_layout = QVBoxLayout()
        stats_layout.setContentsMargins(5, 5, 5, 5)

        budget_layout = QHBoxLayout()
        self.lbl_treasury = QLabel("Tesoro: <b>--</b>")
        self.lbl_treasury.setStyleSheet("color: #27ae60; font-size: 12px;")
        self.lbl_treasury.setAlignment(Qt.AlignmentFlag.AlignLeft)

        self.lbl_debt = QLabel("Debito: <b>--</b>")
        self.lbl_debt.setStyleSheet("color: #c0392b; font-size: 12px;")
        self.lbl_debt.setAlignment(Qt.AlignmentFlag.AlignRight)

        budget_layout.addWidget(self.lbl_treasury)
        budget_layout.addWidget(self.lbl_debt)
        stats_layout.addLayout(budget_layout)

        self.lbl_population = QLabel("Popolazione: <b>-- Milioni</b>")
        self.lbl_population.setStyleSheet("color: #2980b9; font-size: 13px; margin-bottom: 5px;")
        self.lbl_population.setAlignment(Qt.AlignmentFlag.AlignCenter)
        stats_layout.addWidget(self.lbl_population)

        self.bar_stability = self.create_progress_bar("Stabilità Interna", "#3498db")
        stats_layout.addWidget(QLabel("Stabilità Interna:"))
        stats_layout.addWidget(self.bar_stability)

        self.bar_economy = self.create_progress_bar("Salute Economica", "#f1c40f")
        stats_layout.addWidget(QLabel("Salute Economica:"))
        stats_layout.addWidget(self.bar_economy)

        stats_group.setLayout(stats_layout)
        side_panel.addWidget(stats_group)

        # 5. Relazioni Estere
        diplomacy_group = QGroupBox("Relazioni Estere")
        diplomacy_group.setStyleSheet("font-weight: bold; font-size: 12px;")
        diplomacy_layout = QVBoxLayout()
        diplomacy_layout.setContentsMargins(5, 2, 5, 2)

        self.list_diplomacy = QListWidget()
        self.list_diplomacy.setStyleSheet(
            "font-weight: normal; font-size: 11px; background-color: #fdfdfd; border: 1px solid #dcdde1;")
        self.list_diplomacy.setMaximumHeight(65)
        diplomacy_layout.addWidget(self.list_diplomacy)

        diplomacy_group.setLayout(diplomacy_layout)
        side_panel.addWidget(diplomacy_group, stretch=1)

        # 6. Cronologia Eventi
        history_group = QGroupBox("Cronologia Storica")
        history_group.setStyleSheet("font-weight: bold; font-size: 12px;")
        history_layout = QVBoxLayout()
        history_layout.setContentsMargins(5, 2, 5, 2)

        self.list_history = QListWidget()
        self.list_history.setStyleSheet(
            "font-weight: normal; font-size: 11px; background-color: #fdfdfd; border: 1px solid #dcdde1;")
        self.list_history.setMaximumHeight(65)
        history_layout.addWidget(self.list_history)

        history_group.setLayout(history_layout)
        side_panel.addWidget(history_group, stretch=1)

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
        bar.setFixedHeight(8)
        bar.setToolTip(tooltip)
        bar.setStyleSheet(f"""
            QProgressBar {{ border: 1px solid #bdc3c7; border-radius: 3px; background-color: #ecf0f1; margin-bottom: 2px; }}
            QProgressBar::chunk {{ background-color: {color_hex}; border-radius: 2px; }}
        """)
        return bar

    def setup_menu(self) -> None:
        setup_menu_bar(self)

    @pyqtSlot()
    def check_updates(self) -> None:
        """Chiama il modulo AutoUpdater (GitHub)"""
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
            self.update_ui_from_state()
            self.show_startup_scenario_dialog()

    def save_game_dialog(self) -> None:
        if not self.engine.get_current_country():
            QMessageBox.warning(self, "Attenzione", "Nessuna nazione selezionata.")
            return

        filepath, _ = QFileDialog.getSaveFileName(self, "Salva Partita", "", "Polis_AI Save Files (*.json)")
        if filepath:
            if not filepath.endswith('.json'): filepath += '.json'
            try:
                self.engine.save_game(filepath)
                QMessageBox.information(self, "Salvataggio Compiuto", "La partita è stata salvata.")
            except Exception as e:
                QMessageBox.critical(self, "Errore di Salvataggio", str(e))

    def load_game_dialog(self) -> None:
        filepath, _ = QFileDialog.getOpenFileName(self, "Carica Partita", "", "Polis_AI Save Files (*.json)")
        if filepath:
            try:
                self.engine.load_game(filepath)
                self.update_ui_from_state()
                QMessageBox.information(self, "Caricamento Compiuto", "Partita ripristinata con successo.")
            except Exception as e:
                QMessageBox.critical(self, "Errore di Caricamento", str(e))

    def update_ui_from_state(self) -> None:
        country = self.engine.get_current_country()

        # 🛑 GESTIONE UI GAME OVER 🛑
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

        stats = self.engine.get_stats()
        self.bar_stability.setValue(stats["stability"])
        self.bar_economy.setValue(stats["economy"])

        treasury = stats.get("treasury_billions", 0)
        t_color = "#27ae60" if treasury >= 0 else "#c0392b"
        self.lbl_treasury.setText(f"Tesoro: <b style='color:{t_color};'>$ {treasury} Mld</b>")

        debt = stats.get("public_debt_billions", 0)
        self.lbl_debt.setText(f"Debito: <b>$ {debt} Mld</b>")

        pop = stats.get("population_millions", 0.0)
        self.lbl_population.setText(f"Popolazione: <b>{pop} Milioni</b>")

        self.list_history.clear()
        self.list_history.addItems(self.engine.get_history())

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
                    QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
                    result = self.engine.expand_scenario_with_ai(country_name)
                    QApplication.restoreOverrideCursor()

                    if result["status"] == "success":
                        QMessageBox.information(self, "Censimento Completato", result["message"])
                    else:
                        QMessageBox.warning(self, "Errore", result["message"])
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

    def handle_action(self) -> None:
        internal_text: str = self.input_internal.toPlainText().strip()
        economy_text: str = self.input_economy.toPlainText().strip()
        diplomacy_text: str = self.input_diplomacy.toPlainText().strip()
        time_jump_text: str = self.combo_time.currentText()

        if not self.engine.get_current_country():
            QMessageBox.warning(self, "Azione Negata", "Seleziona prima una nazione dalla mappa.")
            return

        self.btn_send.setText("Elaborazione in corso...")
        self.btn_send.setEnabled(False)
        QApplication.processEvents()

        result = self.engine.process_action(internal_text, economy_text, diplomacy_text, time_jump_text)

        self.btn_send.setText("Esegui Turno")
        self.btn_send.setEnabled(True)

        if result.get("status") == "success":
            self.input_internal.clear()
            self.input_economy.clear()
            self.input_diplomacy.clear()
            self.update_ui_from_state()

            report_dialog = ReportDialog(result['new_date'], result['response'], self)
            report_dialog.exec()

        elif result.get("status") == "game_over":
            self.update_ui_from_state()  # Aggiorna la UI per mostrare il banner rosso e bloccare i bottoni

            # Mostra il report epico della sconfitta
            report_dialog = ReportDialog(result['new_date'], result['response'], self)
            report_dialog.setWindowTitle("REPORT FINALE - GOVERNO CADUTO")
            report_dialog.exec()

            QMessageBox.critical(self, "GAME OVER",
                                 "Il tuo governo è caduto. Clicca su 'Nuova Partita' nel menu in alto per ricominciare.")

        else:
            QMessageBox.warning(self, "Errore Operativo", result.get("message", "Errore sconosciuto"))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
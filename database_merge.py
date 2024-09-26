from PyQt5.QtWidgets import QFileDialog, QMessageBox
from PyQt5.QtWidgets import QGroupBox, QVBoxLayout, QLabel, QPushButton, QHBoxLayout
from PyQt5 import QtWidgets, uic
from PyQt5.QtWidgets import *
from PyQt5.QtGui import QFont, QIcon
from PyQt5.QtCore import Qt, QTimer
from datetime import datetime
import sqlite3
import os


class DatabaseIntegrationWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("데이터베이스 통합"))
        self.setMinimumSize(600, 400)
        self.setStyleSheet("""
            QDialog {
                background-color: #f0f0f0;
            }
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 10px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QLabel {
                color: #2c3e50;
                font-size: 14px;
            }
            QProgressBar {
                border: 2px solid #bdc3c7;
                border-radius: 5px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #3498db;
            }
            QTextEdit {
                border: 1px solid #bdc3c7;
                border-radius: 5px;
                padding: 5px;
            }
        """)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # 파일 선택 영역
        file_selection_widget = QWidget()
        file_selection_layout = QHBoxLayout(file_selection_widget)

        # 통합 파일 선택
        integration_widget = QWidget()
        integration_layout = QVBoxLayout(integration_widget)
        self.select_integration_file_btn = QPushButton(QIcon("image/folder.png"), self.tr("통합 파일 선택"))
        self.select_integration_file_btn.clicked.connect(self.select_integration_file)
        integration_layout.addWidget(self.select_integration_file_btn)
        self.selected_integration_file_label = QLabel(self.tr("선택된 통합 파일: 없음"))
        integration_layout.addWidget(self.selected_integration_file_label)
        file_selection_layout.addWidget(integration_widget)

        # 서브 파일 선택
        sub_files_widget = QWidget()
        sub_files_layout = QVBoxLayout(sub_files_widget)
        self.select_sub_files_btn = QPushButton(QIcon("image/files.png"), self.tr("서브 파일 선택"))
        self.select_sub_files_btn.clicked.connect(self.select_sub_files)
        sub_files_layout.addWidget(self.select_sub_files_btn)
        self.sub_files_list = QListWidget()
        sub_files_layout.addWidget(self.sub_files_list)
        file_selection_layout.addWidget(sub_files_widget)

        layout.addWidget(file_selection_widget)

        # 통합 버튼
        self.integrate_btn = QPushButton(QIcon("image/merge.png"), self.tr("통합 시작"))
        self.integrate_btn.clicked.connect(self.start_integration)
        self.integrate_btn.setEnabled(False)
        layout.addWidget(self.integrate_btn)

        # 진행 상황 표시
        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)

        # 로그 표시
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        layout.addWidget(self.log_text)


    def select_integration_file(self):
        file_name, _ = QFileDialog.getOpenFileName(self, self.tr("통합 파일 선택"), "", "SQLite Database Files (*.db)")
        if file_name:
            self.selected_integration_file_label.setText(f"선택된 통합 파일: {os.path.basename(file_name)}")
            self.integration_file = file_name
            self.check_integration_ready()

    def select_sub_files(self):
        file_names, _ = QFileDialog.getOpenFileNames(self, self.tr("서브 파일 선택"), "", "SQLite Database Files (*.db)")
        if file_names:
            self.sub_files_list.clear()
            for file in file_names:
                item = QListWidgetItem(os.path.basename(file))
                item.setIcon(QIcon("image/database.png"))
                self.sub_files_list.addItem(item)
            self.sub_files = file_names
            self.check_integration_ready()

    def check_integration_ready(self):
        if hasattr(self, 'integration_file') and hasattr(self, 'sub_files'):
            self.integrate_btn.setEnabled(True)
        else:
            self.integrate_btn.setEnabled(False)

    def start_integration(self):
        if not hasattr(self, 'integration_file') or not hasattr(self, 'sub_files'):
            QMessageBox.warning(self, self.tr("경고"), self.tr("통합 파일과 서브 파일을 모두 선택해주세요."))
            return

        try:
            self.progress_bar.setValue(0)
            self.log_text.clear()

            integration_conn = sqlite3.connect(self.integration_file)
            integration_cursor = integration_conn.cursor()

            tables = ['cal_assets_en', 'cal_assets_ko', 'dal_assets_en', 'dal_assets_ko']

            total_steps = len(self.sub_files) * len(tables)
            current_step = 0

            for sub_file in self.sub_files:
                try:
                    sub_conn = sqlite3.connect(sub_file)
                    sub_cursor = sub_conn.cursor()

                    for table in tables:
                        self.log_text.append(f"[{os.path.basename(sub_file)}] 테이블 {table} 통합 중...")

                        sub_cursor.execute(f"SELECT * FROM {table}")
                        rows = sub_cursor.fetchall()

                        for row in rows:
                            integration_cursor.execute(
                                f"INSERT OR REPLACE INTO {table} VALUES ({','.join(['?' for _ in row])})", row)

                        integration_conn.commit()
                        self.log_text.append(f"[{os.path.basename(sub_file)}] 테이블 {table} 통합 완료")

                        current_step += 1
                        self.progress_bar.setValue(int(current_step / total_steps * 100))

                    sub_conn.close()
                except Exception as e:
                    self.log_text.append(f"[{os.path.basename(sub_file)}] 오류 발생: {str(e)}")
                    QMessageBox.critical(self, self.tr("오류"), self.tr(f"[{os.path.basename(sub_file)}] 데이터베이스 통합 중 오류가 발생했습니다."))

            integration_conn.close()

            self.log_text.append("모든 테이블 통합 완료")
            QMessageBox.information(self, self.tr("완료"), self.tr("데이터베이스 통합이 완료되었습니다."))

        except Exception as e:
            self.log_text.append(f"오류 발생: {str(e)}")
            QMessageBox.critical(self, self.tr("오류"), self.tr("데이터베이스 통합 중 오류가 발생했습니다."))

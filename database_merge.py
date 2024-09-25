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
        self.setMinimumSize(400, 300)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # 통합 파일 선택 버튼
        self.select_integration_file_btn = QPushButton(self.tr("통합 파일 선택"))
        self.select_integration_file_btn.clicked.connect(self.select_integration_file)
        layout.addWidget(self.select_integration_file_btn)

        # 선택된 통합 파일 표시
        self.selected_integration_file_label = QLabel(self.tr("선택된 통합 파일: 없음"))
        layout.addWidget(self.selected_integration_file_label)

        # 서브 파일 선택 버튼
        self.select_sub_files_btn = QPushButton(self.tr("서브 파일 선택"))
        self.select_sub_files_btn.clicked.connect(self.select_sub_files)
        layout.addWidget(self.select_sub_files_btn)

        # 선택된 서브 파일 표시
        self.selected_sub_files_label = QLabel(self.tr("선택된 서브 파일: 없음"))
        layout.addWidget(self.selected_sub_files_label)

        # 통합 버튼
        self.integrate_btn = QPushButton(self.tr("통합 시작"))
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
            self.selected_integration_file_label.setText(f"선택된 통합 파일: {file_name}")
            self.integration_file = file_name
            self.check_integration_ready()

    def select_sub_files(self):
        file_names, _ = QFileDialog.getOpenFileNames(self, self.tr("서브 파일 선택"), "", "SQLite Database Files (*.db)")
        if file_names:
            self.selected_sub_files_label.setText(f"선택된 서브 파일: {', '.join(file_names)}")
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

            # 통합 파일 연결
            integration_conn = sqlite3.connect(self.integration_file)
            integration_cursor = integration_conn.cursor()

            tables = ['cal_assets_en', 'cal_assets_ko', 'dal_assets_en', 'dal_assets_ko']

            total_steps = len(self.sub_files) * len(tables)
            current_step = 0

            for sub_file in self.sub_files:
                try:
                    # 서브 파일 연결
                    sub_conn = sqlite3.connect(sub_file)
                    sub_cursor = sub_conn.cursor()

                    for table in tables:
                        self.log_text.append(f"[{sub_file}] 테이블 {table} 통합 중...")

                        # 서브 파일에서 데이터 가져오기
                        sub_cursor.execute(f"SELECT * FROM {table}")
                        rows = sub_cursor.fetchall()

                        # 통합 파일에 데이터 삽입
                        for row in rows:
                            integration_cursor.execute(
                                f"INSERT OR REPLACE INTO {table} VALUES ({','.join(['?' for _ in row])})", row)

                        integration_conn.commit()
                        self.log_text.append(f"[{sub_file}] 테이블 {table} 통합 완료")

                        current_step += 1
                        self.progress_bar.setValue(int(current_step / total_steps * 100))

                    sub_conn.close()
                except Exception as e:
                    self.log_text.append(f"[{sub_file}] 오류 발생: {str(e)}")
                    QMessageBox.critical(self, self.tr("오류"), self.tr(f"[{sub_file}] 데이터베이스 통합 중 오류가 발생했습니다."))

            integration_conn.close()

            self.log_text.append("모든 테이블 통합 완료")
            QMessageBox.information(self, self.tr("완료"), self.tr("데이터베이스 통합이 완료되었습니다."))

        except Exception as e:
            self.log_text.append(f"오류 발생: {str(e)}")
            QMessageBox.critical(self, self.tr("오류"), self.tr("데이터베이스 통합 중 오류가 발생했습니다."))

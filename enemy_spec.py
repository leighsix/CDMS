import sys
from PyQt5.QtWidgets import QApplication, QDialog, QVBoxLayout, QFormLayout, QLineEdit, QPushButton, QTableWidget, \
    QTableWidgetItem, \
    QHeaderView, QMessageBox, QHBoxLayout, QWidget, QCheckBox, QStyleOptionButton, QStyle, QGroupBox, QGridLayout
from PyQt5.QtCore import Qt, QRect
import json
from PyQt5.QtWidgets import QSplitter, QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QLabel

class EnemySpecWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("적 미사일 제원 입력"))
        self.initUI()
        self.setWindowFlags(self.windowFlags() | Qt.WindowMaximizeButtonHint | Qt.WindowMinimizeButtonHint)


    def initUI(self):
        layout = QHBoxLayout()
        self.setLayout(layout)

        splitter = QSplitter(Qt.Vertical)
        layout.addWidget(splitter)

        # 상단 위젯 (테이블)
        top_widget = QWidget()
        top_layout = QVBoxLayout(top_widget)

        self.table = MyTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(
            ["", self.tr("미사일명"), self.tr("최소위협반경"), self.tr("최대위협반경"), self.tr("주요기능"), self.tr("궤적계수")])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.table.setColumnWidth(0, 60)
        self.table.hideColumn(5)  # 궤적계수 열(5번 열)을 숨깁니다.

        for i in range(1, 6):
            self.table.horizontalHeader().setSectionResizeMode(i, QHeaderView.Stretch)

        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet(
            "QTableWidget { background-color: #f8f9fa; border: 1px solid #dee2e6; }"
            "QTableWidget::item { padding: 8px; height: 40px; text-align: center; }"
            "QTableWidget::item:selected { background-color: #e9ecef; }"
            "QHeaderView::section { background-color: #343a40; color: white; padding: 8px; font: bold 14px 강한공군체; }"
            "QTableWidget::item:alternate { background-color: #e9ecef; }"
        )

        top_layout.addWidget(self.table)

        # 버튼 레이아웃
        button_layout = QHBoxLayout()
        edit_button = QPushButton(self.tr("수정"))
        delete_button = QPushButton(self.tr("삭제"))

        button_style = (
            "QPushButton { font: 강한공군체; font-size: 14px; font-weight: bold; padding: 8px; "
            "background-color: #007bff; color: white; border: none; border-radius: 4px; }"
            "QPushButton:hover { background-color: #0056b3; }"
        )

        for button in [edit_button, delete_button]:
            button.setStyleSheet(button_style)
            button.setFixedSize(100, 35)

        edit_button.clicked.connect(self.edit_missile_info)
        delete_button.clicked.connect(self.delete_missile_info)

        button_layout.addStretch(1)
        button_layout.addWidget(edit_button)
        button_layout.addWidget(delete_button)

        top_layout.addLayout(button_layout)

        splitter.addWidget(top_widget)

        # 하단 위젯 (입력 폼)
        bottom_widget = QWidget()
        bottom_layout = QVBoxLayout(bottom_widget)

        form_layout = QFormLayout()
        self.name_edit = QLineEdit()
        self.min_radius_edit = QLineEdit()
        self.min_radius_edit.setPlaceholderText("00km")

        self.max_radius_edit = QLineEdit()
        self.max_radius_edit.setPlaceholderText("00km")
        self.function_edit = QTextEdit()
        self.function_edit.setMinimumHeight(100)

        for edit in [self.name_edit, self.min_radius_edit, self.max_radius_edit]:
            edit.setStyleSheet("QLineEdit { padding: 5px; border: 1px solid #ccc; border-radius: 3px; }")

        self.function_edit.setStyleSheet("QTextEdit { padding: 5px; border: 1px solid #ccc; border-radius: 3px; }")

        label_style = "QLabel { font-size: 14px; font-weight: bold; }"

        name_label = QLabel(self.tr("미사일명:"))
        name_label.setStyleSheet(label_style)
        min_radius_label = QLabel(self.tr("최소위협반경:"))
        min_radius_label.setStyleSheet(label_style)
        max_radius_label = QLabel(self.tr("최대위협반경:"))
        max_radius_label.setStyleSheet(label_style)
        function_label = QLabel(self.tr("주요기능:"))
        function_label.setStyleSheet(label_style)

        form_layout.addRow(name_label, self.name_edit)
        form_layout.addRow(min_radius_label, self.min_radius_edit)
        form_layout.addRow(max_radius_label, self.max_radius_edit)
        form_layout.addRow(function_label, self.function_edit)

        bottom_layout.addLayout(form_layout)

        # 궤적계수 입력 그룹박스 수정
        trajectory_group = QGroupBox(self.tr("궤적계수"))
        trajectory_group.setStyleSheet(label_style)
        trajectory_layout = QGridLayout()

        labels = ["alpha", "beta"]
        coeffs = ["a1", "a2", "b1", "b2"]

        for i, label in enumerate(labels):
            for j, coeff in enumerate(coeffs):
                trajectory_layout.addWidget(QLabel(f"{label} {coeff}:"), i * 2, j)
                line_edit = QLineEdit()
                line_edit.setObjectName(f"{label}_{coeff}")
                trajectory_layout.addWidget(line_edit, i * 2 + 1, j)

        trajectory_group.setLayout(trajectory_layout)
        bottom_layout.addWidget(trajectory_group)

        # 저장 버튼
        save_button = QPushButton(self.tr("저장"))
        save_button.setStyleSheet(
            "QPushButton { font: 강한공군체; font-size: 16px; font-weight: bold; padding: 8px; "
            "background-color: #4CAF50; color: white; border: none; border-radius: 4px; "
            "min-width: 150px; }"  # 버튼의 최소 너비를 150px로 설정
            "QPushButton:hover { background-color: #45a049; }"
        )
        save_button.clicked.connect(self.save_missile_info)
        bottom_layout.addWidget(save_button, alignment=Qt.AlignCenter)
        save_button.setFixedWidth(200)  # 버튼의 너비를 200px로 고정

        bottom_layout.addStretch(1)
        splitter.addWidget(bottom_widget)

        # 스플리터 비율 설정
        splitter.setSizes([int(self.height() * 0.7), int(self.height() * 0.3)])

        self.setMinimumSize(900, 600)
        self.setStyleSheet("QDialog { background-color: #ffffff; }")
        self.load_missile_info()

    def save_missile_info(self):
        try:
            name = self.name_edit.text().strip()  # 공백 제거
            min_radius = int(self.min_radius_edit.text() or 0)
            max_radius = int(self.max_radius_edit.text() or 0)
            function = self.function_edit.toPlainText().strip()  # 공백 제거

            # 필수 입력값 검증
            if not all([name, min_radius, max_radius, function]):
                QMessageBox.warning(self, self.tr("경고"), self.tr("모든 필드를 입력해주세요."))
                return

            # JSON 파일 읽기
            try:
                with open('missile_info.json', 'r', encoding='utf-8') as file:
                    data = json.load(file)
            except (FileNotFoundError, json.JSONDecodeError):
                data = {}

            # 기존 데이터 확인
            if name in data:
                reply = QMessageBox.question(self, self.tr('확인'),
                                             self.tr('이미 존재하는 미사일 정보입니다. 수정하시겠습니까?'),
                                             QMessageBox.Yes | QMessageBox.No)
                if reply == QMessageBox.No:
                    return

            # 미사일 계수 처리 Nathan J. Siegel의 "Modeling and Simulation of Ballistic Missile Trajectories" (2016) 논문
            default_coefficients = {
                "alpha": {"a1": -0.1024, "a2": -0.0285, "b1": -0.0228, "b2": -0.0072},
                "beta": {"a1": 2.82, "a2": -0.0334, "b1": 2.35, "b2": -0.00268}
            }

            # 궤적 계수 처리
            trajectory_coefficients = {}
            for label in ["alpha", "beta"]:
                trajectory_coefficients[label] = {}
                for coeff in ["a1", "a2", "b1", "b2"]:
                    line_edit = self.findChild(QLineEdit, f"{label}_{coeff}")
                    if line_edit:
                        try:
                            value = line_edit.text().strip()
                            trajectory_coefficients[label][coeff] = float(value) if value else \
                            default_coefficients[label][coeff]
                        except ValueError:
                            trajectory_coefficients[label][coeff] = default_coefficients[label][coeff]

            # 데이터 구조화
            data[name] = {
                'min_radius': min_radius,
                'max_radius': max_radius,
                'function': function,
                'trajectory_coefficients': trajectory_coefficients
            }

            # JSON 파일 저장
            with open('missile_info.json', 'w', encoding='utf-8') as file:
                json.dump(data, file, ensure_ascii=False, indent=4)

            self.load_missile_info()
            self.clear_inputs()
            QMessageBox.information(self, self.tr("성공"), self.tr("미사일 정보가 저장되었습니다."))

        except Exception as e:
            QMessageBox.critical(self, self.tr("오류"), self.tr(f"저장 중 오류가 발생했습니다: {str(e)}"))

    def load_missile_info(self):
        try:
            with open('missile_info.json', 'r', encoding='utf-8') as file:
                data = json.load(file)
        except FileNotFoundError:
            data = {}

        self.table.setRowCount(0)

        # 기본 폰트 크기 가져오기 및 2포인트 증가
        font = self.table.font()
        font.setPointSize(13)
        self.table.setFont(font)

        for name, info in data.items():
            row = self.table.rowCount()
            self.table.insertRow(row)
            checkbox = CenteredCheckBox()
            self.table.setCellWidget(row, 0, checkbox)
            items = [
                name,
                str(info['min_radius']),
                str(info['max_radius']),
                info['function'],
                json.dumps(info['trajectory_coefficients'])
            ]

            for col, text in enumerate(items, start=1):
                item = QTableWidgetItem(str(text))
                if col == 4:  # function 컬럼
                    item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                else:
                    item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, col, item)

            self.table.setRowHeight(row, 40)
        self.table.resizeColumnsToContents()
        self.table.setColumnWidth(0, 60)

    def clear_inputs(self):
        self.name_edit.clear()
        self.min_radius_edit.clear()
        self.max_radius_edit.clear()
        self.function_edit.clear()

        # 궤적계수 입력란 초기화
        for label in ["alpha", "beta"]:
            for coeff in ["a1", "a2", "b1", "b2"]:
                line_edit = self.findChild(QLineEdit, f"{label}_{coeff}")
                if line_edit:
                    line_edit.clear()

    def edit_missile_info(self):
        checked_rows = []
        for row in range(self.table.rowCount()):
            checkbox_widget = self.table.cellWidget(row, 0)
            if checkbox_widget and checkbox_widget.isChecked():
                checked_rows.append(row)

        if len(checked_rows) != 1:
            QMessageBox.warning(self, self.tr("경고"), self.tr("수정할 항목을 하나만 선택해주세요."))
            return

        row = checked_rows[0]
        try:
            self.name_edit.setText(self.table.item(row, 1).text())
            self.min_radius_edit.setText(self.table.item(row, 2).text())
            self.max_radius_edit.setText(self.table.item(row, 3).text())
            self.function_edit.setText(self.table.item(row, 4).text())

            # 미사일 계수 처리 Nathan J. Siegel의 "Modeling and Simulation of Ballistic Missile Trajectories" (2016) 논문
            default_coefficients = {
                "alpha": {"a1": -0.1024, "a2": -0.0285, "b1": -0.0228, "b2": -0.0072},
                "beta": {"a1": 2.82, "a2": -0.0334, "b1": 2.35, "b2": -0.00268}
            }

            trajectory_coefficients = default_coefficients
            if self.table.item(row, 5):
                try:
                    trajectory_coefficients = json.loads(self.table.item(row, 5).text())
                except json.JSONDecodeError:
                    print("JSON 디코딩 오류, 기본값 사용")

            for label in ["alpha", "beta"]:
                for coeff in ["a1", "a2", "b1", "b2"]:
                    line_edit = self.findChild(QLineEdit, f"{label}_{coeff}")
                    if line_edit:
                        value = trajectory_coefficients[label][coeff]
                        line_edit.setText(str(value))

        except Exception as e:
            QMessageBox.warning(self, self.tr("오류"), self.tr(f"데이터 로드 중 오류가 발생했습니다: {str(e)}"))

    def delete_missile_info(self):
        checked_rows = []
        for row in range(self.table.rowCount()):
            checkbox_widget = self.table.cellWidget(row, 0)
            if checkbox_widget and checkbox_widget.isChecked():
                checked_rows.append(row)

        if not checked_rows:
            QMessageBox.warning(self, self.tr("경고"), self.tr("삭제할 항목을 선택해주세요."))
            return

        reply = QMessageBox.question(self, self.tr('확인'), self.tr('선택한 항목을 삭제하시겠습니까?'),
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            with open('missile_info.json', 'r', encoding='utf-8') as file:
                data = json.load(file)

            for row in sorted(checked_rows, reverse=True):
                name = self.table.item(row, 1).text()
                if name in data:
                    del data[name]
                self.table.removeRow(row)

            with open('missile_info.json', 'w', encoding='utf-8') as file:
                json.dump(data, file, ensure_ascii=False, indent=4)

            self.load_missile_info()
            self.clear_inputs()

class CheckBoxHeader(QHeaderView):
    def __init__(self, orientation, parent):
        super().__init__(orientation, parent)
        self.isOn = False

    def paintSection(self, painter, rect, logicalIndex):
        painter.save()
        super().paintSection(painter, rect, logicalIndex)
        painter.restore()

        if logicalIndex == 0:
            option = QStyleOptionButton()
            option.rect = QRect(rect.x() + rect.width() // 2 - 12, rect.y() + rect.height() // 2 - 12, 24, 24)
            option.state = QStyle.State_Enabled | QStyle.State_Active
            if self.isOn:
                option.state |= QStyle.State_On
            else:
                option.state |= QStyle.State_Off
            self.style().drawControl(QStyle.CE_CheckBox, option, painter)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            x = self.logicalIndexAt(event.pos().x())
            if x == 0:
                self.isOn = not self.isOn
                self.updateSection(0)
                self.parent().on_header_clicked(self.isOn)
        super().mousePressEvent(event)

class CenteredCheckBox(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        self.checkbox = QCheckBox()
        self.checkbox.setStyleSheet("QCheckBox::indicator { width: 20px; height: 20px; }")
        layout.addWidget(self.checkbox)
        layout.setAlignment(Qt.AlignCenter)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

    def isChecked(self):
        return self.checkbox.isChecked()

    def setChecked(self, checked):
        self.checkbox.setChecked(checked)

class MyTableWidget(QTableWidget):
    def __init__(self, *args):
        super().__init__(*args)
        self.header_checked = False
        self.setHorizontalHeader(CheckBoxHeader(Qt.Horizontal, self))

    def on_header_clicked(self, checked):
        for row in range(self.rowCount()):
            checkbox_widget = self.cellWidget(row, 0)
            if checkbox_widget:
                checkbox_widget.checkbox.setChecked(checked)

    def uncheckAllRows(self):
        self.header_checked = False
        self.horizontalHeader().isOn = False
        self.horizontalHeader().updateSection(0)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = EnemySpecWindow()
    window.show()
    sys.exit(app.exec_())

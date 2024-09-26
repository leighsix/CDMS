import sys
from PyQt5.QtWidgets import QApplication, QDialog, QVBoxLayout, QFormLayout, QLineEdit, QPushButton, QTableWidget, \
    QTableWidgetItem, \
    QHeaderView, QMessageBox, QHBoxLayout, QWidget, QCheckBox, QStyleOptionButton, QStyle
from PyQt5.QtCore import Qt, QRect
import json
from PyQt5.QtWidgets import QSplitter, QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QLabel

class EnemySpecWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("방공무기체계 제원 입력"))
        self.initUI()
        self.setWindowFlags(self.windowFlags() | Qt.WindowMaximizeButtonHint | Qt.WindowMinimizeButtonHint)


    def initUI(self):
        layout = QHBoxLayout()
        self.setLayout(layout)

        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter)

        # 왼쪽 위젯 (입력 폼)
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)

        form_layout = QFormLayout()
        self.name_edit = QLineEdit()
        self.radius_edit = QLineEdit()
        self.radius_edit.setInputMask("9999999")
        self.function_edit = QTextEdit()  # QLineEdit에서 QTextEdit로 변경
        self.function_edit.setMinimumHeight(100)  # 최소 높이 설정

        for edit in [self.name_edit, self.radius_edit]:
            edit.setStyleSheet("QLineEdit { padding: 5px; border: 1px solid #ccc; border-radius: 3px; }")

        self.function_edit.setStyleSheet("QTextEdit { padding: 5px; border: 1px solid #ccc; border-radius: 3px; }")

        # 라벨 스타일 설정
        label_style = "QLabel { font-size: 14px; font-weight: bold; }"

        # 라벨 생성 및 스타일 적용
        name_label = QLabel(self.tr("미사일명:"))
        name_label.setStyleSheet(label_style)
        radius_label = QLabel(self.tr("위협반경:"))
        radius_label.setStyleSheet(label_style)
        function_label = QLabel(self.tr("주요기능:"))
        function_label.setStyleSheet(label_style)

        # 폼 레이아웃에 라벨과 입력 필드 추가
        form_layout.addRow(name_label, self.name_edit)
        form_layout.addRow(radius_label, self.radius_edit)
        form_layout.addRow(function_label, self.function_edit)

        left_layout.addLayout(form_layout)

        # 저장 버튼
        save_button = QPushButton(self.tr("저장"))
        save_button.setStyleSheet(
            "QPushButton { font: 강한공군체; font-size: 16px; font-weight: bold; padding: 8px; "
            "background-color: #4CAF50; color: white; border: none; border-radius: 4px; "
            "min-width: 150px; }"  # 버튼의 최소 너비를 150px로 설정
            "QPushButton:hover { background-color: #45a049; }"
        )
        save_button.clicked.connect(self.save_missile_info)
        left_layout.addWidget(save_button, alignment=Qt.AlignCenter)
        save_button.setFixedWidth(200)  # 버튼의 너비를 200px로 고정

        left_layout.addStretch(1)
        splitter.addWidget(left_widget)

        # 오른쪽 위젯 (테이블)
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)

        self.table = MyTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["", self.tr("미사일명"), self.tr("위협반경"), self.tr("주요기능")])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.table.setColumnWidth(0, 60)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet(
            "QTableWidget { background-color: #f8f9fa; border: 1px solid #dee2e6; }"
            "QTableWidget::item { padding: 8px; height: 40px; text-align: center; }"
            "QTableWidget::item:selected { background-color: #e9ecef; }"
            "QHeaderView::section { background-color: #343a40; color: white; padding: 8px; font: bold 14px 강한공군체; }"
            "QTableWidget::item:alternate { background-color: #e9ecef; }"
        )

        right_layout.addWidget(self.table)

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

        right_layout.addLayout(button_layout)

        splitter.addWidget(right_widget)

        # 스플리터 비율 설정
        splitter.setSizes([int(self.width() * 0.3), int(self.width() * 0.7)])

        self.setMinimumSize(900, 600)
        self.setStyleSheet("QDialog { background-color: #ffffff; }")
        self.load_missile_info()

    def save_missile_info(self):
        name = self.name_edit.text()
        radius = self.radius_edit.text()
        function = self.function_edit.toPlainText()  # QTextEdit에서 텍스트를 가져오는 메서드 수정

        if not all([name, radius, function]):
            QMessageBox.warning(self, self.tr("경고"), self.tr("모든 필드를 입력해주세요."))
            return

        try:
            with open('missile_info.json', 'r', encoding='utf-8') as file:
                data = json.load(file)
        except FileNotFoundError:
            data = {}

        if name in data:
            reply = QMessageBox.question(self, self.tr('확인'),
                                         self.tr('이미 존재하는 미사일 정보입니다. 수정하시겠습니까?'),
                                         QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.No:
                return

        data[name] = {
            'radius': radius,
            'function': function
        }

        with open('missile_info.json', 'w', encoding='utf-8') as file:
            json.dump(data, file, ensure_ascii=False, indent=4)

        self.load_missile_info()
        self.clear_inputs()
        QMessageBox.information(self, self.tr("성공"), self.tr("미사일 정보가 저장되었습니다."))

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
            for col, text in enumerate([name, info['radius'], info['function']], start=1):
                item = QTableWidgetItem(str(text))
                item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, col, item)

            # 행 높이 설정 (체크박스 높이 + 여유 공간)
            self.table.setRowHeight(row, 40)

        # 각 열의 내용에 맞게 열 너비 조정
        self.table.resizeColumnsToContents()
        # 체크박스 열은 고정 너비 유지
        self.table.setColumnWidth(0, 60)



    def clear_inputs(self):
        self.name_edit.clear()
        self.radius_edit.clear()
        self.function_edit.clear()

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
        self.name_edit.setText(self.table.item(row, 1).text())
        self.radius_edit.setText(self.table.item(row, 2).text())
        self.function_edit.setText(self.table.item(row, 3).text())

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
            with open('weapon_systems.json', 'r', encoding='utf-8') as file:
                data = json.load(file)

            for row in sorted(checked_rows, reverse=True):
                name = self.table.item(row, 1).text()
                if name in data:
                    del data[name]
                self.table.removeRow(row)

            with open('weapon_systems.json', 'w', encoding='utf-8') as file:
                json.dump(data, file, ensure_ascii=False, indent=4)

            self.load_weapon_systems()

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
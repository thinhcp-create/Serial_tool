import sys
import os
import json
import serial
import serial.tools.list_ports
from PyQt5.QtWidgets import (
    QApplication, QWidget, QPushButton, QVBoxLayout,
    QTextEdit, QLineEdit, QLabel, QComboBox, QHBoxLayout
)
from PyQt5.QtWidgets import QCheckBox  
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtWidgets import QFileDialog

SAVE_FILE = "saved_commands.json"


class SerialReader(QThread):
    data_received = pyqtSignal(str)

    def __init__(self, serial_port):
        super().__init__()
        self.serial = serial_port
        self.running = True

    def run(self):
        while self.running:
            if self.serial.in_waiting:
                try:
                    data = self.serial.readline().decode('utf-8').strip()
                    self.data_received.emit(data)
                except:
                    pass

    def stop(self):
        self.running = False
        self.quit()
        self.wait()


class SerialApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Serial Thinhdev")
        self.serial = None
        self.reader_thread = None
        self.quick_inputs = []
        self.init_ui()
        self.load_saved_commands()
        self.showMaximized()

    def init_ui(self):
        main_layout = QHBoxLayout()

        # ==== BÊN TRÁI: 10 ô gửi nhanh ====
        left_panel = QVBoxLayout()
        for i in range(20):
            row = QHBoxLayout()
            line_edit = QLineEdit()
            button = QPushButton(f"Gửi {i+1}")
            button.clicked.connect(self.make_send_handler(line_edit))
            row.addWidget(line_edit)
            row.addWidget(button)
            left_panel.addLayout(row)
            self.quick_inputs.append(line_edit)
        left_panel.addStretch()
        main_layout.addLayout(left_panel, 1)

        # ==== BÊN PHẢI: Serial + Output ====
        right_panel = QVBoxLayout()

        port_layout = QHBoxLayout()
        self.port_box = QComboBox()
        self.refresh_ports()
        self.baud_box = QComboBox()
        self.baud_box.addItems([ "115200","38400","19200","9600","4800", ])
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.clicked.connect(self.toggle_connection)
        port_layout.addWidget(QLabel("Port:"))
        port_layout.addWidget(self.port_box)
        port_layout.addWidget(QLabel("Baud:"))
        port_layout.addWidget(self.baud_box)
        port_layout.addWidget(self.connect_btn)

        self.receive_text = QTextEdit()
        self.auto_scroll_checkbox = QCheckBox("Auto Scroll")
        self.auto_scroll_checkbox.setChecked(True)  # Mặc định bật

        right_panel.addLayout(port_layout)
        right_panel.addWidget(self.receive_text)
        right_panel.addWidget(self.auto_scroll_checkbox)
        save_log_btn = QPushButton("Save Log")
        save_log_btn.clicked.connect(self.save_log_to_file)
        right_panel.addWidget(save_log_btn)

        main_layout.addLayout(right_panel, 3)

        self.setLayout(main_layout)

    def refresh_ports(self):
        self.port_box.clear()
        self.port_mapping = {}  # Để lưu mapping: hiển thị -> device
        ports = serial.tools.list_ports.comports()
        for port in ports:
            display_name = f"{port.device} - {port.description}"
            self.port_mapping[display_name] = port.device
            self.port_box.addItem(display_name)


    def toggle_connection(self):
        if self.serial and self.serial.is_open:
            self.disconnect_serial()
        else:
            self.connect_serial()

    def connect_serial(self):
        try:
            selected = self.port_box.currentText()
            port = self.port_mapping.get(selected, selected)
            baud = int(self.baud_box.currentText())
            self.serial = serial.Serial(port, baud, timeout=1)
            self.reader_thread = SerialReader(self.serial)
            self.reader_thread.data_received.connect(self.display_data)
            self.reader_thread.start()
            self.connect_btn.setText("Disconnect")
        except Exception as e:
            self.receive_text.append(f"<span style='color:red;'>Error: {str(e)}</span>")


    def disconnect_serial(self):
        if self.reader_thread:
            self.reader_thread.stop()
        if self.serial:
            self.serial.close()
        self.connect_btn.setText("Connect")

    def display_data(self, data):
        self.receive_text.append(f">> {data}")
        if self.auto_scroll_checkbox.isChecked():
            self.receive_text.moveCursor(self.receive_text.textCursor().End)


    def make_send_handler(self, line_edit):
        def handler():
            if not self.serial or not self.serial.is_open:
                QMessageBox.warning(self, "Chưa kết nối", "Bạn chưa kết nối tới cổng COM!")
                return
            text = line_edit.text()
            if text:
                self.serial.write((text).encode())
                self.receive_text.append(f'<span style="color:blue;">&lt;&lt; {text}</span>')
        return handler

    def closeEvent(self, event):
        self.save_commands()
        super().closeEvent(event)

    def save_commands(self):
        commands = [edit.text() for edit in self.quick_inputs]
        try:
            with open(SAVE_FILE, "w", encoding='utf-8') as f:
                json.dump(commands, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Lỗi lưu file: {e}")

    def load_saved_commands(self):
        if os.path.exists(SAVE_FILE):
            try:
                with open(SAVE_FILE, "r", encoding='utf-8') as f:
                    commands = json.load(f)
                    for i in range(min(len(commands), len(self.quick_inputs))):
                        self.quick_inputs[i].setText(commands[i])
            except Exception as e:
                print(f"Lỗi đọc file: {e}")

    def save_log_to_file(self):
        options = QFileDialog.Options()
        filename, _ = QFileDialog.getSaveFileName(
            self, "Lưu log", "serial_log.txt",
            "Text Files (*.txt);;All Files (*)", options=options
        )
        if filename:
            try:
                with open(filename, "w", encoding='utf-8') as f:
                    f.write(self.receive_text.toPlainText())
                QMessageBox.information(self, "Thành công", f"Đã lưu log vào:\n{filename}")
            except Exception as e:
                QMessageBox.critical(self, "Lỗi", f"Lỗi khi lưu log:\n{e}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SerialApp()
    window.show()
    sys.exit(app.exec_())

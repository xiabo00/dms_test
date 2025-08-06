import json
import os
from PyQt5.QtWidgets import QFileDialog, QDialog, QVBoxLayout, QListWidget, QLabel, QHBoxLayout, QPushButton, QLineEdit, QFrame, QGroupBox, QComboBox, QTextEdit
from PyQt5.QtWidgets import QDateTimeEdit
from PyQt5.QtGui import QPixmap, QFont
from PyQt5.QtCore import Qt, QSize, QDateTime
from aws_tool import get_thing_shadow
import images_rc
from log import logger


class TimeRangeDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("选择时间范围")
        self.setFixedSize(400, 200)

        layout = QVBoxLayout()

        # 开始时间选择
        start_layout = QHBoxLayout()
        start_layout.addWidget(QLabel("开始时间:"))
        self.start_edit = QDateTimeEdit()
        self.start_edit.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self.start_edit.setDateTime(QDateTime.currentDateTime().addDays(-1))  # 默认前一天
        start_layout.addWidget(self.start_edit)
        layout.addLayout(start_layout)

        # 结束时间选择
        end_layout = QHBoxLayout()
        end_layout.addWidget(QLabel("结束时间:"))
        self.end_edit = QDateTimeEdit()
        self.end_edit.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self.end_edit.setDateTime(QDateTime.currentDateTime())  # 默认当前时间
        end_layout.addWidget(self.end_edit)
        layout.addLayout(end_layout)

        # 确认按钮
        btn = QPushButton("确定")
        btn.clicked.connect(self.accept)
        layout.addWidget(btn)

        self.setLayout(layout)

    def get_time_range(self):
        """返回格式化后的时间范围"""
        return (
            self.start_edit.dateTime().toString("yyyy-MM-dd HH:mm:ss"),
            self.end_edit.dateTime().toString("yyyy-MM-dd HH:mm:ss")
        )

    @staticmethod
    def get_time_range_from_user(parent=None):
        """静态方法方便调用"""
        dialog = TimeRangeDialog(parent)
        if dialog.exec_() == QDialog.Accepted:
            return dialog.get_time_range()
        return None, None


class DownloadDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("下载选项")
        self.setFixedSize(500, 400)  # 扩大窗口以适应控件

        # 主布局
        layout = QVBoxLayout()

        # 文件选择列表（替换原来的QTextEdit）
        self.file_list_widget = QListWidget()
        self.file_list_widget.setSelectionMode(QListWidget.MultiSelection)  # 允许多选
        layout.addWidget(QLabel("请选择要下载的日志文件:"))
        layout.addWidget(self.file_list_widget)

        # 添加选择按钮
        btn_layout = QHBoxLayout()
        self.select_all_btn = QPushButton("全选")
        self.select_all_btn.clicked.connect(self.select_all_files)
        self.deselect_all_btn = QPushButton("取消全选")
        self.deselect_all_btn.clicked.connect(self.deselect_all_files)
        btn_layout.addWidget(self.select_all_btn)
        btn_layout.addWidget(self.deselect_all_btn)
        layout.addLayout(btn_layout)
        # 下载路径选择部分
        path_layout = QHBoxLayout()
        self.path_display = QLineEdit()
        self.path_display.setReadOnly(True)

        self.path_button = QPushButton("下载到...")
        self.path_button.clicked.connect(self.choose_download_path)

        path_layout.addWidget(QLabel("下载路径:"))
        path_layout.addWidget(self.path_display)
        path_layout.addWidget(self.path_button)

        layout.addLayout(path_layout)

        # 确认下载按钮
        self.confirm_button = QPushButton("开始下载")
        self.confirm_button.clicked.connect(self.start_download)
        layout.addWidget(self.confirm_button)

        self.setLayout(layout)

    def select_all_files(self):
        """选择所有文件"""
        for i in range(self.file_list_widget.count()):
            self.file_list_widget.item(i).setSelected(True)

    def deselect_all_files(self):
        """取消选择所有文件"""
        for i in range(self.file_list_widget.count()):
            self.file_list_widget.item(i).setSelected(False)

    def choose_download_path(self):
        # 打开文件夹选择对话框
        path = QFileDialog.getExistingDirectory(self, "选择下载目录")
        if path:
            self.path_display.setText(path)

    def start_download(self):
        download_path = self.path_display.text()
        if not download_path:
            logger.error("请先选择下载路径")
            return

        # 这里添加实际的下载逻辑
        print(f"开始下载到: {download_path}")
        # 下载完成后可以关闭对话框
        self.accept()


class ImageDialog(QDialog):
    def __init__(self, device_type, mode_value, sn, parent=None):
        super().__init__(parent)
        self.device_type = device_type
        self.mode_value = mode_value
        self.shadow_content = None
        self.result_data = None
        self.up_shadow_data = None
        self.sn = sn
        self._setup_ui()
        self._load_device_image(self.device_type)

    def _setup_ui(self):
        font = QFont('Arial', 15)

        """初始化UI组件"""
        self.setWindowTitle(f"{self.device_type} 设备视图")
        self.resize(800, 600)  # 主窗口大小保持不变

        # 主布局
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)

        # 左侧区域（图片+底部控制）
        left_layout = QVBoxLayout()

        # 图片容器（限制为400x400）
        image_container = QFrame()
        image_container.setFixedSize(400, 400)
        image_container.setStyleSheet("background-color: #f0f0f0;")
        image_container.setFrameShape(QFrame.Box)

        # 图片显示区域（左上角对齐）
        self.image_label = QLabel(image_container)
        self.image_label.setGeometry(0, 0, 400, 400)
        self.image_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)

        left_layout.addWidget(image_container)

        # 控制区域（垂直布局）
        control_layout = QVBoxLayout()

        # 串口选择下拉框（独立一行）
        serial_group = QGroupBox("串口选择")
        serial_group.setFont(font)
        serial_layout = QVBoxLayout()

        self.combo_serial = QComboBox()
        self.combo_serial.setFont(font)
        # 添加串口选项
        for i in range(1, 4):
            self.combo_serial.addItem(f"串口{i}", i)

        serial_layout.addWidget(self.combo_serial)
        serial_group.setLayout(serial_layout)
        control_layout.addWidget(serial_group)

        # 配置操作按钮（一行）
        config_btn_layout = QHBoxLayout()

        btn_get_config = QPushButton("获取Shadow")
        btn_get_config.setFont(font)
        btn_get_config.clicked.connect(self._on_get_config)
        config_btn_layout.addWidget(btn_get_config)

        btn_save_config = QPushButton("保存Shadow")
        btn_save_config.setFont(font)
        btn_save_config.clicked.connect(self._on_save_config)
        config_btn_layout.addWidget(btn_save_config)

        control_layout.addLayout(config_btn_layout)

        # 关闭按钮（独立一行）
        btn_close = QPushButton("关闭")
        btn_close.setFont(font)
        btn_close.clicked.connect(self._close)
        control_layout.addWidget(btn_close)

        left_layout.addLayout(control_layout)
        main_layout.addLayout(left_layout)

        # 右侧区域 - Shaw显示框
        right_layout = QVBoxLayout()

        shaw_group = QGroupBox("Shadow")
        shaw_group.setFont(font)
        shaw_layout = QVBoxLayout()

        self.shaw_display = QTextEdit()
        self.shaw_display.setFont(font)
        self.shaw_display.setReadOnly(True)
        self.shaw_display.setStyleSheet("background-color: white;")
        shaw_layout.addWidget(self.shaw_display)

        shaw_group.setLayout(shaw_layout)
        right_layout.addWidget(shaw_group)

        main_layout.addLayout(right_layout)
        self.setLayout(main_layout)

    def _on_get_config(self):
        """获取配置按钮点击事件"""
        if self.mode_value['mode'] == "INIT":
            try:
                if self.device_type in ["LMDC-V2", "LMDC"]:
                    # 获取当前目录下的Shadow/LMDC_shadow.jsonc文件
                    shadow_file_path = os.path.join("Shadow", "LMDC_shadow.json")
                if self.device_type in ["LBB300"]:
                    # 获取当前目录下的Shadow/LMDC_shadow.jsonc文件
                    shadow_file_path = os.path.join("Shadow", "LBB300_shadow.json")
                if self.device_type in ["LBB400"]:
                    # 获取当前目录下的Shadow/LMDC_shadow.jsonc文件
                    shadow_file_path = os.path.join("Shadow", "LBB400_shadow.json")

                # 读取文件内容
                with open(shadow_file_path, 'r', encoding='utf-8') as file:
                    self.shadow_content = file.read()

                # 显示到shaw_display文本框
                self.shaw_display.setPlainText(self.shadow_content)
                self.shaw_display.setReadOnly(False)
            except FileNotFoundError:
                self.shaw_display.setPlainText(f"Error: {shadow_file_path} not found")
            except Exception as e:
                self.shaw_display.setPlainText(f"Error: {str(e)}")

        elif self.mode_value['mode'] == "OTA" or self.mode_value['mode'] == "SWITCH":
            self.shadow_content = get_thing_shadow(self.sn['value'], 1)
            try:
                # 将 shadow_content 解析为 JSON
                shadow_json = json.loads(self.shadow_content)

                # 提取 state.desired 数据（如果存在）
                desired_data = shadow_json.get('state', {}).get('desired', {})

                # 将 desired_data 格式化为带缩进的 JSON 字符串，便于显示
                formatted_desired = json.dumps(desired_data, indent=2, ensure_ascii=False)
                self.shadow_content = formatted_desired
                self.shaw_display.setPlainText(self.shadow_content)
                self.shaw_display.setReadOnly(False)

            except json.JSONDecodeError as e:
                self.shaw_display = f"解析 shadow 内容出错: {str(e)}"
            except Exception as e:
                self.shaw_display = f"处理 shadow 数据时出错: {str(e)}"

    def _on_save_config(self):
        """保存配置按钮点击事件"""
        self.result_data = self.shaw_display.toPlainText()  # 获取文本内容
        selected_serial = self.combo_serial.currentText()

        if self.result_data:
            self.result_data = json.loads(self.result_data)
            if self.device_type in ["LMDC-V2", "LMDC"]:
                # 检查SN的第4位
                if len(self.sn['value']) >= 4:  # 确保SN长度足够
                    fourth_char = self.sn['value'][3]  # 第4位（索引从0开始）
                    if fourth_char == '1':
                        if selected_serial == "串口1":
                            self.result_data['RS485Port'] = "/dev/ttyS0"
                        elif selected_serial == "串口2":
                            self.result_data['RS485Port'] = "/dev/ttyS1"
                        elif selected_serial == "串口3":
                            self.result_data['RS485Port'] = "/dev/ttyS5"
                    elif fourth_char == '2':
                        if selected_serial == "串口1":
                            self.result_data['RS485Port'] = "/dev/ttyS0"
                        elif selected_serial == "串口2":
                            self.result_data['RS485Port'] = "/dev/ttyS3"
                        elif selected_serial == "串口3":
                            self.result_data['RS485Port'] = "/dev/ttyS4"
                    else:
                        logger.error(f"未知地区代码: {fourth_char}")
            elif self.device_type in ["LBB300"]:
                if selected_serial == "串口1":
                    self.result_data['AccCartopPort'] = "/dev/ttyS0"
                elif selected_serial == "串口2":
                    self.result_data['AccCartopPort'] = "/dev/ttyS3"
                elif selected_serial == "串口3":
                    self.result_data['AccCartopPort'] = "/dev/ttyS1"
            elif self.device_type in ["LBB400"]:
                if selected_serial == "串口1":
                    self.result_data['AccPort'] = "/dev/ttyS4"
                elif selected_serial == "串口2":
                    self.result_data['AccPort'] = "/dev/ttyS3"
                elif selected_serial == "串口3":
                    self.result_data['AccPort'] = "/dev/ttyS5"
            else:
                # 其他设备类型的处理
                pass
        else:
            # 其他模式的处理
            pass
        self.accept()  # 关闭对话框并返回 QDialog.Accepted

    def get_result(self):
        """供外部获取结果的接口"""
        return self.result_data

    def _close(self):
        self.close()

    def _load_device_image(self, device_type):
        """加载并适配图片"""
        if device_type == "LMDC":
            pixmap = QPixmap(":/DMS/images/LMDC.png")
        if device_type == "LBB300":
            pixmap = QPixmap(":/DMS/images/LBB300.png")
        if device_type == "LBB400":
            pixmap = QPixmap(":/DMS/images/LBB400.png")
        if device_type == "LMD6000":
            pixmap = QPixmap(":/DMS/images/LMD6000.png")
        if device_type == "LMDC-V2":
            pixmap = QPixmap(":/DMS/images/LMDC-V2.png")

        if not pixmap.isNull():
            # 计算保持宽高比的缩放尺寸
            scaled_pixmap = pixmap.scaled(
                QSize(400, 600),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.image_label.setPixmap(scaled_pixmap)

            # 可选：显示实际缩放比例
            # print(f"原始尺寸: {pixmap.width()}x{pixmap.height()}")
            # print(f"缩放后尺寸: {scaled_pixmap.width()}x{scaled_pixmap.height()}")
        else:
            # 错误状态显示灰色背景
            error_pixmap = QPixmap(QSize(400, 600))
            error_pixmap.fill(Qt.gray)
            self.image_label.setPixmap(error_pixmap)
            logger.error("图片加载失败")

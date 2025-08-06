from PyQt5.QtWidgets import QMainWindow, QLabel, QVBoxLayout, QWidget, QLineEdit, QHBoxLayout, QPushButton, QComboBox, QScrollArea, QSizePolicy
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QPalette, QColor
from fun import try_connect, try_close, populate_ip_addresses, match_sn, update_st_type_combo, switch_mode_buttons
from fun import update_upload_ui, get_software_version, browse_file, show_download_dialog, start_to_softwar, sn_reset


class DMSWindow(QMainWindow):
    def __init__(self, version="1.0.0"):
        super().__init__()
        self.version = version
        # 设置窗口标题
        self.setWindowTitle(f"DMS V{self.version}")
        self.ui_components = {}  # 存储所有UI组件的字典

        # # 设置窗口的初始大小
        # self.setFixedSize(900, 800)

        # 设置最小尺寸而不是固定尺寸
        self.setMinimumSize(900, 800)
        self.resize(900, 800)

        # # 禁用最大化按钮
        # self.setWindowFlags(self.windowFlags() & ~Qt.WindowMaximizeButtonHint)
        self.widgets = []
        self.creatview()

        # 用于保存socket连接
        self.ssh = {'client': None}  # 使用字典包装
        self.sn = {'value': None}
        self.shadow = {'value': None}

        self.close_falg = {'ssh_close': False, 'sn_close': False}

        self.mode_value = {
            'is_init_mode': False,
            'mode': None,
            'switch_mode_flag': False,
            'upload_label_combo_flag': False
        }

    def creatview(self):
        # 设置字体为Arial，大小为15
        font = QFont('Arial', 18)
        # font.setBold(True)

        # 设置调色板（Palette）来改变颜色
        palette = self.palette()

        palette.setColor(QPalette.Window, QColor(50, 50, 50))

        # 设置文本颜色为黑色（与浅蓝色背景形成对比）
        palette.setColor(QPalette.WindowText, QColor(206, 206, 206))

        # 设置基础控件文本颜色
        palette.setColor(QPalette.Text, Qt.black)

        # 设置按钮文本颜色
        palette.setColor(QPalette.ButtonText, Qt.black)

        # 应用调色板到主窗口
        self.setPalette(palette)

        # 确保样式应用到所有子控件
        self.setAutoFillBackground(True)

        button_style = """
            QPushButton {
                background-color: #808080;  /* 灰色背景 */
                color: white;               /* 白色字体 */
                border: 1px solid #606060;  /* 边框颜色 */
                border-radius: 4px;         /* 圆角 */
            }
            QPushButton:hover {
                background-color: #707070;  /* 鼠标悬停时的颜色 */
            }
            QPushButton:pressed {
                background-color: #505050;  /* 按钮按下时的颜色 */
            }
            QPushButton:disabled {
                background-color: #505050;  /* 禁用时的颜色 */
                color: #AAAAAA;
            }
        """

        # 创建主垂直布局
        self.main_layout = QVBoxLayout()

        # 主布局
        self.main_layout = QVBoxLayout()
        self.main_layout.setContentsMargins(10, 10, 10, 10)

        # 创建6个标准widget
        for widget in [QWidget(self) for _ in range(6)]:
            self.widgets.append(widget)
            self.main_layout.addWidget(widget, stretch=1)

        # 添加大widget
        big_widget = QWidget(self)
        self.widgets.append(big_widget)
        self.main_layout.addWidget(big_widget, stretch=3)

        # 添加最后两个widget
        for _ in range(2):
            widget = QWidget(self)
            self.widgets.append(widget)
            self.main_layout.addWidget(widget, stretch=1)

        # # 创建4个QWidget，每个的宽为900，高为200
        # self.widgets = [QWidget(self) for _ in range(6)]
        # for widget in self.widgets:
        #     widget.setFixedSize(900, 50)  # 设置QWidget的尺寸
        # widget = QWidget(self)
        # widget.setFixedSize(900, 300)  # 设置QWidget的尺寸
        # self.widgets.append(widget)

        # widget = QWidget(self)
        # widget.setFixedSize(900, 50)  # 设置QWidget的尺寸
        # self.widgets.append(widget)

        # widget = QWidget(self)
        # widget.setFixedSize(900, 50)  # 设置QWidget的尺寸
        # self.widgets.append(widget)

        # 第一个QWidget布局 ###
        self.first_layout = QHBoxLayout()
        self.first_layout.setContentsMargins(0, 0, 0, 0)  # 无外边距
        self.first_layout.setSpacing(10)  # 控件间距

        # 创建控件（不需要设置固定尺寸）
        self.local_label = QLabel("LOCAL:")
        self.local_label.setFont(font)
        self.first_layout.addWidget(self.local_label)

        self.local_combo = QComboBox()
        self.local_combo.setFont(font)
        self.local_combo.setMinimumSize(150, 40)
        self.first_layout.addWidget(self.local_combo, stretch=1)  # 可伸缩

        self.device_label = QLabel("DEVICE:")
        self.device_label.setFont(font)
        self.first_layout.addWidget(self.device_label)

        self.device_input = QLineEdit("192.168.1.108")
        self.device_input.setFont(font)
        self.device_input.setMinimumSize(150, 40)
        self.first_layout.addWidget(self.device_input, stretch=1)  # 可伸缩

        # 直接添加按钮
        self.connet_btn = QPushButton('Connect')
        self.connet_btn.setFont(font)
        self.connet_btn.setFixedSize(100, 40)
        self.connet_btn.setStyleSheet(button_style)
        self.first_layout.addWidget(self.connet_btn)

        self.colse_btn = QPushButton('Close')
        self.colse_btn.setFont(font)
        self.colse_btn.setEnabled(False)
        self.colse_btn.setFixedSize(100, 40)
        self.colse_btn.setStyleSheet(button_style)
        self.first_layout.addWidget(self.colse_btn)

        # 连接按钮点击事件
        self.connet_btn.clicked.connect(lambda: try_connect(self.ssh, self.close_falg, self.sn, self.ui_components))
        # 断开按钮点击事件
        self.colse_btn.clicked.connect(lambda: try_close(self.ssh, self.close_falg, self.mode_value, self.ui_components))

        # 获取并填充 IP 地址
        populate_ip_addresses(self.local_combo)

        # 将水平布局添加到主布局并设置对齐
        self.first_layout.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.widgets[0].setLayout(self.first_layout)  # 将水平布局设置到第一个QWidget中

        # 第二行的布局
        self.second_layout = QHBoxLayout()
        self.second_layout.setContentsMargins(0, 0, 0, 0)  # 无外边距
        self.second_layout.setSpacing(10)  # 控件间距

        # 设备类型选择
        self.device_type_label = QLabel("Device Type:")
        self.device_type_label.setFont(font)
        self.second_layout.addWidget(self.device_type_label)

        self.device_type_combo = QComboBox()
        self.device_type_combo.setFont(font)
        self.device_type_combo.setMinimumSize(150, 40)
        self.second_layout.addWidget(self.device_type_combo, stretch=1)  # 可伸缩

        # 序列号显示
        self.sn_label = QLabel("SN:")
        self.sn_label.setFont(font)
        self.second_layout.addWidget(self.sn_label)

        self.sn_display = QLineEdit()
        self.sn_display.setFont(font)
        self.sn_display.setReadOnly(True)
        self.sn_display.setMinimumSize(170, 40)
        self.second_layout.addWidget(self.sn_display, stretch=2)  # 更大的伸缩比例

        # 匹配按钮（右侧固定）
        self.match_but = QPushButton('Match')
        self.match_but.setFont(font)
        self.match_but.setEnabled(False)
        self.match_but.setFixedSize(100, 40)
        self.match_but.setStyleSheet(button_style)
        self.second_layout.addWidget(self.match_but)

        # 重置按钮
        self.reset_but = QPushButton('Reset')
        self.reset_but.setFont(font)
        self.reset_but.setEnabled(False)
        self.reset_but.setFixedSize(100, 40)
        self.reset_but.setStyleSheet(button_style)
        self.reset_but.clicked.connect(lambda: sn_reset(self.close_falg, self.mode_value, self.ui_components))
        self.second_layout.addWidget(self.reset_but)

        # 初始状态控制
        self.device_type_combo.setEnabled(False)
        self.sn_display.setEnabled(False)

        # 断开按钮点击事件
        self.match_but.clicked.connect(lambda: match_sn(self.close_falg, self.sn, self.ui_components))

        # 将第二行的水平布局添加到主布局
        self.second_layout.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.widgets[1].setLayout(self.second_layout)

        # 第三行的布局
        self.third_layout = QHBoxLayout()
        self.third_layout.setContentsMargins(0, 0, 0, 0)  # 无外边距
        self.third_layout.setSpacing(0)  # 禁用默认间距，完全用弹簧控制

        # 添加Mode Type标签
        self.mode_type_label = QLabel('Mode Type:')
        self.mode_type_label.setFont(font)
        self.mode_type_label.setMinimumSize(140, 40)
        self.third_layout.addWidget(self.mode_type_label)
        # self.mode_type_label = QLabel('Mode Type:')
        # self.mode_type_label.setFont(font)
        # self.mode_type_label.setStyleSheet("color: white;")  # 可以根据需要调整样式
        # self.third_layout.addWidget(self.mode_type_label)

        # # 左侧弹簧（使按钮组整体居中）
        # self.third_layout.addStretch(1)

        # 创建初始化按钮
        self.init_but = QPushButton('INIT')
        self.init_but.setFixedSize(100, 40)
        self.init_but.setFont(font)
        self.init_but.setEnabled(False)
        self.init_but.setStyleSheet(button_style)
        self.init_but.clicked.connect(lambda: update_st_type_combo(0, self.sn, self.mode_value, self.close_falg, self.ui_components, self.shadow))
        self.third_layout.addWidget(self.init_but)

        # 添加弹簧间隔
        self.third_layout.addStretch(1)

        # 创建OTA按钮
        self.ota_but = QPushButton('OTA')
        self.ota_but.setFixedSize(100, 40)
        self.ota_but.setFont(font)
        self.ota_but.setEnabled(False)
        self.ota_but.setStyleSheet(button_style)
        self.ota_but.clicked.connect(lambda: update_st_type_combo(1, self.sn, self.mode_value, self.close_falg, self.ui_components, self.shadow))
        self.third_layout.addWidget(self.ota_but)

        # 添加弹簧间隔
        self.third_layout.addStretch(1)

        # 创建SWITCH按钮
        self.switch_but = QPushButton('SWITCH')
        self.switch_but.setFixedSize(100, 40)
        self.switch_but.setFont(font)
        self.switch_but.setEnabled(False)
        self.switch_but.setStyleSheet(button_style)
        self.switch_but.clicked.connect(lambda: update_st_type_combo(2, self.sn, self.mode_value, self.close_falg, self.ui_components, self.shadow))
        self.third_layout.addWidget(self.switch_but)

        # 添加弹簧间隔
        self.third_layout.addStretch(1)

        # 创建模式切换按钮
        self.mode_switch_but = QPushButton('Mode Switch')
        self.mode_switch_but.setFixedSize(150, 40)
        self.mode_switch_but.setFont(font)
        self.mode_switch_but.setEnabled(False)
        self.mode_switch_but.setStyleSheet(button_style)
        self.mode_switch_but.clicked.connect(lambda: switch_mode_buttons(self.mode_value, self.ui_components))
        self.third_layout.addWidget(self.mode_switch_but)

        # 右侧弹簧（与左侧对称）
        self.third_layout.addStretch(1)

        # 将第三行的水平布局添加到主布局
        self.third_layout.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.widgets[2].setLayout(self.third_layout)

        # 第四行的布局
        self.fourth_layout = QHBoxLayout()
        self.fourth_layout.setContentsMargins(0, 0, 0, 0)  # 无外边距
        self.fourth_layout.setSpacing(15)  # 统一控件间距

        # 左侧控件组（标签+下拉框）
        self.st_label = QLabel("Software Type:")
        self.st_label.setFont(font)
        self.st_label.setMinimumSize(140, 40)  # 最小尺寸替代固定尺寸
        self.fourth_layout.addWidget(self.st_label)

        self.st_type_combo = QComboBox()
        self.st_type_combo.setFont(font)
        self.st_type_combo.setMinimumSize(200, 40)
        self.st_type_combo.setEnabled(False)
        self.fourth_layout.addWidget(self.st_type_combo, stretch=1)  # 可伸缩

        # 右侧控件组（标签+下拉框）
        self.upload_label = QLabel("Up Type:")
        self.upload_label.setFont(font)
        self.upload_label.setMinimumSize(80, 40)
        self.fourth_layout.addWidget(self.upload_label)

        self.upload_label_combo = QComboBox()
        self.upload_label_combo.setFont(font)
        self.upload_label_combo.setMinimumSize(200, 40)
        self.upload_label_combo.setEnabled(False)
        self.upload_label_combo.currentTextChanged.connect(
            lambda: update_upload_ui(self.mode_value, self.close_falg, self.ui_components))
        self.fourth_layout.addWidget(self.upload_label_combo)

        # # 添加右侧伸缩空间（可选）
        # self.fourth_layout.addStretch(1)

        # 将第四行的水平布局添加到主布局
        self.fourth_layout.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.widgets[3].setLayout(self.fourth_layout)

        # 第五行的布局
        self.fifth_layout = QHBoxLayout()
        self.fifth_layout.setContentsMargins(0, 0, 0, 0)  # 无外边距
        self.fifth_layout.setSpacing(15)  # 统一控件间距

        # 版本信息标签
        self.csv_label = QLabel("Current Software Version:")
        self.csv_label.setFont(font)
        self.csv_label.setMinimumSize(230, 40)  # 最小宽度替代固定宽度
        self.fifth_layout.addWidget(self.csv_label)

        # 版本显示框
        self.csv_display = QLineEdit()
        self.csv_display.setFont(font)
        self.csv_display.setReadOnly(True)
        self.csv_display.setMinimumSize(300, 40)
        self.fifth_layout.addWidget(self.csv_display, stretch=1)  # 可伸缩

        # GET按钮
        self.get_version_but = QPushButton('GET')
        self.get_version_but.setFont(font)
        self.get_version_but.setMinimumSize(100, 40)  # 按钮保持固定大小
        self.get_version_but.setEnabled(False)
        self.get_version_but.setStyleSheet(button_style)
        self.get_version_but.clicked.connect(
            lambda: get_software_version(self.mode_value, self.ssh, self.sn, self.ui_components))
        self.fifth_layout.addWidget(self.get_version_but)

        # # 右侧伸缩空间（可选）
        # self.fifth_layout.addStretch(1)

        # 将第五行的水平布局添加到主布局
        self.fifth_layout.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.widgets[4].setLayout(self.fifth_layout)

        # 第六行的布局
        self.sixth_layout = QHBoxLayout()
        self.sixth_layout.setContentsMargins(0, 0, 0, 0)  # 无外边距
        self.sixth_layout.setSpacing(10)  # 控件间距

        # 1. Init版本标签
        self.init_Version_label = QLabel("Init Software Version:")
        self.init_Version_label.setMinimumSize(200, 40)
        self.init_Version_label.setFont(font)
        self.sixth_layout.addWidget(self.init_Version_label)

        # 2. OTA版本标签
        self.ota_Version_label = QLabel("Ota Software Version:")
        self.ota_Version_label.setMinimumSize(200, 40)
        self.ota_Version_label.setFont(font)
        self.ota_Version_label.setVisible(False)
        self.sixth_layout.addWidget(self.ota_Version_label)

        # 3. Switch版本标签
        self.switch_Version_label = QLabel("Switch Software Version:")
        self.switch_Version_label.setMinimumSize(250, 40)
        self.switch_Version_label.setFont(font)
        self.switch_Version_label.setVisible(False)
        self.sixth_layout.addWidget(self.switch_Version_label)

        # 4. 本地上传文件路径框 (修改这部分)
        self.local_version_edit = QLineEdit()
        self.local_version_edit.setMinimumSize(250, 40)
        self.local_version_edit.setFont(font)
        self.local_version_edit.setReadOnly(True)
        # 添加以下两行：
        self.local_version_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.sixth_layout.addWidget(self.local_version_edit, stretch=1)  # 设置较大的拉伸因子

        # 5. S3版本下拉框 (修改这部分)
        self.S3_Version_combo = QComboBox()
        self.S3_Version_combo.setMinimumSize(250, 40)
        self.S3_Version_combo.setFont(font)
        self.S3_Version_combo.setVisible(False)
        # 添加以下两行：
        self.S3_Version_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.sixth_layout.addWidget(self.S3_Version_combo, stretch=1)  # 设置较大的拉伸因子

        # 6. 浏览按钮
        self.browse_button = QPushButton("浏览")
        self.browse_button.setFixedSize(80, 40)
        self.browse_button.setFont(font)
        self.browse_button.setEnabled(False)
        self.browse_button.setStyleSheet(button_style)
        self.browse_button.clicked.connect(lambda: browse_file(self.ssh, self.mode_value, self.ui_components))
        self.sixth_layout.addWidget(self.browse_button)

        # 8. 开始按钮
        self.start_button = QPushButton("Start")
        self.start_button.setFixedSize(150, 40)
        self.start_button.setFont(font)
        self.start_button.setEnabled(False)
        self.start_button.setStyleSheet(button_style)
        self.start_button.clicked.connect(lambda: start_to_softwar(self.mode_value, self.sn, self.ui_components, self.shadow, self.ssh))
        self.sixth_layout.addWidget(self.start_button)

        # 将第六行的水平布局添加到主布局
        self.sixth_layout.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.widgets[5].setLayout(self.sixth_layout)

        # 第七行的布局
        self.seventh_layout = QHBoxLayout()
        self.seventh_layout.setContentsMargins(0, 0, 0, 0)  # 无外边距
        self.seventh_layout.setSpacing(0)  # 禁用默认间距

        # 创建滚动区域（占满可用空间）
        self.scroll_area = QScrollArea()
        self.scroll_area.setMinimumSize(700, 300)  # 设置固定尺寸
        self.scroll_area.setWidgetResizable(True)  # 关键设置：允许内容自适应
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)  # 禁用水平滚动条
        self.scroll_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)  # 可伸缩

        # 创建内容容器
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)  # 左上对齐
        self.content_layout.setContentsMargins(5, 5, 5, 5)  # 添加5px内边距
        self.content_layout.setSpacing(5)  # 设置内容间距

        # 关键设置：内容尺寸策略
        self.content_widget.setSizePolicy(
            QSizePolicy.Expanding,  # 水平方向尽可能扩展
            QSizePolicy.Minimum  # 垂直方向按内容最小高度
        )

        # 将容器添加到滚动区域
        self.scroll_area.setWidget(self.content_widget)

        # 添加滚动区域到布局
        self.seventh_layout.addWidget(self.scroll_area)

        # 将第七行的水平布局添加到主布局
        self.seventh_layout.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.widgets[6].setLayout(self.seventh_layout)

        # 倒数第二行的布局
        self.next_to_last_layout = QHBoxLayout()
        self.next_to_last_layout.setContentsMargins(0, 0, 0, 0)  # 设置左右上下边距为0
        self.next_to_last_layout.setSpacing(10)  # 设置按钮之间的水平间距为10像素，可以根据需要调整

        # 创建软件类型标签
        self.log_down_label = QLabel("Download Log")
        self.log_down_label.setFixedSize(160, 40)
        self.log_down_label.setFont(font)
        self.next_to_last_layout.addWidget(self.log_down_label)

        # 将倒数第二行的水平布局添加到主布局
        self.next_to_last_layout.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.widgets[-2].setLayout(self.next_to_last_layout)

        # 最后一行的布局
        self.Last_layout = QHBoxLayout()
        self.Last_layout.setContentsMargins(0, 0, 0, 0)  # 设置左右上下边距为0
        self.Last_layout.setSpacing(10)  # 设置按钮之间的水平间距为10像素，可以根据需要调整

        # 创建软件类型标签
        self.log_st_label = QLabel("Software Type:")
        self.log_st_label.setFixedSize(160, 40)
        self.log_st_label.setFont(font)
        self.Last_layout.addWidget(self.log_st_label)

        # 创建软件类型下拉框
        self.log_st_type_combo = QComboBox()
        self.log_st_type_combo.setFixedSize(200, 40)
        self.log_st_type_combo.setFont(font)
        self.log_st_type_combo.setEnabled(False)  # 初始化为禁用状态
        self.Last_layout.addWidget(self.log_st_type_combo)

        # 创建DOWN类型标签
        self.Download_label = QLabel("Download:")
        self.Download_label.setFixedSize(115, 40)
        self.Download_label.setFont(font)
        self.Last_layout.addWidget(self.Download_label)

        # 创建下载方式下拉框
        self.Download_label_combo = QComboBox()
        self.Download_label_combo.setFixedSize(90, 40)
        self.Download_label_combo.setFont(font)
        self.Download_label_combo.setEnabled(False)  # 初始化为禁用状态
        self.Download_label_combo.addItems(["Local", "S3"])
        self.Last_layout.addWidget(self.Download_label_combo)

        # LOG下载按钮
        self.down_button = QPushButton("下载")
        self.down_button.setFixedSize(80, 40)
        self.down_button.setFont(font)
        self.down_button.setEnabled(False)  # 初始化为禁用状态
        self.down_button.setStyleSheet(button_style)
        self.down_button.clicked.connect(lambda: show_download_dialog(self.ssh, self.ui_components))
        self.Last_layout.addWidget(self.down_button)

        # 将最后一行水平布局添加到主布局
        self.Last_layout.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.widgets[-1].setLayout(self.Last_layout)

        self.ui_components = {
            'first_row': {
                'local_label': self.local_label,
                'local_combo': self.local_combo,
                'device_label': self.device_label,
                'device_input': self.device_input,
                'connect_btn': self.connet_btn,
                'close_btn': self.colse_btn
            },
            'second_row': {
                'device_type_label': self.device_type_label,
                'device_type_combo': self.device_type_combo,
                'sn_label': self.sn_label,
                'sn_display': self.sn_display,
                'match_but': self.match_but,
                'reset_but': self.reset_but
            },
            'third_row': {
                'init_but': self.init_but,
                'ota_but': self.ota_but,
                'switch_but': self.switch_but,
                'mode_switch_but': self.mode_switch_but,
            },
            'fourth_row': {
                'st_label': self.st_label,
                'st_type_combo': self.st_type_combo,
                'upload_label': self.upload_label,
                'upload_label_combo': self.upload_label_combo,
            },
            'fifth_row': {
                'csv_label': self.csv_label,
                'csv_display': self.csv_display,
                'get_version_but': self.get_version_but,
            },
            'sixth_row': {
                'init_Version_label': self.init_Version_label,
                'ota_Version_label': self.ota_Version_label,
                'switch_Version_label': self.switch_Version_label,
                'local_version_edit': self.local_version_edit,
                'S3_Version_combo': self.S3_Version_combo,
                'browse_button': self.browse_button,
                'start_button': self.start_button,
            },
            'seventh_row': {
                'scroll_area': self.scroll_area,
                'content_widget': self.content_widget,
                'content_layout': self.content_layout
            },
            'next_to_last': {
                'log_down_label': self.log_down_label,
            },
            'last_layout': {
                'log_st_label': self.log_st_label,
                'log_st_type_combo': self.log_st_type_combo,
                'Download_label': self.Download_label,
                'Download_label_combo': self.Download_label_combo,
                'down_button': self.down_button,
            },
        }

        # # 将5个QWidget添加到主布局
        # for widget in self.widgets:
        #     self.main_layout.addWidget(widget)

        # 设定中央小部件
        central_widget = QWidget()
        central_widget.setLayout(self.main_layout)
        self.setCentralWidget(central_widget)

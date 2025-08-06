import json
import os
import re
import paramiko
import socket
from PyQt5.QtWidgets import QMessageBox, QFileDialog, QDialog, QLabel
from PyQt5.QtCore import QDateTime
from aws_tool import get_thing_version, get_client
import boto3
from config_win import DownloadDialog, ImageDialog, TimeRangeDialog
from log import logger
import config_in

# 定义各软件类型的验证规则
validation_rules = {
    "LiftBennu100": {
        "prefix": "LiftBennu100",
        "version": r"2\.4\.5",
        "example": "LiftBennu100-3.9.16-3.1.0",
        "target_dir": "/opt/lb100",
        "work_dir": "/opt/lb100/lb100/scripts",
        "executable_file": "/opt/lb100/lb100/scripts/install.sh",
        "version_command": "/opt/lb100/lb100/lb100 -v",
        "pyversion_command": "/opt/lb100/lb100/lb100 -pv",
        "service_name": "lb100"
    },
    "LMD-TSS": {
        "prefix": "lmd-tss",
        "version": r"2\.5\.2-2\.0\.4-2\.0\.3",
        "example": "lmd-tss-2.5.2-2.0.4-2.0.3",
        "target_dir": "/opt/lmd-tss",
        "work_dir": "/opt/lmd-tss/lmd-tss",
        "executable_file": "/opt/lmd-tss/lmd-tss//update.sh",
        "version_path": "/opt/lmd-tss/lmd-tss",
        "version_file": "version",
        "service_name": "tms"
    },
    "LiftPhoenix300-v2": {
        "prefix": "LiftPhoenix300",
        "version": r"2\.0\.8",
        "example": "LiftPhoenix300-3.9.16-2.0.8",
        "target_dir": "/opt/lp300",
        "work_dir": "/opt/lp300/lp300/scripts",
        "executable_file": "/opt/lp300/lp300/scripts/install.sh",
        "version_command": "/opt/lp300/lp300/lp300 -v",
        "pyversion_command": "/opt/lp300/lp300/lp300 -pv",
        "service_name": "lp300"
    },
    "LiftPhoenix400": {
        "prefix": "LiftPhoenix400",
        "version": r"2\.5\.3",
        "example": "LiftPhoenix400-3.9.16-2.5.3",
        "target_dir": "/opt/lp400",
        "work_dir": "/opt/lp400/lp400/scripts",
        "executable_file": "/opt/lp400/lp400/scripts/install.sh",
        "version_command": "/opt/lp400/lp400/lp400 -v",
        "pyversion_command": "/opt/lp400/lp400/lp400 -pv",
        "service_name": "lp400"
    },
    "LiftPhoenix500": {
        "prefix": "LiftPhoenix500",
        "version": r"2\.0\.1",
        "example": "LiftPhoenix500-3.9.16-2.0.1",
        "target_dir": "/opt/lp500",
        "work_dir": "/opt/lp500/lp500/scripts",
        "executable_file": "/opt/lp500/lp500/scripts/install.sh",
        "version_command": "/opt/lp500/lp500/lp500 -v",
        "pyversion_command": "/opt/lp500/lp500/lp500 -pv",
        "service_name": "lp500"
    }
}

"""通过SSH上传文件并部署到指定目录"""


def populate_ip_addresses(local_combo):
    # 获取本机IP地址
    host_name = socket.gethostname()
    local_ip = socket.gethostbyname(host_name)

    # 将本机IP添加到下拉框
    local_combo.addItem(local_ip)


def is_ip_active(ip):
    """使用socket连接检查IP是否在线"""
    try:
        # 连接到IP的端口（通常选择80或其它常用端口）
        sock = socket.create_connection((ip, 22), timeout=1)
        return True
    except (socket.timeout, socket.error):
        return False


def safe_exec(ssh_client, command, timeout=30):
    """安全执行SSH命令并自动清理资源"""
    stdin, stdout, stderr = None, None, None
    try:
        stdin, stdout, stderr = ssh_client['client'].exec_command(command, timeout=timeout)
        output = stdout.read().decode().strip()
        error = stderr.read().decode().strip()
        exit_code = stdout.channel.recv_exit_status()
        return exit_code, output, error
    finally:
        for stream in [stdin, stdout, stderr]:
            if stream:
                stream.close()


def try_connect(ssh_client, close_falg, sn, ui_components, parent_widget=None):
    close_falg['ssh_close'] = False
    """尝试连接到输入的设备IP"""
    device_ip = ui_components['first_row']['device_input'].text()  # 从输入框获取IP
    username = "long0929g"             # 替换为 SSH 用户名
    password = "Password$9026G"             # 替换为 SSH 密码
    try:
        # 创建 SSH 客户端
        ssh_client['client'] = paramiko.SSHClient()
        ssh_client['client'].set_missing_host_key_policy(paramiko.AutoAddPolicy())  # 自动添加主机密钥

        # 连接到设备
        ssh_client['client'].connect(device_ip, username=username, password=password, timeout=5)

        # 获取文件内容
        exit_code, output, error = safe_exec(ssh_client, 'cat /etc/sn')  # 执行获取文件内容的命令
        sn['value'] = output  # 读取命令输出并解码

        # 检查 SN 码是否有效
        if not sn['value']:
            logger.error("文件内容无效, 获取的序列号内容为空.")
            QMessageBox.warning(parent_widget, "文件内容无效", "获取的序列号内容为空。", QMessageBox.Ok)
            return  # 直接返回

        # 检查 SN 码长度是否正确（假设标准 SN 码是 "SFT1230110009"）
        expected_sn_length = len("SFT1230110009")  # 标准 SN 码长度
        if len(sn['value']) != expected_sn_length:
            logger.error(f"SN 码错误: 长度不符合要求（当前长度: {len(sn['value'])}，预期长度: {expected_sn_length}）")
            QMessageBox.warning(parent_widget, "SN 码错误", f"SN 码长度错误，应为 {expected_sn_length} 位。", QMessageBox.Ok)
            return  # 直接返回

        # 检查 SN 码格式是否符合预期（例如必须以 "SFT" 开头）
        if not sn['value'].startswith("SFT"):
            logger.error("SN 码错误: 格式不符合要求（必须以 'SFT' 开头）")
            QMessageBox.warning(parent_widget, "SN 码错误", "SN 码格式错误，必须以 'SFT' 开头。", QMessageBox.Ok)
            return  # 直接返回

        # 如果 SN 码有效，显示到 UI
        ui_components['second_row']['sn_display'].setText(sn['value'])
        # 连接成功，禁用控件
        ui_components['first_row']['local_combo'].setEnabled(False)
        ui_components['first_row']['device_input'].setEnabled(False)
        ui_components['first_row']['connect_btn'].setEnabled(False)
        ui_components['first_row']['close_btn'].setEnabled(True)

        ui_components['second_row']['sn_display'].setEnabled(True)
        ui_components['second_row']['device_type_combo'].addItems(["LMDC", "LBB400", "LBB300", "LMD6000", "LMDC-V2"])
        ui_components['second_row']['device_type_combo'].setEnabled(True)
        ui_components['second_row']['match_but'].setEnabled(True)

        # 显示连接成功的标签
        success_label = QLabel("✅ 设备连接成功！")
        success_label.setStyleSheet("color: green; font-weight: bold; font-size: 18px;")
        ui_components['seventh_row']['content_layout'].addWidget(success_label)

    except paramiko.SSHException as e:
        logger.error(f"连接失败: SSH 连接异常: {str(e)}")
        QMessageBox.critical(parent_widget, "连接失败", f"SSH 连接异常: {str(e)}", QMessageBox.Ok)
    except Exception as e:
        logger.error("连接失败", f"无法连接到设备 IP {device_ip}，错误: {str(e)}")
        QMessageBox.critical(parent_widget, "连接失败", f"无法连接到设备 IP {device_ip}，错误: {str(e)}", QMessageBox.Ok)


def try_close(ssh_client, close_falg, mode_value, ui_components):
    """处理断开连接"""
    if ssh_client['client']:
        ssh_client['client'].close()  # 关闭 SSH 连接
        ssh_client['client'] = None
        ui_components['first_row']['local_combo'].setEnabled(True)
        ui_components['first_row']['device_input'].setEnabled(True)
        ui_components['first_row']['connect_btn'].setEnabled(True)
        ui_components['first_row']['close_btn'].setEnabled(False)  # 禁用Close按钮
        close_falg['ssh_close'] = True

        ui_components['second_row']['device_type_combo'].setEnabled(False)
        ui_components['second_row']['device_type_combo'].clear()
        ui_components['second_row']['sn_display'].setEnabled(False)
        ui_components['second_row']['sn_display'].clear()
        ui_components['second_row']['match_but'].setEnabled(False)

        mode_value['is_init_mode'] = False
        ui_components['third_row']['init_but'].setEnabled(False)
        ui_components['third_row']['ota_but'].setEnabled(False)
        ui_components['third_row']['switch_but'].setEnabled(False)
        ui_components['third_row']['mode_switch_but'].setEnabled(False)

        ui_components['fourth_row']['st_type_combo'].setEnabled(False)
        ui_components['fourth_row']['st_type_combo'].clear()
        ui_components['fourth_row']['upload_label_combo'].setEnabled(False)
        ui_components['fourth_row']['upload_label_combo'].clear()
        mode_value['upload_label_combo_flag'] = False
        ui_components['fifth_row']['get_version_but'].setEnabled(False)
        ui_components['sixth_row']['S3_Version_combo'].setVisible(False)
        ui_components['sixth_row']['S3_Version_combo'].clear()

        ui_components['fifth_row']['csv_display'].clear()
        ui_components['sixth_row']['init_Version_label'].setVisible(True)
        ui_components['sixth_row']['ota_Version_label'].setVisible(False)
        ui_components['sixth_row']['local_version_edit'].clear()
        ui_components['sixth_row']['local_version_edit'].setVisible(True)
        ui_components['sixth_row']['browse_button'].setVisible(True)
        ui_components['sixth_row']['browse_button'].setEnabled(False)
        ui_components['sixth_row']['switch_Version_label'].setVisible(False)
        ui_components['sixth_row']['start_button'].setEnabled(False)

        ui_components['last_layout']['log_st_type_combo'].clear()
        ui_components['last_layout']['log_st_type_combo'].setEnabled(False)
        ui_components['last_layout']['log_st_type_combo'].setEditable(False)  # 确保不可编辑
        ui_components['last_layout']['Download_label_combo'].setEnabled(False)
        ui_components['last_layout']['down_button'].setEnabled(False)

        # 移除标签
        layout = ui_components['seventh_row']['content_layout']
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()  # 删除所有控件，无论类型

        # 显示连接成功的标签
        success_label = QLabel("✅ 设备断开成功！")
        success_label.setStyleSheet("color: green; font-weight: bold; font-size: 18px;")
        ui_components['seventh_row']['content_layout'].addWidget(success_label)


def match_sn(close_falg, sn, ui_components, parent_widget=None):
    """根据sn的第10个字符与设备类型进行匹配"""
    # 获取SN的第10个字符
    sn_element = sn['value'][9] if len(sn['value']) >= 10 else None  # 获取第10个字符（索引9）
    device_type = ui_components['second_row']['device_type_combo'].currentText()  # 获取设备类型

    # 定义匹配规则
    match_dict = {
        '0': ['LMDC', 'LMDC-V2'],
        '1': ['LMD6000'],
        '2': ['LBB300'],
        '7': ['LBB400']
    }

    # 检查匹配
    if sn_element in match_dict:
        if device_type in match_dict[sn_element]:
            # 显示连接成功的标签
            success_label = QLabel("✅ 设备SN匹配成功！")
            success_label.setStyleSheet("color: green; font-weight: bold; font-size: 18px;")
            ui_components['seventh_row']['content_layout'].addWidget(success_label)

            QMessageBox.information(parent_widget, "匹配成功",
                                    f"设备类型 {device_type} 与 SN {sn['value']} 匹配成功！", QMessageBox.Ok)
            # 根据设备类型添加新选项
            ui_components['last_layout']['log_st_type_combo'].clear()
            ui_components['last_layout']['Download_label_combo'].setEnabled(True)
            ui_components['last_layout']['down_button'].setEnabled(True)
            if device_type in ["LMDC", "LMDC-V2"]:
                ui_components['last_layout']['log_st_type_combo'].addItem("LiftBennu100")
            elif device_type in ["LBB400", "LBB300"]:
                ui_components['last_layout']['log_st_type_combo'].addItems(["LiftPhoenix300-v2", "LiftPhoenix400", "LiftPhoenix500"])
            elif device_type == "LMD6000":
                ui_components['last_layout']['log_st_type_combo'].addItem("LMD-TSS")
            # 启用下拉框并确保可操作
            ui_components['last_layout']['log_st_type_combo'].setEnabled(True)
            ui_components['last_layout']['log_st_type_combo'].setEditable(False)  # 确保不可编辑

            # 禁用下拉框和按钮
            ui_components['second_row']['device_type_combo'].setEnabled(False)
            ui_components['second_row']['match_but'].setEnabled(False)
            ui_components['second_row']['reset_but'].setEnabled(True)
            ui_components['third_row']['init_but'].setEnabled(True)
            ui_components['third_row']['ota_but'].setEnabled(True)
            ui_components['third_row']['switch_but'].setEnabled(True)
            close_falg['sn_close'] = False
        else:
            logger.error(f"匹配失败：设备类型 {device_type} 与 SN {sn['value']} 不匹配！")
            QMessageBox.warning(parent_widget, "匹配失败",
                                f"设备类型 {device_type} 与 SN {sn['value']} 不匹配！", QMessageBox.Ok)
            return
    else:
        logger.error("匹配失败：SN 的第12个字符不在匹配规则内！")
        QMessageBox.warning(parent_widget, "匹配失败", "SN 的第12个字符不在匹配规则内！", QMessageBox.Ok)
        return


def sn_reset(close_falg, mode_value, ui_components):
    close_falg['sn_close'] = True
    ui_components['second_row']['device_type_combo'].setEnabled(True)
    ui_components['second_row']['match_but'].setEnabled(True)
    ui_components['second_row']['reset_but'].setEnabled(False)

    mode_value['is_init_mode'] = False
    ui_components['third_row']['init_but'].setEnabled(False)
    ui_components['third_row']['ota_but'].setEnabled(False)
    ui_components['third_row']['switch_but'].setEnabled(False)
    ui_components['third_row']['mode_switch_but'].setEnabled(False)

    ui_components['fourth_row']['st_type_combo'].setEnabled(False)
    ui_components['fourth_row']['st_type_combo'].clear()
    ui_components['fourth_row']['upload_label_combo'].setEnabled(False)
    ui_components['fourth_row']['upload_label_combo'].clear()
    mode_value['upload_label_combo_flag'] = False
    ui_components['fifth_row']['get_version_but'].setEnabled(False)
    ui_components['sixth_row']['S3_Version_combo'].setVisible(False)
    ui_components['sixth_row']['S3_Version_combo'].clear()

    ui_components['fifth_row']['csv_display'].clear()
    ui_components['sixth_row']['init_Version_label'].setVisible(True)
    ui_components['sixth_row']['ota_Version_label'].setVisible(False)
    ui_components['sixth_row']['local_version_edit'].clear()
    ui_components['sixth_row']['local_version_edit'].setVisible(True)
    ui_components['sixth_row']['browse_button'].setVisible(True)
    ui_components['sixth_row']['browse_button'].setEnabled(False)
    ui_components['sixth_row']['switch_Version_label'].setVisible(False)
    ui_components['sixth_row']['start_button'].setEnabled(False)

    ui_components['last_layout']['log_st_type_combo'].clear()
    ui_components['last_layout']['log_st_type_combo'].setEnabled(False)
    ui_components['last_layout']['log_st_type_combo'].setEditable(False)  # 确保不可编辑
    ui_components['last_layout']['Download_label_combo'].setEnabled(False)
    ui_components['last_layout']['down_button'].setEnabled(False)

    # 移除标签
    layout = ui_components['seventh_row']['content_layout']
    while layout.count():
        child = layout.takeAt(0)
        if child.widget():
            child.widget().deleteLater()  # 删除所有控件，无论类型


# 定义软件更新函数
def update_st_type_combo(t, sn, mode_value, close_falg, ui_components, shadow_message):
    if t == 0:
        ui_components['third_row']['ota_but'].setEnabled(False)
        ui_components['third_row']['switch_but'].setEnabled(False)
        ui_components['fifth_row']['get_version_but'].setEnabled(False)
        ui_components['sixth_row']['ota_Version_label'].setVisible(False)
        ui_components['sixth_row']['switch_Version_label'].setVisible(False)
        ui_components['sixth_row']['init_Version_label'].setVisible(True)
        # ui_components['sixth_row']['browse_button'].setEnabled(True)
        ui_components['sixth_row']['start_button'].setEnabled(False)
        mode_value['is_init_mode'] = True
        mode_value['mode'] = "INIT"
        # 显示成功的标签
        success_label = QLabel("✅ 设备进入INIT模式！")

    elif t == 1:
        ui_components['third_row']['init_but'].setEnabled(False)
        ui_components['third_row']['switch_but'].setEnabled(False)
        ui_components['sixth_row']['ota_Version_label'].setVisible(True)
        ui_components['sixth_row']['switch_Version_label'].setVisible(False)
        ui_components['sixth_row']['init_Version_label'].setVisible(False)
        # ui_components['fifth_row']['get_version_but'].setEnabled(True)
        ui_components['sixth_row']['start_button'].setEnabled(False)
        mode_value['is_init_mode'] = False
        mode_value['mode'] = "OTA"
        # 显示成功的标签
        success_label = QLabel("✅ 设备进入OTA模式！")

    elif t == 2:
        ui_components['third_row']['ota_but'].setEnabled(False)
        ui_components['third_row']['init_but'].setEnabled(False)
        ui_components['sixth_row']['ota_Version_label'].setVisible(False)
        ui_components['sixth_row']['switch_Version_label'].setVisible(True)
        ui_components['sixth_row']['init_Version_label'].setVisible(False)
        ui_components['sixth_row']['start_button'].setEnabled(False)
        mode_value['is_init_mode'] = False
        mode_value['mode'] = "SWITCH"
        # 显示成功的标签
        success_label = QLabel("✅ 设备进入SWITCH模式！")

    success_label.setStyleSheet("color: green; font-weight: bold; font-size: 18px;")
    ui_components['seventh_row']['content_layout'].addWidget(success_label)

    ui_components['third_row']['mode_switch_but'].setEnabled(True)
    mode_value['switch_mode_flag'] = False
    ui_components['fourth_row']['st_type_combo'].setEnabled(True)  # 初始化为禁用状态

    ui_components['fourth_row']['upload_label_combo'].setEnabled(True)
    device_type = ui_components['second_row']['device_type_combo'].currentText()
    ui_components['fourth_row']['st_type_combo'].clear()  # 清空原有选项

    # 创建并显示独立对话框
    device_type = ui_components['second_row']['device_type_combo'].currentText()  # 获取设备类型
    if device_type != 'LMD6000':
        image_dialog = ImageDialog(device_type, mode_value, sn)
        # 显示对话框并处理返回值
        if image_dialog.exec_() == QDialog.Accepted:  # 用户点击了"确定"
            shadow_message['value'] = image_dialog.get_result()  # 获取对话框返回的数据

            # 检查是否成功获取到shadow值
            if not shadow_message['value']:
                # 显示警告提示框
                warning_box = QMessageBox()
                warning_box.setIcon(QMessageBox.Warning)
                warning_box.setWindowTitle("警告")
                warning_box.setText("请先配置正确的shadow！")
                warning_box.setStandardButtons(QMessageBox.Ok)
                warning_box.exec_()
                logger.debug("未获取到有效的shadow配置")
                return
            else:
                # 显示连接成功的标签
                success_label = QLabel("✅ 成功保存shadow！")
                success_label.setStyleSheet("color: green; font-weight: bold; font-size: 18px;")
                ui_components['seventh_row']['content_layout'].addWidget(success_label)
                # print("接收到的数据:", shadow_message['value'])
                ui_components['fifth_row']['get_version_but'].setEnabled(True)
        else:  # 用户点击了"取消"
            # 显示警告提示框
            warning_box = QMessageBox()
            warning_box.setIcon(QMessageBox.Warning)
            warning_box.setWindowTitle("警告")
            warning_box.setText("请先配置正确的shadow！")
            warning_box.setStandardButtons(QMessageBox.Ok)
            warning_box.exec_()
            logger.debug("未获取到有效的shadow配置")
            return
            # logger.debug("用户取消了操作")

    # 根据设备类型添加新选项
    if device_type in ["LMDC", "LMDC-V2"]:
        ui_components['fourth_row']['st_type_combo'].addItem("LiftBennu100")
    elif device_type in ["LBB400", "LBB300"]:
        ui_components['fourth_row']['st_type_combo'].addItems(["LiftPhoenix300-v2", "LiftPhoenix400", "LiftPhoenix500"])
    elif device_type == "LMD6000":
        ui_components['fourth_row']['st_type_combo'].addItem("LMD-TSS")

    if not mode_value['upload_label_combo_flag']:
        ui_components['fourth_row']['upload_label_combo'].setCurrentIndex(0)  # 默认选中 "Local"
        update_upload_ui(mode_value, close_falg, ui_components)
        mode_value['upload_label_combo_flag'] = True


# 添加切换mode按钮的方法
def switch_mode_buttons(mode_value, ui_components):
    """启用所有模式切换按钮"""
    ui_components['third_row']['switch_but'].setEnabled(True)
    ui_components['third_row']['ota_but'].setEnabled(True)
    ui_components['third_row']['init_but'].setEnabled(True)
    mode_value['switch_mode_flag'] = True

    # 同时禁用CLOSE按钮（可选）
    ui_components['third_row']['mode_switch_but'].setEnabled(False)

    # 重置其他相关状态（根据需求可选）
    mode_value['is_init_mode'] = False
    ui_components['fourth_row']['st_type_combo'].setEnabled(False)
    ui_components['fourth_row']['st_type_combo'].clear()
    ui_components['fourth_row']['upload_label_combo'].setEnabled(False)
    ui_components['fourth_row']['upload_label_combo'].clear()
    mode_value['upload_label_combo_flag'] = False

    ui_components['fifth_row']['csv_display'].clear()
    ui_components['fifth_row']['get_version_but'].setEnabled(False)
    ui_components['sixth_row']['S3_Version_combo'].setVisible(False)
    ui_components['sixth_row']['S3_Version_combo'].clear()

    ui_components['sixth_row']['local_version_edit'].clear()
    ui_components['sixth_row']['local_version_edit'].setVisible(True)
    ui_components['sixth_row']['browse_button'].setVisible(True)
    ui_components['sixth_row']['browse_button'].setEnabled(False)
    ui_components['sixth_row']['start_button'].setEnabled(False)
    ui_components['sixth_row']['init_Version_label'].setVisible(True)
    ui_components['sixth_row']['ota_Version_label'].setVisible(False)
    ui_components['sixth_row']['switch_Version_label'].setVisible(False)


def update_upload_ui(mode_value, close_falg, ui_components):
    combo = ui_components['fourth_row']['upload_label_combo']
    device_type = ui_components['second_row']['device_type_combo'].currentText()
    # 初始化上传模式选项
    if combo.count() == 0 and not (close_falg['ssh_close'] or close_falg['sn_close']) and not mode_value['switch_mode_flag']:
        if mode_value['is_init_mode'] or device_type == 'LMD6000':
            combo.addItems(["Local"])  # INIT模式只添加Local选项
        else:
            combo.addItems(["Local", "S3"])  # 非INIT模式添加Local和S3选项
    """根据上传模式更新UI显示"""
    # 首先隐藏所有相关控件
    ui_components['fifth_row']['csv_display'].clear()
    ui_components['sixth_row']['local_version_edit'].setVisible(False)
    ui_components['sixth_row']['browse_button'].setVisible(False)
    ui_components['sixth_row']['S3_Version_combo'].setVisible(False)
    ui_components['sixth_row']['browse_button'].setEnabled(False)

    # 获取当前选择的模式
    mode = combo.currentText()

    if mode == "Local":
        # Local模式：显示文件选择相关控件和Start按钮
        ui_components['sixth_row']['local_version_edit'].setVisible(True)
        ui_components['sixth_row']['browse_button'].setVisible(True)
        ui_components['fifth_row']['get_version_but'].setEnabled(True)
        ui_components['sixth_row']['start_button'].setEnabled(False)
    elif mode == "S3":
        # S3模式：只显示Start按钮和版本相关控件
        ui_components['sixth_row']['S3_Version_combo'].setVisible(True)
        ui_components['sixth_row']['S3_Version_combo'].clear()
        ui_components['fifth_row']['get_version_but'].setEnabled(True)
        ui_components['sixth_row']['start_button'].setEnabled(False)

    # 获取当前软件类型
    software_type = ui_components['fourth_row']['st_type_combo'].currentText()
    # 如果当前是INIT模式且软件类型有效
    if mode_value['is_init_mode'] and software_type in validation_rules:
        # 从validation_rules中提取版本号（去除正则转义字符）
        raw_version = validation_rules[software_type]["version"]
        clean_version = raw_version.replace(r'\.', '.').replace(r'\-', '-')
        if mode == "Local":
            # 填充到Version_edit控件
            # ui_components['sixth_row']['local_version_edit'].setText(clean_version)
            ui_components['sixth_row']['local_version_edit'].setReadOnly(True)
            ui_components['fifth_row']['get_version_but'].setEnabled(False)
            ui_components['sixth_row']['browse_button'].setEnabled(True)

        if mode == "S3":
            # 填充到S3_Version_combo控件
            ui_components['sixth_row']['S3_Version_combo'].clear()  # 先清空现有选项
            ui_components['sixth_row']['S3_Version_combo'].addItem(clean_version)  # 添加版本作为唯一选项
            ui_components['sixth_row']['S3_Version_combo'].setCurrentIndex(0)  # 选中第一个（也是唯一一个）选项
            ui_components['sixth_row']['S3_Version_combo'].setEnabled(False)  # 禁用下拉框使其只读
            ui_components['fifth_row']['get_version_but'].setEnabled(False)


def validate_init_file(filename, rule):
    """
    验证文件名格式要求：
    1. 前缀必须匹配 rule['prefix']
    2. 版本号分段结构必须与 rule['example'] 一致
    3. 扩展名必须是 .tar.gz 或 .zip
    """
    # # 检查扩展名
    # if not (filename.endswith('.tar.gz') or filename.endswith('.zip')):
    #     return "只支持 .tar.gz 或 .zip 格式的文件"

    # 提取文件名主干（去掉扩展名）
    basename = filename.split('.')[0]
    example_basename = rule['example'].split('.')[0]

    # 检查前缀
    if not basename.startswith(rule['prefix'] + '-'):
        return f"文件名必须以 '{rule['prefix']}-' 开头"

    # 提取版本号部分（去掉前缀）
    version_part = basename[len(rule['prefix']) + 1:]
    example_version = example_basename[len(rule['prefix']) + 1:]

    # 验证版本号分段结构
    example_segments = example_version.split('-')
    input_segments = version_part.split('-')

    # 检查分段数量是否一致
    if len(input_segments) != len(example_segments):
        return (f"版本号分段数量错误\n"
                f"当前: {len(input_segments)}段 ({version_part})\n"
                f"要求: {len(example_segments)}段 (如 {example_version})")

    # 检查每段格式是否为 X.X.X（数字+点）
    for i, segment in enumerate(input_segments):
        if not re.fullmatch(r'^\d+(\.\d+)*$', segment):
            return f"版本号段 '{segment}' 格式无效（应为数字和点，如 3.9.16)"

        # 可选：检查每段的点数是否与example一致（如3.9.16是2个点）
        if segment.count('.') != example_segments[i].count('.'):
            return (f"版本号段 '{segment}' 点数不符\n"
                    f"当前: {segment.count('.')}个点\n"
                    f"要求: {example_segments[i].count('.')}个点 (如 {example_segments[i]})")

    return None  # 验证通过


def upload_file_via_ssh(ssh, mode_value, ui_components, parent_widget=None):
    # ui_components['third_row']['mode_switch_but'].setEnabled(False)

    # 1. 获取并标准化本地路径（关键修复）
    raw_path = ui_components['sixth_row']['local_version_edit'].text().strip()
    local_file_path = os.path.normpath(raw_path)  # 转换路径分隔符

    if not os.path.exists(local_file_path):
        raise FileNotFoundError(
            f"文件不存在或路径无效:\n{local_file_path}\n"
            f"请检查:\n"
            f"1. 文件是否被移动或删除\n"
            f"2. 路径是否包含中文/特殊字符"
        )
    if not local_file_path:
        logger.error("请先选择要上传的文件")
        QMessageBox.warning(parent_widget, "警告", "请先选择要上传的文件！")
        # ui_components['third_row']['mode_switch_but'].setEnabled(True)
        return

    filename = os.path.basename(local_file_path)
    # logger.error(f'{filename}')
    software_type = ui_components['fourth_row']['st_type_combo'].currentText()

    rule = validation_rules[software_type]

    try:
        # 1. 上传文件到临时目录
        temp_path = f"/home/long0929g/{filename}"
        sftp = ssh['client'].open_sftp()
        sftp.put(local_file_path, temp_path)

        # 2. 部署到目标目录
        target_dir = rule["target_dir"]

        # 构建部署命令
        deploy_cmd = f"""
            # 检查并创建目标目录
            if [ ! -d "{target_dir}" ]; then
                sudo mkdir -p "{target_dir}"
                sudo chown lmahdb:lmahdb "{target_dir}"
            fi;

            # 检查并删除前缀匹配的文件
            if [ -n "{rule['prefix']}" ]; then
                sudo find "{target_dir}" -type f -name "{rule['prefix']}*" -exec rm -f {{}} \\;
            fi;

            # 复制文件到目标目录
            sudo cp -f "{temp_path}" "{target_dir}/"

            # 在目标目录中解压文件
            sudo tar -xvf "{target_dir}/{filename}" -C "{target_dir}"

            # 删除压缩包（保留解压后的文件）
            sudo rm -f "{target_dir}/{filename}"

            # 设置权限
            sudo chown -R lmahdb:lmahdb "{target_dir}"
        """

        exit_code, output, error_msg = safe_exec(ssh, deploy_cmd)

        if error_msg:
            logger.error(f"部署失败: {error_msg}")
            # ui_components['third_row']['mode_switch_but'].setEnabled(True)
            raise Exception(f"部署失败: {error_msg}")

        # 3. 清理临时文件
        sftp.remove(temp_path)

        QMessageBox.information(
            parent_widget,
            "部署成功",
            f"文件已成功部署到: {target_dir}\n"
            f"软件类型: {software_type}\n"
            f"文件名: {filename}\n"
            f"目标路径: {target_dir}/{filename}"
        )
        ui_components['sixth_row']['start_button'].setEnabled(True)
        success_label = QLabel("✅ 上传文件成功！")
        success_label.setStyleSheet("color: green; font-weight: bold; font-size: 18px;")
        ui_components['seventh_row']['content_layout'].addWidget(success_label)

    except Exception as e:
        logger.error(f"请检查SSH连接和权限配置{str(e)}")
        QMessageBox.critical(
            parent_widget,
            "错误",
            f"操作失败: {str(e)}\n"
            f"请检查SSH连接和权限配置"
        )
        # ui_components['third_row']['mode_switch_but'].setEnabled(True)
        return
    finally:
        if 'sftp' in locals():
            sftp.close()


# 添加文件浏览方法
def browse_file(ssh, mode_value, ui_components, parent_widget=None):
    # """严格验证初始化软件文件的浏览方法"""

    # 1. 获取软件类型并验证
    software_type = ui_components['fourth_row']['st_type_combo'].currentText()
    # software_type = "LiftBennu100"
    if software_type not in validation_rules:
        QMessageBox.warning(
            parent_widget,
            "无效软件类型",
            f"未定义的软件类型: {software_type}",
            QMessageBox.Ok
        )
        return

    rule = validation_rules[software_type]

    # 2. 显示上传提示（含示例格式）
    QMessageBox.information(
        parent_widget,
        "上传初始化软件",
        f"请上传{software_type}的初始化软件\n"
        f"格式要求: {rule['prefix']}-<版本号>\n"
        f"示例: {rule['example']}\n"
        f"支持格式: .tar.gz 或 .zip",
        QMessageBox.Ok
    )

    # 3. 文件选择对话框
    file_path, _ = QFileDialog.getOpenFileName(
        parent_widget,
        f"选择{software_type}初始化文件",
        "",
        "所有文件 (*.*)"
    )

    if not file_path:
        return

    # 4. 严格文件验证
    file_name = os.path.basename(file_path)
    error_msg = validate_init_file(file_name, rule)

    if error_msg:
        QMessageBox.critical(
            parent_widget,
            "文件验证失败",
            f"{error_msg}\n"
            f"要求格式: {rule['prefix']}-<版本号>\n"
            f"示例: {rule['example']}",
            QMessageBox.Ok
        )
        return

    # 6. 验证通过后更新UI
    ui_components['sixth_row']['local_version_edit'].setText(file_path)
    logger.info(f"已验证的初始化文件: {file_name}")
    upload_file_via_ssh(ssh, mode_value, ui_components, parent_widget=None)


def execute_ssh_command(ssh, command):
    """执行SSH命令并返回输出"""
    try:
        stdin, stdout, stderr = ssh['client'].exec_command(command, timeout=3)
        error = stderr.read().decode().strip()
        if error:
            logger.error(f"命令执行错误: {command} -> {error}")
            return None
        return stdout.read().decode().strip()
    except Exception as e:
        logger.error(f"SSH命令执行失败: {command} -> {str(e)}")
        return None


# 添加获取版本的方法
def get_software_version(mode_value, ssh, sn, ui_components, parent_widget=None):
    upload_type = ui_components['fourth_row']['upload_label_combo'].currentText()
    software_type = ui_components['fourth_row']['st_type_combo'].currentText()
    if mode_value['mode'] == "INIT":
        return
    if not software_type:  # 空选择
        return

    rule = validation_rules[software_type]
    ui_components['fifth_row']['csv_display'].clear()

    try:
        # 3. 特殊处理LMD-TSS（版本文件）
        if software_type == "LMD-TSS":
            QMessageBox.warning(parent_widget, "警告", f"目前不支持 {software_type} 操作")
            return
            # version_file_path = f"{rule['version_path']}/{rule['version_file']}"
            # stdin, stdout, stderr = ssh['client'].exec_command(f"cat {version_file_path}")
            # version_content = stdout.read().decode().strip()

            # try:
            #     version_data = json.loads(version_content)
            #     version_str = f"{rule['prefix']}-{version_data.get('TMSVersion','0.0.0')}-" \
            #                   f"{version_data.get('SmarthubVersion','0.0.0')}-" \
            #                   f"{version_data.get('ScannerVersion','0.0.0')}"
            #     """更新UI显示版本信息"""
            #     ui_components['fifth_row']['csv_display'].setText(version_str)
            #     ui_components['sixth_row']['browse_button'].setEnabled(True)
            #     # ui_components['sixth_row']['start_button'].setEnabled(True)
            #     ui_components['fifth_row']['get_version_but'].setEnabled(False)
            # except json.JSONDecodeError:
            #     ui_components['fifth_row']['csv_display'].setText("版本文件格式错误")
            #     return

        # 4. 处理其他软件类型（命令获取版本）
        else:
            # 获取主版本
            version_cmd = f"{rule['version_command']}"
            pyversion_cmd = "python3 --version"
            # pyversion_cmd = f"{rule['pyversion_command']}"

            # 执行版本命令
            version_output = execute_ssh_command(ssh, version_cmd)
            if not version_output:
                ui_components['fifth_row']['csv_display'].setText("获取主版本失败")
                return

            # 执行Python版本命令
            py_version_output = execute_ssh_command(ssh, pyversion_cmd)
            if not py_version_output:
                ui_components['fifth_row']['csv_display'].setText("获取Python版本失败")
                return

            # 拼接版本字符串 (prefix-主版本-Python版本)
            py_version = py_version_output.split()[1]
            version_str = f"{rule['prefix']}-{py_version}-{version_output.strip()}"
            if upload_type == "Local":
                """更新UI显示版本信息"""
                ui_components['fifth_row']['csv_display'].setText(version_str)
                ui_components['sixth_row']['browse_button'].setEnabled(True)
                # ui_components['sixth_row']['start_button'].setEnabled(True)
                ui_components['fifth_row']['get_version_but'].setEnabled(False)

                success_label = QLabel("✅ 获取版本成功！")
                success_label.setStyleSheet("color: green; font-weight: bold; font-size: 18px;")
                ui_components['seventh_row']['content_layout'].addWidget(success_label)
            if upload_type == "S3":
                ui_components['fifth_row']['csv_display'].setText(version_str)
                # 填充S3版本列表
                if populate_s3_versions(ui_components, py_version):
                    # 设置到显示控件
                    ui_components['fifth_row']['get_version_but'].setEnabled(False)
                    ui_components['sixth_row']['start_button'].setEnabled(True)
                    ui_components['sixth_row']['S3_Version_combo'].setEnabled(True)
                else:
                    return

                success_label = QLabel("✅ 获取版本成功！")
                success_label.setStyleSheet("color: green; font-weight: bold; font-size: 18px;")
                ui_components['seventh_row']['content_layout'].addWidget(success_label)

    except Exception as e:
        logger.error(f"获取版本失败: {str(e)}")
        ui_components['fifth_row']['csv_display'].setText(f"版本获取错误: {str(e)}")


def extract_version_info(software_type, s3_response):
    """
    从S3响应中提取并格式化版本信息
    参数:
        software_type: 软件类型 (LMD-TSS, LiftBennu100, LiftPhoenix300-v2, LiftPhoenix500)
        s3_response: S3 list_objects_v2 的响应
    返回:
        版本列表，格式根据软件类型不同:
        - LMD-TSS: ['lmd-tss-2.5.2-2.4.1-2.2.0', ...]
        - LiftBennu100: ['LiftBennu100-3.0.3', ...]
        - LiftPhoenix300-v2: ['LiftPhoenix300-V2-2.0.1', ...]
        - LiftPhoenix500: ['LiftPhoenix500-3.9.16', ...]
    """
    version_list = []

    if not s3_response or 'Contents' not in s3_response:
        return version_list

    for obj in s3_response['Contents']:
        key = obj['Key']
        # print(s3_response['Contents'])

        # 根据软件类型采用不同的提取逻辑
        if software_type == 'LMD-TSS':
            if key.startswith('lmd-tss-'):
                parts = key.split('-')
                if len(parts) >= 6:
                    version = '-'.join(parts[:6])  # lmd-tss-2.5.2-2.4.1-2.2.0
                    version_list.append(version)

        elif software_type == 'LiftBennu100':
            if 'LiftBennu100/' in key and key.endswith('.tar.gz'):
                # 提取类似 embedded-software/LiftBennu100/LiftBennu100-3.0.3.tar.gz 中的 LiftBennu100-3.0.3
                filename = key.split('/')[-1]  # LiftBennu100-3.0.3.tar.gz
                version = filename.rsplit('.', 2)[0]  # 从右边分割两次，取第一部分（去掉最后两个点及之后内容）
                version_list.append(version)

        elif software_type == 'LiftPhoenix300-v2':
            if 'LiftPhoenix300/' in key and (key.endswith('.tar.gz') or key.endswith('.zip')):
                # 提取类似 embedded-software/LiftPhoenix300/LiftPhoenix300-V2-2.0.1.tar.gz 中的 LiftPhoenix300-V2-2.0.1
                filename = key.split('/')[-1]  # LiftPhoenix300-V2-2.0.1.tar.gz
                version = filename.rsplit('.', 1)[0]  # 从右边分割一次，取第一部分（去掉最后一个点及之后内容）
                version_list.append(version)

        elif software_type == 'LiftPhoenix500':
            if 'LiftPhoenix500/' in key and (key.endswith('.tar.gz') or key.endswith('.zip')):
                # 提取类似 embedded-software/LiftPhoenix500/LiftPhoenix500-3.9.16-0.0.0-beta.3.tar.gz 中的 LiftPhoenix500-3.9.16-0.0.0-beta.3
                filename = key.split('/')[-1]  # LiftPhoenix500-3.9.16-0.0.0-beta.3.tar.gz
                version = filename.rsplit('.', 1)[0]  # 从右边分割一次，取第一部分（去掉最后一个点及之后内容）
                version_list.append(version)

    # 去重并排序
    version_list = sorted(list(set(version_list)), reverse=True)
    return version_list


def download_via_s3(software_type, download_path):
    """通过S3下载日志文件"""
    print(f"通过S3下载 {software_type} 的日志到 {download_path}")
    # 这里可以添加实际的S3下载代码
    # 需要根据你的S3配置实现


def on_versions_loaded(success, result):
    """版本加载完成后的回调"""
    if success:
        print(f"成功加载{len(result)}个版本")
    else:
        logger.error(f"加载失败: {result}")
        return
        # print(f"加载失败: {result}")


# 从S3桶中获取软件版本并填充下拉框
def populate_s3_versions(ui_components, py_version, parent_widget=None):
    """从S3桶中获取软件版本并填充下拉框"""
    # 清空当前下拉框内容
    ui_components['sixth_row']['S3_Version_combo'].clear()
    # 获取当前选择的软件类型
    software_type = ui_components['fourth_row']['st_type_combo'].currentText()

    try:
        if software_type == 'LMD-TSS':
            QMessageBox.warning(parent_widget, "警告", f"不支持加载 {software_type} 的版本信息")
            return
        else:
            s3 = boto3.client(
                's3',
                aws_access_key_id=config_in.CONFIG_AWS_KEY,
                aws_secret_access_key=config_in.CONFIG_AWS_SECRET_KEY,
                region_name=config_in.CONFIG_AWS_S3_OTA_BUCKET_REGION  # 你的S3桶所在区域
            )

        # 根据软件类型确定S3路径
        s3_paths = {
            'LiftBennu100': 'embedded-software/LiftBennu100/',
            'LiftPhoenix300-v2': 'embedded-software/LiftPhoenix300/',
            'LiftPhoenix500': 'embedded-software/LiftPhoenix500/',
            'LMD-TSS': 'lmd-tss/'
        }

        # 特殊处理：没有可用版本的软件类型
        if software_type == 'LiftPhoenix400':
            logger.error("LiftPhoenix400目前没有可用软件版本")
            ui_components['fourth_row']['st_type_combo'].addItem("目前没有可用软件版本")
            QMessageBox.information(parent_widget, "提示", "LiftPhoenix400目前没有可用软件版本")
            return False

        # 检查软件类型是否在支持列表中
        if software_type not in s3_paths:
            logger.error(f"不支持加载 {software_type} 的版本信息")
            ui_components['fourth_row']['st_type_combo'].addItem("不支持的软件类型")
            QMessageBox.warning(parent_widget, "警告", f"不支持加载 {software_type} 的版本信息")
            return False

        # 构建S3路径参数
        if software_type == 'LMD-TSS':
            QMessageBox.warning(parent_widget, "警告", f"不支持加载 {software_type} 的版本信息")
            # response = s3.list_objects_v2(Bucket='lmd-tss')
        else:
            bucket = config_in.CONFIG_AWS_S3_OTA_BUCKET
            prefix = s3_paths[software_type]
            # 列出指定路径下的对象
            response = s3.list_objects_v2(
                Bucket=bucket,
                Prefix=prefix
            )

        # 提取并格式化版本信息
        versions = extract_version_info(software_type, response)

        # 过滤版本：只保留包含指定Python版本的软件
        filtered_versions = [v for v in versions if py_version in v]

        # 清空并填充下拉框
        ui_components['sixth_row']['S3_Version_combo'].clear()

        if filtered_versions:
            for version in filtered_versions:
                ui_components['sixth_row']['S3_Version_combo'].addItem(version)
        else:
            logger.error(f"没有找到包含Python {py_version}的软件版本")
            ui_components['sixth_row']['S3_Version_combo'].addItem(f"未找到Python {py_version}的版本")
            QMessageBox.information(parent_widget, "提示",
                                  f"没有找到包含Python {py_version}的软件版本")
            return False

    except Exception as e:
        logger.error(f"加载版本信息失败: {str(e)}")
        ui_components['sixth_row']['S3_Version_combo'].addItem("加载失败")
        QMessageBox.critical(parent_widget, "错误", f"加载版本信息失败: {str(e)}")
        return False
    
    return True


def download_via_ssh(ssh, ui_components, download_path, remote_path, dialog, parent_widget=None):
    """通过SSH下载选中的日志文件"""
    selected_files = [item.text() for item in dialog.file_list_widget.selectedItems()]

    if not selected_files:
        logger.error("请至少选择一个文件进行下载")
        QMessageBox.warning(parent_widget, "警告", "请至少选择一个文件进行下载")
        return

    try:
        sftp = ssh['client'].open_sftp()
        for filename in selected_files:
            remote_file = f"{remote_path}/{filename}"
            local_file = f"{download_path}/{filename}"
            sftp.get(remote_file, local_file)
            # print(f"已下载: {filename}")

        QMessageBox.information(parent_widget, "完成", f"已成功下载 {len(selected_files)} 个文件")
        success_label = QLabel("✅ 下载log文件成功！")
        success_label.setStyleSheet("color: green; font-weight: bold; font-size: 18px;")
        ui_components['seventh_row']['content_layout'].addWidget(success_label)

    except Exception as e:
        logger.error(f"下载失败: {str(e)}")
        QMessageBox.critical(parent_widget, "错误", f"下载失败: {str(e)}")
        return


def show_download_dialog(ssh, ui_components, parent_widget=None):
    # 获取时间范围
    start_time, end_time = TimeRangeDialog.get_time_range_from_user(parent_widget)
    if not start_time or not end_time:
        return  # 用户取消了操作

    # 验证时间范围
    if QDateTime.fromString(start_time, "yyyy-MM-dd HH:mm:ss") > QDateTime.fromString(end_time, "yyyy-MM-dd HH:mm:ss"):
        QMessageBox.warning(parent_widget, "错误", "开始时间不能晚于结束时间")
        return

    dialog = DownloadDialog()
    generated_files = []  # 用于记录生成的临时文件

    # 获取下载类型
    download_type = ui_components['last_layout']['Download_label_combo'].currentText()

    # 如果是S3下载类型，直接提示不支持并返回
    if download_type == "S3":
        logger.warning("当前不支持通过S3下载")
        QMessageBox.information(
            parent_widget,
            "功能提示",
            "目前暂不支持通过S3下载，请使用本地下载方式。",
            QMessageBox.Ok
        )
        return

    # 获取软件类型
    software_type = ui_components['last_layout']['log_st_type_combo'].currentText()
    if software_type in validation_rules:
        remote_path = validation_rules[software_type]['target_dir']

    # 定义各软件类型的日志处理命令（已修改为支持时间范围）
    commands = {
        "LiftBennu100": {
            'split_cmd': f"sudo su lmahdb -c 'cd /opt/lb100 && sudo journalctl -u lb100 --since \"{start_time}\" --until \"{end_time}\" --no-pager | split -b 5M -d - lb100_log.'",
            'list_cmd': "ls /opt/lb100/lb100_log.*",
            'cleanup_cmd': "sudo su lmahdb -c 'rm -f /opt/lb100/lb100_log.*'",
            'direct_download': False
        },
        "LiftPhoenix300-v2": {
            'split_cmd': f"sudo su lmahdb -c 'cd /opt/lp300 && sudo journalctl -u lp300 --since \"{start_time}\" --until \"{end_time}\" --no-pager | split -b 5M -d - lp300_log.'",
            'list_cmd': "ls /opt/lp300/lp300_log.*",
            'cleanup_cmd': "sudo su lmahdb -c 'rm -f /opt/lp300/lp300_log.*'",
            'direct_download': False
        },
        "LiftPhoenix400": {
            'split_cmd': f"sudo su lmahdb -c 'cd /opt/lp400 && sudo journalctl -u lp400 --since \"{start_time}\" --until \"{end_time}\" --no-pager | split -b 5M -d - lp400_log.'",
            'list_cmd': "ls /opt/lp400/lp400_log.*",
            'cleanup_cmd': "sudo su lmahdb -c 'rm -f /opt/lp400/lp400_log.*'",
            'direct_download': False
        },
        "LiftPhoenix500": {
            'split_cmd': f"sudo su lmahdb -c 'cd /opt/lp500 && sudo journalctl -u lp500 --since \"{start_time}\" --until \"{end_time}\" --no-pager | split -b 5M -d - lp500_log.'",
            'list_cmd': "ls /opt/lp500/lp500_log.*",
            'cleanup_cmd': "sudo su lmahdb -c 'rm -f /opt/lp500/lp500_log.*'",
            'direct_download': False
        },
        "LMD-TSS": {
            'list_cmd': "ls /opt/lmd-tss/log",
            'direct_download': True  # 标记为直接下载模式
        }
    }

    try:
        cmd_info = commands[software_type]

        if not cmd_info.get('direct_download', False):
            # 常规处理流程（journalctl + split）
            stdin, stdout, stderr = ssh['client'].exec_command(cmd_info['split_cmd'])
            if stderr.read():
                raise Exception(f"日志分割失败: {stderr.read().decode('utf-8')}")

        # 获取文件列表（所有类型通用）
        stdin, stdout, stderr = ssh['client'].exec_command(cmd_info['list_cmd'])
        remote_files = stdout.read().decode('utf-8').split()
        generated_files = remote_files if not cmd_info.get('direct_download', False) else []

        # 清空并填充文件列表
        dialog.file_list_widget.clear()
        for file in sorted(remote_files):
            dialog.file_list_widget.addItem(file.split('/')[-1])

    except Exception as e:
        logger.error(f"处理日志文件失败: {str(e)}")
        QMessageBox.warning(parent_widget, "错误", f"处理日志文件失败: {str(e)}")
        return

    # 执行对话框
    if dialog.exec_():
        try:
            download_path = dialog.path_display.text()
            remote_path = "/opt/lmd-tss/log" if software_type == "LMD-TSS" else remote_path

            # 执行下载
            download_via_ssh(ssh, ui_components, download_path, remote_path, dialog)

            # 仅非直接下载模式需要清理临时文件
            if generated_files and not cmd_info.get('direct_download', False):
                logger.info(f"开始清理临时文件: {generated_files}")
                stdin, stdout, stderr = ssh['client'].exec_command(cmd_info['cleanup_cmd'])
                if stderr.read():
                    logger.error(f"清理临时文件失败: {stderr.read().decode('utf-8')}")
                else:
                    logger.info("临时文件清理完成")

        except Exception as e:
            logger.error(f"下载过程中出错: {str(e)}")
            QMessageBox.warning(parent_widget, "错误", f"下载过程中出错: {str(e)}")
        finally:
            # 确保即使出错也尝试清理（仅限非直接下载模式）
            if generated_files and not cmd_info.get('direct_download', False):
                try:
                    ssh['client'].exec_command(cmd_info['cleanup_cmd'])
                except:
                    pass


# 添加证书
def attach_cert_to_existing_thing(thing_name, certificate_id):
    """
    为已存在的设备绑定证书（图片中未展示但兼容的后续操作）
    :param thing_name: 已创建的设备名称（需符合图片中的命名规则）
    :param certificate_id: 证书ID（如用户提供的4bce1a...）
    """
    iot = get_client('iot', 1)

    try:
        # 1. 验证设备存在（匹配图片中的Thing name）
        iot.describe_thing(thingName=thing_name)

        # 2. 构造证书ARN（需与图片中设备所在区域一致）
        region = iot.meta.region_name
        account_id = get_client('sts', 1).get_caller_identity()['Account']
        cert_arn = f"arn:aws:iot:{region}:{account_id}:cert/{certificate_id}"

        # 3. 验证证书存在
        iot.describe_certificate(certificateId=certificate_id)

        # 4. 执行绑定（图片流程的后续独立操作）
        iot.attach_thing_principal(
            thingName=thing_name,
            principal=cert_arn
        )
        # print(f"✅ 证书 {certificate_id} 已绑定到设备 {thing_name}")

    except iot.exceptions.ResourceNotFoundException as e:
        logger.error(f"设备或证书不存在: {str(e)}")
        # print(f"❌ 设备或证书不存在: {str(e)}")
    except iot.exceptions.InvalidRequestException as e:
        logger.error(f"设备名不符合图片规范: {str(e)}")
        # print(f"❌ 设备名不符合图片规范: {str(e)}")
    except Exception as e:
        logger.error(f"操作失败: {str(e)}")
        # print(f"❌ 操作失败: {str(e)}")
        raise


def execute_software(ui_components, software_type, ssh_client, parent_widget=None):
    """
    执行指定类型的软件程序

    参数:
        software_type: 软件类型名称
        ssh_client: SSH客户端连接
        parent_widget: 父窗口部件(用于显示消息框)

    返回:
        bool: 是否执行成功
    """
    device_type = ui_components['second_row']['device_type_combo'].currentText()
    try:
        # 检查软件类型是否在验证规则中
        if software_type not in validation_rules:
            logger.error(f"⚠️ 未知软件类型: {software_type}")
            QMessageBox.warning(
                parent_widget,
                "未知类型",
                f"未知的软件类型: {software_type}"
            )
            return False

        rule = validation_rules[software_type]

        # 构建执行命令
        exec_cmd = f"""
            sudo su lmahdb {rule['executable_file']}
        """

        # 通过SSH执行命令
        exit_code, output, error_msg = safe_exec(ssh_client, exec_cmd)
        if device_type != 'LMD6000':
            # 检查退出码为0且输出中包含"+ exit 0"
            if "+ exit 0" in error_msg:
                logger.debug(f"✅ 成功启动 {software_type} (exit code: {exit_code})")
                QMessageBox.information(
                    parent_widget,
                    "执行成功",
                    f"已成功启动 {software_type}\n输出: {error_msg}"
                )
                return True
            else:
                error_display = ""
                if exit_code != 0:
                    error_display = f"进程退出码: {exit_code}\n"
                if "+ exit 0" not in error_msg:
                    error_display += "输出中未包含'+ exit 0'成功标志\n"
                if error_msg:
                    error_display += f"错误信息: {error_msg}"

                logger.error(f" 执行 {software_type} 失败: {error_display}")
                QMessageBox.warning(
                    parent_widget,
                    "执行失败",
                    f"启动 {software_type} 失败:\n{error_display}"
                )
                return False
        else:
            return True

    except Exception as e:
        logger.error(f"执行软件时出错: {str(e)}")
        QMessageBox.critical(
            parent_widget,
            "执行错误",
            f"执行过程中发生错误:\n{str(e)}"
        )
        return False


# 检查设备是否正常运行
def check_service_active(mode_value, ssh_client, service_name, type, parent_widget=None):
    """
    检查服务是否处于active (running)状态

    参数:
        ssh_client: SSH连接对象
        service_name: 服务名称(如lb100)
        parent_widget: 父窗口对象(可选)

    返回:
        bool: True表示服务正在运行，False表示服务未运行或检查失败
    """
    try:
        # 执行精简版检查命令
        exit_code, output, error = safe_exec(ssh_client, f"systemctl is-active {service_name} 2>/dev/null")

        # 检查返回状态和输出
        if exit_code == 0:
            if type:
                if mode_value['mode'] == "INIT":
                    QMessageBox.information(parent_widget, "服务状态", f"{service_name}初始化成功", QMessageBox.Ok)
                else:
                    QMessageBox.information(parent_widget, "服务状态", f"{service_name}更新成功", QMessageBox.Ok)
            return True
        else:
            if not type:
                QMessageBox.warning(parent_widget, "服务状态", f"{service_name}服务未运行", QMessageBox.Ok)
            else:
                QMessageBox.warning(parent_widget, "服务状态", f"{service_name}服务未运行，请先启动服务", QMessageBox.Ok)
            return False

    except Exception as e:
        QMessageBox.critical(parent_widget, "检查失败", f"无法检查服务状态:\n{str(e)}", QMessageBox.Ok)
        return False


# 停止服务
def stop_service(ssh_client, service_name, parent_widget=None):
    """
    通过SSH停止指定的系统服务

    参数:
        ssh_client: 已建立的SSH连接(paramiko.SSHClient)
        service_name: 要停止的服务名称(如lb100)
        parent_widget: 父窗口对象(用于显示弹窗，可选)

    返回:
        tuple: (success: bool, message: str)
    """
    # 执行停止命令（使用sudo需要确保SSH用户有权限）
    stdin, stdout, stderr = ssh_client['client'].exec_command(
        f"sudo systemctl stop {service_name}",
        get_pty=True  # 需要PTY来执行sudo
    )

    exit_status = stdout.channel.recv_exit_status()

    # try:
    #     # 执行停止命令（使用sudo需要确保SSH用户有权限）
    #     stdin, stdout, stderr = ssh_client['client'].exec_command(
    #         f"sudo systemctl stop {service_name}",
    #         get_pty=True  # 需要PTY来执行sudo
    #     )

    #     exit_status = stdout.channel.recv_exit_status()

    #     if exit_status == 0:
    #         return True
    #     else:
    #         error_msg = stderr.read().decode('utf-8').strip()
    #         msg = f"停止服务失败: {error_msg or '未知错误'}"
    #         QMessageBox.critical(parent_widget, "操作失败", msg, QMessageBox.Ok)
    #         return False

    # except Exception as e:
    #     msg = f"停止服务时发生异常: {str(e)}"
    #     QMessageBox.critical(parent_widget, "错误", msg, QMessageBox.Ok)
    #     return False


# 创建设备，并且启动设备
def start_to_softwar(mode_value, sn, ui_components, shadow_message, ssh_client, parent_widget=None):
    certificate_id = config_in.CONFIG_CERTIFICATE_ID
    software_type = ui_components['fourth_row']['st_type_combo'].currentText()
    device_type = ui_components['second_row']['device_type_combo'].currentText()
    upload_type = ui_components['fourth_row']['upload_label_combo'].currentText()
    service_name = validation_rules.get(software_type, {}).get('service_name')

    iot_client = get_client('iot', 1)  # 假设使用目标账户客户端
    iot_data = get_client('iot-data', 1)

    if device_type != 'LMD6000':
        if not shadow_message['value']:
            logger.error("请先获取设备影子配置")
            QMessageBox.warning(parent_widget, "操作中断", "请先获取设备影子配置", QMessageBox.Ok)
            return

    # 完全匹配用户提供的影子结构
    shadow_payload = {
        "state": {
            "desired": {
                "welcome": "aws-iot"  # 图片中要求的字段
            },
            "reported": {
                "welcome": "aws-iot"  # 保持与desired一致
            }
        }
    }

    if mode_value['mode'] == "INIT":
        """
        完整的IoT设备初始化流程
        :param thing_name: 设备名称 (如 "SN123456")
        :param group_name: 设备组名称 (如 "LMDC")
        :param initial_shadow: 初始影子配置 (如 {"version": "1.0.0"})
        """

        # 1. 验证SN码格式（符合图片中的命名规则）
        if not all(c.isalnum() or c in ('-', '_', ':') for c in sn['value']):
            raise ValueError("SN码只能包含字母、数字、连字符、下划线或冒号")

        # 2. 确定设备类型
        def get_thing_type(device_type):
            if device_type in ["LMDC", "LMDC-V2"]:
                return "LMDC-TSB"
            elif device_type == "LBB300":
                return "lbb300"
            elif device_type == "LBB400":
                return "LBB400"
            elif device_type == "LMD6000":
                return "LMD-TSS"
            else:
                # 新增：不支持的类型弹出提示框
                QMessageBox.warning(
                    parent_widget,
                    "不支持的类型",
                    f"当前不支持 {device_type} 类型的设备，仅支持 LMDC/LMDC-V2/LBB300/LBB400/LMD6000",
                    QMessageBox.Ok
                )
                return None  # 返回None表示不支持

        thing_type = get_thing_type(device_type)
        if thing_type is None:  # 检查是否是不支持的类型
            return  # 直接返回，不继续执行

        # 尝试获取设备信息，如果成功则表示设备已存在
        if device_type != 'LMD6000':
            try:
                iot_client.describe_thing(thingName=sn['value'])
                logger.error(f"设备 {sn['value']} 已存在，请切换模式")
                # 弹出 QMessageBox 错误提示
                QMessageBox.critical(
                    parent_widget,  # 父窗口设为当前窗口
                    "设备已存在",
                    f"设备 {sn['value']} 已存在，请切换模式！",
                    QMessageBox.Ok
                )
                return  # 可以选择返回或抛出特定异常
            except iot_client.exceptions.ResourceNotFoundException:
                try:
                    # 2. 创建设备（带类型和属性）
                    response = iot_client.create_thing(
                        thingName=sn['value'],
                        thingTypeName=thing_type,
                    )

                    if shadow_message['value']:
                        shadow_payload["state"]["desired"].update(shadow_message['value'])

                    # "Unnamed shadow"
                    response = iot_data.update_thing_shadow(
                        # thingName=sn['value'],
                        thingName=sn['value'],
                        payload=json.dumps(shadow_payload)
                    )

                    # # 验证结果
                    # print("经典影子配置完成")
                    attach_cert_to_existing_thing(sn['value'], certificate_id)
                    if not execute_software(ui_components, software_type, ssh_client):
                        return
                    if execute_software(ui_components, software_type, ssh_client):
                        # 调用检查方法，模式为INIT
                        check_service_active(mode_value, ssh_client, service_name, 1)
                except iot_client.exceptions.ResourceAlreadyExistsException:
                    logger.debug(f"设备 {sn['value']} 已存在，跳过创建")
                    # print(f"⚠️ 设备 {thing_name} 已存在，跳过创建")
                except Exception as e:
                    logger.error(f"初始化失败: {str(e)}")
                    # print(f"❌ 初始化失败: {str(e)}")
                    raise
        else:
            if not execute_software(ui_components, software_type, ssh_client):
                return
            if execute_software(ui_components, software_type, ssh_client):
                # 调用检查方法，模式为INIT
                check_service_active(mode_value, ssh_client, service_name, 1)
    else:
        if device_type != 'LMD6000':
            try:
                iot_client.describe_thing(thingName=sn['value'])
            except iot_client.exceptions.ResourceNotFoundException:
                logger.error(f"设备 {sn['value']} 不存在")
                # print(f"设备 {thing_name} 不存在")
                return

        if upload_type == 'S3':
            if not check_service_active(mode_value, ssh_client, service_name, 0):
                return
            s3_version_full = ui_components['sixth_row']['S3_Version_combo'].currentText()
            # print(f"原始版本字符串: {s3_version_full}")

            # 根据 software_type 提取版本号
            if software_type in ['LiftBennu100', 'LiftPhoenix300-v2', 'LiftPhoenix400', 'LiftPhoenix500']:
                # 找到最后一个 '-' 并提取后面的内容
                version_number = s3_version_full.rsplit('-', 1)[-1]
                if shadow_message['value']:
                    shadow_message['value']['DesiredVersion'] = version_number
                    # print(shadow_message['value'])
                if shadow_message['value']:
                    shadow_payload["state"]["desired"].update(shadow_message['value'])

                # "更新设备影子"
                response = iot_data.update_thing_shadow(
                    thingName=sn['value'],
                    payload=json.dumps(shadow_payload)
                )

                # 调用检查方法，模式为UPDATE
                check_service_active(mode_value, ssh_client, service_name, 1)
                success_label = QLabel("✅ 执行成功！")
                success_label.setStyleSheet("color: green; font-weight: bold; font-size: 18px;")
                ui_components['seventh_row']['content_layout'].addWidget(success_label)
            else:
                logger.debug('原始版本字符串,目前不支持LMD-TSS')

        if upload_type == "Local":
            stop_service(ssh_client, service_name)
            if device_type != 'LMD6000':
                if shadow_message['value']:
                    shadow_payload["state"]["desired"].update(shadow_message['value'])

                # "更新设备影子"
                response = iot_data.update_thing_shadow(
                    thingName=sn['value'],
                    payload=json.dumps(shadow_payload)
                )
                if not execute_software(ui_components, software_type, ssh_client):
                    return
                success_label = QLabel("✅ 执行成功！")
                success_label.setStyleSheet("color: green; font-weight: bold; font-size: 18px;")
                ui_components['seventh_row']['content_layout'].addWidget(success_label)
            else:
                if not execute_software(ui_components, software_type, ssh_client):
                    return
                success_label = QLabel("✅ 执行成功！")
                success_label.setStyleSheet("color: green; font-weight: bold; font-size: 18px;")
                ui_components['seventh_row']['content_layout'].addWidget(success_label)

import sys
from PyQt5.QtWidgets import QApplication
from view import DMSWindow  # 替换为实际模块路径


def get_version():
    """从readme.txt的注释行读取版本号"""
    try:
        with open("readme.txt", "r", encoding="utf-8") as f:
            first_line = f.readline()
            if first_line.startswith("# Version:"):
                return first_line.split(":")[1].strip()
    except:
        pass
    return "1.0.0"  # 默认版本


def main():
    version = get_version()
    app = QApplication(sys.argv)
    window = DMSWindow(version)  # 传递版本号
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

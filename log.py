import sys
import os
import logging


def setup_logger():
    """配置全局日志记录器"""
    # 判断是否打包成 EXE
    if getattr(sys, 'frozen', False):
        log_dir = os.path.dirname(sys.executable)  # EXE 所在目录
    else:
        log_dir = os.path.dirname(os.path.abspath(__file__))  # 开发时脚本目录

    log_file = os.path.join(log_dir, 'dms.log')

    logger = logging.getLogger()
    if not logger.handlers:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(
            logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        )
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter('%(levelname)s - %(message)s'))

        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        logger.setLevel(logging.ERROR)  # 确保日志级别足够低

    return logger


logger = setup_logger()

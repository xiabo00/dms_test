from pathlib import Path
import json, sys, os, toml
import argparse
import re
import subprocess
import sys
import tarfile
import shutil
from typing import Literal, Optional, Union


def print_c(color: Literal['R', 'G', 'B', 'Y', 'Purple', 'Cyan'], s: str) -> None:
    color_map = {
        'R': '31',
        'G': '32',
        'B': '34',
        'Y': '33',
        'Purple': '35',
        'Cyan': '36'
    }
    print(f"\033[{color_map[color]}m{s}\033[0m")


def generate_resources():
    """生成资源文件"""
    if not os.path.isfile("images.qrc"):
        raise FileNotFoundError("未找到 images.qrc 文件")
    try:
        subprocess.run(["pyrcc5", "images.qrc", "-o", "images_rc.py"], check=True)
        print("资源文件已生成: images_rc.py")
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"生成资源文件失败: {str(e)}")


def update_readme_version(version):
    """智能替换或追加版本行（第一行）"""
    if not version:  # 新增检查
        raise ValueError("版本号不能为None或空")

    version_line = f"# Version: {version}\n"
    readme_path = Path("readme.txt").absolute()  # 使用绝对路径

    try:
        if not readme_path.exists():
            readme_path.write_text(version_line, encoding="utf-8")
            return

        content = readme_path.read_text(encoding="utf-8")
        lines = content.splitlines(keepends=True)

        with open(readme_path, "w", encoding="utf-8") as f:
            if lines and lines[0].startswith("# Version:"):
                f.write(version_line)
                f.writelines(lines[1:])
            else:
                f.write(version_line + content)

        print(f"[SUCCESS] 已更新 README 版本为: {version}")
    except Exception as e:
        print(f"[ERROR] 更新 README 失败: {str(e)}")


def build_executable(script_path, version):
    # 1. 更新readme.txt版本行
    update_readme_version(version)

    """在当前目录生成可执行文件"""
    app_name = f"DMS V{version}"
    exe_name = app_name + ".exe"

    # 清理旧文件
    if os.path.exists(exe_name):
        os.remove(exe_name)
    if os.path.exists("build"):
        shutil.rmtree("build", ignore_errors=True)

    cmd = [
        "pyinstaller",
        "--onefile",
        "--windowed",
        "--clean",
        "--name", app_name,
        "--distpath", ".",
        "--workpath", "build",
        "--specpath", "build",
        script_path,
    ]

    print(f"执行打包命令: {' '.join(cmd)}")
    try:
        subprocess.run(cmd, check=True)
        return exe_name
    except KeyboardInterrupt:
        print("\n用户中断操作，正在清理...")
        if os.path.exists(exe_name):
            os.remove(exe_name)
        if os.path.exists("build"):
            shutil.rmtree("build", ignore_errors=True)
        raise SystemExit("已取消打包")


def create_tar_and_clean(exe_name, version):
    """打包文件并清理.exe"""
    required_files = {
        exe_name: "可执行文件",
        "readme.txt": "说明文件",
        "Shadow": "资源目录"
    }

    # 检查文件是否存在
    missing = [name for file, name in required_files.items() if not os.path.exists(file)]
    if missing:
        raise FileNotFoundError(f"缺失必要文件: {', '.join(missing)}")

    # 创建tar包
    tar_name = f"DMS_V{version}.tar"
    print(f"创建压缩包: {tar_name}")

    try:
        with tarfile.open(tar_name, "w") as tar:
            for file in required_files:
                print(f"添加: {file}")
                tar.add(file)
    except Exception as e:
        if os.path.exists(tar_name):
            os.remove(tar_name)
        raise RuntimeError(f"创建压缩包失败: {str(e)}")

    # 关键修改：打包后立即删除.exe
    print(f"删除临时文件: {exe_name}")
    os.remove(exe_name)
    return tar_name


def clean_up():
    """清理所有构建残留"""
    print("清理临时文件...")
    # 删除build目录
    if os.path.exists("build"):
        shutil.rmtree("build", ignore_errors=True)
        print("已删除 build 目录")
    # 删除.spec文件
    for file in os.listdir("."):
        if file.endswith(".spec"):
            os.remove(file)
            print(f"已删除 {file}")

    if os.path.exists("config_in.py"):
        os.remove('config_in.py')
        print("已删除 config_in.py")


def validate_version(version: str) -> str:
    """
    验证版本号格式是否符合 X.Y.Z 格式
    :param version: 输入的版本号字符串
    :return: 验证通过的版本号
    :raises argparse.ArgumentTypeError: 如果格式不匹配
    """
    if not re.match(r'^\d+\.\d+\.\d+$', version):
        raise argparse.ArgumentTypeError(f"版本号格式错误，应为 X.Y.Z 格式（如 1.0.0），当前输入: {version}")
    return version


def load_config(config_file: str, args) -> Optional[dict]:
    with open(config_file, "r", encoding="utf-8") as f:
        config: dict = toml.load(f)

    build_config = {
        "CONFIG_VERSION": args.version if args.version else "1.0.1-beta.1",
        "CONFIG_INTERPRETER_VERSION": sys.version.split(" ")[0],
        "CONFIG_AWS_CERT": "",
        "CONFIG_AWS_PRIVATE_KEY": "",
        "CONFIG_AWS_ROOTCA": "",
        **{k: v for k, v in config.items()},
    }

    if args.cert:
        print_c("B", "- use cert config file")
        try:
            # 直接读取并解析 cert.json 文件
            with open(args.cert, 'r', encoding='utf-8') as f:
                cert_data = json.load(f)

            # 按字段名直接赋值（假设cert.json结构与字段名匹配）
            build_config.update({
                'CONFIG_AWS_CERT': cert_data['cert'],
                'CONFIG_AWS_PRIVATE_KEY': cert_data['privateKey'],
                'CONFIG_AWS_ROOTCA': cert_data['rootCA']
            })
        except FileNotFoundError:
            print_c("R", f"Error: Certificate file {args.cert} not found!")
            return
        except json.JSONDecodeError:
            print_c("R", f"Error: Invalid JSON format in {args.cert}!")
            return
        except KeyError as e:
            print_c("R", f"Error: Missing required field {e} in certificate file!")
            return
        except Exception as e:
            print_c("R", f"Unexpected error loading certificate: {str(e)}")
            return
    else:
        print_c("B", "- use env cert config")
        cert = os.getenv("AWS_CERT")
        pk = os.getenv("AWS_PRIVATE_KEY")
        ca = os.getenv("AWS_ROOTCA")
        if not (cert and pk and ca):
            return

        build_config['CONFIG_AWS_CERT'] = cert
        build_config['CONFIG_AWS_PRIVATE_KEY'] = pk
        build_config['CONFIG_AWS_ROOTCA'] = ca

    for k, v in build_config.items():
        if k not in ['CONFIG_AWS_CERT', 'CONFIG_AWS_PRIVATE_KEY', 'CONFIG_AWS_ROOTCA']:
            print_c("Y", f"- {k} = {v}")

    return build_config


def config_inject(config_file: str, properties: dict[str, Union[int, float, str, list]]) -> bool:
    """
    将配置字典写入指定文件，生成Python格式的配置文件

    参数:
        config_file (str): 目标配置文件的路径
        properties (dict): 包含配置项的字典，支持int/float/str/list类型

    示例:
        >>> config_inject("config.py", {"API_KEY": "abc123", "PORT": 8080})
        生成文件内容:
            API_KEY = abc123
            PORT = 8080
    """
    try:
        # 使用上下文管理器确保文件正确关闭
        with open(config_file, 'w', encoding="utf-8") as f:
            # 遍历字典所有键值对
            for k, v in properties.items():
                # 字符串类型处理（使用三重引号避免转义问题）
                if isinstance(v, str):
                    f.write(f"{k} = \"\"\"{v}\"\"\"\n")

                # 数字或列表类型处理（直接写入Python字面量）
                elif isinstance(v, (int, float, list)):
                    f.write(f"{k} = {v}\n")

                # 可扩展其他数据类型（如dict/bool等）
                # elif isinstance(v, dict):
                #     f.write(f"{k} = {v}\n")

        return True

    except IOError as e:
        # 实际项目中建议记录日志或抛出异常
        print(f"配置文件写入失败: {str(e)}")
        return False
        # 或者 raise RuntimeError(f"无法写入配置文件: {config_file}") from e


def main():
    # 获取当前脚本所在目录（即 config.toml 所在目录）
    CURRENT_DIR = Path(__file__).parent.absolute()

    parser = argparse.ArgumentParser(description="DMS 极简打包工具")
    parser.add_argument("script", help="主脚本路径（如 main.py）")
    parser.add_argument("-v", "--version", required=True, help="版本号（如 1.0.0）", type=validate_version)
    parser.add_argument("-c", "--cert", required=False, dest="cert", help="cert config file path")
    args = parser.parse_args()

    # 检查如果传入了 -c 参数，验证文件是否存在
    if args.cert:
        if not os.path.isfile(args.cert):
            parser.error(f"证书文件不存在: {args.cert}")
            return

    try:
        print("=== 开始打包流程 ===")

    # 加载配置（直接使用当前目录下的 config.toml）
        configs = load_config(str(CURRENT_DIR / "config.toml"), args)
        if configs is None:
            return
        # 生成 config_in.py（输出到同一目录）
        config_inject(str(CURRENT_DIR / "config_in.py"), configs)

        generate_resources()
        print(f'{args.version}')
        exe_name = build_executable(args.script, args.version)
        tar_name = create_tar_and_clean(exe_name, args.version)
        clean_up()

        print("\n=== 打包成功 ===")
        print(f"最终生成: {tar_name}")
        print("包含内容:")
        print("  - 可执行文件（已打包进tar）")
        print("  - readme.txt（原始文件保留）")
        print("  - Shadow/（原始目录保留）")

    except Exception as e:
        print(f"\n=== 打包失败 ===")
        print(f"错误: {str(e)}")
        clean_up()  # 失败时也尝试清理
        exit(1)


if __name__ == "__main__":
    main()

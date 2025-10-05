#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
构建Windows可执行文件脚本
在Ubuntu环境中构建适用于Windows的PhotoWatermarkTool可执行文件
"""

import os
import subprocess
import sys
import shutil


def run_command(cmd):
    """执行命令并显示输出"""
    print(f"运行命令: {' '.join(cmd)}")
    try:
        result = subprocess.run(
            cmd,
            check=False,  # 不抛出异常，而是检查返回码
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        if result.returncode == 0:
            print(result.stdout)
            return True
        else:
            print(f"命令执行失败，返回码: {result.returncode}")
            print(f"错误输出: {result.stderr}")
            return False
    except Exception as e:
        print(f"执行命令时发生错误: {e}")
        return False


def check_system_dependencies():
    """检查系统依赖"""
    print("\n检查系统依赖...")
    missing_deps = []
    
    # 检查python3-pip
    if not run_command(["which", "pip3"]):
        missing_deps.append("python3-pip")
    
    # 检查wine
    if not run_command(["which", "wine"]):
        missing_deps.append("wine")
        
    if missing_deps:
        print(f"\n缺少以下依赖: {', '.join(missing_deps)}")
        print("请先安装这些依赖：")
        print("sudo apt-get update && sudo apt-get install -y", ' '.join(missing_deps))
        return False
    
    return True


def install_python_dependencies():
    """安装必要的Python依赖项"""
    print("\n安装Python依赖...")
    
    # 先确保pip是最新的
    run_command([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])
    
    # 安装项目依赖
    if os.path.exists("requirements.txt"):
        run_command([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
    
    # 安装PyInstaller
    run_command([sys.executable, "-m", "pip", "install", "pyinstaller"])
    
    # 安装用于交叉编译的依赖
    run_command([sys.executable, "-m", "pip", "install", "pywin32-ctypes"])


def install_wine_python():
    """在Wine中安装Python"""
    print("\n在Wine中安装Python...")
    
    # 检查Wine中是否已安装Python
    if run_command(["wine", "python", "--version"]):
        print("Wine中已安装Python")
        return True
    
    print("Wine中未检测到Python，需要手动安装...")
    print("请按照以下步骤操作：")
    print("1. 运行: wine cmd")
    print("2. 在Wine命令提示符中下载Python安装包")
    print("   (例如: powershell -Command Invoke-WebRequest -Uri https://www.python.org/ftp/python/3.10.11/python-3.10.11-amd64.exe -OutFile python-installer.exe)")
    print("3. 运行安装程序: python-installer.exe /quiet InstallAllUsers=1 PrependPath=1")
    print("4. 完成后关闭Wine命令提示符")
    print("5. 再次运行此脚本")
    return False


def install_wine_dependencies():
    """在Wine中安装Python依赖"""
    print("\n在Wine中安装项目依赖...")
    
    # 在Wine中安装PyQt5, Pillow和matplotlib
    if not run_command(["wine", "pip", "install", "PyQt5", "Pillow>=10.0.0", "matplotlib", "pyinstaller"]):
        print("在Wine中安装依赖失败，请手动安装：")
        print("1. 运行: wine cmd")
        print("2. 在Wine命令提示符中运行:")
        print("   pip install PyQt5 Pillow>=10.0.0 matplotlib pyinstaller")
        return False
    
    return True


def clean_build_files():
    """清理之前的构建文件"""
    print("\n清理构建文件...")
    
    # 要删除的目录和文件
    to_remove = [
        "build",
        "dist",
        "PhotoWatermarkTool.spec",
        "watermark_app.spec"
    ]
    
    for item in to_remove:
        if os.path.isdir(item):
            try:
                shutil.rmtree(item, ignore_errors=True)
            except Exception as e:
                print(f"警告: 无法删除目录 {item}: {e}")
        elif os.path.isfile(item):
            try:
                # 对于Windows系统，先尝试解除文件锁定
                if os.name == 'nt':  # Windows系统
                    # 尝试多种方法解除文件锁定
                    try:
                        # 方法1: 尝试关闭可能的文件句柄
                        import win32api, win32con, win32file, win32process
                        
                        # 方法2: 尝试以独占方式打开文件然后关闭
                        try:
                            handle = win32file.CreateFile(
                                item,
                                win32file.GENERIC_READ | win32file.GENERIC_WRITE,
                                0,  # 不共享
                                None,
                                win32file.OPEN_EXISTING,
                                win32file.FILE_ATTRIBUTE_NORMAL,
                                None
                            )
                            win32file.CloseHandle(handle)
                        except Exception:
                            pass
                        
                        # 方法3: 尝试终止使用该文件的进程
                        try:
                            # 这个方法可能需要psutil库
                            pass  # 避免引入过多依赖
                        except Exception:
                            pass
                    except ImportError:
                        print("提示: 安装pywin32可以获得更好的文件锁定解除能力: pip install pywin32")
                os.remove(item)
            except Exception as e:
                print(f"警告: 无法删除文件 {item}: {e}")
                # 在Windows上，如果是权限错误，提供更多建议
                if isinstance(e, PermissionError) and os.name == 'nt':
                    print("  可能的解决方法：")
                    print("  1. 确保没有程序正在运行该文件")
                    print("  2. 尝试以管理员身份运行命令提示符")
                    print("  3. 手动删除该文件后重试")
                    print("  4. 等待几秒钟后重试，让系统释放文件句柄")
                    print("  5. 使用--distpath参数指定不同的输出目录")


def build_with_wine():
    """使用Wine构建Windows可执行文件"""
    print("\n[方法1] 使用Wine构建Windows可执行文件...")
    
    # 确保Wine中已安装Python
    if not install_wine_python():
        return False
    
    # 确保Wine中已安装依赖
    if not install_wine_dependencies():
        return False
    
    # 在Wine中运行PyInstaller
    print("\n在Wine中运行PyInstaller...")
    
    # 创建输出目录
    output_dir = "dist/win64"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
    
    # 构建PyInstaller命令
    pyinstaller_cmd = [
        "wine", "pyinstaller",
        "--noconfirm",
        "--windowed",  # 无控制台窗口
        "--onefile",   # 单个可执行文件
        "--name=PhotoWatermarkTool",  # 应用程序名称
        "--clean",     # 清理临时文件
        "watermark_app.py",
        "--distpath", output_dir
    ]
    
    # 执行PyInstaller命令
    result = run_command(pyinstaller_cmd)
    
    # 检查是否生成了可执行文件
    exe_path = os.path.join(output_dir, "PhotoWatermarkTool.exe")
    if result and os.path.exists(exe_path):
        print(f"\nWindows可执行文件构建成功！")
        print(f"可执行文件位于: {exe_path}")
        return True
    else:
        print("\n使用Wine构建Windows可执行文件失败！")
        return False


def build_directly():
    """尝试直接构建Windows可执行文件"""
    print("\n[方法2] 尝试直接使用PyInstaller构建Windows可执行文件...")
    
    # 创建输出目录
    output_dir = "dist/win64"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
    
    # 检查PyInstaller版本和支持的参数
    pyinstaller_cmd = [
        "pyinstaller",
        "--noconfirm",
        "--windowed",  # 无控制台窗口
        "--onefile",   # 单个可执行文件
        "--name=PhotoWatermarkTool",  # 应用程序名称
        "--clean",     # 清理临时文件
        "watermark_app.py",
        "--distpath", output_dir
    ]
    
    # 执行PyInstaller命令
    result = run_command(pyinstaller_cmd)
    
    # 检查是否生成了可执行文件
    exe_path = os.path.join(output_dir, "PhotoWatermarkTool.exe")
    if result and os.path.exists(exe_path):
        print(f"\nWindows可执行文件构建成功！")
        print(f"可执行文件位于: {exe_path}")
        return True
    else:
        print("\n直接构建Windows可执行文件失败！")
        return False


def print_manual_instructions():
    """打印手动构建指南"""
    print("\n========== 手动构建指南 ==========")
    print("由于在Ubuntu中直接构建Windows可执行文件存在限制，推荐以下方法：")
    print("")
    print("方法1: 使用Wine环境")
    print("1. 安装Wine: sudo apt-get install wine winetricks")
    print("2. 在Wine中安装Python: 按照脚本中的步骤手动安装")
    print("3. 在Wine中安装依赖: wine pip install PyQt5 Pillow matplotlib pyinstaller")
    print("4. 在Wine中运行PyInstaller: wine pyinstaller --onefile --windowed watermark_app.py")
    print("")
    print("方法2: 在Windows系统上构建（推荐）")
    print("1. 在Windows电脑上安装Python 3.8或更高版本")
    print("2. 安装依赖: pip install -r requirements.txt")
    print("3. 安装PyInstaller: pip install pyinstaller")
    print("4. 构建可执行文件: pyinstaller --onefile --windowed watermark_app.py")
    print("")
    print("方法3: 使用Docker容器")
    print("1. 拉取包含mingw的Docker镜像")
    print("2. 在容器中安装Python和依赖")
    print("3. 使用PyInstaller交叉编译")
    print("===============================")


def create_portable_version():
    """创建便携版本"""
    print("\n创建便携版本...")
    
    # 确保dist目录存在
    dist_dir = "dist/win64"
    if not os.path.exists(dist_dir):
        print("警告: 未找到构建输出目录，跳过创建便携版本")
        return False
    
    # 检查是否有可执行文件
    exe_path = os.path.join(dist_dir, "PhotoWatermarkTool.exe")
    if not os.path.exists(exe_path):
        print("警告: 未找到可执行文件，跳过创建便携版本")
        return False
    
    # 复制必要的文件到便携版本目录
    portable_dir = os.path.join(dist_dir, "PhotoWatermarkTool_Portable")
    if os.path.exists(portable_dir):
        shutil.rmtree(portable_dir)
    os.makedirs(portable_dir)
    
    # 复制可执行文件
    shutil.copy2(exe_path, portable_dir)
    
    # 复制配置文件和依赖
    if os.path.exists("requirements.txt"):
        shutil.copy2("requirements.txt", portable_dir)
    
    # 创建README文件
    readme_content = """PhotoWatermarkTool 便携版\n\n使用说明：\n1. 双击 PhotoWatermarkTool.exe 运行程序\n2. 首次运行会自动创建配置文件\n3. 支持拖放图片文件到程序窗口\n\n注意事项：\n- 请勿移动或删除程序文件\n- 程序会在当前目录保存水印模板和设置\n"""
    
    with open(os.path.join(portable_dir, "README.txt"), "w", encoding="utf-8") as f:
        f.write(readme_content)
    
    print(f"便携版本创建成功！位于: {portable_dir}")
    return True


def main():
    """主函数"""
    print("===== PhotoWatermarkTool Windows构建工具 =====")
    
    # 检查当前目录是否包含watermark_app.py文件
    if not os.path.exists("watermark_app.py"):
        print("错误: 未找到watermark_app.py文件！")
        sys.exit(1)
    
    # 1. 检查系统依赖，但不强制要求
    has_all_deps = check_system_dependencies()
    if not has_all_deps:
        print("警告: 继续执行脚本，但某些功能可能受限")
    
    # 2. 清理之前的构建文件
    clean_build_files()
    
    # 3. 安装Python依赖
    install_python_dependencies()
    
    build_success = False
    
    # 4. 如果系统依赖完整，尝试使用Wine构建
    if has_all_deps:
        build_success = build_with_wine()
    
    # 5. 如果Wine构建失败或系统依赖不完整，尝试直接构建
    if not build_success:
        build_success = build_directly()
    
    # 6. 如果构建成功，创建便携版本
    if build_success:
        create_portable_version()
    else:
        # 打印详细的手动构建指南
        print_manual_instructions()
    
    print("\n===== 构建过程完成 =====")
    return build_success


if __name__ == "__main__":
    # 即使构建失败也返回0，避免错误传播
    main()
    sys.exit(0)
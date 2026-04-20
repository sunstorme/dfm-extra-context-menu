#!/usr/bin/env python3
"""
DDE Tools 主程序入口

用法:
  dfm-tools              # 启动系统托盘
  dfm-tools --tray       # 同上
  dfm-tools <plugin-id> [path]  # 执行某个插件命令（供 .desktop 调用）
"""

import os
import sys
import signal
from pathlib import Path

# 添加 src 目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib

from plugin_manager import get_plugin_manager
from config import get_config_manager
from executor import get_executor

# 托盘功能（可选依赖）
try:
    gi.require_version('AyatanaAppIndicator3', '0.1')
    from gi.repository import AyatanaAppIndicator3
    from tray import get_tray_icon
    TRAY_AVAILABLE = True
except (ImportError, ValueError):
    TRAY_AVAILABLE = False
    AyatanaAppIndicator3 = None
    get_tray_icon = None


# ============================================================================
# 常量定义
# ============================================================================

FIRST_RUN_FLAG = Path.home() / '.config' / 'dfm-tools' / 'first_run'
AUTOSTART_FILE = '/etc/xdg/autostart/dfm-tools.desktop'


# ============================================================================
# 首次运行向导
# ============================================================================

class FirstRunWizard:
    """首次运行向导"""

    def __init__(self):
        """初始化向导"""
        self._autostart_enabled = False

    def show(self):
        """显示首次运行向导"""
        dialog = Gtk.MessageDialog(
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.YES_NO,
            text="欢迎使用 DDE Tools"
        )
        dialog.format_secondary_text(
            "是否在登录时自动启动 DDE Tools 托盘图标？\n\n"
            "托盘图标提供快速访问开发工具的菜单，\n"
            "可以稍后在设置中更改。"
        )
        dialog.set_title("DDE Tools 首次运行")

        response = dialog.run()
        dialog.destroy()

        if response == Gtk.ResponseType.YES:
            self._autostart_enabled = True
            self._enable_autostart()
            print("✓ 已启用开机自启动")
        else:
            print("✓ 未启用开机自启动")

        # 创建标记文件
        FIRST_RUN_FLAG.parent.mkdir(parents=True, exist_ok=True)
        FIRST_RUN_FLAG.touch()

    def _enable_autostart(self):
        """启用开机自启动（使用 pkexec 获取权限）"""
        # 确保自启动目录存在
        autostart_dir = Path(AUTOSTART_FILE).parent
        autostart_dir.mkdir(parents=True, exist_ok=True)

        # 创建自启动 .desktop 文件
        desktop_content = f"""[Desktop Entry]
Type=Application
Name=DDE Tools
Name[zh_CN]=DFM开发工具箱
Comment=Development toolbox tray icon
Comment[zh_CN]=开发工具箱托盘图标
Exec=dfm-tools --tray
Icon=dfm-menu-manager
Terminal=false
X-GNOME-Autostart-enabled=true
"""

        # 使用 pkexec 写入系统目录
        import subprocess
        import tempfile

        try:
            # 创建临时文件
            with tempfile.NamedTemporaryFile(mode='w', suffix='.desktop', delete=False) as tmp:
                tmp.write(desktop_content)
                tmp_path = tmp.name

            # 使用 pkexec tee 写入系统目录（需要用户授权）
            subprocess.run([
                'pkexec', 'sh', '-c',
                f'tee {AUTOSTART_FILE} < {tmp_path} && rm {tmp_path}'
            ], check=True)

            print(f"✓ 自启动已配置: {AUTOSTART_FILE}")

        except subprocess.CalledProcessError as e:
            print(f"✗ 自启动配置失败: {e}")
            print("提示: 您可以稍后手动配置自启动")


# ============================================================================
# 主程序
# ============================================================================

class DfmToolsApp:
    """DDE Tools 主程序"""

    def __init__(self):
        """初始化主程序"""
        self.plugin_manager = get_plugin_manager()
        self.config_manager = get_config_manager()

    def run_tray(self):
        """运行托盘模式"""
        print("=" * 50)
        print("DDE Tools - 系统托盘模式")
        print("=" * 50)
        print()

        # 检查托盘功能是否可用
        if not TRAY_AVAILABLE:
            print("错误: 系统托盘功能不可用")
            print()
            print("请安装以下依赖包:")
            print("  sudo apt install gir1.2-ayatanaappindicator3-0.1")
            print()
            print("或者使用文件管理器右键菜单功能（不需要托盘）")
            return 1

        # 检查首次运行
        if not FIRST_RUN_FLAG.exists():
            wizard = FirstRunWizard()
            wizard.show()

        # 启动托盘
        tray = get_tray_icon()
        tray.run()

    def execute_plugin(self, plugin_id: str, path: str = None):
        """
        执行插件命令

        Args:
            plugin_id: 插件 ID
            path: 文件路径（由文件管理器传入）
        """
        plugin = self.plugin_manager.get_plugin(plugin_id)
        if not plugin:
            print(f"错误: 未找到插件: {plugin_id}")
            return 1

        # 检查依赖
        if not plugin.available:
            missing = plugin.missing_dep
            print(f"错误: 插件依赖不满足: 缺少 {missing}")
            return 1

        # 执行命令
        command = plugin.command
        if not command:
            print(f"错误: 插件没有配置命令: {plugin_id}")
            return 1

        # 替换路径占位符
        if path and '%p' in command:
            command = command.replace('%p', path)
        elif path and '%P' in command:
            command = command.replace('%P', path)

        # 执行
        import subprocess
        import shlex

        try:
            if ' ' in command or '\t' in command:
                # 包含空格或制表符，使用 shell
                subprocess.Popen(command, shell=True)
            else:
                # 简单命令，直接执行
                subprocess.Popen(shlex.split(command))

            print(f"执行插件: {plugin.name} ({plugin_id})")
            return 0
        except Exception as e:
            print(f"执行失败: {e}")
            return 1


# ============================================================================
# 入口函数
# ============================================================================

def print_usage():
    """打印使用说明"""
    print("用法:")
    print("  dfm-tools              # 启动系统托盘")
    print("  dfm-tools --tray       # 同上")
    print("  dfm-tools <plugin-id> [path]  # 执行插件命令")
    print()
    print("示例:")
    print("  dfm-tools")
    print("  dfm-tools --tray")
    print("  dfm-tools gitk /path/to/repo")
    print()


def main():
    """主函数"""
    # 解析命令行参数
    args = sys.argv[1:]

    if not args or args[0] == '--tray':
        # 托盘模式
        app = DfmToolsApp()
        app.run_tray()

    elif args[0] in ['-h', '--help']:
        print_usage()

    else:
        # 插件执行模式
        plugin_id = args[0]
        path = args[1] if len(args) > 1 else None

        app = DfmToolsApp()
        sys.exit(app.execute_plugin(plugin_id, path))


if __name__ == "__main__":
    main()

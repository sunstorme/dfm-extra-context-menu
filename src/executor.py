#!/usr/bin/env python3
"""
DFM Tools 命令执行器
负责执行外部命令，支持多种执行模式
"""

import subprocess
import shlex
import shutil
from typing import Dict, Optional, Callable

try:
    import gi
    gi.require_version('Gtk', '3.0')
    from gi.repository import Gtk
    GTK_AVAILABLE = True
except ImportError:
    GTK_AVAILABLE = False
    Gtk = None


# ============================================================================
# 命令执行器类
# ============================================================================

class CommandExecutor:
    """命令执行器"""

    def __init__(self):
        """初始化命令执行器"""
        self._confirm_callback: Optional[Callable] = None

    def set_confirm_callback(self, callback: Callable[[str], bool]):
        """
        设置确认对话框回调

        Args:
            callback: 确认回调函数，接收消息文本，返回用户选择
        """
        self._confirm_callback = callback

    def execute(self, item_config: Dict):
        """
        执行命令（主入口）

        Args:
            item_config: 菜单项配置字典，包含 command 和执行选项
        """
        command = item_config.get('command', '')
        if not command:
            return

        # 检查是否需要确认
        if item_config.get('confirm', False):
            confirm_msg = item_config.get('confirm_message', f'确定要执行: {command}?')
            if not self._confirm(confirm_msg):
                print(f"用户取消执行: {command}")
                return

        # 执行选项
        use_shell = item_config.get('shell', False)
        use_terminal = item_config.get('terminal', False)
        background = item_config.get('background', True)

        # 检查命令是否存在（仅针对非 shell 命令）
        if not use_shell and command:
            cmd_parts = command.split()
            if cmd_parts and not shutil.which(cmd_parts[0]):
                error_msg = f"命令未找到: {cmd_parts[0]}\n\n请安装对应的软件包后重试。"
                print(f"错误: {error_msg}")
                if GTK_AVAILABLE:
                    self._show_error_dialog("命令未找到", error_msg)
                return

        try:
            if use_terminal:
                self._execute_in_terminal(command, use_shell)
            elif background:
                self._execute_background(command, use_shell)
            else:
                self._execute_sync(command, use_shell)
        except Exception as e:
            print(f"命令执行失败: {e}")
            if GTK_AVAILABLE:
                self._show_error_dialog("命令执行失败", str(e))

    def _execute_in_terminal(self, command: str, use_shell: bool = False):
        """
        在终端中执行命令

        Args:
            command: 要执行的命令
            use_shell: 是否通过 shell 执行
        """
        terminal_emulators = [
            'deepin-terminal', 'gnome-terminal', 'xfce4-terminal',
            'konsole', 'xterm'
        ]

        # 查找可用的终端
        terminal = self._find_terminal(terminal_emulators)
        if not terminal:
            error_msg = "未找到可用的终端模拟器"
            print(f"错误: {error_msg}")
            if GTK_AVAILABLE:
                self._show_error_dialog("错误", error_msg)
            return

        # 构建终端命令
        cmd = self._build_terminal_command(terminal, command)

        try:
            subprocess.Popen(cmd)
            print(f"终端执行: {command}")
        except Exception as e:
            print(f"终端执行失败: {e}")
            raise

    def _execute_background(self, command: str, use_shell: bool = False):
        """
        后台执行命令

        Args:
            command: 要执行的命令
            use_shell: 是否通过 shell 执行
        """
        try:
            if use_shell:
                subprocess.Popen(command, shell=True,
                              stdout=subprocess.DEVNULL,
                              stderr=subprocess.DEVNULL)
            else:
                subprocess.Popen(shlex.split(command),
                              stdout=subprocess.DEVNULL,
                              stderr=subprocess.DEVNULL)
            print(f"后台执行: {command}")
        except Exception as e:
            raise e

    def _execute_sync(self, command: str, use_shell: bool = False):
        """
        同步执行命令（等待完成）

        Args:
            command: 要执行的命令
            use_shell: 是否通过 shell 执行
        """
        try:
            if use_shell:
                result = subprocess.run(command, shell=True,
                                      capture_output=True, text=True)
            else:
                result = subprocess.run(shlex.split(command),
                                      capture_output=True, text=True)

            if result.returncode != 0:
                print(f"命令返回错误: {result.stderr}")
            else:
                print(f"命令执行成功: {command}")
                if result.stdout:
                    print(f"输出: {result.stdout}")
        except Exception as e:
            raise e

    def _find_terminal(self, terminal_emulators: list) -> Optional[str]:
        """
        查找可用的终端模拟器

        Args:
            terminal_emulators: 终端模拟器列表

        Returns:
            找到的终端名称，未找到返回 None
        """
        for term in terminal_emulators:
            if shutil.which(term):
                return term
        return None

    def _build_terminal_command(self, terminal: str, command: str) -> list:
        """
        构建终端执行命令

        Args:
            terminal: 终端名称
            command: 要执行的命令

        Returns:
            命令列表
        """
        if terminal == 'deepin-terminal':
            return [terminal, '-e', 'bash', '-c',
                   f'{command}; read -n 1 -p "按任意键关闭..."']
        elif terminal == 'gnome-terminal':
            return [terminal, '--', 'bash', '-c',
                   f'{command}; read -n 1']
        else:
            return [terminal, '-e', 'bash', '-c',
                   f'{command}; read -n 1']

    def _confirm(self, message: str) -> bool:
        """
        显示确认对话框

        Args:
            message: 确认消息

        Returns:
            用户是否确认
        """
        if self._confirm_callback:
            return self._confirm_callback(message)
        return True

    def _show_error_dialog(self, title: str, message: str):
        """
        显示错误对话框

        Args:
            title: 标题
            message: 消息内容
        """
        if not GTK_AVAILABLE:
            return

        dialog = Gtk.MessageDialog(
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK,
            text=title
        )
        dialog.format_secondary_text(message)
        dialog.run()
        dialog.destroy()


# ============================================================================
# 工具函数
# ============================================================================

def get_executor() -> CommandExecutor:
    """
    获取命令执行器单例

    Returns:
        命令执行器实例
    """
    if not hasattr(get_executor, '_instance'):
        get_executor._instance = CommandExecutor()
    return get_executor._instance


# ============================================================================
# 测试代码
# ============================================================================

if __name__ == "__main__":
    import sys

    print("=" * 50)
    print("DFM Tools 命令执行器测试")
    print("=" * 50)
    print()

    # 测试命令
    test_config = {
        "command": "echo 'Hello from executor!'",
        "shell": True,
        "background": False
    }

    executor = get_executor()
    print(f"执行命令: {test_config['command']}")
    executor.execute(test_config)

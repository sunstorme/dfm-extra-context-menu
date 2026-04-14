#!/usr/bin/env python3
"""
DFM Tools 托盘图标
基于 Ayatana AppIndicator 的系统托盘实现
"""

import signal
import sys
from pathlib import Path
from typing import Dict

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('AyatanaAppIndicator3', '0.1')

from gi.repository import Gtk, AyatanaAppIndicator3 as AppIndicator3
from gi.repository import Gio, GLib

from config import get_config_manager
from executor import get_executor


# ============================================================================
# 托盘图标类
# ============================================================================

class TrayIcon:
    """系统托盘图标类"""

    def __init__(self, config: Dict = None):
        """
        初始化托盘图标

        Args:
            config: 托盘配置字典，为 None 则使用默认配置
        """
        self.config_manager = get_config_manager()
        self.executor = get_executor()
        self.dynamic_data = {'count': 0}
        self.checkbox_items = {}
        self.dynamic_items = {}

        # 加载配置
        if config is None:
            config = self.config_manager.get_tray_config()

        self.config = config
        self.app_id = config.get('app_id', 'dfm-tools')
        icon_config = config.get('icon', 'dfm-tools')
        self.initial_label = config.get('label', '')

        # 处理图标路径
        # 如果是绝对路径，直接使用；否则从图标主题查找
        if icon_config.startswith('/'):
            self.icon_name = icon_config
        else:
            # 开发环境：使用项目根目录的图标
            import os
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            local_icon = os.path.join(project_root, f"{icon_config}.svg")
            if os.path.exists(local_icon):
                self.icon_name = local_icon
            else:
                # 生产环境：使用图标主题中的图标
                self.icon_name = icon_config

        # 创建 AppIndicator
        self.indicator = AppIndicator3.Indicator.new(
            self.app_id,
            self.icon_name,
            AppIndicator3.IndicatorCategory.APPLICATION_STATUS
        )

        # 设置初始状态
        self.indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
        if self.initial_label:
            self.indicator.set_label(self.initial_label, "")

        # 创建菜单
        self.menu = self._create_menu()
        self.indicator.set_menu(self.menu)

        # 设置确认对话框回调
        self.executor.set_confirm_callback(self._confirm_dialog)

        # 启动配置文件监听
        self._config_monitor = None
        self._start_config_monitor()

        print(f"✓ 托盘图标已创建: {self.app_id}")
        print(f"✓ 配置监听已启动: {self._get_config_file()}")

    def _create_menu(self) -> Gtk.Menu:
        """
        从配置创建菜单

        Returns:
            GTK 菜单对象
        """
        menu = Gtk.Menu()
        menu_items = self.config.get('menu_items', [])

        for item_config in menu_items:
            self._add_menu_item(menu, item_config)

        return menu

    def _add_menu_item(self, menu: Gtk.Menu, item_config: Dict):
        """
        根据配置添加菜单项

        Args:
            menu: GTK 菜单
            item_config: 菜单项配置
        """
        item_type = item_config.get('type', 'item')

        if item_type == 'separator':
            self._add_separator(menu)

        elif item_type == 'header':
            label = item_config.get('label', '')
            self._add_header_item(menu, label)

        elif item_type == 'item':
            label = item_config.get('label', '')
            self._add_item(menu, label, item_config)

        elif item_type == 'checkbox':
            label = item_config.get('label', '')
            self._add_checkbox_item(menu, label, item_config)

        elif item_type == 'dynamic':
            label_template = item_config.get('label', '')
            action = item_config.get('action', '')
            self._add_dynamic_item(menu, label_template, action)

    def _add_item(self, menu: Gtk.Menu, label: str, item_config: Dict):
        """添加普通菜单项"""
        has_icon = item_config.get('icon', False)
        if has_icon:
            item = Gtk.ImageMenuItem(label=label)
        else:
            item = Gtk.MenuItem(label=label)

        enabled = item_config.get('enabled', True)
        item.set_sensitive(enabled)

        command = item_config.get('command')
        action = item_config.get('action')

        if command:
            item.connect("activate", lambda w: self.executor.execute(item_config))
        elif action:
            callback = self._get_callback(action)
            if callback:
                item.connect("activate", callback)

        item.show()
        menu.append(item)

    def _add_header_item(self, menu: Gtk.Menu, label: str):
        """添加标题项"""
        item = Gtk.MenuItem(label=label)
        item.set_sensitive(False)
        item.show()
        menu.append(item)

    def _add_checkbox_item(self, menu: Gtk.Menu, label: str, item_config: Dict):
        """添加复选框菜单项"""
        item = Gtk.CheckMenuItem(label=label)
        checked = item_config.get('checked', False)
        item.set_active(checked)

        command = item_config.get('command')
        if command:
            item.connect("activate", lambda w: self._execute_checkbox_command(w, item_config))

        item.show()
        menu.append(item)

        # 保存引用
        key = command or item_config.get('action', f'checkbox_{id(item)}')
        self.checkbox_items[key] = item

    def _add_dynamic_item(self, menu: Gtk.Menu, label_template: str, action: str):
        """添加动态菜单项"""
        label = label_template.format(**self.dynamic_data)
        item = Gtk.MenuItem(label=label)

        callback = self._get_callback(action)
        if callback:
            item.connect("activate", callback)

        item.show()
        menu.append(item)

        self.dynamic_items[action] = {
            'item': item,
            'template': label_template
        }

    def _add_separator(self, menu: Gtk.Menu):
        """添加分隔线"""
        separator = Gtk.SeparatorMenuItem()
        separator.show()
        menu.append(separator)

    def _get_callback(self, action_name: str):
        """获取回调函数"""
        return getattr(self, f'on_{action_name}', None)

    def _update_dynamic_items(self):
        """更新所有动态菜单项"""
        for action, info in self.dynamic_items.items():
            item = info['item']
            template = info['template']
            new_label = template.format(**self.dynamic_data)
            item.set_label(new_label)

    def _execute_checkbox_command(self, widget, item_config: Dict):
        """执行复选框命令"""
        command = item_config.get('command', '')
        if not command:
            return

        checked = widget.get_active()
        command = command.replace('{{checked}}', str(checked).lower())

        use_shell = item_config.get('shell', False)
        try:
            if use_shell:
                from subprocess import DEVNULL
                subprocess.Popen(command, shell=True, stdout=DEVNULL, stderr=DEVNULL)
            else:
                from subprocess import DEVNULL
                subprocess.Popen(command.split(), stdout=DEVNULL, stderr=DEVNULL)
            print(f"复选框命令执行: {command}")
        except Exception as e:
            print(f"命令执行失败: {e}")

    def _confirm_dialog(self, message: str) -> bool:
        """显示确认对话框"""
        dialog = Gtk.MessageDialog(
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.YES_NO,
            text="确认操作"
        )
        dialog.format_secondary_text(message)
        response = dialog.run()
        dialog.destroy()
        return response == Gtk.ResponseType.YES

    # ========================================================================
    # 回调函数
    # ========================================================================

    def on_show_message(self, widget):
        """显示消息对话框"""
        dialog = Gtk.MessageDialog(
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text="DFM Tools"
        )
        dialog.format_secondary_text(
            "DFM Tools - 开发工具箱\n\n"
            "系统托盘 + 文件管理器插件\n"
            "支持插件化扩展"
        )
        dialog.run()
        dialog.destroy()

    def on_restart(self, widget):
        """重启托盘应用"""
        print("重启应用...")
        Gtk.main_quit()
        # 使用 spawn 重新启动当前进程
        import os
        try:
            os.execv(sys.executable, [sys.executable] + sys.argv)
        except Exception as e:
            print(f"重启失败: {e}")

    def on_quit(self, widget):
        """退出"""
        print("退出应用...")
        Gtk.main_quit()

    # ========================================================================
    # 配置文件监听
    # ========================================================================

    def _get_config_file(self) -> Path:
        """
        获取用户配置文件路径

        Returns:
            配置文件路径
        """
        return Path.home() / ".config" / "dfm-tools" / "tray.json"

    def _start_config_monitor(self):
        """启动配置文件监听"""
        config_file = self._get_config_file()

        # 如果配置文件不存在，监听其父目录
        monitor_path = config_file if config_file.exists() else config_file.parent

        try:
            # 创建 Gio 文件对象
            gfile = Gio.File.new_for_path(str(monitor_path))

            # 创建文件监听器
            self._config_monitor = gfile.monitor_file(
                Gio.FileMonitorFlags.NONE,
                None
            )

            # 连接变化信号
            self._config_monitor.connect("changed", self._on_config_changed)

        except Exception as e:
            print(f"配置监听启动失败: {e}")

    def _on_config_changed(self, _monitor, _file, _other_file, event_type):
        """
        配置文件变化回调

        Args:
            _monitor: Gio 文件监听器（未使用）
            _file: 变化的文件（未使用）
            _other_file: 其他相关文件（未使用）
            event_type: 事件类型
        """
        # 只在文件修改完成时重新加载（避免编辑过程中的临时文件）
        if event_type == Gio.FileMonitorEvent.CHANGES_DONE_HINT:
            print("检测到配置文件变化，正在重新加载...")
            self._reload_config()

    def _reload_config(self):
        """重新加载配置并重建菜单"""
        # 清除缓存
        self.config_manager._tray_config = None

        # 重新加载配置
        new_config = self.config_manager.get_tray_config()
        self.config = new_config

        # 重建菜单
        new_menu = self._create_menu()
        self.indicator.set_menu(new_menu)
        self.menu = new_menu

        print("✓ 配置已重新加载，菜单已更新")

    def run(self):
        """运行主循环"""
        signal.signal(signal.SIGINT, signal.SIG_DFL)

        print("\n托盘图标已启动！")
        print("配置方式: JSON + 插件")
        print("  - 右键托盘图标查看菜单")
        print("  - 按 Ctrl+C 或选择'退出'停止\n")

        try:
            Gtk.main()
        except KeyboardInterrupt:
            print("\n正在退出...")
            Gtk.main_quit()


# ============================================================================
# 工具函数
# ============================================================================

def get_tray_icon(config: Dict = None) -> TrayIcon:
    """
    获取托盘图标实例

    Args:
        config: 托盘配置

    Returns:
        托盘图标实例
    """
    return TrayIcon(config)

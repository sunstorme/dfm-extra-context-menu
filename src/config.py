#!/usr/bin/env python3
"""
DDE Tools 配置管理器
负责从插件生成托盘菜单配置，支持配置合并
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, List

from plugin_manager import get_plugin_manager, Plugin


# ============================================================================
# 常量定义
# ============================================================================

# 默认配置目录
DEFAULT_CONFIG_DIR = Path("/usr/share/dfm-tools")

# 用户配置目录
USER_CONFIG_DIR = Path.home() / ".config" / "dfm-tools"

# 默认配置文件
DEFAULT_CONFIG_FILE = DEFAULT_CONFIG_DIR / "default.json"

# 用户配置文件
USER_CONFIG_FILE = USER_CONFIG_DIR / "tray.json"


# ============================================================================
# 配置管理器
# ============================================================================

class ConfigManager:
    """配置管理器"""

    def __init__(self):
        """初始化配置管理器"""
        self._tray_config = None

    def load_default_config(self) -> Dict:
        """
        加载默认配置

        Returns:
            默认配置字典
        """
        if DEFAULT_CONFIG_FILE.exists():
            with open(DEFAULT_CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def load_user_config(self) -> Dict:
        """
        加载用户配置

        Returns:
            用户配置字典
        """
        if USER_CONFIG_FILE.exists():
            with open(USER_CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def save_user_config(self, config: Dict):
        """
        保存用户配置

        Args:
            config: 配置字典
        """
        USER_CONFIG_DIR.parent.mkdir(parents=True, exist_ok=True)
        USER_CONFIG_DIR.mkdir(exist_ok=True)

        with open(USER_CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

    def generate_tray_config(self) -> Dict:
        """
        从插件生成托盘菜单配置

        Returns:
            托盘配置字典
        """
        if self._tray_config is not None:
            return self._tray_config

        pm = get_plugin_manager()
        all_plugins = pm.get_all_plugins()

        # 基础配置
        config = {
            "app_id": "dfm-tools",
            "icon": "dfm-tools",  # 使用项目图标 dfm-tools.svg
            "label": "",
            "menu_items": []
        }

        # 按分组收集菜单项
        groups: Dict[str, List[Dict]] = {}

        for plugin in all_plugins.values():
            tray_cfg = plugin.tray_config
            if not tray_cfg:
                continue

            label = tray_cfg.get('label', plugin.name)
            group = tray_cfg.get('group', '其他')
            order = tray_cfg.get('order', 999)

            menu_item = {
                "type": "item",
                "label": label,
                "enabled": True,  # 托盘菜单默认启用，点击时再检查依赖
                "action": plugin.id,
                "command": plugin.command
            }

            # 添加图标
            if plugin.icon_path:
                menu_item["icon"] = str(plugin.icon_path)

            # 按分组和排序
            if group not in groups:
                groups[group] = []
            groups[group].append((order, menu_item))

        # 构建菜单
        menu_items = []

        # 预定义分组顺序
        group_order = {
            "Git工具": 1,
            "开发工具": 2,
            "构建工具": 3,
            "系统工具": 4,
            "深度工具": 5,
            "其他": 999
        }

        # 按分组顺序添加菜单项
        sorted_groups = sorted(
            groups.keys(),
            key=lambda g: (group_order.get(g, 999), g)
        )

        for group in sorted_groups:
            items = groups[group]

            # 添加分组标题
            if group != "其他":
                menu_items.append({
                    "type": "header",
                    "label": f"── {group} ──"
                })

            # 按排序权重添加菜单项
            items.sort(key=lambda x: x[0])
            for _, item in items:
                menu_items.append(item)

            # 添加分隔线
            menu_items.append({"type": "separator"})

        # 移除最后的分隔线
        if menu_items and menu_items[-1].get("type") == "separator":
            menu_items.pop()

        config["menu_items"] = menu_items + [
            {"type": "separator"},
            {"type": "item", "label": "重启", "action": "restart"},
            {"type": "item", "label": "关于", "action": "show_message"},
            {"type": "item", "label": "退出", "action": "quit"}
        ]

        self._tray_config = config
        return config

    def get_tray_config(self) -> Dict:
        """
        获取托盘配置（合并默认、插件、用户配置）

        Returns:
            最终托盘配置
        """
        # 生成基础配置（从插件）
        config = self.generate_tray_config()

        # 合并用户配置
        user_config = self.load_user_config()
        if user_config:
            # 处理 extra_menu_items（追加而不是覆盖）
            if 'extra_menu_items' in user_config:
                extra_items = user_config.pop('extra_menu_items')
                if isinstance(extra_items, list):
                    # 追加到现有菜单项
                    config['menu_items'].extend(extra_items)

            # 其他配置项深度合并
            config = self._deep_merge(config, user_config)

        # 确保核心菜单项始终存在（重启、关于、退出）
        self._ensure_core_menu_items(config)

        return config

    def _ensure_core_menu_items(self, config: Dict):
        """
        确保核心菜单项（重启、关于、退出）始终在最底部

        Args:
            config: 配置字典
        """
        menu_items = config.get('menu_items', [])

        # 核心菜单项 action 列表
        core_actions = {'restart', 'show_message', 'quit'}

        # 移除所有已存在的核心菜单项（无论位置）
        filtered_items = []
        for item in menu_items:
            if item.get('type') == 'item' and item.get('action') in core_actions:
                continue  # 跳过核心菜单项，稍后重新添加
            filtered_items.append(item)

        # 移除末尾的分隔线
        while filtered_items and filtered_items[-1].get("type") == "separator":
            filtered_items.pop()

        # 在最末尾添加核心菜单项
        core_items = [
            {"type": "separator"},
            {"type": "item", "label": "重启", "action": "restart"},
            {"type": "item", "label": "关于", "action": "show_message"},
            {"type": "item", "label": "退出", "action": "quit"}
        ]
        filtered_items.extend(core_items)

        config['menu_items'] = filtered_items

    def _deep_merge(self, base: Dict, override: Dict) -> Dict:
        """
        深度合并字典

        Args:
            base: 基础字典
            override: 覆盖字典

        Returns:
            合并后的字典
        """
        result = base.copy()

        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value

        return result


# ============================================================================
# 工具函数
# ============================================================================

def get_config_manager() -> ConfigManager:
    """
    获取配置管理器单例

    Returns:
        配置管理器实例
    """
    if not hasattr(get_config_manager, '_instance'):
        get_config_manager._instance = ConfigManager()
    return get_config_manager._instance


# ============================================================================
# 测试代码
# ============================================================================

if __name__ == "__main__":
    cm = get_config_manager()

    print("=" * 50)
    print("DDE Tools 配置管理器")
    print("=" * 50)
    print()

    config = cm.get_tray_config()

    print(f"App ID: {config.get('app_id')}")
    print(f"Icon: {config.get('icon')}")
    print(f"Menu Items: {len(config.get('menu_items', []))}")
    print()

    print("托盘菜单结构:")
    for item in config.get('menu_items', []):
        item_type = item.get('type', 'item')
        if item_type == 'separator':
            print("  " + "─" * 20)
        elif item_type == 'header':
            print(f"  {item.get('label')}")
        else:
            label = item.get('label', '')
            enabled = "✓" if item.get('enabled', True) else "✗"
            print(f"  {enabled} {label}")

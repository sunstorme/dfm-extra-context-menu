#!/usr/bin/env python3
"""
DFM Tools 插件管理器
负责插件的发现、加载和依赖检测
"""

import os
import json
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# ============================================================================
# 常量定义
# ============================================================================

# 系统插件目录
SYSTEM_PLUGIN_DIR = Path("/usr/share/dfm-tools/plugins")

# 用户插件目录
USER_PLUGIN_DIR = Path.home() / ".config" / "dfm-tools" / "plugins"

# 插件声明文件名
PLUGIN_MANIFEST = "plugin.json"

# 插件文件扩展名
LAUNCHER_EXTENSIONS = [".sh"]


# ============================================================================
# 插件类
# ============================================================================

class Plugin:
    """插件信息类"""

    def __init__(self, manifest_path: Path, plugin_dir: Path):
        """
        初始化插件

        Args:
            manifest_path: plugin.json 文件路径
            plugin_dir: 插件目录路径
        """
        self.manifest_path = manifest_path
        self.plugin_dir = plugin_dir
        self._manifest = None
        self._available = None
        self._missing_dep = None

    @property
    def manifest(self) -> Dict:
        """插件声明内容"""
        if self._manifest is None:
            with open(self.manifest_path, 'r', encoding='utf-8') as f:
                self._manifest = json.load(f)
        return self._manifest

    @property
    def id(self) -> str:
        """插件 ID"""
        return self.manifest.get('id', self.plugin_dir.name)

    @property
    def name(self) -> str:
        """插件名称"""
        return self.manifest.get('name', self.id)

    @property
    def name_zh_CN(self) -> str:
        """中文名称"""
        return self.manifest.get('name_zh_CN', self.name)

    @property
    def description(self) -> str:
        """描述"""
        return self.manifest.get('description', '')

    @property
    def description_zh_CN(self) -> str:
        """中文描述"""
        return self.manifest.get('description_zh_CN', self.description)

    @property
    def icon(self) -> str:
        """图标文件名"""
        return self.manifest.get('icon', 'application.svg')

    @property
    def icon_path(self) -> Optional[Path]:
        """图标文件完整路径"""
        icon_file = self.plugin_dir / self.icon
        return icon_file if icon_file.exists() else None

    @property
    def category(self) -> str:
        """分类"""
        return self.manifest.get('category', 'other')

    @property
    def depends(self) -> List[str]:
        """依赖列表"""
        return self.manifest.get('depends', [])

    @property
    def menu_types(self) -> List[str]:
        """文件管理器菜单类型"""
        return self.manifest.get('menu_types', [])

    @property
    def command(self) -> Optional[str]:
        """启动命令"""
        return self.manifest.get('command')

    @property
    def launcher_path(self) -> Optional[Path]:
        """启动脚本路径"""
        if self.command:
            # 从 command 中提取启动脚本名
            # 例如: /usr/bin/gitk-launcher.sh %p -> gitk-launcher.sh
            cmd_parts = self.command.split()
            if cmd_parts:
                launcher_name = Path(cmd_parts[0]).name
                launcher_path = self.plugin_dir / launcher_name
                return launcher_path if launcher_path.exists() else None
        return None

    @property
    def tray_config(self) -> Dict:
        """托盘菜单配置"""
        return self.manifest.get('tray', {})

    def check_dependencies(self) -> Tuple[bool, Optional[str]]:
        """
        检查插件依赖是否满足

        Returns:
            (是否满足, 缺失的依赖名)
        """
        if self._available is not None:
            return self._available, self._missing_dep

        for dep in self.depends:
            if not shutil.which(dep):
                self._available = False
                self._missing_dep = dep
                return False, dep

        self._available = True
        self._missing_dep = None
        return True, None

    @property
    def available(self) -> bool:
        """插件是否可用（依赖满足）"""
        available, _ = self.check_dependencies()
        return available

    @property
    def missing_dep(self) -> Optional[str]:
        """缺失的依赖"""
        _, missing = self.check_dependencies()
        return missing


# ============================================================================
# 插件管理器
# ============================================================================

class PluginManager:
    """插件管理器"""

    def __init__(self):
        """初始化插件管理器"""
        self._plugins: Dict[str, Plugin] = {}
        self._scan_directories()

    def _scan_directories(self):
        """扫描插件目录"""
        # 扫描系统插件目录
        if SYSTEM_PLUGIN_DIR.exists():
            self._scan_directory(SYSTEM_PLUGIN_DIR)

        # 扫描用户插件目录
        if USER_PLUGIN_DIR.exists():
            self._scan_directory(USER_PLUGIN_DIR)

    def _scan_directory(self, plugin_dir: Path):
        """
        扫描指定目录下的插件

        Args:
            plugin_dir: 插件目录
        """
        for item in plugin_dir.iterdir():
            if not item.is_dir():
                continue

            manifest_path = item / PLUGIN_MANIFEST
            if not manifest_path.exists():
                continue

            try:
                plugin = Plugin(manifest_path, item)
                self._plugins[plugin.id] = plugin
            except Exception as e:
                print(f"警告: 加载插件失败 {item}: {e}")

    def get_plugin(self, plugin_id: str) -> Optional[Plugin]:
        """
        获取指定插件

        Args:
            plugin_id: 插件 ID

        Returns:
            插件对象，不存在则返回 None
        """
        return self._plugins.get(plugin_id)

    def get_all_plugins(self) -> Dict[str, Plugin]:
        """获取所有插件"""
        return self._plugins.copy()

    def get_enabled_plugins(self) -> Dict[str, Plugin]:
        """
        获取已启用的插件（依赖满足）

        Returns:
            可用插件字典
        """
        return {
            pid: plugin
            for pid, plugin in self._plugins.items()
            if plugin.available
        }

    def get_disabled_plugins(self) -> Dict[str, Plugin]:
        """
        获取已禁用的插件（依赖不满足）

        Returns:
            不可用插件字典
        """
        return {
            pid: plugin
            for pid, plugin in self._plugins.items()
            if not plugin.available
        }

    def reload(self):
        """重新扫描插件目录"""
        self._plugins.clear()
        self._scan_directories()


# ============================================================================
# 工具函数
# ============================================================================

def get_plugin_manager() -> PluginManager:
    """
    获取插件管理器单例

    Returns:
        插件管理器实例
    """
    if not hasattr(get_plugin_manager, '_instance'):
        get_plugin_manager._instance = PluginManager()
    return get_plugin_manager._instance


# ============================================================================
# 测试代码
# ============================================================================

if __name__ == "__main__":
    pm = get_plugin_manager()

    print("=" * 50)
    print("DFM Tools 插件管理器")
    print("=" * 50)
    print()

    print(f"系统插件目录: {SYSTEM_PLUGIN_DIR}")
    print(f"用户插件目录: {USER_PLUGIN_DIR}")
    print()

    all_plugins = pm.get_all_plugins()
    enabled_plugins = pm.get_enabled_plugins()
    disabled_plugins = pm.get_disabled_plugins()

    print(f"插件总数: {len(all_plugins)}")
    print(f"已启用: {len(enabled_plugins)}")
    print(f"已禁用: {len(disabled_plugins)}")
    print()

    print("已启用的插件:")
    for pid, plugin in enabled_plugins.items():
        print(f"  ✓ {plugin.name} ({plugin.id})")

    print()

    print("已禁用的插件:")
    for pid, plugin in disabled_plugins.items():
        print(f"  ✗ {plugin.name} ({plugin.id}) - 缺少依赖: {plugin.missing_dep}")

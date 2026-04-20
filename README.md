# DDE Tools - 开发工具箱

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

为深度桌面环境（DDE）提供系统托盘和文件管理器右键菜单集成的开发工具箱。

## 项目简介

DDE Tools 是一个统一的开发工具箱，通过插件化架构提供：
- **系统托盘图标** - 快速访问开发工具的统一入口
- **文件管理器集成** - 右键菜单扩展，支持常用开发操作
- **外部配置扩展** - 支持用户自定义 JSON 配置添加新功能

## 功能特性

### 🛠️ 集成工具

- **Gitk** - Git 仓库历史可视化工具
- **Visual Studio Code** - 跨平台代码编辑器
- **Qt Creator** - Qt 开发 IDE
- **D-Feet** - D-Bus 调试工具
- **DDE DConfig 编辑器** - 系统配置管理
- **DEB 构建器** - 快速构建 Debian 包
- **DEB 包管理器** - 下载和管理 DEB 包
- **项目下载器** - 从各种源下载项目
- **更新日志管理** - 自动更新 changelog

### 🔌 插件化架构

- JSON 声明式插件配置
- 运行时依赖检测
- 自动菜单分组和排序
- 支持用户自定义扩展

### 🎨 双入口设计

- **系统托盘** - 常驻托盘，快速访问
- **右键菜单** - 文件管理器上下文集成

## 安装

### 从 Debian 包安装

```bash
# 安装主包
sudo dpkg -i dfm-tools_*.deb

# 修复依赖（如果需要）
sudo apt-get install -f
```

### 运行

```bash
# 启动系统托盘
dfm-tools --tray

# 或直接运行
dfm-tools
```

## 使用方法

### 系统托盘

托盘菜单按功能分组：

```
├── Git 工具
│   └── Gitk
├── 开发工具
│   ├── D-Feet
│   ├── 构建DEB包
│   ├── DEB 包管理
│   ├── 项目下载器
│   └── 更新日志
├── 系统工具
│   └── DConfig 编辑器
├── IDE
│   ├── VSCode
│   └── Qt Creator
└── 退出
```

### 文件管理器右键菜单

在 DDE 文件管理器中右键点击：
- **空白区域** - 显示项目下载器等工具
- **单个目录** - 显示 Gitk、VSCode 等工具
- **多个文件/目录** - 显示批量操作工具

## 外部配置扩展

DDE Tools 支持通过 JSON 配置文件自定义托盘菜单，无需修改代码。

### 配置文件位置

```bash
~/.config/dfm-tools/tray.json
```

### 示例配置

```json
{
  "menu_items": [
    {
      "type": "header",
      "label": "── 我的工具 ──"
    },
    {
      "type": "item",
      "label": "打开项目",
      "command": "code ~/projects"
    },
    {
      "type": "checkbox",
      "label": "启用服务",
      "command": "systemctl start my-service --user {{checked}}"
    }
  ]
}
```

详细的配置说明请参考：[外部配置扩展指南](docs/EXTERNAL_CONFIG.md)

## 插件开发

### 添加新插件

1. 在 `plugins/` 目录创建插件目录：

```bash
mkdir plugins/my-tool
cd plugins/my-tool
```

2. 创建 `plugin.json`：

```json
{
  "id": "my-tool",
  "name": "My Tool",
  "name_zh_CN": "我的工具",
  "description": "My custom development tool",
  "icon": "my-icon.svg",
  "category": "development",
  "depends": ["python3"],
  "menu_types": ["SingleDir"],
  "command": "/usr/bin/my-tool-launcher.sh %p",
  "tray": {
    "label": "我的工具",
    "group": "开发工具",
    "order": 100
  }
}
```

3. 添加启动脚本和图标：

```bash
# 创建启动脚本
cat > my-tool-launcher.sh << 'EOF'
#!/bin/bash
# 处理传入的路径
path="$1"
# 执行你的工具
/usr/bin/my-tool "$path"
EOF
chmod +x my-tool-launcher.sh

# 添加图标文件（SVG 格式）
cp /path/to/icon.svg my-icon.svg
```

4. 重新构建和安装：

```bash
dpkg-buildpackage -us -uc -b -j16
sudo dpkg -i ../dfm-tools_*.deb
```

### 插件配置字段

| 字段 | 说明 |
|------|------|
| `id` | 唯一标识符 |
| `name` | 英文名称 |
| `name_zh_CN` | 中文名称 |
| `description` | 描述 |
| `icon` | 图标文件名 |
| `category` | 分类 |
| `depends` | 依赖列表 |
| `menu_types` | 文件管理器菜单类型 |
| `command` | 启动命令 |
| `tray` | 托盘菜单配置 |

## 项目结构

```
dfm-tools/
├── src/                        # 核心模块
│   ├── main.py                 # 主入口
│   ├── tray.py                 # 托盘实现
│   ├── config.py               # 配置管理
│   ├── plugin_manager.py       # 插件管理器
│   └── executor.py             # 命令执行器
├── plugins/                    # 插件目录
│   ├── gitk/
│   ├── vscode/
│   └── ...
├── debian/                     # Debian 打包
├── autostart/                  # 自启动配置
├── integration-all/            # 文件管理器集成
└── docs/                       # 文档
```

## 依赖

### 必需依赖

- python3
- python3-gi
- gir1.2-ayatanaappindicator3-0.1

### 推荐依赖

- git, gitk
- dpkg-dev, debhelper
- python3-tk
- dde-dconfig-editor
- d-feet
- zenity | kdialog

### 可选依赖

- code (VSCode)
- qtcreator

## 开发

### 构建包

```bash
# 安装构建依赖
sudo apt-get install debhelper dh-python

# 构建
dpkg-buildpackage -us -uc -b -j16
```

### 测试

```bash
# 启动托盘（开发模式）
python3 src/main.py --tray

# 测试插件管理器
python3 -c "
import sys
sys.path.insert(0, 'src')
from plugin_manager import get_plugin_manager

pm = get_plugin_manager()
for pid, plugin in pm.get_all_plugins().items():
    print(f'{plugin.name}: {\"可用\" if plugin.available else \"不可用\"}')"
```

## 更新日志

### 1.5.6 (当前版本)

- 重构为单包架构
- 新增系统托盘入口
- 新增插件化架构
- 新增外部 JSON 配置扩展
- 支持运行时依赖检测

## 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

## 贡献

欢迎提交 Issue 和 Pull Request！

项目主页：https://gitee.com/sunstom/dfm-tools.git

# DDE File Manager Extra Context Menu Plugins

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

为深度桌面环境（DDE）文件管理器提供额外上下文菜单插件的集合，增强开发者的工作效率。

## 项目简介

`dfm-tools-plugins` 是一个为 DDE 文件管理器设计的扩展插件包，通过右键菜单提供常用的开发工具快捷访问。该项目采用模块化设计，每个功能都是独立的 Debian 包，用户可以根据需要选择性安装。

## 功能特性

### 🛠️ 开发工具集成

- **DEB 包构建器** - 快速构建 Debian 软件包
- **DEB 包保存器** - 从各种来源下载和管理 DEB 包，支持网络和本地源
- **Gitk** - Git 仓库历史可视化工具
- **Git Cola** - 图形化 Git 操作界面
- **Visual Studio Code** - 跨平台代码编辑器，智能检测工程目录
- **Qt Creator** - 跨平台 Qt 开发 IDE，智能检测 qmake/CMake 工程
- **Deepin 开发工具箱** - 从各种来源下载和管理深度项目
- **DDE DConfig 编辑器** - 系统和应用程序配置管理
- **D-Feet** - D-Bus 调试和检查工具
- **更新日志管理** - 自动更新 Debian 更新日志和版本信息

### 📦 模块化设计

每个功能都是独立的 Debian 包，支持：
- 灵活的依赖管理
- 独立的功能更新
- 按需安装和卸载
- 清晰的职责分离

## 安装方式

### 安装所有插件

```bash
sudo apt install dfm-tools-plugins
```

### 单独安装插件

```bash
# DEB 包工具
sudo apt install dfm-tools-deb-builder dfm-tools-deb-saver

# Git 工具
sudo apt install dfm-tools-gitk dfm-tools-git-cola

# 代码编辑器和 IDE
sudo apt install dfm-tools-vscode dfm-tools-qtcreator

# 项目管理工具
sudo apt install dfm-tools-deepin-project-downloader

# 系统工具
sudo apt install dfm-tools-dde-dconfig-editor dfm-tools-d-feet

# 更新日志工具
sudo apt install dfm-tools-changelog-update

# 集成菜单（包含所有工具）
sudo apt install dfm-tools-integration-all
```

## 使用方法

安装完成后，在 DDE 文件管理器中右键点击空白区域或文件夹，即可看到新增的上下文菜单选项。

### 支持的菜单类型

- `EmptyArea` - 空白区域右键菜单
- `SingleDir` - 单个目录右键菜单
- `MultiFileDirs` - 多文件/目录右键菜单

## 插件规范与贡献

本项目欢迎社区贡献新的右键菜单插件。每个插件是一个独立目录，遵循以下约定：

### 目录结构规范

```
插件名/
├── 插件名.desktop          # 必需 - FreeDesktop 桌面入口文件
├── 插件名-launcher.sh      # 可选 - 启动脚本（需可执行权限）
├── 插件名-icon.svg         # 必需 - 插件图标（SVG 格式）
└── 其他所需文件             # Python 脚本、配置文件等
```

### 开发规则

- **命名规范**：目录和文件使用小写字母加连字符（如 `deb-saver`）
- **Desktop 文件**：必须包含正确的 `Actions` 和 DDE 文件管理器菜单类型（`EmptyArea`、`SingleDir`、`MultiFileDirs`）
- **启动脚本**：使用 `.sh` 脚本包装调用，处理路径和参数传递
- **图标**：统一使用 SVG 格式，风格与现有插件保持一致
- **打包**：新增插件需同步更新 `debian/` 目录下的相关文件（见下方 Debian 打包规范）
- **依赖**：在 `debian/control` 中声明功能依赖，不硬编码路径

### Debian 打包规范

新增插件时，需要在 `debian/` 目录下创建以下文件（以 `dfm-tools-xxx` 为例）：

```
debian/
├── control                           # 必需 - 添加新的 Package 段落
├── changelog                         # 必需 - 记录版本变更
├── rules                             # 一般不需修改 - 标准 dh 构建流程
├── dfm-tools-xxx.install             # 必需 - 声明文件安装路径
├── dfm-tools-xxx.postinst            # 必需 - 注册插件到集成菜单
└── dfm-tools-xxx.prerm               # 必需 - 从集成菜单注销插件
```

#### 1. `dfm-tools-xxx.install` — 文件安装映射

每行格式：`源路径 目标安装路径`

```
xxx/xxx.desktop          usr/share/deepin/dde-file-manager/oem-menuextensions
xxx/xxx-launcher.sh      usr/bin
xxx/xxx-icon.svg         usr/share/dfm-tools-plugins
```

- `.desktop` 文件安装到 DDE 文件管理器的菜单扩展目录
- 启动脚本安装到 `/usr/bin`
- 图标安装到 `/usr/share/dfm-tools-plugins`

#### 2. `dfm-tools-xxx.postinst` — 安装后脚本

Python 脚本，负责将插件注册到 `integration-all.desktop` 的集成菜单中。核心逻辑：

- 从脚本文件名自动提取插件名（`dfm-tools-xxx.postinst` → `xxx`）
- 在 `Actions=` 行追加插件名
- 添加 `[Desktop Action xxx]` 段落，配置菜单项名称、执行命令和图标

可参考现有插件的 `.postinst` 文件（如 [dfm-tools-deb-builder.postinst](debian/dfm-tools-deb-builder.postinst)），复制后无需修改，插件名会自动从文件名提取。

#### 3. `dfm-tools-xxx.prerm` — 卸载前脚本

与 `postinst` 相反，负责从集成菜单中移除插件。逻辑：

- 从 `Actions=` 行删除插件名
- 移除对应的 `[Desktop Action xxx]` 段落

同样可复制现有 `.prerm` 文件直接使用。

#### 4. `debian/control` — 包定义

每个插件需添加一个 `Package` 段落：

```debcontrol
Package: dfm-tools-xxx
Architecture: all
Depends: ${misc:Depends},
  插件所需依赖
Description: 简短描述
 详细描述
```

同时需要在元包 `dfm-tools-plugins` 和 `dfm-tools-integration-all` 的 `Depends` 中添加 `dfm-tools-xxx`。

## 开发构建

### 构建环境要求

- Debian/Ubuntu 系统
- debhelper (>= 13)
- dpkg-dev
- build-essential

### 构建步骤

1. 克隆项目
```bash
git clone https://gitee.com/sunstom/dfm-extra-context-menu.git
cd dfm-tools-plugins
```

2. 使用快速构建脚本
```bash
./build-deb/deb-builder-launcher.sh
```

3. 或使用标准 Debian 构建流程
```bash
dpkg-buildpackage -us -uc -b
```

### 构建选项

快速构建脚本支持多种选项：
```bash
# 使用所有 CPU 核心（默认）
./build-deb/deb-builder-launcher.sh

# 使用一半 CPU 核心
./build-deb/deb-builder-launcher.sh . yes half

# 指定并行任务数
./build-deb/deb-builder-launcher.sh . yes 8

# 构建后不清理缓存
./build-deb/deb-builder-launcher.sh . no
```

## 依赖关系

### 核心依赖
- `dde-file-manager` - DDE 文件管理器
- `debhelper-compat (= 13)` - Debian 构建助手

### 功能依赖
- `git`, `gitk` - Git 版本控制
- `git-cola` - Git 图形界面
- `code` - Visual Studio Code 编辑器
- `qtcreator` - Qt Creator IDE
- `zenity | kdialog` - 图形对话框支持
- `dpkg-dev`, `debhelper` - DEB 包构建
- `python3`, `python3-tk` - Python 运行环境（DEB 保存器依赖）
- `dde-dconfig-editor` - DDE 配置编辑器
- `d-feet` - D-Bus 调试工具

## 贡献指南

欢迎提交 Issue 和 Pull Request！

1. Fork 本项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 作者

- **zhanghongyuan** - *初始开发* - [zhanghongyuan@uniontech.com](mailto:zhanghongyuan@uniontech.com)

## 致谢

- 深度桌面环境（DDE）团队
- Debian 打包社区
- 所有贡献者和用户

## 链接

- [项目主页](hhttps://gitee.com/sunstom/dfm-extra-context-menu)
- [问题反馈](https://gitee.com/sunstom/dfm-extra-context-menu/issues)
- [深度桌面环境](https://www.deepin.org/)
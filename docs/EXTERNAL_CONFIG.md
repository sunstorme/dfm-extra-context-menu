# DFM Tools 外部配置扩展指南

## 概述

DFM Tools 支持通过外部 JSON 配置文件扩展托盘菜单，用户可以：
- 覆盖默认托盘配置
- 添加自定义菜单项
- 禁用特定插件菜单项
- 修改菜单分组和排序

## 配置文件位置

用户配置文件：`~/.config/dfm-tools/tray.json`

## 配置结构

### 基础结构

```json
{
  "app_id": "dfm-tools",
  "icon": "dfm-tools",
  "label": "",
  "extra_menu_items": [...]  // 可选：追加到默认菜单之后
}
```

**字段说明**：
- `menu_items` - 完全替换默认菜单（不推荐）
- `extra_menu_items` - 追加到默认菜单之后（推荐，保留默认菜单）

### 菜单项类型

#### 1. 普通菜单项 (item)

```json
{
  "type": "item",
  "label": "我的工具",
  "enabled": true,
  "command": "/usr/bin/my-tool",
  "icon": "/path/to/icon.svg"
}
```

#### 2. 分隔线 (separator)

```json
{
  "type": "separator"
}
```

#### 3. 分组标题 (header)

```json
{
  "type": "header",
  "label": "── 我的工具 ──"
}
```

#### 4. 复选框项 (checkbox)

```json
{
  "type": "checkbox",
  "label": "启用服务",
  "enabled": true,
  "checked": false,
  "command": "systemctl start my-service --user {{checked}}",
  "shell": true
}
```

**说明**：`{{checked}}` 会被替换为 `true` 或 `false`

#### 5. 动态菜单项 (dynamic)

```json
{
  "type": "dynamic",
  "label": "计数: {count}",
  "action": "show_count"
}
```

**说明**：`{count}` 会被替换为动态数据

## 配置合并规则

用户配置与默认配置采用**深度合并**策略：

1. **覆盖**：用户配置的同级字段会覆盖默认值
2. **合并**：字典类型字段会递归合并
3. **替换**：列表类型字段（如 menu_items）会完全替换

## 示例配置

### 示例 1：添加自定义菜单项

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
      "enabled": true,
      "command": "code ~/projects"
    },
    {
      "type": "item",
      "label": "启动数据库",
      "enabled": true,
      "command": "sudo systemctl start postgresql",
      "shell": true,
      "confirm": "确定要启动 PostgreSQL 数据库吗？"
    },
    {
      "type": "separator"
    }
  ]
}
```

**注意**：此配置会**完全替换**默认菜单。

### 示例 2：简单添加自定义菜单项（推荐）

使用 `extra_menu_items` 追加菜单项到默认菜单之后，不会覆盖默认菜单：

```json
{
  "extra_menu_items": [
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
      "type": "separator"
    }
  ]
}
```

创建配置文件：

```bash
# 创建配置目录
mkdir -p ~/.config/dfm-tools

# 创建配置文件
cat > ~/.config/dfm-tools/tray.json << 'EOF'
{
  "extra_menu_items": [
    {
      "type": "header",
      "label": "── 我的工具 ──"
    },
    {
      "type": "item",
      "label": "打开项目",
      "command": "code ~/projects"
    }
  ]
}
EOF
```

重启托盘后，你的自定义菜单项会显示在默认菜单之后。

### 示例 3：使用 menu_items 完全自定义菜单

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
    }
  ]
}
```

**注意**：使用 `menu_items` 会**完全替换**默认菜单，不推荐使用。

### 示例 3：禁用特定插件菜单项

```json
{
  "menu_items": [
    {
      "type": "header",
      "label": "── Git 工具 ──"
    },
    {
      "type": "item",
      "label": "Gitk",
      "enabled": false,
      "action": "gitk"
    }
  ]
}
```

**注意**：此方法需要完整指定 menu_items，不推荐用于禁用单个项。推荐使用示例 4 的方法。

### 示例 4：使用系统命令显示信息

调用系统工具显示信息（使用 zenity 对话框）：

```json
{
  "menu_items": [
    {
      "type": "item",
      "label": "显示系统信息",
      "command": "zenity --info --text='内核: $(uname -r)\\n架构: $(uname -m)'",
      "shell": true
    }
  ]
}
```

**提示**：`shell: true` 允许使用 bash 特性如命令替换 `$()` 和换行符 `\\n`。

## 命令执行选项

### command 字段选项

| 选项 | 类型 | 说明 |
|------|------|------|
| `command` | string | 要执行的命令 |
| `shell` | boolean | 是否使用 shell 执行（默认 false） |
| `terminal` | boolean | 是否在终端中执行（默认 false） |
| `background` | boolean | 是否后台执行（默认 true） |
| `confirm` | string | 执行前确认对话框的消息 |
| `sync` | boolean | 是否同步等待执行完成（默认 false） |

### 路径占位符

| 占位符 | 说明 |
|--------|------|
| `%p` | 文件管理器传入的路径（仅限文件管理器菜单） |
| `%P` | 同 %p |
| `{{checked}}` | 复选框状态 (true/false) |
| `{variable}` | 动态数据变量 |

## 配置文件重新加载

修改配置文件后，需要重启托盘应用：

```bash
# 杀死现有进程
pkill -f "dfm-tools --tray"

# 重新启动
dfm-tools --tray
```

或通过托盘菜单选择"退出"，然后重新运行 `dfm-tools --tray`。

## 调试配置

### 验证配置文件语法

```bash
python3 -m json.tool ~/.config/dfm-tools/tray.json
```

### 查看合并后的配置

```bash
python3 -c "
import sys
sys.path.insert(0, '/usr/lib/dfm-tools')
from config import get_config_manager
import json

cm = get_config_manager()
config = cm.get_tray_config()

# 清除缓存，强制重新加载
cm._tray_config = None
config = cm.get_tray_config()

print(json.dumps(config, ensure_ascii=False, indent=2))
"
```

### 测试单个菜单项

创建临时配置文件测试：

```bash
# 备份现有配置
mv ~/.config/dfm-tools/tray.json ~/.config/dfm-tools/tray.json.bak

# 创建测试配置
cat > ~/.config/dfm-tools/tray.json << 'EOF'
{
  "app_id": "dfm-tools",
  "icon": "dfm-tools",
  "menu_items": [
    {"type": "item", "label": "测试项", "command": "echo Hello"},
    {"type": "separator"},
    {"type": "item", "label": "退出", "action": "quit"}
  ]
}
EOF

# 重启托盘查看效果
pkill -f "dfm-tools --tray" && dfm-tools --tray &
```

## 高级用法

### 自定义托盘图标

```json
{
  "icon": "/path/to/my-icon.svg"
}
```

或使用主题图标：

```json
{
  "icon": "my-custom-icon"
}
```

### 自定义托盘标签

```json
{
  "label": "Dev"
}
```

### 添加子菜单（实验性）

注意：Deepin DDE 的 StatusNotifierItem 实现可能不完全支持子菜单。

```json
{
  "menu_items": [
    {
      "type": "item",
      "label": "开发工具",
      "submenu": [
        {"type": "item", "label": "VSCode", "command": "code"},
        {"type": "item", "label": "Gitk", "command": "gitk"}
      ]
    }
  ]
}
```

## 故障排除

### 配置不生效

1. 检查文件权限：`ls -l ~/.config/dfm-tools/tray.json`
2. 验证 JSON 语法：`python3 -m json.tool ~/.config/dfm-tools/tray.json`
3. 查看托盘日志：重新启动托盘并查看终端输出

### 菜单项不显示

1. 检查 `enabled` 字段是否为 `true`
2. 验证 `command` 或 `action` 字段是否存在
3. 检查是否有语法错误

### 命令执行失败

1. 尝试在终端手动执行命令
2. 检查是否需要 `shell: true`
3. 检查命令路径是否正确（使用绝对路径）

## 参考资源

- 项目主页：https://gitee.com/sunstom/dfm-tools.git
- Ayatana AppIndicator 文档：https://github.com/AyatanaIndicators/libayatana-appindicator
- GTK+ 3 Python 文档：https://lazka.github.io/pgi-docs/

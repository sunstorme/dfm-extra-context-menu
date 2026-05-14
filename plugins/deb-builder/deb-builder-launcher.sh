#!/bin/bash

# 快速DEB包/玲珑包构建脚本
# 使用方法: ./deb-builder-launcher.sh [源码目录] [格式] [构建后清理选项] [并行任务数]
# 格式: deb(默认) | linglong | all

set -e

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# 日志函数
log() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
    # 统一用 send_notification 发送错误通知
    send_notification "构建错误" "$1" "critical" "dialog-error"
}

# 通知函数
send_notification() {
    local summary="$1"
    local body="$2"
    local urgency="${3:-normal}"  # low, normal, critical，默认 normal
    local icon="${4:-package}"    # 可选 icon，默认 package

    # 使用notify-send发送桌面通知
    if command -v notify-send >/dev/null 2>&1; then
        local urgency_param=""
        if [ -n "$urgency" ]; then
            urgency_param="-u $urgency"
        fi
        notify-send $urgency_param -a "quick-build-deb" -i "$icon" "$summary" "$body"
    else
        echo -e "${RED}[NOTIFY-ERROR]${NC} notify-send 未找到，无法发送桌面通知: $summary - $body"
    fi
}

# 清理构建缓存函数
clean_build_cache() {
    local source_dir="$1"
    
    log "开始清理构建缓存..."
    
    # 切换到源码目录执行清理
    cd "$source_dir"
    
    # 使用dh_clean清理构建缓存
    if command -v dh_clean >/dev/null 2>&1; then
        log "执行: dh_clean"
        if dh_clean; then
            success "使用dh_clean清理构建缓存成功!"
        else
            error "使用dh_clean清理构建缓存失败!"
            return 1
        fi
    else
        error "dh_clean命令未找到，请确保已安装debhelper包"
        return 1
    fi
    
    # 额外清理debian构建目录
    log "清理debian构建目录..."
    rm -rf debian/.debhelper/
    rm -rf debian/dfm-tools-*/
    rm -f debian/files debian/debhelper-build-stamp
    rm -f debian/*.log debian/*.substvars
    
    success "构建缓存清理完成!"
    
    # 发送清理完成通知
    send_notification "构建缓存清理完成" "已清理: $(basename "$source_dir")" "normal"
}

# 构建玲珑包
build_linglong() {
    local source_dir="$1"
    local packages_dir="$2"
    
    log "开始构建玲珑包..."
    
    # 检查 linglong.yaml 是否存在
    if [ ! -f "$source_dir/linglong.yaml" ]; then
        error "未找到 linglong.yaml 文件: $source_dir/linglong.yaml"
        return 1
    fi
    
    # 检查 ll-builder 是否可用
    if ! command -v ll-builder >/dev/null 2>&1; then
        error "ll-builder 命令未找到，请安装 linglong-builder 包"
        return 1
    fi
    
    # 切换到源码目录
    cd "$source_dir"

    # 发送开始构建通知
    send_notification "开始构建玲珑包" "正在构建: $(basename "$(pwd)")" "low"
    
    # 记录构建开始时间
    local build_start_time=$(date +%s)
    
    # 执行 ll-builder build
    log "执行: ll-builder build"
    if ll-builder build; then
        success "ll-builder build 成功!"
    else
        error "ll-builder build 失败!"
        return 1
    fi
    
    # 尝试导出玲珑包
    local export_success=false
    local export_type=""
    
    # 先尝试导出 UAB 文件
    log "执行: ll-builder export (导出 UAB)"
    if ll-builder export; then
        export_success=true
        export_type="UAB"
        success "玲珑包 UAB 导出成功!"
    else
        log "UAB 导出失败，尝试导出 layer 文件..."
        # UAB 导出失败，尝试导出 layer
        log "执行: ll-builder export --layer"
        if ll-builder export --layer; then
            export_success=true
            export_type="Layer"
            success "玲珑包 Layer 导出成功!"
        else
            error "玲珑包导出失败 (UAB 和 Layer 都失败)!"
            return 1
        fi
    fi
    
    local build_end_time=$(date +%s)
    local build_duration=$((build_end_time - build_start_time))
    local build_minutes=$((build_duration / 60))
    local build_seconds=$((build_duration % 60))
    
    success "玲珑包构建成功! (导出格式: $export_type)"
    success "构建耗时: ${build_minutes}分${build_seconds}秒"

    # 移动构建产物到packages目录
    move_linglong_packages "$source_dir" "$packages_dir"

    # 构建完成后清理缓存文件
    log "清理玲珑构建缓存文件 (*.install)..."
    local install_files=$(find "$source_dir" -maxdepth 1 -name "*.install" ! -path "$source_dir/debian/*" 2>/dev/null || true)
    if [ -n "$install_files" ]; then
        while IFS= read -r install_file; do
            if [ -f "$install_file" ]; then
                log "  删除缓存: $(basename "$install_file")"
                rm -f "$install_file"
            fi
        done <<< "$install_files"
        success "已清理 *.install 缓存文件"
    else
        log "未发现 *.install 缓存文件"
    fi

    # 清理构建目录 (build/, obj-*/, linglong/)
    log "清理构建目录 (build/, obj-*/, linglong/)..."
    rm -rf "$source_dir/build" "$source_dir/linglong" 2>/dev/null || true
    rm -rf "$source_dir"/obj-* 2>/dev/null || true
    success "已清理构建目录"

    # 发送成功通知
    send_notification "玲珑包构建完成" "成功构建: $(basename "$source_dir") ($export_type)" "normal"

    return 0
}

# 移动玲珑包构建产物到packages目录
move_linglong_packages() {
    local source_dir="$1"
    local packages_dir="$2"
    
    log "移动玲珑包构建产物到packages目录..."
    
    # 创建packages目录（如果不存在）
    if [ ! -d "$packages_dir" ]; then
        log "创建packages目录: $packages_dir"
        mkdir -p "$packages_dir"
    fi
    
    local moved_count=0
    local uab_count=0
    local layer_count=0
    
    # 查找并移动 .uab 文件
    local uab_files=$(find "$source_dir" -maxdepth 2 -name "*.uab" 2>/dev/null || true)
    if [ -n "$uab_files" ]; then
        while IFS= read -r pkg_file; do
            if [ -f "$pkg_file" ]; then
                local pkg_name=$(basename "$pkg_file")
                log "  移动 UAB: $pkg_name"
                mv "$pkg_file" "$packages_dir/"
                moved_count=$((moved_count + 1))
                uab_count=$((uab_count + 1))
            fi
        done <<< "$uab_files"
    fi
    
    # 查找并移动 .layer 文件
    local layer_files=$(find "$source_dir" -maxdepth 2 -name "*.layer" 2>/dev/null || true)
    if [ -n "$layer_files" ]; then
        while IFS= read -r pkg_file; do
            if [ -f "$pkg_file" ]; then
                local pkg_name=$(basename "$pkg_file")
                log "  移动 Layer: $pkg_name"
                mv "$pkg_file" "$packages_dir/"
                moved_count=$((moved_count + 1))
                layer_count=$((layer_count + 1))
            fi
        done <<< "$layer_files"
    fi
    
    # 查找并移动 .linya 文件（备用格式）
    local linya_files=$(find "$source_dir" -maxdepth 2 -name "*.linya" 2>/dev/null || true)
    if [ -n "$linya_files" ]; then
        while IFS= read -r pkg_file; do
            if [ -f "$pkg_file" ]; then
                local pkg_name=$(basename "$pkg_file")
                log "  移动 Layer (.linya): $pkg_name"
                mv "$pkg_file" "$packages_dir/"
                moved_count=$((moved_count + 1))
                layer_count=$((layer_count + 1))
            fi
        done <<< "$linya_files"
    fi
    
    if [ $moved_count -gt 0 ]; then
        local summary=""
        if [ $uab_count -gt 0 ] && [ $layer_count -gt 0 ]; then
            summary=" ($uab_count 个 UAB, $layer_count 个 Layer)"
        elif [ $uab_count -gt 0 ]; then
            summary=" ($uab_count 个 UAB)"
        elif [ $layer_count -gt 0 ]; then
            summary=" ($layer_count 个 Layer)"
        fi
        success "已移动 $moved_count 个玲珑包${summary}到: $packages_dir"
        
        # 显示packages目录中的玲珑包文件
        echo ""
        log "packages目录中的玲珑包文件:"
        ls -lh "$packages_dir"/*.{uab,layer,linya} 2>/dev/null || true
    else
        log "未找到 .uab、.layer 或 .linya 文件"
    fi
    
    # 使用系统默认应用打开packages目录
    log "正在打开packages目录..."
    if command -v xdg-open >/dev/null 2>&1; then
        xdg-open "$packages_dir" >/dev/null 2>&1 &
        success "已打开packages目录"
    elif command -v deepin-file-manager >/dev/null 2>&1; then
        deepin-file-manager "$packages_dir" >/dev/null 2>&1 &
        success "已打开packages目录"
    elif command -v nautilus >/dev/null 2>&1; then
        nautilus "$packages_dir" >/dev/null 2>&1 &
        success "已打开packages目录"
    elif command -v dolphin >/dev/null 2>&1; then
        dolphin "$packages_dir" >/dev/null 2>&1 &
        success "已打开packages目录"
    else
        log "提示: 无法自动打开packages目录，请手动打开: $packages_dir"
    fi
    
    return 0
}

# 移动构建产物到packages目录（分类存储）
move_built_packages() {
    local source_dir="$1"
    local packages_dir="$2"
    local project_name=""

    # 尝试从源码目录名获取项目名
    project_name=$(basename "$source_dir")

    # 如果源码目录是当前目录，尝试从debian/control文件获取项目名
    if [ "$project_name" = "." ]; then
        project_name=$(basename "$(pwd)")
    fi

    # 获取当前构建产生的deb包（通过时间戳筛选最近2分钟内创建的包）
    local recent_debs=$(find .. -maxdepth 1 -name "*.deb" -mmin -2 2>/dev/null || true)

    # 如果没有找到最近的包，则尝试通过项目名筛选
    if [ -z "$recent_debs" ]; then
        recent_debs=$(find .. -maxdepth 1 -name "*${project_name}*.deb" -o -name "dfm-tools-*.deb" 2>/dev/null || true)
    fi

    if [ -z "$recent_debs" ]; then
        error "未找到当前项目的构建产物"
        return 1
    fi

    # 创建packages目录及子目录
    local app_dir="$packages_dir/app"
    local debug_dir="$packages_dir/debug"
    local dev_dir="$packages_dir/dev"

    mkdir -p "$app_dir" "$debug_dir" "$dev_dir"

    # 用于记录要打开的 app 目录（只打开当前项目的）
    local open_app_dir=""

    # 移动构建产物到对应分类目录
    log "移动构建产物到packages目录（分类存储）..."
    local moved_count=0
    local app_count=0
    local debug_count=0
    local dev_count=0

    # 分类移动.deb包
    while IFS= read -r deb_file; do
        if [ -f "$deb_file" ]; then
            local deb_name=$(basename "$deb_file")
            local target_dir="$app_dir"
            local pkg_type="普通包"

            # 判断包类型
            if [[ "$deb_name" =~ dbgsym ]]; then
                target_dir="$debug_dir"
                pkg_type="调试包"
                debug_count=$((debug_count + 1))
            elif [[ "$deb_name" =~ \-dev_ ]]; then
                target_dir="$dev_dir"
                pkg_type="开发包"
                dev_count=$((dev_count + 1))
            else
                app_count=$((app_count + 1))
                # 从包名中提取项目名称（第一个下划线之前的部分）
                local pkg_name="${deb_name%%_*}"
                local project_app_dir="$app_dir/$pkg_name"

                # 创建项目子目录
                mkdir -p "$project_app_dir"
                target_dir="$project_app_dir"

                # 记录第一个遇到的 app 目录用于打开文件管理器
                if [ -z "$open_app_dir" ]; then
                    open_app_dir="$project_app_dir"
                fi
            fi

            log "  移动 [$pkg_type]: $deb_name"
            mv "$deb_file" "$target_dir/"
            moved_count=$((moved_count + 1))
        fi
    done <<< "$recent_debs"
    
    # 移动对应的.buildinfo和.changes文件（跟随主包分类）
    local buildinfo_files=$(find .. -maxdepth 1 -name "*.buildinfo" -mmin -2 2>/dev/null || true)
    if [ -z "$buildinfo_files" ]; then
        buildinfo_files=$(find .. -maxdepth 1 -name "*${project_name}*.buildinfo" 2>/dev/null || true)
    fi

    while IFS= read -r buildinfo_file; do
        if [ -f "$buildinfo_file" ]; then
            local buildinfo_name=$(basename "$buildinfo_file")
            log "  移动 [元数据]: $buildinfo_name"
            mv "$buildinfo_file" "$packages_dir/"
            moved_count=$((moved_count + 1))
        fi
    done <<< "$buildinfo_files"

    local changes_files=$(find .. -maxdepth 1 -name "*.changes" -mmin -2 2>/dev/null || true)
    if [ -z "$changes_files" ]; then
        changes_files=$(find .. -maxdepth 1 -name "*${project_name}*.changes" 2>/dev/null || true)
    fi

    while IFS= read -r changes_file; do
        if [ -f "$changes_file" ]; then
            local changes_name=$(basename "$changes_file")
            log "  移动 [元数据]: $changes_name"
            mv "$changes_file" "$packages_dir/"
            moved_count=$((moved_count + 1))
        fi
    done <<< "$changes_files"

    # 显示分类统计
    success "已移动 $moved_count 个文件到: $packages_dir"
    success "  - 普通包: $app_count 个 (app/<项目名>/)"
    if [ $debug_count -gt 0 ]; then
        success "  - 调试包: $debug_count 个 (debug/)"
    fi
    if [ $dev_count -gt 0 ]; then
        success "  - 开发包: $dev_count 个 (dev/)"
    fi

    # 使用系统默认应用打开当前项目的 app 目录
    local open_dir="$open_app_dir"
    if [ -z "$open_dir" ]; then
        # 如果没有普通包，回退到打开 packages 根目录
        open_dir="$packages_dir"
    fi

    log "正在打开目录..."
    if command -v xdg-open >/dev/null 2>&1; then
        xdg-open "$open_dir" >/dev/null 2>&1 &
        success "已打开目录: $open_dir"
    elif command -v deepin-file-manager >/dev/null 2>&1; then
        deepin-file-manager "$open_dir" >/dev/null 2>&1 &
        success "已打开目录: $open_dir"
    elif command -v nautilus >/dev/null 2>&1; then
        nautilus "$open_dir" >/dev/null 2>&1 &
        success "已打开目录: $open_dir"
    elif command -v dolphin >/dev/null 2>&1; then
        dolphin "$open_dir" >/dev/null 2>&1 &
        success "已打开目录: $open_dir"
    else
        log "提示: 无法自动打开目录，请手动打开: $open_dir"
    fi

    return 0
}

# 显示构建产物路径（分类显示）
show_built_packages() {
    local source_dir="$1"
    local packages_dir="$2"
    local project_name=""

    # 尝试从源码目录名获取项目名
    project_name=$(basename "$source_dir")

    # 如果源码目录是当前目录，尝试从debian/control文件获取项目名
    if [ "$project_name" = "." ]; then
        project_name=$(basename "$(pwd)")
    fi

    # 检查packages目录是否存在
    if [ ! -d "$packages_dir" ]; then
        error "packages目录不存在: $packages_dir"
        return 1
    fi

    # 定义子目录
    local app_dir="$packages_dir/app"
    local debug_dir="$packages_dir/debug"
    local dev_dir="$packages_dir/dev"

    # 从packages子目录获取当前构建产生的deb包
    # 普通包现在在 app/<项目名>/ 子目录中，需要递归查找
    local app_debs=$(find "$app_dir" -maxdepth 2 -name "*.deb" -mmin -2 2>/dev/null || true)
    local debug_debs=$(find "$debug_dir" -maxdepth 1 -name "*.deb" -mmin -2 2>/dev/null || true)
    local dev_debs=$(find "$dev_dir" -maxdepth 1 -name "*.deb" -mmin -2 2>/dev/null || true)

    # 如果没有找到最近的包，则尝试通过项目名筛选
    if [ -z "$app_debs" ]; then
        app_debs=$(find "$app_dir" -maxdepth 2 -name "*${project_name}*.deb" 2>/dev/null || true)
    fi
    if [ -z "$debug_debs" ]; then
        debug_debs=$(find "$debug_dir" -maxdepth 1 -name "*${project_name}*.deb" 2>/dev/null || true)
    fi
    if [ -z "$dev_debs" ]; then
        dev_debs=$(find "$dev_dir" -maxdepth 1 -name "*${project_name}*.deb" 2>/dev/null || true)
    fi

    # 显示分类构建产物
    if [ -n "$app_debs" ] || [ -n "$debug_debs" ] || [ -n "$dev_debs" ]; then
        log "构建产物 (已按类型分类存储):"
        echo ""

        # 显示普通应用包
        if [ -n "$app_debs" ]; then
            log "普通应用包 (app/<项目名>/):"
            ls -lh $app_debs
            echo ""
        fi

        # 显示调试包
        if [ -n "$debug_debs" ]; then
            log "调试符号包 (debug/):"
            ls -lh $debug_debs
            echo ""
        fi

        # 显示开发包
        if [ -n "$dev_debs" ]; then
            log "开发包 (dev/):"
            ls -lh $dev_debs
            echo ""
        fi

        # 显示所有元数据文件
        log "元数据文件 (.buildinfo, .changes):"
        ls -lh "$packages_dir"/*.{buildinfo,changes} 2>/dev/null || true
        echo ""

        # 生成安装命令（按分类）
        if [ -n "$app_debs" ]; then
            local app_files=$(echo "$app_debs" | tr '\n' ' ')
            log "普通应用包安装命令:"
            log "  sudo apt install $app_files"
            log "  sudo dpkg -i $app_files"
            echo ""
        fi

        if [ -n "$dev_debs" ]; then
            local dev_files=$(echo "$dev_debs" | tr '\n' ' ')
            log "开发包安装命令 (用于开发编译):"
            log "  sudo apt install $dev_files"
            log "  sudo dpkg -i $dev_files"
            echo ""
        fi

        if [ -n "$debug_debs" ]; then
            local debug_files=$(echo "$debug_debs" | tr '\n' ' ')
            log "调试符号包安装命令 (用于调试崩溃):"
            log "  sudo apt install $debug_files"
            log "  sudo dpkg -i $debug_files"
            echo ""
        fi

        log "全部安装命令 (包含所有包):"
        local all_debs=""
        if [ -n "$app_debs" ]; then
            all_debs="$all_debs $(echo "$app_debs" | tr '\n' ' ')"
        fi
        if [ -n "$dev_debs" ]; then
            all_debs="$all_debs $(echo "$dev_debs" | tr '\n' ' ')"
        fi
        if [ -n "$debug_debs" ]; then
            all_debs="$all_debs $(echo "$debug_debs" | tr '\n' ' ')"
        fi
        log "  sudo apt install$all_debs"
        log "  sudo dpkg -i$all_debs"
    else
        error "未找到当前项目的构建产物"
    fi
}

# 主函数
main() {
    local source_dir
    local format
    local clean_after_build
    local parallel_jobs
    
    # 智能解析参数：如果第一个参数是格式名称，则使用当前目录
    if [ "${1:-}" = "deb" ] || [ "${1:-}" = "linglong" ] || [ "${1:-}" = "ll" ] || [ "${1:-}" = "all" ]; then
        source_dir="."
        format="${1:-deb}"
        clean_after_build="${2:-yes}"
        parallel_jobs="${3:-auto}"
    else
        source_dir="${1:-.}"
        format="${2:-deb}"
        clean_after_build="${3:-yes}"
        parallel_jobs="${4:-auto}"
    fi

    # 规范化格式名：将简写转换为完整名称
    if [ "$format" = "ll" ]; then
        format="linglong"
    fi
    
    # 确定packages目录路径（项目目录的上一级目录的packages子目录）
    local project_parent_dir="$(cd "$source_dir/.." && pwd)"
    local packages_dir="$project_parent_dir/packages"
    
    # 构建结果标志
    local deb_build_success=false
    local linglong_build_success=false
    
    echo "=========================================="
    echo "        快速包构建工具"
    echo "=========================================="
    echo
    
    # 检查源码目录
    if [ ! -d "$source_dir" ]; then
        error "源码目录不存在: $source_dir"
        exit 1
    fi
    
    # 根据构建格式检查必要文件
    if [ "$format" = "deb" ] || [ "$format" = "all" ]; then
        if [ ! -d "$source_dir/debian" ]; then
            error "缺少debian目录: $source_dir/debian"
            exit 1
        fi
    fi
    
    if [ "$format" = "linglong" ] || [ "$format" = "all" ]; then
        if [ ! -f "$source_dir/linglong.yaml" ]; then
            error "缺少linglong.yaml文件: $source_dir/linglong.yaml"
            exit 1
        fi
        
        # 检查 ll-builder 是否可用
        if ! command -v ll-builder >/dev/null 2>&1; then
            error "ll-builder 命令未找到，请安装 linglong-builder 包"
            exit 1
        fi
    fi
    
    # 切换到源码目录
    cd "$source_dir"
    
    # 确定并行任务数
    local cpu_count=$(nproc)
    local parallel_num
    
    if [ "$parallel_jobs" = "auto" ]; then
        parallel_num=$cpu_count
    elif [ "$parallel_jobs" = "half" ]; then
        parallel_num=$((cpu_count / 2))
        if [ $parallel_num -lt 1 ]; then
            parallel_num=1
        fi
    elif [[ "$parallel_jobs" =~ ^[0-9]+$ ]]; then
        parallel_num=$parallel_jobs
    else
        error "无效的并行任务数: $parallel_jobs"
        exit 1
    fi
    
    log "源码目录: $(pwd)"
    log "构建格式: $format"
    log "构建后清理: $clean_after_build"
    log "系统CPU核心数: $cpu_count"
    log "使用并行任务数: $parallel_num"
    log "构建产物将移动到: $packages_dir"
    echo ""
    
    # 构建 DEB 包
    if [ "$format" = "deb" ] || [ "$format" = "all" ]; then
        log "========== 开始构建 DEB 包 =========="
        
        # 设置构建环境
        export DEB_BUILD_OPTIONS="parallel=$parallel_num"
        
        # 验证debian/rules是否支持并行构建
        log "验证debian/rules配置..."
        if grep -q "parallel" debian/rules; then
            success "debian/rules已配置并行构建支持"
        else
            log "警告: debian/rules可能未正确配置并行构建"
            log "当前DEB_BUILD_OPTIONS=$DEB_BUILD_OPTIONS"
        fi
        
        # 执行构建命令
        log "执行: dpkg-buildpackage -us -uc -b"
        log "构建选项: DEB_BUILD_OPTIONS=$DEB_BUILD_OPTIONS"
        
        # 记录构建开始时间
        local build_start_time=$(date +%s)
        
        # 发送开始构建通知
        send_notification "开始构建DEB包" "正在构建: $(basename "$(pwd)") (并行: $parallel_num)" "low"
        
        if dpkg-buildpackage -us -uc -b; then
            local build_end_time=$(date +%s)
            local build_duration=$((build_end_time - build_start_time))
            local build_minutes=$((build_duration / 60))
            local build_seconds=$((build_duration % 60))
            
            deb_build_success=true
            success "DEB包构建成功!"
            success "构建耗时: ${build_minutes}分${build_seconds}秒 (并行任务数: $parallel_num)"
            
            # 移动构建产物到packages目录
            move_built_packages "$source_dir" "$packages_dir"
            
            # 显示构建产物
            show_built_packages "$source_dir" "$packages_dir"
            
            # 发送成功通知
            local project_name=""
            project_name=$(basename "$source_dir")
            if [ "$project_name" = "." ]; then
                project_name=$(basename "$(pwd)")
            fi
            
            # 从packages目录获取构建的deb包
            local recent_debs=$(find "$packages_dir" -maxdepth 1 -name "*.deb" -mmin -5 2>/dev/null || true)
            if [ -z "$recent_debs" ]; then
                recent_debs=$(find "$packages_dir" -maxdepth 1 -name "*${project_name}*.deb" -o -name "dfm-tools-*.deb" 2>/dev/null | head -1 || true)
            fi
            
            if [ -n "$recent_debs" ]; then
                local deb_name=$(basename "$recent_debs")
                send_notification "DEB包构建完成" "成功构建: $deb_name" "normal"
            else
                send_notification "DEB包构建完成" "构建成功，但未找到当前项目的构建产物" "normal"
            fi
            
        else
            error "DEB包构建失败!"
            
            # 发送失败通知
            send_notification "DEB包构建失败" "构建过程中出现错误，请检查构建日志" "critical"
        fi
        
        echo ""
    fi
    
    # 构建玲珑包
    if [ "$format" = "linglong" ] || [ "$format" = "all" ]; then
        log "========== 开始构建玲珑包 =========="
        
        if build_linglong "$source_dir" "$packages_dir"; then
            linglong_build_success=true
        fi
        
        echo ""
    fi
    
    # 清理构建缓存
    if [ "$clean_after_build" = "yes" ]; then
        if [ "$format" = "deb" ] || [ "$format" = "all" ]; then
            if [ "$deb_build_success" = true ]; then
                log "开始清理DEB构建缓存..."
            else
                log "DEB构建失败，开始清理构建缓存..."
            fi
            clean_build_cache "$source_dir"
        fi
    else
        log "跳过构建缓存清理"
    fi
    
    # 根据构建结果决定退出码
    if [ "$format" = "all" ]; then
        # all 模式：至少一个成功就算成功
        if [ "$deb_build_success" = true ] || [ "$linglong_build_success" = true ]; then
            exit 0
        else
            exit 1
        fi
    elif [ "$format" = "deb" ]; then
        if [ "$deb_build_success" = false ]; then
            exit 1
        fi
    elif [ "$format" = "linglong" ]; then
        if [ "$linglong_build_success" = false ]; then
            exit 1
        fi
    fi
}

# 显示帮助
if [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
    cat << EOF
快速DEB包/玲珑包构建脚本

用法: $0 [源码目录|格式] [格式] [构建后清理选项] [并行任务数]

参数:
    源码目录        包含debian目录或linglong.yaml的源码路径 (默认: 当前目录)
                    如果省略，第一个参数可以是格式名称
    格式            deb/linglong/ll/all (默认: deb)
                    deb      - 仅构建DEB包
                    linglong - 仅构建玲珑包
                    ll       - linglong的简写，仅构建玲珑包
                    all      - 同时构建DEB包和玲珑包
    构建后清理选项  yes/no (默认: yes，构建完成后自动清理构建缓存)
    并行任务数      auto/half/数字 (默认: auto)
                    auto  - 自动使用所有CPU核心
                    half  - 使用一半CPU核心
                    数字  - 指定具体的并行任务数

示例:
    $0                           # 在当前目录构建DEB包并清理，使用所有CPU核心
    $0 ll                         # 在当前目录构建玲珑包并清理（简写），使用所有CPU核心
    $0 linglong                  # 在当前目录构建玲珑包并清理，使用所有CPU核心
    $0 all                       # 在当前目录同时构建DEB包和玲珑包
    $0 /path/to/source           # 在指定目录构建DEB包并清理，使用所有CPU核心
    $0 /path/to/source ll        # 在指定目录构建玲珑包并清理（简写），使用所有CPU核心
    $0 . ll                      # 在当前目录构建玲珑包并清理（简写），使用所有CPU核心
    $0 ll no                    # 在当前目录构建玲珑包但不清理（简写），使用所有CPU核心
    $0 all yes half              # 在当前目录构建两种包并清理，使用一半CPU核心
    $0 all yes 8                 # 在当前目录构建两种包并清理，使用8个并行任务
    $0 /path/to/source ll no 4  # 在指定目录构建玲珑包但不清理（简写），使用4个并行任务

功能特性:
    - 支持DEB包和玲珑包构建 (deb/linglong/ll/all，ll为linglong简写)
    - 灵活的并行构建选项 (auto/half/指定数字)
    - 自动检测CPU核心数 (使用nproc命令)
    - DEB构建完成后自动使用dh_clean清理构建缓存
    - 玲珑构建前自动清理 .install 缓存文件（排除debian/目录）
    - 桌面通知提示构建状态
    - 显示构建产物信息
    - 构建产物自动移动到packages目录（不污染源码目录）
    - 按类型和项目名称分类存储 (app/<项目名>/、debug/、dev/)
    - 同时处理.deb、.buildinfo、.changes、.linya、.uab文件
    - 构建成功后自动打开当前项目的app目录
    - DEB_BUILD_OPTIONS环境变量正确设置

玲珑包构建依赖:
    - linglong-builder (提供 ll-builder 命令)
    - linglong.yaml 文件（项目根目录）

环境变量:
    DEB_BUILD_OPTIONS  自动设置为 parallel=N，其中N为并行任务数

构建产物:
    - DEB包: 按类型自动分类到packages目录的子目录
      * packages/app/<项目名>/   - 普通应用包（按项目名称分类）
      * packages/debug/           - 调试符号包（*dbgsym，用于调试崩溃）
      * packages/dev/             - 开发包（*-dev，包含头文件和开发库）
      * .buildinfo、.changes 文件保留在 packages/ 根目录
    - 玲珑包: .uab 或 .layer 文件会自动移动到packages目录
    - packages目录会自动创建（如果不存在）
    - 构建成功后会自动打开当前项目的 app 目录（使用系统默认文件管理器）
    - 显示分类后的安装命令（可按类型选择性安装）

EOF
    exit 0
fi

# 执行主函数
main "$@" 
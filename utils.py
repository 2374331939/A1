"""
=============================================================================
 utils.py — 工具函数模块
=============================================================================
 本模块提供图像扫描、元数据提取、路径校验等辅助功能。
 与 database.py 无直接依赖，可以独立测试。
=============================================================================
"""

import os
from pathlib import Path
from typing import Iterator, Optional

from PIL import Image, UnidentifiedImageError


# ── 支持的图像格式 ──────────────────────────────────────────────────────────
SUPPORTED_EXTENSIONS: set = {
    ".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif", ".dicom", ".dcm"
}


# ═══════════════════════════════════════════════════════════════════════════════
# 文件扫描
# ═══════════════════════════════════════════════════════════════════════════════

def scan_image_files(folder_path: str, recursive: bool = True) -> list[Path]:
    """
    扫描文件夹中的图像文件。

    参数：
        folder_path : 文件夹路径（字符串或 Path 对象）
        recursive   : 是否递归扫描子文件夹，默认 True

    返回：
        匹配的图像文件路径列表（Path 对象），按文件名排序。

    如果文件夹不存在或无法访问，返回空列表。
    """
    folder = Path(folder_path)

    if not folder.exists():
        return []
    if not folder.is_dir():
        return []

    if recursive:
        # 递归扫描所有子文件夹
        files = sorted(f for f in folder.rglob("*") if f.suffix.lower() in SUPPORTED_EXTENSIONS)
    else:
        files = sorted(f for f in folder.glob("*") if f.suffix.lower() in SUPPORTED_EXTENSIONS)

    return files


def get_image_info(image_path: Path) -> Optional[dict]:
    """
    提取一张图像的元数据。

    参数：
        image_path : 图像文件路径（Path 对象）

    返回：
        字典包含 file_path, file_name, file_size, width, height；
        如果文件无法打开则返回 None。
    """
    try:
        # 文件大小（字节）
        file_size = image_path.stat().st_size

        # 用 Pillow 打开图像获取尺寸
        with Image.open(image_path) as img:
            width, height = img.size

        return {
            "file_path": str(image_path.resolve()),  # 转绝对路径
            "file_name": image_path.name,
            "file_size": file_size,
            "width": width,
            "height": height,
        }

    except (FileNotFoundError, UnidentifiedImageError, OSError) as e:
        # 文件不存在、不是有效图像、或权限不足
        print(f"[警告] 无法读取图像: {image_path} — {e}")
        return None


def batch_scan_and_import(folder_path: str,
                          import_callback,
                          recursive: bool = True) -> dict:
    """
    批量扫描文件夹并逐张导入数据库。

    这是一个生成器函数，每次 yield 一个进度报告字典，
    方便 Streamlit 页面展示进度条。

    参数：
        folder_path     : 要扫描的文件夹路径
        import_callback : 导入回调函数，接收 (file_path, file_name, file_size, width, height)
        recursive       : 是否递归子文件夹

    Yields:
        {
            "current": 当前处理序号,
            "total":   总文件数,
            "file":    当前处理的文件名,
            "success": 是否成功,
            "message": 状态消息
        }

    用法示例：
        for report in batch_scan_and_import("/path", database.add_image):
            print(f"进度: {report['current']}/{report['total']}")
    """
    files = scan_image_files(folder_path, recursive=recursive)

    if not files:
        yield {
            "current": 0,
            "total": 0,
            "file": "",
            "success": False,
            "message": "未找到任何支持的图像文件（支持格式：PNG, JPG, BMP, TIFF）",
        }
        return

    total = len(files)
    success_count = 0
    skip_count = 0
    error_count = 0

    for i, file_path in enumerate(files, start=1):
        info = get_image_info(file_path)

        if info is None:
            error_count += 1
            yield {
                "current": i,
                "total": total,
                "file": file_path.name,
                "success": False,
                "message": f"无法打开文件: {file_path.name}",
            }
            continue

        # 调用传入的回调函数（通常是 database.add_image）
        result = import_callback(
            info["file_path"],
            info["file_name"],
            info["file_size"],
            info["width"],
            info["height"],
        )

        if result is not None:
            success_count += 1
            yield {
                "current": i,
                "total": total,
                "file": file_path.name,
                "success": True,
                "message": f"已导入: {file_path.name}",
            }
        else:
            skip_count += 1
            yield {
                "current": i,
                "total": total,
                "file": file_path.name,
                "success": True,
                "message": f"已跳过（重复）: {file_path.name}",
            }

    # 最终汇总
    yield {
        "current": total,
        "total": total,
        "file": "",
        "success": True,
        "message": (
            f"扫描完成！成功 {success_count} 张，"
            f"跳过 {skip_count} 张，"
            f"失败 {error_count} 张"
        ),
        "done": True,
        "summary": {
            "success": success_count,
            "skipped": skip_count,
            "errors": error_count,
        },
    }


# ═══════════════════════════════════════════════════════════════════════════════
# 图像加载（带缓存）
# ═══════════════════════════════════════════════════════════════════════════════

def load_image_safe(image_path: str, max_size: tuple = (800, 800)) -> Optional[Image.Image]:
    """
    安全加载图像，限制最大尺寸以节省内存。

    参数：
        image_path : 图像文件路径
        max_size   : (宽, 高) 最大尺寸，超过则等比例缩放到此范围内

    返回：
        PIL Image 对象；如果无法加载则返回 None。
    """
    try:
        img = Image.open(image_path)

        # 如果是灰度图（如很多 X 光片），转 RGB 以便统一处理
        if img.mode != "RGB":
            img = img.convert("RGB")

        # 如果图像太大，等比例缩小
        if img.width > max_size[0] or img.height > max_size[1]:
            img.thumbnail(max_size, Image.Resampling.LANCZOS)

        return img

    except Exception as e:
        print(f"[错误] 加载图像失败: {image_path} — {e}")
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# 字符串辅助
# ═══════════════════════════════════════════════════════════════════════════════

def format_file_size(size_bytes: int) -> str:
    """将字节数转换为人类可读的格式，如 "1.23 MB"。"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"


def format_dimensions(width: int, height: int) -> str:
    """将宽高格式化为 '{宽} × {高}' 的形式。"""
    return f"{width} × {height}"

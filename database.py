"""
=============================================================================
 database.py — 数据库操作模块
=============================================================================
 本模块封装所有 SQLite 数据库的读写操作。
 使用 Python 内置 sqlite3，无需额外安装数据库服务。
 数据库文件自动创建在项目目录的 data/ 文件夹下。

 表结构说明：
 ┌─────────────┐       ┌─────────────────┐
 │   images    │ 1──1  │  annotations    │
 │ (图像元数据) │  <──> │  (标注结果)     │
 └─────────────┘       └─────────────────┘
=============================================================================
"""

import sqlite3
from pathlib import Path
from typing import Optional, Any

# ── 数据库路径 ──────────────────────────────────────────────────────────────
# 使用 pathlib 处理路径，跨平台兼容（Windows / macOS / Linux）
DB_DIR = Path(__file__).parent / "data"
DB_PATH = DB_DIR / "medimage_labeler.db"


# ── 工具函数 ────────────────────────────────────────────────────────────────

def _dict_factory(cursor: sqlite3.Cursor, row: tuple) -> dict:
    """将查询结果行转换为字典，方便通过列名访问。"""
    return {col[0]: row[i] for i, col in enumerate(cursor.description)}


def get_connection() -> sqlite3.Connection:
    """
    获取数据库连接。

    返回的连接已设置：
    - row_factory = dict_factory（查询结果可直接当字典用）
    - journal_mode = WAL（写入性能更好，多线程安全）
    - check_same_thread = False（允许 Streamlit 多线程使用）
    """
    DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = _dict_factory
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# ── 初始化 ──────────────────────────────────────────────────────────────────

def init_database():
    """
    初始化数据库表结构。

    如果表已存在则跳过（CREATE TABLE IF NOT EXISTS），
    因此多次运行不会丢失已有数据。
    """
    conn = get_connection()
    cursor = conn.cursor()

    # ----- 图像表 -----
    # 存储导入的图像文件的元数据
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS images (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            file_path   TEXT    UNIQUE NOT NULL,   -- 图像完整路径（唯一约束，防止重复导入）
            file_name   TEXT    NOT NULL,           -- 文件名（仅名称，不含路径）
            file_size   INTEGER,                    -- 文件大小，单位字节
            width       INTEGER,                    -- 图像宽度，像素
            height      INTEGER,                    -- 图像高度，像素
            imported_at TEXT    DEFAULT (datetime('now','localtime'))  -- 导入时间
        )
    """)

    # ----- 标注表 -----
    # image_id 设置了 UNIQUE，意味着一张图片只能有一条标注记录（分组合并）
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS annotations (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            image_id     INTEGER NOT NULL UNIQUE,   -- 关联 images.id
            label        TEXT,                       -- 分类标签：'Normal' / 'Pneumonia' / 'Uncertain'
            bbox_x       INTEGER,                    -- 边界框左上角 X 坐标
            bbox_y       INTEGER,                    -- 边界框左上角 Y 坐标
            bbox_w       INTEGER,                    -- 边界框宽度
            bbox_h       INTEGER,                    -- 边界框高度
            annotated_at TEXT DEFAULT (datetime('now','localtime')),
            FOREIGN KEY (image_id) REFERENCES images(id) ON DELETE CASCADE
        )
    """)

    conn.commit()


# ═══════════════════════════════════════════════════════════════════════════════
# 图像相关操作
# ═══════════════════════════════════════════════════════════════════════════════

def add_image(file_path: str, file_name: str,
              file_size: int, width: int, height: int) -> Optional[int]:
    """
    添加一条图像记录。

    参数：
        file_path : 图像完整路径
        file_name : 文件名
        file_size : 文件大小（字节）
        width     : 图像宽度（像素）
        height    : 图像高度（像素）

    返回：
        新记录的 ID；如果文件已存在（重复导入）则返回 None。
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO images (file_path, file_name, file_size, width, height)
            VALUES (?, ?, ?, ?, ?)
        """, (file_path, file_name, file_size, width, height))
        conn.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        # file_path 有 UNIQUE 约束，重复时会触发此异常
        return None


def get_all_images() -> list[dict]:
    """获取所有图像（含标注信息），按导入时间倒序。"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT i.*, a.label, a.annotated_at AS annotation_time
        FROM images i
        LEFT JOIN annotations a ON i.id = a.image_id
        ORDER BY i.imported_at DESC
    """)
    return cursor.fetchall()


def get_image_by_id(image_id: int) -> Optional[dict]:
    """根据 ID 获取单张图像信息（含标注信息）。"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT i.*, a.label, a.bbox_x, a.bbox_y, a.bbox_w, a.bbox_h,
               a.annotated_at AS annotation_time
        FROM images i
        LEFT JOIN annotations a ON i.id = a.image_id
        WHERE i.id = ?
    """, (image_id,))
    return cursor.fetchone()


def get_unannotated_images() -> list[dict]:
    """获取所有尚未标注的图像。"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT i.* FROM images i
        LEFT JOIN annotations a ON i.id = a.image_id
        WHERE a.id IS NULL
        ORDER BY i.imported_at DESC
    """)
    return cursor.fetchall()


def get_annotated_images() -> list[dict]:
    """获取所有已标注的图像（含标注信息）。"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT i.*, a.label, a.bbox_x, a.bbox_y, a.bbox_w, a.bbox_h,
               a.annotated_at AS annotation_time
        FROM images i
        INNER JOIN annotations a ON i.id = a.image_id
        ORDER BY a.annotated_at DESC
    """)
    return cursor.fetchall()


def delete_image(image_id: int):
    """删除图像及其标注记录（ON DELETE CASCADE 会自动处理 annotations）。"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM images WHERE id = ?", (image_id,))
    conn.commit()


def delete_images_batch(image_ids: list[int]) -> int:
    """
    批量删除图像，所有操作包裹在单个事务中，大幅提升大批量删除性能。

    参数：
        image_ids : 要删除的图像 ID 列表

    返回：
        实际删除的图像数量。
    """
    if not image_ids:
        return 0
    conn = get_connection()
    cursor = conn.cursor()
    # 用单条 DELETE ... IN (...) 一次性删除，避免逐条提交的开销
    placeholders = ",".join("?" for _ in image_ids)
    cursor.execute(
        f"DELETE FROM images WHERE id IN ({placeholders})",
        image_ids,
    )
    deleted = cursor.rowcount
    conn.commit()
    return deleted


# ═══════════════════════════════════════════════════════════════════════════════
# 标注相关操作
# ═══════════════════════════════════════════════════════════════════════════════

def save_annotation(image_id: int, label: str,
                    bbox_x: Optional[int] = None,
                    bbox_y: Optional[int] = None,
                    bbox_w: Optional[int] = None,
                    bbox_h: Optional[int] = None) -> bool:
    """
    保存（或更新）一张图像的标注结果。

    参数：
        image_id : 图像 ID
        label    : 分类标签，可选 'Normal' / 'Pneumonia' / 'Uncertain'
        bbox_*   : 边界框坐标（可选）

    返回：
        True 表示成功。
    """
    conn = get_connection()
    cursor = conn.cursor()

    # UPSERT：如果 image_id 已存在则 UPDATE，否则 INSERT
    cursor.execute("""
        INSERT INTO annotations (image_id, label, bbox_x, bbox_y, bbox_w, bbox_h, annotated_at)
        VALUES (?, ?, ?, ?, ?, ?, datetime('now','localtime'))
        ON CONFLICT(image_id) DO UPDATE SET
            label        = excluded.label,
            bbox_x       = excluded.bbox_x,
            bbox_y       = excluded.bbox_y,
            bbox_w       = excluded.bbox_w,
            bbox_h       = excluded.bbox_h,
            annotated_at = datetime('now','localtime')
    """, (image_id, label, bbox_x, bbox_y, bbox_w, bbox_h))

    conn.commit()
    return True


def delete_annotation(image_id: int):
    """删除某张图像的标注。"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM annotations WHERE image_id = ?", (image_id,))
    conn.commit()


# ═══════════════════════════════════════════════════════════════════════════════
# 统计查询
# ═══════════════════════════════════════════════════════════════════════════════

def get_statistics() -> dict:
    """
    获取项目统计数据。

    返回示例：
        {
            "total_images": 100,
            "annotated_count": 65,
            "unannotated_count": 35,
            "label_counts": {"Normal": 30, "Pneumonia": 25, "Uncertain": 10},
            "annotation_progress": 65.0
        }
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) AS cnt FROM images")
    total = cursor.fetchone()["cnt"]

    cursor.execute("SELECT COUNT(*) AS cnt FROM annotations")
    annotated = cursor.fetchone()["cnt"]

    cursor.execute("""
        SELECT label, COUNT(*) AS cnt
        FROM annotations
        WHERE label IS NOT NULL
        GROUP BY label
    """)
    label_counts = {row["label"]: row["cnt"] for row in cursor.fetchall()}

    return {
        "total_images": total,
        "annotated_count": annotated,
        "unannotated_count": total - annotated,
        "label_counts": label_counts,
        "annotation_progress": (annotated / total * 100) if total > 0 else 0.0,
    }


def get_image_size_stats() -> list[dict]:
    """获取所有图像的尺寸与文件大小，用于分析页面的分布图。"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT width, height, file_size,
               CASE WHEN a.id IS NOT NULL THEN '已标注' ELSE '未标注' END AS status
        FROM images i
        LEFT JOIN annotations a ON i.id = a.image_id
    """)
    return cursor.fetchall()


def get_daily_stats() -> list[dict]:
    """获取每日标注数量，用于时间序列折线图。"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT DATE(annotated_at) AS date, COUNT(*) AS count
        FROM annotations
        GROUP BY DATE(annotated_at)
        ORDER BY date
    """)
    return cursor.fetchall()


# ═══════════════════════════════════════════════════════════════════════════════
# 导出
# ═══════════════════════════════════════════════════════════════════════════════

def export_annotated_data() -> list[dict]:
    """
    导出所有包含标注的图像数据。
    用于生成 CSV 文件。

    仅返回已有标注（label 非空）的记录。
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            i.id              AS "编号",
            i.file_path       AS "文件路径",
            i.file_name       AS "文件名",
            i.width           AS "图像宽度",
            i.height          AS "图像高度",
            a.label           AS "分类标签",
            a.bbox_x          AS "边界框_X",
            a.bbox_y          AS "边界框_Y",
            a.bbox_w          AS "边界框_宽度",
            a.bbox_h          AS "边界框_高度",
            a.annotated_at    AS "标注时间"
        FROM images i
        INNER JOIN annotations a ON i.id = a.image_id
        WHERE a.label IS NOT NULL
        ORDER BY a.annotated_at DESC
    """)
    return cursor.fetchall()

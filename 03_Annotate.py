"""
=============================================================================
 03_Annotate.py — 标注主页面（核心功能）
=============================================================================
 提供完整的图像标注工作流：
 1. 图像选择（下拉列表 + 缩略图网格浏览）
 2. 大图显示（附带当前标注信息）
 3. 分类标签（正常 / 肺炎 / 不确定）
 4. 边界框标注（bbox，使用 streamlit-drawable-canvas 或手动输入）
 5. 保存 / 清除标注

 这是本应用最核心的页面。
=============================================================================
"""

import streamlit as st
from pathlib import Path

from database import (
    get_all_images,
    get_image_by_id,
    save_annotation,
    delete_annotation,
)
from utils import load_image_safe, format_file_size, format_dimensions

# ── 页面标题 ────────────────────────────────────────────────────────────────
st.title("🏷️ 图像标注")
st.caption("浏览图像并进行分类标注（正常 / 肺炎 / 不确定）")


# ── 加载图像列表 ────────────────────────────────────────────────────────────
all_images = get_all_images()

if not all_images:
    st.info("📭 数据库为空，请先前往 **导入页面** 导入图像。")
    st.stop()


# ═══════════════════════════════════════════════════════════════════════════════
# 初始化 Session 状态
# ═══════════════════════════════════════════════════════════════════════════════

if "selected_image_id" not in st.session_state:
    # 默认选择第一张图像
    st.session_state["selected_image_id"] = all_images[0]["id"]

if "filter_option" not in st.session_state:
    st.session_state["filter_option"] = "全部"


# ═══════════════════════════════════════════════════════════════════════════════
# 辅助函数：根据筛选条件获取图像列表
# ═══════════════════════════════════════════════════════════════════════════════

def get_filtered_images(filter_opt: str) -> list[dict]:
    """根据筛选选项返回对应的图像列表。"""
    if filter_opt == "未标注":
        return [img for img in all_images if img["label"] is None]
    elif filter_opt == "已标注":
        return [img for img in all_images if img["label"] is not None]
    elif filter_opt == "正常":
        return [img for img in all_images if img["label"] == "正常"]
    elif filter_opt == "肺炎":
        return [img for img in all_images if img["label"] == "肺炎"]
    elif filter_opt == "不确定":
        return [img for img in all_images if img["label"] == "不确定"]
    else:
        return all_images


# ═══════════════════════════════════════════════════════════════════════════════
# 顶部控制区：筛选 + 翻页 + 图像选择 + 导航
# ═══════════════════════════════════════════════════════════════════════════════

PAGE_SIZE = 20

if "annotate_page" not in st.session_state:
    st.session_state["annotate_page"] = 0

st.subheader("🔍 选择图像")
top_col1, top_col2, top_col3, top_col4 = st.columns([1, 3, 1, 1])

# ── 筛选下拉框 ──────────────────────────────────────────────────────────────
with top_col1:
    filter_opt = st.selectbox(
        "筛选",
        options=["全部", "未标注", "已标注", "正常", "肺炎", "不确定"],
        index=["全部", "未标注", "已标注", "正常", "肺炎", "不确定"].index(
            st.session_state["filter_option"]
        ),
        key="filter_select",
    )
    if st.session_state["filter_option"] != filter_opt:
        st.session_state["annotate_page"] = 0
    st.session_state["filter_option"] = filter_opt

# 根据筛选条件获取图像列表
filtered_images = get_filtered_images(filter_opt)

if not filtered_images:
    st.info(f"筛选条件「{filter_opt}」下没有图像。")
    st.stop()

# ── 翻页计算 ────────────────────────────────────────────────────────────────
total_pages = max(1, (len(filtered_images) + PAGE_SIZE - 1) // PAGE_SIZE)
page = st.session_state["annotate_page"]
if page >= total_pages:
    page = 0
    st.session_state["annotate_page"] = 0

start = page * PAGE_SIZE
end = min(start + PAGE_SIZE, len(filtered_images))
page_images = filtered_images[start:end]

# ── 当前选中图像在全局列表中的索引 ──────────────────────────────────────────
current_global_idx = next(
    (i for i, img in enumerate(filtered_images)
     if img["id"] == st.session_state["selected_image_id"]),
    0,
)

# ── 翻页控件 ────────────────────────────────────────────────────────────────
nav_c1, nav_c2, nav_c3, nav_c4, nav_c5, nav_c6 = st.columns([0.8, 0.8, 1.5, 0.8, 0.8, 2])
with nav_c1:
    if st.button("◀◀", disabled=(page == 0), key="ap_first", use_container_width=True):
        st.session_state["annotate_page"] = 0
        st.session_state["selected_image_id"] = filtered_images[0]["id"]
        st.rerun()
with nav_c2:
    if st.button("◀", disabled=(page == 0), key="ap_prev", use_container_width=True):
        new_page = page - 1
        st.session_state["annotate_page"] = new_page
        st.session_state["selected_image_id"] = filtered_images[new_page * PAGE_SIZE]["id"]
        st.rerun()
with nav_c3:
    st.caption(f"第 {page + 1} / {total_pages} 页（共 {len(filtered_images)} 张）")
with nav_c4:
    if st.button("▶", disabled=(page >= total_pages - 1), key="ap_nextpg", use_container_width=True):
        new_page = page + 1
        st.session_state["annotate_page"] = new_page
        st.session_state["selected_image_id"] = filtered_images[new_page * PAGE_SIZE]["id"]
        st.rerun()
with nav_c5:
    if st.button("▶▶", disabled=(page >= total_pages - 1), key="ap_last", use_container_width=True):
        last_page = total_pages - 1
        st.session_state["annotate_page"] = last_page
        st.session_state["selected_image_id"] = filtered_images[last_page * PAGE_SIZE]["id"]
        st.rerun()

# ── 图像下拉选择器 ──────────────────────────────────────────────────────────
with top_col2:
    image_options = {
        f"{img['file_name']}  [{img['label'] or '未标注'}]": img["id"]
        for img in page_images
    }

    current_display_name = None
    for display_name, img_id in image_options.items():
        if img_id == st.session_state["selected_image_id"]:
            current_display_name = display_name
            break

    if current_display_name is None and image_options:
        current_display_name = list(image_options.keys())[0]
        st.session_state["selected_image_id"] = image_options[current_display_name]

    selected_display = st.selectbox(
        "选择图像",
        options=list(image_options.keys()),
        index=(
            list(image_options.keys()).index(current_display_name)
            if current_display_name in image_options
            else 0
        ),
        key="image_selector",
    )
    st.session_state["selected_image_id"] = image_options[selected_display]

# ── 当前选中图像在全局列表中的索引 ──────────────────────────────────────────
current_index = current_global_idx

# ── 上一张 / 下一张 按钮（全局导航，自动翻页）──────────────────────────────
with top_col3:
    if st.button("◀ 上一张", use_container_width=True):
        if current_index > 0:
            new_idx = current_index - 1
            new_page = new_idx // PAGE_SIZE
            st.session_state["selected_image_id"] = filtered_images[new_idx]["id"]
            if new_page != page:
                st.session_state["annotate_page"] = new_page
        else:
            st.toast("已经是第一张了", icon="⚠️")
        st.rerun()

with top_col4:
    if st.button("下一张 ▶", use_container_width=True):
        if current_index < len(filtered_images) - 1:
            new_idx = current_index + 1
            new_page = new_idx // PAGE_SIZE
            st.session_state["selected_image_id"] = filtered_images[new_idx]["id"]
            if new_page != page:
                st.session_state["annotate_page"] = new_page
        else:
            st.toast("已经是最后一张了", icon="⚠️")
        st.rerun()

# 显示当前进度
st.caption(f"当前：第 {current_index + 1} / {len(filtered_images)} 张")


# ═══════════════════════════════════════════════════════════════════════════════
# 加载当前选中的图像
# ═══════════════════════════════════════════════════════════════════════════════

image_data = get_image_by_id(st.session_state["selected_image_id"])

if image_data is None:
    st.error("无法加载图像信息，可能已被删除。")
    st.stop()

# 安全加载图像（限制最大尺寸 900×900）
pil_image = load_image_safe(image_data["file_path"], max_size=(900, 900))

if pil_image is None:
    st.error(f"❌ 无法打开图像文件：{image_data['file_name']}")
    st.caption(f"路径：{image_data['file_path']}")
    st.stop()


# ═══════════════════════════════════════════════════════════════════════════════
# 缩略图网格浏览
# ═══════════════════════════════════════════════════════════════════════════════

with st.expander(f"🖼️ 缩略图浏览（第 {page + 1} 页）", expanded=False):
    # 每行显示 5 张缩略图
    thumb_cols = st.columns(5)

    for idx, img in enumerate(page_images):
        col_idx = idx % 5

        with thumb_cols[col_idx]:
            thumb = load_image_safe(img["file_path"], max_size=(150, 150))
            if thumb:
                # 如果是当前选中的图像，加边框标记
                is_selected = img["id"] == st.session_state["selected_image_id"]
                border = "2px solid #dc3545" if is_selected else "1px solid #ddd"
                st.image(thumb)
                st.caption(f"{img['file_name'][:15]}...")

                # 标签颜色标记
                label_color = {
                    "正常": "🟢",
                    "肺炎": "🔴",
                    "不确定": "🟡",
                }
                label_mark = label_color.get(img["label"], "⬜")

                if st.button(f"{label_mark} 选择", key=f"thumb_{img['id']}"):
                    st.session_state["selected_image_id"] = img["id"]
                    st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# 大图显示区
# ═══════════════════════════════════════════════════════════════════════════════

st.divider()

# ── 图像信息头 ──────────────────────────────────────────────────────────────
info_col1, info_col2, info_col3, info_col4 = st.columns(4)
with info_col1:
    st.markdown(f"**文件名：** {image_data['file_name']}")
with info_col2:
    st.markdown(f"**尺寸：** {format_dimensions(image_data['width'], image_data['height'])}")
with info_col3:
    st.markdown(f"**大小：** {format_file_size(image_data['file_size'])}")
with info_col4:
    status_text = (
        f"✅ **{image_data['label']}**"
        if image_data["label"]
        else "⏳ **未标注**"
    )
    st.markdown(f"**状态：** {status_text}")

if image_data.get("annotation_time"):
    st.caption(f"标注时间：{image_data['annotation_time']}")

# ── 大图显示 ────────────────────────────────────────────────────────────────
st.image(pil_image)


# ═══════════════════════════════════════════════════════════════════════════════
# 标注控制区
# ═══════════════════════════════════════════════════════════════════════════════

st.divider()
st.subheader("🏷️ 标注操作")

# ── 分类标签按钮 ────────────────────────────────────────────────────────────
st.markdown("#### 选择分类标签")
label_col1, label_col2, label_col3 = st.columns(3)

# 用 session 暂存当前选中的标签
if "current_label" not in st.session_state:
    st.session_state["current_label"] = image_data["label"] or ""

# 如果图像已有标注，自动填入
if image_data["label"] and st.session_state["current_label"] != image_data["label"]:
    st.session_state["current_label"] = image_data["label"]

with label_col1:
    normal_clicked = st.button(
        "🟢 正常",
        type="primary" if st.session_state["current_label"] == "正常" else "secondary",
        use_container_width=True,
    )
    if normal_clicked:
        st.session_state["current_label"] = "正常"

with label_col2:
    pneumonia_clicked = st.button(
        "🔴 肺炎",
        type="primary" if st.session_state["current_label"] == "肺炎" else "secondary",
        use_container_width=True,
    )
    if pneumonia_clicked:
        st.session_state["current_label"] = "肺炎"

with label_col3:
    uncertain_clicked = st.button(
        "🟡 不确定",
        type="primary" if st.session_state["current_label"] == "不确定" else "secondary",
        use_container_width=True,
    )
    if uncertain_clicked:
        st.session_state["current_label"] = "不确定"

# 显示当前选择
if st.session_state["current_label"]:
    color_map = {"正常": "🟢", "肺炎": "🔴", "不确定": "🟡"}
    st.info(f"当前选择：{color_map.get(st.session_state['current_label'], '')} **{st.session_state['current_label']}**")
else:
    st.warning("⚠️ 请先选择分类标签")


# ═══════════════════════════════════════════════════════════════════════════════
# 边界框标注（可选）
# ═══════════════════════════════════════════════════════════════════════════════

st.divider()
st.markdown("#### 📐 边界框标注（可选）")
st.caption("在图像上绘制矩形框，标记病灶区域。如果不需 bbox，直接保存分类标签即可。")

# 尝试导入 streamlit-drawable-canvas
try:
    from streamlit_drawable_canvas import st_canvas
    CANVAS_AVAILABLE = True
except ImportError:
    CANVAS_AVAILABLE = False

# 默认从已保存的数据中读取 bbox
bbox_x = st.session_state.get("bbox_x", image_data.get("bbox_x"))
bbox_y = st.session_state.get("bbox_y", image_data.get("bbox_y"))
bbox_w = st.session_state.get("bbox_w", image_data.get("bbox_w"))
bbox_h = st.session_state.get("bbox_h", image_data.get("bbox_h"))

# 两种模式：画布模式 / 手动输入模式
use_canvas = st.checkbox(
    "✏️ 启用画布标注（可在图像上直接拖动绘制矩形框）",
    value=False,
    help="需要安装 streamlit-drawable-canvas 库",
)

if use_canvas and CANVAS_AVAILABLE:
    # ── 画布模式 ──────────────────────────────────────────────────────────
    st.caption("在图像上拖动鼠标绘制矩形框（红色）")

    canvas_result = st_canvas(
        fill_color="rgba(220, 53, 69, 0.2)",  # 填充色（半透明红）
        stroke_width=3,
        stroke_color="#dc3545",
        background_image=pil_image,
        drawing_mode="rect",      # 只允许画矩形
        width=pil_image.width if pil_image else 800,
        height=pil_image.height if pil_image else 600,
        key=f"canvas_{image_data['id']}",  # 切换图像时重新创建画布
    )

    # 从画布结果中提取最后一个矩形
    if canvas_result.json_data is not None:
        objects = canvas_result.json_data.get("objects", [])
        if objects:
            last_obj = objects[-1]
            st.session_state["bbox_x"] = int(last_obj.get("left", 0))
            st.session_state["bbox_y"] = int(last_obj.get("top", 0))
            st.session_state["bbox_w"] = int(last_obj.get("width", 0))
            st.session_state["bbox_h"] = int(last_obj.get("height", 0))

            st.success(
                f"已绘制矩形：位置 ({st.session_state['bbox_x']}, {st.session_state['bbox_y']})"
                f"，大小 {st.session_state['bbox_w']} × {st.session_state['bbox_h']}"
            )

elif not use_canvas:
    # ── 手动输入模式 ──────────────────────────────────────────────────────
    st.caption("手动输入边界框坐标（像素）：")
    bbox_col1, bbox_col2, bbox_col3, bbox_col4 = st.columns(4)

    with bbox_col1:
        bbox_x_input = st.number_input(
            "左上角 X",
            min_value=0,
            max_value=image_data["width"],
            value=int(bbox_x) if bbox_x else 0,
            key=f"bbox_x_{image_data['id']}",
        )
        st.session_state["bbox_x"] = bbox_x_input

    with bbox_col2:
        bbox_y_input = st.number_input(
            "左上角 Y",
            min_value=0,
            max_value=image_data["height"],
            value=int(bbox_y) if bbox_y else 0,
            key=f"bbox_y_{image_data['id']}",
        )
        st.session_state["bbox_y"] = bbox_y_input

    with bbox_col3:
        bbox_w_input = st.number_input(
            "宽度",
            min_value=0,
            max_value=image_data["width"],
            value=int(bbox_w) if bbox_w else 0,
            key=f"bbox_w_{image_data['id']}",
        )
        st.session_state["bbox_w"] = bbox_w_input

    with bbox_col4:
        bbox_h_input = st.number_input(
            "高度",
            min_value=0,
            max_value=image_data["height"],
            value=int(bbox_h) if bbox_h else 0,
            key=f"bbox_h_{image_data['id']}",
        )
        st.session_state["bbox_h"] = bbox_h_input

else:
    # 用户勾选了画布但库不可用
    st.warning(
        "⚠️ 未检测到 streamlit-drawable-canvas 库。\n\n"
        "请运行 `pip install streamlit-drawable-canvas` 安装，"
        "或取消勾选后使用手动输入模式。"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 保存 / 清除 按钮
# ═══════════════════════════════════════════════════════════════════════════════

st.divider()
action_col1, action_col2, action_col3 = st.columns([2, 2, 4])

with action_col1:
    save_clicked = st.button(
        "💾 保存标注",
        type="primary",
        use_container_width=True,
        disabled=not st.session_state.get("current_label"),
    )

with action_col2:
    clear_clicked = st.button(
        "🗑️ 清除标注",
        type="secondary",
        use_container_width=True,
    )

# ── 保存 ────────────────────────────────────────────────────────────────────
if save_clicked:
    label = st.session_state["current_label"]

    if not label:
        st.error("请先选择分类标签！")
    else:
        # 获取 bbox 坐标（如果有的话）
        bbox_x_val = st.session_state.get("bbox_x")
        bbox_y_val = st.session_state.get("bbox_y")
        bbox_w_val = st.session_state.get("bbox_w")
        bbox_h_val = st.session_state.get("bbox_h")

        # 只有当所有值都 > 0 时才保存 bbox
        if all(v is not None and v > 0 for v in [bbox_x_val, bbox_y_val, bbox_w_val, bbox_h_val]):
            save_annotation(
                image_data["id"], label,
                bbox_x=int(bbox_x_val), bbox_y=int(bbox_y_val),
                bbox_w=int(bbox_w_val), bbox_h=int(bbox_h_val),
            )
        else:
            save_annotation(image_data["id"], label)

        st.success(f"✅ 标注已保存：{label}")

        # 清除缓存，刷新数据
        st.cache_data.clear()

        # 短暂延迟后刷新页面
        st.rerun()

# ── 清除 ────────────────────────────────────────────────────────────────────
if clear_clicked:
    delete_annotation(image_data["id"])
    st.session_state["current_label"] = ""
    st.session_state.pop("bbox_x", None)
    st.session_state.pop("bbox_y", None)
    st.session_state.pop("bbox_w", None)
    st.session_state.pop("bbox_h", None)

    st.success("🗑️ 标注已清除")
    st.cache_data.clear()
    st.rerun()

# ── 底部快捷键提示 ──────────────────────────────────────────────────────────
with action_col3:
    st.caption(
        "💡 **使用提示**\n\n"
        "1. 从下拉列表选择一张图像\n"
        "2. 点击分类标签按钮\n"
        "3. （可选）在图像上画矩形框\n"
        "4. 点击「保存标注」\n"
        "5. 用「下一张」按钮快速连续标注"
    )

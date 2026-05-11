"""
=============================================================================
 02_Import.py — 图像导入页面
=============================================================================
 支持两种导入方式：
 1. 输入文件夹路径，批量扫描导入
 2. 使用文件上传器逐个/批量上传

 导入过程中显示进度条和实时日志。
=============================================================================
"""

import streamlit as st
from pathlib import Path

from database import add_image, get_all_images, delete_image, delete_images_batch, get_statistics
from utils import scan_image_files, get_image_info, SUPPORTED_EXTENSIONS, format_file_size, format_dimensions

# ── 页面标题 ────────────────────────────────────────────────────────────────
st.title("📥 导入图像")
st.caption("将胸部X光图像导入系统，支持批量操作")


# ═══════════════════════════════════════════════════════════════════════════════
# 方式一：从本地文件夹导入
# ═══════════════════════════════════════════════════════════════════════════════

st.subheader("📂 方式一：从本地文件夹导入")

# 用文本输入框让用户填写文件夹路径
folder_path = st.text_input(
    "输入图像文件夹的完整路径：",
    placeholder="例如：C:/Users/用户名/Documents/X光 或 /home/user/x光",
    help="支持 PNG / JPG / JPEG / BMP / TIFF 格式，会自动扫描子文件夹",
)

# 高级选项（可折叠）
with st.expander("⚙️ 导入选项", expanded=False):
    recursive = st.checkbox("递归扫描子文件夹", value=True)

# 扫描和导入按钮
scan_col, import_col, status_col = st.columns([1, 1, 2])

with scan_col:
    scan_clicked = st.button("🔍 扫描文件夹", type="secondary", use_container_width=True)

with import_col:
    import_clicked = st.button("📥 导入全部", type="primary", use_container_width=True)

# ── 扫描预览 ────────────────────────────────────────────────────────────────
if scan_clicked and folder_path:
    scan_path = Path(folder_path)

    if not scan_path.exists():
        st.error(f"❌ 文件夹不存在：{folder_path}")
    elif not scan_path.is_dir():
        st.error(f"❌ 路径不是一个文件夹：{folder_path}")
    else:
        # 扫描文件
        found_files = scan_image_files(folder_path, recursive=recursive)

        if not found_files:
            st.warning(
                f"在「{folder_path}」中未找到支持的图像文件。\n\n"
                f"支持的格式：{', '.join(SUPPORTED_EXTENSIONS)}"
            )
        else:
            st.success(f"找到 {len(found_files)} 张图像！")

            # 存入 session_state 供导入按钮使用
            st.session_state["scanned_files"] = found_files
            st.session_state["scan_folder"] = folder_path

            # 显示文件列表前几项作为预览
            preview_count = min(len(found_files), 10)
            preview_data = []
            for f in found_files[:preview_count]:
                info = get_image_info(f)
                if info:
                    preview_data.append({
                        "文件名": info["file_name"],
                        "尺寸": f"{info['width']}×{info['height']}",
                        "大小": f"{info['file_size'] / 1024:.1f} KB",
                    })
                else:
                    preview_data.append({"文件名": f.name, "尺寸": "❌ 无法读取", "大小": "-"})

            st.dataframe(preview_data, use_container_width=True)

            if len(found_files) > preview_count:
                st.caption(f"... 以及另外 {len(found_files) - preview_count} 张")

# ── 执行导入 ────────────────────────────────────────────────────────────────
if import_clicked:
    if not folder_path:
        st.warning("请先输入文件夹路径。")
    else:
        scan_path = Path(folder_path)
        if not scan_path.exists() or not scan_path.is_dir():
            st.error(f"无效的文件夹路径：{folder_path}")
        else:
            files = scan_image_files(folder_path, recursive=recursive)

            if not files:
                st.warning("未找到可供导入的图像文件。")
            else:
                # 显示进度条
                progress_bar = st.progress(0, text="准备导入...")
                status_text = st.empty()
                log_area = st.container()

                success = 0
                skipped = 0
                errors = 0

                for i, file_path in enumerate(files):
                    # 更新进度
                    progress = (i + 1) / len(files)
                    progress_bar.progress(progress, text=f"正在处理：{file_path.name}")

                    # 提取图像信息
                    info = get_image_info(file_path)

                    if info is None:
                        errors += 1
                        with log_area:
                            st.error(f"❌ 无法读取：{file_path.name}")
                        continue

                    # 导入到数据库
                    result = add_image(
                        info["file_path"],
                        info["file_name"],
                        info["file_size"],
                        info["width"],
                        info["height"],
                    )

                    if result is not None:
                        success += 1
                    else:
                        skipped += 1

                # 导入完成
                progress_bar.progress(1.0, text="导入完成！")

                st.success(
                    f"✅ 导入完成！\n"
                    f"- 成功导入：{success} 张\n"
                    f"- 跳过重复：{skipped} 张\n"
                    f"- 读取失败：{errors} 张"
                )

                # 清除缓存
                st.cache_data.clear()


# ═══════════════════════════════════════════════════════════════════════════════
# 方式二：通过上传器导入
# ═══════════════════════════════════════════════════════════════════════════════

st.divider()
st.subheader("☁️ 方式二：上传文件")

uploaded_files = st.file_uploader(
    "选择图像文件（可多选）",
    type=list(SUPPORTED_EXTENSIONS),
    accept_multiple_files=True,
    help="支持 PNG / JPG / JPEG / BMP / TIFF 格式",
)

if uploaded_files:
    upload_progress = st.progress(0, text="正在保存上传的文件...")

    # 创建临时目录存放上传的文件
    import tempfile
    import os
    from PIL import Image
    from io import BytesIO

    upload_dir = Path(__file__).parent.parent / "uploads"
    upload_dir.mkdir(exist_ok=True)

    upload_success = 0
    upload_errors = 0

    for i, uploaded_file in enumerate(uploaded_files):
        upload_progress.progress(
            (i + 1) / len(uploaded_files),
            text=f"正在处理：{uploaded_file.name}",
        )

        try:
            # 读取上传的文件
            file_bytes = uploaded_file.read()

            # 用 Pillow 获取尺寸
            img = Image.open(BytesIO(file_bytes))
            width, height = img.size

            # 保存到本地 uploads 目录
            save_path = upload_dir / uploaded_file.name
            with open(save_path, "wb") as f:
                f.write(file_bytes)

            # 导入数据库
            result = add_image(
                str(save_path.resolve()),
                uploaded_file.name,
                len(file_bytes),
                width,
                height,
            )

            if result is not None:
                upload_success += 1
            else:
                upload_errors += 1

        except Exception as e:
            upload_errors += 1
            st.error(f"处理 {uploaded_file.name} 时出错：{e}")

    upload_progress.progress(1.0, text="上传完成！")

    if upload_success > 0:
        st.success(f"✅ 成功上传并导入 {upload_success} 张图像！")
    if upload_errors > 0:
        st.warning(f"⚠️ 有 {upload_errors} 张导入失败（可能是重复）")

    st.cache_data.clear()


# ═══════════════════════════════════════════════════════════════════════════════
# 图像管理区（查看 / 删除已导入的图像）
# ═══════════════════════════════════════════════════════════════════════════════

st.divider()
st.subheader("🗂️ 管理已导入图像")

all_imgs = get_all_images()
stats = get_statistics()

if not all_imgs:
    st.info("暂无已导入的图像。")
else:
    col_a, col_b, col_c = st.columns(3)
    col_a.metric("📁 图像总数", stats["total_images"])
    col_b.metric("✅ 已标注", stats["annotated_count"])
    col_c.metric("⏳ 未标注", stats["unannotated_count"])

    st.divider()

    if "delete_confirm_id" not in st.session_state:
        st.session_state["delete_confirm_id"] = None
    if "manage_page" not in st.session_state:
        st.session_state["manage_page"] = 0

    if "manage_page_size" not in st.session_state:
        st.session_state["manage_page_size"] = 20

    filter_col, size_col = st.columns([3, 1])
    with filter_col:
        filter_opt = st.radio(
            "筛选条件", ["全部", "未标注", "已标注"],
            horizontal=True,
            key="manage_filter"
        )
    with size_col:
        new_size = st.selectbox(
            "每页显示", [20, 50, 100, 500, 1000],
            index=[20, 50, 100, 500, 1000].index(st.session_state["manage_page_size"]),
            key="manage_page_size_select",
        )
        if new_size != st.session_state["manage_page_size"]:
            st.session_state["manage_page_size"] = new_size
            st.session_state["manage_page"] = 0
            st.rerun()

    # 切换筛选条件时清空选择
    if st.session_state.get("_last_filter") != filter_opt:
        st.session_state["selected_ids"] = set()
        st.session_state["manage_page"] = 0
        st.session_state["_last_filter"] = filter_opt

    if filter_opt == "未标注":
        imgs = [img for img in all_imgs if img["label"] is None]
    elif filter_opt == "已标注":
        imgs = [img for img in all_imgs if img["label"] is not None]
    else:
        imgs = all_imgs

    page_size = st.session_state["manage_page_size"]
    total_pages = max(1, (len(imgs) + page_size - 1) // page_size)
    page = st.session_state["manage_page"]

    # 翻页超出范围时修正
    if page >= total_pages:
        page = 0
        st.session_state["manage_page"] = 0

    start = page * page_size
    end = start + page_size
    page_imgs = imgs[start:end]

    st.caption(f"共 {len(imgs)} 张（每页 {page_size} 张，第 {page + 1} / {total_pages} 页）")

    # 分页控件
    pc1, pc2, pc3, pc4, pc5 = st.columns([1, 1, 2, 1, 1])
    with pc1:
        if st.button("◀◀ 首页", disabled=(page == 0), use_container_width=True):
            st.session_state["manage_page"] = 0
            st.rerun()
    with pc2:
        if st.button("◀ 上一页", disabled=(page == 0), use_container_width=True):
            st.session_state["manage_page"] -= 1
            st.rerun()
    with pc3:
        go_page = st.number_input(
            "跳转到", min_value=1, max_value=total_pages,
            value=page + 1, key="go_page", label_visibility="collapsed"
        )
        if st.button("跳转", key="go_btn"):
            st.session_state["manage_page"] = go_page - 1
            st.rerun()
    with pc4:
        if st.button("下一页 ▶", disabled=(page >= total_pages - 1), use_container_width=True):
            st.session_state["manage_page"] += 1
            st.rerun()
    with pc5:
        if st.button("末页 ▶▶", disabled=(page >= total_pages - 1), use_container_width=True):
            st.session_state["manage_page"] = total_pages - 1
            st.rerun()

    if "batch_delete_mode" not in st.session_state:
        st.session_state["batch_delete_mode"] = False
    if "selected_ids" not in st.session_state:
        st.session_state["selected_ids"] = set()

    st.divider()

    if not page_imgs:
        st.info("该筛选条件下无图像。")
    else:
        # ── 批量操作栏 ──────────────────────────────────────────────────────
        bar_col1, bar_col2, bar_col3, bar_col4 = st.columns([1, 1, 1, 3])

        page_ids = {img["id"] for img in page_imgs}
        all_on_page_selected = page_ids.issubset(st.session_state["selected_ids"])

        with bar_col1:
            if st.checkbox("全选本页", value=all_on_page_selected, key="select_all_page"):
                st.session_state["selected_ids"].update(page_ids)
            else:
                st.session_state["selected_ids"].difference_update(page_ids)

        with bar_col2:
            total_selected = len(st.session_state["selected_ids"])
            st.caption(f"已选 {total_selected} 张")

        with bar_col3:
            if st.button(
                "🗑️ 批量删除",
                type="primary",
                disabled=(total_selected == 0),
                use_container_width=True,
            ):
                st.session_state["batch_delete_mode"] = True
                st.rerun()

        with bar_col4:
            if total_selected > 0:
                st.caption("勾选下方复选框可跨页累计选择")

        # ── 批量删除二次确认 ────────────────────────────────────────────────
        if st.session_state["batch_delete_mode"] and total_selected > 0:
            st.error(f"⚠️ 确定要删除选中的 {total_selected} 张图像吗？此操作不可撤销。")
            bc1, bc2, bc3 = st.columns([1, 1, 3])
            with bc1:
                if st.button("✅ 确认批量删除", type="primary"):
                    deleted = delete_images_batch(list(st.session_state["selected_ids"]))
                    st.session_state["selected_ids"].clear()
                    st.session_state["batch_delete_mode"] = False
                    st.cache_data.clear()
                    st.success(f"已删除 {deleted} 张图像")
                    st.rerun()
            with bc2:
                if st.button("❌ 取消", key="cancel_batch"):
                    st.session_state["batch_delete_mode"] = False
                    st.rerun()

        st.divider()

        # ── 图像列表（每行：复选框 + 信息 + 单独删除）───────────────────────
        for img in page_imgs:
            img_id = img["id"]
            c0, c1, c2, c3, c4, c5 = st.columns([0.5, 3, 1.5, 1, 2, 1.5])

            with c0:
                is_checked = img_id in st.session_state["selected_ids"]
                checked = st.checkbox(
                    "选择", value=is_checked,
                    key=f"sel_{img_id}", label_visibility="collapsed"
                )
                if checked:
                    st.session_state["selected_ids"].add(img_id)
                else:
                    st.session_state["selected_ids"].discard(img_id)

            with c1:
                st.write(f"**{img['file_name']}**")
            with c2:
                st.caption(format_dimensions(img["width"], img["height"]))
            with c3:
                st.caption(format_file_size(img["file_size"]))
            with c4:
                if img["label"]:
                    st.success(f"✅ {img['label']}")
                else:
                    st.warning("⏳ 未标注")

            with c5:
                if st.button("🗑️", key=f"delbtn_{img_id}", use_container_width=True):
                    st.session_state["delete_confirm_id"] = img_id
                    st.rerun()

            # 单独删除二次确认
            if st.session_state["delete_confirm_id"] == img_id:
                st.warning(f"⚠️ 确定要删除「{img['file_name']}」吗？此操作不可撤销。")
                cc1, cc2, cc3 = st.columns([1, 1, 3])
                with cc1:
                    if st.button("✅ 确认", key=f"confirm_{img_id}", type="primary"):
                        delete_image(img_id)
                        st.session_state["selected_ids"].discard(img_id)
                        st.session_state["delete_confirm_id"] = None
                        st.cache_data.clear()
                        st.success(f"已删除：{img['file_name']}")
                        st.rerun()
                with cc2:
                    if st.button("❌ 取消", key=f"cancel_{img_id}"):
                        st.session_state["delete_confirm_id"] = None
                        st.rerun()

            st.divider()

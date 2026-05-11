"""
=============================================================================
 04_Analysis.py — 数据分析页面
=============================================================================
 提供详细的标注统计数据：
 - 各类别数量对比（柱状图）
 - 标注状态分布
 - 图像尺寸分布（散点图 / 直方图）
 - 每日标注趋势
=============================================================================
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from database import get_statistics, get_image_size_stats, get_daily_stats

# ── 页面标题 ────────────────────────────────────────────────────────────────
st.title("📊 数据分析")
st.caption("标注进度、类别分布和图像属性统计")


# ── 获取数据 ────────────────────────────────────────────────────────────────
stats = get_statistics()
size_stats = get_image_size_stats()
daily_stats = get_daily_stats()

if stats["total_images"] == 0:
    st.info("📭 数据库为空，请先导入图像。")
    st.stop()


# ═══════════════════════════════════════════════════════════════════════════════
# 概览行
# ═══════════════════════════════════════════════════════════════════════════════

overview_col1, overview_col2, overview_col3, overview_col4 = st.columns(4)

with overview_col1:
    st.metric("📁 总图像数", stats["total_images"])

with overview_col2:
    st.metric("✅ 已标注", stats["annotated_count"])

with overview_col3:
    st.metric("⏳ 未标注", stats["unannotated_count"])

with overview_col4:
    st.metric("📈 标注完成率", f"{stats['annotation_progress']:.1f}%")


# ═══════════════════════════════════════════════════════════════════════════════
# 图表行 1：类别分布 + 标注状态
# ═══════════════════════════════════════════════════════════════════════════════

st.divider()
chart_row1_col1, chart_row1_col2 = st.columns(2)

# ── 左侧：各类别数量柱状图 ──────────────────────────────────────────────────
with chart_row1_col1:
    st.subheader("🏷️ 各类别数量")

    if stats["label_counts"]:
        labels = list(stats["label_counts"].keys())
        counts = list(stats["label_counts"].values())

        color_map = {
            "正常": "#28a745",
            "肺炎": "#dc3545",
            "不确定": "#ffc107",
        }
        bar_colors = [color_map.get(l, "#6c757d") for l in labels]

        fig1 = go.Figure(data=[
            go.Bar(
                x=labels,
                y=counts,
                marker=dict(color=bar_colors),
                text=counts,
                textposition="auto",
            )
        ])
        fig1.update_layout(
            height=400,
            margin=dict(l=20, r=20, t=30, b=20),
            yaxis=dict(title="图像数量"),
            xaxis=dict(title="分类标签"),
        )
        st.plotly_chart(fig1, use_container_width=True)
    else:
        st.info("暂无标注数据")

# ── 右侧：标注状态玫瑰图 ────────────────────────────────────────────────────
with chart_row1_col2:
    st.subheader("📊 标注状态")

    fig2 = go.Figure(data=[
        go.Pie(
            labels=["未标注", "已标注"],
            values=[stats["unannotated_count"], stats["annotated_count"]],
            marker=dict(colors=["#ffc107", "#28a745"]),
            hole=0.3,
            textinfo="label+percent",
        )
    ])
    fig2.update_layout(
        height=400,
        margin=dict(l=20, r=20, t=30, b=20),
    )
    st.plotly_chart(fig2, use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════════
# 图表行 2：图像尺寸分布
# ═══════════════════════════════════════════════════════════════════════════════

st.divider()
st.subheader("📐 图像尺寸分布")

if size_stats:
    # 准备数据
    widths = [s["width"] for s in size_stats]
    heights = [s["height"] for s in size_stats]
    file_sizes_kb = [s["file_size"] / 1024 for s in size_stats]
    statuses = [s["status"] for s in size_stats]

    size_chart_col1, size_chart_col2 = st.columns(2)

    # ── 散点图：宽 vs 高 ────────────────────────────────────────────────────
    with size_chart_col1:
        fig_scatter = px.scatter(
            x=widths,
            y=heights,
            color=statuses,
            labels={"x": "宽度（像素）", "y": "高度（像素）", "color": "状态"},
            title="图像尺寸散点图",
            opacity=0.7,
        )
        fig_scatter.update_layout(height=400)
        st.plotly_chart(fig_scatter, use_container_width=True)

    # ── 文件大小直方图 ──────────────────────────────────────────────────────
    with size_chart_col2:
        fig_hist = px.histogram(
            x=file_sizes_kb,
            nbins=20,
            labels={"x": "文件大小（KB）", "y": "数量"},
            title="文件大小分布",
            color_discrete_sequence=["#17a2b8"],
        )
        fig_hist.update_layout(height=400)
        st.plotly_chart(fig_hist, use_container_width=True)

else:
    st.info("暂无图像尺寸数据")


# ═══════════════════════════════════════════════════════════════════════════════
# 图表行 3：每日标注趋势
# ═══════════════════════════════════════════════════════════════════════════════

st.divider()
st.subheader("📈 标注时间线")

if daily_stats:
    dates = [d["date"] for d in daily_stats]
    counts = [d["count"] for d in daily_stats]

    fig_timeline = px.bar(
        x=dates,
        y=counts,
        labels={"x": "日期", "y": "标注数量"},
        title="每日标注数量",
        color_discrete_sequence=["#28a745"],
    )
    fig_timeline.update_layout(
        height=400,
        xaxis=dict(tickangle=-45),
    )
    # 叠加折线
    fig_timeline.add_trace(
        go.Scatter(
            x=dates, y=counts,
            mode="lines+markers",
            line=dict(color="#dc3545", width=2),
            name="趋势",
        )
    )
    st.plotly_chart(fig_timeline, use_container_width=True)
else:
    st.info("暂无标注时间线数据")


# ═══════════════════════════════════════════════════════════════════════════════
# 明细数据表
# ═══════════════════════════════════════════════════════════════════════════════

st.divider()
st.subheader("📋 标注明细")

# 按标签分组的统计
if stats["label_counts"]:
    detail_data = []
    for label, count in stats["label_counts"].items():
        pct = count / stats["annotated_count"] * 100 if stats["annotated_count"] > 0 else 0
        detail_data.append({
            "分类标签": label,
            "数量": count,
            "占比": f"{pct:.1f}%",
        })

    # 添加合计行
    detail_data.append({
        "分类标签": "**合计**",
        "数量": stats["annotated_count"],
        "占比": "100%",
    })

    st.dataframe(detail_data, use_container_width=True)
else:
    st.info("暂无标注数据")

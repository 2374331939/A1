"""
=============================================================================
 01_Dashboard.py — 首页仪表盘
=============================================================================
 展示项目核心统计数据：
 - 统计卡片（总图片数、已标注数、标注进度）
 - 饼图（标签分布）
 - 柱状图（标注进度概览）
=============================================================================
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from database import get_statistics, get_daily_stats

# ── 页面标题 ────────────────────────────────────────────────────────────────
st.title("📊 医学影像标注仪表盘")
st.caption("项目整体标注进度和数据总览")


# ── 获取数据 ────────────────────────────────────────────────────────────────
stats = get_statistics()
daily_stats = get_daily_stats()


# ═══════════════════════════════════════════════════════════════════════════════
# 第 1 行：统计卡片
# ═══════════════════════════════════════════════════════════════════════════════

if stats["total_images"] == 0:
    # 数据库为空时的提示
    st.info("📭 数据库为空，请先前往 **导入页面** 导入图像。")
    st.stop()

# 用 5 列展示核心指标
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.metric(
        label="📁 总图像数",
        value=stats["total_images"],
    )

with col2:
    st.metric(
        label="✅ 已标注",
        value=stats["annotated_count"],
    )

with col3:
    st.metric(
        label="⏳ 未标注",
        value=stats["unannotated_count"],
    )

with col4:
    st.metric(
        label="📈 标注进度",
        value=f"{stats['annotation_progress']:.1f}%",
        delta=None,
    )

with col5:
    # 计算各类别总数
    total_labeled = sum(stats["label_counts"].values())
    label_breakdown = " | ".join(
        f"{k}: {v}" for k, v in stats["label_counts"].items()
    )
    st.metric(
        label="🏷️ 已分类数",
        value=total_labeled,
        help=label_breakdown if label_breakdown else "暂无分类数据",
    )

st.divider()


# ═══════════════════════════════════════════════════════════════════════════════
# 第 2 行：图表区域（两列布局）
# ═══════════════════════════════════════════════════════════════════════════════

chart_col1, chart_col2 = st.columns(2)


# ── 左侧：标签分布饼图 ──────────────────────────────────────────────────────
with chart_col1:
    st.subheader("🥧 标签分布")

    if stats["label_counts"]:
        # 准备数据
        labels = list(stats["label_counts"].keys())
        values = list(stats["label_counts"].values())

        # 定义颜色映射
        color_map = {
            "正常": "#28a745",
            "肺炎": "#dc3545",
            "不确定": "#ffc107",
        }
        colors = [color_map.get(l, "#6c757d") for l in labels]

        # 创建饼图
        fig_pie = go.Figure(data=[
            go.Pie(
                labels=labels,
                values=values,
                marker=dict(colors=colors),
                textinfo="label+percent",
                hole=0.4,  # 环形效果
            )
        ])
        fig_pie.update_layout(
            height=400,
            margin=dict(l=20, r=20, t=30, b=20),
            showlegend=False,
        )
        st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.info("暂无标注数据")


# ── 右侧：标注进度对比柱状图 ───────────────────────────────────────────────
with chart_col2:
    st.subheader("📊 标注状态概览")

    # 用柱状图展示已标注 vs 未标注
    fig_bar = go.Figure(data=[
        go.Bar(
            x=["未标注", "已标注"],
            y=[stats["unannotated_count"], stats["annotated_count"]],
            marker=dict(
                color=["#ffc107", "#28a745"],
            ),
            text=[stats["unannotated_count"], stats["annotated_count"]],
            textposition="auto",
        )
    ])
    fig_bar.update_layout(
        height=400,
        margin=dict(l=20, r=20, t=30, b=20),
        yaxis=dict(title="图像数量"),
        showlegend=False,
    )
    st.plotly_chart(fig_bar, use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════════
# 第 3 行：每日标注趋势
# ═══════════════════════════════════════════════════════════════════════════════

st.divider()
st.subheader("📈 每日标注趋势")

if daily_stats:
    dates = [row["date"] for row in daily_stats]
    counts = [row["count"] for row in daily_stats]

    fig_line = px.line(
        x=dates,
        y=counts,
        markers=True,
        labels={"x": "日期", "y": "标注数量"},
    )
    fig_line.update_layout(
        height=350,
        margin=dict(l=20, r=20, t=20, b=20),
        xaxis=dict(tickangle=-45),
        hovermode="x unified",
    )
    # 填充面积
    fig_line.update_traces(fill="tozeroy", fillcolor="rgba(40, 167, 69, 0.15)")

    st.plotly_chart(fig_line, use_container_width=True)
else:
    st.info("暂无标注数据，开始标注后将显示每日趋势")

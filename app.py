"""
=============================================================================
 医学影像标注工具（主入口）
=============================================================================
 基于 Streamlit 的胸部X光二分类标注 Web 应用。

 启动方式：
     cd F:/MedImage-Labeler
     streamlit run app.py

 项目结构：
     F:/MedImage-Labeler/
     ├── app.py              ← 本文件（主入口 + 页面导航）
     ├── database.py         ← 数据库操作
     ├── utils.py            ← 工具函数
     ├── pages/
     │   ├── 01_Dashboard.py  ← 仪表盘
     │   ├── 02_Import.py     ← 导入图像
     │   ├── 03_Annotate.py   ← 图像标注
     │   ├── 04_Analysis.py   ← 数据分析
     │   └── 05_Export.py     ← 数据导出
     ├── data/               ← 自动生成：SQLite 数据库文件存放处
     └── requirements.txt    ← Python 依赖清单
=============================================================================
"""

import streamlit as st

# 页面全局配置（必须在所有 st 命令之前）
st.set_page_config(
    page_title="医学影像标注工具",
    page_icon="🩻",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── 初始化数据库（应用启动时自动执行）──
from database import init_database
init_database()


# ═══════════════════════════════════════════════════════════════════════════════
# 首页（欢迎页面）
# ═══════════════════════════════════════════════════════════════════════════════

def home():
    # 侧边栏底部信息
    with st.sidebar:
        st.divider()
        st.caption("数据库路径：")
        st.code("data/medimage_labeler.db")
        st.caption("v1.0 | 🩻 医学影像标注工具")

    # 首页内容
    st.title("🩻 欢迎使用医学影像标注工具")

    st.markdown("""
    ### 医学影像标注工具

    这是一个面向入门用户的 **胸部X光** 图像标注工具，支持 **正常** 和 **肺炎** 二分类标注。

    ---

    #### 📋 快速开始

    1. **📥 导入页面** — 选择本地文件夹，批量导入 X光 图像
    2. **🏷️ 图像标注页面** — 浏览图像并逐张标注分类标签
    3. **📊 分析页面** — 查看标注进度和数据分布
    4. **📤 导出页面** — 将标注结果导出为 CSV 文件

    ---

    #### 💡 使用提示

    - 支持格式：PNG、JPG、JPEG、BMP、TIFF
    - 标注支持 **正常 / 肺炎 / 不确定** 三种标签
    - 可添加可选的 **边界框** 标注病变区域
    - 所有数据自动保存在 SQLite 数据库中，无需额外配置

    ---
    """)

    # 首页统计概览（如果数据库有数据的话）
    from database import get_statistics

    stats = get_statistics()
    if stats["total_images"] > 0:
        st.subheader("📊 当前项目概览")

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("📁 总图像数", stats["total_images"])
        col2.metric("✅ 已标注", stats["annotated_count"])
        col3.metric("⏳ 未标注", stats["unannotated_count"])
        col4.metric("📈 标注进度", f"{stats['annotation_progress']:.1f}%")
    else:
        st.info("👆 点击左侧导航栏的 **导入** 开始导入你的 X光 图像。")


# ═══════════════════════════════════════════════════════════════════════════════
# 页面导航（中文化标签）
# ═══════════════════════════════════════════════════════════════════════════════

home_page = st.Page(home, title="首页", icon="🏠", default=True)
dashboard = st.Page("views/01_Dashboard.py", title="仪表盘", icon="📊")
import_pg = st.Page("views/02_Import.py", title="导入", icon="📥")
annotate = st.Page("views/03_Annotate.py", title="标注", icon="🏷️")
analysis = st.Page("views/04_Analysis.py", title="分析", icon="📊")
export = st.Page("views/05_Export.py", title="导出", icon="📤")

pg = st.navigation(
    [home_page, dashboard, import_pg, annotate, analysis, export]
)
pg.run()

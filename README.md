# A1
使用python在医学方面的帮助
数据存放指南：
├── app.py # 主入口 + 欢迎页
├── database.py # SQLite 数据库操作（images + annotations 两张表）
├── utils.py # 工具函数（文件扫描、图像加载、格式化）
├── requirements.txt # Python 依赖清单
├── pages/
│ ├── 01_Dashboard.py # 仪表盘：统计卡片 + 饼图 + 柱状图
│ ├── 02_Import.py # 导入页面：文件夹扫描 + 文件上传
│ ├── 03_Annotate.py # ⭐ 核心标注页面
│ ├── 04_Analysis.py # 数据分析：类别分布 + 尺寸分布 + 趋势
│ └── 05_Export.py # 导出页面：CSV 预览 + 下载
└── data/ # 自动创建：SQLite 数据库文件



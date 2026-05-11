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

仪表盘界面：
<img width="1915" height="880" alt="image" src="https://github.com/user-attachments/assets/16812fa4-6adb-42fc-9c34-fa0f65beeb8b" />

导入界面：
<img width="1919" height="924" alt="image" src="https://github.com/user-attachments/assets/26668f0e-97d2-44df-bf09-539cf38af156" />

标注界面：
<img width="1395" height="600" alt="image" src="https://github.com/user-attachments/assets/d3326d49-ad72-47a4-9f03-8aa92f60c412" />

数据分析界面：
<img width="1525" height="830" alt="image" src="https://github.com/user-attachments/assets/7abcb6c5-67fd-402f-8e07-7d18e8e425ed" />

数据导出界面：
<img width="1503" height="655" alt="image" src="https://github.com/user-attachments/assets/92c397de-9530-47d6-bd14-042a0c252663" />

更多功能正在开发中…………

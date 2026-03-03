# Price Searcher - 硬件价格追踪系统

## 概述

Price Searcher 是一个基于 Django 的日本乐天（Rakuten）电脑硬件价格追踪系统。系统自动采集 GPU、CPU、主板、内存、SSD 等硬件的价格数据，生成每日价格快照，并通过可视化仪表盘展示价格趋势。

## 核心功能

### 1. 关键词管理

- 支持五大硬件品类：GPU、CPU、Motherboard、RAM、SSD
- 预置主流硬件型号关键词（NVIDIA RTX 30/40/50 系列、AMD RX 6000/7000 系列、Intel Arc 等）
- 每个关键词可设置最低价格阈值（`min_price`），过滤掉低于此价格的非相关结果
- 支持通过管理后台或 API 手动添加/管理关键词

### 2. 价格采集

- 对接乐天商品搜索 API（支持 2022 新版 API 和旧版 API 双通道）
- 按关键词逐一搜索，遵守 API 速率限制（2 QPS，关键词间隔 1 秒）
- 自动去重：同一关键词、同一日期、同一商品 URL 不重复入库
- 价格过滤：仅保存高于关键词设定最低价的结果
- 支持后台线程异步采集，前端可实时查看采集进度

### 3. 数据存储（DailyPriceSnapshot）

- 每日每个搜索结果保存一条快照记录
- 反范式化设计：快照中冗余存储关键词名、品类、最低搜索价格，便于独立查询和历史回溯
- 记录字段：关键词、日期、来源站点、商品名称、价格、商品链接

### 4. 数据聚合与统计

- **单关键词统计**：按日期聚合最低价、最高价、平均价及最低价商品链接
- **全关键词汇总**：跨关键词的每日价格摘要，支持按品类筛选
- **日期价格列表**：查看指定日期所有商品的价格分布
- **关键词摘要**：每个关键词的最新采集日期和最低价格

### 5. 可视化仪表盘

- 基于 Web 的价格趋势可视化页面
- 支持按品类切换查看（GPU / CPU / RAM / SSD / Motherboard）
- 展示每日价格走势图表和明细数据表

### 6. 硬件档位参考表

- 预置 CPU、主板、内存、SSD 的档位划分（入门 → 发烧级，共 6 档）
- 对比展示 Intel/AMD 对应型号或各类主流型号
- 为关键词初始化提供数据来源

## API 接口

| 接口路径 | 方法 | 说明 |
|---------|------|------|
| `/api/search/` | GET | 实时搜索（`?q=关键词`） |
| `/api/keywords/` | GET | 获取所有关键词及最新价格摘要 |
| `/api/daily-stats/` | GET | 单关键词每日统计（`?keyword=xxx` 或 `?keyword_id=123`） |
| `/api/dashboard-stats/` | GET | 全关键词每日汇总（`?category=gpu`） |
| `/api/daily-prices/` | GET | 指定日期所有价格记录（`?date=YYYY-MM-DD`） |
| `/api/collect-progress/` | GET | 采集进度查询 |
| `/api/seed-gpu-keywords/` | POST | 初始化 GPU 预设关键词 |
| `/api/run-collect-daily-prices/` | POST | 启动后台采集（可选指定关键词列表） |

## 管理命令

| 命令 | 说明 |
|------|------|
| `python manage.py seed_gpu_keywords` | 初始化 GPU 型号关键词（60+ 款） |
| `python manage.py seed_hardware_tiers` | 初始化硬件档位参考表 |
| `python manage.py seed_other_hardware_keywords --category=cpu` | 从档位表提取并创建 CPU/RAM/SSD/主板关键词 |
| `python manage.py collect_daily_prices` | 采集所有关键词的当日价格快照 |
| `python manage.py sync_snapshots_to_keywords` | 从快照数据反向创建缺失的关键词记录 |

## 数据模型

### Keyword（关键词）

追踪的硬件搜索关键词。

| 字段 | 类型 | 说明 |
|------|------|------|
| name | CharField(200) | 关键词名称（唯一） |
| category | CharField(20) | 品类：gpu / cpu / motherboard / ram / ssd |
| min_price | PositiveIntegerField | 最低价格阈值（日元），默认 20000 |

### DailyPriceSnapshot（每日价格快照）

每日每个搜索结果的价格记录。

| 字段 | 类型 | 说明 |
|------|------|------|
| keyword | ForeignKey(Keyword) | 关联的关键词 |
| date | DateField | 采集日期 |
| keyword_name | CharField(200) | 冗余：关键词名称 |
| category | CharField(20) | 冗余：品类 |
| min_search_price | PositiveIntegerField | 冗余：采集时的最低价阈值 |
| site | CharField(50) | 来源平台（如 Rakuten） |
| product_name | CharField(500) | 商品名称 |
| price | PositiveIntegerField | 价格（日元） |
| url | URLField(1000) | 商品链接 |

### HardwareTierRow（硬件档位参考）

硬件档位对照表，用于展示和初始化关键词。

| 字段 | 类型 | 说明 |
|------|------|------|
| category | CharField(20) | 品类 |
| tier | CharField(20) | 档位：entry / value / mid / mid_high / high / enthusiast |
| sort_order | PositiveSmallIntegerField | 排序 |
| col1_name / col1_value | CharField | 第一列（如 Intel 系列） |
| col2_name / col2_value | CharField | 第二列（如 AMD 系列） |

## 技术栈

- **后端**: Django + Django REST Framework
- **数据库**: SQLite（开发）/ MySQL（生产）
- **外部 API**: 乐天商品搜索 API（Rakuten Ichiba Item Search）
- **前端**: HTML 模板 + JavaScript 可视化

## 环境变量

| 变量 | 说明 |
|------|------|
| `RAKUTEN_APP_ID` | 乐天 API 应用 ID（必需） |
| `RAKUTEN_ACCESS_KEY` | 2022 版 API 访问密钥（可选） |
| `RAKUTEN_APP_URL` | API 白名单域名（默认 http://localhost） |
| `MYSQL_NAME` | MySQL 数据库名（设置后使用 MySQL） |

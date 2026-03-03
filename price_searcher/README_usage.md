# 价格查询项目 - 使用说明

## 一、这个项目怎么用（Django 部分）

### 1. 启动服务

```powershell
cd c:\Users\gos\project\price_searcher\price_searcher
# 如有虚拟环境先激活，例如：..\openclaw\Scripts\activate.ps1
python manage.py runserver
```

### 2. 你能用的页面和接口

| 用途 | 地址 |
|------|------|
| **仪表盘**（看每日最低价/平均价曲线 + 最低价链接） | http://127.0.0.1:8000/api/dashboard/ |
| **即时搜索**（输入关键词立刻查乐天价格） | http://127.0.0.1:8000/api/search/?q=RTX%204070 |
| **管理后台**（添加/管理要追踪的关键词） | http://127.0.0.1:8000/admin/ |

### 3. 日常使用流程

1. **第一次**：在 admin 里添加关键词（如 `RTX 4070`、`RTX 4080`），并创建管理员账号：  
   `python manage.py createsuperuser`
2. **每天一次**：在终端执行采集，把当天各平台价格写入数据库：  
   `python manage.py collect_daily_prices`
3. **随时查看**：打开 **仪表盘**，选择关键词，看折线图和表格（每日最低价、平均价、最低价链接）。

---

## 二、和 OpenClaw 的关系

**这个 Django 项目本身没有“内置” OpenClaw**，两者是分开的两个东西：

- **Django（本项目）**：跑在 8000 端口，提供价格搜索 API 和仪表盘网页。
- **OpenClaw**：跑在 18789 端口，是你的 AI 助手（聊天、工具调用等）。

### 怎么“一起用”OpenClaw 和这个项目

**方式 A：各用各的（最简单）**

- 用浏览器打开：http://127.0.0.1:8000/api/dashboard/ 看价格、用搜索。
- OpenClaw 照常用来聊天、写代码等。两者互不依赖。

**方式 B：让 OpenClaw 帮你“查价格”**

1. 保证 Django 已启动：`python manage.py runserver`（127.0.0.1:8000）。
2. 打开 OpenClaw（例如 http://127.0.0.1:18789/）。
3. 在对话里用自然语言让 AI 去请求你的 API，例如：
   - “帮我请求 http://127.0.0.1:8000/api/search/?q=RTX%204070 并把返回的 JSON 里价格和链接整理成列表。”
   - “打开 http://127.0.0.1:8000/api/daily-stats/?keyword=RTX%204070 看看最近每日最低价。”
4. 若 OpenClaw 启用了 **Web 工具**（如 `web_fetch`），它可以用工具去访问上述 URL，拿到 JSON 后再用文字总结给你。

也就是说：**“用到 OpenClaw” = 在 OpenClaw 里对话，让 AI 去调用你本机 8000 端口的 Django API**，而不是在 Django 里装 OpenClaw。

---

## 三、小结

| 想做的事 | 做法 |
|----------|------|
| 看每日价格曲线、最低价链接 | 浏览器打开 **http://127.0.0.1:8000/api/dashboard/** |
| 立刻查某关键词价格 | 打开 **http://127.0.0.1:8000/api/search/?q=关键词** 或让 OpenClaw 请求这个 URL |
| 添加/管理追踪关键词 | 打开 **http://127.0.0.1:8000/admin/** |
| 每天存一次价格 | 运行 `python manage.py collect_daily_prices` |
| 用 OpenClaw 查价格 | 在 OpenClaw 里让 AI 请求 `http://127.0.0.1:8000/api/search/?q=xxx` 或 daily-stats，并帮你总结 |

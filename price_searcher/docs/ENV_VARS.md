# 环境变量说明（含 Render 部署必填项）

本地开发可用 `.env` 文件（不要提交到 Git，已列入 `.gitignore`）；  
在 Render 上请在 Web Service 的 **Environment** 里逐项添加。

---

## 必填（Render 部署）

| 变量名 | 说明 | 示例 / 获取方式 |
|--------|------|-----------------|
| **DATABASE_URL** | PostgreSQL 连接串（Render 会为 PostgreSQL 实例提供） | 在 Render 的 PostgreSQL 详情页复制 **Internal Database URL**；或 Environment 里选「Add from Render PostgreSQL」自动绑定 |
| **DJANGO_SECRET_KEY** | Django 安全密钥，生产环境必须设 | 本地生成：`python -c "import secrets; print(secrets.token_hex(32))"`；或 Render 用「Generate」生成 |
| **DJANGO_DEBUG** | 是否开启调试 | 生产填 **0** |
| **ALLOWED_HOSTS** | 允许的 Host，逗号分隔 | 部署在 Render 填 **.onrender.com**（含子域名）；若有自定义域名再加进去 |
| **RAKUTEN_APP_ID** | 乐天 API 应用 ID | 从乐天开发者后台获取，必填否则无法搜价 |

---

## 可选（按需填写）

| 变量名 | 说明 | 示例 |
|--------|------|------|
| **EXPORT_DATA_KEY** | 导出数据用的密钥；在本地 .env 设置后，用浏览器打开「导出」链接即可下载 data.json（不用 Shell） | 自设一串随机字符，例如 `my-export-secret` |
| **IMPORT_DATA_KEY** | 导入数据用的密钥；在 Render 环境变量里设置后，在浏览器打开「导入」页面上传 data.json 即可迁入（不用 Shell） | 与 EXPORT_DATA_KEY 同值或另设一串，例如 `my-import-secret` |
| **RAKUTEN_ACCESS_KEY** | 乐天 2022 新 API 的 Access Key | 若使用新 API 再填 |
| **RAKUTEN_APP_URL** | 乐天 2022 新 API 的 App URL | 如 `https://your-app.onrender.com` |
| **MYSQL_NAME** | 本地用 MySQL 时的数据库名 | 仅本地；Render 用 PostgreSQL 不需设 |
| **MYSQL_USER** / **MYSQL_PASSWORD** / **MYSQL_HOST** / **MYSQL_PORT** | 本地 MySQL 连接用 | 仅本地 |

---

## 小结：在 Render 最少要设的 5 个

1. **DATABASE_URL**（从 Render PostgreSQL 绑定或粘贴）  
2. **DJANGO_SECRET_KEY**（随机字符串或 Generate）  
3. **DJANGO_DEBUG** = `0`  
4. **ALLOWED_HOSTS** = `.onrender.com`  
5. **RAKUTEN_APP_ID**（你的乐天应用 ID）

其他变量按需添加（如乐天新 API、自定义域名等）。

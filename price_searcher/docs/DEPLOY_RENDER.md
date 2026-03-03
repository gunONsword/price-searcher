# 部署到 Render 并迁移数据库

本文说明如何将 Price Searcher 部署到 Render，并使用 PostgreSQL 做数据库迁移。

---

## 一、前置准备

- 已把本仓库推送到 GitHub/GitLab，并可在 Render 中连接。
- 乐天 API：准备好 `RAKUTEN_APP_ID`（必填），如需 2022 新 API 再准备 `RAKUTEN_ACCESS_KEY`、`RAKUTEN_APP_URL`。

---

## 二、在 Render 创建 PostgreSQL 数据库

1. 登录 [Render](https://render.com) → **Dashboard** → **New +** → **PostgreSQL**。
2. 填写：
   - **Name**：例如 `price-searcher-db`
   - **Database**：例如 `price_searcher`
   - **User**：例如 `price_searcher`
   - **Region**：选离你近的（如 Singapore）。
3. 创建完成后，在数据库详情页找到 **Internal Database URL**（或 **External Database URL**，若要从本机迁移数据用外网地址）。  
   Render 会提供形如：  
   `postgres://user:password@host/database?sslmode=require`  
   的 `DATABASE_URL`，后面 Web 服务会用到。

---

## 三、创建 Web Service 并绑定仓库

1. **New +** → **Web Service**。
2. 连接你的 Git 仓库，选中本项目所在仓库和分支。
3. **Root Directory**（若仓库根就是本项目，即根目录有 `manage.py`）：留空。  
   若项目在子目录（例如仓库根下有个 `price_searcher` 文件夹，里面有 `manage.py`），则填：`price_searcher`。
4. 配置：
   - **Runtime**：Python 3
   - **Build Command**：
     ```bash
     pip install -r requirements.txt && python manage.py collectstatic --noinput
     ```
   - **Start Command**：
     ```bash
     gunicorn price_searcher.wsgi:application
     ```
   - **Release Command**（每次部署前执行，用于迁移）：
     ```bash
     python manage.py migrate --noinput
     ```

---

## 四、环境变量

在 Web Service 的 **Environment** 里添加。**完整列表与说明见 [docs/ENV_VARS.md](ENV_VARS.md)**。

**Render 上最少要设的 5 个：**

| Key | 说明 | 示例/必填 |
|-----|------|-----------|
| `DATABASE_URL` | PostgreSQL 连接串 | 从上面创建的 PostgreSQL 实例里复制 **Internal Database URL**；或 Environment 里选「Add from Render PostgreSQL」自动绑定 |
| `DJANGO_SECRET_KEY` | Django 密钥 | 生产必填，可点 Render 的「Generate」或本地运行 `python -c "import secrets; print(secrets.token_hex(32))"` |
| `DJANGO_DEBUG` | 是否调试 | 生产填 **0** |
| `ALLOWED_HOSTS` | 允许的 Host | 填 **.onrender.com**（有自定义域名再逗号追加） |
| `RAKUTEN_APP_ID` | 乐天应用 ID | 必填 |

可选：`RAKUTEN_ACCESS_KEY`、`RAKUTEN_APP_URL`（乐天 2022 新 API）。详见 [ENV_VARS.md](ENV_VARS.md)。

---

## 五、数据库迁移（表结构）

- 每次部署时，Render 会先执行 **Release Command**：`python manage.py migrate --noinput`，自动应用所有 Django migrations，无需在本地对 Render 的库再执行一次。
- 若首次部署前想确认迁移是否正常，可在本地用同一 `DATABASE_URL`（用 External URL + 本机 IP 白名单）执行：
  ```bash
  export DATABASE_URL="postgres://..."
  python manage.py migrate --noinput
  ```

---

## 六、把本地数据库数据迁移到 Render 的 PostgreSQL

若你本地用的是 SQLite（默认）或 MySQL，需要把现有数据迁到 Render 的 PostgreSQL。  
**可以不使用 Shell**，只用浏览器完成导出和导入。

---

### 方式 A：不用 Shell（推荐，仅用浏览器）

#### 1. 在本地导出 data.json

1. 在本地项目 **.env** 里增加一行（自设一串密钥，不要泄露）：
   ```env
   EXPORT_DATA_KEY=你自己设的密钥
   ```
2. **不要** 设置 `DATABASE_URL`，让项目继续用本地 SQLite（或 MySQL）。
3. 在本地用 IDE 的「运行」启动 Django（例如运行 `manage.py runserver`），在浏览器打开：
   ```
   http://127.0.0.1:8000/api/tools/export-data/?key=你自己设的密钥
   ```
   把 `你自己设的密钥` 换成上面设置的 `EXPORT_DATA_KEY`。
4. 浏览器会下载一个 **data.json** 文件，保存好，待会在 Render 上导入。

#### 2. 在 Render 上导入数据

1. 在 Render 的 **Web Service** → **Environment** 里添加环境变量：
   - **IMPORT_DATA_KEY** = 与本地用的密钥一致（或你另设的一串，记住即可）。
2. 部署完成后，在浏览器打开（把 `https://你的服务.onrender.com` 换成你的实际地址）：
   ```
   https://你的服务.onrender.com/api/tools/import-data/
   ```
3. 在页面上输入 **Key**（与 `IMPORT_DATA_KEY` 相同），选择刚才下载的 **data.json**，点击「Run migrate and import」。
4. 页面会显示 migrate 和 loaddata 的结果；成功即表示数据已迁入 Render 的 PostgreSQL。

**说明**：首次部署时 Render 的 Release Command 会先执行 `migrate` 建表；导入页面的「Run migrate and import」会再执行一次 migrate（无影响）并执行 loaddata 导入你的 data.json。

---

### 方式 B：使用 Shell 迁移（可选）

若你习惯用命令行，可以用下面的方式。

#### B.1 在 Render 开放本机 IP（仅方式 B 需要）

1. 打开 Render Dashboard → 你的 **PostgreSQL** 实例。
2. 在 **Connections** 里找到 **External Database URL**，复制备用。
3. 同一页找到 **Allow List**，点击 **Add IP** 或 **Add current IP**，以便本机连上 PostgreSQL。

#### B.2 在本地用命令导出

在项目根目录（有 `manage.py` 的目录）执行：

```bash
python manage.py dumpdata --natural-foreign --natural-primary -e contenttypes -e auth.Permission -o data.json
```

会生成 `data.json`（已列入 `.gitignore`）。

#### B.3 在本地用命令导入到 Render

设置 `DATABASE_URL` 为 Render 的 **External Database URL** 后执行：

- **Windows（PowerShell）：**  
  `$env:DATABASE_URL = "postgres://..."; python manage.py migrate --noinput; python manage.py loaddata data.json`
- **Windows（CMD）：**  
  `set DATABASE_URL=postgres://...` 然后 `python manage.py migrate --noinput` 与 `python manage.py loaddata data.json`
- **Linux / macOS：**  
  `export DATABASE_URL="postgres://..."; python manage.py migrate --noinput; python manage.py loaddata data.json`

---

### 迁移完成后

- 数据已在 Render 的 PostgreSQL 里；Web Service 使用 **Internal Database URL** 即可。
- 若用了方式 B，可把 Allow List 里本机 IP 移除。
- `data.json` 可本地保留或删除，不要提交到 Git。

---

## 七、一键蓝图（可选）

仓库根目录下的 `render.yaml` 为 Render Blueprint，可同时创建 Web Service 和 PostgreSQL：

1. Dashboard → **New +** → **Blueprint**。
2. 连接仓库，选择带 `render.yaml` 的分支。
3. Render 会解析 `render.yaml`，创建数据库和 Web 服务；你只需在 Web Service 里补上 `RAKUTEN_APP_ID` 等环境变量（见第四节）。

若使用蓝图，数据库名、Release Command、Build/Start 已写在 `render.yaml` 中，只需核对 **Root Directory** 是否与仓库结构一致（见第三节）。

---

## 八、部署后检查

- 打开 Web Service 的 URL（如 `https://price-searcher-xxx.onrender.com`），应能打开仪表盘。
- 若 500 错误：在 Render 的 **Logs** 里查看 traceback；常见原因：`DATABASE_URL` 未设、`SECRET_KEY` 未设、`ALLOWED_HOSTS` 未包含当前域名。
- 静态文件由 WhiteNoise 提供，无需再配 CDN（除非你另有需求）。

---

## 九、小结

| 步骤 | 动作 |
|------|------|
| 1 | 在 Render 创建 PostgreSQL，拿到 `DATABASE_URL` |
| 2 | 创建 Web Service，连仓库，设 Root Directory（如需） |
| 3 | Build：`pip install -r requirements.txt && python manage.py collectstatic --noinput` |
| 4 | Start：`gunicorn price_searcher.wsgi:application` |
| 5 | Release：`python manage.py migrate --noinput` |
| 6 | 环境变量：`DATABASE_URL`、`DJANGO_SECRET_KEY`、`DJANGO_DEBUG=0`、`ALLOWED_HOSTS`、`RAKUTEN_APP_ID` 等 |
| 7 | 若要从旧库迁数据：dumpdata → 在 Render DB 上 migrate → loaddata |

完成以上步骤后，应用会在每次部署时自动执行迁移，数据库使用 Render 的 PostgreSQL。

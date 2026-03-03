# 乐天 API 方案 A：设置 Referer/Origin 白名单（继续用 pk_...）

使用 **pk_...** 这种 accessKey 时，新 API（openapi.rakuten.co.jp）会校验请求的 **Origin / Referer**。  
若返回 `403 HTTP_REFERRER_NOT_ALLOWED`，需要在乐天应用里把允许的网址登记上。

---

## 步骤 1：登录乐天开发者后台

1. 打开：**https://webservice.rakuten.co.jp/** 或你当时申请 **pk_** 密钥时用的那个后台。
2. 用乐天账号登录。

---

## 步骤 2：找到「许可的网站」或类似设置

- 进入 **应用一览** / **アプリ一覧**：https://webservice.rakuten.co.jp/app/list/
- 点进你用来拿 **pk_** 密钥的**那一个应用**。
- 在应用详情或编辑页面里，查找类似下面的项目（名称可能略有不同）：
  - **許可されたWebサイト** / 许可的网站
  - **Allowed websites** / Referer URL / Redirect URI
  - **リファラ登録** / Referer 登记

（2026 年新后台里，有时会在「应用信息编辑」「API 访问范围」等页面。）

---

## 步骤 3：添加允许的 URL

在「许可的网站」里**新增**下面任意一种（或两种都加，更稳）：

| 用途           | 建议填写的 URL                  |
|----------------|----------------------------------|
| 通用（推荐先试） | `https://www.rakuten.co.jp/`     |
| 本机调试       | `http://127.0.0.1:8000/` 或 `http://localhost:8000/` |

- 若支持「前缀匹配」，只填 `https://www.rakuten.co.jp` 也可。
- 保存后，部分后台会提示「约 10 分钟生效」，可稍等再试。

---

## 步骤 4：确认请求里已带 Origin / Referer

本项目里已经对 2022 API 做了：

- 请求头：`Origin: https://www.rakuten.co.jp/`
- 请求头：`Referer: https://www.rakuten.co.jp/`
- 以及合适的 `User-Agent`

只要你在步骤 3 里把 **https://www.rakuten.co.jp/** 加进「许可的网站」，一般就不会再出现 `HTTP_REFERRER_NOT_ALLOWED`。

---

## 步骤 5：再跑一次采集

```powershell
cd c:\Users\gos\project\price_searcher\price_searcher
python manage.py collect_daily_prices --keyword "RTX 4070"
```

若仍 403，请确认：

1. 登录的是**拥有 pk_ 密钥的同一个应用**；
2. 保存后已等待几分钟；
3. 填写的 URL 和上面完全一致（末尾有无 `/` 按后台要求）。

---

## 参考

- 乐天 2022 API 文档：https://webservice.rakuten.co.jp/documentation/ichiba-item-search  
- 应用一览：https://webservice.rakuten.co.jp/app/list/  
- 他人经验：设置 **Origin** 解决 403（Referer 用 `https://www.rakuten.co.jp/` 可过检）

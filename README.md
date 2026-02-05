# 校园网自动登录脚本

该脚本会定时检测外网连通性，发现断网后自动打开校园网登录页面，填充账号密码并点击登录。支持系统托盘图标，后台持续监控。

## 打包文件(文件太大传不上来)
可在控制台运行
pyinstaller --onefile --noconsole auto_login_portal.py --hidden-import=pystray --hidden-import=PIL --hidden-import=playwright.sync_api
自行打包
输出文件在 `dist/auto_login_portal.exe`，已包含环境和浏览器内核，可直接运行。

注意事项：

- 文件体积较大（包含浏览器内核属于正常现象）
- 运行时会在同目录生成 `login_credentials.json`（明文保存账号密码）
- 如需更新账号密码，删除该文件后重新运行即可弹窗输入

## 功能概览

- 断网检测与自动登录
- 账号密码弹窗输入并保存
- Edge -> Chrome -> Chromium 启动兜底
- 托盘图标一键退出

## 环境要求

- Windows 10/11
- Python 3.10+（建议 3.11 或 3.12）
- Microsoft Edge 或 Google Chrome（至少其一）

## 安装与运行

1. 克隆或下载代码

2. 安装依赖

```powershell
pip install playwright pystray pillow
playwright install msedge
playwright install chrome
```

3. 运行脚本

```powershell
python auto_login_portal.py
```

首次运行会弹出输入窗口，要求填写用户名和密码。脚本会将凭据保存到本地文件，后续自动使用。

## 托盘使用

- 运行后会出现托盘图标
- 右键 `Exit` 退出后台监控

## 配置说明

- 登录页面地址：`auto_login_portal.py` 内的 `LOGIN_URL`
- 外网检测目标：`CHECK_HOST`（默认 223.5.5.5）
- 凭据文件：`login_credentials.json`

## 打包为 exe

### 仅打包程序（体积小，但目标机需安装浏览器内核）

```powershell
pyinstaller --onefile --noconsole auto_login_portal.py --hidden-import=pystray --hidden-import=PIL --hidden-import=playwright.sync_api
```

目标机需执行一次：

```powershell
playwright install msedge
playwright install chrome
```

### 打包程序 + 浏览器内核（体积大，可直接运行）

```powershell
robocopy "$env:LOCALAPPDATA\ms-playwright" ".\playwright-browsers" /E
pyinstaller --onefile --noconsole auto_login_portal.py --hidden-import=pystray --hidden-import=PIL --hidden-import=playwright.sync_api --add-data "playwright-browsers;playwright-browsers"
```

输出文件在 `dist/auto_login_portal.exe`。

## 常见问题

- `ModuleNotFoundError: No module named 'playwright'`
  - 当前 Python 环境未安装依赖，请执行 `pip install playwright`

- 浏览器没有弹出或无法点击
  - 请确认已执行 `playwright install msedge` 或 `playwright install chrome`
  - 确保本机已安装 Edge/Chrome

- 登录后仍显示未联网
  - 可能校园网认证系统异常，建议稍后重试或修改 `CHECK_HOST`

## 安全提示

- 凭据保存在 `login_credentials.json`（明文）
- 请勿将该文件提交到公共仓库
- 如需清除凭据，直接删除该文件即可

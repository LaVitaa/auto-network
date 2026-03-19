import os
import time
import subprocess
import platform
import json
import threading
import pystray
from PIL import Image, ImageDraw
import sys
from playwright.sync_api import sync_playwright

# 你要打开的认证页面 URL
LOGIN_URL = (
    "http://10.10.9.9/eportal/index.jsp?"
    "wlanuserip=58.199.169.135&"
    "wlanacname=BS-E3_RG-N18010&"
    "ssid=&"
    "nasip=172.18.2.19&"
    "snmpagentip=&"
    "mac=7085c2ac2045&"
    "t=wireless-v2-plain&"
    "url=http://123.123.123.123/&"
    "apmac=&"
    "nasid=BS-E3_RG-N18010&"
    "vid=106&"
    "port=69&"
    "nasportid=TenGigabitEthernet%208/21.01060000:106-0"
)

# 用于检测外网连通性的目标（ping 外网才能判断是否需要重新认证）
CHECK_HOST = "223.5.5.5"  # 阿里 DNS，国内访问稳定；也可以用 8.8.8.8

# 凭据存储文件
CREDENTIALS_FILE = "login_credentials.json"
LOG_FILE = "auto_login.log"



def save_credentials(username, password):
    """保存用户凭据到文件"""
    try:
        credentials = {"username": username, "password": password}
        with open(CREDENTIALS_FILE, 'w', encoding='utf-8') as f:
            json.dump(credentials, f)
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 凭据已保存")
    except Exception as e:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 保存凭据失败: {e}")

def load_credentials():
    """从文件加载用户凭据"""
    try:
        if os.path.exists(CREDENTIALS_FILE):
            with open(CREDENTIALS_FILE, 'r', encoding='utf-8') as f:
                credentials = json.load(f)
                return credentials.get("username"), credentials.get("password")
    except Exception as e:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 加载凭据失败: {e}")
    return None, None

def prompt_credentials_popup():
    """使用弹窗获取用户凭据（同一窗口，密码可见）"""
    try:
        import tkinter as tk
        from tkinter import ttk

        root = tk.Tk()
        root.title("校园网登录")
        root.attributes("-topmost", True)
        root.resizable(False, False)

        result = {"username": None, "password": None}

        frame = ttk.Frame(root, padding=12)
        frame.grid(row=0, column=0)

        ttk.Label(frame, text="用户名:").grid(row=0, column=0, sticky="w")
        username_entry = ttk.Entry(frame, width=30)
        username_entry.grid(row=0, column=1, padx=(8, 0), pady=(0, 8))

        ttk.Label(frame, text="密码:").grid(row=1, column=0, sticky="w")
        password_entry = ttk.Entry(frame, width=30)
        password_entry.grid(row=1, column=1, padx=(8, 0), pady=(0, 8))

        def on_submit():
            result["username"] = username_entry.get().strip()
            result["password"] = password_entry.get().strip()
            root.destroy()

        def on_cancel():
            root.destroy()

        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=2, column=0, columnspan=2, pady=(4, 0))
        ttk.Button(btn_frame, text="确定", command=on_submit).grid(row=0, column=0, padx=4)
        ttk.Button(btn_frame, text="取消", command=on_cancel).grid(row=0, column=1, padx=4)

        username_entry.focus_set()
        root.mainloop()

        username = result["username"]
        password = result["password"]

        if username and password:
            return username, password
    except Exception:
        return None, None

    return None, None


def get_user_credentials():
    """获取用户凭据（从文件或弹窗/控制台输入）"""
    username, password = load_credentials()
    
    if username and password:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 使用已保存的凭据")
        return username, password

    print(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] 需要输入校园网登录凭据（用于自动登录）")
    username, password = prompt_credentials_popup()
    if username and password:
        save_credentials(username, password)
        return username, password

    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 弹窗获取失败，改用控制台输入")
    try:
        username = input("请输入用户名: ").strip()
        password = input("请输入密码: ").strip()

        if username and password:
            save_credentials(username, password)
            return username, password
        print("用户名或密码不能为空")
        return None, None
    except KeyboardInterrupt:
        print("\n用户取消输入")
        return None, None

def is_network_up():
    """通过 ping 外网地址判断网络是否通畅（能访问外网=已认证）"""
    param = "-n" if platform.system().lower() == "windows" else "-c"
    try:
        creationflags = 0
        startupinfo = None
        if platform.system().lower() == "windows":
            creationflags = subprocess.CREATE_NO_WINDOW
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        # 尝试 ping 一次，超时设为 2 秒
        result = subprocess.run(
            ["ping", param, "1", "-w", "2000" if platform.system().lower() == "windows" else "2", CHECK_HOST],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=creationflags,
            startupinfo=startupinfo
        )
        return result.returncode == 0
    except Exception as e:
        return False

def create_tray_icon(stop_event):
    """创建系统托盘图标"""
    image = Image.new("RGB", (64, 64), "#1f2937")
    draw = ImageDraw.Draw(image)
    draw.ellipse((12, 12, 52, 52), fill="#22c55e")

    def on_exit(icon, item):
        stop_event.set()
        icon.stop()

    menu = pystray.Menu(
        pystray.MenuItem("Exit", on_exit),
    )
    icon = pystray.Icon("auto_login_portal", image, "校园网自动登录", menu)
    return icon

def auto_login():
    """单方案：Playwright 自动填充并点击登录"""
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 开始自动登录流程...")
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 方案: 自动登录模式")
    
    # 获取用户凭据
    username, password = get_user_credentials()
    if not username or not password:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 未提供凭据，无法自动登录")
        return False
    
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        browser = None
        try:
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 第 {retry_count + 1} 次自动登录尝试...")
            with sync_playwright() as p:
                # 尝试启动 Edge -> Chrome -> Chromium
                try:
                    browser = p.chromium.launch(
                        channel="msedge",
                        headless=False,
                        args=['--no-sandbox', '--start-maximized']
                    )
                    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 成功启动 Edge 浏览器")
                except Exception:
                    try:
                        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Edge 启动失败，尝试 Chrome...")
                        browser = p.chromium.launch(
                            channel="chrome",
                            headless=False,
                            args=['--no-sandbox', '--start-maximized']
                        )
                        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 成功启动 Chrome 浏览器")
                    except Exception:
                        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Chrome 启动失败，使用 Chromium...")
                        browser = p.chromium.launch(headless=False, args=['--start-maximized'])

                page = browser.new_page()
                
                # 打开登录页面
                print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 正在访问登录页面...")
                page.goto(LOGIN_URL, timeout=30000)
                print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 页面加载完成，开始自动填充...")
                
                # 等待页面加载
                time.sleep(2)
                
                # 查找用户名和密码输入框并填充（先聚焦再输入，避免需要鼠标点选）
                try:
                    username_selector = "#username"
                    password_selector = "#pwd"

                    if page.locator(username_selector).count() > 0:
                        page.wait_for_selector(username_selector, state="attached", timeout=5000)
                        page.evaluate(
                            """
                            ({ selector, value }) => {
                                const el = document.querySelector(selector);
                                if (!el) return false;
                                el.value = value;
                                el.dispatchEvent(new Event('input', { bubbles: true }));
                                el.dispatchEvent(new Event('change', { bubbles: true }));
                                return true;
                            }
                            """,
                            {"selector": username_selector, "value": username},
                        )
                        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 已填充用户名")
                    else:
                        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 警告：未找到用户名输入框")

                    if page.locator(password_selector).count() > 0:
                        page.wait_for_selector(password_selector, state="attached", timeout=5000)
                        page.evaluate(
                            """
                            ({ selector, value }) => {
                                const el = document.querySelector(selector);
                                if (!el) return false;
                                el.value = value;
                                el.dispatchEvent(new Event('input', { bubbles: true }));
                                el.dispatchEvent(new Event('change', { bubbles: true }));
                                return true;
                            }
                            """,
                            {"selector": password_selector, "value": password},
                        )
                        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 已填充密码")
                    else:
                        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 警告：未找到密码输入框")

                except Exception as e:
                    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 填充凭据时出错: {e}")
                
                # 查找并点击登录按钮
                print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 查找登录按钮...")
                page.wait_for_selector("#loginLink", timeout=15000)
                page.click("#loginLink")
                print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 已点击登录按钮，等待登录完成...")
                
                # 等待登录处理
                time.sleep(3)
                
                # 检测网络连通性
                print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 检测网络连通性...")
                for i in range(8):  # 40秒内每5秒检测一次
                    if is_network_up():
                        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 自动登录成功！网络已连通")
                        return True
                    else:
                        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 等待网络连通... ({i+1}/8)")
                        time.sleep(5)
                
                print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 登录后网络仍未连通")
            
        except Exception as e:
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 第 {retry_count + 1} 次自动登录失败: {e}")
        finally:
            if browser:
                print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 关闭浏览器...")
                browser.close()
        
        retry_count += 1
        if retry_count < max_retries:
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 等待 10 秒后重试...")
            time.sleep(10)
    
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 所有登录尝试失败")
    return False

def monitor_loop(stop_event):
    write_log("=== 校园网自动登录监控程序 ===")
    write_log("网络监控已启动，可从托盘图标退出...")
    write_log(f"检测目标: {CHECK_HOST}")

    trigger_count = 0
    write_log("历史断网触发次数: 本次运行内统计")

    # 首次运行时预先获取凭据（如果需要）
    write_log("检查登录凭据...")
    username, password = load_credentials()
    if not username or not password:
        write_log("首次运行，请设置登录凭据（用于备用自动登录）")
        get_user_credentials()
    else:
        write_log("已加载保存的登录凭据")

    write_log("开始监控...")
    was_down = False  # 记录上次是否断网，避免重复打开页面

    while not stop_event.is_set():
        try:
            network_status = is_network_up()

            if not network_status:
                if not was_down:
                    trigger_count += 1
                    write_log("=" * 50)
                    write_log(f"🚨 检测到网络断开！触发次数: {trigger_count}")
                    write_log("=" * 50)

                    success = auto_login()
                    if success:
                        write_log("✅ 自动登录成功")
                        was_down = False  # 登录成功，重置状态
                    else:
                        write_log("❌ 自动登录失败，将在下次检测时重试")
                        was_down = True
                else:
                    write_log("📡 网络仍处于断开状态...")
            else:
                if was_down:
                    write_log("🌐 网络已恢复连通！")
                else:
                    write_log("✓ 网络状态正常")
                was_down = False

            stop_event.wait(10)  # 每10秒检查一次

        except KeyboardInterrupt:
            write_log("用户主动停止监控")
            stop_event.set()
        except Exception as e:
            write_log(f"监控过程出错: {e}")
            stop_event.wait(10)

def main():
    stop_event = threading.Event()
    monitor_thread = threading.Thread(target=monitor_loop, args=(stop_event,), daemon=True)
    monitor_thread.start()

    try:
        icon = create_tray_icon(stop_event)
        icon.run()
    except Exception as e:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 托盘图标启动失败: {e}")
        while not stop_event.is_set():
            time.sleep(1)

if __name__ == "__main__":
    main()
# check_availability.py
import os
import requests
import resend
import sys
import time # 引入 time 模块用于等待
from datetime import datetime

# --- 配置 ---
URLS_TO_CHECK = [
    "https://wx.dishu.de",
    "https://tb.dishu.de",
    "https://nps.dishu.de",
    "https://md.dishu.de",
    "https://tv.dishu.de",
    "https://llm.dishu.de",
]

RESEND_API_KEY = os.environ.get('RESEND_API_KEY')
SENDER_EMAIL = os.environ.get('SENDER_EMAIL')
RECEIVER_EMAIL = os.environ.get('RECEIVER_EMAIL')

if not RESEND_API_KEY:
    print("错误：环境变量 RESEND_API_KEY 未设置。")
    sys.exit(1)
if not SENDER_EMAIL:
    print("错误：环境变量 SENDER_EMAIL 未设置。")
    sys.exit(1)
if not RECEIVER_EMAIL:
    print("错误：环境变量 RECEIVER_EMAIL 未设置。")
    sys.exit(1)

resend.api_key = RESEND_API_KEY

# --- 检查逻辑 ---
down_sites = []
# 模拟常见的浏览器 User-Agent
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36'
    # 可以考虑添加更多常用头信息
    # 'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
    # 'Accept-Language': 'en-US,en;q=0.9',
}
timeout_seconds = 30 # 增加超时时间到 30 秒
max_retries = 2      # 最多尝试次数 (包括首次)
retry_delay = 5      # 重试前等待秒数

print(f"开始检查 {len(URLS_TO_CHECK)} 个网站 (超时: {timeout_seconds}s, 重试: {max_retries-1}次)...")

for url in URLS_TO_CHECK:
    success = False
    last_error = ""
    for attempt in range(max_retries):
        try:
            print(f"  尝试 #{attempt + 1} 检查: {url}")
            response = requests.get(url, headers=headers, timeout=timeout_seconds, allow_redirects=True)

            # --- 修改开始 ---
            # 检查是否是 wx.dishu.de 并且状态码是 403
            is_wx_dishu_de_special_case = (url == "https://wx.dishu.de" and response.status_code == 403)

            # 成功条件：状态码 < 400 或者 是 wx.dishu.de 的 403 特例
            if response.status_code < 400 or is_wx_dishu_de_special_case:
                status_info = f"状态码: {response.status_code}"
                if is_wx_dishu_de_special_case:
                    status_info += " (作为特例视为成功)"
                print(f"  检查成功: {url} - {status_info}")
                success = True
                break # 成功则跳出重试循环
            # --- 修改结束 ---
            else:
                last_error = f"状态码: {response.status_code}"
                print(f"  检查失败: {url} - {last_error}")

        except requests.exceptions.Timeout:
            last_error = f"请求超时 ({timeout_seconds}秒)"
            print(f"  检查失败: {url} - {last_error}")
        except requests.exceptions.RequestException as e:
            last_error = f"错误: {e}"
            print(f"  检查失败: {url} - {last_error}")

        # 如果还未成功且还有重试次数，则等待后重试
        if not success and attempt < max_retries - 1:
            print(f"  将在 {retry_delay} 秒后重试...")
            time.sleep(retry_delay)

    # 如果所有尝试都失败了，才记录为 down
    if not success:
        down_sites.append(f"{url} ({last_error})")

# --- 发送邮件通知 ---
# (邮件发送部分代码与之前相同，此处省略)
if down_sites:
    print(f"\n发现 {len(down_sites)} 个网站在多次尝试后仍无法访问，准备发送邮件通知...")
    subject = f"⚠️ 网站可用性警告 ({len(down_sites)} 个站点异常)"
    html_body = f"""
    <html>
    <body>
    <h2>网站可用性检查报告 ({datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')})</h2>
    <p>以下网站在多次尝试检查后仍无法访问或返回错误：</p>
    <ul>
    """
    for site in down_sites:
        html_body += f"<li>{site}</li>"
    html_body += """
    </ul>
    <p>请尽快检查！</p>
    </body>
    </html>
    """
    try:
        params = {
            "from": SENDER_EMAIL,
            "to": [RECEIVER_EMAIL],
            "subject": subject,
            "html": html_body,
        }
        email = resend.Emails.send(params)
        print(f"邮件已发送至 {RECEIVER_EMAIL}。 Resend ID: {email['id']}")
    except Exception as e:
        print(f"发送邮件失败: {e}")
        sys.exit(1)
else:
    print("\n所有网站检查通过，无需发送通知。")

sys.exit(0)


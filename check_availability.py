# check_availability.py
import os
import requests
import resend
import sys
from datetime import datetime

# --- 配置 ---
# 要检查的 URL 列表
URLS_TO_CHECK = [
    "https://wx.dishu.de",
    "https://tb.dishu.de",
    "https://nps.dishu.de",
    "https://alist.dishu.de",
]

# 从环境变量读取 Resend 配置
RESEND_API_KEY = os.environ.get('RESEND_API_KEY')
SENDER_EMAIL = os.environ.get('SENDER_EMAIL') # Resend 中验证过的发件邮箱
RECEIVER_EMAIL = os.environ.get('RECEIVER_EMAIL') # 你的收件邮箱

# 检查环境变量是否设置
if not RESEND_API_KEY:
    print("错误：环境变量 RESEND_API_KEY 未设置。")
    sys.exit(1)
if not SENDER_EMAIL:
    print("错误：环境变量 SENDER_EMAIL 未设置。")
    sys.exit(1)
if not RECEIVER_EMAIL:
    print("错误：环境变量 RECEIVER_EMAIL 未设置。")
    sys.exit(1)

# 设置 Resend API Key
resend.api_key = RESEND_API_KEY

# --- 检查逻辑 ---
down_sites = []
headers = {
    'User-Agent': 'GitHubActions-HealthCheck/1.0 (+https://github.com/your_username/your_repo)' # 设置一个友好的 User-Agent
}
timeout_seconds = 15 # 请求超时时间

print(f"开始检查 {len(URLS_TO_CHECK)} 个网站...")

for url in URLS_TO_CHECK:
    try:
        # 发送 GET 请求，允许重定向，设置超时
        response = requests.get(url, headers=headers, timeout=timeout_seconds, allow_redirects=True)
        # 检查状态码，4xx 和 5xx 都认为是失败
        if response.status_code >= 400:
            print(f"检查失败: {url} - 状态码: {response.status_code}")
            down_sites.append(f"{url} (状态码: {response.status_code})")
        else:
            print(f"检查成功: {url} - 状态码: {response.status_code}")
    except requests.exceptions.Timeout:
        print(f"检查失败: {url} - 请求超时 ({timeout_seconds}秒)")
        down_sites.append(f"{url} (请求超时)")
    except requests.exceptions.RequestException as e:
        # 其他请求相关的错误 (例如 DNS 解析失败, 连接被拒绝等)
        print(f"检查失败: {url} - 错误: {e}")
        down_sites.append(f"{url} (错误: {e})")

# --- 发送邮件通知 ---
if down_sites:
    print(f"\n发现 {len(down_sites)} 个网站无法访问，准备发送邮件通知...")
    subject = f"⚠️ 网站可用性警告 ({len(down_sites)} 个站点异常)"
    # 使用 HTML 格式化邮件内容
    html_body = f"""
    <html>
    <body>
    <h2>网站可用性检查报告 ({datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')})</h2>
    <p>以下网站在检查时无法访问或返回错误：</p>
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
        # 如果邮件发送失败，在 Action log 中输出错误，以便排查
        sys.exit(1) # 以失败状态退出 Action
else:
    print("\n所有网站检查通过，无需发送通知。")

# --- 脚本正常结束 ---
sys.exit(0)

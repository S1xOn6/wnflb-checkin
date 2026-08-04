#!/usr/bin/env python3
"""
福利吧论坛 (wnflb2023.com) 自动签到脚本
- 使用 Cookies 认证，无需浏览器
- 自动检测登录状态和签到状态
- 支持 PushPlus / Server酱 微信推送通知
- 早上9点签到 + 晚上10点复查，两次都自动补签
"""

import os
import re
import sys
import time
import requests
from datetime import datetime, timezone, timedelta

# ========== 配置 ==========
FORUM_URL = "https://www.wnflb2023.com/forum.php"
BASE_URL = "https://www.wnflb2023.com"
TIMEOUT = 30
MAX_RETRIES = 3
RETRY_DELAY = 5  # 秒

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Referer": "https://www.wnflb2023.com/forum.php",
}

# ========== 工具函数 ==========

def get_cst_time():
    """获取北京时间"""
    utc_now = datetime.now(timezone.utc)
    cst = utc_now + timedelta(hours=8)
    return cst.strftime("%Y-%m-%d %H:%M:%S")


def create_session(cookie_str):
    """创建带 Cookie 的请求会话"""
    session = requests.Session()
    session.headers.update(HEADERS)
    session.headers["Cookie"] = cookie_str
    return session


def fetch_with_retry(session, url, max_retries=MAX_RETRIES):
    """带重试的 HTTP GET 请求"""
    for attempt in range(1, max_retries + 1):
        try:
            resp = session.get(url, timeout=TIMEOUT)
            # 论坛使用 GBK 编码
            if resp.encoding and resp.encoding.lower() not in ("gbk", "gb2312"):
                resp.encoding = "gbk"
            return resp
        except requests.RequestException as e:
            print(f"  第 {attempt}/{max_retries} 次请求失败: {e}")
            if attempt < max_retries:
                print(f"  {RETRY_DELAY} 秒后重试...")
                time.sleep(RETRY_DELAY)
    return None


def check_logged_in(html):
    """检测是否已登录"""
    # 已登录页面包含退出登录链接
    if "mod=logging&action=logout" in html or "logging&action=logout" in html:
        return True
    # 未登录页面包含登录表单
    if 'name="username"' in html or "action=login" in html:
        return False
    # 默认假设已登录
    return True


def check_already_signed(html):
    """检测今日是否已签到
    fx_chk_menu=true 表示已签到，false 表示未签到
    """
    match = re.search(r"fx_chk_menu\s*=\s*(true|false)", html)
    if match:
        return match.group(1) == "true"
    # 备用检测：如果签到按钮显示为"已签到"状态
    if "已签到" in html and "签到成功" in html:
        return True
    return False


def extract_formhash(html):
    """从页面提取签到所需的 formhash
    URL 格式: plugin.php?id=fx_checkin:checkin&formhash=XXXX&YYYY
    其中 XXXX 是 Discuz formhash，YYYY 是 FX_FORMHASH
    """
    # 方法1：从 fx_checkin() 函数中提取完整 URL
    match = re.search(
        r"fx_checkin:checkin&formhash=([a-f0-9]+)&([a-f0-9]+)", html
    )
    if match:
        return match.group(1), match.group(2)

    # 方法2：从隐藏表单字段提取 formhash
    match = re.search(r'name="formhash"\s+value="([a-f0-9]+)"', html)
    if match:
        formhash = match.group(1)
        # 尝试提取 FX_FORMHASH
        fx_match = re.search(r'FX_FORMHASH\s*=\s*"([a-f0-9]+)"', html)
        fx_formhash = fx_match.group(1) if fx_match else ""
        return formhash, fx_formhash

    # 方法3：从 JavaScript 变量提取
    match = re.search(r"formhash\s*=\s*[\"']([a-f0-9]+)[\"']", html)
    if match:
        formhash = match.group(1)
        fx_match = re.search(r'FX_FORMHASH\s*=\s*"([a-f0-9]+)"', html)
        fx_formhash = fx_match.group(1) if fx_match else ""
        return formhash, fx_formhash

    return None, None


def do_checkin(session, formhash, fx_formhash):
    """执行签到请求"""
    url = (
        f"{BASE_URL}/plugin.php?id=fx_checkin:checkin"
        f"&formhash={formhash}&{fx_formhash}&inajax=1"
    )
    resp = fetch_with_retry(session, url)
    if resp is None:
        return None, "网络请求失败"
    return resp.text, None


def parse_result(response_text):
    """解析签到结果"""
    if response_text is None:
        return False, "无响应"

    # 签到成功
    if "签到成功" in response_text:
        # 尝试提取排名信息
        rank_match = re.search(r"第(\d+)个签到", response_text)
        if rank_match:
            return True, f"签到成功！今日第 {rank_match.group(1)} 个签到"
        return True, "签到成功！"

    # 已经签到过
    if "已经签到" in response_text or "已签到" in response_text:
        return True, "今日已签到（重复签到）"

    # 需要登录
    if "登录" in response_text or "请先登录" in response_text:
        return False, "Cookie 已过期，请重新获取"

    # 补签相关
    if "补签" in response_text and "成功" in response_text:
        return True, "补签成功"

    # 尝试提取 CDATA 中的内容
    cdata_match = re.search(r"<!\[CDATA\[(.*?)\]\]>", response_text, re.DOTALL)
    if cdata_match:
        content = cdata_match.group(1).strip()
        # 去除 HTML 标签
        clean = re.sub(r"<[^>]+>", " ", content).strip()
        clean = re.sub(r"\s+", " ", clean)
        if "签到成功" in clean or "已经签到" in clean:
            return True, clean[:200]
        return False, clean[:200] if clean else response_text[:200]

    # 未知响应
    clean = re.sub(r"<[^>]+>", " ", response_text).strip()
    clean = re.sub(r"\s+", " ", clean)
    return False, f"未知响应: {clean[:300]}"


def send_notification(title, content):
    """通过 PushPlus 或 Server酱 发送微信通知"""
    # PushPlus
    token = os.environ.get("PUSHPLUS_TOKEN", "")
    if token:
        try:
            resp = requests.post(
                "http://www.pushplus.plus/send",
                json={
                    "token": token,
                    "title": title,
                    "content": content,
                    "template": "txt",
                },
                timeout=10,
            )
            data = resp.json()
            print(f"  [PushPlus] {data.get('msg', 'unknown')}")
        except Exception as e:
            print(f"  [PushPlus] 发送失败: {e}")

    # Server酱
    key = os.environ.get("SERVERCHAN_KEY", "")
    if key:
        try:
            resp = requests.post(
                f"https://sctapi.ftqq.com/{key}.send",
                data={"title": title, "desp": content},
                timeout=10,
            )
            data = resp.json()
            print(f"  [Server酱] {data.get('message', 'unknown')}")
        except Exception as e:
            print(f"  [Server酱] 发送失败: {e}")

    # 如果都没有配置
    if not token and not key:
        print("  (未配置推送通知，结果仅在日志中查看)")


# ========== 主流程 ==========

def main():
    cookie_str = os.environ.get("FORUM_COOKIE", "")
    mode = os.environ.get("CHECKIN_MODE", "checkin")
    now = get_cst_time()

    print("=" * 50)
    print(f"  福利吧论坛自动签到")
    print(f"  模式: {'早起签到' if mode == 'checkin' else '晚间复查'}")
    print(f"  时间: {now}")
    print("=" * 50)
    print()

    if not cookie_str:
        print("[FATAL] 未设置 FORUM_COOKIE 环境变量")
        sys.exit(1)

    # Step 1: 创建会话并访问论坛
    print("[1/4] 正在访问论坛...")
    session = create_session(cookie_str)
    resp = fetch_with_retry(session, FORUM_URL)

    if resp is None:
        msg = "访问论坛失败（网络错误）"
        print(f"[FAIL] {msg}")
        send_notification(
            f"[签到失败] {mode}",
            f"时间: {now}\n模式: {mode}\n错误: {msg}",
        )
        sys.exit(1)

    html = resp.text

    # Step 2: 检查登录状态
    print("[2/4] 检查登录状态...")
    if not check_logged_in(html):
        msg = "Cookie 已过期，请重新获取 Cookie 并更新 GitHub Secrets"
        print(f"[FAIL] {msg}")
        send_notification(
            f"[签到失败] Cookie过期",
            f"时间: {now}\n模式: {mode}\n错误: {msg}",
        )
        sys.exit(1)
    print("  -> 登录状态正常")

    # Step 3: 检查签到状态
    print("[3/4] 检查签到状态...")
    already_signed = check_already_signed(html)
    if already_signed:
        msg = f"今日已签到，无需重复操作"
        print(f"[OK] {msg}")
        send_notification(
            f"[签到成功] {mode}",
            f"时间: {now}\n模式: {mode}\n状态: {msg}",
        )
        sys.exit(0)
    print("  -> 今日尚未签到")

    # Step 4: 执行签到
    print("[4/4] 提取 formhash 并执行签到...")
    formhash, fx_formhash = extract_formhash(html)

    if not formhash:
        msg = "无法从页面提取 formhash，页面结构可能已变化"
        print(f"[FAIL] {msg}")
        send_notification(
            f"[签到失败] {mode}",
            f"时间: {now}\n模式: {mode}\n错误: {msg}",
        )
        sys.exit(1)

    print(f"  -> formhash: {formhash}")
    print(f"  -> fx_formhash: {fx_formhash}")

    response_text, err = do_checkin(session, formhash, fx_formhash)
    if err:
        print(f"[FAIL] {err}")
        send_notification(
            f"[签到失败] {mode}",
            f"时间: {now}\n模式: {mode}\n错误: {err}",
        )
        sys.exit(1)

    success, message = parse_result(response_text)
    print(f"  -> 签到结果: {message}")

    if success:
        print("[OK] 签到成功！")
        send_notification(
            f"[签到成功] {mode}",
            f"时间: {now}\n模式: {mode}\n结果: {message}",
        )
    else:
        print(f"[FAIL] 签到失败: {message}")
        send_notification(
            f"[签到失败] {mode}",
            f"时间: {now}\n模式: {mode}\n结果: {message}",
        )
        sys.exit(1)


if __name__ == "__main__":
    main()

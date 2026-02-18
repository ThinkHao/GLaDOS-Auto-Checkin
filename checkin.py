import os
import json
import time
import random
import requests
from pypushdeer import PushDeer


CHECKIN_URL = "https://glados.cloud/api/user/checkin"
STATUS_URL = "https://glados.cloud/api/user/status"

HEADERS_BASE = {
    "origin": "https://glados.cloud",
    "referer": "https://glados.cloud/console/checkin",
    "user-agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "content-type": "application/json;charset=UTF-8",
}

PAYLOAD = {"token": "glados.cloud"}
TIMEOUT = 10


def push(sckey: str, title: str, text: str):
    if sckey:
        PushDeer(pushkey=sckey).send_text(title, desp=text)


def safe_json(resp):
    try:
        return resp.json()
    except Exception:
        return {}


def pick_value(*values):
    for v in values:
        if v is not None and v != "":
            return v
    return "-"




def extract_balance_from_checkin(data):
    if not isinstance(data, dict):
        return "-"

    records = data.get("list")
    if not isinstance(records, list) or not records:
        return "-"

    latest = records[0]
    if not isinstance(latest, dict):
        return "-"

    return pick_value(latest.get("balance"))


def main():
    sckey = os.getenv("SENDKEY", "")
    cookies_env = os.getenv("COOKIES", "")
    cookies = [c.strip() for c in cookies_env.split("&") if c.strip()]

    if not cookies:
        push(sckey, "GLaDOS 签到", "❌ 未检测到 COOKIES")
        return

    session = requests.Session()
    ok = fail = repeat = 0
    lines = []

    for idx, cookie in enumerate(cookies, 1):
        headers = dict(HEADERS_BASE)
        headers["cookie"] = cookie

        email = "unknown"
        points = "-"
        balance = "-"
        days = "-"

        try:
            r = session.post(
                CHECKIN_URL,
                headers=headers,
                data=json.dumps(PAYLOAD),
                timeout=TIMEOUT,
            )

            j = safe_json(r)
            msg = j.get("message", "")
            msg_lower = msg.lower()

            if "got" in msg_lower:
                ok += 1
                points = pick_value(j.get("points"))
                balance = pick_value(
                    j.get("balance"),
                    extract_balance_from_checkin(j),
                    j.get("points"),
                    balance,
                )
                status = "✅ 成功"
            elif "repeat" in msg_lower or "already" in msg_lower:
                repeat += 1
                points = pick_value(j.get("points"), "0")
                balance = pick_value(
                    j.get("balance"),
                    extract_balance_from_checkin(j),
                    j.get("points"),
                    balance,
                )
                status = "🔁 已签到"
            else:
                fail += 1
                status = "❌ 失败"

            # 状态接口（允许失败）
            s = session.get(STATUS_URL, headers=headers, timeout=TIMEOUT)
            sj = safe_json(s).get("data") or {}
            email = sj.get("email", email)
            if sj.get("leftDays") is not None:
                days = f"{int(float(sj['leftDays']))} 天"
            balance = pick_value(sj.get("balance"), sj.get("points"), balance)

        except Exception:
            fail += 1
            status = "❌ 异常"

        lines.append(
            f"{idx}. {email} | {status} | P:{points} | 累计:{balance} | 剩余:{days}"
        )
        time.sleep(random.uniform(1, 2))

    title = f"GLaDOS 签到完成 ✅{ok} ❌{fail} 🔁{repeat}"
    content = "\n".join(lines)

    print(content)
    push(sckey, title, content)


if __name__ == "__main__":
    main()

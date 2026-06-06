"""上大（SHU）校园网 Wi-Fi 门户的自动登录/注销脚本。

核心思路
========
门户登录接口需要一串 ``queryString``（包含 ``wlanuserip`` / ``mac`` / ``url`` 等
字段）。这串参数是门户在「未登录」时把你重定向到登录页时**动态下发**的加密会话
令牌，会过期。因此本脚本不再硬编码这些参数，而是在登录前主动访问一个外网探测地址，
让门户把我们重定向到登录页，再从重定向 URL 中提取当时有效的 ``queryString``。

凭证（账号 / 密码）不写在代码里，改为从同目录的 ``config.json`` 读取，或通过
``WIFI_USERNAME`` / ``WIFI_PASSWORD`` 环境变量提供，避免明文进入代码与 git 历史。
"""

import json
import os
import sys
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

# 静音 macOS 自带 Python(LibreSSL) 在 import requests 时触发的 urllib3 兼容性警告。
# 必须在 import requests 之前设置，否则拦不住导入期发出的警告。
warnings.filterwarnings("ignore", message=".*OpenSSL.*")

import requests
from requests import Response
from urllib.parse import urlparse


# 门户网关地址（各校区一致）。
PORTAL_HOST = "http://10.10.9.9"
LOGIN_API_URL = f"{PORTAL_HOST}/eportal/InterFace.do?method=login"
LOGOUT_API_URL = f"{PORTAL_HOST}/eportal/InterFace.do?method=logout"

# 用于探测「是否已登录 / 触发门户重定向」的纯 HTTP 地址。
# 这些地址在线时返回固定的成功响应；未登录时会被门户 302 到登录页。
PROBE_URLS: List[str] = [
    "http://captive.apple.com/hotspot-detect.html",
    "http://connect.rom.miui.com/generate_204",
    "http://www.msftconnecttest.com/redirect",
]

# 已登录时探测页应包含的成功标记。
ONLINE_MARKERS = ("Success", "<TITLE>Success</TITLE>")

# 配置文件路径（与脚本同目录）。
CONFIG_PATH = Path(__file__).resolve().parent / "config.json"

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36"
)


class PortalLoginError(RuntimeError):
    """门户登录接口返回非预期结果时抛出。"""


class AlreadyOnlineError(RuntimeError):
    """当前网络已处于在线状态、无需登录时抛出。"""


@dataclass(frozen=True)
class PortalCredentials:
    """封装门户所需的账号、密码等字段。"""

    username: str
    password: str
    service: str = "shu"
    operator_user_id: str = ""
    operator_password: str = ""
    password_encrypt: bool = False

    @classmethod
    def load(cls) -> "PortalCredentials":
        """按优先级读取凭证：环境变量 > config.json。

        都没有时抛出明确的错误，提示用户如何配置，绝不在代码里内置默认账号密码。
        """
        username = os.getenv("WIFI_USERNAME")
        password = os.getenv("WIFI_PASSWORD")
        service = os.getenv("WIFI_SERVICE", "shu")

        if not (username and password) and CONFIG_PATH.exists():
            try:
                data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError) as exc:
                raise PortalLoginError(f"无法读取配置文件 {CONFIG_PATH}: {exc}") from exc
            username = username or data.get("username")
            password = password or data.get("password")
            service = data.get("service", service)

        if not (username and password):
            raise PortalLoginError(
                "未找到账号密码。请在脚本同目录创建 config.json：\n"
                '  {"username": "你的学号", "password": "你的密码"}\n'
                "或设置环境变量 WIFI_USERNAME / WIFI_PASSWORD。"
            )

        return cls(username=username, password=password, service=service)


def _build_session() -> requests.Session:
    """构造带浏览器 UA 的会话，避免被门户判定为非正常访问。"""
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": DEFAULT_USER_AGENT,
            "Accept": "*/*",
            "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
        }
    )
    return session


def _looks_online(response: Response) -> bool:
    """判断探测响应是否表示「已经在线」。"""
    if response.status_code == 204:
        return True
    text = response.text or ""
    return any(marker in text for marker in ONLINE_MARKERS)


def fetch_query_string(session: requests.Session) -> str:
    """通过门户重定向获取当前有效的 queryString。

    依次访问探测地址：若直接拿到成功响应，说明已经在线 -> 抛 AlreadyOnlineError；
    若被门户重定向到登录页，则从最终 URL 中提取 queryString 返回。
    """
    last_error: Optional[Exception] = None
    for probe_url in PROBE_URLS:
        try:
            # allow_redirects=True 让 requests 跟随门户的 302，最终落在登录页。
            response = session.get(probe_url, timeout=10, allow_redirects=True)
        except requests.RequestException as exc:
            last_error = exc
            continue

        final_url = response.url
        parsed = urlparse(final_url)

        # 落点是门户登录页：从中提取 queryString。
        if "index.jsp" in parsed.path and parsed.query:
            return parsed.query

        # 未被重定向到门户、且响应像成功页 -> 已经在线。
        if PORTAL_HOST not in final_url and _looks_online(response):
            raise AlreadyOnlineError("当前网络已在线，无需登录。")

        # 有些门户把参数放在响应体的 meta refresh / JS 跳转里，尝试解析。
        extracted = _extract_query_from_body(response.text)
        if extracted:
            return extracted

    if last_error:
        raise PortalLoginError(f"无法连接门户以获取登录参数：{last_error}")
    raise PortalLoginError(
        "未能从门户获取登录参数。可能已在线，或门户重定向格式有变化。"
    )


def _extract_query_from_body(body: str) -> Optional[str]:
    """从 HTML 响应体中尝试提取 index.jsp?... 的 queryString（兜底）。"""
    if not body or "index.jsp" not in body:
        return None
    marker = "index.jsp?"
    start = body.find(marker)
    if start == -1:
        return None
    start += len(marker)
    # 截到第一个引号 / 空白 / 反斜杠为止。
    end = len(body)
    for ch in ("'", '"', " ", "\\", "<", ">"):
        pos = body.find(ch, start)
        if pos != -1:
            end = min(end, pos)
    query = body[start:end].strip()
    return query or None


def _build_login_payload(credentials: PortalCredentials, query_string: str) -> Dict[str, Any]:
    """根据账号信息和 queryString 拼装登录接口所需的表单数据。"""
    return {
        "userId": credentials.username,
        "password": credentials.password,
        "service": credentials.service,
        "queryString": query_string,
        "operatorPwd": credentials.operator_password,
        "operatorUserId": credentials.operator_user_id,
        "validcode": "",
        "passwordEncrypt": str(credentials.password_encrypt).lower(),
    }


def _interpret_response(response: Response) -> Dict[str, Any]:
    """尝试将响应解析为 JSON，若失败则保留原始文本内容。"""
    try:
        return response.json()
    except ValueError:
        text = response.text.strip()
        if text:
            return {"raw": text}
        raise PortalLoginError("门户返回了空响应。")


def _ensure_success(result: Dict[str, Any]) -> None:
    """检查门户返回值是否表示成功，否则抛出带原因的异常。"""
    if str(result.get("result", "")).lower() in ("true", "success"):
        return
    if str(result.get("success", "")).lower() == "true":
        return
    # 门户失败时通常把原因放在 message 字段。
    message = result.get("message") or result
    raise PortalLoginError(f"登录失败：{message}")


def do_login(credentials: Optional[PortalCredentials] = None) -> Dict[str, Any]:
    """执行登录：自动抓取实时参数 -> 提交登录接口 -> 校验结果。"""
    credentials = credentials or PortalCredentials.load()

    with _build_session() as session:
        query_string = fetch_query_string(session)
        payload = _build_login_payload(credentials, query_string)

        # 用抓到的登录页 URL 作为 Referer，更贴近真实浏览器行为。
        referer = f"{PORTAL_HOST}/eportal/index.jsp?{query_string}"
        response = session.post(
            LOGIN_API_URL,
            data=payload,
            timeout=10,
            headers={
                "Referer": referer,
                "Origin": PORTAL_HOST,
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            },
        )
        response.raise_for_status()

        result = _interpret_response(response)
        _ensure_success(result)
        return result


def do_logout(username: Optional[str] = None) -> Dict[str, Any]:
    """发起注销请求，默认使用配置中的账号。"""
    if not username:
        username = PortalCredentials.load().username

    with _build_session() as session:
        response = session.post(
            LOGOUT_API_URL,
            data={"userId": username},
            timeout=10,
            headers={
                "Origin": PORTAL_HOST,
                "Referer": f"{PORTAL_HOST}/eportal/index.jsp",
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            },
        )
        response.raise_for_status()
        return _interpret_response(response)


def main() -> None:
    """命令行入口：支持 login（默认）与 logout 两种动作。"""
    action = sys.argv[1] if len(sys.argv) > 1 else "login"

    try:
        if action == "logout":
            result = do_logout()
            print("注销结果：", result)
        else:
            result = do_login()
            print("登录成功：", result)
    except AlreadyOnlineError as exc:
        print(f"✅ {exc}")
        sys.exit(0)
    except PortalLoginError as exc:
        print(f"❌ {exc}")
        sys.exit(1)
    except requests.RequestException as exc:
        print(f"网络错误：{exc}")
        sys.exit(2)


if __name__ == "__main__":
    main()

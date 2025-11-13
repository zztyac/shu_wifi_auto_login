import os
import sys
from dataclasses import dataclass
from typing import Any, Dict, Optional

"""shu校园网 Wi-Fi 门户的自动登录/注销脚本。"""

import requests
from requests import Response
from urllib.parse import urlparse


LOGIN_PAGE_URL = (
    "http://10.10.9.9/eportal/index.jsp?"
    "wlanuserip=6eed71b47ee3f3e4fb8087e45f7959a9&"
    "wlanacname=6490c0a3a220e2c8&"
    "ssid=6ae3954b35cf28b790001cca1f2b1cfc&"
    "nasip=ee125bf0240ace65c22cc80cf4874cfc&"
    "mac=7ea6ac09a0f80274b0458781bb58fdcf&"
    "t=wireless-v2&"
    "url=2c0328164651e2b4f13b933ddf36628bea622dedcc302b30"
)

LOGIN_API_URL = "http://10.10.9.9/eportal/InterFace.do?method=login"
LOGOUT_API_URL = "http://10.10.9.9/eportal/InterFace.do?method=logout"


class PortalLoginError(RuntimeError):
    """Raised when the portal login endpoint returns an unexpected result."""


@dataclass(frozen=True)
class PortalCredentials:
    """封装门户所需的账号、密码等字段。"""

    username: str = ""
    password: str = ""
    service: str = "shu"
    operator_user_id: str = ""
    operator_password: str = ""
    password_encrypt: bool = False

    @classmethod
    def from_env(cls) -> "PortalCredentials":
        """优先从环境变量读取账号密码，避免硬编码在脚本中。"""
        username = os.getenv("WIFI_USERNAME")
        password = os.getenv("WIFI_PASSWORD")

        if username and password:
            return cls(username=username, password=password)

        return cls()


def _extract_query_string(login_url: str) -> str:
    """从登录页面 URL 中提取 queryString 字符串。"""
    parsed = urlparse(login_url)
    return parsed.query


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
        raise PortalLoginError("Empty response body from portal.")


def _ensure_success(result: Dict[str, Any]) -> None:
    """检查门户返回值是否表示成功，否则抛出异常。"""
    if "result" in result:
        if result["result"] is True or str(result["result"]).lower() == "success":
            return
    if "success" in result and str(result["success"]).lower() == "true":
        return
    raise PortalLoginError(f"Login failed: {result}")


def do_login(credentials: Optional[PortalCredentials] = None) -> Dict[str, Any]:
    """执行登录请求，成功则返回门户返回的 JSON 数据。"""
    credentials = credentials or PortalCredentials.from_env()
    query_string = _extract_query_string(LOGIN_PAGE_URL)
    payload = _build_login_payload(credentials, query_string)

    with requests.Session() as session:
        # 设置模拟浏览器的 HTTP 头，避免被门户判定为非正常访问。
        session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36"
                ),
                "Referer": LOGIN_PAGE_URL,
                "Origin": "http://10.10.9.9",
                "Accept": "*/*",
                "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            }
        )

        response = session.post(LOGIN_API_URL, data=payload, timeout=10)
        response.raise_for_status()

        result = _interpret_response(response)
        _ensure_success(result)
        return result


def do_logout(username: Optional[str] = None) -> Dict[str, Any]:
    """发起注销请求，默认使用当前环境中的账号。"""
    if not username:
        credentials = PortalCredentials.from_env()
        username = credentials.username

    with requests.Session() as session:
        # 注销接口同样需要携带 Referer/Origin 等头字段。
        response = session.post(
            LOGOUT_API_URL,
            data={"userId": username},
            timeout=10,
            headers={
                "Origin": "http://10.10.9.9",
                "Referer": LOGIN_PAGE_URL,
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            },
        )
        response.raise_for_status()
        return _interpret_response(response)


def main() -> None:
    """命令行入口：执行登录并处理异常情况。"""
    try:
        result = do_login()
        print("Login success:", result)
    except PortalLoginError as exc:
        print(f"Login failed: {exc}")
        sys.exit(1)
    except requests.RequestException as exc:
        print(f"Network error: {exc}")
        sys.exit(2)


if __name__ == "__main__":
    main()


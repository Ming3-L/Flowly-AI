"""
从画布节点 ``config`` JSON 中剥离敏感字段，再写入 ``WorkflowGraphNode``。

仅做保守规则：键名命中子串则删除（不递归扫描字符串值内容）。
"""

from __future__ import annotations

import copy
from typing import Any

_SENSITIVE_SUBSTRINGS = (
    "api_key",
    "apikey",
    "secret",
    "token",
    "password",
    "credential",
    "authorization",
)


def strip_sensitive_config(obj: Any) -> Any:
    """返回深拷贝后的结构，去掉疑似密钥的键。"""
    if isinstance(obj, dict):
        out: dict[str, Any] = {}
        for k, v in obj.items():
            lk = str(k).lower()
            if any(s in lk for s in _SENSITIVE_SUBSTRINGS):
                continue
            out[k] = strip_sensitive_config(v)
        return out
    if isinstance(obj, list):
        return [strip_sensitive_config(i) for i in obj]
    return copy.deepcopy(obj)

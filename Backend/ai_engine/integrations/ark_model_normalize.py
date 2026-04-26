"""方舟生成类 model_id 展示名 / 旧种子名 → 控制台常用 id（供聊天、画布与 ark_generative 共用）。"""

from __future__ import annotations

_ALIASES: dict[str, str] = {
    "Doubao-Seed3D-2.0": "doubao-seed3d-2-0-260328",
    "doubao-seed3d-2.0": "doubao-seed3d-2-0-260328",
    "Doubao-Seed3D-1.0": "doubao-seed3d-1-0-250928",
    "doubao-seed3d-1.0": "doubao-seed3d-1-0-250928",
    "Hiitem3D-2.0": "Hitem3D-2.0",
    "Hyper3D-Gen2": "hyper3d-gen2-260112",
    "hyper3d-gen2": "hyper3d-gen2-260112",
    "Hitem3D-2.0": "hitem3d-2-0-251223",
    "hitem3d-2.0": "hitem3d-2-0-251223",
}


def normalize_ark_generation_model_id(model_id: str) -> str:
    mid = (model_id or "").strip()
    if not mid:
        return mid
    return _ALIASES.get(mid, mid)

"""图片描述生成 — 用视觉模型为图片生成 alt text。"""

import base64
import hashlib
from pathlib import Path
from typing import Optional

from ..config import settings
from ..llm import call_vision_with_config, get_llm_config
from ..storage import FileStore


async def caption_images(
    images: list[dict],
    file_store: FileStore,
    global_store: FileStore,
    media_dir: Path,
) -> list[dict]:
    """为图片列表生成描述。

    Args:
        images: 图片信息列表 [{filename, rel_path, sha256, ...}]
        file_store: 文件存储实例（用于缓存）

    Returns:
        带 caption 字段的图片列表
    """
    # 从环境变量或 settings.json 获取多模态模型配置
    multimodal_model = settings.MULTIMODAL_MODEL
    if not multimodal_model:
        stored = global_store.get_settings()
        multimodal_model = stored.get("multimodalModel", "")

    if not multimodal_model and not settings.MULTIMODAL_API_KEY:
        # 没有配置多模态模型，跳过
        for img in images:
            img["caption"] = ""
        return images

    results = []
    for img in images:
        # 检查缓存
        cached = file_store.get_image_caption(img["sha256"])
        if cached:
            img["caption"] = cached
        else:
            caption = await _generate_caption(img, multimodal_model, global_store, media_dir)
            img["caption"] = caption
            if caption:
                file_store.save_image_caption(img["sha256"], caption)
        results.append(img)

    return results


async def _generate_caption(
    image_info: dict,
    multimodal_model: str,
    global_store: FileStore,
    media_dir: Optional[Path] = None,
) -> str:
    """调用视觉模型生成单张图片描述。"""
    try:
        # 读取图片并 base64 编码
        if media_dir is None:
            return ""
        img_path = media_dir / image_info["filename"]
        if not img_path.exists():
            return ""

        img_bytes = img_path.read_bytes()
        b64 = base64.b64encode(img_bytes).decode("utf-8")

        ext = Path(image_info["filename"]).suffix.lower()
        media_type = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".webp": "image/webp",
        }.get(ext, "image/png")

        config = get_llm_config(global_store)
        if settings.MULTIMODAL_API_KEY:
            config["api_key"] = settings.MULTIMODAL_API_KEY
        if settings.MULTIMODAL_BASE_URL:
            config["base_url"] = settings.MULTIMODAL_BASE_URL
        config["model"] = multimodal_model or config["model"]
        return await call_vision_with_config(
            config,
            b64,
            media_type,
            "请用中文简要描述这张图片的内容，用于替代文字（alt text）。不超过100字。只输出描述，不要任何前缀或解释。",
        )

    except Exception as e:
        print(f"[image-caption] 描述生成失败: {e}")

    return ""

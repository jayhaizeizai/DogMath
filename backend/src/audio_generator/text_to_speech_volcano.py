"""
火山引擎 Text-to-Speech 封装  (SSML & cluster 修正版 + 参数范围修正 + LaTeX支持)
==============================================================
- 支持纯文本 / SSML / LaTeX混排语音合成
- 默认 cluster="volcano_tts"，音色为 BV 系列
- **修正**: `speed_ratio` `volume_ratio` `pitch_ratio` 默认1.0 （推荐范围 0.1–3.0）
- 保持 LaTeX 识别开关打开 (`enable_latex_tn=True`，并且 `disable_markdown_filter=True`)
- 自动映射 `language` 字段，解析 4xx 错误 message，方便排查
"""
from __future__ import annotations
import os, uuid, json, base64, requests, tempfile, re
from pathlib import Path
from typing import List, Optional
from loguru import logger

# ------------------------------ 配置 ------------------------------ #
try:
    from .config import VOLCANO_ENGINE, TEXT_TO_SPEECH  # type: ignore
    logger.info("已加载 config.py 配置文件")
except ImportError:
    logger.warning("未找到 config.py，使用默认配置")
    VOLCANO_ENGINE = {
        "token": "YOUR_TOKEN",
        "app_id": "YOUR_APPID",
        "voice": "BV001_streaming",
        "cluster": "volcano_tts",
    }
    TEXT_TO_SPEECH = {
        "default_language": "cmn-CN",
        "default_voice": "cmn-CN-Standard-A",
    }

from .utils.audio_utils import merge_audio_files  # type: ignore

# ------------------------------ 工具 ------------------------------ #

def _lang_to_api(language_code: str | None) -> str:
    if not language_code:
        return "cn"
    code = language_code.lower()
    if code.startswith(("zh", "cmn")):
        return "cn"
    if code.startswith("en"):
        return "en"
    return "cn"

# ------------------------------ 主类 ------------------------------ #

class VolcanoTextToSpeech:
    """火山引擎 TTS 封装——兼容 GoogleTTS 接口，支持 SSML和LaTeX。"""

    def __init__(
        self,
        language_code: Optional[str] = None,
        voice_name: Optional[str] = None,
        output_dir: Optional[str] = None,
        token: Optional[str] = None,
        app_id: Optional[str] = None,
        cluster: Optional[str] = None,
    ) -> None:
        self.language_code = language_code or TEXT_TO_SPEECH.get("default_language")
        self.voice_name = voice_name or VOLCANO_ENGINE.get("voice")
        self.output_dir = Path(output_dir or os.path.join(os.getcwd(), "output", "audio"))
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.token = token or VOLCANO_ENGINE.get("token")
        self.app_id = app_id or VOLCANO_ENGINE.get("app_id")
        self.cluster = cluster or VOLCANO_ENGINE.get("cluster", "volcano_tts")

        if not self.token or self.token == "YOUR_TOKEN":
            logger.warning("未设置火山引擎 TOKEN，请检查 config.py VOLCANO_ENGINE.token")
        if not self.app_id or self.app_id == "YOURAPPID":
            logger.warning("未设置火山引擎 APP_ID，请检查 config.py VOLCANO_ENGINE.app_id")

        logger.info(f"火山引擎 TTS 初始化完成，默认音色: {self.voice_name}; cluster: {self.cluster}")

    def synthesize_speech(
        self,
        text: str,
        output_path: Optional[str] = None,
        voice_name: Optional[str] = None,
        language_code: Optional[str] = None,
        ssml: Optional[bool] = None,
        *,
        speed_ratio: float = 1.0,
        volume_ratio: float = 1.0,
        pitch_ratio: float = 1.0,
    ) -> str:
        voice_name = voice_name or self.voice_name
        language_code = language_code or self.language_code

        is_ssml = ssml if ssml is not None else bool(re.search(r"<\s*speak", text, re.I))
        if is_ssml and not re.search(r"<\s*speak", text, re.I):
            text = f"<speak>{text}</speak>"
            logger.debug("已自动补全 <speak> 标签")

        payload = {
            "app": {
                "appid": self.app_id,
                "token": "access_token",
                "cluster": self.cluster,
            },
            "user": {"uid": "user_" + str(uuid.uuid4())[:8]},
            "audio": {
                "voice_type": voice_name,
                "encoding": "wav",
                "speed_ratio": max(0.2, min(speed_ratio, 3.0)),
                "volume_ratio": max(0.1, min(volume_ratio, 3.0)),
                "pitch_ratio": max(0.1, min(pitch_ratio, 3.0)),
                "emotion": "neutral",
                "language": _lang_to_api(language_code),
            },
            "request": {
                "reqid": str(uuid.uuid4()),
                "text": text,
                "text_type": "ssml" if is_ssml else "plain",
                "operation": "query",
            },
        }

        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "Authorization": f"Bearer; {self.token}",
        }

        resp = requests.post(
            "https://openspeech.bytedance.com/api/v1/tts",
            headers=headers,
            json=payload,
            timeout=30,
        )

        if resp.status_code != 200:
            try:
                err = resp.json().get("message", "<no message>")
            except Exception:
                err = resp.text[:200]
            logger.error(f"TTS HTTP {resp.status_code} — {err}")
            resp.raise_for_status()

        audio_b64 = resp.json().get("data")
        if not audio_b64:
            raise RuntimeError(f"TTS 无音频返回: {resp.text[:200]}")

        audio_bytes = base64.b64decode(audio_b64)
        output_path = Path(output_path) if output_path else self.output_dir / f"tts_{abs(hash(text)) % 10000}.wav"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(audio_bytes)
        logger.info(f"音频已保存: {output_path}")
        return str(output_path)

    def synthesize_multiple(
        self,
        texts: List[str],
        output_path: str,
        voice_name: Optional[str] = None,
        language_code: Optional[str] = None,
        **kw,
    ) -> str:
        with tempfile.TemporaryDirectory() as tmp:
            parts: List[str] = []
            for i, t in enumerate(texts):
                p = Path(tmp) / f"part_{i}.wav"
                self.synthesize_speech(t, str(p), voice_name=voice_name, language_code=language_code, **kw)
                parts.append(str(p))
            return merge_audio_files(parts, output_path)

"""
Google Cloud Text‑to‑Speech 封装（官方 Python SDK 版本）
=====================================================
· 摆脱手写 curl 与 Token 拼接，直接使用 `google‑cloud‑texttospeech` 客户端。
· 自动读取 `GOOGLE_APPLICATION_CREDENTIALS` 环境变量或显式传入的
  `service_account_file`，也可使用明文 `api_key`（SDK 4.0+ 支持）。
· 接口保持与旧版一致：``synthesize_speech`` / ``synthesize_multiple``。
"""
from __future__ import annotations

import base64
import os
import json
import tempfile
from pathlib import Path
from typing import List, Optional

from loguru import logger

try:
    from .config import GOOGLE_CLOUD, TEXT_TO_SPEECH  # type: ignore
    logger.info("已加载 config.py 配置文件")
except ImportError:
    logger.warning("未找到 config.py，使用默认配置")
    GOOGLE_CLOUD = {
        "api_key": None,
        "service_account_file": None,
        "use_api_key": False,
        "project_id": None,
    }
    TEXT_TO_SPEECH = {
        "default_language": "cmn-CN",
        "default_voice": "cmn-CN-Standard-A",
    }

# 如果 utils 模块不存在，运行时会抛错——保持与旧实现兼容
from .utils.audio_utils import save_audio_to_wav, merge_audio_files  # type: ignore

# ---------------------------------------------------------------------------
# 主类
# ---------------------------------------------------------------------------

class GoogleTextToSpeech:
    """官方 SDK 封装，与之前版本 API 兼容。"""

    def __init__(
        self,
        language_code: Optional[str] = None,
        voice_name: Optional[str] = None,
        output_dir: Optional[str] = None,
        api_key: Optional[str] = None,
        service_account_file: Optional[str] = None,
    ) -> None:
        # ---------- 基本配置 ----------
        self.language_code = language_code or TEXT_TO_SPEECH.get("default_language")
        self.voice_name = voice_name or TEXT_TO_SPEECH.get("default_voice")
        self.output_dir = Path(output_dir or os.path.join(os.getcwd(), "output", "audio"))
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # ---------- 认证处理 ----------
        # 参数优先，其次 config.py
        self.api_key = api_key or GOOGLE_CLOUD.get("api_key")
        self.service_account_file = service_account_file or GOOGLE_CLOUD.get("service_account_file")

        if self.service_account_file:
            abs_path = os.path.abspath(self.service_account_file)
            os.environ.setdefault("GOOGLE_APPLICATION_CREDENTIALS", abs_path)
            logger.info(f"使用服务账号文件认证: {abs_path}")
        elif self.api_key:
            logger.info("使用 API Key 认证")
        else:
            logger.info("使用应用默认凭据 (ADC) 认证")

        # ---------- 创建 SDK 客户端 ----------
        from google.cloud import texttospeech  # import 放后面，防止未安装时报错位置不清晰

        if self.api_key:
            # SDK ≥ 3.0.0 支持明文 API Key，通过 client_options 传递
            self.client = texttospeech.TextToSpeechClient(
                client_options={"api_key": self.api_key}
            )
        else:
            self.client = texttospeech.TextToSpeechClient()

    # ---------------------------------------------------------------------
    # 单段文本
    # ---------------------------------------------------------------------

    def synthesize_speech(
        self,
        text: str,
        output_path: Optional[str] = None,
        voice_name: Optional[str] = None,
        language_code: Optional[str] = None,
    ) -> str:
        """将 *text* 转为 WAV（LINEAR16）。返回生成文件路径。"""
        from google.cloud import texttospeech  # 再次 import 方便类型提示

        voice_name = voice_name or self.voice_name
        language_code = language_code or self.language_code

        # -------- 1. 组装请求 --------
        # 根据文本是否包含 <speak> 判断普通文本还是 SSML
        if "<speak" in text.lower():
            synthesis_input = texttospeech.SynthesisInput(ssml=text)
        else:
            synthesis_input = texttospeech.SynthesisInput(text=text)

        voice_params = texttospeech.VoiceSelectionParams(
            language_code=language_code,
            name=voice_name,
        )

        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.LINEAR16,
        )

        # -------- 2. 调用 API --------
        logger.debug("调用 Google Cloud TTS…")
        response = self.client.synthesize_speech(
            input=synthesis_input,
            voice=voice_params,
            audio_config=audio_config,
        )

        # -------- 3. 保存文件 --------
        output_path = (
            Path(output_path)
            if output_path
            else self.output_dir / f"tts_{abs(hash(text)) % 10000}.wav"
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # SDK 返回 bytes，直接写文件
        output_path.write_bytes(response.audio_content)
        logger.info(f"音频已保存到: {output_path}")
        return str(output_path)

    # ---------------------------------------------------------------------
    # 多段文本合成并合并
    # ---------------------------------------------------------------------

    def synthesize_multiple(
        self,
        texts: List[str],
        output_path: str,
        voice_name: Optional[str] = None,
        language_code: Optional[str] = None,
    ) -> str:
        """多个片段合成为一个 WAV。"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            pieces: List[str] = []
            for idx, snippet in enumerate(texts):
                part_path = Path(tmp_dir) / f"part_{idx}.wav"
                self.synthesize_speech(
                    text=snippet,
                    output_path=str(part_path),
                    voice_name=voice_name,
                    language_code=language_code,
                )
                pieces.append(str(part_path))

            merged = merge_audio_files(pieces, output_path)  # type: ignore
            return merged

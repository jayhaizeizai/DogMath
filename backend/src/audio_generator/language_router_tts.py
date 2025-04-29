"""
语言路由TTS
=========
根据文本语言自动选择合适的TTS引擎：
- 中文文本使用火山引擎
- 英文和其他文本使用Google TTS
提供与原始TTS类相同的接口，使调用者无需关心底层实现。
"""
from __future__ import annotations

import re
import os
import tempfile
from pathlib import Path
from typing import List, Optional, Dict, Any, Union

from loguru import logger

# 导入两种TTS引擎
from .text_to_speech_google import GoogleTextToSpeech
from .text_to_speech_volcano import VolcanoTextToSpeech

try:
    from .config import TEXT_TO_SPEECH  # type: ignore
except ImportError:
    TEXT_TO_SPEECH = {
        "default_language": "cmn-CN",
        "default_voice": "cmn-CN-Standard-A",
        "chinese_threshold": 0.5,  # 如果中文字符占比超过此阈值，则使用火山引擎
    }

# 使用默认配置或从配置文件加载
CHINESE_THRESHOLD = TEXT_TO_SPEECH.get("chinese_threshold", 0.5)

class LanguageRouterTTS:
    """语言路由TTS，自动选择合适的TTS引擎"""

    def __init__(
        self,
        output_dir: Optional[str] = None,
        google_tts_params: Optional[Dict[str, Any]] = None,
        volcano_tts_params: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        初始化语言路由TTS
        
        Args:
            output_dir: 输出目录
            google_tts_params: Google TTS参数
            volcano_tts_params: 火山引擎TTS参数
        """
        self.output_dir = Path(output_dir or os.path.join(os.getcwd(), "output", "audio"))
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化Google TTS
        self.google_tts_params = google_tts_params or {}
        self.google_tts = GoogleTextToSpeech(
            output_dir=str(self.output_dir),
            **self.google_tts_params
        )
        
        # 初始化火山引擎TTS
        self.volcano_tts_params = volcano_tts_params or {}
        self.volcano_tts = VolcanoTextToSpeech(
            output_dir=str(self.output_dir),
            **self.volcano_tts_params
        )
        
        logger.info("语言路由TTS初始化完成")
    
    def _is_chinese_text(self, text: str) -> bool:
        """
        判断文本是否主要为中文
        
        Args:
            text: 输入文本
            
        Returns:
            如果中文字符占比超过阈值，返回True，否则返回False
        """
        # 移除SSML标签
        if "<speak" in text.lower():
            clean_text = re.sub(r'<[^>]+>', '', text)
        else:
            clean_text = text
            
        # 计算中文字符数量
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', clean_text))
        total_chars = len(clean_text.strip())
        
        if total_chars == 0:
            return False
            
        chinese_ratio = chinese_chars / total_chars
        logger.debug(f"文本中文字符占比: {chinese_ratio:.2f}")
        
        return chinese_ratio >= CHINESE_THRESHOLD
    
    def _get_tts_engine(self, text: str) -> Union[GoogleTextToSpeech, VolcanoTextToSpeech]:
        """
        根据文本语言获取合适的TTS引擎
        
        Args:
            text: 输入文本
            
        Returns:
            适合处理该文本的TTS引擎
        """
        if self._is_chinese_text(text):
            logger.info("检测到中文文本，使用火山引擎TTS")
            return self.volcano_tts
        else:
            logger.info("检测到非中文文本，使用Google TTS")
            return self.google_tts
    
    def synthesize_speech(
        self,
        text: str,
        output_path: Optional[str] = None,
        voice_name: Optional[str] = None,
        language_code: Optional[str] = None,
    ) -> str:
        """
        将文本转换为语音
        
        Args:
            text: 输入文本
            output_path: 输出文件路径
            voice_name: 语音名称
            language_code: 语言代码
            
        Returns:
            生成的音频文件路径
        """
        # 获取合适的TTS引擎
        tts_engine = self._get_tts_engine(text)
        
        # 调用对应引擎的方法
        return tts_engine.synthesize_speech(
            text=text,
            output_path=output_path,
            voice_name=voice_name,
            language_code=language_code
        )
    
    def synthesize_multiple(
        self,
        texts: List[str],
        output_path: str,
        voice_name: Optional[str] = None,
        language_code: Optional[str] = None,
    ) -> str:
        """
        合成多段文本为一个音频文件
        
        Args:
            texts: 文本列表
            output_path: 输出文件路径
            voice_name: 语音名称
            language_code: 语言代码
            
        Returns:
            生成的音频文件路径
        """
        # 对每段文本分别处理
        with tempfile.TemporaryDirectory() as tmp_dir:
            pieces: List[str] = []
            
            for idx, text in enumerate(texts):
                # 为每段文本选择合适的TTS引擎
                tts_engine = self._get_tts_engine(text)
                
                # 生成临时音频文件
                part_path = Path(tmp_dir) / f"part_{idx}.wav"
                tts_engine.synthesize_speech(
                    text=text,
                    output_path=str(part_path),
                    voice_name=voice_name,
                    language_code=language_code
                )
                pieces.append(str(part_path))
            
            # 合并所有音频片段
            from .utils.audio_utils import merge_audio_files
            merged = merge_audio_files(pieces, output_path)
            return merged 
"""
新版 simple_example.py：专业化文本转音频脚本
=============================================
- 支持 --text_file 文件输入 或 --text 直接文本
- 自动识别 SSML
- 规范参数，清晰调用
- 日志友好
"""

import os
import sys
import argparse
from pathlib import Path
from loguru import logger

# 加载工程路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
from backend.src.audio_generator.language_router_tts import LanguageRouterTTS

# 配置日志
log_path = Path(__file__).parent.parent.parent.parent / "logs" / "audio_generator.log"
os.makedirs(log_path.parent, exist_ok=True)
logger.add(log_path, rotation="10 MB", retention="7 days", level="DEBUG", encoding="utf-8")

def main():
    parser = argparse.ArgumentParser(description="文本转语音生成器")
    parser.add_argument("--text_file", type=str, help="输入文本文件路径 (.txt)")
    parser.add_argument("--text", type=str, help="直接输入文本内容")
    parser.add_argument("--output", type=str, required=True, help="输出音频文件路径 (.wav)")
    parser.add_argument("--language_code", type=str, help="语言代码 (如 cmn-CN)")
    parser.add_argument("--voice_name", type=str, help="音色名称 (可选)")
    args = parser.parse_args()

    # 确保至少提供一种输入
    if not args.text and not args.text_file:
        logger.error("必须提供 --text 或 --text_file 参数之一")
        sys.exit(1)

    # 读取文本
    if args.text_file:
        try:
            text = Path(args.text_file).read_text(encoding="utf-8")
            logger.info(f"从文件 {args.text_file} 读取文本成功")
        except Exception as e:
            logger.error(f"读取文本文件失败: {e}")
            sys.exit(1)
    else:
        text = args.text
        logger.info("直接使用命令行输入文本")

    # 生成器初始化
    tts = LanguageRouterTTS()

    # 确保输出目录存在
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)

    # 调用生成
    try:
        logger.info(f"开始生成音频: 输出路径={args.output}")
        tts.synthesize_speech(
            text=text,
            output_path=args.output,
            language_code=args.language_code,
            voice_name=args.voice_name
        )
        logger.info("✅ 音频生成成功")
    except Exception as e:
        logger.error(f"音频生成失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

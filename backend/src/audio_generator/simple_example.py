"""
新版 simple_example.py：专业化文本转音频脚本
=============================================
- 支持 --text_file 文件输入 或 --text 直接文本
- 支持长文本自动分段处理并拼接
- 自动识别 SSML
- 规范参数，清晰调用
- 日志友好
"""

import os
import sys
import argparse
import tempfile
import subprocess
from pathlib import Path
from loguru import logger
import re
import uuid

# 加载工程路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
from backend.src.audio_generator.language_router_tts import LanguageRouterTTS

# 配置日志
log_path = Path(__file__).parent.parent.parent.parent / "logs" / "audio_generator.log"
os.makedirs(log_path.parent, exist_ok=True)
logger.add(log_path, rotation="10 MB", retention="7 days", level="DEBUG", encoding="utf-8")

# 分段的最大字符数（可根据实际需求调整）
MAX_SEGMENT_LENGTH = 300
# 分段点的正则表达式（在句号、问号、感叹号后分段）
SENTENCE_BREAK = re.compile(r'([。？！.?!])')

def split_text(text):
    """
    将长文本分段，尽量在自然语句结束处分段
    
    Args:
        text: 要分段的文本
        
    Returns:
        分段后的文本列表
    """
    # 如果文本较短，直接返回
    if len(text) <= MAX_SEGMENT_LENGTH:
        return [text]
    
    # 尝试在句子边界分段
    segments = []
    current_segment = ""
    
    # 在句号、问号、感叹号处添加标记
    marked_text = SENTENCE_BREAK.sub(r'\1<BREAK>', text)
    sentences = marked_text.split('<BREAK>')
    
    for sentence in sentences:
        if not sentence:
            continue
            
        # 如果当前分段加上新句子仍然在限制内
        if len(current_segment) + len(sentence) <= MAX_SEGMENT_LENGTH:
            current_segment += sentence
        else:
            # 如果当前分段不为空，添加到结果中
            if current_segment:
                segments.append(current_segment)
            
            # 如果单个句子超过长度限制，强制分段
            if len(sentence) > MAX_SEGMENT_LENGTH:
                # 简单地按长度切分
                for i in range(0, len(sentence), MAX_SEGMENT_LENGTH):
                    segments.append(sentence[i:i+MAX_SEGMENT_LENGTH])
            else:
                current_segment = sentence
    
    # 添加最后一个分段
    if current_segment:
        segments.append(current_segment)
    
    logger.info(f"文本被分为 {len(segments)} 个片段")
    return segments

def run_command(cmd):
    """
    执行命令行命令
    
    Args:
        cmd: 命令列表
        
    Returns:
        执行是否成功
    """
    try:
        logger.debug(f"执行命令: {' '.join(cmd)}")
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        stdout, stderr = process.communicate()
        
        if process.returncode != 0:
            logger.error(f"命令执行失败: {stderr}")
            return False
            
        return True
    except Exception as e:
        logger.error(f"命令执行出错: {e}")
        return False

def concat_audio_files(audio_files, output_path):
    """
    合并多个音频文件
    
    Args:
        audio_files: 音频文件路径列表
        output_path: 输出文件路径
        
    Returns:
        合并是否成功
    """
    try:
        # 创建临时文件列表
        with tempfile.NamedTemporaryFile('w', suffix='.txt', delete=False) as f:
            concat_list = f.name
            for audio_file in audio_files:
                f.write(f"file '{os.path.abspath(audio_file)}'\n")
        
        # 使用FFmpeg合并
        cmd = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", concat_list,
            "-c", "copy",
            output_path
        ]
        
        success = run_command(cmd)
        
        # 删除临时文件
        os.unlink(concat_list)
        
        return success
    except Exception as e:
        logger.error(f"合并音频失败: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="文本转语音生成器")
    parser.add_argument("--text_file", type=str, help="输入文本文件路径 (.txt)")
    parser.add_argument("--text", type=str, help="直接输入文本内容")
    parser.add_argument("--output", type=str, required=True, help="输出音频文件路径 (.wav)")
    parser.add_argument("--language_code", type=str, help="语言代码 (如 cmn-CN)")
    parser.add_argument("--voice_name", type=str, help="音色名称 (可选)")
    parser.add_argument("--no_split", action="store_true", help="禁用长文本分段处理")
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
    output_dir = Path(args.output).parent
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 检查文本长度，决定是否需要分段
    if len(text) > MAX_SEGMENT_LENGTH and not args.no_split:
        logger.info(f"文本长度为 {len(text)} 字符，将进行分段处理")
        text_segments = split_text(text)
        
        # 创建临时目录存放分段音频
        temp_dir = output_dir / f"temp_audio_{uuid.uuid4().hex[:8]}"
        temp_dir.mkdir(exist_ok=True)
        
        try:
            # 为每个分段生成音频
            segment_files = []
            for i, segment in enumerate(text_segments):
                segment_path = temp_dir / f"segment_{i:03d}.wav"
                logger.info(f"处理第 {i+1}/{len(text_segments)} 段 (长度: {len(segment)})")
                
                try:
                    tts.synthesize_speech(
                        text=segment,
                        output_path=str(segment_path),
                        language_code=args.language_code,
                        voice_name=args.voice_name
                    )
                    segment_files.append(str(segment_path))
                except Exception as e:
                    logger.error(f"片段 {i+1} 生成失败: {e}")
            
            # 合并所有分段音频
            if segment_files:
                logger.info(f"合并 {len(segment_files)} 个音频片段")
                if concat_audio_files(segment_files, args.output):
                    logger.info("✅ 合并音频成功")
                else:
                    logger.error("合并音频失败")
                    sys.exit(1)
            else:
                logger.error("没有生成任何音频片段")
                sys.exit(1)
        finally:
            # 清理临时文件
            for file in temp_dir.glob("*.wav"):
                try:
                    file.unlink()
                except:
                    pass
            try:
                temp_dir.rmdir()
            except:
                pass
    else:
        # 单段处理
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

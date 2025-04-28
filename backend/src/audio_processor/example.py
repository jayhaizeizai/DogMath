"""
示例脚本：演示如何使用 GoogleTextToSpeech 类
"""
import os
import sys
import json
from pathlib import Path
from loguru import logger

# 添加项目根目录到系统路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

# 使用绝对导入
from backend.src.audio_processor import GoogleTextToSpeech

# 配置loguru日志
log_path = Path(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))) / "logs" / "audio_processor.log"
logger.add(log_path, rotation="10 MB", retention="1 week", level="DEBUG", encoding="utf-8")

def generate_audio_from_json(json_path: str, output_path: str):
    """
    从JSON文件生成音频文件
    
    Args:
        json_path: 输入JSON文件路径
        output_path: 输出音频文件路径
    """
    try:
        # 读取JSON数据
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        # 获取音频配置数据
        audio_data = data.get('audio', {})
        narration = audio_data.get('narration', [])
        
        if not narration:
            logger.warning("没有找到旁白数据")
            return
            
        # 创建TTS实例
        tts = GoogleTextToSpeech(
            language_code="zh-CN",
            voice_name="zh-CN-Standard-A"
        )
        
        # 提取文本内容
        texts = []
        for item in narration:
            # 优先使用SSML，如果没有则使用普通文本
            if 'ssml' in item and item['ssml']:
                texts.append(item['ssml'])
            elif 'text' in item and item['text']:
                texts.append(item['text'])
                
        # 确保有文本内容
        if not texts:
            logger.warning("没有找到可用的文本内容")
            return
            
        # 生成音频
        logger.info(f"开始生成音频，共{len(texts)}个片段")
        
        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        if len(texts) == 1:
            # 单个文本片段
            audio_file = tts.synthesize_speech(
                text=texts[0],
                output_path=output_path
            )
        else:
            # 多个文本片段
            audio_file = tts.synthesize_multiple(
                texts=texts,
                output_path=output_path
            )
            
        logger.info(f"音频生成完成：{audio_file}")
        
    except Exception as e:
        logger.error(f"音频生成失败: {str(e)}")
        raise

def generate_simple_audio(text: str, output_path: str, language_code: str = "en-US", voice_name: str = "en-US-Chirp3-HD-Leda"):
    """
    生成简单的音频文件
    
    Args:
        text: 文本内容
        output_path: 输出文件路径
        language_code: 语言代码
        voice_name: 声音名称
    """
    try:
        # 创建TTS实例
        tts = GoogleTextToSpeech(
            language_code=language_code,
            voice_name=voice_name
        )
        
        # 生成音频
        audio_file = tts.synthesize_speech(
            text=text,
            output_path=output_path
        )
        
        logger.info(f"音频生成完成：{audio_file}")
        return audio_file
        
    except Exception as e:
        logger.error(f"音频生成失败: {str(e)}")
        raise

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("用法1: python example.py <输入JSON文件路径> <输出音频文件路径>")
        print("用法2: python example.py --text \"要转换的文本\" <输出音频文件路径> [语言代码] [声音名称]")
        sys.exit(1)
    
    if sys.argv[1] == "--text":
        if len(sys.argv) < 4:
            print("用法2: python example.py --text \"要转换的文本\" <输出音频文件路径> [语言代码] [声音名称]")
            sys.exit(1)
            
        text = sys.argv[2]
        output_path = sys.argv[3]
        
        # 可选参数
        language_code = sys.argv[4] if len(sys.argv) > 4 else "en-US"
        voice_name = sys.argv[5] if len(sys.argv) > 5 else "en-US-Chirp3-HD-Leda"
        
        # 确保输出目录存在
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        # 生成音频
        generate_simple_audio(text, output_path, language_code, voice_name)
    else:
        json_path = sys.argv[1]
        output_path = sys.argv[2]
        
        # 确保输出目录存在
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        # 从JSON生成音频
        generate_audio_from_json(json_path, output_path) 
"""
示例脚本：演示如何使用 LanguageRouterTTS 类按分段生成音频
支持自动根据文本语言选择合适的TTS引擎：
- 中文文本使用火山引擎
- 英文和其他文本使用Google TTS
"""
import os
import sys
import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from loguru import logger

# 添加项目根目录到系统路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

# 使用绝对导入
from backend.src.audio_generator.language_router_tts import LanguageRouterTTS

# 尝试导入配置文件
try:
    from backend.src.audio_generator.config import TEXT_TO_SPEECH
except ImportError:
    TEXT_TO_SPEECH = {
        "default_language": "zh-CN",
        "default_voice": "zh-CN-Standard-A",
        "chinese_threshold": 0.5
    }

# 配置loguru日志
log_path = Path(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))) / "logs" / "audio_generator.log"
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
            
        # 创建TTS实例，会自动根据文本语言选择合适的TTS引擎
        tts = LanguageRouterTTS()
        
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

def generate_simple_audio(text: str, output_path: str, language_code: Optional[str] = None, voice_name: Optional[str] = None):
    """
    生成简单的音频文件
    
    Args:
        text: 文本内容
        output_path: 输出文件路径
        language_code: 语言代码，如果为None则使用配置文件中的默认值
        voice_name: 声音名称，如果为None则使用配置文件中的默认值
    """
    try:
        # 创建TTS实例，会自动根据文本语言选择合适的TTS引擎
        tts = LanguageRouterTTS()
        
        # 生成音频
        audio_file = tts.synthesize_speech(
            text=text,
            output_path=output_path,
            language_code=language_code,
            voice_name=voice_name
        )
        
        logger.info(f"音频生成完成：{audio_file}")
        return audio_file
        
    except Exception as e:
        logger.error(f"音频生成失败: {str(e)}")
        raise

def generate_segmented_audio(json_path: str, output_dir: str) -> List[Dict[str, Any]]:
    """
    从JSON文件生成分段音频文件
    
    Args:
        json_path: 输入JSON文件路径
        output_dir: 输出目录路径
    
    Returns:
        包含所有音频片段信息的元数据列表
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
            return []
            
        # 创建TTS实例，会自动根据文本语言选择合适的TTS引擎
        tts = LanguageRouterTTS()
        
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        # 生成音频片段
        audio_segments = []
        for idx, segment in enumerate(narration):
            # 获取文本内容（优先使用SSML）
            text = segment.get('ssml') if segment.get('ssml') else segment.get('text', '')
            if not text:
                logger.warning(f"片段{idx}没有文本内容，跳过")
                continue
                
            # 构建输出文件路径
            timestamp = int(segment.get('start_time', 0) * 1000)  # 转换为毫秒
            output_path = os.path.join(output_dir, f"audio_{timestamp}_{idx}.wav")
            
            # 生成音频
            logger.info(f"正在生成音频片段 {idx+1}/{len(narration)}")
            
            # 应用语音配置
            voice_config = segment.get('voice_config', {})
            voice_name = voice_config.get('speaker')
            
            # 生成音频文件
            audio_file = tts.synthesize_speech(
                text=text,
                output_path=output_path,
                voice_name=voice_name
            )
            
            # 添加到元数据
            duration = segment.get('end_time', 0) - segment.get('start_time', 0)
            audio_segments.append({
                'id': idx,
                'timestamp': timestamp,
                'path': audio_file,
                'duration': duration,
                'start_time': segment.get('start_time', 0),
                'end_time': segment.get('end_time', 0)
            })
            
        logger.info(f"音频生成完成：共{len(audio_segments)}个片段")
        return audio_segments
        
    except Exception as e:
        logger.error(f"音频生成失败: {str(e)}")
        raise

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("用法1: python example.py <输入JSON文件路径> <输出音频文件路径>")
        print("用法2: python example.py --text \"要转换的文本\" <输出音频文件路径> [语言代码] [声音名称]")
        print("用法3: python example.py --segmented <输入JSON文件路径> <输出目录路径>")
        sys.exit(1)
    
    if sys.argv[1] == "--text":
        if len(sys.argv) < 4:
            print("用法2: python example.py --text \"要转换的文本\" <输出音频文件路径> [语言代码] [声音名称]")
            sys.exit(1)
            
        text = sys.argv[2]
        output_path = sys.argv[3]
        
        # 可选参数
        language_code = sys.argv[4] if len(sys.argv) > 4 else None
        voice_name = sys.argv[5] if len(sys.argv) > 5 else None
        
        # 确保输出目录存在
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        # 生成音频
        generate_simple_audio(text, output_path, language_code, voice_name)
    elif sys.argv[1] == "--segmented":
        if len(sys.argv) < 4:
            print("用法3: python example.py --segmented <输入JSON文件路径> <输出目录路径>")
            sys.exit(1)
            
        json_path = sys.argv[2]
        output_dir = sys.argv[3]
        
        # 确保输出目录存在
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        # 从JSON生成分段音频
        audio_segments = generate_segmented_audio(json_path, output_dir)
        
        # 输出元数据
        metadata_path = os.path.join(output_dir, "audio_metadata.json")
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(audio_segments, f, ensure_ascii=False, indent=2)
        
        print(f"分段音频生成完成，元数据保存到：{metadata_path}")
    else:
        json_path = sys.argv[1]
        output_path = sys.argv[2]
        
        # 确保输出目录存在
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        # 从JSON生成音频
        generate_audio_from_json(json_path, output_path) 
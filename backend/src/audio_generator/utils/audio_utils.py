"""
音频处理工具函数
"""
import os
import json
import wave
import base64
import numpy as np
from pathlib import Path
from typing import Optional, Union, Tuple, Dict, Any

def save_audio_to_wav(audio_content_base64: str, output_path: str) -> str:
    """
    将base64编码的音频内容保存为WAV文件
    
    Args:
        audio_content_base64: base64编码的音频数据
        output_path: 输出文件路径
    
    Returns:
        保存的文件路径
    """
    # 确保输出目录存在
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # 解码base64数据
    audio_data = base64.b64decode(audio_content_base64)
    
    # 保存为WAV文件
    with open(output_path, "wb") as f:
        f.write(audio_data)
    
    return output_path

def merge_audio_files(audio_files: list, output_path: str) -> str:
    """
    合并多个WAV音频文件
    
    Args:
        audio_files: WAV文件路径列表
        output_path: 输出文件路径
    
    Returns:
        合并后的文件路径
    """
    # 确保输出目录存在
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # 读取所有音频数据
    data = []
    sample_rate = None
    sample_width = None
    for file in audio_files:
        with wave.open(file, 'rb') as wav:
            if sample_rate is None:
                sample_rate = wav.getframerate()
            if sample_width is None:
                sample_width = wav.getsampwidth()
            
            # 读取音频数据
            file_data = wav.readframes(wav.getnframes())
            data.append(file_data)
    
    # 创建输出文件
    with wave.open(output_path, 'wb') as output:
        output.setnchannels(1)  # 单声道
        output.setsampwidth(sample_width)
        output.setframerate(sample_rate)
        
        # 写入所有数据
        for audio_data in data:
            output.writeframes(audio_data)
    
    return output_path 
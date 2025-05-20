import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Union

logger = logging.getLogger(__name__)

def load_json_file(file_path: str) -> Dict:
    """
    加载JSON文件。
    
    Args:
        file_path: JSON文件的路径
        
    Returns:
        加载的JSON内容
        
    Raises:
        FileNotFoundError: 如果文件不存在
        json.JSONDecodeError: 如果JSON格式无效
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        logger.debug(f"成功加载JSON文件: {file_path}")
        return data
    except FileNotFoundError:
        logger.error(f"文件不存在: {file_path}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"JSON格式无效: {file_path}, 错误: {e}")
        raise
    except Exception as e:
        logger.error(f"加载JSON文件时发生错误: {e}")
        raise

def save_json_file(data: Dict, file_path: str, indent: int = 2) -> None:
    """
    保存JSON文件。
    
    Args:
        data: 要保存的数据
        file_path: 目标文件路径
        indent: JSON缩进格式（默认为2）
    """
    try:
        # 确保目标目录存在
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=indent)
        
        logger.debug(f"成功保存JSON文件: {file_path}")
    except Exception as e:
        logger.error(f"保存JSON文件时发生错误: {e}")
        raise

def calculate_total_audio_duration(audio_metadata: List[Dict]) -> float:
    """
    计算音频段的总持续时间。
    
    Args:
        audio_metadata: 音频元数据列表
        
    Returns:
        总音频持续时间（秒）
    """
    if not audio_metadata:
        return 0.0
    
    # 如果有end_time字段，使用最后一个片段的end_time
    if "end_time" in audio_metadata[-1]:
        return audio_metadata[-1]["end_time"]
    
    # 否则，计算所有片段的持续时间总和
    total_duration = 0.0
    for segment in audio_metadata:
        if "duration" in segment:
            total_duration += segment["duration"]
    
    return total_duration

def calculate_total_blackboard_duration(blackboard_data: Dict) -> float:
    """
    计算黑板动画的总持续时间。
    
    Args:
        blackboard_data: 黑板数据
        
    Returns:
        总黑板动画持续时间（秒）
    """
    if not blackboard_data or "steps" not in blackboard_data:
        return 0.0
    
    # 计算所有步骤的持续时间总和
    total_duration = 0.0
    for step in blackboard_data["steps"]:
        if "duration" in step:
            total_duration += step["duration"]
    
    return total_duration

def create_timing_mapping(audio_narration: List[Dict], blackboard_steps: List[Dict]) -> Dict:
    """
    创建音频段落与黑板步骤之间的时间映射。
    
    Args:
        audio_narration: 音频旁白列表
        blackboard_steps: 黑板步骤列表
        
    Returns:
        音频段落到黑板步骤的映射
    """
    # 构建步骤时间范围
    step_time_ranges = []
    current_time = 0
    
    for step in blackboard_steps:
        step_id = step["step_id"]
        duration = step["duration"]
        
        step_time_ranges.append({
            "step_id": step_id,
            "start_time": current_time,
            "end_time": current_time + duration
        })
        
        current_time += duration
    
    # 为每个音频段落分配步骤
    narration_to_step = {}
    
    for narr_idx, narration in enumerate(audio_narration):
        narr_start = narration["start_time"]
        narr_end = narration["end_time"]
        
        # 找出与当前音频段落重叠的步骤
        matching_steps = []
        
        for step_info in step_time_ranges:
            step_id = step_info["step_id"]
            step_start = step_info["start_time"]
            step_end = step_info["end_time"]
            
            # 检查重叠情况
            if narr_start < step_end and narr_end > step_start:
                # 计算重叠程度
                overlap_start = max(narr_start, step_start)
                overlap_end = min(narr_end, step_end)
                overlap_duration = overlap_end - overlap_start
                
                matching_steps.append({
                    "step_id": step_id,
                    "overlap_duration": overlap_duration,
                    "overlap_percent": overlap_duration / (narr_end - narr_start) * 100
                })
        
        # 按重叠程度排序，选择重叠最多的步骤
        if matching_steps:
            matching_steps.sort(key=lambda x: x["overlap_duration"], reverse=True)
            primary_step = matching_steps[0]["step_id"]
        else:
            # 如果没有重叠，选择最近的步骤
            closest_step = None
            min_distance = float('inf')
            
            for step_info in step_time_ranges:
                step_id = step_info["step_id"]
                step_mid = (step_info["start_time"] + step_info["end_time"]) / 2
                narr_mid = (narr_start + narr_end) / 2
                
                distance = abs(step_mid - narr_mid)
                if distance < min_distance:
                    min_distance = distance
                    closest_step = step_id
            
            primary_step = closest_step
        
        narration_to_step[narr_idx] = {
            "step_id": primary_step,
            "matching_steps": matching_steps
        }
    
    return narration_to_step

def get_timestamp_mapping(content_json: Dict) -> Dict[int, Dict[str, float]]:
    """
    获取内容JSON中的时间戳映射。
    
    Args:
        content_json: 内容JSON数据
        
    Returns:
        Dict: 步骤ID到时间戳范围的映射
    """
    mapping = {}
    current_time = 0
    
    for step in content_json["blackboard"]["steps"]:
        step_id = step["step_id"]
        duration = step["duration"]
        
        mapping[step_id] = {
            "start_time": current_time,
            "end_time": current_time + duration,
            "duration": duration
        }
        
        current_time += duration
    
    return mapping

def format_time(seconds: float) -> str:
    """
    将秒数格式化为人类可读的时间格式。
    
    Args:
        seconds: 时间（秒）
        
    Returns:
        格式化的时间字符串（MM:SS.mm）
    """
    minutes = int(seconds // 60)
    remaining_seconds = seconds % 60
    return f"{minutes:02d}:{remaining_seconds:05.2f}" 
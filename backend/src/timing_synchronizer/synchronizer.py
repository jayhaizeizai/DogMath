import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path

from .utils import load_json_file, save_json_file

logger = logging.getLogger(__name__)

class TimingSynchronizer:
    """
    用于同步音频时间与黑板动画时间的类。
    读取实际音频元数据并调整内容JSON文件中的时间，确保音频和视觉元素同步。
    """
    
    def __init__(self, audio_metadata_path: str, content_json_path: str):
        """
        初始化同步器。
        
        Args:
            audio_metadata_path: 音频元数据JSON文件的路径
            content_json_path: 内容JSON文件的路径
        """
        self.audio_metadata_path = audio_metadata_path
        self.content_json_path = content_json_path
        self.audio_metadata = None
        self.content_json = None
    
    def load_data(self) -> None:
        """加载音频元数据和内容JSON文件"""
        try:
            self.audio_metadata = load_json_file(self.audio_metadata_path)
            self.content_json = load_json_file(self.content_json_path)
            logger.info(f"成功加载音频元数据和内容JSON文件")
        except Exception as e:
            logger.error(f"加载文件失败: {e}")
            raise
    
    def get_original_durations(self) -> Dict[int, int]:
        """获取原始黑板步骤持续时间"""
        if not self.content_json:
            self.load_data()
        
        original_durations = {}
        for step in self.content_json["blackboard"]["steps"]:
            original_durations[step["step_id"]] = step["duration"]
        
        return original_durations
    
    def create_step_audio_mapping(self) -> Dict[int, List[Dict]]:
        """
        创建黑板步骤和音频段落之间的映射关系。
        基于实际音频元数据来确定每个步骤对应的音频段落。
        """
        if not self.content_json or not self.audio_metadata:
            self.load_data()
        
        # 从内容JSON获取步骤的原始时间信息作为参考
        original_step_times = []
        current_time = 0
        for step in self.content_json["blackboard"]["steps"]:
            step_id = step["step_id"]
            duration = step["duration"]
            original_step_times.append({
                "step_id": step_id,
                "start_time": current_time,
                "end_time": current_time + duration
            })
            current_time += duration
        
        # 为每个步骤关联对应的音频段落
        step_to_audio = {}
        for step_info in original_step_times:
            step_to_audio[step_info["step_id"]] = []
        
        # 将每个音频段落映射到相应的步骤
        for segment in self.audio_metadata:
            # 根据音频段落的开始时间找到对应的步骤
            step_id = self.map_time_to_step_id(segment["start_time"])
            if step_id is not None:
                step_to_audio[step_id].append(segment)
        
        return step_to_audio
    
    def map_time_to_step_id(self, time_point: float) -> Optional[int]:
        """
        将时间点映射到对应的黑板步骤ID。
        
        Args:
            time_point: 要映射的时间点（秒）
            
        Returns:
            对应的步骤ID，如果没有匹配则返回None
        """
        if not self.content_json:
            self.load_data()
            
        current_time = 0
        for step in self.content_json["blackboard"]["steps"]:
            step_id = step["step_id"]
            duration = step["duration"]
            
            if current_time <= time_point < (current_time + duration):
                return step_id
                
            current_time += duration
            
        return None
    
    def get_actual_audio_durations(self) -> Dict[int, float]:
        """
        计算每个黑板步骤对应的实际音频持续时间。
        
        Returns:
            Dict: 步骤ID到实际音频持续时间的映射
        """
        if not self.audio_metadata:
            self.load_data()
            
        segments = {}
        for segment in self.audio_metadata:
            start_time = segment["start_time"]
            end_time = segment["end_time"]
            
            # 将音频段落映射到对应的黑板步骤
            step_id = self.map_time_to_step_id(start_time)
            if step_id not in segments:
                segments[step_id] = []
                
            segments[step_id].append((start_time, end_time))
        
        # 计算每个步骤的实际时长
        step_durations = {}
        for step_id, time_ranges in segments.items():
            if step_id is None:  # 跳过无法映射的段落
                continue
                
            total_duration = sum(end - start for start, end in time_ranges)
            step_durations[step_id] = total_duration
        
        return step_durations
    
    def calculate_actual_durations(self, step_to_audio_mapping: Dict[int, List[Dict]]) -> Dict[int, int]:
        """
        根据音频与步骤的映射计算每个步骤的实际音频持续时间。
        
        Args:
            step_to_audio_mapping: 步骤ID到音频段落的映射
            
        Returns:
            Dict: 步骤ID到实际音频持续时间（取整到整数秒）的映射
        """
        actual_durations = {}
        
        for step_id, narrations in step_to_audio_mapping.items():
            if not narrations:
                # 如果没有对应的音频段落，保持原来的持续时间
                for step in self.content_json["blackboard"]["steps"]:
                    if step["step_id"] == step_id:
                        actual_durations[step_id] = step["duration"]
                        break
                continue
                
            # 计算这个步骤的音频持续时间（取最后一个段落的结束时间减去第一个段落的开始时间）
            start_time = min(narr["start_time"] for narr in narrations)
            end_time = max(narr["end_time"] for narr in narrations)
            duration = end_time - start_time
            
            # 四舍五入到整数秒
            actual_durations[step_id] = round(duration)
        
        return actual_durations
    
    def adjust_step_durations(self, actual_durations: Dict[int, int]) -> None:
        """
        根据实际音频持续时间调整黑板步骤的持续时间。
        
        Args:
            actual_durations: 步骤ID到实际持续时间的映射
        """
        if not self.content_json:
            self.load_data()
            
        # 更新每个步骤的持续时间
        for step in self.content_json["blackboard"]["steps"]:
            step_id = step["step_id"]
            if step_id in actual_durations:
                logger.info(f"步骤 {step_id}: 原持续时间 {step['duration']}秒, 调整为 {actual_durations[step_id]}秒")
                step["duration"] = actual_durations[step_id]
    
    def adjust_animation_timings(self) -> None:
        """
        调整步骤内动画的持续时间，以适应步骤的新持续时间。
        如果步骤持续时间发生变化，等比例调整动画的进入/退出时间。
        """
        if not self.content_json:
            self.load_data()
            
        original_durations = self.get_original_durations()
        
        for step in self.content_json["blackboard"]["steps"]:
            step_id = step["step_id"]
            new_duration = step["duration"]
            original_duration = original_durations.get(step_id, new_duration)
            
            # 如果持续时间发生变化，调整动画时间
            if new_duration != original_duration and new_duration > 0:
                scale_factor = new_duration / original_duration
                
                # 调整每个元素的动画时间
                for element in step.get("elements", []):
                    if "animation" in element:
                        animation = element["animation"]
                        if "duration" in animation:
                            animation["duration"] = round(animation["duration"] * scale_factor, 1)
                            
                logger.info(f"步骤 {step_id} 的动画时间已按比例 {scale_factor:.2f} 调整")
    
    def analyze_timing_differences(self) -> Dict:
        """
        分析音频和黑板动画的时间差异
        
        Returns:
            Dict: 时间差异分析结果
        """
        if not self.content_json or not self.audio_metadata:
            self.load_data()
            
        original_durations = self.get_original_durations()
        step_to_audio = self.create_step_audio_mapping()
        actual_durations = self.calculate_actual_durations(step_to_audio)
        
        differences = {}
        for step_id in original_durations:
            original = original_durations[step_id]
            actual = actual_durations.get(step_id, original)
            diff = actual - original
            diff_percent = (diff / original) * 100 if original > 0 else 0
            
            differences[step_id] = {
                "original": original,
                "actual": actual,
                "difference": diff,
                "difference_percent": round(diff_percent, 2)
            }
            
        total_original = sum(original_durations.values())
        total_actual = sum(actual_durations.values())
        
        return {
            "step_differences": differences,
            "total_original": total_original,
            "total_actual": total_actual,
            "total_difference": total_actual - total_original,
            "total_difference_percent": round(((total_actual - total_original) / total_original) * 100, 2) if total_original > 0 else 0
        }
    
    def calculate_total_audio_duration(self) -> float:
        """
        计算总音频持续时间。
        
        Returns:
            float: 总音频持续时间（秒）
        """
        if not self.audio_metadata:
            self.load_data()
            
        if not self.audio_metadata:
            return 0.0
            
        # 查找最后一个片段的结束时间
        if self.audio_metadata:
            return self.audio_metadata[-1]["end_time"]
        return 0.0
    
    def calculate_total_blackboard_duration(self) -> int:
        """
        计算总黑板动画持续时间。
        
        Returns:
            int: 总黑板动画持续时间（秒）
        """
        if not self.content_json:
            self.load_data()
            
        return sum(step["duration"] for step in self.content_json["blackboard"]["steps"])
    
    def save_adjusted_content(self, output_path: str = None) -> str:
        """
        保存调整后的内容JSON文件。
        
        Args:
            output_path: 输出文件路径，如果为None则生成默认路径
            
        Returns:
            str: 保存的文件路径
        """
        if not self.content_json:
            raise ValueError("没有内容可保存，请先调用synchronize()")
            
        if output_path is None:
            # 生成默认输出路径
            original_path = Path(self.content_json_path)
            filename = original_path.stem + "_synchronized" + original_path.suffix
            output_path = str(original_path.parent / filename)
            
        save_json_file(self.content_json, output_path)
        logger.info(f"已将调整后的内容保存到 {output_path}")
        
        return output_path
    
    def synchronize(self, output_path: str = None) -> Dict:
        """
        执行完整的同步过程并返回结果摘要。
        
        Args:
            output_path: 输出文件路径，如果为None则生成默认路径
            
        Returns:
            Dict: 同步结果摘要
        """
        # 加载数据
        self.load_data()
        
        # 分析音频段落与黑板步骤的对应关系
        step_to_audio_mapping = self.create_step_audio_mapping()
        
        # 计算每个步骤的实际音频持续时间
        actual_step_durations = self.calculate_actual_durations(step_to_audio_mapping)
        
        # 获取原始持续时间（用于比较）
        original_durations = self.get_original_durations()
        
        # 调整黑板步骤的持续时间
        self.adjust_step_durations(actual_step_durations)
        
        # 调整步骤内动画的持续时间
        self.adjust_animation_timings()
        
        # 保存调整后的内容
        saved_path = self.save_adjusted_content(output_path)
        
        # 返回同步结果摘要
        return {
            "original_durations": original_durations,
            "adjusted_durations": actual_step_durations,
            "total_audio_duration": self.calculate_total_audio_duration(),
            "total_blackboard_duration": self.calculate_total_blackboard_duration(),
            "saved_to": saved_path,
            "timing_analysis": self.analyze_timing_differences()
        } 
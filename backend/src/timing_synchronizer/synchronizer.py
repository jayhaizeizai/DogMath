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
        
        original_step_times = []
        current_time = 0
        for step in self.content_json["blackboard"]["steps"]:
            step_id_int = step["step_id"] # Ensuring this is an int
            duration = step["duration"]
            original_step_times.append({
                "step_id": step_id_int,
                "start_time": current_time,
                "end_time": current_time + duration
            })
            current_time += duration
        
        step_to_audio = {}
        for step_info in original_step_times:
            step_to_audio[step_info["step_id"]] = [] # Keys are integers
        
        for segment in self.audio_metadata:
            # map_time_to_step_id returns a tuple (start_step_id, end_step_id)
            # When called with only start_time, it effectively uses end_time=None,
            # and both elements of the returned tuple should be the same integer step_id (or None).
            mapping_result_tuple = self.map_time_to_step_id(segment["start_time"])
            
            # The first element of the tuple is the actual start_step_id (integer or None)
            actual_start_step_id_for_segment = mapping_result_tuple[0] 
            
            if actual_start_step_id_for_segment is not None:
                # Ensure the key used for step_to_audio is an integer
                if actual_start_step_id_for_segment in step_to_audio:
                    step_to_audio[actual_start_step_id_for_segment].append(segment)
                else:
                    # This case might indicate an issue if map_time_to_step_id returns an ID
                    # not present in original_step_times, or if step_id was not an int.
                    logger.warning(
                        f"Step ID {actual_start_step_id_for_segment} (type: {type(actual_start_step_id_for_segment)}) "
                        f"from map_time_to_step_id not found as an initialized key in step_to_audio. "
                        f"Segment: {segment}"
                    )
            else:
                logger.warning(f"Segment {segment} could not be mapped to a starting step_id in create_step_audio_mapping.")
        
        return step_to_audio
    
    def map_time_to_step_id(self, start_time: float, end_time: float = None) -> Tuple[Optional[int], Optional[int]]:
        """
        将音频时间点或时间范围映射到对应的黑板步骤ID。
        
        Args:
            start_time: 开始时间点（秒）
            end_time: 结束时间点（秒），如果提供，将返回覆盖的所有步骤
            
        Returns:
            Tuple[Optional[int], Optional[int]]: (开始步骤ID, 结束步骤ID)，如果没有匹配则返回(None, None)
        """
        if not self.content_json:
            self.load_data()
        
        current_time = 0
        start_step_id = None
        end_step_id = None
        
        for i, step in enumerate(self.content_json["blackboard"]["steps"]):
            step_id = step["step_id"]
            duration = step["duration"]
            step_start = current_time
            step_end = current_time + duration
            
            # 找出开始时间所在的步骤
            if start_step_id is None and step_start <= start_time < step_end:
                start_step_id = step_id
            
            # 如果提供了结束时间，找出结束时间所在的步骤
            if end_time is not None:
                if step_start < end_time <= step_end:
                    end_step_id = step_id
                    break
                # 如果结束时间超过了最后一个步骤
                if i == len(self.content_json["blackboard"]["steps"]) - 1 and end_time > step_end:
                    end_step_id = step_id  # 使用最后一个步骤
                    break
            else:
                # 如果没有提供结束时间，则开始和结束步骤相同
                if start_step_id is not None:
                    end_step_id = start_step_id
                    break
            
            current_time += duration
        
        # 如果结束步骤仍未找到但开始步骤已找到，
        # 将结束步骤设为最后一个步骤
        if start_step_id is not None and end_step_id is None:
            end_step_id = self.content_json["blackboard"]["steps"][-1]["step_id"]
        
        return (start_step_id, end_step_id)
    
    def get_actual_audio_durations(self) -> Dict[int, float]:
        """
        计算每个黑板步骤对应的实际音频持续时间。
        
        Returns:
            Dict: 步骤ID到实际音频持续时间的映射
        """
        if not self.audio_metadata:
            self.load_data()
            
        segments = {} # Keys for this dictionary should be integer step_ids
        for segment in self.audio_metadata:
            audio_segment_start_time = segment["start_time"]
            audio_segment_end_time = segment["end_time"]
            
            # map_time_to_step_id returns a tuple (start_step_id, end_step_id)
            # For this function's original logic, we're interested in where the segment starts.
            mapping_result_tuple = self.map_time_to_step_id(audio_segment_start_time)
            step_id_for_segment_start = mapping_result_tuple[0] # This should be an integer or None

            if step_id_for_segment_start is not None:
                if step_id_for_segment_start not in segments:
                    segments[step_id_for_segment_start] = []
                segments[step_id_for_segment_start].append((audio_segment_start_time, audio_segment_end_time))
            else:
                logger.warning(
                    f"Segment starting at {audio_segment_start_time} could not be mapped to a step in get_actual_audio_durations."
                )
        
        step_durations = {}
        for step_id_key, time_ranges in segments.items():
            # step_id_key here is already an integer
            if step_id_key is None: 
                continue
                
            total_duration = sum(end - start for start, end in time_ranges)
            step_durations[step_id_key] = total_duration
        
        return step_durations
    
    def calculate_actual_durations(self, step_to_audio_mapping: Dict[int, List[Dict]]) -> Dict[int, int]:
        """
        根据音频与步骤的映射计算每个步骤的实际音频持续时间。
        改进版：处理跨步骤音频，分配全部音频时间，确保不会有音频被截断。
        
        Args:
            step_to_audio_mapping: 步骤ID到音频段落的映射
            
        Returns:
            Dict: 步骤ID到实际音频持续时间（取整到整数秒）的映射
        """
        if not self.content_json or not self.audio_metadata:
            self.load_data()
        
        # 获取原始步骤持续时间，用于计算比例
        original_durations = self.get_original_durations()
        total_original_duration = sum(original_durations.values())
        
        # 获取总音频时长
        total_audio_duration = self.calculate_total_audio_duration()
        
        # 创建音频段落到步骤的完整映射
        segment_to_steps = []
        for segment in self.audio_metadata:
            start_time = segment["start_time"]
            end_time = segment["end_time"]
            start_step_id, end_step_id = self.map_time_to_step_id(start_time, end_time)
            
            if start_step_id is not None:
                segment_to_steps.append({
                    "segment": segment,
                    "start_step_id": start_step_id,
                    "end_step_id": end_step_id
                })
            
        # 计算每个步骤占用的音频时间
        step_audio_times = {}
        for step_id in original_durations:
            step_audio_times[step_id] = []
        
        # 为每个步骤分配音频时间
        for mapping in segment_to_steps:
            segment = mapping["segment"]
            start_step_id = mapping["start_step_id"]
            end_step_id = mapping["end_step_id"]
            
            if start_step_id == end_step_id:
                # 音频段落完全在一个步骤内
                step_audio_times[start_step_id].append((segment["start_time"], segment["end_time"]))
            else:
                # 音频段落跨多个步骤，需要分配
                current_time = segment["start_time"]
                current_step_idx = self.content_json["blackboard"]["steps"].index(
                    next(s for s in self.content_json["blackboard"]["steps"] if s["step_id"] == start_step_id)
                )
                
                while current_step_idx < len(self.content_json["blackboard"]["steps"]):
                    step = self.content_json["blackboard"]["steps"][current_step_idx]
                    step_id = step["step_id"]
                    
                    # 找出当前步骤的时间范围
                    step_start_time = 0
                    for i in range(current_step_idx):
                        step_start_time += self.content_json["blackboard"]["steps"][i]["duration"]
                    step_end_time = step_start_time + step["duration"]
                    
                    # 计算这个步骤与音频段落的重叠部分
                    overlap_start = max(current_time, step_start_time)
                    if step_id == end_step_id:
                        overlap_end = min(segment["end_time"], step_end_time)
                    else:
                        overlap_end = min(segment["end_time"], step_end_time)
                    
                    if overlap_end > overlap_start:
                        step_audio_times[step_id].append((overlap_start, overlap_end))
                        current_time = overlap_end
                    
                    if current_time >= segment["end_time"] or step_id == end_step_id:
                        break
                    
                    current_step_idx += 1
        
        # 计算每个步骤的音频持续时间
        actual_durations = {}
        for step_id, time_ranges in step_audio_times.items():
            if not time_ranges:
                # 如果没有对应的音频段落，按比例分配总时长
                original_duration = original_durations[step_id]
                proportion = original_duration / total_original_duration
                actual_durations[step_id] = max(1, round(total_audio_duration * proportion))
                continue
            
            # 合并重叠的时间范围
            time_ranges.sort()
            merged_ranges = []
            for time_range in time_ranges:
                if not merged_ranges or time_range[0] > merged_ranges[-1][1]:
                    merged_ranges.append(time_range)
                else:
                    merged_ranges[-1] = (merged_ranges[-1][0], max(merged_ranges[-1][1], time_range[1]))
            
            # 计算合并后的总时长
            total_duration = sum(end - start for start, end in merged_ranges)
            
            # 最小持续时间为1秒
            actual_durations[step_id] = max(1, round(total_duration))
        
        # 确保所有步骤的总持续时间不少于总音频时长
        total_assigned_duration = sum(actual_durations.values())
        if total_assigned_duration < total_audio_duration:
            # 将剩余时间分配给最后一个步骤
            last_step_id = self.content_json["blackboard"]["steps"][-1]["step_id"]
            remaining_time = total_audio_duration - total_assigned_duration
            actual_durations[last_step_id] += round(remaining_time)
            logger.info(f"将剩余的 {remaining_time:.2f} 秒分配给最后一个步骤 {last_step_id}")
        
        # 记录音频分配详情
        logger.info(f"音频总时长: {total_audio_duration:.2f} 秒")
        logger.info(f"步骤分配时长: {sum(actual_durations.values())} 秒")
        for step_id, duration in actual_durations.items():
            original = original_durations.get(step_id, 0)
            logger.info(f"步骤 {step_id}: 原时长 {original}秒, 新时长 {duration}秒, 时间范围: {step_audio_times.get(step_id, [])}")
        
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
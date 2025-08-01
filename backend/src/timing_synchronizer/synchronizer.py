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
            original_durations[step["step_id"]] = step["duration"] # duration is likely int already
        
        return original_durations
    
    def _build_step_intervals(self):
        """返回 [(step_id, start, end), ...]，方便后续快速查重叠"""
        intervals = []
        t = 0.0
        # Ensure durations from content_json are treated as floats for interval calculation
        for step in self.content_json["blackboard"]["steps"]:
            start = t
            # It's crucial that step["duration"] here refers to the *original* duration
            # as intended by the logic of _build_step_intervals, which is called before
            # durations are modified.
            # If get_original_durations() is called before any modification,
            # using step["duration"] directly from self.content_json["blackboard"]["steps"]
            # at this stage should still reflect original durations.
            # However, to be absolutely safe and clear, it might be better to
            # fetch from a pre-calculated original_durations map if available,
            # or ensure this method is only called when content_json reflects original state.
            # For now, assuming step["duration"] is the original when this is first called.
            try:
                duration = float(step["duration"])
            except (TypeError, ValueError):
                logger.warning(f"Step {step.get('step_id', 'N/A')} has invalid duration {step.get('duration', 'N/A')}. Using 0.0.")
                duration = 0.0
            end = t + duration
            intervals.append((step["step_id"], start, end))
            t = end
        return intervals

    def create_step_audio_mapping(self) -> Dict[int, List[Dict]]:
        """
        创建黑板步骤和音频段落之间的映射关系。
        (此方法在新逻辑中不直接用于时长计算，但保留以防其他部分依赖)
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
        (此方法在新逻辑中不直接用于时长计算，但保留以防其他部分依赖)
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
        (此方法在新逻辑中不直接用于时长计算，将被新的 calculate_actual_durations 替代核心功能)
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
    
    def calculate_actual_durations(self) -> Dict[int, float]:
        """
        根据理论旁白的起始时间将其映射到唯一的黑板步骤，
        然后将对应实际音频片段的时长累加到该步骤。
        如果无法映射（即旁白起始时间超出所有步骤的原始范围），则将时长累加到最后一个步骤。
        """
        if not self.content_json or not self.audio_metadata:
            self.load_data()

        step_intervals = self._build_step_intervals()
        if not step_intervals:
            logger.warning("未构建有效的步骤时间区间，无法计算实际时长。")
            return {}
        
        new_step_durations = {step_id: 0.0 for step_id, _, _ in step_intervals}
        last_step_id_in_sequence = step_intervals[-1][0] # ID of the last defined step

        theoretical_narrations = self.content_json.get("audio", {}).get("narration", [])
        actual_audio_segments = self.audio_metadata

        for i, narration_item in enumerate(theoretical_narrations):
            if i >= len(actual_audio_segments):
                logger.warning(f"理论旁白索引 {i} 超出实际音频片段数量 ({len(actual_audio_segments)})。跳过此旁白。")
                continue

            theoretical_start_time_val = narration_item.get("start_time")
            if theoretical_start_time_val is None:
                logger.warning(f"理论旁白 {i} 缺少 'start_time'。跳过。")
                continue
            
            try:
                theoretical_start_time = float(theoretical_start_time_val)
            except (TypeError, ValueError):
                logger.warning(f"理论旁白 {i} 的 'start_time' ({theoretical_start_time_val}) 无效。跳过。")
                continue

            target_step_id = None
            for step_id_loop, step_original_start, step_original_end in step_intervals:
                if step_original_start == step_original_end and step_original_start == theoretical_start_time and step_id_loop == last_step_id_in_sequence:
                    target_step_id = step_id_loop
                    break
                if step_original_start <= theoretical_start_time < step_original_end:
                    target_step_id = step_id_loop
                    break
            
            actual_segment = actual_audio_segments[i]
            actual_duration_val = actual_segment.get("duration")
            if actual_duration_val is None:
                logger.warning(f"实际音频片段 {i} (对应理论旁白 {i}) 缺少 'duration'。跳过。")
                continue
            try:
                actual_duration = float(actual_duration_val)
            except (TypeError, ValueError):
                logger.warning(f"实际音频片段 {i} 的 'duration' ({actual_duration_val}) 无效。跳过。")
                continue

            if actual_duration <= 1e-6: # 只有有效时长才累加
                logger.debug(f"理论旁白 {i} 对应的实际音频时长 ({actual_duration:.3f}s) 过短，未累加。")
                continue

            if target_step_id is not None:
                new_step_durations[target_step_id] += actual_duration
                logger.debug(f"理论旁白 {i} (原start: {theoretical_start_time:.2f}s) "
                             f"映射到步骤 {target_step_id}. "
                             f"其实际音频时长 {actual_duration:.3f}s 已累加. "
                             f"步骤 {target_step_id} 当前总长: {new_step_durations[target_step_id]:.3f}s")
            else:
                # 如果无法映射到任何步骤的定义区间内，则累加到最后一个步骤
                new_step_durations[last_step_id_in_sequence] += actual_duration
                logger.info(f"理论旁白 {i} (原start: {theoretical_start_time:.2f}s) "
                               f"无法映射到任何定义区间。已将其对应的实际音频时长 {actual_duration:.3f}s "
                               f"累加到最后一个步骤 {last_step_id_in_sequence}. "
                               f"步骤 {last_step_id_in_sequence} 当前总长: {new_step_durations[last_step_id_in_sequence]:.3f}s")

        min_len = 0.1
        final_step_durations = {}
        for step_id_from_interval, _, _ in step_intervals:
            accumulated_audio_duration = new_step_durations.get(step_id_from_interval, 0.0)
            final_duration = round(max(min_len, accumulated_audio_duration), 3)
            final_step_durations[step_id_from_interval] = final_duration
            if accumulated_audio_duration < min_len and accumulated_audio_duration >= 0:
                 logger.info(f"步骤 {step_id_from_interval}: 累积音频时长 {accumulated_audio_duration:.3f}s "
                             f"小于最小限制 {min_len}s。已调整为 {min_len}s。")
        
        total_actual_audio_duration_from_metadata = sum(
            float(seg.get("duration", 0.0)) 
            for seg in actual_audio_segments 
            if isinstance(seg.get("duration"), (int, float))
        )
        total_calculated_step_durations = sum(final_step_durations.values())

        logger.info(f"实际音频总时长 (来自audio_metadata各项duration之和): {total_actual_audio_duration_from_metadata:.3f}s")
        logger.info(f"调整后所有黑板步骤总时长 (应用最小时长保护后): {total_calculated_step_durations:.3f}s")
        
        diff_threshold = max(1.0, 0.05 * total_actual_audio_duration_from_metadata)
        if abs(total_actual_audio_duration_from_metadata - total_calculated_step_durations) > diff_threshold:
            logger.warning(f"⚠️ 调整后步骤总时长 ({total_calculated_step_durations:.3f}s) "
                           f"与实际音频总时长 ({total_actual_audio_duration_from_metadata:.3f}s) "
                           f"差异超过阈值 ({diff_threshold:.2f}s)。请检查日志中是否有未映射的旁白，"
                           f"或评估最小时长保护对整体时长的影响。")

        log_output = ", ".join([f"步骤 {k}: {v:.3f}s" for k, v in final_step_durations.items()])
        logger.info(f"各步骤最终调整后时长: {log_output}")

        return final_step_durations
    
    def adjust_step_durations(self, actual_durations: Dict[int, float]) -> None:
        """
        根据实际音频持续时间调整黑板步骤的持续时间。
        """
        if not self.content_json:
            self.load_data()
            
        for step in self.content_json["blackboard"]["steps"]:
            step_id = step["step_id"]
            if step_id in actual_durations:
                original_duration_val = step['duration']
                new_duration_val = actual_durations[step_id]
                # Log with appropriate formatting for float or int
                logger.info(f"步骤 {step_id}: 原持续时间 {original_duration_val}秒, "
                            f"调整为 {new_duration_val:.3f}秒")
                step["duration"] = new_duration_val # Store as float
    
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
    
    def analyze_timing_differences(self, original_durations: Dict[int, float], adjusted_durations: Dict[int, float]) -> Dict:
        """
        分析音频和黑板动画的时间差异, 基于已提供的原始和调整后的时长。
        """
        differences = {}
        for step_id in original_durations:
            original = original_durations[step_id]
            actual = adjusted_durations.get(step_id, original)
            diff = actual - original
            diff_percent = (diff / original) * 100 if original > 1e-6 else 0
            
            differences[step_id] = {
                "original": round(original, 3),
                "actual": round(actual, 3),
                "difference": round(diff, 3),
                "difference_percent": round(diff_percent, 2)
            }
            
        total_original = sum(original_durations.values())
        total_actual = sum(adjusted_durations.values())
        total_diff_overall = total_actual - total_original
        
        return {
            "step_differences": differences,
            "total_original": round(total_original, 3),
            "total_actual": round(total_actual, 3),
            "total_difference": round(total_diff_overall, 3),
            "total_difference_percent": round((total_diff_overall / total_original) * 100, 2) if total_original > 1e-6 else 0
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
    
    def calculate_total_blackboard_duration(self) -> float:
        """
        计算总黑板动画持续时间。
        
        Returns:
            float: 总黑板动画持续时间（秒）
        """
        if not self.content_json:
            self.load_data()
            
        # Durations are now floats in content_json
        return sum(float(step["duration"]) for step in self.content_json["blackboard"]["steps"])
    
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
        采用基于理论时间映射和实际音频时长比例分配的方式调整步骤时长。
        """
        self.load_data()
        
        actual_step_durations_float = self.calculate_actual_durations()
        
        original_durations_float: Dict[int, float] = {
            k: float(v) for k, v in self.get_original_durations().items()
        }

        if not actual_step_durations_float:
             logger.error("未能计算出有效的实际步骤时长，同步中止。")
             # Ensure original_durations_float is used for reporting if actual_step_durations_float is empty
             total_blackboard_orig_duration = sum(original_durations_float.values())
             return {
                "error": "Failed to calculate actual step durations.",
                "original_durations": {k: round(v,3) for k,v in original_durations_float.items()},
                "adjusted_durations": {},
                "total_audio_duration": round(self.calculate_total_audio_duration(), 3),
                "total_blackboard_duration": round(total_blackboard_orig_duration, 3),
             }

        self.adjust_step_durations(actual_step_durations_float)
        self.adjust_animation_timings()
        saved_path = self.save_adjusted_content(output_path)
        
        # Pass float dictionaries to analyze_timing_differences
        timing_analysis = self.analyze_timing_differences(original_durations_float, actual_step_durations_float)
        
        # Ensure all reported durations are consistently rounded for the final report
        final_adjusted_durations_report = {k: round(v,3) for k,v in actual_step_durations_float.items()}
        total_blackboard_adjusted_duration = self.calculate_total_blackboard_duration() # Recalculates from modified content_json

        return {
            "original_durations": {k: round(v,3) for k,v in original_durations_float.items()},
            "adjusted_durations": final_adjusted_durations_report,
            "total_audio_duration": round(self.calculate_total_audio_duration(), 3),
            "total_blackboard_duration": round(total_blackboard_adjusted_duration, 3),
            "saved_to": saved_path,
            "timing_analysis": timing_analysis
        } 
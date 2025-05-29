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
        计算每个黑板步骤的实际持续时间。
        核心逻辑：
        1. 确定每个理论旁白片段 (来自 content_json["audio"]["narration"]) 覆盖了哪些原始黑板步骤
           (基于 content_json 中定义的理论时间)。
        2. 获取每个理论旁白片段对应的实际音频时长 (来自 audio_metadata.json)。
        3. 将该实际音频时长，按比例分配给被其理论上覆盖的黑板步骤。
           比例依据是这些黑板步骤在理论旁白覆盖范围内的原始时长占比。
        4. 一个黑板步骤的最终时长是其从所有相关旁白片段分配到的时长之和。

        Returns:
            Dict: 步骤ID到实际音频持续时间（浮点数，至少为0.1秒，保留3位小数）的映射。
        """
        if not self.content_json or not self.audio_metadata:
            self.load_data()

        blackboard_data = self.content_json.get("blackboard", {})
        blackboard_steps_list = blackboard_data.get("steps", [])
        audio_narration_list = self.content_json.get("audio", {}).get("narration", [])
        actual_audio_segments_list = self.audio_metadata

        if not blackboard_steps_list:
            logger.warning("在 content_json 中未找到黑板步骤。无法计算实际时长。")
            return {}
        
        original_durations_map = {k: float(v) for k, v in self.get_original_durations().items()}

        if not audio_narration_list:
            logger.warning("在 content_json 的 audio.narration 中未找到旁白数据。将使用原始步骤时长。")
            return original_durations_map
        
        if not actual_audio_segments_list:
            logger.warning("在 audio_metadata 中未找到实际音频片段。将使用原始步骤时长。")
            return original_durations_map

        original_step_timing_info = []
        current_original_time = 0.0
        for step_item in blackboard_steps_list:
            step_id = step_item["step_id"]
            original_duration = float(original_durations_map.get(step_id, 0.0)) 
            original_step_timing_info.append({
                "step_id": step_id,
                "original_start_time": current_original_time,
                "original_end_time": current_original_time + original_duration,
                "original_duration": original_duration
            })
            current_original_time += original_duration
        
        accumulated_new_step_durations_float = {step["step_id"]: 0.0 for step in blackboard_steps_list}

        num_narrations = len(audio_narration_list)
        num_actual_segments = len(actual_audio_segments_list)

        for i in range(num_narrations):
            if i >= num_actual_segments:
                logger.warning(f"理论旁白片段 {i} 没有在 audio_metadata.json 中找到对应的实际音频片段。跳过此旁白。")
                continue

            narration_item = audio_narration_list[i]
            actual_audio_segment = actual_audio_segments_list[i] 

            try:
                narr_theoretical_start = float(narration_item["start_time"])
                narr_theoretical_end = float(narration_item["end_time"])
                actual_total_duration_for_this_narration = float(actual_audio_segment["duration"])
            except (TypeError, ValueError) as e:
                logger.warning(f"解析旁白 {i} 或其对应实际音频片段的时长/时间时出错: {e}。跳过此旁白。")
                continue

            if actual_total_duration_for_this_narration <= 1e-6: # Use a small epsilon for float comparison
                logger.info(f"旁白 {i} 对应的实际音频时长过小 ({actual_total_duration_for_this_narration:.3f}s)。跳过分配。")
                continue
            
            if narr_theoretical_end <= narr_theoretical_start:
                logger.info(f"旁白 {i} 的理论结束时间 ({narr_theoretical_end:.2f}s) 不大于理论开始时间 ({narr_theoretical_start:.2f}s)。跳过分配。")
                continue

            steps_covered_by_this_narration = []
            total_original_duration_of_steps_in_narration_span = 0.0

            for step_info in original_step_timing_info:
                overlap_start = max(step_info["original_start_time"], narr_theoretical_start)
                overlap_end = min(step_info["original_end_time"], narr_theoretical_end)
                
                original_duration_of_step_in_narration_span = 0.0
                if overlap_end > overlap_start: 
                    original_duration_of_step_in_narration_span = overlap_end - overlap_start
                
                if original_duration_of_step_in_narration_span > 1e-6: 
                    steps_covered_by_this_narration.append({
                        "step_id": step_info["step_id"],
                        "original_contribution_in_span": original_duration_of_step_in_narration_span
                    })
                    total_original_duration_of_steps_in_narration_span += original_duration_of_step_in_narration_span
            
            if not steps_covered_by_this_narration:
                logger.info(f"旁白 {i} (理论时间 {narr_theoretical_start:.2f}s-{narr_theoretical_end:.2f}s) "
                               f"未覆盖任何原始黑板步骤。其总实际音频时长 {actual_total_duration_for_this_narration:.3f}s 无法分配。")
                continue
            
            if total_original_duration_of_steps_in_narration_span <= 1e-6: 
                logger.warning(f"旁白 {i} 覆盖的步骤在其理论时间范围内的总原始时长贡献过小或为零 "
                               f"({total_original_duration_of_steps_in_narration_span:.2f}s)。无法按比例分配实际时长 "
                               f"{actual_total_duration_for_this_narration:.3f}s。")
                if len(steps_covered_by_this_narration) == 1:
                    only_covered_step_id = steps_covered_by_this_narration[0]["step_id"]
                    accumulated_new_step_durations_float[only_covered_step_id] += actual_total_duration_for_this_narration
                    logger.info(f"  由于上述警告，但仅覆盖一个步骤 {only_covered_step_id}，已将全部实际时长分配给它。")
                continue

            for covered_step in steps_covered_by_this_narration:
                step_id_to_update = covered_step["step_id"]
                original_contribution = covered_step["original_contribution_in_span"]
                
                proportion = original_contribution / total_original_duration_of_steps_in_narration_span
                distributed_duration_for_step = actual_total_duration_for_this_narration * proportion
                
                accumulated_new_step_durations_float[step_id_to_update] += distributed_duration_for_step
                logger.debug(f"  步骤 {step_id_to_update}: 从旁白 {i} 分配到 {distributed_duration_for_step:.3f}s "
                            f"(原始贡献: {original_contribution:.2f}s / 总原始贡献: {total_original_duration_of_steps_in_narration_span:.2f}s, "
                            f"旁白总实际时长: {actual_total_duration_for_this_narration:.3f}s)")

        final_actual_durations_map_float = {}
        min_step_duration = 0.1 # 设定一个最小的步骤时长，例如0.1秒

        for step_id, calculated_total_duration_float in accumulated_new_step_durations_float.items():
            if calculated_total_duration_float <= 1e-6: 
                original_step_duration = float(original_durations_map.get(step_id, min_step_duration))
                # 保留原始精度或至少为min_step_duration
                final_duration = max(min_step_duration, original_step_duration)
                final_actual_durations_map_float[step_id] = round(final_duration, 3)
                logger.info(f"步骤 {step_id} 未从任何旁白分配到有效时长。使用其原始时长 {original_step_duration:.3f}s, "
                               f"调整为 {final_actual_durations_map_float[step_id]:.3f}s。")
            else:
                # 保留计算精度，但确保不小于最小步骤时长，并四舍五入到3位小数
                final_duration = max(min_step_duration, calculated_total_duration_float)
                final_actual_durations_map_float[step_id] = round(final_duration, 3)
        
        total_adjusted_blackboard_duration_float = sum(final_actual_durations_map_float.values())
        logger.info(f"所有黑板步骤调整后的总时长为: {total_adjusted_blackboard_duration_float:.3f}s。")
        
        log_output = ", ".join([f"Step {k}: {v:.3f}s" for k,v in final_actual_durations_map_float.items()])
        logger.info(f"各步骤最终调整后时长: {log_output}")

        return final_actual_durations_map_float
    
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
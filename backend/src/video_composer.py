"""
视频合成器：将黑板视频和音频片段合成为完整视频
"""
import os
import sys
import json
import subprocess
from pathlib import Path
import tempfile
from typing import List, Dict, Any
import shutil
import math
from loguru import logger
from config import Config

# 添加项目根目录到系统路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

# 配置loguru日志
log_path = Path(os.path.dirname(os.path.dirname(__file__))) / "logs" / "video_composer.log"
os.makedirs(log_path.parent, exist_ok=True)
logger.add(log_path, rotation="10 MB", retention="1 week", level="DEBUG", encoding="utf-8")

def run_command(cmd: List[str], ffmpeg_loglevel: str | None = "error") -> bool:
    """
    执行命令行命令。
    对于ffmpeg命令，可以指定日志级别，默认为 'error'。
    
    Args:
        cmd: 命令行命令列表
        ffmpeg_loglevel: ffmpeg的日志级别 (例如 "debug", "info", "warning", "error")。
                         如果为 None，则不添加 -loglevel 参数。
                         默认为 "error"。
        
    Returns:
        执行是否成功
    """
    try:
        processed_cmd = list(cmd) # Make a copy to modify
        is_ffmpeg_command = processed_cmd and processed_cmd[0] == "ffmpeg"

        if is_ffmpeg_command and ffmpeg_loglevel:
            # 检查是否已经存在 -loglevel 参数，如果存在则先移除
            try:
                idx = processed_cmd.index("-loglevel")
                processed_cmd.pop(idx) # remove -loglevel
                processed_cmd.pop(idx) # remove its value
            except ValueError:
                pass # -loglevel not found, no need to remove

            # 查找 "-y" (如果存在) 以便在其后插入新的loglevel (如果ffmpeg_loglevel不是None)
            y_index = -1
            if "-y" in processed_cmd:
                try:
                    y_index = processed_cmd.index("-y")
                except ValueError:
                    pass

            if y_index > 0 and processed_cmd[y_index-1] == "ffmpeg": # Common case: ffmpeg -y
                 processed_cmd.insert(y_index + 1, "-loglevel")
                 processed_cmd.insert(y_index + 2, ffmpeg_loglevel)
            else: # Default: insert right after "ffmpeg"
                 processed_cmd.insert(1, "-loglevel")
                 processed_cmd.insert(2, ffmpeg_loglevel)
            logger.info(f"为ffmpeg命令设置日志级别为: -loglevel {ffmpeg_loglevel}")
        elif is_ffmpeg_command and ffmpeg_loglevel is None:
            # 如果 ffmpeg_loglevel显式设置为 None, 则不添加 -loglevel 参数，使用ffmpeg默认值
            logger.info("ffmpeg命令将使用其默认日志级别。")


        logger.info(f"执行命令: {' '.join(processed_cmd)}")
        process = subprocess.Popen(
            processed_cmd, # 使用处理后的命令执行
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        stdout, stderr = process.communicate()
        
        # 即使是debug日志，ffmpeg也可能将大量信息输出到stderr
        # 所以这里同时记录stdout和stderr
        if stdout:
            logger.debug(f"命令标准输出 (stdout):\n{stdout.strip()}")
        if stderr:
            # 对于ffmpeg的debug日志，stderr通常包含主要信息
            logger.debug(f"命令标准错误/日志 (stderr):\n{stderr.strip()}")

        if process.returncode != 0:
            # 即使返回码非0，stderr中也可能有重要的debug信息，所以上面已经记录了
            logger.error(f"命令执行失败，返回码: {process.returncode}")
            return False
            
        # logger.debug(f"命令执行成功，输出: {stdout.strip() if stdout else 'N/A'}") # 这行可以被上面的详细日志取代
        return True
    except Exception as e:
        logger.error(f"命令执行异常: {str(e)}")
        return False

def get_video_duration(video_path: str) -> float:
    """获取视频时长（单位：秒，返回浮点数）。出错或无法解析则返回 0.0。"""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", video_path],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False
        )
        if result.returncode != 0 or not result.stdout.strip():
            logger.error(f"ffprobe获取时长失败 for {video_path}. Stderr: {result.stderr.strip() if result.stderr else 'N/A'}")
            return 0.0
        duration = float(result.stdout.strip())
        return duration
    except FileNotFoundError:
        logger.error("ffprobe命令未找到。请确保ffmpeg已安装并添加到PATH。")
        return 0.0
    except ValueError:
        logger.error(f"无法将ffprobe的输出转换为浮点数: '{result.stdout.strip() if result.stdout else 'N/A'}' for {video_path}")
        return 0.0
    except Exception as e:
        logger.error(f"获取视频时长 {video_path} 时发生未知错误: {str(e)}")
        return 0.0

def generate_audio_segments(json_path: str, output_dir: str) -> str:
    """
    生成音频片段
    
    Args:
        json_path: 输入JSON文件路径
        output_dir: 输出目录
        
    Returns:
        音频元数据文件路径
    """
    cmd = [
        sys.executable,
        "backend/src/audio_generator/example.py",
        "--segmented",
        json_path,
        output_dir
    ]
    
    if run_command(cmd):
        metadata_path = os.path.join(output_dir, "audio_metadata.json")
        if os.path.exists(metadata_path):
            logger.info(f"音频片段生成成功，元数据文件: {metadata_path}")
            return metadata_path
        else:
            logger.error("元数据文件不存在")
            return ""
    else:
        logger.error("音频片段生成失败")
        return ""

def synchronize_timing(audio_metadata_path: str, json_path: str) -> str:
    """
    根据音频元数据调整内容JSON的时间
    
    Args:
        audio_metadata_path: 音频元数据文件路径
        json_path: 内容JSON文件路径
        
    Returns:
        调整后的JSON文件路径，失败则返回空字符串
    """
    # 生成输出路径
    original_path = Path(json_path)
    synchronized_path = str(original_path.parent / f"{original_path.stem}_synchronized{original_path.suffix}")
    
    # 调用timing_synchronizer的命令行接口
    cmd = [
        sys.executable,
        "-m", "backend.src.timing_synchronizer.cli",
        "--audio-metadata", audio_metadata_path,
        "--content-json", json_path,
        "--output", synchronized_path
    ]
    
    if run_command(cmd):
        if os.path.exists(synchronized_path):
            logger.info(f"时间同步成功，生成调整后的JSON文件: {synchronized_path}")
            return synchronized_path
        else:
            logger.error("调整后的JSON文件不存在")
            return ""
    else:
        logger.error("时间同步失败")
        return ""

def generate_blackboard_video(json_path: str, output_path: str) -> bool:
    """
    生成黑板视频
    
    Args:
        json_path: 输入JSON文件路径
        output_path: 输出视频文件路径
        
    Returns:
        生成是否成功
    """
    cmd = [
        sys.executable,
        "backend/src/blackboard_video_generator/example.py",
        json_path,
        output_path
    ]
    
    if run_command(cmd):
        if os.path.exists(output_path):
            logger.info(f"黑板视频生成成功: {output_path}")
            return True
        else:
            logger.error("视频文件不存在")
            return False
    else:
        logger.error("黑板视频生成失败")
        return False

def compose_video(video_path: str, audio_metadata_path: str, output_path: str) -> bool:
    """
    合成视频和音频
    
    Args:
        video_path: 视频文件路径
        audio_metadata_path: 音频元数据文件路径
        output_path: 输出文件路径
        
    Returns:
        合成是否成功
    """
    try:
        # 读取音频元数据
        with open(audio_metadata_path, 'r', encoding='utf-8') as f:
            audio_segments = json.load(f)
            
        if not audio_segments:
            logger.error("没有音频片段")
            return False
            
        # 创建临时文件用于合成
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as temp_file:
            temp_path = temp_file.name
            
            # 创建FFmpeg文件列表
            for segment in audio_segments:
                audio_path = segment['path']
                start_time = segment['start_time']
                temp_file.write(f"file '{os.path.abspath(audio_path)}'\n".encode('utf-8'))
                
        # 先合并所有音频片段
        temp_audio = os.path.join(os.path.dirname(output_path), "temp_audio.wav")
        concat_cmd = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", temp_path, 
            "-c", "copy", 
            temp_audio
        ]
        
        if not run_command(concat_cmd):
            logger.error("音频合并失败")
            return False
            
        # 将音频和视频合并
        output_cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-i", temp_audio,
            "-c:v", "copy",
            "-c:a", "aac",
            "-shortest",
            output_path
        ]
        
        success = run_command(output_cmd)
        
        # 清理临时文件
        os.unlink(temp_path)
        if os.path.exists(temp_audio):
            os.unlink(temp_audio)
            
        if success and os.path.exists(output_path):
            logger.info(f"视频合成成功: {output_path}")
            return True
        else:
            logger.error("视频合成失败")
            return False
            
    except Exception as e:
        logger.error(f"视频合成异常: {str(e)}")
        return False

def process_teacher_video(json_path: str, output_dir: str) -> bool:
    """
    生成教师视频
    
    Args:
        json_path: 输入JSON文件路径
        output_dir: 输出目录
        
    Returns:
        生成是否成功
    """
    try:
        # 导入teacher_video_generator模块
        from teacher_video_generator.teacher_video_generator import process_all_audio_files
        process_all_audio_files()
        return True
    except Exception as e:
        logger.error(f"生成教师视频失败: {str(e)}")
        return False

def get_timestamp_from_filename(filename: str) -> int:
    """
    从文件名中提取时间戳
    
    Args:
        filename: 文件名，格式如 teacher_video_3000_1.mp4
        
    Returns:
        时间戳数值
    """
    try:
        # 从文件名中提取时间戳部分（第一个数字）
        parts = filename.split('_')
        if len(parts) >= 4:
            return int(parts[2])  # 提取3000这样的时间戳
        return 0
    except:
        return 0

def preprocess_teacher_segment(input_video_path: str, output_video_path: str) -> bool:
    """
    对单个教师视频片段进行预处理（抠像、特效），输出带有Alpha通道的视频。
    
    Args:
        input_video_path: 原始教师视频片段路径
        output_video_path: 处理后视频的输出路径 (推荐 .mov 格式使用 qtrle 编码)
        
    Returns:
        预处理是否成功
    """
    try:
        os.makedirs(os.path.dirname(output_video_path), exist_ok=True)

        filter_effects = (
            "format=rgba,"  # 确保有Alpha通道用于抠像
            "colorkey=0x0D47A1:0.05:0.05,"  # 蓝幕抠像 (根据实际背景色调整)
            "boxblur=0:0:0:0:2:1,"          # 轻微模糊边缘 (可选)
            "colorbalance=bs=0.10:bh=-0.05," # 色彩平衡调整 (可选)
            "unsharp=5:5:1.0:5:5:0.0"       # 轻微锐化 (可选)
        )

        cmd = [
            "ffmpeg", "-y",
            "-i", input_video_path,
            "-vf", filter_effects,
            "-c:v", "qtrle",  # QuickTime Animation 编码，支持Alpha通道，适合做中间文件
            output_video_path
        ]
        
        logger.info(f"预处理教师片段: {Path(input_video_path).name} -> {Path(output_video_path).name}")
        if run_command(cmd):
            if os.path.exists(output_video_path):
                logger.debug(f"成功预处理并保存: {output_video_path}")
                return True
            else:
                logger.error(f"预处理命令执行成功但未找到输出文件: {output_video_path}")
                return False
        else:
            logger.error(f"预处理命令失败: {input_video_path}")
            return False
    except Exception as e:
        logger.error(f"预处理片段 {input_video_path} 时发生异常: {str(e)}")
        return False

def overlay_teacher_video(main_video: str, teacher_videos: List[str], output_path: str) -> bool:
    """
    叠加教师视频到主视频

    Args:
        main_video: 主视频文件路径 (通常是 temp_with_audio.mp4)
        teacher_videos: 教师视频片段文件名列表 (相对于 Config.TEACHER_VIDEO_DIR)
        output_path: 最终输出文件路径

    Returns:
        叠加是否成功
    """
    if not teacher_videos:
        logger.info("没有教师视频需要叠加，跳过此步骤。")
        # 将主视频复制到最终输出路径
        try:
            shutil.copy(main_video, output_path)
            logger.info(f"主视频已复制到: {output_path}")
            return True
        except Exception as e:
            logger.error(f"复制主视频到输出路径失败: {e}")
            return False

    main_video_duration = get_video_duration(main_video)
    if main_video_duration == 0.0:
        logger.error("无法获取主视频时长，无法叠加教师视频。")
        return False
    logger.info(f"主视频时长: {main_video_duration:.2f}秒")

    # 根据文件名中的时间戳对教师视频排序
    # 文件名格式应为 teacher_video_{timestamp_ms}_{index}.mp4
    try:
        sorted_teacher_videos = sorted(
            teacher_videos,
            key=lambda x: get_timestamp_from_filename(Path(x).stem)
        )
        logger.info(f"原始教师视频（待预处理）顺序: {sorted_teacher_videos}")
    except Exception as e:
        logger.error(f"教师视频文件名格式不正确或无法排序: {e}")
        return False
        
    processed_teacher_segments = []
    base_output_dir = Path(output_path).parent
    processed_teacher_dir = base_output_dir / "teacher_video_processed"
    os.makedirs(processed_teacher_dir, exist_ok=True)

    logger.info("开始预处理教师视频片段...")
    for teacher_video_filename in sorted_teacher_videos:
        input_segment_path = str(Path(Config.TEACHER_VIDEO_DIR) / teacher_video_filename)
        # 使用原始文件名（不含后缀）加上新的后缀和目录
        output_segment_name = f"{Path(teacher_video_filename).stem}_processed.mov"
        output_segment_path = str(processed_teacher_dir / output_segment_name)
        
        if not preprocess_teacher_segment(input_segment_path, output_segment_path):
            logger.error(f"预处理教师视频片段 {input_segment_path} 失败。")
            return False
        processed_teacher_segments.append(output_segment_path)
    
    if not processed_teacher_segments:
        logger.error("没有成功预处理的教师视频片段。")
        return False
    
    logger.info(f"所有教师视频片段预处理完成: {processed_teacher_segments}")

    # 将所有预处理后的教师视频片段(.mov)合并成一个文件
    concatenated_processed_teacher_video_path = str(base_output_dir / "temp_teacher_concat_processed.mov")
    
    # 创建FFmpeg concat demuxer的输入文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as concat_file:
        for segment_path in processed_teacher_segments:
            # FFmpeg concat demuxer 需要绝对路径或相对于当前工作目录的路径。
            # 为了安全，我们使用绝对路径，并确保它们被正确引用。
            # 注意：FFmpeg的concat demuxer对文件名中的特殊字符很敏感。
            # 确保路径不含需要转义的特殊字符，或者使用更安全的引用方式（如果FFmpeg支持）。
            # 简单的单引号通常可以处理大部分情况，但更复杂的文件名可能需要额外处理。
            # 这里我们假设路径是"安全"的，或者subprocess能正确处理。
            # FFmpeg的 `-safe 0` 允许使用绝对路径，但路径本身要能被FFmpeg解析。
            concat_file.write(f"file '{os.path.abspath(segment_path)}'\n")
        temp_concat_list_path = concat_file.name

    cmd_concat_teacher = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", temp_concat_list_path,
        "-c", "copy", # 直接拷贝流，因为已经是qtrle
        concatenated_processed_teacher_video_path
    ]
    if not run_command(cmd_concat_teacher):
        logger.error("合并预处理后的教师视频失败。")
        os.unlink(temp_concat_list_path) # 清理临时文件
        return False
    logger.info("合并预处理后的教师视频成功。")
    os.unlink(temp_concat_list_path) # 清理临时文件

    # 新增步骤：将合并后的 QTRLE 教师视频压缩为高质量 H.264
    temp_teacher_concat_compressed_path = str(base_output_dir / "temp_teacher_concat_compressed.mp4")
    logger.info(f"开始将合并后的教师视频 (QTRLE) 压缩为高质量 H.264 -> {temp_teacher_concat_compressed_path}")
    cmd_compress_teacher = [
        "ffmpeg", "-y", 
        "-i", concatenated_processed_teacher_video_path,
        "-c:v", "libx264",
        "-preset", "medium", 
        "-crf", "18",         
        "-pix_fmt", "yuv420p",
        "-an",                
        temp_teacher_concat_compressed_path
    ]
    if not run_command(cmd_compress_teacher):
        logger.error(f"将合并后的教师视频压缩为 H.264 失败: {concatenated_processed_teacher_video_path}")
        return False
    logger.info("合并后的教师视频已成功压缩为 H.264。")

    # 获取压缩后的单个教师视频单元的时长
    # concatenated_teacher_duration = get_video_duration(concatenated_processed_teacher_video_path)
    # 改为获取新压缩的 H.264 文件的时长
    concatenated_teacher_duration = get_video_duration(temp_teacher_concat_compressed_path)


    if concatenated_teacher_duration == 0.0:
        logger.error("无法获取合并后的教师视频单元时长，无法进行循环。")
        return False
    
    logger.info(f"主视频时长: {main_video_duration:.2f}s, 压缩后教师视频单元时长: {concatenated_teacher_duration:.2f}s")

    # 计算循环次数
    # FFmpeg的 -stream_loop N 表示输入流会被额外循环 N 次。所以总播放次数是 N+1。
    # 我们需要总播放次数 M = ceil(main_video_duration / concatenated_teacher_duration)
    # 因此 N = M - 1
    if concatenated_teacher_duration == 0: # 避免除以零
        logger.error("教师视频单元时长为0，无法计算循环次数。")
        return False
        
    total_plays_needed = math.ceil(main_video_duration / concatenated_teacher_duration)
    ffmpeg_stream_loop_param = total_plays_needed - 1
    if ffmpeg_stream_loop_param < 0: # 至少播放一次，所以loop参数不能小于0
        ffmpeg_stream_loop_param = 0 
        
    logger.info(f"压缩后的教师视频单元将通过 -stream_loop {ffmpeg_stream_loop_param} (播放 {ffmpeg_stream_loop_param + 1} 次) 并重编码以覆盖主视频。")
    
    # 准备物理循环扩展并重编码教师视频
    # 输出一个MP4文件，使用libx264编码，不包含音频
    materialized_looped_teacher_path = str(base_output_dir / "temp_teacher_materialized_reencoded.mp4")

    logger.info(f"开始重新编码物理循环扩展后的教师视频 (libx264) -> {Path(materialized_looped_teacher_path).name}")
    
    cmd_loop_reencode_teacher = [
        "ffmpeg", "-y", 
        "-stream_loop", str(ffmpeg_stream_loop_param),
        # 使用新压缩的 H.264 文件作为输入
        "-i", temp_teacher_concat_compressed_path, 
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-preset", "ultrafast", 
        "-crf", "18", 
        "-an", 
        materialized_looped_teacher_path
    ]

    # 这是我们重点关注的命令，所以在这里传递 "debug" 级别
    if not run_command(cmd_loop_reencode_teacher, ffmpeg_loglevel="debug"):
        logger.error("重新编码物理循环扩展后的教师视频失败。")
        return False
    logger.info("重新编码物理循环扩展后的教师视频成功。")

    # 最后，叠加处理好的教师视频到主视频上
    logger.info(f"开始最终叠加教师视频 {Path(materialized_looped_teacher_path).name} 到主视频 {Path(main_video).name}")
    final_overlay_cmd = [
        "ffmpeg", "-y", 
        "-i", main_video,
        "-i", materialized_looped_teacher_path,
        "-filter_complex",
        # 确保这里的尺寸和位置符合预期
        # '[0:v][1:v]overlay=main_w-overlay_w-10:main_h-overlay_h-10:shortest=1[out_v]',
        # 动态获取主视频尺寸以进行精确定位
        # TODO: 考虑将教师视频缩放到特定尺寸或比例，而不是依赖其原始尺寸
        # 例如: "[1:v]scale=iw*0.2:-1[scaled_teacher];[0:v][scaled_teacher]overlay=main_w-overlay_w-10:main_h-overlay_h-10:shortest=1[out_v]",
        # 为了简化，暂时保持原有逻辑，但这里的overlay参数值得回顾
        f"[0:v][1:v]overlay=main_w-overlay_w-{Config.TEACHER_VIDEO_MARGIN_X}:main_h-overlay_h-{Config.TEACHER_VIDEO_MARGIN_Y}:shortest=1[out_v]",
        "-map", "[out_v]",
        "-map", "0:a?", # 映射主视频的音频流（如果存在）
        "-c:v", "libx264", # 最终输出的视频编码
        "-pix_fmt", "yuv420p",
        "-crf", str(Config.VIDEO_ENCODING_CRF), 
        "-preset", Config.VIDEO_ENCODING_PRESET,
        "-c:a", "copy", # 从主视频复制音频流
        "-shortest", # 确保输出以最短的输入流为准（通常是主视频，因为教师视频已循环匹配）
        output_path
    ]
    if not run_command(final_overlay_cmd):
        logger.error("最终叠加教师视频失败。")
        return False

    logger.info(f"教师视频叠加成功，最终输出: {output_path}")

    # 清理临时文件
    # temp_teacher_concat_processed.mov (QTRLE)
    # temp_teacher_concat_compressed.mp4 (H.264 压缩版)
    # temp_teacher_materialized_reencoded.mp4 (循环并重编码的 H.264)
    try:
        if os.path.exists(concatenated_processed_teacher_video_path):
            os.remove(concatenated_processed_teacher_video_path)
            logger.debug(f"已清理临时文件: {concatenated_processed_teacher_video_path}")
        if os.path.exists(temp_teacher_concat_compressed_path):
            os.remove(temp_teacher_concat_compressed_path)
            logger.debug(f"已清理临时文件: {temp_teacher_concat_compressed_path}")
        if os.path.exists(materialized_looped_teacher_path):
            os.remove(materialized_looped_teacher_path)
            logger.debug(f"已清理临时文件: {materialized_looped_teacher_path}")
    except OSError as e:
        logger.warning(f"清理临时教师视频文件时出错: {e}")
        
    return True

def generate_subtitle_file(json_path: str, audio_metadata_path: str, output_path: str) -> bool:
    """
    从JSON文件和音频元数据生成SRT字幕文件
    
    Args:
        json_path: 输入JSON文件路径
        audio_metadata_path: 音频元数据文件路径
        output_path: 输出SRT文件路径
        
    Returns:
        生成是否成功
    """
    try:
        # 读取JSON文件获取字幕文本
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        narrations = data.get('audio', {}).get('narration', [])
        if not narrations:
            logger.error("未找到字幕内容")
            return False
            
        # 读取音频元数据获取准确的时间信息
        with open(audio_metadata_path, 'r', encoding='utf-8') as f:
            audio_segments = json.load(f)
            
        if not audio_segments:
            logger.error("未找到音频元数据")
            return False
            
        # 生成SRT格式字幕
        with open(output_path, 'w', encoding='utf-8') as f:
            for i, segment in enumerate(audio_segments, 1):
                # 从音频元数据中获取准确的时间
                start_time = segment['start_time']
                end_time = segment['end_time']
                
                # 从narrations中获取对应的文本
                text = narrations[i-1]['text'] if i-1 < len(narrations) else ""
                
                # 转换时间格式为 HH:MM:SS,mmm
                start_formatted = '{:02d}:{:02d}:{:02d},000'.format(
                    int(start_time) // 3600,
                    (int(start_time) % 3600) // 60,
                    int(start_time) % 60
                )
                end_formatted = '{:02d}:{:02d}:{:02d},000'.format(
                    int(end_time) // 3600,
                    (int(end_time) % 3600) // 60,
                    int(end_time) % 60
                )
                
                # 写入SRT格式
                f.write(f"{i}\n")
                f.write(f"{start_formatted} --> {end_formatted}\n")
                f.write(f"{text}\n\n")
                
        logger.info(f"字幕文件生成成功: {output_path}")
        return True
        
    except Exception as e:
        logger.error(f"生成字幕文件失败: {str(e)}")
        return False

def add_subtitle_to_video(video_path: str, subtitle_path: str, output_path: str) -> bool:
    """
    将字幕添加到视频中
    
    Args:
        video_path: 输入视频路径
        subtitle_path: 字幕文件路径
        output_path: 输出视频路径
        
    Returns:
        添加是否成功
    """
    try:
        # 定义字幕样式
        # Fontsize: 字体大小，从24减小到18
        # PrimaryColour: 主颜色 (FFFFFF 为白色)
        # OutlineColour: 描边颜色 (000000 为黑色)
        # BorderStyle: 边框样式。1 = 描边+阴影 (更轻量), 3 = 不透明背景框 (较重)
        # MarginV: 垂直边距 (从底部算起)，增加到25像素，使字幕位置更靠下
        # WrapStyle: 换行方式。0=智能换行, 1=只在\n处换行, 2=不换行(超长会溢出), 3=复杂换行(更倾向于单行但仍会处理过长文本)
        # Alignment: 字幕对齐方式 (ASS标准: 1=左下, 2=中下, 3=右下 ... 默认为2，通常无需更改)
        subtitle_style = "Fontsize=18,PrimaryColour=&HFFFFFF&,OutlineColour=&H000000&,BorderStyle=1,MarginV=25,WrapStyle=3"
        
        # 使用FFmpeg添加字幕
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-vf", f"subtitles={subtitle_path}:force_style='{subtitle_style}'",
            "-c:a", "copy",
            output_path
        ]
        
        # 字幕命令通常也用默认的 "error" 级别
        if run_command(cmd): # 将使用run_command默认的 ffmpeg_loglevel="error"
            logger.info(f"字幕添加成功: {output_path}")
            return True
        else:
            logger.error("字幕添加失败")
            return False
            
    except Exception as e:
        logger.error(f"添加字幕过程出错: {str(e)}")
        return False

def main(json_path: str, output_dir: str, final_output_filename: str = "output.mp4"):
    """
    主函数
    
    Args:
        json_path: 输入JSON文件路径
        output_dir: 输出目录
        final_output_filename: 最终输出文件名
    """
    try:
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        # 生成中间文件路径
        audio_segments_dir = os.path.join(output_dir, "audio_segments")
        os.makedirs(audio_segments_dir, exist_ok=True)
        
        temp_video_path = os.path.join(output_dir, "temp_video.mp4")
        temp_with_audio_path = os.path.join(output_dir, "temp_with_audio.mp4")
        final_output_path = os.path.join(output_dir, final_output_filename)
        
        # 步骤1: 生成音频片段
        logger.info("步骤1: 生成音频片段")
        audio_metadata_path = generate_audio_segments(json_path, audio_segments_dir)
        if not audio_metadata_path:
            logger.error("音频片段生成失败，终止")
            return
        
        # 步骤2: 时间同步 - 调整内容JSON的时间
        logger.info("步骤2: 调整内容JSON的时间以匹配音频")
        synchronized_json_path = synchronize_timing(audio_metadata_path, json_path)
        if not synchronized_json_path:
            logger.error("时间同步失败，将使用原始JSON继续")
            synchronized_json_path = json_path
            
        # 步骤3: 生成黑板视频（使用调整后的JSON）
        logger.info(f"步骤3: 生成黑板视频 (使用{synchronized_json_path})")
        if not generate_blackboard_video(synchronized_json_path, temp_video_path):
            logger.error("黑板视频生成失败，终止")
            return
            
        # 步骤4: 合成视频和音频
        logger.info("步骤4: 合成视频和音频")
        if not compose_video(temp_video_path, audio_metadata_path, temp_with_audio_path):
            logger.error("视频音频合成失败，终止")
            return

        # 独立控制是否生成教师视频
        if Config.ENABLE_TEACHER_VIDEO_GENERATION:
            # 步骤5: 生成教师视频
            logger.info("步骤5: 生成教师视频")
            if not process_teacher_video(json_path, output_dir):
                logger.error("教师视频生成失败，继续执行后续步骤")
                # 注意这里不return，继续执行
        
        # 独立控制是否叠加教师视频 - 不再嵌套在生成判断中
        if Config.ENABLE_TEACHER_VIDEO_OVERLAY:
            # 步骤6: 叠加教师视频
            logger.info("步骤6: 叠加教师视频")
            teacher_video_dir = os.path.join(output_dir, "teacher_video")
            
            # 检查教师视频目录是否存在
            if os.path.exists(teacher_video_dir):
                teacher_videos = [
                    os.path.join(teacher_video_dir, f) 
                    for f in os.listdir(teacher_video_dir) 
                    if f.startswith("teacher_video_") and f.endswith(".mp4")
                ]

                if teacher_videos:
                    # 记录找到的视频文件
                    logger.info(f"找到以下教师视频文件: {[os.path.basename(v) for v in teacher_videos]}")

                    if overlay_teacher_video(temp_with_audio_path, teacher_videos, final_output_path):
                        logger.info(f"教师视频叠加完成: {final_output_path}")
                    else:
                        logger.error("教师视频叠加失败，使用无教师视频版本")
                        os.rename(temp_with_audio_path, final_output_path)
                else:
                    logger.error("未找到教师视频文件，使用无教师视频版本")
                    os.rename(temp_with_audio_path, final_output_path)
            else:
                logger.error("教师视频目录不存在，使用无教师视频版本")
                os.rename(temp_with_audio_path, final_output_path)
        else:
            # 如果不叠加教师视频，直接使用带音频的视频作为最终输出
            os.rename(temp_with_audio_path, final_output_path)
            logger.info(f"视频制作完成（无教师视频叠加）: {final_output_path}")
            
        # 步骤7: 生成字幕文件
        logger.info("步骤7: 生成字幕文件")
        subtitle_path = os.path.join(output_dir, "subtitle.srt")
        audio_metadata_path = os.path.join(output_dir, "audio_segments", "audio_metadata.json")
        
        if not os.path.exists(audio_metadata_path):
            logger.error("音频元数据文件不存在")
            return
            
        # 使用同步后的JSON生成字幕，以确保字幕与音频同步
        if not generate_subtitle_file(synchronized_json_path, audio_metadata_path, subtitle_path):
            logger.error("字幕文件生成失败")
            return
            
        # 步骤8: 添加字幕
        logger.info("步骤8: 添加字幕")
        temp_final_path = os.path.join(output_dir, "temp_final.mp4")
        os.rename(final_output_path, temp_final_path)
        
        if add_subtitle_to_video(temp_final_path, subtitle_path, final_output_path):
            logger.info(f"视频制作完成: {final_output_path}")
        else:
            logger.error("字幕添加失败")
            # 如果添加字幕失败，至少保留原始视频
            if os.path.exists(temp_final_path):
                os.rename(temp_final_path, final_output_path)
            
        # 清理临时文件
        for temp_file in [temp_video_path, temp_with_audio_path, temp_final_path, subtitle_path]:
            if os.path.exists(temp_file):
                os.unlink(temp_file)
        
        # 清理同步生成的临时JSON文件
        # if synchronized_json_path != json_path and os.path.exists(synchronized_json_path):
        #     os.unlink(synchronized_json_path)
        #     logger.info(f"已清理临时同步JSON文件: {synchronized_json_path}")
            
        # 清理同步报告JSON文件
        report_path = Path(synchronized_json_path).with_suffix('.report.json')
        if os.path.exists(report_path):
            os.unlink(report_path)
            logger.info(f"已清理同步报告文件: {report_path}")
            
    except Exception as e:
        logger.error(f"视频制作过程中出现错误: {str(e)}")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("用法: python video_composer.py <输入JSON文件路径> [输出目录] [最终输出文件名]")
        sys.exit(1)
        
    json_arg = sys.argv[1]
    output_dir_arg = sys.argv[2] if len(sys.argv) > 2 else "backend/output"
    # 如果直接运行，默认输出文件名基于输入JSON名
    final_filename_arg = sys.argv[3] if len(sys.argv) > 3 else f"{Path(json_arg).stem}.mp4"
    
    # 配置日志（如果这个文件可能被独立运行）
    if not logger.handlers: # 避免重复添加处理器
        log_file_path = Path(output_dir_arg) / "video_composer_direct_run.log"
        os.makedirs(Path(output_dir_arg), exist_ok=True)
        logger.add(log_file_path, rotation="10 MB", retention="1 week", level="DEBUG", encoding="utf-8")

    main(json_arg, output_dir_arg, final_output_filename=final_filename_arg) 
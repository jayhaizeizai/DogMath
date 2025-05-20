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
from loguru import logger
from config import Config

# 添加项目根目录到系统路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

# 配置loguru日志
log_path = Path(os.path.dirname(os.path.dirname(__file__))) / "logs" / "video_composer.log"
os.makedirs(log_path.parent, exist_ok=True)
logger.add(log_path, rotation="10 MB", retention="1 week", level="DEBUG", encoding="utf-8")

def run_command(cmd: List[str]) -> bool:
    """
    执行命令行命令
    
    Args:
        cmd: 命令行命令列表
        
    Returns:
        执行是否成功
    """
    try:
        logger.info(f"执行命令: {' '.join(cmd)}")
        process = subprocess.Popen(
            cmd, 
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        stdout, stderr = process.communicate()
        
        if process.returncode != 0:
            logger.error(f"命令执行失败，错误信息: {stderr}")
            return False
            
        logger.debug(f"命令执行成功，输出: {stdout}")
        return True
    except Exception as e:
        logger.error(f"命令执行异常: {str(e)}")
        return False

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

def overlay_teacher_video(main_video: str, teacher_videos: List[str], output_path: str) -> bool:
    """
    将教师视频叠加到主视频的右下角
    
    Args:
        main_video: 主视频路径
        teacher_videos: 教师视频路径列表
        output_path: 输出视频路径
        
    Returns:
        合成是否成功
    """
    try:
        # 获取主视频时长
        duration_cmd = [
            "ffprobe", "-v", "error", 
            "-show_entries", "format=duration", 
            "-of", "default=noprint_wrappers=1:nokey=1", 
            main_video
        ]
        process = subprocess.Popen(duration_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        main_duration = float(process.communicate()[0].decode().strip())
        logger.info(f"主视频时长: {main_duration}秒")
        
        # 确保视频按时间戳排序
        sorted_videos = sorted(teacher_videos, 
                             key=lambda x: get_timestamp_from_filename(os.path.basename(x)))
        logger.info(f"视频合并顺序: {[os.path.basename(v) for v in sorted_videos]}")
        
        if not sorted_videos:
            logger.error("没有可用的教师视频")
            return False
        
        # 只有在未生成教师视频时才循环使用
        if not Config.ENABLE_TEACHER_VIDEO_GENERATION:
            # 计算所有教师视频的实际总时长
            total_teacher_duration = 0
            for video in sorted_videos:
                duration_cmd = [
                    "ffprobe", "-v", "error", 
                    "-show_entries", "format=duration", 
                    "-of", "default=noprint_wrappers=1:nokey=1", 
                    video
                ]
                process = subprocess.Popen(duration_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                video_duration = float(process.communicate()[0].decode().strip())
                total_teacher_duration += video_duration
                
            logger.info(f"教师视频总时长: {total_teacher_duration}秒")
            
            # 判断是否需要循环使用教师视频
            original_videos = sorted_videos.copy()
            if total_teacher_duration < main_duration:
                repeat_times = int(main_duration / total_teacher_duration) + 1
                logger.info(f"教师视频时长不足，需要循环使用 {repeat_times} 次")
                # 重复添加视频直到总时长超过主视频
                while len(sorted_videos) < repeat_times * len(original_videos):
                    sorted_videos.extend(original_videos)
                logger.info(f"循环后视频合并顺序: {[os.path.basename(v) for v in sorted_videos]}")
        else:
            logger.info("正常生成教师视频模式，按1:1方式使用教师视频")
            
        # 创建临时文件用于存储教师视频列表
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as temp_file:
            temp_path = temp_file.name
            for video in sorted_videos:
                temp_file.write(f"file '{os.path.abspath(video)}'\n".encode('utf-8'))
                
        # 首先合并所有教师视频
        temp_teacher_video = os.path.join(os.path.dirname(output_path), "temp_teacher.mp4")
        concat_cmd = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", temp_path,
            "-c", "copy",
            temp_teacher_video
        ]
        
        if not run_command(concat_cmd):
            logger.error("教师视频合并失败")
            return False

        # 使用FFmpeg去除蓝色背景并叠加视频，并明确限制输出视频长度为主视频长度
        overlay_cmd = [
            "ffmpeg", "-y",
            "-i", main_video,
            "-i", temp_teacher_video,
            "-filter_complex",
            (
                "[1:v]format=rgba,"
                "colorkey=0x0D47A1:0.05:0.05,"
                "boxblur=0:0:0:0:2:1,"
                "colorbalance=bs=0.10:bh=-0.05,"
                "unsharp=5:5:1.0:5:5:0.0[fg];"
                "[0:v][fg]overlay=main_w-overlay_w-10:main_h-overlay_h-10[out]"
            ),
            "-map", "[out]",
            "-map", "0:a?",
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-crf", "20",
            "-preset", "medium",
            "-c:a", "copy",
            "-shortest",  # 添加这个参数，确保输出视频长度为最短输入流的长度
            output_path,
        ]
        
        success = run_command(overlay_cmd)
        
        # 清理临时文件
        os.unlink(temp_path)
        if os.path.exists(temp_teacher_video):
            os.unlink(temp_teacher_video)
        
        if success:
            logger.info(f"教师视频叠加成功: {output_path}")
            return True
        else:
            logger.error("教师视频叠加失败")
            return False
            
    except Exception as e:
        logger.error(f"教师视频叠加过程出错: {str(e)}")
        return False

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
        # 使用FFmpeg添加字幕
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-vf", f"subtitles={subtitle_path}:force_style='Fontsize=24,PrimaryColour=&HFFFFFF&,OutlineColour=&H000000&,BorderStyle=3'",
            "-c:a", "copy",
            output_path
        ]
        
        if run_command(cmd):
            logger.info(f"字幕添加成功: {output_path}")
            return True
        else:
            logger.error("字幕添加失败")
            return False
            
    except Exception as e:
        logger.error(f"添加字幕过程出错: {str(e)}")
        return False

def main(json_path: str, output_dir: str):
    """
    主函数
    
    Args:
        json_path: 输入JSON文件路径
        output_dir: 输出目录
    """
    try:
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        # 生成中间文件路径
        audio_segments_dir = os.path.join(output_dir, "audio_segments")
        os.makedirs(audio_segments_dir, exist_ok=True)
        
        temp_video_path = os.path.join(output_dir, "temp_video.mp4")
        temp_with_audio_path = os.path.join(output_dir, "temp_with_audio.mp4")
        final_output_path = os.path.join(output_dir, "output.mp4")
        
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
        if synchronized_json_path != json_path and os.path.exists(synchronized_json_path):
            os.unlink(synchronized_json_path)
            logger.info(f"已清理临时同步JSON文件: {synchronized_json_path}")
            
        # 清理同步报告JSON文件
        report_path = Path(synchronized_json_path).with_suffix('.report.json')
        if os.path.exists(report_path):
            os.unlink(report_path)
            logger.info(f"已清理同步报告文件: {report_path}")
            
    except Exception as e:
        logger.error(f"视频制作过程中出现错误: {str(e)}")

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("用法: python video_composer.py <输入JSON文件路径>")
        sys.exit(1)
        
    json_path = sys.argv[1]
    output_dir = "backend/output"
    
    main(json_path, output_dir) 
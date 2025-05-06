import requests
import base64
import json
import time
import os
import importlib.util
import sys
from pathlib import Path
import binascii
from moviepy.editor import VideoFileClip, AudioFileClip
import logging
import concurrent.futures
from datetime import datetime
import traceback
import shutil

# 修改配置文件路径读取方式
script_dir = Path(__file__).parent
config_path = script_dir / "config.py"

if config_path.exists():
    spec = importlib.util.spec_from_file_location("config", config_path)
    config = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(config)
else:
    print(f"错误: {config_path} 文件不存在。请根据 config.example.py 创建配置文件。")
    sys.exit(1)

# 从配置文件读取配置
API_KEY = config.API_KEY
ENDPOINT_ID = config.ENDPOINT_ID
API_URL = f"https://api.runpod.ai/v2/{ENDPOINT_ID}/run"
STATUS_URL = f"https://api.runpod.ai/v2/{ENDPOINT_ID}/status/"

# 从配置文件读取其他选项
POSE_PATH = getattr(config, 'POSE_PATH', '')
MERGE_AUDIO = getattr(config, 'MERGE_AUDIO', True)  # 默认开启音频合成

# 添加日志配置
def setup_logging():
    log_dir = Path("backend/logs/teacher_video_generator")
    log_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"generation_{timestamp}.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )

def encode_file(file_path):
    """将文件编码为base64字符串并确保格式正确"""
    with open(file_path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode()
        # 确保编码结果是4的倍数长度
        padding = len(encoded) % 4
        if padding:
            encoded += '=' * (4 - padding)
        return encoded

def validate_base64(b64_string):
    """验证并修复Base64字符串格式"""
    if not isinstance(b64_string, str):
        print(f"警告: Base64字符串类型不正确: {type(b64_string)}")
        return None
        
    # 处理数据URI前缀
    if b64_string.startswith('data:'):
        b64_string = b64_string.split(',', 1)[1]
        
    # 确保长度是4的倍数
    padding = len(b64_string) % 4
    if padding:
        print(f"修复Base64字符串填充: 添加{4-padding}个'='")
        b64_string += '=' * (4 - padding)
        
    # 验证解码
    try:
        base64.b64decode(b64_string)
        return b64_string
    except Exception as e:
        print(f"Base64验证错误: {e}")
        return None

def generate_teacher_video(audio_path, output_path):
    """
    生成教师视频的核心函数，所有参数通过函数参数传递，而不是全局变量
    
    Args:
        audio_path: 输入音频文件路径
        output_path: 输出视频文件路径
        
    Returns:
        生成是否成功
    """
    try:
        # 检查音频文件是否存在
        if not os.path.exists(audio_path):
            logging.error(f"错误: 音频文件不存在 - {audio_path}")
            return False
        
        logging.info(f"正在读取音频文件: {audio_path}")
        audio_base64 = encode_file(audio_path)
        
        # 获取音频时长
        audio_clip = AudioFileClip(audio_path)
        audio_duration = audio_clip.duration
        audio_clip.close()
        
        # 获取fps参数
        fps = getattr(config, 'DEFAULT_FPS', 24)
        
        # 根据音频时长和fps计算帧数
        calculated_length = int(fps * audio_duration)
        logging.info(f"音频时长: {audio_duration}秒, FPS: {fps}, 计算得出的帧数: {calculated_length}")
        
        # 验证音频Base64编码
        validated_audio = validate_base64(audio_base64)
        if not validated_audio:
            logging.error("错误: 音频文件的Base64编码无效")
            return False
        
        # 构建基本请求数据
        input_data = {
            "audio": validated_audio,
            "width": getattr(config, 'DEFAULT_WIDTH', 768),
            "height": getattr(config, 'DEFAULT_HEIGHT', 768),
            "steps": getattr(config, 'DEFAULT_STEPS', 6),
            "guidance_scale": getattr(config, 'DEFAULT_GUIDANCE_SCALE', 1.0),
            "fps": fps,
            "seed": getattr(config, 'DEFAULT_SEED', 420),
            "length": calculated_length,  # 使用计算得出的帧数而不是固定值
            "context_frames": getattr(config, 'DEFAULT_CONTEXT_FRAMES', 12),
            "context_overlap": getattr(config, 'DEFAULT_CONTEXT_OVERLAP', 3),
            "sample_rate": getattr(config, 'DEFAULT_SAMPLE_RATE', 16000),
            "start_idx": getattr(config, 'DEFAULT_START_IDX', 0)
        }
        
        # 处理姿势数据（如果提供）
        if POSE_PATH and os.path.exists(POSE_PATH):
            logging.info(f"正在处理姿势数据: {POSE_PATH}")
            if os.path.isdir(POSE_PATH):
                # 如果是目录，通知用户我们将使用目录
                logging.info(f"将使用姿势数据目录: {POSE_PATH}")
                input_data["pose"] = POSE_PATH
            else:
                # 如果是文件（假设是zip），编码为base64
                logging.info(f"将姿势数据文件进行base64编码: {POSE_PATH}")
                pose_b64 = encode_file(POSE_PATH)
                validated_pose = validate_base64(pose_b64)
                if not validated_pose:
                    logging.error("错误: 姿势数据的Base64编码无效")
                    return False
                input_data["pose"] = validated_pose
                logging.info("姿势数据编码完成")
        
        payload = {
            "input": input_data
        }
        
        # 发送请求
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        }
        
        logging.info("正在发送请求到RunPod API...")
        try:
            response = requests.post(API_URL, headers=headers, json=payload)
            response.raise_for_status()  # 检查HTTP错误
            data = response.json()
            
            # 检查是否是异步作业
            if "id" in data:
                job_id = data["id"]
                logging.info(f"已成功提交异步作业，ID: {job_id}")
                return process_async_job(job_id, headers, output_path, audio_path)
            else:
                # 同步作业，直接处理结果
                return process_result(data, output_path, audio_path)
                
        except requests.exceptions.RequestException as e:
            logging.error(f"API请求错误: {e}")
            return False
        except json.JSONDecodeError:
            logging.error(f"无效的JSON响应: {response.text}")
            return False
        except Exception as e:
            logging.error(f"发生错误: {e}")
            return False
            
    except Exception as e:
        logging.error(f"生成教师视频异常: {e}")
        return False

def process_async_job(job_id, headers, output_path, audio_path):
    """
    轮询异步作业状态并处理结果
    
    Args:
        job_id: 异步作业ID
        headers: HTTP请求头
        output_path: 输出视频路径
        audio_path: 输入音频路径
        
    Returns:
        处理是否成功
    """
    status_url = STATUS_URL + job_id
    
    logging.info("等待作业完成...")
    while True:
        try:
            response = requests.get(status_url, headers=headers)
            response.raise_for_status()
            status_data = response.json()
            
            status = status_data.get("status")
            logging.info(f"作业状态: {status}")
            
            if status == "COMPLETED":
                logging.info("作业已完成!")
                return process_result(status_data, output_path, audio_path)
            elif status == "FAILED":
                logging.error(f"作业失败: {status_data.get('error', '未知错误')}")
                return False
            elif status == "CANCELLED":
                logging.error("作业已取消")
                return False
            
            # 等待10秒后再次轮询
            logging.info("等待10秒...")
            time.sleep(10)
            
        except Exception as e:
            logging.error(f"轮询状态时发生错误: {e}")
            time.sleep(10)  # 出错后继续尝试
    
    return False

def process_result(data, output_path, audio_path):
    """
    处理API返回的结果
    
    Args:
        data: API返回的数据
        output_path: 输出视频路径
        audio_path: 输入音频路径
        
    Returns:
        处理是否成功
    """
    try:
        # 保存原始响应到日志目录
        log_dir = Path("backend/logs/teacher_video_generator")
        response_file = log_dir / "raw_response.json"
        with open(response_file, "w") as f:
            json.dump(data, f, indent=2)
        
        # 提取有效数据（处理多层嵌套）
        response_data = data
        if isinstance(response_data, dict) and "output" in response_data:
            response_data = response_data["output"]
            # 处理第二层嵌套
            if isinstance(response_data, dict) and "output" in response_data:
                response_data = response_data["output"]
        
        if isinstance(response_data, dict) and "video" in response_data:
            video_base64 = response_data["video"]
            
            if isinstance(video_base64, str):
                # 处理数据URI前缀
                if video_base64.startswith('data:'):
                    video_base64 = video_base64.split(',', 1)[1]
                
                # Base64完整性检查
                padding = len(video_base64) % 4
                if padding:
                    video_base64 += '=' * (4 - padding)
                
                # 解码验证
                try:
                    video_data = base64.b64decode(video_base64)
                    if len(video_data) < 1024:
                        raise ValueError("视频数据小于1KB，可能无效")
                        
                    # 确保输出目录存在
                    output_dir = Path(output_path).parent
                    output_dir.mkdir(parents=True, exist_ok=True)
                    
                    # 如果不需要合成音频，直接保存为最终视频
                    if not MERGE_AUDIO:
                        logging.info("跳过音频合成，直接保存无声视频")
                        with open(output_path, "wb") as f:
                            f.write(video_data)
                        logging.info(f"视频已保存到: {output_path}")
                        return True
                    
                    # 如果需要合成音频，保存临时无声视频
                    silent_video_path = output_path.replace('.mp4', '_silent.mp4')
                    with open(silent_video_path, "wb") as f:
                        f.write(video_data)
                    logging.info(f"无声视频已保存到: {silent_video_path}")
                    
                    # 添加音频轨道
                    try:
                        # 创建视频和音频对象
                        video_clip = VideoFileClip(silent_video_path)
                        audio_clip = AudioFileClip(audio_path)
                        
                        # 如果音频比视频长，裁剪音频
                        if audio_clip.duration > video_clip.duration:
                            audio_clip = audio_clip.subclip(0, video_clip.duration)
                        
                        # 添加音频并保存
                        final_clip = video_clip.set_audio(audio_clip)
                        final_clip.write_videofile(output_path, codec="libx264", audio_codec="aac")
                        
                        # 关闭文件
                        video_clip.close()
                        audio_clip.close()
                        final_clip.close()
                        
                        # 删除无声视频
                        if os.path.exists(silent_video_path):
                            os.remove(silent_video_path)
                        
                        logging.info(f"添加音频后的视频保存到: {output_path}")
                        return True
                    except Exception as e:
                        logging.error(f"添加音频时出错: {e}")
                        logging.error("保留无声视频文件")
                        # 如果添加音频失败，至少保留原始视频
                        if not os.path.exists(output_path):
                            os.rename(silent_video_path, output_path)
                            logging.info(f"无声视频重命名为: {output_path}")
                        return False
                    
                except binascii.Error as e:
                    logging.error(f"Base64解码错误: {e}")
                    with open("invalid_base64.txt", "w") as f:
                        f.write(video_base64[:1000])
                    return False
                        
            else:
                logging.error(f"错误: video字段类型应为字符串，实际为{type(video_base64)}")
                return False
        else:
            logging.error("错误: 响应中未找到有效的video字段")
            logging.error(f"可用字段: {list(response_data.keys()) if isinstance(response_data, dict) else '非字典响应'}")
            return False
            
    except Exception as e:
        logging.error(f"处理响应时出错: {e}")
        logging.error(traceback.format_exc())
        return False

def process_single_audio(audio_file):
    """处理单个音频文件"""
    try:
        # 使用绝对路径
        project_root = Path(__file__).parent.parent.parent.parent
        
        # 准备输出路径
        audio_name = audio_file.stem
        video_name = f"teacher_video_{audio_name.split('_', 1)[1]}.mp4"
        output_dir = project_root / "backend/output/teacher_video"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 计算实际的输入和输出路径
        actual_audio_path = str(audio_file)
        actual_output_path = str(output_dir / video_name)
        
        logging.info(f"开始处理音频: {audio_file.name}")
        logging.info(f"输出视频将保存到: {actual_output_path}")
        start_time = time.time()
        
        # 调用核心函数处理单个文件，直接传递路径参数
        success = generate_teacher_video(actual_audio_path, actual_output_path)
        
        # 验证文件是否成功保存
        if success and os.path.exists(actual_output_path):
            file_size = os.path.getsize(actual_output_path)
            logging.info(f"视频文件已保存: {actual_output_path} (大小: {file_size/1024/1024:.2f}MB)")
        else:
            logging.error(f"视频文件未能成功保存: {actual_output_path}")
            return False
        
        end_time = time.time()
        processing_time = end_time - start_time
        logging.info(f"完成处理 {audio_file.name}, 用时: {processing_time:.2f}秒")
        
        return True
    except Exception as e:
        logging.error(f"处理 {audio_file.name} 时出错: {e}")
        logging.error(traceback.format_exc())
        return False

def process_all_audio_files():
    """处理所有音频文件"""
    # 设置日志
    setup_logging()
    
    # 获取所有音频文件
    audio_dir = Path("backend/output/audio_segments")
    audio_files = sorted(audio_dir.glob("*.wav"))
    
    if not audio_files:
        logging.error(f"在 {audio_dir} 中未找到音频文件")
        return
    
    # 清空输出目录
    output_dir = Path("backend/output/teacher_video")
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    total_start_time = time.time()
    logging.info(f"开始处理 {len(audio_files)} 个音频文件")
    
    # 使用线程池并发处理，最多5个并发
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(process_single_audio, audio_file) 
                  for audio_file in audio_files]
        
        # 等待所有任务完成
        concurrent.futures.wait(futures)
    
    total_end_time = time.time()
    total_time = total_end_time - total_start_time
    
    # 统计成功和失败的数量
    success_count = sum(1 for future in futures if future.result())
    fail_count = len(audio_files) - success_count
    
    logging.info(f"""处理完成:
    总用时: {total_time:.2f}秒
    成功: {success_count}个文件
    失败: {fail_count}个文件""")

if __name__ == "__main__":
    process_all_audio_files()

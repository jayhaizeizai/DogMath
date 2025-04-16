import json
from pathlib import Path
from loguru import logger
from blackboard_video_generator import BlackboardVideoGenerator
import sys
import os

# 配置loguru日志
log_path = Path(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))) / "logs" / "video_generator.log"
logger.add(log_path, rotation="10 MB", retention="1 week", level="INFO", encoding="utf-8")

def generate_blackboard_video(json_path: str, output_path: str):
    """
    生成黑板视频
    
    Args:
        json_path: 输入JSON文件路径
        output_path: 输出视频文件路径
    """
    try:
        # 读取JSON数据
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        # 获取黑板数据
        blackboard_data = data.get('blackboard', {})
        logger.info(f"读取到黑板数据：{blackboard_data}")
        
        # 创建视频生成器
        width = blackboard_data.get('resolution', [1920, 1080])[0]
        height = blackboard_data.get('resolution', [1920, 1080])[1]
        logger.info(f"创建视频生成器，分辨率：{width}x{height}")
        
        generator = BlackboardVideoGenerator(width=width, height=height)
        
        # 生成视频
        logger.info("开始生成视频...")
        video = generator.generate_video(blackboard_data)
        
        # 保存视频
        logger.info("开始保存视频...")
        if isinstance(video, str):  # 如果返回的是临时文件路径
            import shutil
            shutil.copy2(video, output_path)
        else:  # 如果返回的是视频对象
            video.release()
            
        logger.info(f"视频已生成: {output_path}")
        
    except Exception as e:
        logger.error(f"视频生成失败: {str(e)}")
        raise

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("用法: python example.py <输入JSON文件路径> <输出视频文件路径>")
        sys.exit(1)
        
    json_path = sys.argv[1]
    output_path = sys.argv[2]
    
    # 确保输出目录存在
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    
    # 生成视频
    generate_blackboard_video(json_path, output_path) 
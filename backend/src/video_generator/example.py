import json
from pathlib import Path
from loguru import logger
from .blackboard_video_generator import BlackboardVideoGenerator

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
        video.write_videofile(
            output_path,
            fps=30,
            codec='libx264',
            audio=False,
            threads=4,
            preset='medium',  # 使用中等压缩预设
            bitrate='5000k'  # 设置比特率
        )
        
        logger.info(f"视频已生成: {output_path}")
        
    except Exception as e:
        logger.error(f"视频生成失败: {str(e)}")
        raise

if __name__ == '__main__':
    # 示例用法
    json_path = 'samples/math_problems/sample_math_problem_001.json'
    output_path = 'output/blackboard_video.mp4'
    
    # 确保输出目录存在
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    
    # 生成视频
    generate_blackboard_video(json_path, output_path) 
import pytest
import os
import json
from loguru import logger
from src.video_generator.blackboard_video_generator import BlackboardVideoGenerator

def test_generate_blackboard_video():
    """测试黑板视频生成"""
    # 设置日志
    logger.add("test_blackboard_video.log", rotation="500 MB")
    
    # 读取示例数据
    json_path = os.path.join(os.path.dirname(__file__), '..', 'samples', 'math_problems', 'sample_math_problem_002.json')
    logger.info(f"读取JSON文件: {json_path}")
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        logger.info(f"JSON数据: {data}")
    
    # 创建输出目录
    output_dir = os.path.join(os.path.dirname(__file__), '..', 'output')
    os.makedirs(output_dir, exist_ok=True)
    
    # 生成视频
    output_path = os.path.join(output_dir, 'test_blackboard_video.mp4')
    logger.info(f"开始生成视频，输出路径: {output_path}")
    
    generator = BlackboardVideoGenerator(debug=True)  # 启用调试模式
    video = generator.generate_video(data['blackboard'])
    
    # 写入视频文件
    logger.info("开始写入视频文件")
    video.write_videofile(
        output_path,
        fps=30,
        codec='libx264',
        audio=False,
        logger=None
    )
    logger.info("视频文件写入完成")
    
    # 验证输出文件
    assert os.path.exists(output_path), "视频文件未生成"
    file_size = os.path.getsize(output_path)
    logger.info(f"视频文件大小: {file_size} 字节")
    assert file_size > 0, "生成的视频文件为空"
    logger.info(f"视频生成成功，文件大小：{file_size / 1024:.2f}KB") 
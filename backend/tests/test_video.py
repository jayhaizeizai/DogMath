import json
import os
import shutil
from pathlib import Path
from loguru import logger
from src.video_generator.blackboard_video_generator import BlackboardVideoGenerator

def main():
    # 获取项目根目录
    root_dir = Path(__file__).parent.parent
    
    # 设置日志
    logs_dir = root_dir / "logs"
    logs_dir.mkdir(exist_ok=True)
    logger.add(logs_dir / "test_video.log", rotation="500 MB")
    
    # 读取示例数据
    json_path = root_dir / "data/samples/math_problems/sample_math_problem_002.json"
    logger.info(f"读取JSON文件: {json_path}")
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        logger.info(f"JSON数据: {data}")
    
    # 创建输出目录
    output_dir = root_dir / "output"
    output_dir.mkdir(exist_ok=True)
    
    # 设置输出路径 (使用.mp4格式)
    output_path = output_dir / "test_blackboard_video.mp4"
    logger.info(f"开始生成视频，输出路径: {output_path}")
    
    # 生成视频
    generator = BlackboardVideoGenerator(debug=True)  # 启用调试模式
    temp_video_file = generator.generate_video(data['blackboard'])
    
    if temp_video_file and os.path.exists(temp_video_file):
        # 将临时文件复制到目标位置
        logger.info(f"将临时文件复制到: {output_path}")
        shutil.copy(temp_video_file, output_path)
        
        # 删除临时文件
        logger.info(f"删除临时文件: {temp_video_file}")
        os.remove(temp_video_file)
        
        # 验证输出文件
        assert output_path.exists(), "视频文件未生成"
        file_size = output_path.stat().st_size
        logger.info(f"视频文件大小: {file_size} 字节")
        assert file_size > 0, "生成的视频文件为空"
        logger.info(f"视频生成成功，文件大小：{file_size / 1024:.2f}KB")
    else:
        logger.error("视频生成失败，没有收到有效的临时文件")

if __name__ == "__main__":
    main() 
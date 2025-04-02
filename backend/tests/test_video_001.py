import json
import os
import shutil
from pathlib import Path
from loguru import logger
from src.video_generator.blackboard_video_generator import BlackboardVideoGenerator

def main():
    # 设置日志
    logger.add("test_video_001.log", rotation="500 MB")
    
    # 读取示例数据
    json_path = Path("samples/math_problems/sample_math_problem_001.json")
    logger.info(f"读取JSON文件: {json_path}")
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        logger.info(f"JSON数据: {data}")
    
    # 创建输出目录
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    # 设置输出路径
    output_path = output_dir / "test_blackboard_video_001.mp4"
    logger.info(f"开始生成视频，输出路径: {output_path}")
    
    # 生成视频
    generator = BlackboardVideoGenerator(debug=True)  # 启用调试模式
    temp_video_file = generator.generate_video(data['blackboard'])
    
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

if __name__ == "__main__":
    main() 
import os
import sys
from pathlib import Path
import logging

# 设置项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.video_generator.blackboard_video_generator import BlackboardVideoGenerator

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    # 获取项目根目录
    root_dir = Path(__file__).parent.parent
    
    # 测试数据
    test_data = {
        "metadata": {
            "problem_id": "GEOMETRY_TRIANGLE_004",
            "difficulty": "medium",
            "estimated_duration": 30,
            "knowledge_tags": ["几何图形", "三角形", "图形绘制"],
            "created_at": "2024-04-01T00:00:00Z"
        },
        "blackboard": {
            "background": "classic_blackboard",
            "resolution": [1920, 1080],
            "steps": [
                {
                    "step_id": 1,
                    "title": "三角形绘制",
                    "duration": 20,
                    "elements": [
                        {
                            "type": "geometry",
                            "content": "M0 0 L100 0 L50 100 Z",
                            "position": [960, 540],
                            "font_size": 32,
                            "animation": {
                                "enter": "draw_path",
                                "duration": 5
                            }
                        },
                        {
                            "type": "text",
                            "content": "三角形示例",
                            "position": [960, 300],
                            "font_size": 48,
                            "animation": {
                                "enter": "fade_in",
                                "duration": 2
                            }
                        },
                        {
                            "type": "formula",
                            "content": "A = \\frac{1}{2}bh",
                            "position": [960, 780],
                            "font_size": 42,
                            "animation": {
                                "enter": "fade_in",
                                "duration": 3
                            }
                        }
                    ]
                }
            ]
        }
    }
    
    logger.info(f"测试数据: {test_data}")
    
    # 创建输出目录
    output_dir = root_dir / "output"
    output_dir.mkdir(exist_ok=True)
    
    # 设置输出路径
    output_path = output_dir / "test_triangle_video.mp4"
    logger.info(f"开始生成视频，输出路径: {output_path}")
    
    # 生成视频
    generator = BlackboardVideoGenerator(debug=True)
    temp_video_file = generator.generate_video(test_data['blackboard'])
    
    # 复制到最终输出路径
    import shutil
    logger.info(f"将临时文件复制到: {output_path}")
    shutil.copy2(temp_video_file, output_path)
    
    # 删除临时文件
    logger.info(f"删除临时文件: {temp_video_file}")
    os.remove(temp_video_file)
    
    # 检查生成的视频文件大小
    video_size = os.path.getsize(output_path)
    logger.info(f"视频文件大小: {video_size} 字节")
    logger.info(f"视频生成成功，文件大小：{video_size/1024:.2f}KB")

if __name__ == "__main__":
    main() 
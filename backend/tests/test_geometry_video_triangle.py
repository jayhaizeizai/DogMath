import json
import os
import shutil
from pathlib import Path
from loguru import logger
from backend.src.video_generator.blackboard_video_generator import BlackboardVideoGenerator

def main():
    # 获取项目根目录
    root_dir = Path(__file__).parent.parent
    
    # 设置日志
    logs_dir = root_dir / "logs"
    logs_dir.mkdir(exist_ok=True)
    logger.add(logs_dir / "test_geometry_triangle.log", rotation="500 MB")
    
    # 创建三角形测试数据
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
    generator = BlackboardVideoGenerator(debug=True)  # 启用调试模式
    temp_video_file = generator.generate_video(test_data['blackboard'])
    
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
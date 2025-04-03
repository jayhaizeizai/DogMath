import os
import json
from src.video_generator.blackboard_video_generator import BlackboardVideoGenerator

def test_arc_geometry():
    # 读取示例数据
    sample_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'samples', 'math_problems', 'sample_math_problem_003.json')
    with open(sample_path, 'r', encoding='utf-8') as f:
        sample_data = json.load(f)
    
    # 创建视频生成器实例
    generator = BlackboardVideoGenerator(
        width=1920,
        height=1080,
        debug=True  # 启用调试模式
    )
    
    # 设置输出路径
    output_path = os.path.join(os.path.dirname(__file__), '..', 'output', 'test_arc_geometry.mp4')
    
    # 生成视频
    temp_video_file = generator.generate_video(sample_data['blackboard'])
    
    # 复制到最终输出路径
    import shutil
    shutil.copy2(temp_video_file, output_path)
    
    # 删除临时文件
    os.remove(temp_video_file)
    
    # 检查生成的视频文件大小
    video_size = os.path.getsize(output_path)
    print(f"视频生成成功，文件大小：{video_size/1024:.2f}KB")

if __name__ == "__main__":
    test_arc_geometry() 
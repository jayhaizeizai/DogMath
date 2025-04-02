import pytest
from pathlib import Path
from src.video_generator.video_generator import VideoGenerator

def test_video_generator_initialization():
    """测试视频生成器初始化"""
    generator = VideoGenerator(output_dir="test_output")
    assert generator.output_dir == Path("test_output")
    assert generator.output_dir.exists()

def test_load_script():
    """测试脚本加载"""
    generator = VideoGenerator()
    script_path = Path(__file__).parent.parent.parent / "samples" / "math_problems" / "sample_math_problem_001.json"
    script = generator.load_script(str(script_path))
    
    # 验证基本结构
    assert "metadata" in script
    assert "blackboard" in script
    assert "avatar" in script
    assert "audio" in script
    assert "annotations" in script
    
    # 验证元数据
    assert script["metadata"]["problem_id"] == "CIRCLE_CHORD_001"
    assert script["metadata"]["difficulty"] == "medium"
    assert "knowledge_tags" in script["metadata"] 
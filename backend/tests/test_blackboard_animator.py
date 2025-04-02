import pytest
from pathlib import Path
import cv2
import numpy as np
from src.video_generator.blackboard_animator import BlackboardAnimator

def test_blackboard_animator_initialization():
    """测试黑板动画生成器初始化"""
    animator = BlackboardAnimator(output_dir="test_output")
    assert animator.output_dir == Path("test_output")
    assert animator.output_dir.exists()
    assert animator.temp_dir.exists()

def test_create_blackboard():
    """测试创建黑板背景"""
    animator = BlackboardAnimator()
    resolution = (1920, 1080)
    blackboard = animator.create_blackboard(resolution)
    
    assert blackboard.shape == (resolution[1], resolution[0], 3)
    assert blackboard.dtype == np.uint8
    assert np.all(blackboard == animator.background_color)

def test_draw_text():
    """测试文本绘制"""
    animator = BlackboardAnimator()
    resolution = (1920, 1080)
    image = animator.create_blackboard(resolution)
    
    # 测试文本绘制
    text = "测试文本"
    position = (100, 100)
    result = animator.draw_text(image, text, position)
    
    assert result.shape == image.shape
    assert result.dtype == image.dtype
    
    # 验证文本区域不是黑色（背景色）
    text_region = result[position[1]-10:position[1]+10, position[0]-10:position[0]+10]
    assert not np.all(text_region == animator.background_color)

def test_draw_formula():
    """测试LaTeX公式渲染"""
    animator = BlackboardAnimator()
    resolution = (1920, 1080)
    image = animator.create_blackboard(resolution)
    
    # 测试简单公式
    formula = r"$x^2 + y^2 = r^2$"
    position = (960, 540)  # 中心位置
    result = animator.draw_formula(image, formula, position)
    
    assert result.shape == image.shape
    assert result.dtype == image.dtype
    
    # 验证公式区域不是黑色（背景色）
    formula_region = result[position[1]-20:position[1]+20, position[0]-20:position[0]+20]
    assert not np.all(formula_region == animator.background_color)
    
    # 测试复杂公式
    complex_formula = r"$\int_{0}^{\infty} e^{-x^2} dx = \frac{\sqrt{\pi}}{2}$"
    result = animator.draw_formula(image, complex_formula, position)
    
    assert result.shape == image.shape
    assert result.dtype == image.dtype
    
    # 测试中文公式
    chinese_formula = r"$\text{圆的面积} = \pi r^2$"
    result = animator.draw_formula(image, chinese_formula, position)
    
    assert result.shape == image.shape
    assert result.dtype == image.dtype

def test_create_animation():
    """测试创建动画"""
    animator = BlackboardAnimator(output_dir="test_output")
    
    # 创建测试脚本
    test_script = {
        "metadata": {
            "problem_id": "TEST_001"
        },
        "blackboard": {
            "resolution": [1920, 1080],
            "steps": [
                {
                    "step_id": 1,
                    "title": "测试步骤",
                    "duration": 1,  # 1秒
                    "elements": [
                        {
                            "type": "text",
                            "content": "测试文本",
                            "position": [10, 10],
                            "font_size": 32
                        },
                        {
                            "type": "formula",
                            "content": r"$x^2 + y^2 = r^2$",
                            "position": [50, 50],
                            "font_size": 32
                        }
                    ]
                }
            ]
        }
    }
    
    # 生成动画
    output_path = animator.create_animation(test_script, "test_animation.mp4")
    
    # 验证输出文件
    assert Path(output_path).exists()
    
    # 验证视频文件
    cap = cv2.VideoCapture(output_path)
    assert cap.isOpened()
    
    # 验证帧数（1秒 * 30fps）
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    assert frame_count == 30
    
    # 释放资源
    cap.release() 
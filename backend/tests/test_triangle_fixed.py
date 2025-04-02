import json
import os
import shutil
from pathlib import Path
from loguru import logger
import sys

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from backend.src.video_generator.blackboard_video_generator import BlackboardVideoGenerator

def main():
    # 获取项目根目录
    root_dir = Path(__file__).parent.parent
    
    # 设置日志
    logs_dir = root_dir / "logs"
    logs_dir.mkdir(exist_ok=True)
    logger.add(logs_dir / "test_triangle_fixed.log", rotation="500 MB")
    
    # 创建三角形测试数据
    test_data = {
        "metadata": {
            "problem_id": "GEOMETRY_TRIANGLE_TEST",
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
                            "content": "$A = \\frac{1}{2}bh$",
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
    output_path = output_dir / "test_triangle_fixed.mp4"
    logger.info(f"开始生成视频，输出路径: {output_path}")
    
    # 自定义BlackboardVideoGenerator，确保svg_path和scale_factor在时间轴中
    class FixedBlackboardVideoGenerator(BlackboardVideoGenerator):
        def _render_and_add_to_timeline(self, element, fade_in_frames=0, fade_out_frames=0, draw_path_frames=0):
            """
            渲染元素并添加到时间轴 - 修复版本，确保几何图形的svg_path和scale_factor被保存
            
            Args:
                element: 元素字典
                fade_in_frames: 淡入帧数
                fade_out_frames: 淡出帧数
                draw_path_frames: 路径绘制帧数
            """
            try:
                element_type = element.get('type', '')
                if element_type == 'text':
                    text = element.get('content', 'Text Placeholder')
                    scale_factor = element.get('font_size', 32)
                    img = self._render_text(text, scale_factor)
                elif element_type == 'formula':
                    formula = element.get('content', 'E=mc^2')
                    scale_factor = element.get('font_size', 100)
                    img = self._render_formula(formula, scale_factor)
                elif element_type == 'geometry':
                    svg_path = element.get('content', 'M0 0 L100 0 L100 100 L0 100 Z')
                    scale_factor = element.get('font_size', 32)
                    img = self._render_geometry(svg_path, scale_factor)
                else:
                    self.logger.error(f"未知的元素类型: {element_type}")
                    return
                    
                # 转换坐标为像素位置
                position = element.get('position', [0.5, 0.5])
                x_ratio, y_ratio = position
                x = int(x_ratio * self.width)
                y = int(y_ratio * self.height)
                
                # 居中图像
                h, w = img.shape[:2]
                x = x - w // 2
                y = y - h // 2
                
                # 添加到时间轴
                current_frame = self.current_frame
                duration_frames = element.get('duration_frames', 30)
                
                timeline_element = {
                    'element': img,
                    'position': (x, y),
                    'start_frame': current_frame,
                    'end_frame': current_frame + duration_frames,
                    'fade_in_frames': fade_in_frames,
                    'fade_out_frames': fade_out_frames,
                }
                
                # 对于几何图形元素，添加动画路径绘制效果和原始SVG数据
                if element_type == 'geometry' and draw_path_frames > 0:
                    timeline_element['type'] = 'geometry'
                    timeline_element['svg_path'] = svg_path
                    timeline_element['scale_factor'] = scale_factor
                    timeline_element['draw_path_frames'] = draw_path_frames
                    self.logger.info(f"添加几何图形到时间轴: svg_path={svg_path}, scale_factor={scale_factor}")
                
                self.timeline.append(timeline_element)
                self.current_frame += duration_frames
                
            except Exception as e:
                self.logger.error(f"渲染和添加到时间轴时出错: {str(e)}")
    
    # 生成视频
    generator = FixedBlackboardVideoGenerator(debug=True)  # 启用调试模式
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
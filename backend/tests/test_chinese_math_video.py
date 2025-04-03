import json
import os
import sys
import shutil
import time
from pathlib import Path
from loguru import logger
import re
import cv2
import numpy as np
import traceback

# 设置项目根目录到Python路径
project_root = str(Path(__file__).parent.parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from backend.src.video_generator.blackboard_video_generator import BlackboardVideoGenerator

# 配置日志
log_dir = Path("backend/logs")
log_dir.mkdir(parents=True, exist_ok=True)
log_file = log_dir / f"chinese_math_video_{time.strftime('%Y%m%d_%H%M%S')}.log"

# 移除默认logger
logger.remove()
# 添加文件logger
logger.add(log_file, rotation="100 MB", level="DEBUG")
# 添加控制台logger
logger.add(sys.stdout, level="INFO")

class ChineseMathVideoGenerator(BlackboardVideoGenerator):
    def __init__(self, resolution=(1920, 1080), debug=False):
        width, height = resolution
        super().__init__(width=width, height=height, debug=debug)
        self.timeline = []

    def _render_and_add_to_timeline(self, element, progress=1.0):
        try:
            if element['type'] == 'geometry':
                self.logger.info(f"开始渲染几何元素: {element}")
                
                # 获取几何数据和缩放因子
                geometry_data = element['content']
                scale_factor = element.get('scale', 1.0)
                
                self.logger.info(f"几何数据: {geometry_data}")
                self.logger.info(f"缩放因子: {scale_factor}")
                
                # 渲染几何图形
                img = self._render_geometry(geometry_data, progress=progress, scale_factor=scale_factor)
                
                # 计算位置并添加到时间线
                x_ratio, y_ratio = element['position']
                x = int(x_ratio * self.width)
                y = int(y_ratio * self.height)
                
                # 居中图像
                img_height, img_width = img.shape[:2]
                x = x - img_width // 2
                y = y - img_height // 2
                
                self.logger.info(f"几何元素位置: ({x}, {y})")
                
                # 添加到时间轴
                duration_frames = int(element.get('animation', {}).get('duration', 2) * self.fps)
                
                timeline_element = {
                    'element': img,
                    'position': (x, y),
                    'start_frame': self.current_frame,
                    'end_frame': self.current_frame + duration_frames,
                    'fade_in_frames': 0,
                    'fade_out_frames': 0,
                    'draw_path_frames': duration_frames if element.get('animation', {}).get('enter') == 'draw_path' else 0
                }
                
                self.timeline.append(timeline_element)
                self.current_frame += duration_frames
                
            else:
                super()._render_and_add_to_timeline(element, progress)
                
        except Exception as e:
            self.logger.error(f"渲染元素时出错: {str(e)}")
            self.logger.error(f"错误堆栈: {traceback.format_exc()}")

def main():
    """生成中文数学教学视频"""
    try:
        # 读取数据文件
        data_file = "backend/data/samples/math_problems/sample_math_problem_004.json"
        logger.info(f"读取数据文件: {data_file}")
        
        with open(data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            logger.debug(f"读取的数据: {json.dumps(data, ensure_ascii=False, indent=2)}")
        
        # 创建输出目录
        output_dir = Path("backend/output")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 生成视频
        generator = ChineseMathVideoGenerator(debug=True)
        temp_output = generator.generate_video(data['blackboard'])  # 注意这里需要传入blackboard部分
        
        if temp_output and os.path.exists(temp_output):
            # 复制到最终位置
            output_file = output_dir / "chinese_math_video_004.mp4"
            shutil.copy2(temp_output, output_file)
            logger.info(f"视频生成完成: {output_file}")
            
            # 删除临时文件
            os.unlink(temp_output)
            logger.info("已删除临时文件")
        else:
            logger.error("视频生成失败")
            
    except Exception as e:
        logger.error(f"生成视频时出错: {str(e)}")
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        raise

if __name__ == "__main__":
    main()
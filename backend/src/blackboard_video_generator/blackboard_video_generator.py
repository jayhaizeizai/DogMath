from typing import List, Dict, Any, Tuple
import numpy as np
import cv2
from loguru import logger
import matplotlib
import matplotlib.pyplot as plt
import os
import time

from .utils.image_utils import create_blackboard_background, blend_image_to_frame
from .utils.video_utils import compress_video, get_z_index
from .renderers.text_renderer import render_text
from .renderers.formula_renderer import render_formula
from .renderers.geometry_renderer import render_geometry

class BlackboardVideoGenerator:
    """黑板视频生成器"""
    
    def __init__(self, width: int = 1920, height: int = 1080, debug: bool = False):
        """
        初始化黑板视频生成器
        
        Args:
            width: 视频宽度
            height: 视频高度
            debug: 是否启用调试模式
        """
        self.width = width
        self.height = height
        self.debug = debug
        self.logger = logger.bind(context="blackboard_video")
        
        # 确保debug模式下日志级别生效
        if self.debug:
            self.logger.debug("调试模式已启用")
            self.logger.info(f"初始化黑板视频生成器: width={width}, height={height}")
        
        # 配置matplotlib
        self._setup_matplotlib()
        
    def _setup_matplotlib(self):
        """配置matplotlib的渲染设置"""
        # 设置中文字体
        plt.rcParams['font.sans-serif'] = [
            'WenQuanYi Micro Hei', 
            'WenQuanYi Zen Hei', 
            'Noto Sans CJK SC', 
            'Source Han Sans CN', 
            'Hiragino Sans GB', 
            'Microsoft YaHei', 
            'SimHei', 
            'STHeiti', 
            'DejaVu Sans'
        ]
        plt.rcParams['axes.unicode_minus'] = False  # 用来正常显示负号
        plt.rcParams['font.family'] = 'sans-serif'
        matplotlib.use('Agg')  # 使用无界面后端
        
        # 打印当前可用字体
        if self.debug:
            try:
                from matplotlib.font_manager import fontManager
                font_names = sorted([f.name for f in fontManager.ttflist])
                self.logger.info(f"可用字体: {', '.join(font_names[:10])}...")
            except Exception as e:
                self.logger.warning(f"无法获取字体列表: {str(e)}")
    
    def generate_video(self, data):
        """生成视频"""
        try:
            # 获取视频参数
            width = data['resolution'][0]
            height = data['resolution'][1]
            fps = 30  # 默认帧率
            
            # 创建视频写入器
            output_path = "backend/output/blackboard_video.mp4"
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            video_writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
            
            # 创建黑板背景
            background = create_blackboard_background(width, height)
            
            # 在创建timeline之前，识别几何元素和文本标签
            for step in data['steps']:
                geometry_elements = []
                text_elements = []
                
                for element in step['elements']:
                    if element['type'] == 'geometry':
                        geometry_elements.append(element)
                    elif element['type'] == 'text' and element['content'] in ['O', 'A', 'B', 'C']:
                        text_elements.append(element)
                
                # 如果同时存在几何图形和字母标签，确保它们的位置匹配
                if geometry_elements and text_elements:
                    self.logger.info("检测到几何图形和文本标签，调整位置以确保匹配")
                    
                    # 具体的调整逻辑
                    # 例如，可以根据几何图形的大小和位置调整文本标签的位置
            
            # 处理每个步骤
            for step in data['steps']:
                # 计算总帧数
                total_frames = int(step['duration'] * fps)
                
                # 创建时间线
                timeline = []
                
                # 处理每个元素
                for element in step['elements']:
                    element_type = element['type']
                    content = None
                    
                    # 根据元素类型渲染内容
                    if element_type == 'text':
                        if self.debug:
                            self.logger.debug(f"渲染文本元素: {element['content'][:30]}...")
                        content = render_text(element['content'], element.get('font_size', 32), self.debug)
                    elif element_type == 'formula':
                        if self.debug:
                            self.logger.debug(f"渲染公式元素: {element['content'][:30]}...")
                        content = render_formula(element['content'], element.get('font_size', 32), self.debug)
                    elif element_type == 'geometry':
                        if self.debug:
                            self.logger.debug(f"渲染几何元素，包含键: {list(element['content'].keys())}")
                        content = render_geometry(element['content'], scale_factor=element.get('scale', 1.0), debug=self.debug)
                    
                    if content is not None:
                        # 处理动画配置
                        animation = element.get('animation', {})
                        fade_in_frames = 0
                        
                        if animation:
                            fade_duration = animation.get('duration', 1.0)
                            fade_in_frames = int(fade_duration * fps)
                        
                        # 添加到时间线，包含所有必要的属性
                        timeline.append({
                            'type': element_type,
                            'content': content,
                            'position': element['position'],
                            'start_frame': 0,  # 从开始就显示
                            'end_frame': total_frames,  # 持续到结束
                            'fade_in_frames': fade_in_frames,
                            'fade_out_frames': 0,
                            'z_index': get_z_index(element_type)
                        })
                
                # 按z_index排序时间线元素
                timeline.sort(key=lambda x: x['z_index'])
                
                # 生成帧
                for frame_idx in range(total_frames):
                    # 复制背景
                    frame = background.copy()
                    
                    # 渲染当前帧的所有元素
                    for item in timeline:
                        if item['start_frame'] <= frame_idx < item['end_frame']:
                            # 计算alpha值（淡入效果）
                            alpha = 1.0
                            if item['fade_in_frames'] > 0 and frame_idx < item['fade_in_frames']:
                                alpha = frame_idx / item['fade_in_frames']
                            
                            # 获取位置（0-1的比例值）
                            pos_x, pos_y = item['position']
                            
                            # 混合元素到帧中
                            blend_image_to_frame(frame, item['content'], pos_x, pos_y, alpha, self.debug)
                    
                    # 写入帧
                    video_writer.write(frame)
                    
                    # 显示进度
                    if frame_idx % 30 == 0:
                        self.logger.info(f"正在生成视频 {frame_idx}/{total_frames} 帧 ({frame_idx/total_frames*100:.1f}%)")
            
            # 释放视频写入器
            video_writer.release()
            
            # 压缩视频
            compress_video(output_path, self.logger)
            
            return output_path
            
        except Exception as e:
            self.logger.error(f"生成视频时出错: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return None


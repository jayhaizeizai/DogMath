from typing import List, Dict, Any, Tuple
import numpy as np
import cv2
from loguru import logger
import matplotlib
import matplotlib.pyplot as plt
import os
import time
import json

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
    
    def _auto_vertical_stack(self, step: dict) -> None:
        """
        自动垂直堆叠元素
        
        Args:
            step: 步骤配置字典
        """
        safe = step.get('safe_zone', {})
        safe_top = safe.get('top', 0.05)
        safe_bottom = safe.get('bottom', 0.05)
        safe_right = safe.get('right', 0.40)  # 增加右侧安全区为40%
        v_space = step.get('vertical_spacing', 0.02)

        y_cursor = safe_top  # 游标指向"下一行的顶边"
        for el in step['elements']:
            w_ratio, h_ratio = el['size']
            
            # 1. 处理 X 位置
            if 'position' in el:
                x = el['position'][0]
            else:
                x = 0.5  # 默认居中
                
            # 检查右侧安全区（使用半宽度判断）
            if x + w_ratio/2 > 1 - safe_right:
                x = 0.5 - safe_right / 2  # 把中心移到可见区域正中
                
            # 2. 设置中心点 Y ——顶边 + ½ 行高
            anchor_y = y_cursor + h_ratio / 2
            el['position'] = [x, anchor_y]
            
            # 3. 游标下移：整行高 + 垂直间距
            y_cursor += h_ratio + v_space
            
        # 4. （可选）如果溢出底部安全区，可在这里整体 scale / 分页

    def generate_video(self, blackboard_data: dict) -> str:
        """
        生成黑板视频
        
        Args:
            blackboard_data: 黑板数据字典
            
        Returns:
            临时视频文件路径
        """
        try:
            # 获取步骤列表
            steps = blackboard_data.get('steps', [])
            if not steps:
                self.logger.error("未找到步骤数据")
                return ""
                
            # 处理每个步骤
            for step in steps:
                # 处理每个元素
                for element in step.get('elements', []):
                    # 渲染元素并缓存尺寸
                    if element['type'] == 'formula':
                        img = render_formula(element['content'], element.get('font_size', 32), self.debug)
                    elif element['type'] == 'text':
                        img = render_text(element['content'], element.get('font_size', 32), self.debug)
                    elif element['type'] == 'geometry':
                        img = render_geometry(element['content'], scale_factor=element.get('scale', 1.0), debug=self.debug)
                    else:
                        continue
                        
                    # 缓存元素尺寸
                    h_ratio = img.shape[0] / self.height
                    w_ratio = img.shape[1] / self.width
                    element['size'] = (w_ratio, h_ratio)
                    
                # 如果配置了自动垂直堆叠，则应用
                if step.get('layout') == 'vertical-stack':
                    self._auto_vertical_stack(step)
                    
            # 获取视频参数
            width = blackboard_data.get('resolution', [self.width, self.height])[0]
            height = blackboard_data.get('resolution', [self.width, self.height])[1]
            fps = 30  # 默认帧率
            
            # 创建临时输出路径
            temp_output = "backend/output/temp_blackboard.mp4"
            
            # 创建视频写入器
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            video_writer = cv2.VideoWriter(temp_output, fourcc, fps, (width, height))
            
            # 创建黑板背景
            background = create_blackboard_background(width, height)
            
            # 在创建timeline之前，识别几何元素和文本标签
            for step in blackboard_data['steps']:
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
            for step in blackboard_data['steps']:
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
                        fade_out_frames = 0
                        
                        if animation:
                            fade_duration = animation.get('duration', 1.0)
                            fade_in_frames = int(fade_duration * fps)
                            if 'exit' in animation:
                                fade_out_frames = int(fade_duration * fps)
                        
                        # 添加到时间线
                        timeline.append({
                            'type': element_type,
                            'content': content,
                            'position': element['position'],
                            'start_frame': 0,
                            'end_frame': total_frames - fade_out_frames if fade_out_frames > 0 else total_frames,
                            'fade_in_frames': fade_in_frames,
                            'fade_out_frames': fade_out_frames,
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
                            # 计算alpha值（淡入淡出效果）
                            alpha = 1.0
                            if item['fade_in_frames'] > 0 and frame_idx < item['fade_in_frames']:
                                alpha = frame_idx / item['fade_in_frames']
                            elif item['fade_out_frames'] > 0 and frame_idx >= item['end_frame'] - item['fade_out_frames']:
                                alpha = (item['end_frame'] - frame_idx) / item['fade_out_frames']
                            
                            # 获取位置
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
            compress_video(temp_output, self.logger)
            
            # 返回临时视频文件路径
            return temp_output
            
        except Exception as e:
            self.logger.error(f"视频生成失败: {str(e)}")
            return ""


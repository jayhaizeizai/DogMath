from typing import List, Dict, Any, Tuple
import numpy as np
import cv2
from loguru import logger
import matplotlib
import matplotlib.pyplot as plt
from matplotlib import mathtext
import os
import io
import tempfile
import time
import subprocess
import sys
import re
import traceback

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
        
        # 配置matplotlib
        self._setup_matplotlib()
        
        if self.debug:
            self.logger.info(f"初始化黑板视频生成器: width={width}, height={height}")
            
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
            background = self._create_blackboard_background(width, height)
            
            # 处理每个步骤
            for step in data['steps']:
                # 计算总帧数
                total_frames = int(step['duration'] * fps)
                
                # 创建时间线
                timeline = []
                
                # 处理每个元素
                for element in step['elements']:
                    element_type = element['type']
                    position = element['position']
                    
                    # 计算元素的开始和结束帧
                    start_frame = 0
                    end_frame = total_frames
                    
                    # 处理动画
                    animation = element.get('animation', {})
                    fade_in_frames = 0
                    fade_out_frames = 0
                    
                    if animation.get('enter') == 'fade_in':
                        fade_duration = animation.get('duration', 1)
                        fade_in_frames = int(fade_duration * fps)
                    elif animation.get('enter') == 'slide_in_left':
                        fade_duration = animation.get('duration', 1)
                        fade_in_frames = int(fade_duration * fps)
                    elif animation.get('enter') == 'draw_path':
                        fade_duration = animation.get('duration', 1)
                        fade_in_frames = int(fade_duration * fps)
                    
                    # 渲染元素
                    content = None
                    if element_type == 'text':
                        content = self._render_text(element['content'], element.get('font_size', 32))
                    elif element_type == 'formula':
                        content = self._render_formula(element['content'], element.get('font_size', 32))
                    elif element_type == 'geometry':
                        content = self._render_geometry(element['content'], scale_factor=element.get('scale', 1.0))
                    
                    if content is not None:
                        # 计算像素坐标
                        img_h, img_w = content.shape[:2]
                        x = int(position[0] * width) - img_w // 2
                        y = int(position[1] * height) - img_h // 2
                        
                        timeline.append({
                            'type': element_type,
                            'content': content,
                            'position': (x, y),
                            'start_frame': start_frame,
                            'end_frame': end_frame,
                            'fade_in_frames': fade_in_frames,
                            'fade_out_frames': fade_out_frames
                        })
                
                # 生成帧
                for frame_idx in range(total_frames):
                    # 复制背景
                    frame = background.copy()
                    
                    # 渲染当前帧的所有元素
                    for item in timeline:
                        if item['start_frame'] <= frame_idx < item['end_frame']:
                            # 获取内容
                            content = item['content']
                            pos_x, pos_y = item['position']
                            
                            # 计算Alpha值（淡入和淡出效果）
                            alpha = 1.0
                            if item['fade_in_frames'] > 0 and frame_idx < item['start_frame'] + item['fade_in_frames']:
                                relative_frame = frame_idx - item['start_frame']
                                alpha = relative_frame / item['fade_in_frames']
                            elif item['fade_out_frames'] > 0 and frame_idx > item['end_frame'] - item['fade_out_frames']:
                                relative_frame = item['end_frame'] - frame_idx
                                alpha = relative_frame / item['fade_out_frames']
                            
                            self.logger.info(f"渲染帧 {frame_idx}, 元素类型: {item['type']}, 位置: ({pos_x}, {pos_y}), Alpha: {alpha}")
                            
                            # 合成元素到帧中
                            self._blend_image_to_frame(frame, content, pos_x, pos_y, alpha)
                    
                    # 写入帧
                    video_writer.write(frame)
                    
                    # 显示进度
                    if frame_idx % 30 == 0:
                        self.logger.info(f"正在生成视频 {frame_idx}/{total_frames} 帧 ({frame_idx/total_frames*100:.1f}%)")
            
            # 释放视频写入器
            video_writer.release()
            
            # 压缩视频
            self._compress_video(output_path)
            
            return output_path
            
        except Exception as e:
            self.logger.error(f"生成视频时出错: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return None
    
    def _create_blackboard_background(self, width: int, height: int) -> np.ndarray:
        """创建黑板背景"""
        # 创建黑色背景
        background = np.ones((height, width, 3), dtype=np.uint8) * np.array([30, 30, 30], dtype=np.uint8)
        
        # 添加轻微噪点和纹理
        noise = np.random.normal(0, 5, background.shape).astype(np.int16)
        background = np.clip(background.astype(np.int16) + noise, 10, 50).astype(np.uint8)
        
        # 添加一些粉笔灰
        dust_mask = np.random.random(background.shape[:2]) > 0.995
        background[dust_mask] = np.array([70, 70, 70])
        
        return background
    
    def _blend_image_to_frame(self, frame: np.ndarray, img: np.ndarray, x: int, y: int, alpha: float = 1.0):
        """
        将图像混合到帧中
        
        Args:
            frame: 目标帧
            img: 要混合的图像
            x: x坐标（中心点）
            y: y坐标（中心点）
            alpha: 透明度
        """
        try:
            if img is None:
                return
                
            # 获取图像尺寸
            img_h, img_w = img.shape[:2]
            frame_h, frame_w = frame.shape[:2]
            
            # 计算图像的实际位置（中心对齐）
            x = int(x - img_w / 2)
            y = int(y - img_h / 2)
            
            # 确保坐标在有效范围内
            x = max(0, min(x, frame_w - img_w))
            y = max(0, min(y, frame_h - img_h))
            
            # 计算重叠区域
            x1, y1 = max(0, x), max(0, y)
            x2, y2 = min(frame_w, x + img_w), min(frame_h, y + img_h)
            
            # 计算源图像的对应区域
            src_x1, src_y1 = max(0, -x), max(0, -y)
            src_x2, src_y2 = src_x1 + (x2 - x1), src_y1 + (y2 - y1)
            
            # 检查是否有重叠区域
            if x2 <= x1 or y2 <= y1 or src_x2 <= src_x1 or src_y2 <= src_y1:
                return
                
            # 提取源图像区域
            src_region = img[src_y1:src_y2, src_x1:src_x2]
            
            # 如果源图像是RGBA格式
            if src_region.shape[2] == 4:
                # 提取alpha通道并应用全局alpha
                src_alpha = src_region[:, :, 3] / 255.0 * alpha
                src_alpha = np.expand_dims(src_alpha, axis=2)
                
                # 将源图像转换为RGB
                src_rgb = src_region[:, :, :3]
                
                # 提取目标区域
                dst_region = frame[y1:y2, x1:x2]
                
                # 混合图像
                blended = dst_region * (1 - src_alpha) + src_rgb * src_alpha
                frame[y1:y2, x1:x2] = blended.astype(np.uint8)
            else:
                # 如果是RGB格式，直接应用alpha混合
                src_alpha = alpha
                dst_region = frame[y1:y2, x1:x2]
                blended = dst_region * (1 - src_alpha) + src_region * src_alpha
                frame[y1:y2, x1:x2] = blended.astype(np.uint8)
                
        except Exception as e:
            self.logger.error(f"图像混合失败: {str(e)}")
            self.logger.error(f"frame shape: {frame.shape}, img shape: {img.shape}, position: ({x}, {y})")
    
    def _render_formula(self, formula: str, font_size: int) -> np.ndarray:
        """
        渲染公式
        
        Args:
            formula: 公式字符串
            font_size: 字体大小
            
        Returns:
            公式图像
        """
        try:
            # 检测是否含有中文
            has_chinese = any('\u4e00' <= c <= '\u9fff' for c in formula)
            
            # 检测是否含有LaTeX格式的公式
            is_latex = '\\' in formula or '$' in formula
            
            # 混合内容处理（中文+LaTeX）
            if has_chinese and is_latex:
                # 分割文本和LaTeX公式
                components = re.split(r'(\$[^$]*\$)', formula)
                
                # 处理多个LaTeX部分
                rendered_parts = []
                
                for comp in components:
                    if comp.strip():  # 忽略空字符串
                        if comp.startswith('$') and comp.endswith('$'):
                            # 渲染LaTeX部分
                            latex_img = self._render_latex_as_image(comp, font_size)
                            rendered_parts.append(latex_img)
                        else:
                            # 渲染中文部分
                            chinese_img = self._render_text_as_image(comp, font_size)
                            rendered_parts.append(chinese_img)
                
                # 计算总宽度和最大高度
                total_width = sum(img.shape[1] for img in rendered_parts) + 20 * (len(rendered_parts) - 1)
                max_height = max(img.shape[0] for img in rendered_parts)
                
                # 创建组合图像
                combined_img = np.ones((max_height, total_width, 3), dtype=np.uint8) * np.array([30, 30, 30], dtype=np.uint8)
                
                # 放置各个部分
                x_offset = 0
                for img in rendered_parts:
                    h, w = img.shape[:2]
                    y_offset = (max_height - h) // 2
                    combined_img[y_offset:y_offset+h, x_offset:x_offset+w] = img
                    x_offset += w + 20
                
                # 检查是否需要缩放最终图像
                max_width = 800  # 最大宽度
                max_img_height = 600  # 最大高度
                
                h, w = combined_img.shape[:2]
                if self.debug:
                    self.logger.info(f"组合公式原始图像大小: {w}x{h}")
                
                # 如果图像太大，进行等比例缩放
                if w > max_width or h > max_img_height:
                    scale = min(max_width / w, max_img_height / h)
                    new_w = int(w * scale)
                    new_h = int(h * scale)
                    combined_img = cv2.resize(combined_img, (new_w, new_h), interpolation=cv2.INTER_AREA)
                    if self.debug:
                        self.logger.info(f"组合公式缩放后图像大小: {new_w}x{new_h}")
                
                return combined_img
            
            # 对于纯中文公式(不含LaTeX格式)
            if has_chinese and not is_latex:
                return self._render_text_as_image(formula, font_size)
                
            # 对于纯LaTeX公式
            if is_latex:
                # 确保LaTeX公式有$符号
                if not formula.startswith('$') and not formula.endswith('$'):
                    formula = f'${formula}$'
                return self._render_latex_as_image(formula, font_size)
            
            # 对于普通文本
            return self._render_text_as_image(formula, font_size)
            
        except Exception as e:
            self.logger.error(f"渲染公式时出错: {str(e)}")
            # 创建一个默认图像
            img = np.zeros((100, 300, 3), dtype=np.uint8)
            cv2.putText(img, "Formula Error", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            return img
            
    def _render_text_as_image(self, text: str, font_size: int) -> np.ndarray:
        """
        将文本渲染为图像
        
        Args:
            text: 文本内容
            font_size: 字体大小
            
        Returns:
            文本图像
        """
        try:
            # 创建matplotlib图形
            fig = plt.figure(figsize=(10, 2), dpi=200, facecolor='none')
            ax = fig.add_subplot(111)
            
            # 设置背景完全透明
            fig.patch.set_alpha(0.0)
            ax.set_facecolor((0, 0, 0, 0))
            ax.patch.set_alpha(0.0)
            
            # 尝试检测可用的中文字体
            chinese_font = None
            has_chinese = any('\u4e00' <= c <= '\u9fff' for c in text)
            
            if has_chinese:
                try:
                    from matplotlib.font_manager import fontManager
                    font_priorities = [
                        'Noto Sans CJK SC', 
                        'Noto Sans CJK JP', 
                        'Source Han Sans CN', 
                        'WenQuanYi Micro Hei', 
                        'WenQuanYi Zen Hei', 
                        'Microsoft YaHei', 
                        'SimHei', 
                        'STHeiti'
                    ]
                    
                    for font in font_priorities:
                        matching_fonts = [f.name for f in fontManager.ttflist if font.lower() in f.name.lower()]
                        if matching_fonts:
                            chinese_font = matching_fonts[0]
                            if self.debug:
                                self.logger.info(f"文本渲染使用中文字体: {chinese_font}")
                            break
                except Exception as e:
                    if self.debug:
                        self.logger.warning(f"检测中文字体失败: {str(e)}")
                
            # 渲染文本
            if chinese_font:
                ax.text(0.5, 0.5, text, 
                       fontsize=font_size*0.8,  # 调整字体大小
                       color='white',
                       horizontalalignment='center',
                       verticalalignment='center',
                       transform=ax.transAxes,
                       family=chinese_font)
            else:
                # 如果没有找到合适的中文字体，尝试用sans-serif字体族
                ax.text(0.5, 0.5, text, 
                       fontsize=font_size*0.8,  # 调整字体大小
                       color='white',
                       horizontalalignment='center',
                       verticalalignment='center',
                       transform=ax.transAxes,
                       family='sans-serif')
                if self.debug and has_chinese:
                    self.logger.warning("未找到中文字体，使用sans-serif族")
            
            # 移除坐标轴和边框
            ax.axis('off')
            for spine in ax.spines.values():
                spine.set_visible(False)
            
            # 调整边距
            plt.tight_layout(pad=0.5)
            
            # 将图形转换为图像
            buf = io.BytesIO()
            plt.savefig(buf, format='png', 
                       bbox_inches='tight',
                       pad_inches=0.2,
                       facecolor='none',
                       edgecolor='none',
                       transparent=True)
            plt.close(fig)
            
            # 读取图像数据
            buf.seek(0)
            img = cv2.imdecode(np.frombuffer(buf.read(), np.uint8), cv2.IMREAD_UNCHANGED)
            
            # 处理透明通道 (BGRA -> RGB)
            if img.shape[2] == 4:  # BGRA
                # 创建一个与黑板背景颜色匹配的画布
                canvas = np.ones((img.shape[0], img.shape[1], 3), dtype=np.uint8) * np.array([30, 30, 30], dtype=np.uint8)
                
                # 提取透明通道作为蒙版
                alpha = img[:, :, 3] / 255.0
                
                # 只将非透明部分渲染为白色
                for c in range(3):  # RGB通道
                    canvas[:, :, c] = canvas[:, :, c] * (1 - alpha) + 255 * alpha
                
                return canvas
            else:
                return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                
        except Exception as e:
            self.logger.error(f"渲染文本为图像时出错: {str(e)}")
            # 创建一个默认图像
            img = np.zeros((100, max(len(text) * 20, 200), 3), dtype=np.uint8)
            cv2.putText(img, "Text Error", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            return img
            
    def _render_latex_as_image(self, latex: str, font_size: int = 24) -> np.ndarray:
        """
        将LaTeX公式渲染为图像
        
        Args:
            latex: LaTeX公式字符串
            font_size: 字体大小
            
        Returns:
            渲染后的图像
        """
        try:
            # 创建matplotlib图形
            fig = plt.figure(figsize=(10, 2), dpi=200, facecolor='none')
            ax = fig.add_subplot(111)
            
            # 设置背景完全透明
            fig.patch.set_alpha(0.0)
            ax.set_facecolor((0, 0, 0, 0))
            ax.patch.set_alpha(0.0)
            
            # 移除坐标轴和边框
            ax.axis('off')
            for spine in ax.spines.values():
                spine.set_visible(False)
            
            # 设置LaTeX导言区
            plt.rcParams['text.latex.preamble'] = r'\usepackage{amsmath,amssymb,ctex}'
            
            # 渲染LaTeX公式
            latex_content = latex.strip('$').replace(r'\begin{align*}', '').replace(r'\end{align*}', '')
            ax.text(0.5, 0.5, r'\begin{align*}' + latex_content + r'\end{align*}',
                   fontsize=font_size,
                   color='white',
                   horizontalalignment='center',
                   verticalalignment='center',
                   transform=ax.transAxes,
                   usetex=True)
            
            # 调整边距
            plt.tight_layout(pad=0.5)
            
            # 将图形转换为图像
            buf = io.BytesIO()
            plt.savefig(buf, format='png', 
                        bbox_inches='tight',
                        pad_inches=0.2,
                        facecolor='none',
                        edgecolor='none',
                        transparent=True)
            plt.close(fig)
            
            # 读取图像数据
            buf.seek(0)
            img = cv2.imdecode(np.frombuffer(buf.read(), np.uint8), cv2.IMREAD_UNCHANGED)
            
            # 处理透明通道 (BGRA -> RGB)
            if img.shape[2] == 4:  # BGRA
                # 创建一个与黑板背景颜色匹配的画布
                canvas = np.ones((img.shape[0], img.shape[1], 3), dtype=np.uint8) * np.array([30, 30, 30], dtype=np.uint8)
                
                # 提取透明通道作为蒙版
                alpha = img[:, :, 3] / 255.0
                
                # 只将非透明部分渲染为白色
                for c in range(3):  # RGB通道
                    canvas[:, :, c] = canvas[:, :, c] * (1 - alpha) + 255 * alpha
                
                # 检查是否需要缩放图像
                max_width = 800  # 最大宽度
                max_height = 600  # 最大高度
                
                h, w = canvas.shape[:2]
                if self.debug:
                    self.logger.info(f"LaTeX公式原始图像大小: {w}x{h}")
                
                # 如果图像太大，进行等比例缩放
                if w > max_width or h > max_height:
                    scale = min(max_width / w, max_height / h)
                    new_w = int(w * scale)
                    new_h = int(h * scale)
                    canvas = cv2.resize(canvas, (new_w, new_h), interpolation=cv2.INTER_AREA)
                    if self.debug:
                        self.logger.info(f"LaTeX公式缩放后图像大小: {new_w}x{new_h}")
                
                return canvas
            else:
                return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                
        except Exception as e:
            self.logger.error(f"渲染LaTeX公式时出错: {latex}")
            self.logger.error(str(e))
            import traceback
            self.logger.error(traceback.format_exc())
            # 创建一个默认图像，使用与黑板背景匹配的颜色
            img = np.ones((100, 300, 3), dtype=np.uint8) * np.array([30, 30, 30], dtype=np.uint8)
            cv2.putText(img, "LaTeX Error", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            return img

    def _render_text(self, text: str, font_size: int) -> np.ndarray:
        """
        渲染文本
        
        Args:
            text: 文本内容
            font_size: 字体大小
            
        Returns:
            文本图像
        """
        try:
            # 创建matplotlib图形
            fig = plt.figure(figsize=(10, 2), dpi=200, facecolor='none')
            ax = fig.add_subplot(111)
            
            # 设置背景完全透明
            fig.patch.set_alpha(0.0)
            ax.set_facecolor((0, 0, 0, 0))
            ax.patch.set_alpha(0.0)
            
            # 尝试检测可用的中文字体
            chinese_font = None
            try:
                from matplotlib.font_manager import fontManager
                font_priorities = [
                    'Noto Sans CJK SC', 
                    'Noto Sans CJK JP', 
                    'Source Han Sans CN', 
                    'WenQuanYi Micro Hei', 
                    'WenQuanYi Zen Hei', 
                    'Microsoft YaHei', 
                    'SimHei', 
                    'STHeiti'
                ]
                
                for font in font_priorities:
                    matching_fonts = [f.name for f in fontManager.ttflist if font.lower() in f.name.lower()]
                    if matching_fonts:
                        chinese_font = matching_fonts[0]
                        if self.debug:
                            self.logger.info(f"选择中文字体: {chinese_font}")
                        break
            except Exception as e:
                if self.debug:
                    self.logger.warning(f"检测中文字体失败: {str(e)}")
                
            # 渲染文本
            if chinese_font:
                ax.text(0.5, 0.5, text, 
                       fontsize=font_size*0.8,  # 调整字体大小
                       color='white',
                       horizontalalignment='center',
                       verticalalignment='center',
                       transform=ax.transAxes,
                       family=chinese_font)
            else:
                # 如果没有找到合适的中文字体，尝试用sans-serif字体族
                ax.text(0.5, 0.5, text, 
                       fontsize=font_size*0.8,  # 调整字体大小
                       color='white',
                       horizontalalignment='center',
                       verticalalignment='center',
                       transform=ax.transAxes,
                       family='sans-serif')
                if self.debug:
                    self.logger.warning("未找到中文字体，使用sans-serif族")
            
            # 移除坐标轴和边框
            ax.axis('off')
            for spine in ax.spines.values():
                spine.set_visible(False)
            
            # 调整边距
            plt.tight_layout(pad=0.5)
            
            # 将图形转换为图像
            buf = io.BytesIO()
            plt.savefig(buf, format='png', 
                       bbox_inches='tight',
                       pad_inches=0.2,
                       facecolor='none',
                       edgecolor='none',
                       transparent=True)
            plt.close(fig)
            
            # 读取图像数据
            buf.seek(0)
            img = cv2.imdecode(np.frombuffer(buf.read(), np.uint8), cv2.IMREAD_UNCHANGED)
            
            # 处理透明通道 (BGRA -> RGB)
            if img.shape[2] == 4:  # BGRA
                # 创建一个与黑板背景颜色匹配的画布
                canvas = np.ones((img.shape[0], img.shape[1], 3), dtype=np.uint8) * np.array([30, 30, 30], dtype=np.uint8)
                
                # 提取透明通道作为蒙版
                alpha = img[:, :, 3] / 255.0
                
                # 只将非透明部分（文本）渲染为白色
                for c in range(3):  # RGB通道
                    canvas[:, :, c] = canvas[:, :, c] * (1 - alpha) + 255 * alpha
                
                # 检查是否需要缩放图像
                max_width = 800  # 最大宽度
                max_height = 600  # 最大高度
                
                h, w = canvas.shape[:2]
                if self.debug:
                    self.logger.info(f"文本原始图像大小: {w}x{h}")
                
                # 如果图像太大，进行等比例缩放
                if w > max_width or h > max_height:
                    scale = min(max_width / w, max_height / h)
                    new_w = int(w * scale)
                    new_h = int(h * scale)
                    canvas = cv2.resize(canvas, (new_w, new_h), interpolation=cv2.INTER_AREA)
                    if self.debug:
                        self.logger.info(f"文本缩放后图像大小: {new_w}x{new_h}")
                
                return canvas
            else:
                return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                
        except Exception as e:
            self.logger.error(f"渲染文本时出错: {str(e)}")
            # 创建一个默认图像 - 使用OpenCV渲染文本（无中文支持）
            img = np.zeros((100, max(len(text) * 20, 200), 3), dtype=np.uint8)
            cv2.putText(img, "Text Error", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            return img

    def _render_geometry(self, geometry_data: Dict[str, Any], progress: float = 1.0, scale_factor: float = 1.0) -> np.ndarray:
        """
        渲染几何图形
        
        Args:
            geometry_data: 包含多个形状的字典，每个形状都有path和style属性
            progress: 渲染进度（0-1）
            scale_factor: 缩放因子
            
        Returns:
            渲染后的画布
        """
        try:
            # 创建透明画布
            img_size = 512
            canvas = np.zeros((img_size, img_size, 4), dtype=np.uint8)  # 使用RGBA格式
            
            if not isinstance(geometry_data, dict):
                raise ValueError("几何数据必须是字典类型")
            
            # 遍历所有形状
            for shape_name, shape_data in geometry_data.items():
                if not isinstance(shape_data, dict) or 'path' not in shape_data:
                    continue
                
                # 解析SVG路径
                commands = self._parse_svg_path(shape_data['path'])
                if not commands:
                    continue
                
                # 计算边界框
                bbox = self._calculate_bbox(commands)
                if not bbox:
                    continue
                
                # 计算变换参数
                scale, offset_x, offset_y = self._calculate_transform(bbox, (img_size, img_size), scale_factor)
                transformed_commands = self._transform_commands(commands, scale, offset_x, offset_y)
                
                # 获取样式信息
                style = shape_data.get('style', {})
                stroke_color = (255, 255, 255, 255)  # 白色，完全不透明
                stroke_width = int(style.get('stroke-width', 2))
                
                # 收集所有点用于填充
                points = []
                last_pos = None
                
                # 渲染路径
                for i, cmd in enumerate(transformed_commands):
                    if cmd['command'] == 'M':
                        last_pos = (int(cmd['x']), int(cmd['y']))
                        points.append(last_pos)
                    elif cmd['command'] == 'L' and last_pos is not None:
                        end_pos = (int(cmd['x']), int(cmd['y']))
                        # 计算当前线段是否应该被渲染
                        segment_progress = (i + 1) / len(transformed_commands)
                        if segment_progress <= progress:
                            cv2.line(canvas, last_pos, end_pos, stroke_color, stroke_width)
                        points.append(end_pos)
                        last_pos = end_pos
                    elif cmd['command'] == 'Z' and last_pos is not None and points:
                        # 闭合路径
                        segment_progress = (i + 1) / len(transformed_commands)
                        if segment_progress <= progress:
                            cv2.line(canvas, last_pos, points[0], stroke_color, stroke_width)
                
                # 如果有足够的点来形成一个闭合路径，添加填充效果
                if len(points) >= 3:
                    mask = np.zeros((img_size, img_size), dtype=np.uint8)
                    points_array = np.array(points, dtype=np.int32)
                    cv2.fillPoly(mask, [points_array], 255)
                    
                    # 使用半透明填充
                    fill_alpha = 64  # 填充的透明度
                    canvas[mask == 255, 3] = np.maximum(canvas[mask == 255, 3], fill_alpha)
                    
                    # 重新绘制边界线，使用抗锯齿
                    for j in range(len(points)):
                        p1 = points[j]
                        p2 = points[(j + 1) % len(points)]
                        cv2.line(canvas, p1, p2, stroke_color, stroke_width)
            
            return canvas
            
        except Exception as e:
            self.logger.error(f"渲染几何图形时出错: {str(e)}")
            error_img = np.zeros((512, 512, 4), dtype=np.uint8)  # 创建透明错误图像
            cv2.putText(error_img, "Geometry Error", (10, 256), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255, 255), 2)
            return error_img

    def _render_partial_geometry(self, svg_path: Dict[str, Any], progress: float = 1.0, scale_factor: float = 1.0) -> np.ndarray:
        """
        渲染部分几何图形
        
        Args:
            svg_path: 包含多个形状的字典，每个形状都有path和style属性
            progress: 渲染进度（0-1）
            scale_factor: 缩放因子
            
        Returns:
            渲染后的画布
        """
        try:
            # 创建画布
            canvas_size = 512
            canvas = np.full((canvas_size, canvas_size, 3), 64, dtype=np.uint8)
            
            if not isinstance(svg_path, dict):
                raise ValueError("几何数据必须是字典类型")
            
            # 遍历所有形状
            for shape_name, shape_data in svg_path.items():
                if not isinstance(shape_data, dict) or 'path' not in shape_data:
                    continue
                    
                # 解析SVG路径
                commands = self._parse_svg_path(shape_data['path'])
                if not commands:
                    continue
            
            # 计算边界框
                bbox = self._calculate_bbox(commands)
                if not bbox:
                    continue
                    
                # 计算变换参数
                scale, offset_x, offset_y = self._calculate_transform(bbox, (canvas_size, canvas_size), scale_factor)
                transformed_commands = self._transform_commands(commands, scale, offset_x, offset_y)
                
                # 获取样式信息
                style = shape_data.get('style', {})
                stroke_color = (255, 255, 255)  # 默认白色
                stroke_width = int(style.get('stroke-width', 2))
                
                # 根据进度渲染路径
                last_pos = None
                for i, cmd in enumerate(transformed_commands):
                    if cmd['command'] == 'M':
                        last_pos = (int(cmd['x']), int(cmd['y']))
                    elif cmd['command'] == 'L' and last_pos is not None:
                        end_pos = (int(cmd['x']), int(cmd['y']))
                        # 计算当前线段是否应该被渲染
                        segment_progress = (i + 1) / len(transformed_commands)
                        if segment_progress <= progress:
                            cv2.line(canvas, last_pos, end_pos, stroke_color, stroke_width)
                        last_pos = end_pos
                    elif cmd['command'] == 'Z' and last_pos is not None:
                        # 找到路径的起始点
                        for start_cmd in transformed_commands:
                            if start_cmd['command'] == 'M':
                                start_pos = (int(start_cmd['x']), int(start_cmd['y']))
                                segment_progress = (i + 1) / len(transformed_commands)
                                if segment_progress <= progress:
                                    cv2.line(canvas, last_pos, start_pos, stroke_color, stroke_width)
                    break
                
            return canvas
            
        except Exception as e:
            self.logger.error(f"渲染部分几何图形时出错: {str(e)}")
            self.logger.error(f"Traceback (most recent call last):\n{traceback.format_exc()}")
            # 返回带有错误信息的画布
            cv2.putText(canvas, "Geometry Error", (10, canvas.shape[0]//2), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            return canvas

    def _parse_svg_path(self, svg_path: str) -> List[Dict[str, Any]]:
        """
        解析SVG路径命令
        
        Args:
            svg_path: SVG路径字符串
            
        Returns:
            解析后的命令列表
        """
        try:
            if not isinstance(svg_path, str):
                raise ValueError("SVG路径必须是字符串类型")
            
            # 使用正则表达式匹配命令和参数
            pattern = r'([MLZmlz])([^MLZmlz]*)'
            commands = []
            
            for match in re.finditer(pattern, svg_path):
                cmd, params = match.groups()
                # 提取数字参数
                numbers = [float(n) for n in params.strip().split()]
                
                if cmd in ['M', 'm']:  # 移动命令
                    commands.append({
                        'command': cmd.upper(),
                        'x': numbers[0],
                        'y': numbers[1]
                    })
                elif cmd in ['L', 'l']:  # 直线命令
                    commands.append({
                        'command': cmd.upper(),
                        'x': numbers[0],
                        'y': numbers[1]
                    })
                elif cmd in ['Z', 'z']:  # 闭合路径命令
                    commands.append({
                        'command': 'Z'
                    })
                
            return commands
            
        except Exception as e:
            self.logger.error(f"解析SVG路径时出错: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return []

    def _calculate_bbox(self, commands: List[Dict[str, Any]]) -> Tuple[float, float, float, float]:
        """
        计算SVG路径命令列表的边界框
        
        Args:
            commands: SVG路径命令列表
            
        Returns:
            (min_x, min_y, max_x, max_y)的元组
        """
        if not commands:
            return (0, 0, 0, 0)
        
        points = []
        for cmd in commands:
            if cmd['command'] in ['M', 'L']:
                points.append((cmd['x'], cmd['y']))
            
        if not points:
            return (0, 0, 0, 0)
        
        min_x = min(p[0] for p in points)
        min_y = min(p[1] for p in points)
        max_x = max(p[0] for p in points)
        max_y = max(p[1] for p in points)
        
        return (min_x, min_y, max_x, max_y)

    def _calculate_transform(self, bbox: Tuple[float, float, float, float], canvas_size: Tuple[int, int], scale_factor: float = 1.0) -> Tuple[float, float, float]:
        """
        计算几何图形的变换参数（缩放和偏移）
        
        Args:
            bbox: 边界框元组 (min_x, min_y, max_x, max_y)
            canvas_size: 画布大小元组 (width, height)
            scale_factor: 额外的缩放因子，默认为1.0
            
        Returns:
            (scale, offset_x, offset_y) 元组
        """
        # 提取画布尺寸
        canvas_width, canvas_height = canvas_size
        
        # 计算边界框的宽度和高度
        bbox_width = bbox[2] - bbox[0]
        bbox_height = bbox[3] - bbox[1]
        
        if bbox_width == 0 or bbox_height == 0:
            return 1.0, 0, 0
        
        # 计算基础缩放因子
        scale_x = (canvas_width * 0.8) / bbox_width  # 留出10%的边距
        scale_y = (canvas_height * 0.8) / bbox_height
        base_scale = min(scale_x, scale_y)
        
        # 应用额外的缩放因子
        final_scale = base_scale * scale_factor
        
        # 计算居中偏移
        scaled_width = bbox_width * final_scale
        scaled_height = bbox_height * final_scale
        offset_x = (canvas_width - scaled_width) / 2 - bbox[0] * final_scale
        offset_y = (canvas_height - scaled_height) / 2 - bbox[1] * final_scale
        
        return final_scale, offset_x, offset_y

    def _transform_commands(self, commands: List[Dict[str, Any]], scale: float, offset_x: float, offset_y: float) -> List[Dict[str, Any]]:
        """
        对SVG命令应用变换（缩放和偏移）
        
        Args:
            commands: SVG命令列表
            scale: 缩放因子
            offset_x: X轴偏移
            offset_y: Y轴偏移
            
        Returns:
            变换后的命令列表
        """
        transformed = []
        for cmd in commands:
            if cmd['command'] in ['M', 'L']:
                transformed.append({
                    'command': cmd['command'],
                    'x': cmd['x'] * scale + offset_x,
                    'y': cmd['y'] * scale + offset_y
                })
            elif cmd['command'] == 'Z':
                transformed.append({'command': 'Z'})
        return transformed

    def _compress_video(self, input_path: str) -> None:
        """使用ffmpeg压缩视频"""
        try:
            # 获取输入文件的目录和文件名
            input_dir = os.path.dirname(input_path)
            input_filename = os.path.basename(input_path)
            filename_without_ext = os.path.splitext(input_filename)[0]
            
            # 创建临时输出文件路径
            temp_output_path = os.path.join(input_dir, f"{filename_without_ext}_compressed.mp4")
            
            # 构建ffmpeg命令
            command = [
                'ffmpeg',
                '-i', input_path,
                '-c:v', 'libx264',
                '-preset', 'medium',
                '-crf', '23',
                '-y',
                temp_output_path
            ]
            
            # 执行ffmpeg命令
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = process.communicate()
            
            if process.returncode == 0:
                # 压缩成功，替换原文件
                os.replace(temp_output_path, input_path)
                self.logger.info("视频压缩完成")
            else:
                self.logger.error(f"视频压缩失败: {stderr.decode()}")
                
        except Exception as e:
            self.logger.error(f"压缩视频时出错: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())


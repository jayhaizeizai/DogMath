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
import math

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
                        content = self._render_text(element['content'], element.get('font_size', 32))
                    elif element_type == 'formula':
                        content = self._render_formula(element['content'], element.get('font_size', 32))
                    elif element_type == 'geometry':
                        content = self._render_geometry(element['content'], scale_factor=element.get('scale', 1.0))
                    
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
                            'z_index': self._get_z_index(element_type)
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
                            self._blend_image_to_frame(frame, item['content'], pos_x, pos_y, alpha)
                    
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
    
    def _blend_image_to_frame(self, frame: np.ndarray, img: np.ndarray, x: float, y: float, alpha: float = 1.0):
        """
        将图像混合到帧中
        
        Args:
            frame: 目标帧
            img: 要混合的图像
            x: x坐标（0-1的比例值）
            y: y坐标（0-1的比例值）
            alpha: 透明度
        """
        try:
            if img is None:
                return
                
            # 获取图像尺寸
            img_h, img_w = img.shape[:2]
            frame_h, frame_w = frame.shape[:2]
            
            # 将0-1的比例转换为实际像素位置
            pixel_x = int(x * frame_w)
            pixel_y = int(y * frame_h)
            
            # 计算左上角坐标（考虑图像尺寸的一半）
            x_start = pixel_x - img_w // 2
            y_start = pixel_y - img_h // 2
            
            # 确保坐标在有效范围内
            x_start = max(0, min(x_start, frame_w - img_w))
            y_start = max(0, min(y_start, frame_h - img_h))
            
            # 计算结束位置
            x_end = x_start + img_w
            y_end = y_start + img_h
            
            # 确保不超出边界
            if x_end > frame_w:
                img = img[:, :-(x_end - frame_w)]
                x_end = frame_w
            if y_end > frame_h:
                img = img[:-(y_end - frame_h), :]
                y_end = frame_h
                
            # 在开始添加日志
            if img is not None and self.debug:
                self.logger.info(f"混合图像: 位置=({x:.2f}, {y:.2f}), 尺寸={img.shape}")
                
            # 如果是RGBA图像
            if img.shape[2] == 4:
                # 提取alpha通道并应用全局alpha
                src_alpha = img[:, :, 3] / 255.0 * alpha
                src_alpha = np.expand_dims(src_alpha, axis=2)
                
                # 将源图像转换为RGB
                src_rgb = img[:, :, :3]
                
                # 提取目标区域
                dst_region = frame[y_start:y_end, x_start:x_end]
                
                # 混合图像
                blended = dst_region * (1 - src_alpha) + src_rgb * src_alpha
                frame[y_start:y_end, x_start:x_end] = blended.astype(np.uint8)
            else:
                # RGB图像的混合
                dst_region = frame[y_start:y_end, x_start:x_end]
                blended = cv2.addWeighted(dst_region, 1 - alpha, img, alpha, 0)
                frame[y_start:y_end, x_start:x_end] = blended
                
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
            logger.info(f"渲染公式: {formula}, 字体大小: {font_size}")
            # 检测是否含有中文
            has_chinese = any('\u4e00' <= c <= '\u9fff' for c in formula)
            logger.debug(f"公式是否包含中文: {has_chinese}")
            
            # 检测是否含有LaTeX格式的公式
            is_latex = '\\' in formula or '$' in formula
            logger.debug(f"公式是否为LaTeX格式: {is_latex}")
            
            # 混合内容处理（中文+LaTeX）
            if has_chinese and is_latex:
                # 分割文本和LaTeX公式
                components = re.split(r'(\$[^$]*\$)', formula)
                logger.debug(f"分割后的组件: {components}")
                
                # 处理多个LaTeX部分
                rendered_parts = []
                
                for comp in components:
                    if comp.strip():  # 忽略空字符串
                        if comp.startswith('$') and comp.endswith('$'):
                            # 渲染LaTeX部分
                            latex_img = self._render_latex_as_image(comp, font_size, skip_scaling=True)
                            rendered_parts.append(latex_img)
                            logger.debug(f"渲染LaTeX部分: {comp}, 大小: {latex_img.shape}")
                        else:
                            # 渲染中文部分
                            chinese_img = self._render_text_as_image(comp, font_size)
                            rendered_parts.append(chinese_img)
                            logger.debug(f"渲染中文部分: {comp}, 大小: {chinese_img.shape}")
                
                # 计算总宽度和最大高度
                total_width = sum(img.shape[1] for img in rendered_parts) + 5 * (len(rendered_parts) - 1)
                max_height = max(img.shape[0] for img in rendered_parts)
                logger.debug(f"组合图像总宽度: {total_width}, 最大高度: {max_height}")
                
                # 创建组合图像
                combined_img = np.ones((max_height, total_width, 3), dtype=np.uint8) * np.array([30, 30, 30], dtype=np.uint8)
                
                # 放置各个部分
                x_offset = 0
                for img in rendered_parts:
                    # 如果使用了裁剪功能，保留它
                    # img = self._trim_image(img)  # 保留此行如果已实现裁剪功能
                    
                    h, w = img.shape[:2]
                    y_offset = (max_height - h) // 2
                    combined_img[y_offset:y_offset+h, x_offset:x_offset+w] = img
                    x_offset += w + 5  # 恢复为5像素的间隔
                    logger.debug(f"放置图像部分，当前x_offset: {x_offset}")
                
                # 检查是否需要缩放最终图像
                max_width = 800
                max_img_height = 600
                
                h, w = combined_img.shape[:2]
                if self.debug:
                    self.logger.info(f"组合公式原始图像大小: {w}x{h}")
                
                # 如果图像太大，进行等比例缩放
                if w > max_width or h > max_img_height:
                    scale = min(max_width / w, max_height / h)
                    new_w = int(w * scale)
                    new_h = int(h * scale)
                    combined_img = cv2.resize(combined_img, (new_w, new_h), interpolation=cv2.INTER_AREA)
                    if self.debug:
                        self.logger.info(f"组合公式缩放后图像大小: {new_w}x{new_h}")
                
                # 裁剪图像
                combined_img = self._trim_image(combined_img)
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
            logger.error(f"渲染公式时出错: {str(e)}")
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
            logger.info(f"渲染文本: {text}, 字体大小: {font_size}")
            
            # 动态计算画布大小
            text_length = len(text)
            # 中文字符通常需要更多空间
            has_chinese = any('\u4e00' <= c <= '\u9fff' for c in text)
            width_factor = 0.4 if has_chinese else 0.25
            # 根据文本长度和字体大小动态计算宽度
            fig_width = min(max(text_length * width_factor, 2), 10)
            # 根据字体大小调整高度
            fig_height = min(max(font_size / 40, 1), 3)
            
            # 创建matplotlib图形，使用动态大小
            fig = plt.figure(figsize=(fig_width, fig_height), dpi=200, facecolor='none')
            ax = fig.add_subplot(111)
            
            # 设置背景完全透明
            fig.patch.set_alpha(0.0)
            ax.set_facecolor((0, 0, 0, 0))
            ax.patch.set_alpha(0.0)
            
            # 尝试检测可用的中文字体
            chinese_font = None
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
                       pad_inches=0.05,
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
                
                # 裁剪图像
                canvas = self._trim_image(canvas)
                return canvas
            else:
                return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                
        except Exception as e:
            logger.error(f"渲染文本为图像时出错: {str(e)}")
            # 创建一个默认图像
            img = np.zeros((100, max(len(text) * 20, 200), 3), dtype=np.uint8)
            cv2.putText(img, "Text Error", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            return img
            
    def _render_latex_as_image(self, latex: str, font_size: int = 24, skip_scaling: bool = False) -> np.ndarray:
        """
        将LaTeX公式渲染为图像
        
        Args:
            latex: LaTeX公式字符串
            font_size: 字体大小
            skip_scaling: 是否跳过缩放
            
        Returns:
            渲染后的图像
        """
        try:
            logger.info(f"渲染LaTeX公式: {latex}, 字体大小: {font_size}")
            
            # 动态计算画布大小
            content = latex.strip('$')
            
            # 检测特殊结构需要更宽的画布
            has_fraction = '\\frac' in content
            has_matrix = 'matrix' in content
            has_align = 'align' in content
            
            # 基本宽度系数
            width_factor = 0.25
            # 根据特殊结构增加宽度
            if has_fraction: width_factor += 0.1
            if has_matrix: width_factor += 0.3
            if has_align: width_factor += 0.2
            
            # 计算宽度，长公式给更宽的空间
            content_length = len(content)
            fig_width = min(max(content_length * width_factor, 2), 12)
            
            # 公式通常需要更多垂直空间，特别是分数和矩阵
            fig_height = min(max(font_size / 30, 1.5), 4)
            if has_fraction or has_matrix:
                fig_height = min(fig_height * 1.5, 5)
            
            # 创建matplotlib图形，使用动态大小
            fig = plt.figure(figsize=(fig_width, fig_height), dpi=200, facecolor='none')
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
                        pad_inches=0.05,
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
                
                # 裁剪图像
                canvas = self._trim_image(canvas)
                
                # 检查是否需要缩放图像
                if not skip_scaling:  # 添加此条件
                    max_width = 800  # 最大宽度
                    max_height = 600  # 最大高度
                    
                    h, w = canvas.shape[:2]
                    logger.debug(f"LaTeX公式原始图像大小: {w}x{h}")
                    
                    # 如果图像太大，进行等比例缩放
                    if w > max_width or h > max_height:
                        scale = min(max_width / w, max_height / h)
                        new_w = int(w * scale)
                        new_h = int(h * scale)
                        canvas = cv2.resize(canvas, (new_w, new_h), interpolation=cv2.INTER_AREA)
                        logger.debug(f"LaTeX公式缩放后图像大小: {new_w}x{new_h}")
                
                return canvas
            else:
                return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                
        except Exception as e:
            logger.error(f"渲染LaTeX公式时出错: {latex}")
            logger.error(str(e))
            import traceback
            logger.error(traceback.format_exc())
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
                       pad_inches=0.05,
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
                
                # 裁剪图像
                canvas = self._trim_image(canvas)
                
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
            logger.error(f"渲染文本时出错: {str(e)}")
            # 创建一个默认图像 - 使用OpenCV渲染文本（无中文支持）
            img = np.zeros((100, max(len(text) * 20, 200), 3), dtype=np.uint8)
            cv2.putText(img, "Text Error", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            return img

    def _render_geometry(self, geometry_data: Dict[str, Any], progress: float = 1.0, scale_factor: float = 1.0) -> np.ndarray:
        """
        渲染几何图形
        """
        try:
            # 创建透明画布
            img_size = 400
            canvas = np.zeros((img_size, img_size, 4), dtype=np.uint8)
            
            if not isinstance(geometry_data, dict):
                raise ValueError("几何数据必须是字典类型")
            
            # 首先解析所有形状，计算整体边界框
            shapes_commands = {}
            combined_bbox = None
            
            # 第一遍：解析所有形状并计算统一边界框
            for shape_name, shape_data in geometry_data.items():
                if not isinstance(shape_data, dict) or 'path' not in shape_data:
                    continue
                    
                path_str = shape_data['path']
                self.logger.info(f"处理SVG路径: {path_str}")
                
                commands = self._parse_svg_path(path_str)
                if not commands:
                    continue
                    
                shapes_commands[shape_name] = commands
                
                # 计算当前形状的边界框
                bbox = self._calculate_bbox(commands)
                if not bbox:
                    continue
                    
                self.logger.info(f"形状'{shape_name}'的边界框: {bbox}")
                
                # 更新组合边界框
                if combined_bbox is None:
                    combined_bbox = bbox
                else:
                    combined_bbox = (
                        min(combined_bbox[0], bbox[0]),
                        min(combined_bbox[1], bbox[1]),
                        max(combined_bbox[2], bbox[2]),
                        max(combined_bbox[3], bbox[3])
                    )
            
            # 确保我们有有效的边界框
            if combined_bbox is None:
                self.logger.warning("没有找到有效的几何图形边界框")
                return canvas
            
            self.logger.info(f"所有几何形状的组合边界框: {combined_bbox}")
            
            # 计算统一的变换参数
            scale, offset_x, offset_y = self._calculate_transform(
                combined_bbox, (img_size, img_size), scale_factor
            )
            self.logger.info(f"统一变换参数: scale={scale}, offset_x={offset_x}, offset_y={offset_y}")
            
            # 第二遍：使用统一变换参数渲染所有形状
            for shape_name, commands in shapes_commands.items():
                # 应用统一变换
                transformed_commands = self._transform_commands(commands, scale, offset_x, offset_y)
                
                # 获取样式信息
                shape_data = geometry_data[shape_name]
                style = shape_data.get('style', {})
                stroke_color = (255, 255, 255, 255)  # 白色
                stroke_width = int(style.get('stroke-width', 2))
                
                # 渲染路径
                last_pos = None
                for cmd in transformed_commands:
                    if cmd['command'] == 'M':
                        last_pos = (int(cmd['x']), int(cmd['y']))
                    elif cmd['command'] == 'L' and last_pos is not None:
                        end_pos = (int(cmd['x']), int(cmd['y']))
                        # 使用抗锯齿
                        cv2.line(canvas, last_pos, end_pos, stroke_color, stroke_width, cv2.LINE_AA)
                        last_pos = end_pos
                    elif cmd['command'] == 'Z' and last_pos is not None and len(transformed_commands) > 0:
                        # 闭合路径
                        for start_cmd in transformed_commands:
                            if start_cmd['command'] == 'M':
                                start_pos = (int(start_cmd['x']), int(start_cmd['y']))
                                cv2.line(canvas, last_pos, start_pos, stroke_color, stroke_width, cv2.LINE_AA)
                                break
            
            return canvas
            
        except Exception as e:
            self.logger.error(f"渲染几何图形时出错: {str(e)}")
            self.logger.error(traceback.format_exc())
            # 返回错误图像
            canvas = np.zeros((img_size, img_size, 4), dtype=np.uint8)
            cv2.putText(canvas, "Geometry Error", (50, img_size//2), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255, 255), 2)
            return canvas

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
            
            # 更新正则表达式以匹配更多命令类型，包括弧形命令a
            pattern = r'([MLZAamlz])([^MLZAamlz]*)'
            commands = []
            
            # 检测是否是圆形路径
            is_circle = "a 40 40 0 1 0 80 0 a 40 40 0 1 0 -80 0" in svg_path
            
            # 如果是完整圆，直接使用参数方程生成更平滑的圆
            if is_circle:
                self.logger.info("检测到完整圆形路径，使用参数方程生成")
                # 假设圆心在(50,50)，半径为40
                center_x, center_y = 50, 50
                radius = 40
                # 生成24个点的平滑圆
                num_points = 24
                
                # 第一个点
                commands.append({
                    'command': 'M',
                    'x': center_x + radius,
                    'y': center_y
                })
                
                # 其余点
                for i in range(1, num_points):
                    angle = 2 * 3.14159 * i / num_points
                    x = center_x + radius * math.cos(angle)
                    y = center_y + radius * math.sin(angle)
                    commands.append({
                        'command': 'L',
                        'x': x,
                        'y': y
                    })
                
                # 闭合路径
                commands.append({
                    'command': 'Z'
                })
                
                self.logger.info(f"生成平滑圆形，中心=({center_x}, {center_y})，半径={radius}，点数={num_points}")
                return commands
            
            # 常规SVG路径解析
            current_pos = [0, 0]
            self.logger.info(f"开始解析SVG路径: {svg_path}")
            
            for match in re.finditer(pattern, svg_path):
                cmd = match.group(1)
                params = match.group(2).strip()
                
                self.logger.info(f"检测到命令: {cmd}, 参数: {params}")
                
                # 提取数字参数
                numbers = [float(n) for n in params.strip().split()]
                
                if cmd in ['M', 'm']:  # 移动命令
                    if len(numbers) >= 2:
                        x, y = numbers[0], numbers[1]
                        if cmd == 'm':  # 相对坐标
                            x += current_pos[0]
                            y += current_pos[1]
                        current_pos = [x, y]
                        commands.append({
                            'command': 'M',
                            'x': x,
                            'y': y
                        })
                        self.logger.info(f"添加移动命令(M) 到 ({x}, {y})")
                
                elif cmd in ['L', 'l']:  # 直线命令
                    if len(numbers) >= 2:
                        x, y = numbers[0], numbers[1]
                        if cmd == 'l':  # 相对坐标
                            x += current_pos[0]
                            y += current_pos[1]
                        current_pos = [x, y]
                        commands.append({
                            'command': 'L',
                            'x': x,
                            'y': y
                        })
                        self.logger.info(f"添加直线命令(L) 到 ({x}, {y})")
                
                elif cmd in ['Z', 'z']:  # 闭合路径命令
                    commands.append({
                        'command': 'Z'
                    })
                    self.logger.info(f"添加闭合命令(Z)")
                
                elif cmd in ['A', 'a']:  # 弧形命令 - 使用多个线段近似
                    if len(numbers) >= 7:
                        rx, ry = numbers[0], numbers[1]
                        x_axis_rotation = numbers[2]
                        large_arc_flag = int(numbers[3])
                        sweep_flag = int(numbers[4])
                        x, y = numbers[5], numbers[6]
                        
                        self.logger.info(f"处理弧形命令(A/a): rx={rx}, ry={ry}, 终点=({x}, {y})")
                        
                        if cmd == 'a':  # 相对坐标
                            x += current_pos[0]
                            y += current_pos[1]
                        
                        # 简化：使用多个点近似圆弧
                        # 创建8-12个中间点来近似圆弧
                        num_segments = 12
                        self.logger.info(f"将弧形分为{num_segments}段，从({current_pos[0]}, {current_pos[1]})到({x}, {y})")
                        
                        # 计算起点和终点之间的直线距离
                        dx = x - current_pos[0]
                        dy = y - current_pos[1]
                        
                        # 对于每个线段，添加一个控制点
                        for i in range(1, num_segments):
                            t = i / num_segments
                            # 这只是一个简单的线性插值，可以使用更复杂的贝塞尔曲线近似
                            ix = current_pos[0] + dx * t
                            iy = current_pos[1] + dy * t
                            
                            # 加入凸度来模拟圆弧
                            # 这是一个简单的近似，不完全准确但视觉上会更接近圆弧
                            bulge = min(rx, ry) * 0.5
                            mid_x = (current_pos[0] + x) / 2
                            mid_y = (current_pos[1] + y) / 2
                            
                            # 垂直于直线的方向
                            perpendicular_x = -dy
                            perpendicular_y = dx
                            
                            # 归一化
                            length = (perpendicular_x**2 + perpendicular_y**2)**0.5
                            if length > 0:
                                perpendicular_x /= length
                                perpendicular_y /= length
                                
                                # 调整点的位置，使其向外凸出形成圆弧
                                # 根据距离中点的远近调整凸出量
                                dist_from_mid = ((ix - mid_x)**2 + (iy - mid_y)**2)**0.5
                                max_dist = ((current_pos[0] - mid_x)**2 + (current_pos[1] - mid_y)**2)**0.5
                                
                                if max_dist > 0:
                                    # 创建弧形效果 - 这里是关键部分
                                    if sweep_flag == 0:
                                        bulge_factor = -(1 - (dist_from_mid / max_dist)**2) * bulge
                                    else:
                                        bulge_factor = (1 - (dist_from_mid / max_dist)**2) * bulge
                                    
                                    ix += perpendicular_x * bulge_factor
                                    iy += perpendicular_y * bulge_factor
                                    
                                    self.logger.info(f"添加弧形插值点 {i}/{num_segments}: ({ix}, {iy}) 凸度: {bulge_factor}")
                                    commands.append({
                                        'command': 'L',
                                        'x': ix,
                                        'y': iy
                                    })
                        
                        # 添加终点
                        commands.append({
                            'command': 'L',
                            'x': x,
                            'y': y
                        })
                        self.logger.info(f"添加弧形终点: ({x}, {y})")
                        current_pos = [x, y]
            
            self.logger.info(f"SVG路径解析完成，共生成{len(commands)}个命令点")
            return commands
            
        except Exception as e:
            self.logger.error(f"解析SVG路径时出错: {str(e)}")
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
        """
        # 提取画布尺寸
        canvas_width, canvas_height = canvas_size
        
        # 计算边界框的宽度和高度
        bbox_width = bbox[2] - bbox[0]
        bbox_height = bbox[3] - bbox[1]
        
        # 防止极端情况
        if bbox_width < 1:
            bbox_width = 1
        if bbox_height < 1:
            bbox_height = 1
        
        # 计算基础缩放因子
        scale_x = (canvas_width * 0.8) / bbox_width  # 留出10%的边距
        scale_y = (canvas_height * 0.8) / bbox_height
        base_scale = min(scale_x, scale_y)
        
        # 限制最大缩放倍数
        MAX_SCALE = 10.0
        if base_scale > MAX_SCALE:
            base_scale = MAX_SCALE
        
        # 应用额外的缩放因子
        final_scale = base_scale * scale_factor
        
        # 计算居中偏移 - 基于边界框的中心
        bbox_center_x = (bbox[0] + bbox[2]) / 2
        bbox_center_y = (bbox[1] + bbox[3]) / 2
        
        # 计算中心对齐偏移
        offset_x = canvas_width / 2 - bbox_center_x * final_scale
        offset_y = canvas_height / 2 - bbox_center_y * final_scale
        
        self.logger.info(f"边界框尺寸: {bbox_width}x{bbox_height}, 中心点: ({bbox_center_x}, {bbox_center_y})")
        self.logger.info(f"缩放计算: scale_x={scale_x}, scale_y={scale_y}, 最终缩放={final_scale}")
        self.logger.info(f"偏移计算: offset_x={offset_x}, offset_y={offset_y}")
        
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

    def _get_z_index(self, element_type: str) -> int:
        """
        获取元素的z-index值
        
        Args:
            element_type: 元素类型
            
        Returns:
            z-index值
        """
        z_index_map = {
            'text': 1,
            'formula': 2,
            'geometry': 3
        }
        return z_index_map.get(element_type, 0)

    def _trim_image(self, img):
        """
        裁剪图像，只保留非背景部分
        
        Args:
            img: 输入图像 (RGB或RGBA)
            
        Returns:
            裁剪后的图像
        """
        # 如果是RGBA图像，使用alpha通道
        if img.shape[2] == 4:
            # 寻找非透明区域
            mask = img[:,:,3] > 0
        else:
            # RGB图像，假设背景是暗色的(30,30,30)
            mask = np.any(img > 60, axis=2)
        
        # 寻找非零区域的边界
        coords = np.argwhere(mask)
        if len(coords) == 0:
            return img
        
        y_min, x_min = coords.min(axis=0)
        y_max, x_max = coords.max(axis=0)
        
        # 添加小边距(2像素)
        y_min = max(0, y_min - 2)
        x_min = max(0, x_min - 2)
        y_max = min(img.shape[0] - 1, y_max + 2)
        x_max = min(img.shape[1] - 1, x_max + 2)
        
        # 裁剪图像
        return img[y_min:y_max+1, x_min:x_max+1]


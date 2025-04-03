from typing import Dict, List, Tuple, Optional
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import logging
from loguru import logger
import matplotlib.pyplot as plt
from matplotlib import rcParams
import io
from .animations import (
    AnimationManager,
    FadeInEffect,
    FadeOutEffect,
    SlideInLeftEffect,
    SlideInRightEffect,
    HighlightEffect,
    DrawPathEffect
)
from .blackboard_texture import BlackboardTextureGenerator
from .svg_parser import SVGPathParser

class BlackboardAnimator:
    """黑板动画生成器"""
    
    def __init__(self, output_dir: str = "output"):
        """
        初始化黑板动画生成器
        
        Args:
            output_dir: 输出目录路径
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logger.bind(context="blackboard_animator")
        
        # 默认黑板背景
        self.background_color = (0, 0, 0)  # 黑色背景
        self.text_color = (255, 255, 255)  # 白色文字
        
        # 创建临时目录
        self.temp_dir = self.output_dir / "temp"
        self.temp_dir.mkdir(exist_ok=True)
        
        # 配置matplotlib
        self._setup_matplotlib()
        
        # 初始化动画管理器和纹理生成器
        self.animation_manager = AnimationManager()
        self.texture_generator = BlackboardTextureGenerator()
        self.svg_parser = SVGPathParser()
        
    def _setup_matplotlib(self):
        """配置matplotlib的LaTeX渲染设置"""
        # 设置中文字体
        plt.rcParams['font.sans-serif'] = ['SimHei']  # 用来正常显示中文标签
        plt.rcParams['axes.unicode_minus'] = False  # 用来正常显示负号
        
        # 设置LaTeX渲染器
        rcParams['text.usetex'] = True
        rcParams['text.latex.preamble'] = r'\usepackage{amsmath} \usepackage{amssymb}'
        
    def create_blackboard(self, resolution: Tuple[int, int]) -> np.ndarray:
        """
        创建黑板背景
        
        Args:
            resolution: 分辨率 (width, height)
            
        Returns:
            黑板背景图像
        """
        # 创建基础黑板
        blackboard = np.full((resolution[1], resolution[0], 3), self.background_color, dtype=np.uint8)
        
        # 生成并应用纹理
        texture = self.texture_generator.generate_texture(resolution)
        return self.texture_generator.apply_texture(blackboard, texture)
        
    def draw_text(self, 
                 image: np.ndarray,
                 text: str,
                 position: Tuple[int, int],
                 font_size: int = 32,
                 color: Tuple[int, int, int] = None,
                 animation: Optional[Dict] = None) -> np.ndarray:
        """
        在图像上绘制文本
        
        Args:
            image: 目标图像
            text: 要绘制的文本
            position: 位置 (x, y)
            font_size: 字体大小
            color: 文字颜色
            animation: 动画配置
            
        Returns:
            绘制后的图像
        """
        if color is None:
            color = self.text_color
            
        # 将OpenCV图像转换为PIL图像
        image_pil = Image.fromarray(image)
        draw = ImageDraw.Draw(image_pil)
        
        # 使用默认字体
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", font_size)
        except:
            font = ImageFont.load_default()
            
        # 绘制文本
        draw.text(position, text, font=font, fill=color)
        
        # 转换回OpenCV格式
        result = np.array(image_pil)
        
        # 应用动画效果
        if animation:
            effect = self._create_animation_effect(animation, result)
            if effect:
                self.animation_manager.add_effect(f"text_{position}", effect)
                
        return result
        
    def draw_formula(self, 
                    image: np.ndarray,
                    formula: str,
                    position: Tuple[int, int],
                    font_size: int = 32,
                    animation: Optional[Dict] = None) -> np.ndarray:
        """
        在图像上绘制LaTeX公式
        
        Args:
            image: 目标图像
            formula: LaTeX公式
            position: 位置 (x, y)
            font_size: 字体大小
            animation: 动画配置
            
        Returns:
            绘制后的图像
        """
        try:
            # 创建matplotlib图形
            fig = plt.figure(figsize=(10, 1))
            ax = fig.add_subplot(111)
            
            # 设置背景透明
            fig.patch.set_alpha(0.0)
            ax.patch.set_alpha(0.0)
            
            # 渲染公式
            ax.text(0.5, 0.5, formula, 
                   fontsize=font_size,
                   color='white',
                   horizontalalignment='center',
                   verticalalignment='center',
                   transform=ax.transAxes)
            
            # 移除坐标轴
            ax.axis('off')
            
            # 调整边距
            plt.tight_layout()
            
            # 将图形转换为图像
            buf = io.BytesIO()
            plt.savefig(buf, format='png', 
                       bbox_inches='tight',
                       pad_inches=0.1,
                       facecolor='none',
                       edgecolor='none',
                       transparent=True)
            plt.close()
            
            # 读取图像数据
            buf.seek(0)
            formula_image = Image.open(buf)
            formula_array = np.array(formula_image)
            
            # 获取公式图像的尺寸
            h, w = formula_array.shape[:2]
            
            # 计算目标位置（考虑公式图像的中心点）
            x = position[0] - w // 2
            y = position[1] - h // 2
            
            # 确保位置在图像范围内
            x = max(0, min(x, image.shape[1] - w))
            y = max(0, min(y, image.shape[0] - h))
            
            # 将公式图像合成到黑板图像上
            result = image.copy()
            if formula_array.shape[2] == 4:  # 如果有alpha通道
                alpha = formula_array[:, :, 3] / 255.0
                for c in range(3):
                    result[y:y+h, x:x+w, c] = (
                        result[y:y+h, x:x+w, c] * (1 - alpha) +
                        formula_array[:, :, c] * alpha
                    )
            else:
                result[y:y+h, x:x+w] = formula_array
                
            # 应用动画效果
            if animation:
                effect = self._create_animation_effect(animation, result)
                if effect:
                    self.animation_manager.add_effect(f"formula_{position}", effect)
                    
            return result
            
        except Exception as e:
            self.logger.error(f"LaTeX公式渲染失败: {str(e)}")
            return image
        
    def draw_geometry(self, 
                     image: np.ndarray,
                     svg_path: str,
                     position: Tuple[int, int],
                     color: Tuple[int, int, int] = None,
                     animation: Optional[Dict] = None) -> np.ndarray:
        """
        在图像上绘制几何图形
        
        Args:
            image: 目标图像
            svg_path: SVG路径数据
            position: 位置 (x, y)
            color: 线条颜色
            animation: 动画配置
            
        Returns:
            绘制后的图像
        """
        if color is None:
            color = self.text_color
            
        # 创建临时图像用于绘制
        result = image.copy()
        
        # 解析SVG路径
        try:
            # 这里需要集成SVG解析库，如svg.path或cairosvg
            # 暂时使用简单的路径绘制
            points = self._parse_svg_path(svg_path)
            if points:
                points = np.array(points, dtype=np.int32)
                cv2.polylines(result, [points], False, color, 2)
                
                # 应用动画效果
                if animation:
                    effect = DrawPathEffect(animation.get("duration", 1.0), points.tolist())
                    self.animation_manager.add_effect(f"geometry_{position}", effect)
                    
        except Exception as e:
            self.logger.error(f"几何图形绘制失败: {str(e)}")
            
        return result
        
    def _parse_svg_path(self, svg_path: str) -> List[Tuple[int, int]]:
        """
        解析SVG路径数据
        
        Args:
            svg_path: SVG路径数据字符串
            
        Returns:
            路径点列表 [(x, y), ...]
        """
        try:
            # 解析SVG路径
            points = self.svg_parser.parse_path_data(svg_path)
            
            # 标准化路径点（缩放到合适的大小）
            target_size = (100, 100)  # 默认目标大小
            normalized_points = self.svg_parser.normalize_path(points, target_size)
            
            # 转换为整数坐标
            return [(int(x), int(y)) for x, y in normalized_points]
            
        except Exception as e:
            self.logger.error(f"SVG路径解析失败: {str(e)}")
            return []
        
    def _create_animation_effect(self, animation: Dict, image: np.ndarray) -> Optional[AnimationEffect]:
        """
        创建动画效果
        
        Args:
            animation: 动画配置
            image: 目标图像
            
        Returns:
            动画效果对象
        """
        try:
            effect_type = animation.get('enter', 'fade_in')
            duration = animation.get('duration', 1.0)
            
            if effect_type == 'fade_in':
                return FadeInEffect(duration)
            elif effect_type == 'slide_in_left':
                return SlideInEffect(duration, 'left')
            elif effect_type == 'slide_in_right':
                return SlideInEffect(duration, 'right')
            elif effect_type == 'slide_in_up':
                return SlideInEffect(duration, 'up')
            elif effect_type == 'slide_in_down':
                return SlideInEffect(duration, 'down')
            elif effect_type == 'scale_in':
                return ScaleInEffect(duration)
            elif effect_type == 'rotate_in':
                return RotateInEffect(duration)
            elif effect_type == 'draw_path':
                return DrawPathEffect(duration)
            elif effect_type == 'write_text':
                return WriteTextEffect(duration)
            elif effect_type == 'bounce_in':
                return BounceInEffect(duration)
            elif effect_type == 'elastic_in':
                return ElasticInEffect(duration)
            else:
                self.logger.warning(f"未知的动画效果类型: {effect_type}")
                return None
            
        except Exception as e:
            self.logger.error(f"创建动画效果时出错: {str(e)}")
            return None

class AnimationEffect:
    """动画效果基类"""
    def __init__(self, duration: float):
        self.duration = duration
        self.progress = 0.0
        
    def update(self, delta_time: float) -> bool:
        """更新动画进度"""
        self.progress = min(1.0, self.progress + delta_time / self.duration)
        return self.progress < 1.0
        
    def apply(self, image: np.ndarray) -> np.ndarray:
        """应用动画效果"""
        raise NotImplementedError

class FadeInEffect(AnimationEffect):
    """淡入效果"""
    def apply(self, image: np.ndarray) -> np.ndarray:
        alpha = self.progress
        return cv2.addWeighted(image, alpha, np.zeros_like(image), 1 - alpha, 0)

class SlideInEffect(AnimationEffect):
    """滑入效果"""
    def __init__(self, duration: float, direction: str):
        super().__init__(duration)
        self.direction = direction
        
    def apply(self, image: np.ndarray) -> np.ndarray:
        h, w = image.shape[:2]
        offset = int((1 - self.progress) * max(h, w))
        
        if self.direction == 'left':
            return np.roll(image, -offset, axis=1)
        elif self.direction == 'right':
            return np.roll(image, offset, axis=1)
        elif self.direction == 'up':
            return np.roll(image, -offset, axis=0)
        else:  # down
            return np.roll(image, offset, axis=0)

class ScaleInEffect(AnimationEffect):
    """缩放效果"""
    def apply(self, image: np.ndarray) -> np.ndarray:
        h, w = image.shape[:2]
        scale = self.progress
        new_w = int(w * scale)
        new_h = int(h * scale)
        
        if new_w == 0 or new_h == 0:
            return image
            
        scaled = cv2.resize(image, (new_w, new_h))
        result = np.zeros_like(image)
        
        y_offset = (h - new_h) // 2
        x_offset = (w - new_w) // 2
        result[y_offset:y_offset+new_h, x_offset:x_offset+new_w] = scaled
        
        return result

class RotateInEffect(AnimationEffect):
    """旋转效果"""
    def apply(self, image: np.ndarray) -> np.ndarray:
        h, w = image.shape[:2]
        center = (w // 2, h // 2)
        angle = (1 - self.progress) * 360
        
        matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
        return cv2.warpAffine(image, matrix, (w, h))

class BounceInEffect(AnimationEffect):
    """弹跳效果"""
    def apply(self, image: np.ndarray) -> np.ndarray:
        # 使用缓动函数
        t = self.progress
        if t < 0.5:
            scale = 2 * t * t
        else:
            scale = 1 - pow(-2 * t + 2, 2) / 2
            
        h, w = image.shape[:2]
        new_w = int(w * scale)
        new_h = int(h * scale)
        
        if new_w == 0 or new_h == 0:
            return image
            
        scaled = cv2.resize(image, (new_w, new_h))
        result = np.zeros_like(image)
        
        y_offset = (h - new_h) // 2
        x_offset = (w - new_w) // 2
        result[y_offset:y_offset+new_h, x_offset:x_offset+new_w] = scaled
        
        return result

class ElasticInEffect(AnimationEffect):
    """弹性效果"""
    def apply(self, image: np.ndarray) -> np.ndarray:
        # 使用弹性缓动函数
        t = self.progress
        if t == 0:
            scale = 0
        elif t == 1:
            scale = 1
        else:
            scale = pow(2, -10 * t) * sin((t * 10 - 0.75) * (2 * pi / 3)) + 1
            
        h, w = image.shape[:2]
        new_w = int(w * scale)
        new_h = int(h * scale)
        
        if new_w == 0 or new_h == 0:
            return image
            
        scaled = cv2.resize(image, (new_w, new_h))
        result = np.zeros_like(image)
        
        y_offset = (h - new_h) // 2
        x_offset = (w - new_w) // 2
        result[y_offset:y_offset+new_h, x_offset:x_offset+new_w] = scaled
        
        return result
        
    def create_animation(self, 
                        script: Dict,
                        output_name: str) -> str:
        """
        创建黑板动画
        
        Args:
            script: 解析后的脚本数据
            output_name: 输出文件名
            
        Returns:
            生成的视频文件路径
        """
        try:
            # 获取黑板配置
            blackboard_config = script["blackboard"]
            resolution = tuple(blackboard_config["resolution"])
            fps = 30  # 默认帧率
            
            # 创建视频写入器
            output_path = self.output_dir / output_name
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(str(output_path), fourcc, fps, resolution)
            
            # 创建初始黑板
            current_frame = self.create_blackboard(resolution)
            
            # 处理每个步骤
            for step in blackboard_config["steps"]:
                # 计算该步骤的帧数
                frames = int(step["duration"] * fps)
                
                # 处理每个元素
                for element in step["elements"]:
                    element_type = element["type"]
                    content = element["content"]
                    position = tuple(int(p * resolution[i] / 100) for i, p in enumerate(element["position"]))
                    animation = element.get("animation")
                    
                    # 根据元素类型进行绘制
                    if element_type == "text":
                        current_frame = self.draw_text(
                            current_frame,
                            content,
                            position,
                            element.get("font_size", 32),
                            animation=animation
                        )
                    elif element_type == "formula":
                        current_frame = self.draw_formula(
                            current_frame,
                            content,
                            position,
                            element.get("font_size", 32),
                            animation=animation
                        )
                    elif element_type == "geometry":
                        current_frame = self.draw_geometry(
                            current_frame,
                            content,
                            position,
                            animation=animation
                        )
                        
                # 写入帧
                for _ in range(frames):
                    # 更新动画效果
                    delta_time = 1.0 / fps
                    animated_elements = self.animation_manager.update(delta_time)
                    
                    # 应用动画效果
                    frame = current_frame.copy()
                    for element_id, effect in animated_elements.items():
                        frame = effect.apply(frame)
                        
                    out.write(frame)
                    
            # 释放资源
            out.release()
            
            return str(output_path)
            
        except Exception as e:
            self.logger.error(f"创建动画时出错: {str(e)}")
            raise 
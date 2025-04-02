from typing import Dict, List, Tuple, Optional
import numpy as np
from moviepy.video.VideoClip import VideoClip, TextClip, ColorClip
from moviepy.video.compositing.CompositeVideoClip import CompositeVideoClip
from loguru import logger

class BaseEffect:
    """动画效果基类"""
    
    def __init__(self, duration: float = 1.0):
        """
        初始化动画效果
        
        Args:
            duration: 动画持续时间（秒）
        """
        self.duration = duration
        
    def create_clip(self, width: int, height: int, fps: int = 30) -> VideoClip:
        """
        创建视频片段
        
        Args:
            width: 视频宽度
            height: 视频高度
            fps: 视频帧率
            
        Returns:
            视频片段
        """
        raise NotImplementedError
        
class FadeInEffect(BaseEffect):
    """淡入效果"""
    
    def __init__(self, text: str, position: Tuple[float, float], font_size: int = 32, duration: float = 1.0):
        """
        初始化淡入效果
        
        Args:
            text: 文本内容
            position: 位置坐标
            font_size: 字体大小
            duration: 动画持续时间
        """
        super().__init__(duration)
        self.text = text
        self.position = position
        self.font_size = font_size
        self.logger = logger.bind(context="fade_in_effect")
        
    def create_clip(self, width: int, height: int, fps: int = 30) -> VideoClip:
        """创建淡入效果视频片段"""
        self.logger.info(f"创建淡入效果: text={self.text}, position={self.position}, font_size={self.font_size}")
        
        def make_frame(t):
            # 创建一个空白帧
            frame = np.zeros((height, width, 3), dtype=np.uint8)
            
            # 创建文本图像
            text_clip = TextClip(self.text, fontsize=self.font_size, color='white', font='SimHei', method='label')
            text_size = text_clip.size
            
            # 计算文本的居中位置
            x = (width - text_size[0]) // 2
            y = (height - text_size[1]) // 2
            
            self.logger.info(f"文本尺寸: {text_size[0]}x{text_size[1]}")
            self.logger.info(f"文本位置: ({x}, {y})")
            
            # 计算当前透明度
            opacity = min(1.0, t / self.duration) if self.duration > 0 else 1.0
            self.logger.info(f"当前时间: {t}秒, 透明度: {opacity}")
            
            # 将文本合成到帧上
            text_frame = text_clip.get_frame(0)
            alpha = text_frame[:, :, 3] if text_frame.shape[2] == 4 else np.ones(text_frame.shape[:2])
            alpha = alpha * opacity
            
            # 确保位置有效
            x = max(0, min(x, width - text_size[0]))
            y = max(0, min(y, height - text_size[1]))
            
            # 合成文本
            self.logger.info(f"合成文本: 区域=({x}:{x+text_size[0]}, {y}:{y+text_size[1]})")
            frame[y:y+text_size[1], x:x+text_size[0]] = text_frame[:, :, :3] * alpha[..., np.newaxis]
            
            return frame
            
        return VideoClip(make_frame, duration=self.duration)
        
class FadeOutEffect(BaseEffect):
    """淡出效果"""
    
    def __init__(self, duration: float = 1.0):
        """
        初始化淡出效果
        
        Args:
            duration: 动画持续时间
        """
        super().__init__(duration)
        
    def create_clip(self, width: int, height: int, fps: int = 30) -> VideoClip:
        """创建淡出效果视频片段"""
        def make_frame(t):
            # 计算当前透明度
            alpha = max(0.0, 1.0 - t / self.duration)
            
            # 创建透明帧
            frame = np.zeros((height, width, 3), dtype=np.uint8)
            
            # 根据透明度调整亮度
            frame[:, :] = [int(255 * alpha)] * 3
            
            return frame
            
        return VideoClip(make_frame, duration=self.duration)
        
class SlideInLeftEffect(BaseEffect):
    """从左侧滑入效果"""
    
    def __init__(self, text: str, position: Tuple[float, float], font_size: int = 32, duration: float = 1.0):
        """
        初始化从左侧滑入效果
        
        Args:
            text: 文本内容
            position: 目标位置坐标
            font_size: 字体大小
            duration: 动画持续时间
        """
        super().__init__(duration)
        self.text = text
        self.position = position
        self.font_size = font_size
        
    def create_clip(self, width: int, height: int, fps: int = 30) -> VideoClip:
        """创建从左侧滑入效果视频片段"""
        def make_frame(t):
            # 计算当前位置
            progress = min(1.0, t / self.duration)
            
            # 创建文本
            text_clip = TextClip(
                self.text,
                fontsize=self.font_size,
                color='white',
                font='SimHei',  # 使用中文字体
                size=(None, None),  # 自动调整大小
                method='label'  # 使用label方法
            )
            
            # 获取文本帧
            text_frame = text_clip.get_frame(0)  # 使用t=0因为文本内容不变
            
            # 计算文本位置
            h, w = text_frame.shape[:2]
            x = int(self.position[0] - (1 - progress) * width)
            y = int(self.position[1])
            
            # 确保位置在有效范围内
            if y < 0: y = 0
            if y + h > height: y = height - h
            
            # 创建空白帧
            frame = np.zeros((height, width, 3), dtype=np.uint8)
            
            # 计算可见部分的范围
            visible_x = max(0, x)
            visible_w = min(w, width - visible_x)
            
            if visible_w > 0:
                # 将文本合成到帧上
                frame[y:y+h, visible_x:visible_x+visible_w] = text_frame[:, :visible_w]
            
            return frame
            
        return VideoClip(make_frame, duration=self.duration)
        
class DrawPathEffect(BaseEffect):
    """路径绘制效果"""
    
    def __init__(self, points: List[Tuple[float, float]], duration: float = 1.0):
        """
        初始化路径绘制效果
        
        Args:
            points: 路径点列表
            duration: 动画持续时间
        """
        super().__init__(duration)
        self.points = points
        
    def create_clip(self, width: int, height: int, fps: int = 30) -> VideoClip:
        """创建路径绘制效果视频片段"""
        def make_frame(t):
            # 创建空白帧
            frame = np.zeros((height, width, 3), dtype=np.uint8)  # 改为RGB格式
            
            # 计算当前进度
            progress = min(1.0, t / self.duration)
            num_points = int(len(self.points) * progress)
            
            if num_points < 2:
                return frame
                
            # 绘制路径
            for i in range(num_points - 1):
                p1 = self.points[i]
                p2 = self.points[i + 1]
                
                # 绘制线段
                x1, y1 = int(p1[0]), int(p1[1])
                x2, y2 = int(p2[0]), int(p2[1])
                
                # 使用Bresenham算法绘制线段
                dx = abs(x2 - x1)
                dy = abs(y2 - y1)
                x, y = x1, y1
                n = 1 + dx + dy
                x_inc = 1 if x2 > x1 else -1
                y_inc = 1 if y2 > y1 else -1
                error = dx - dy
                dx *= 2
                dy *= 2
                
                for _ in range(n):
                    if 0 <= x < width and 0 <= y < height:
                        frame[y, x] = [255, 255, 255]  # 白色（RGB格式）
                    if error > 0:
                        x += x_inc
                        error -= dy
                    else:
                        y += y_inc
                        error += dx
                        
            return frame
            
        return VideoClip(make_frame, duration=self.duration)
        
class HighlightEffect(BaseEffect):
    """高亮效果"""
    
    def __init__(self, text: str, position: Tuple[float, float], font_size: int = 32, duration: float = 1.0):
        """
        初始化高亮效果
        
        Args:
            text: 文本内容
            position: 位置坐标
            font_size: 字体大小
            duration: 动画持续时间
        """
        super().__init__(duration)
        self.text = text
        self.position = position
        self.font_size = font_size
        
    def create_clip(self, width: int, height: int, fps: int = 30) -> VideoClip:
        """创建高亮效果视频片段"""
        def make_frame(t):
            # 计算高亮强度
            intensity = 0.5 + 0.5 * np.sin(2 * np.pi * t / self.duration)
            
            # 创建文本
            text_clip = TextClip(
                self.text,
                fontsize=self.font_size,
                color='white',
                font='Arial',
                size=(width, None),
                method='caption'
            )
            
            # 设置位置
            text_clip = text_clip.set_position(self.position)
            
            # 创建高亮背景
            bg_clip = ColorClip(
                size=(width, height),
                color=(255, 255, 0, int(100 * intensity))  # 黄色半透明
            )
            
            # 合成帧
            frame = CompositeVideoClip([bg_clip, text_clip]).get_frame(t)
            return frame
            
        return VideoClip(make_frame, duration=self.duration)

class AnimationManager:
    """动画管理器"""
    
    def __init__(self):
        self.effects: Dict[str, BaseEffect] = {}
        
    def add_effect(self, element_id: str, effect: BaseEffect):
        """添加动画效果"""
        self.effects[element_id] = effect
        
    def update(self, delta_time: float) -> Dict[str, np.ndarray]:
        """更新所有动画效果"""
        results = {}
        finished_effects = []
        
        for element_id, effect in self.effects.items():
            progress = effect.update(delta_time)
            if effect.is_finished():
                finished_effects.append(element_id)
            else:
                results[element_id] = effect
                
        # 移除已完成的动画
        for element_id in finished_effects:
            del self.effects[element_id]
            
        return results
        
    def is_empty(self) -> bool:
        """检查是否还有正在进行的动画"""
        return len(self.effects) == 0 
import numpy as np
import cv2
from typing import Tuple
from loguru import logger

class BlackboardTextureGenerator:
    """黑板纹理生成器"""
    
    def __init__(self):
        self.logger = logger.bind(context="blackboard_texture")
        
    def generate_noise(self, size: Tuple[int, int], scale: float = 0.1) -> np.ndarray:
        """生成噪声纹理"""
        noise = np.random.normal(0, scale, size)
        return np.clip(noise, 0, 1)
        
    def generate_chalk_dust(self, size: Tuple[int, int], density: float = 0.1) -> np.ndarray:
        """生成粉笔灰效果"""
        dust = np.random.random(size) < density
        return dust.astype(np.float32)
        
    def generate_scratch_marks(self, size: Tuple[int, int], num_marks: int = 50) -> np.ndarray:
        """生成划痕效果"""
        scratches = np.zeros(size, dtype=np.float32)
        for _ in range(num_marks):
            x1, y1 = np.random.randint(0, size[0]), np.random.randint(0, size[1])
            x2, y2 = np.random.randint(0, size[0]), np.random.randint(0, size[1])
            cv2.line(scratches, (x1, y1), (x2, y2), 0.1, 1)
        return scratches
        
    def generate_texture(self, 
                        size: Tuple[int, int],
                        base_color: Tuple[int, int, int] = (0, 0, 0),
                        noise_scale: float = 0.1,
                        dust_density: float = 0.1,
                        num_scratch_marks: int = 50) -> np.ndarray:
        """生成完整的黑板纹理"""
        try:
            # 创建基础颜色
            texture = np.full((size[1], size[0], 3), base_color, dtype=np.uint8)
            
            # 添加噪声
            noise = self.generate_noise(size, noise_scale)
            texture = (texture * (1 - noise[:, :, np.newaxis])).astype(np.uint8)
            
            # 添加粉笔灰
            dust = self.generate_chalk_dust(size, dust_density)
            texture = (texture * (1 - dust[:, :, np.newaxis])).astype(np.uint8)
            
            # 添加划痕
            scratches = self.generate_scratch_marks(size, num_scratch_marks)
            texture = (texture * (1 - scratches[:, :, np.newaxis])).astype(np.uint8)
            
            # 添加轻微的模糊效果
            texture = cv2.GaussianBlur(texture, (3, 3), 0)
            
            return texture
            
        except Exception as e:
            self.logger.error(f"生成黑板纹理时出错: {str(e)}")
            return np.full((size[1], size[0], 3), base_color, dtype=np.uint8)
            
    def apply_texture(self, 
                     image: np.ndarray,
                     texture: np.ndarray,
                     strength: float = 0.1) -> np.ndarray:
        """将纹理应用到图像上"""
        return cv2.addWeighted(image, 1, texture, strength, 0) 
from typing import List, Tuple
import re
from loguru import logger

class SVGPathParser:
    """SVG路径解析器"""
    
    def __init__(self):
        """初始化SVG路径解析器"""
        self.logger = logger.bind(context="svg_parser")
        
    def parse_path_data(self, path_data: str) -> List[Tuple[float, float]]:
        """
        解析SVG路径数据
        
        Args:
            path_data: SVG路径数据
            
        Returns:
            路径点列表
        """
        # 这是一个简化版本，只处理M和L命令
        if not path_data:
            return []
            
        points = []
        # 匹配移动(M)和线(L)命令
        pattern = r'([ML])(\d+),(\d+)'
        for match in re.finditer(pattern, path_data):
            cmd = match.group(1)
            x = float(match.group(2))
            y = float(match.group(3))
            points.append((x, y))
            
        return points
        
    def normalize_path(self, points: List[Tuple[float, float]], target_size: Tuple[float, float]) -> List[Tuple[float, float]]:
        """
        归一化路径点
        
        Args:
            points: 路径点列表
            target_size: 目标尺寸
            
        Returns:
            归一化后的路径点列表
        """
        if not points:
            return []
            
        # 查找最小和最大值
        x_values = [p[0] for p in points]
        y_values = [p[1] for p in points]
        
        min_x = min(x_values) if x_values else 0
        max_x = max(x_values) if x_values else 0
        min_y = min(y_values) if y_values else 0
        max_y = max(y_values) if y_values else 0
        
        # 计算原始宽度和高度
        width = max_x - min_x
        height = max_y - min_y
        
        if width == 0 or height == 0:
            return points
            
        # 计算缩放因子
        scale_x = target_size[0] / width
        scale_y = target_size[1] / height
        
        # 应用缩放
        normalized_points = [
            ((p[0] - min_x) * scale_x, (p[1] - min_y) * scale_y)
            for p in points
        ]
        
        return normalized_points
        
    def translate_path(self, points: List[Tuple[float, float]], offset: Tuple[float, float]) -> List[Tuple[float, float]]:
        """
        平移路径点
        
        Args:
            points: 路径点列表
            offset: 偏移量
            
        Returns:
            平移后的路径点列表
        """
        return [
            (p[0] + offset[0], p[1] + offset[1])
            for p in points
        ] 
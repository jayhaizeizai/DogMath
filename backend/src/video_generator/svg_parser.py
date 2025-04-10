from typing import List, Tuple
import re
from loguru import logger
import traceback

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
        try:
            # 更全面的路径解析，支持M,L,Z,A命令和空格分隔
            points = []
            # 使用正则表达式提取命令和坐标
            pattern = r'([MLZAmlza])\s*([^MLZAmlza]*)'  # 匹配M,L,Z,A命令
            
            current_pos = (0, 0)
            start_pos = (0, 0)
            
            for match in re.finditer(pattern, path_data):
                cmd = match.group(1).upper()  # 统一转为大写处理
                params = match.group(2).strip()
                
                # 处理空格或逗号分隔的坐标
                coords = re.findall(r'[-+]?\d*\.?\d+', params)
                
                if cmd == 'M' and len(coords) >= 2:
                    x = float(coords[0])
                    y = float(coords[1])
                    current_pos = (x, y)
                    start_pos = (x, y)  # 记住起始位置
                    points.append(current_pos)
                    
                elif cmd == 'L' and len(coords) >= 2:
                    x = float(coords[0])
                    y = float(coords[1])
                    current_pos = (x, y)
                    points.append(current_pos)
                    
                elif cmd == 'A' and len(coords) >= 7:
                    # 处理弧形命令，简化为直线
                    # A rx ry x-axis-rotation large-arc-flag sweep-flag x y
                    x = float(coords[5])  # 目标x坐标
                    y = float(coords[6])  # 目标y坐标
                    # 添加中间点来模拟弧形
                    if current_pos != (0, 0):
                        # 添加几个中间点来模拟曲线
                        mid_x = (current_pos[0] + x) / 2
                        mid_y = (current_pos[1] + y) / 2
                        # 稍微偏移中间点，使其不在直线上
                        rx = float(coords[0])  # 弧形的x半径
                        offset = rx / 2
                        points.append((mid_x + offset, mid_y - offset))
                    
                    current_pos = (x, y)
                    points.append(current_pos)
                    
                elif cmd == 'Z':
                    # 闭合路径，回到起点
                    points.append(start_pos)
                    
            self.logger.info(f"解析SVG路径: {path_data} -> 生成{len(points)}个点")
            return points
            
        except Exception as e:
            self.logger.error(f"SVG路径解析失败: {str(e)}")
            self.logger.error(traceback.format_exc())
            return []
        
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
            
        # 使用较小的缩放因子，保持图形合适大小
        scale = min(target_size[0] / width, target_size[1] / height) * 0.5  # 添加0.5的缩放系数使图形更大
        
        # 应用统一缩放以保持比例
        normalized_points = [
            ((p[0] - min_x) * scale, (p[1] - min_y) * scale)
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
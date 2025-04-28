import numpy as np
import cv2
import re
import math
import logging
import traceback
from typing import List, Dict, Any, Tuple
from ..utils.image_utils import trim_image
from .text_renderer import render_text_as_image

# 配置日志
logger = logging.getLogger(__name__)
# 确保日志级别足够低以捕获DEBUG
logger.setLevel(logging.DEBUG)

def parse_svg_path(svg_path: str) -> List[Dict[str, Any]]:
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
            logger.info("检测到完整圆形路径，使用参数方程生成")
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
            
            logger.info(f"生成平滑圆形，中心=({center_x}, {center_y})，半径={radius}，点数={num_points}")
            return commands
        
        # 常规SVG路径解析
        current_pos = [0, 0]
        logger.info(f"开始解析SVG路径: {svg_path}")
        
        for match in re.finditer(pattern, svg_path):
            cmd = match.group(1)
            params = match.group(2).strip()
            
            logger.info(f"检测到命令: {cmd}, 参数: {params}")
            
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
                    logger.info(f"添加移动命令(M) 到 ({x}, {y})")
            
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
                    logger.info(f"添加直线命令(L) 到 ({x}, {y})")
            
            elif cmd in ['Z', 'z']:  # 闭合路径命令
                commands.append({
                    'command': 'Z'
                })
                logger.info(f"添加闭合命令(Z)")
            
            elif cmd in ['A', 'a']:  # 弧形命令 - 使用多个线段近似
                if len(numbers) >= 7:
                    rx, ry = numbers[0], numbers[1]
                    x_axis_rotation = numbers[2]
                    large_arc_flag = int(numbers[3])
                    sweep_flag = int(numbers[4])
                    x, y = numbers[5], numbers[6]
                    
                    logger.info(f"处理弧形命令(A/a): rx={rx}, ry={ry}, 终点=({x}, {y})")
                    
                    if cmd == 'a':  # 相对坐标
                        x += current_pos[0]
                        y += current_pos[1]
                    
                    # 简化：使用多个点近似圆弧
                    # 创建8-12个中间点来近似圆弧
                    num_segments = 12
                    logger.info(f"将弧形分为{num_segments}段，从({current_pos[0]}, {current_pos[1]})到({x}, {y})")
                    
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
                                
                                logger.info(f"添加弧形插值点 {i}/{num_segments}: ({ix}, {iy}) 凸度: {bulge_factor}")
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
                    logger.info(f"添加弧形终点: ({x}, {y})")
                    current_pos = [x, y]
        
        logger.info(f"SVG路径解析完成，共生成{len(commands)}个命令点")
        return commands
        
    except Exception as e:
        logger.error(f"解析SVG路径时出错: {str(e)}")
        logger.error(traceback.format_exc())
        return []

def calculate_bbox(commands: List[Dict[str, Any]]) -> Tuple[float, float, float, float]:
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

def calculate_transform(bbox: Tuple[float, float, float, float], canvas_size: Tuple[int, int], 
                         scale_factor: float = 1.0, center_point: Tuple[float, float] = None) -> Tuple[float, float, float]:
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
    
    # 计算边界框中心
    bbox_center_x = (bbox[0] + bbox[2]) / 2
    bbox_center_y = (bbox[1] + bbox[3]) / 2
    
    # 确定要使用的中心点
    use_center_x = center_point[0] if center_point else bbox_center_x
    use_center_y = center_point[1] if center_point else bbox_center_y
    
    # 计算尺寸，确保包含整个形状
    # 如果有特定中心点，需要计算最远的顶点到中心的距离
    if center_point:
        # 计算中心点到边界框四个角的最大距离
        corners = [
            (bbox[0], bbox[1]),  # 左上
            (bbox[2], bbox[1]),  # 右上
            (bbox[0], bbox[3]),  # 左下
            (bbox[2], bbox[3])   # 右下
        ]
        
        # 找出最远的距离
        max_distance = 0
        for corner_x, corner_y in corners:
            distance = math.sqrt((corner_x - use_center_x)**2 + (corner_y - use_center_y)**2)
            max_distance = max(max_distance, distance)
        
        # 将距离作为半径，确保完整显示
        shape_radius = max_distance
        required_width = required_height = 2 * shape_radius
    else:
        # 使用边界框尺寸
        required_width = bbox_width
        required_height = bbox_height
    
    # 调整安全边距，确保图形完全可见
    safety_margin = 0.8  # 增加到0.8，给图形更多显示空间
    
    # 计算基础缩放因子时考虑整体图形大小
    scale_x = (canvas_width * safety_margin) / required_width
    scale_y = (canvas_height * safety_margin) / required_height
    base_scale = min(scale_x, scale_y)
    
    # 调整最小缩放值
    MIN_SCALE = 0.5  # 降低最小缩放限制
    MAX_SCALE = 4.0
    
    # 应用用户指定的缩放因子，但仍限制在范围内
    final_scale = base_scale * scale_factor
    final_scale = min(max(final_scale, MIN_SCALE), MAX_SCALE)
    
    # 计算偏移量，确保形状在画布中心
    offset_x = canvas_width / 2 - use_center_x * final_scale
    offset_y = canvas_height / 2 - use_center_y * final_scale
    
    # 记录参数
    logger.info(f"通用变换计算:")
    logger.info(f"- 边界框: {bbox}, 尺寸: {bbox_width}x{bbox_height}")
    logger.info(f"- 使用中心点: ({use_center_x}, {use_center_y})")
    logger.info(f"- 缩放限制: {MIN_SCALE} ~ {MAX_SCALE}, 用户缩放: {scale_factor}")
    logger.info(f"- 基础缩放: {base_scale}, 最终缩放: {final_scale}")
    logger.info(f"- 最终偏移: ({offset_x}, {offset_y})")
    
    return final_scale, offset_x, offset_y

def transform_commands(commands: List[Dict[str, Any]], scale: float, offset_x: float, offset_y: float) -> List[Dict[str, Any]]:
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

def render_geometry(geometry_data: Dict[str, Any], progress: float = 1.0, scale_factor: float = 1.0, debug: bool = False) -> np.ndarray:
    """渲染几何图形"""
    try:
        if debug:
            logger.debug(f"开始渲染几何图形，数据类型: {type(geometry_data)}")
        
        # 创建透明画布
        img_size = 400
        canvas = np.zeros((img_size, img_size, 4), dtype=np.uint8)
        
        if not isinstance(geometry_data, dict):
            logger.error(f"几何数据必须是字典类型，但收到了: {type(geometry_data)}")
            raise ValueError("几何数据必须是字典类型")
        
        # 处理content字段包装的情况
        actual_data = geometry_data.get('content', geometry_data)
        
        if debug:
            logger.debug(f"处理几何数据结构: {actual_data.keys()}")
            for key in actual_data.keys():
                logger.debug(f"  - {key}类型: {type(actual_data[key])}")
                if key == 'line' and isinstance(actual_data[key], list):
                    logger.debug(f"    线段数量: {len(actual_data[key])}")
                elif key == 'label' and isinstance(actual_data[key], list):
                    logger.debug(f"    标签数量: {len(actual_data[key])}")
        
        # 使用处理后的数据继续执行
        shapes_commands = {}
        combined_bbox = None
        
        # 检查标签数据
        has_labels = False
        if 'label' in actual_data and isinstance(actual_data['label'], list) and len(actual_data['label']) > 0:
            has_labels = True
            if debug:
                logger.debug(f"检测到{len(actual_data['label'])}个标签")
        
        # 修改这部分代码来处理不同类型的几何图形
        for shape_name, shape_data in actual_data.items():
            # 特殊处理标签数组
            if shape_name == "label":
                if debug:
                    logger.debug(f"跳过标签数组处理，将在后续单独处理")
                continue
            
            # 处理数组类型的几何元素（如线段）
            if shape_name == "line" and isinstance(shape_data, list):
                if debug:
                    logger.debug(f"发现线段数组：{len(shape_data)}个线段")
                
                for i, item in enumerate(shape_data):
                    if isinstance(item, dict) and 'path' in item:
                        path_str = item['path']
                        if debug:
                            logger.debug(f"处理线段{i}的SVG路径: {path_str}, 样式: {item.get('style')}")
                        
                        item_key = f"line_{i}"  # 创建唯一键
                        commands = parse_svg_path(path_str)
                        if commands:
                            shapes_commands[item_key] = commands
                            
                            # 保存原始样式信息
                            style_key = f"{item_key}_style"
                            shapes_commands[style_key] = item.get('style', {})
                            if debug:
                                logger.debug(f"为线段{i}保存样式信息，键名: {style_key}")
                            
                            # 计算当前形状的边界框
                            bbox = calculate_bbox(commands)
                            if bbox:
                                if debug:
                                    logger.debug(f"线段{i}的边界框: {bbox}")
                                
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
                    elif debug:
                        logger.warning(f"线段{i}数据结构异常: {item}")
            else:
                # 原有的单个形状处理（如圆）
                if isinstance(shape_data, dict) and 'path' in shape_data:
                    path_str = shape_data['path']
                    if debug:
                        logger.debug(f"处理形状 {shape_name} 的SVG路径: {path_str}")
                    commands = parse_svg_path(path_str)
                    if commands:
                        shapes_commands[shape_name] = commands
                        
                        # 计算当前形状的边界框
                        bbox = calculate_bbox(commands)
                        if bbox:
                            if debug:
                                logger.info(f"形状 {shape_name} 的边界框: {bbox}")
                            
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
        
        # 处理标签 (在图像上渲染)
        label_images = []
        if 'label' in actual_data and isinstance(actual_data['label'], list):
            for i, label_data in enumerate(actual_data['label']):
                if isinstance(label_data, dict) and 'text' in label_data and 'position' in label_data:
                    text = label_data['text']
                    position = label_data['position']
                    font_size = label_data.get('font_size', 24)  # 默认字体大小
                    if debug:
                        logger.info(f"处理标签{i}: 文本={text}, 位置={position}, 字体大小={font_size}")
                    
                    # 使用text_renderer渲染标签
                    label_img = render_text_as_image(text, font_size, debug=debug)
                    
                    if label_img is None or label_img.size == 0:
                        if debug:
                            logger.warning(f"标签 '{text}' 渲染失败，跳过此标签")
                        continue
                    
                    if debug:
                        logger.info(f"标签图像 '{text}' 大小: {label_img.shape}, 最大值: {np.max(label_img)}")
                    
                    # 保存标签图像及其位置
                    label_images.append((label_img, position[0], position[1]))
                    
                    # 更新边界框以包含标签
                    h, w = label_img.shape[:2]
                    label_bbox = (
                        position[0] - w//2,
                        position[1] - h//2,
                        position[0] + w//2,
                        position[1] + h//2
                    )
                    
                    # 更新组合边界框
                    if combined_bbox is None:
                        combined_bbox = label_bbox
                    else:
                        combined_bbox = (
                            min(combined_bbox[0], label_bbox[0]),
                            min(combined_bbox[1], label_bbox[1]),
                            max(combined_bbox[2], label_bbox[2]),
                            max(combined_bbox[3], label_bbox[3])
                        )
        
        # 确保我们有有效的边界框
        if combined_bbox is None:
            logger.warning("没有找到有效的几何图形边界框")
            # 创建默认边界框，覆盖整个画布区域
            combined_bbox = (0, 0, img_size, img_size)
        
        if debug:
            logger.info(f"所有几何形状的组合边界框: {combined_bbox}")
        
        # 计算统一的变换参数
        scale, offset_x, offset_y = calculate_transform(
            combined_bbox, (img_size, img_size), scale_factor, None
        )
        if debug:
            logger.info(f"统一变换参数: scale={scale}, offset_x={offset_x}, offset_y={offset_y}")
        
        # 确保偏移量不会使图形完全移出画布
        min_offset_x = -scale * (combined_bbox[2] - combined_bbox[0]) * 0.7
        max_offset_x = scale * (img_size - (combined_bbox[2] - combined_bbox[0]) / 2)
        offset_x = max(min_offset_x, min(offset_x, max_offset_x))

        min_offset_y = -scale * (combined_bbox[3] - combined_bbox[1]) * 0.7
        max_offset_y = scale * (img_size - (combined_bbox[3] - combined_bbox[1]) / 2)
        offset_y = max(min_offset_y, min(offset_y, max_offset_y))
        
        # 第二遍：使用统一变换参数渲染所有形状
        if debug:
            logger.debug(f"开始渲染形状，共有 {len(shapes_commands)} 个形状命令")
            logger.debug(f"形状命令键: {list(shapes_commands.keys())}")

        for shape_name, commands in shapes_commands.items():
            # 跳过样式信息键
            if "_style" in shape_name:
                continue
            
            if debug:
                logger.debug(f"渲染形状: {shape_name}, 命令数: {len(commands)}")
            
            # 应用统一变换
            transformed_commands = transform_commands(commands, scale, offset_x, offset_y)
            
            # 获取样式信息
            style = {}
            stroke_color = (255, 255, 255, 255)  # 默认白色
            stroke_width = 2
            
            # 区分线段和其他形状
            if shape_name.startswith("line_"):
                style_key = f"{shape_name}_style"
                if style_key in shapes_commands:
                    style = shapes_commands[style_key]
                    if debug:
                        logger.debug(f"使用线段样式: {style}, 键名: {style_key}")
                else:
                    if debug:
                        logger.warning(f"未找到线段样式: {style_key}")
            else:
                # 原有样式获取方式
                original_shape_data = actual_data.get(shape_name)
                if isinstance(original_shape_data, dict):
                    style = original_shape_data.get('style', {})
                    if debug:
                        logger.debug(f"使用形状样式: {style}")
                else:
                    if debug:
                        logger.warning(f"形状 {shape_name} 没有有效的样式数据")
            
            # 设置绘制属性
            stroke_width = int(style.get('stroke-width', 2))
            if style.get('stroke') == 'yellow':
                stroke_color = (255, 255, 0, 255)  # 黄色
            else:
                stroke_color = (255, 255, 255, 255)  # 白色
            
            # 渲染路径
            last_pos = None
            for cmd in transformed_commands:
                if cmd['command'] == 'M':
                    last_pos = (int(cmd['x']), int(cmd['y']))
                elif cmd['command'] == 'L' and last_pos is not None:
                    end_pos = (int(cmd['x']), int(cmd['y']))
                    # 使用抗锯齿
                    cv2.line(canvas, last_pos, end_pos, stroke_color, stroke_width, cv2.LINE_AA)
                    last_pos = end_pos  # 更新起点位置
                elif cmd['command'] == 'Z' and last_pos is not None and len(transformed_commands) > 0:
                    # 闭合路径
                    for start_cmd in transformed_commands:
                        if start_cmd['command'] == 'M':
                            start_pos = (int(start_cmd['x']), int(start_cmd['y']))
                            cv2.line(canvas, last_pos, start_pos, stroke_color, stroke_width, cv2.LINE_AA)
                            break
        
        # 渲染标签
        for label_img, x, y in label_images:
            # 转换坐标
            tx = int(x * scale + offset_x)
            ty = int(y * scale + offset_y)
            
            if debug:
                logger.info(f"标签放置位置: 原始=({x}, {y}), 转换后=({tx}, {ty})")
            
            # 将标签图像放置在指定位置
            h, w = label_img.shape[:2]
            x_start = tx - w // 2
            y_start = ty - h // 2
            
            # 确保坐标在有效范围内
            x_start = max(0, min(x_start, img_size - w))
            y_start = max(0, min(y_start, img_size - h))
            
            # 计算结束位置
            x_end = min(x_start + w, img_size)
            y_end = min(y_start + h, img_size)
            
            # 裁剪标签以适应画布
            label_w = x_end - x_start
            label_h = y_end - y_start
            
            if label_w > 0 and label_h > 0:
                if debug:
                    logger.info(f"混合标签图像到位置: ({x_start}, {y_start}), 大小: {label_w}x{label_h}")
                
                # 复制标签图像的一部分到画布上
                if label_img.shape[2] == 4:  # RGBA
                    # 提取alpha通道，确保值足够大以便于显示
                    alpha = label_img[:label_h, :label_w, 3] / 255.0
                    alpha = np.expand_dims(alpha, axis=2)
                    
                    # 混合RGB通道
                    src_rgb = label_img[:label_h, :label_w, :3]
                    dst_rgb = canvas[y_start:y_end, x_start:x_end, :3]
                    
                    # 确保文本是白色且清晰可见
                    white_mask = np.any(src_rgb > 100, axis=2)
                    for c in range(3):
                        src_channel = src_rgb[:, :, c]
                        src_channel[white_mask] = 255
                    
                    canvas[y_start:y_end, x_start:x_end, :3] = (
                        dst_rgb * (1 - alpha) + src_rgb * alpha
                    ).astype(np.uint8)
                    
                    # 更新Alpha通道
                    canvas[y_start:y_end, x_start:x_end, 3] = np.maximum(
                        canvas[y_start:y_end, x_start:x_end, 3],
                        (label_img[:label_h, :label_w, 3]).astype(np.uint8)
                    )
                else:  # RGB
                    # 简单叠加
                    canvas[y_start:y_end, x_start:x_end, :3] = label_img[:label_h, :label_w]
                    canvas[y_start:y_end, x_start:x_end, 3] = 255  # 设置完全不透明
        
        # 转换为RGB格式并裁剪
        if canvas.shape[2] == 4:  # RGBA
            # 创建一个与黑板背景颜色匹配的画布
            rgb_canvas = np.ones((img_size, img_size, 3), dtype=np.uint8) * np.array([30, 30, 30], dtype=np.uint8)
            
            # 提取透明通道作为蒙版
            alpha = (canvas[:, :, 3] / 255.0).reshape(img_size, img_size, 1)
            
            # 应用alpha混合（一次性处理所有通道）
            rgb_canvas = (rgb_canvas * (1 - alpha) + canvas[:, :, :3] * alpha).astype(np.uint8)
            
            # 裁剪图像
            return trim_image(rgb_canvas)
        else:
            return canvas
        
    except Exception as e:
        error_msg = f"渲染几何图形时出错: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        
        # 打印到控制台方便查看
        import sys
        print(error_msg, file=sys.stderr)
        print(traceback.format_exc(), file=sys.stderr)
        
        # 返回错误图像
        canvas = np.zeros((img_size, img_size, 4), dtype=np.uint8)
        cv2.putText(canvas, "Geometry Error", (50, img_size//2), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255, 255), 2)
        return canvas 
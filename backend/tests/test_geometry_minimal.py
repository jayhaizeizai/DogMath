import sys
import os
import cv2
import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt

# 设置环境变量和Python路径
root_dir = str(Path(__file__).parent.parent.parent)
sys.path.insert(0, root_dir)

def render_geometry(svg_path, scale_factor):
    """
    渲染几何图形
    
    Args:
        svg_path: SVG路径字符串
        scale_factor: 缩放因子
        
    Returns:
        渲染后的图像
    """
    # 创建一个空白画布 - 使用深灰色背景以匹配黑板
    img_size = 256  # 默认几何图形大小
    canvas = np.ones((img_size, img_size, 3), dtype=np.uint8) * np.array([30, 30, 30], dtype=np.uint8)
    
    # 解析SVG路径
    # 这里是一个简化版，只支持基本的移动(M)、线(L)和圆弧(A)命令
    path_commands = svg_path.strip().split(' ')
    points = []
    current_point = None
    
    # 计算缩放和偏移，使图形居中
    scale = scale_factor / 100  # 假设SVG坐标在0-100范围内
    offset_x = img_size // 2
    offset_y = img_size // 2
    
    i = 0
    while i < len(path_commands):
        cmd = path_commands[i]
        
        if cmd == 'M' or cmd == 'm':  # 移动
            x = float(path_commands[i+1])
            y = float(path_commands[i+2])
            if cmd == 'M':  # 绝对坐标
                current_point = (int(x * scale + offset_x), int(y * scale + offset_y))
            else:  # 相对坐标
                if current_point:
                    current_point = (int(current_point[0] + x * scale), int(current_point[1] + y * scale))
                else:
                    current_point = (int(x * scale + offset_x), int(y * scale + offset_y))
            points.append(current_point)
            i += 3
            
        elif cmd == 'L' or cmd == 'l':  # 线
            x = float(path_commands[i+1])
            y = float(path_commands[i+2])
            if cmd == 'L':  # 绝对坐标
                next_point = (int(x * scale + offset_x), int(y * scale + offset_y))
            else:  # 相对坐标
                next_point = (int(current_point[0] + x * scale), int(current_point[1] + y * scale))
            
            if current_point and next_point:
                cv2.line(canvas, current_point, next_point, (255, 255, 255), 2)
            
            current_point = next_point
            points.append(current_point)
            i += 3
            
        elif cmd == 'A' or cmd == 'a':  # 圆弧 (简化处理)
            # 圆弧参数: rx ry x-axis-rotation large-arc-flag sweep-flag x y
            rx = float(path_commands[i+1])
            ry = float(path_commands[i+2])
            x_axis_rot = float(path_commands[i+3])
            large_arc = int(path_commands[i+4])
            sweep = int(path_commands[i+5])
            x = float(path_commands[i+6])
            y = float(path_commands[i+7])
            
            if cmd == 'A':  # 绝对坐标
                next_point = (int(x * scale + offset_x), int(y * scale + offset_y))
            else:  # 相对坐标
                next_point = (int(current_point[0] + x * scale), int(current_point[1] + y * scale))
            
            # 简化：绘制一条直线来代替圆弧
            if current_point and next_point:
                cv2.line(canvas, current_point, next_point, (255, 255, 255), 2)
            
            current_point = next_point
            points.append(current_point)
            i += 8
            
        elif cmd == 'Z' or cmd == 'z':  # 闭合路径
            if len(points) > 1 and points[0] != current_point:
                cv2.line(canvas, current_point, points[0], (255, 255, 255), 2)
            i += 1
            
        else:
            # 跳过未识别的命令
            i += 1
    
    # 如果有足够的点来形成一个闭合路径，尝试填充
    if len(points) >= 3:
        # 创建一个填充蒙版
        mask = np.zeros((img_size, img_size), dtype=np.uint8)
        # 转换points为numpy数组以便填充
        points_array = np.array(points, dtype=np.int32)
        # 填充多边形
        cv2.fillPoly(mask, [points_array], 255)
        
        # 使用蒙版为图形添加半透明填充效果
        for c in range(3):
            # 将填充区域变为略亮的灰色，而不是纯白色
            fill_color = 80  # 灰色填充
            canvas[:, :, c] = np.where(mask == 255, 
                                     canvas[:, :, c] * 0.6 + fill_color * 0.4,  # 半透明填充
                                     canvas[:, :, c])
        
        # 重新绘制边界线，使其清晰
        for j in range(len(points)):
            p1 = points[j]
            p2 = points[(j + 1) % len(points)]
            cv2.line(canvas, p1, p2, (255, 255, 255), 2)
    
    return canvas

def render_partial_geometry(canvas, svg_path, scale_factor, progress):
    """
    渲染部分几何图形，用于实现动画绘制效果
    
    Args:
        canvas: 目标画布
        svg_path: SVG路径字符串
        scale_factor: 缩放因子
        progress: 绘制进度（0.0-1.0）
    
    Returns:
        修改后的画布
    """
    # 解析SVG路径
    path_commands = svg_path.strip().split(' ')
    points = []
    current_point = None
    
    # 计算缩放和偏移，使图形居中
    img_size = canvas.shape[0]  # 假设是正方形
    scale = scale_factor / 100  # 假设SVG坐标在0-100范围内
    offset_x = img_size // 2
    offset_y = img_size // 2
    
    # 计算总命令数量，确定当前进度应绘制的命令
    total_commands = 0
    command_indices = []
    
    # 预处理，计算点的总数和命令位置
    i = 0
    while i < len(path_commands):
        cmd = path_commands[i]
        if cmd in ['M', 'm', 'L', 'l']:
            total_commands += 1
            command_indices.append(i)
            i += 3
        elif cmd in ['A', 'a']:
            total_commands += 1
            command_indices.append(i)
            i += 8
        elif cmd in ['Z', 'z']:
            # Z命令是闭合路径，连接到第一个点
            if total_commands > 0:
                total_commands += 1
                command_indices.append(i)
            i += 1
        else:
            i += 1
    
    # 计算当前进度下应绘制的命令数
    commands_to_draw = max(1, int(total_commands * progress))
    
    # 只绘制应该显示的命令
    i = 0
    points = []
    current_point = None
    
    for cmd_idx in range(min(commands_to_draw, len(command_indices))):
        i = command_indices[cmd_idx]
        cmd = path_commands[i]
        
        if cmd == 'M' or cmd == 'm':  # 移动
            x = float(path_commands[i+1])
            y = float(path_commands[i+2])
            if cmd == 'M':  # 绝对坐标
                current_point = (int(x * scale + offset_x), int(y * scale + offset_y))
            else:  # 相对坐标
                if current_point:
                    current_point = (int(current_point[0] + x * scale), int(current_point[1] + y * scale))
                else:
                    current_point = (int(x * scale + offset_x), int(y * scale + offset_y))
            points.append(current_point)
        
        elif cmd == 'L' or cmd == 'l':  # 线
            x = float(path_commands[i+1])
            y = float(path_commands[i+2])
            if cmd == 'L':  # 绝对坐标
                next_point = (int(x * scale + offset_x), int(y * scale + offset_y))
            else:  # 相对坐标
                next_point = (int(current_point[0] + x * scale), int(current_point[1] + y * scale))
            
            if current_point and next_point:
                cv2.line(canvas, current_point, next_point, (255, 255, 255), 2)
            
            current_point = next_point
            points.append(current_point)
        
        elif cmd == 'A' or cmd == 'a':  # 圆弧 (简化处理)
            # 圆弧参数: rx ry x-axis-rotation large-arc-flag sweep-flag x y
            rx = float(path_commands[i+1])
            ry = float(path_commands[i+2])
            x_axis_rot = float(path_commands[i+3])
            large_arc = int(path_commands[i+4])
            sweep = int(path_commands[i+5])
            x = float(path_commands[i+6])
            y = float(path_commands[i+7])
            
            if cmd == 'A':  # 绝对坐标
                next_point = (int(x * scale + offset_x), int(y * scale + offset_y))
            else:  # 相对坐标
                next_point = (int(current_point[0] + x * scale), int(current_point[1] + y * scale))
            
            # 简化：绘制一条直线来代替圆弧
            if current_point and next_point:
                cv2.line(canvas, current_point, next_point, (255, 255, 255), 2)
            
            current_point = next_point
            points.append(current_point)
        
        elif cmd == 'Z' or cmd == 'z':  # 闭合路径
            if len(points) > 1 and points[0] != current_point:
                cv2.line(canvas, current_point, points[0], (255, 255, 255), 2)
    
    # 如果有足够的点来形成一个闭合路径并且进度超过70%，添加填充
    if len(points) >= 3 and progress > 0.7:
        # 创建一个填充蒙版
        mask = np.zeros((img_size, img_size), dtype=np.uint8)
        # 转换points为numpy数组以便填充
        points_array = np.array(points, dtype=np.int32)
        # 填充多边形
        cv2.fillPoly(mask, [points_array], 255)
        
        # 计算填充透明度，从0逐渐增加到0.4
        fill_alpha = min(0.4, (progress - 0.7) * 1.33)  # 在0.7-1.0的进度范围内，透明度从0增加到0.4
        
        for c in range(3):
            fill_color = 80  # 灰色填充
            canvas[:, :, c] = np.where(mask == 255, 
                                     canvas[:, :, c] * (1 - fill_alpha) + fill_color * fill_alpha,
                                     canvas[:, :, c])
    
    return canvas

def create_animation_frames(svg_path, scale_factor, num_frames):
    """
    创建几何图形动画帧序列
    
    Args:
        svg_path: SVG路径字符串
        scale_factor: 缩放因子
        num_frames: 帧数量
        
    Returns:
        帧序列列表
    """
    frames = []
    img_size = 256
    
    for i in range(num_frames):
        progress = (i + 1) / num_frames
        canvas = np.ones((img_size, img_size, 3), dtype=np.uint8) * np.array([30, 30, 30], dtype=np.uint8)
        frame = render_partial_geometry(canvas, svg_path, scale_factor, progress)
        frames.append(frame)
    
    return frames

def save_animation_frames(frames, output_dir):
    """保存动画帧到指定目录"""
    os.makedirs(output_dir, exist_ok=True)
    
    for i, frame in enumerate(frames):
        frame_path = os.path.join(output_dir, f"frame_{i:03d}.jpg")
        cv2.imwrite(frame_path, frame)
    
    print(f"保存了 {len(frames)} 帧动画到 {output_dir}")

def main():
    # 测试三角形
    triangle_path = "M0 0 L100 0 L50 100 Z"
    scale_factor = 32
    
    # 渲染完整三角形
    triangle_img = render_geometry(triangle_path, scale_factor)
    
    # 保存完整三角形
    output_dir = Path(__file__).parent.parent / "output"
    os.makedirs(output_dir, exist_ok=True)
    
    cv2.imwrite(str(output_dir / "triangle_full.jpg"), triangle_img)
    print(f"保存完整三角形: {output_dir / 'triangle_full.jpg'}")
    
    # 创建动画帧
    animation_frames = create_animation_frames(triangle_path, scale_factor, 10)
    
    # 保存动画帧
    animation_dir = output_dir / "triangle_animation"
    save_animation_frames(animation_frames, str(animation_dir))
    
    # 测试矩形+圆弧
    rect_arc_path = "M0 0 L100 0 A50 50 0 0 1 100 100 L0 100 Z"
    
    # 渲染完整矩形+圆弧
    rect_arc_img = render_geometry(rect_arc_path, scale_factor)
    
    # 保存完整矩形+圆弧
    cv2.imwrite(str(output_dir / "rect_arc_full.jpg"), rect_arc_img)
    print(f"保存完整矩形+圆弧: {output_dir / 'rect_arc_full.jpg'}")
    
    # 创建动画帧
    animation_frames = create_animation_frames(rect_arc_path, scale_factor, 10)
    
    # 保存动画帧
    animation_dir = output_dir / "rect_arc_animation"
    save_animation_frames(animation_frames, str(animation_dir))
    
    print("测试完成")

if __name__ == "__main__":
    main() 
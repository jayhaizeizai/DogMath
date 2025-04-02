"""
更新BlackboardVideoGenerator类，修复几何图形动画绘制功能
"""
import os
import re
import sys
import cv2
import numpy as np
from pathlib import Path

def update_blackboard_generator():
    """更新BlackboardVideoGenerator类，添加几何图形动画绘制功能"""
    
    # 初始化路径
    root_dir = Path(__file__).parent
    target_file = root_dir / "backend/src/video_generator/blackboard_video_generator.py"
    
    if not target_file.exists():
        print(f"错误：找不到目标文件: {target_file}")
        return False
    
    # 备份原始文件
    backup_file = target_file.with_suffix('.py.bak')
    backup_file.write_text(target_file.read_text(encoding='utf-8'), encoding='utf-8')
    print(f"已备份原始文件到: {backup_file}")
    
    # 读取原始内容
    original_content = target_file.read_text(encoding='utf-8')
    
    # 添加_render_partial_geometry方法到类中
    # 定位到合适的位置（_render_geometry方法之后）
    partial_geometry_method = """
    def _render_partial_geometry(self, canvas, svg_path, scale_factor, progress):
        \"\"\"
        渲染部分几何图形，用于实现动画绘制效果
        
        Args:
            canvas: 目标画布
            svg_path: SVG路径字符串
            scale_factor: 缩放因子
            progress: 绘制进度（0.0-1.0）
        \"\"\"
        try:
            # 图像大小
            img_size = canvas.shape[0]  # 假设是正方形
            
            # 解析SVG路径
            path_commands = svg_path.strip().split(' ')
            points = []
            current_point = None
            
            # 计算缩放和偏移，使图形居中
            scale = scale_factor / 100  # 假设SVG坐标在0-100范围内
            offset_x = img_size // 2
            offset_y = img_size // 2
            
            # 计算总路径点数和当前应绘制的点数
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
                    
                    # 绘制直线代替圆弧（简化）
                    if current_point and next_point:
                        cv2.line(canvas, current_point, next_point, (255, 255, 255), 2)
                    
                    current_point = next_point
                    points.append(current_point)
                
                elif cmd == 'Z' or cmd == 'z':  # 闭合路径
                    if len(points) > 1 and points[0] != current_point:
                        cv2.line(canvas, current_point, points[0], (255, 255, 255), 2)
            
            # 如果有足够的点来形成一个闭合路径并且进度超过50%，添加填充
            if len(points) >= 3 and progress > 0.5:
                # 应用半透明填充
                mask = np.zeros((img_size, img_size), dtype=np.uint8)
                points_array = np.array(points, dtype=np.int32)
                cv2.fillPoly(mask, [points_array], 255)
                
                # 计算填充透明度，从0逐渐增加到0.4
                fill_alpha = min(0.4, (progress - 0.5) * 0.8)  # 在0.5-1.0的进度范围内，透明度从0增加到0.4
                
                for c in range(3):
                    fill_color = 80  # 灰色填充
                    canvas[:, :, c] = np.where(mask == 255, 
                                            canvas[:, :, c] * (1 - fill_alpha) + fill_color * fill_alpha,
                                            canvas[:, :, c])
                
                # 重新绘制边界线，确保清晰可见
                for j in range(len(points) - 1):
                    cv2.line(canvas, points[j], points[j+1], (255, 255, 255), 2)
                
                # 如果是闭合路径，绘制最后一条线
                if len(points) > 1 and cmd_idx >= len(command_indices) - 1:
                    cv2.line(canvas, points[-1], points[0], (255, 255, 255), 2)
            
        except Exception as e:
            self.logger.error(f"渲染部分几何图形时出错: {str(e)}")
    """
    
    # 修改几何图形动画处理部分
    updated_geometry_animation = """
                        # 处理几何图形动画
                        if item['type'] == 'geometry' and 'draw_path_frames' in item and item['draw_path_frames'] > 0 and 'svg_path' in item:
                            if frame_idx < item['start_frame'] + item['draw_path_frames']:
                                relative_frame = frame_idx - item['start_frame']
                                progress = relative_frame / item['draw_path_frames']
                                
                                # 创建临时画布用于渲染部分几何图形
                                svg_path = item['svg_path']
                                scale_factor = item.get('scale_factor', 32)
                                h, w = content.shape[:2]
                                temp_canvas = np.ones((h, w, 3), dtype=np.uint8) * np.array([30, 30, 30], dtype=np.uint8)
                                
                                # 使用部分几何图形渲染方法
                                self._render_partial_geometry(temp_canvas, svg_path, scale_factor, progress)
                                
                                # 合成元素到帧中
                                self._blend_image_to_frame(frame, temp_canvas, pos_x, pos_y, alpha)
                            else:
                                # 合成完整元素到帧中
                                self._blend_image_to_frame(frame, content, pos_x, pos_y, alpha)
                        else:
                            # 合成元素到帧中
                            self._blend_image_to_frame(frame, content, pos_x, pos_y, alpha)
    """
    
    # 更新添加到时间轴的几何图形动画配置
    updated_geometry_timeline = """
                        # 添加到时间轴
                        timeline.append({
                            'type': 'geometry',
                            'content': geo_img,
                            'position': (x, y),
                            'start_frame': int(current_time * fps),
                            'end_frame': int((current_time + step_duration) * fps),
                            'fade_in_frames': fade_in_frames,
                            'draw_path_frames': draw_path_frames,
                            'svg_path': svg_path,  # 添加SVG路径
                            'scale_factor': font_size  # 添加缩放因子
                        })
    """
    
    # 寻找并替换代码
    # 1. 替换添加到时间轴部分
    pattern_timeline = re.compile(r"(timeline\.append\(\{\s*'type': 'geometry'.*?'draw_path_frames': draw_path_frames\s*\}\))", re.DOTALL)
    if pattern_timeline.search(original_content):
        updated_content = pattern_timeline.sub(updated_geometry_timeline, original_content)
    else:
        print("警告：找不到几何图形时间轴添加代码")
        updated_content = original_content
    
    # 2. 寻找_render_geometry方法的结束位置并添加_render_partial_geometry方法
    pattern_render_geometry = re.compile(r"(def _render_geometry.*?return img\s*)", re.DOTALL)
    match = pattern_render_geometry.search(updated_content)
    if match:
        insert_position = match.end()
        updated_content = updated_content[:insert_position] + partial_geometry_method + updated_content[insert_position:]
    else:
        print("警告：找不到_render_geometry方法")
    
    # 3. 替换处理几何图形动画部分
    pattern_animation = re.compile(r"(# 处理绘制路径动画.*?self\._blend_image_to_frame\(frame, content, pos_x, pos_y, alpha\))", re.DOTALL)
    if pattern_animation.search(updated_content):
        updated_content = pattern_animation.sub(updated_geometry_animation, updated_content)
        print("成功替换了处理几何图形动画代码")
    else:
        print("警告：找不到处理几何图形动画代码，尝试使用备用模式匹配")
        # 查找处理几何图形的代码段
        geo_pattern = re.compile(r'(# 处理几何图形动画\s*if item\.get\(\'type\'\) == \'geometry\' and \'draw_path_frames\' in item.*?)(self\._blend_image_to_frame\(frame, content, pos_x, pos_y, alpha\))', re.DOTALL)
        geo_match = geo_pattern.search(updated_content)
        if geo_match:
            replacement = geo_match.group(1) + updated_geometry_animation.strip()
            updated_content = geo_pattern.sub(replacement, updated_content)
            print("使用几何图形备用模式成功匹配并替换了动画代码")
        else:
            print("警告：无法找到几何图形动画处理代码块，尝试识别_generate_frame方法中添加代码")
            
            # 查找_generate_frame方法
            generate_frame_pattern = re.compile(r'def _generate_frame\(self, frame_number\):(.*?)return frame', re.DOTALL)
            frame_match = generate_frame_pattern.search(updated_content)
            
            if frame_match:
                frame_content = frame_match.group(1)
                print("已找到_generate_frame方法")
                
                # 在_generate_frame方法中查找几何图形处理部分
                geometry_check_pattern = re.compile(r'(if item\.get\(\'type\'\) == \'geometry\' and \'draw_path_frames\' in item.*?)(\n\s+self\._blend_image_to_frame\(frame, \w+, \w+, \w+, \w+\))', re.DOTALL)
                geometry_match = geometry_check_pattern.search(frame_content)
                
                if geometry_match:
                    print("找到了几何图形处理代码，正在更新...")
                    # 替换几何图形处理代码
                    new_frame_content = frame_content.replace(
                        geometry_match.group(0),
                        """
                        # 处理几何图形动画
                        if item.get('type') == 'geometry' and 'draw_path_frames' in item and item['draw_path_frames'] > 0 and 'svg_path' in item:
                            if frame_number < item['start_frame'] + item['draw_path_frames']:
                                relative_frame = frame_number - item['start_frame']
                                progress = relative_frame / item['draw_path_frames']
                                
                                # 创建临时画布用于渲染部分几何图形
                                svg_path = item['svg_path']
                                scale_factor = item.get('scale_factor', 32)
                                h, w = item['content'].shape[:2]
                                temp_canvas = np.ones((h, w, 3), dtype=np.uint8) * np.array([30, 30, 30], dtype=np.uint8)
                                
                                # 使用部分几何图形渲染方法
                                self._render_partial_geometry(temp_canvas, svg_path, scale_factor, progress)
                                
                                # 合成元素到帧中
                                self._blend_image_to_frame(frame, temp_canvas, item['position'][0], item['position'][1], alpha)
                            else:
                                # 合成完整元素到帧中
                                self._blend_image_to_frame(frame, item['content'], item['position'][0], item['position'][1], alpha)"""
                    )
                    
                    # 更新方法内容
                    updated_content = updated_content.replace(frame_match.group(1), new_frame_content)
                    print("成功更新了_generate_frame方法中的几何图形动画处理代码")
                else:
                    print("警告：在_generate_frame方法中找不到几何图形处理代码，将创建新的处理代码")
                    
                    # 查找方法中合适的位置添加我们的代码 - 在处理透明度之后
                    fade_out_pattern = re.compile(r'(# 计算透明度.*?alpha = \(end_frame - frame_number\) / fade_out_frames\n\s+)', re.DOTALL)
                    fade_match = fade_out_pattern.search(frame_content)
                    
                    if fade_match:
                        insertion_point = fade_match.end()
                        new_frame_content = frame_content[:insertion_point] + """
                        # 处理几何图形动画
                        if item.get('type') == 'geometry' and 'draw_path_frames' in item and item['draw_path_frames'] > 0 and 'svg_path' in item:
                            if frame_number < item['start_frame'] + item['draw_path_frames']:
                                relative_frame = frame_number - item['start_frame']
                                progress = relative_frame / item['draw_path_frames']
                                
                                # 创建临时画布用于渲染部分几何图形
                                svg_path = item['svg_path']
                                scale_factor = item.get('scale_factor', 32)
                                h, w = item['content'].shape[:2]
                                temp_canvas = np.ones((h, w, 3), dtype=np.uint8) * np.array([30, 30, 30], dtype=np.uint8)
                                
                                # 使用部分几何图形渲染方法
                                self._render_partial_geometry(temp_canvas, svg_path, scale_factor, progress)
                                
                                # 合成元素到帧中
                                position = item['position']
                                self._blend_image_to_frame(frame, temp_canvas, position[0], position[1], alpha)
                            else:
                                # 合成完整元素到帧中
                                position = item['position']
                                content = item['content']
                                self._blend_image_to_frame(frame, content, position[0], position[1], alpha)
                        else:
                            # 合成元素到帧中
                            position = item.get('position', (0, 0))
                            content = item.get('element', None)
                            if content is not None:
                                self._blend_image_to_frame(frame, content, position[0], position[1], alpha)
                        """ + frame_content[insertion_point:]
                        
                        # 更新方法内容
                        updated_content = updated_content.replace(frame_match.group(1), new_frame_content)
                        print("成功在_generate_frame方法中创建了新的几何图形动画处理代码")
                    else:
                        print("警告：在_generate_frame方法中找不到适合插入代码的位置")
            else:
                print("警告：找不到_generate_frame方法")
    
    # 写入修改后的内容
    target_file.write_text(updated_content, encoding='utf-8')
    print(f"已更新 {target_file}")
    return True

def main():
    """主函数"""
    print("开始更新BlackboardVideoGenerator...")
    success = update_blackboard_generator()
    if success:
        print("更新完成")
    else:
        print("更新失败")

if __name__ == "__main__":
    main() 
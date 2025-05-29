from typing import List, Dict, Any, Tuple
import numpy as np
import cv2
from loguru import logger
import matplotlib
import matplotlib.pyplot as plt
import os
import time
import json

# 1️⃣ 添加常量定义：15% 高度专门留给字幕
MIN_BOTTOM_SAFE = 0.15

from .utils.image_utils import create_blackboard_background, blend_image_to_frame
from .utils.video_utils import compress_video, get_z_index
from .renderers.text_renderer import render_text
from .renderers.formula_renderer import render_formula
from .renderers.geometry_renderer import render_geometry

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
        
        # 确保debug模式下日志级别生效
        if self.debug:
            self.logger.debug("调试模式已启用")
            self.logger.info(f"初始化黑板视频生成器: width={width}, height={height}")
        
        # 配置matplotlib
        self._setup_matplotlib()
        
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
    
    def _scale_step_content(self, step: dict) -> None:
        """
        计算 (1) 纵向可用高度、(2) 横向可用宽度 ，
        取二者里更严格的缩放因子，等比缩小元素 & 行间距。
        """
        safe = step.get("safe_zone") or {}
        safe_left   = safe.get("left", 0.05) 
        safe_top    = safe.get("top", 0.05)
        safe_bottom = max(safe.get("bottom", MIN_BOTTOM_SAFE), MIN_BOTTOM_SAFE)
        safe_right  = safe.get("right", 0.40)

        vertical_spacing_val = step.get("vertical_spacing")
        v_space = vertical_spacing_val if vertical_spacing_val is not None else 0.02
        elems   = step.get("elements", [])

        # ---------- ① 纵向约束 ----------
        valid_elems_for_h_ratio = [el for el in elems if "size" in el and isinstance(el["size"], tuple) and len(el["size"]) == 2]
        if not valid_elems_for_h_ratio and elems:
             self.logger.warning(f"Step {step.get('step_id', 'N/A')}: No valid element sizes found for vertical scaling. Skipping vertical scaling constraint.")
             scale_v = 1.0
        elif not valid_elems_for_h_ratio:
            scale_v = 1.0
        else:
            total_h_ratio = sum(el["size"][1] for el in valid_elems_for_h_ratio) \
                            + v_space * (len(valid_elems_for_h_ratio) - 1 if len(valid_elems_for_h_ratio) > 1 else 0)
            avail_h_ratio = 1.0 - safe_top - safe_bottom
            if avail_h_ratio <= 0:
                self.logger.warning(f"Step {step.get('step_id', 'N/A')}: Available height ratio non-positive ({avail_h_ratio:.3f}). Using scale_v=1.0.")
                scale_v = 1.0
            elif total_h_ratio > 0:
                scale_v = avail_h_ratio / total_h_ratio
            else:
                scale_v = 1.0
        
        # ---------- ② 横向约束 ----------
        valid_elems_for_w_ratio = [el for el in elems if "size" in el and isinstance(el["size"], tuple) and len(el["size"]) == 2]
        if not valid_elems_for_w_ratio and elems:
            max_w_ratio = 0.0 # Or handle as error/warning
            self.logger.warning(f"Step {step.get('step_id', 'N/A')}: No valid element sizes found for horizontal scaling. Skipping horizontal scaling constraint.")
            scale_h = 1.0
        elif not valid_elems_for_w_ratio: # No elements
            max_w_ratio = 0.0
            scale_h = 1.0
        else:
            max_w_ratio = max(el["size"][0] for el in valid_elems_for_w_ratio) if valid_elems_for_w_ratio else 0.0
            
        avail_w_ratio = 1.0 - safe_left - safe_right
        if avail_w_ratio <= 0:
            self.logger.warning(f"Step {step.get('step_id', 'N/A')}: Available width ratio non-positive ({avail_w_ratio:.3f}). Using scale_h=1.0.")
            scale_h = 1.0
        elif max_w_ratio > 0:
            scale_h = avail_w_ratio / max_w_ratio
        else:
            scale_h = 1.0
        
        scale_v = max(0.001, scale_v) 
        scale_h = max(0.001, scale_h)

        scale = min(scale_v, scale_h, 1.0)
        if scale >= 1.0:    
            for el in elems: # Ensure image and size keys exist
                if "image" not in el: el["image"] = np.zeros((1,1,3), dtype=np.uint8)
                if "size" not in el: el["size"] = (0.0, 0.0)
            return

        step["vertical_spacing"] = v_space * scale

        for el in elems:
            if "image" not in el or "size" not in el : # Should have been set by now
                 self.logger.warning(f"Step {step.get('step_id', 'N/A')}, Element: Missing 'image' or 'size' during scaling. Element might not be rendered correctly.")
                 if "image" not in el: el["image"] = np.zeros((1,1,3), dtype=np.uint8) # Placeholder
                 if "size" not in el: el["size"] = (0.0,0.0) # Placeholder

            img = el["image"]
            h,  w = img.shape[:2]
            new_w, new_h = max(1, int(w * scale)), max(1, int(h * scale))
            el["image"]  = cv2.resize(img, (new_w, new_h),
                                    interpolation=cv2.INTER_AREA)
            el["size"]   = (new_w / self.width, new_h / self.height)

        if self.debug:
            self.logger.info(
                f"Step {step.get('step_id', 'N/A')} 自动缩放: scale_v={scale_v:.3f}, "
                f"scale_h={scale_h:.3f}, 使用={scale:.3f}"
            )

    def _auto_vertical_stack(self, step: dict) -> None:
        """
        把 center 定义在可见内容区：
            左 = safe_left，右 = 1 - safe_right
        无论 text / formula / geometry 都水平居中摆放；
        有显式 'position' 的，用户给的 x 被解释为相对于安全区。
        """
        safe  = step.get('safe_zone') or {}
        safe_left   = safe.get('left', 0.05)       
        safe_top    = safe.get('top', 0.05)
        safe_bottom = max(safe.get('bottom', MIN_BOTTOM_SAFE), MIN_BOTTOM_SAFE)
        safe_right  = safe.get('right', 0.40)

        safe_area_w = 1.0 - safe_left - safe_right
        step_id_for_log = step.get('step_id', 'N/A')
        
        content_area_horizontal_center: float
        if safe_area_w <= 0:
            self.logger.warning(
                f"Step {step_id_for_log} in _auto_vertical_stack: "
                f"Safe area width is non-positive ({safe_area_w:.3f}). "
                f"Elements will be centered globally for X (0.5)."
            )
            content_area_horizontal_center = 0.5 
        else:
            content_area_horizontal_center = safe_left + safe_area_w / 2

        vertical_spacing_val = step.get("vertical_spacing")
        v_space = vertical_spacing_val if vertical_spacing_val is not None else 0.02

        y_cursor = safe_top 
        for el in step.get('elements', []):
            if "size" not in el or not isinstance(el["size"], tuple) or len(el["size"]) != 2:
                self.logger.warning(f"Step {step_id_for_log}, Element type {el.get('type', 'Unknown')}: Skipping in _auto_vertical_stack due to missing or invalid 'size'.")
                continue

            _w_ratio, h_ratio = el['size'] 

            current_x_global: float
            if el.get('position') and el['position'][0] is not None:
                json_rel_x = el['position'][0] 
                if safe_area_w <= 0: 
                    current_x_global = 0.5 
                    self.logger.warning(f"Step {step_id_for_log}, Element type {el.get('type', 'Unknown')}: Using global center X due to non-positive safe_area_w in _auto_vertical_stack with provided relative X.")
                else:
                    current_x_global = safe_left + json_rel_x * safe_area_w
            else: 
                current_x_global = content_area_horizontal_center
            
            anchor_y_global = y_cursor + h_ratio / 2
            el['position'] = [current_x_global, anchor_y_global] 

            y_cursor += h_ratio + v_space

    def generate_video(self, blackboard_data: dict) -> str:
        """
        生成黑板视频
        
        Args:
            blackboard_data: 黑板数据字典
            
        Returns:
            临时视频文件路径
        """
        try:
            input_steps = blackboard_data.get('steps', [])
            if not input_steps:
                self.logger.error("未找到步骤数据")
                return ""
                
            processed_steps = []

            for step_data in input_steps:
                current_step = {key: value for key, value in step_data.items()} # Deepcopy if complex, shallow for dicts of primitives
                elements_in_step_data = current_step.get('elements', [])
                current_step['elements'] = [{key: value for key, value in el.items()} for el in elements_in_step_data]


                step_id_for_log = current_step.get('step_id', 'N/A')

                safe_settings = current_step.get("safe_zone") or {}
                s_top = safe_settings.get("top", 0.05)
                s_bottom = max(safe_settings.get("bottom", MIN_BOTTOM_SAFE), MIN_BOTTOM_SAFE)
                s_right = safe_settings.get("right", 0.40)
                s_left = safe_settings.get("left", 0.05) 

                safe_area_w = 1.0 - s_left - s_right
                safe_area_h = 1.0 - s_top - s_bottom

                if safe_area_w <= 0:
                    self.logger.warning(f"Step {step_id_for_log}: Safe area width non-positive ({safe_area_w:.3f}). Positioning may be affected.")
                if safe_area_h <= 0:
                    self.logger.warning(f"Step {step_id_for_log}: Safe area height non-positive ({safe_area_h:.3f}). Positioning may be affected.")

                temp_processed_elements = []
                for element_data in current_step.get('elements', []):
                    element = element_data # Already a copy
                    img = None
                    if element['type'] == 'formula':
                        img = render_formula(element['content'], element.get('font_size', 32), self.debug)
                    elif element['type'] == 'text':
                        img = render_text(element['content'], element.get('font_size', 32), self.debug)
                    elif element['type'] == 'geometry':
                        img = render_geometry(element['content'], scale_factor=element.get('scale', 1.0), debug=self.debug)
                    
                    if img is None:
                        element['image'] = np.zeros((1,1,4), dtype=np.uint8) # Use 4 channels for alpha
                        element['size'] = (0.0, 0.0)
                        self.logger.warning(f"Step {step_id_for_log}, Element type {element.get('type')}: Failed to render. Using placeholder image.")
                    else:
                        element['image'] = img # This is BGRA from renderers
                        h_ratio = img.shape[0] / self.height
                        w_ratio = img.shape[1] / self.width
                        element['size'] = (w_ratio, h_ratio)
                    temp_processed_elements.append(element)
                current_step['elements'] = temp_processed_elements
                
                self._scale_step_content(current_step)
                
                is_vertical_stack_layout = current_step.get('layout') == 'vertical-stack'

                if is_vertical_stack_layout:
                    self._auto_vertical_stack(current_step)
                else:
                    for element in current_step.get('elements', []):
                        element_type_for_log = element.get('type', 'Unknown')
                        if element.get('position'): 
                            json_pos_x = element['position'][0]
                            json_pos_y = element['position'][1]
                            
                            global_center_x = 0.5 # Default global center X
                            global_center_y = 0.5 # Default global center Y

                            if safe_area_w > 0:
                                global_center_x = s_left + json_pos_x * safe_area_w
                            else:
                                self.logger.warning(f"Step {step_id_for_log}, Element {element_type_for_log}: Using global center X due to non-positive safe_area_w for non-vertical_stack.")
                            
                            if safe_area_h > 0:
                                global_center_y = s_top + json_pos_y * safe_area_h
                            else:
                                self.logger.warning(f"Step {step_id_for_log}, Element {element_type_for_log}: Using global center Y due to non-positive safe_area_h for non-vertical_stack.")
                                
                            element['position'] = [global_center_x, global_center_y]
                        else:
                            default_x = 0.5
                            default_y = 0.5
                            if safe_area_w > 0: default_x = s_left + 0.5 * safe_area_w
                            if safe_area_h > 0: default_y = s_top + 0.5 * safe_area_h
                            element['position'] = [default_x, default_y]
                            self.logger.info(
                                f"Step {step_id_for_log}, Element {element_type_for_log}: "
                                f"No 'position' in JSON for non-vertical-stack. Defaulting to global {element['position']} (safe area center if valid)."
                            )
                processed_steps.append(current_step)
                            
            width = blackboard_data.get('resolution', [self.width, self.height])[0]
            height = blackboard_data.get('resolution', [self.width, self.height])[1]
            fps = 30  
            
            temp_output_dir = "backend/output"
            if not os.path.exists(temp_output_dir):
                os.makedirs(temp_output_dir)
            temp_output = os.path.join(temp_output_dir, f"temp_blackboard_{int(time.time())}.mp4")
            
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            video_writer = cv2.VideoWriter(temp_output, fourcc, fps, (width, height))
            
            background = create_blackboard_background(width, height)
            
            for step in processed_steps:
                geometry_elements = []
                text_elements = []
                step_id_for_log = step.get('step_id', 'N/A')
                
                for element in step.get('elements', []):
                    if element['type'] == 'geometry':
                        geometry_elements.append(element)
                    elif element['type'] == 'text' and element.get('content','') in ['O', 'A', 'B', 'C']: # Check content exists
                        text_elements.append(element)
                
                if geometry_elements and text_elements:
                    self.logger.info(f"Step {step_id_for_log}: 检测到几何图形和文本标签，调整位置以确保匹配 (此部分逻辑未实现)")
            
            for step in processed_steps:
                total_frames = int(step.get('duration',0) * fps) # Ensure duration exists
                step_id_for_log = step.get('step_id', 'N/A')
                timeline = []
                
                for element in step.get('elements', []):
                    element_type = element.get('type', 'unknown')
                    
                    content = element.get('image') # Should be scaled BGRA image
                    
                    if content is None or not isinstance(content, np.ndarray) or content.size == 0 :
                        self.logger.warning(f"Step {step_id_for_log}, Element {element_type}: Content image is missing or invalid. Skipping element in timeline.")
                        continue

                    # Position should be global by now
                    position = element.get('position')
                    if position is None or len(position) != 2:
                        self.logger.warning(f"Step {step_id_for_log}, Element {element_type}: Position is missing or invalid. Defaulting to [0.5, 0.5].")
                        position = [0.5, 0.5] # Default global center
                    
                    animation = element.get('animation', {})
                    fade_in_frames = 0
                    fade_out_frames = 0
                    
                    if animation and isinstance(animation, dict): # Check animation is a dict
                        fade_duration = animation.get('duration', 1.0)
                        fade_in_frames = int(fade_duration * fps)
                        if 'exit' in animation: # Check key existence
                            fade_out_frames = int(fade_duration * fps)
                    
                    timeline.append({
                        'type': element_type,
                        'content': content, # This is an image
                        'position': position,
                        'start_frame': 0, # Simplified start/end for now
                        'end_frame': total_frames - fade_out_frames if fade_out_frames > 0 else total_frames,
                        'fade_in_frames': fade_in_frames,
                        'fade_out_frames': fade_out_frames,
                        'z_index': get_z_index(element_type)
                    })
                
                timeline.sort(key=lambda x: x['z_index'])
                
                for frame_idx in range(total_frames):
                    # 复制背景
                    frame = background.copy()
                    
                    # 渲染当前帧的所有元素
                    for item in timeline:
                        if item['start_frame'] <= frame_idx < item['end_frame']:
                            # 计算alpha值（淡入淡出效果）
                            alpha = 1.0
                            if item['fade_in_frames'] > 0 and frame_idx < item['fade_in_frames']:
                                alpha = frame_idx / item['fade_in_frames']
                            elif item['fade_out_frames'] > 0 and frame_idx >= item['end_frame'] - item['fade_out_frames']:
                                alpha = (item['end_frame'] - frame_idx) / item['fade_out_frames']
                            
                            # 获取位置
                            pos_x, pos_y = item['position']
                            
                            # 获取图像内容
                            content = item['content']
                            
                            # 混合元素到帧中
                            blend_image_to_frame(frame, content, pos_x, pos_y, alpha, self.debug)
                    
                    # 写入帧
                    video_writer.write(frame)
                    
                    # 显示进度
                    if frame_idx % 30 == 0:
                        self.logger.info(f"正在生成视频 {frame_idx}/{total_frames} 帧 ({frame_idx/total_frames*100:.1f}%)")
            
            # 释放视频写入器
            video_writer.release()
            
            # 压缩视频
            compress_video(temp_output, self.logger)
            
            # 返回临时视频文件路径
            return temp_output
            
        except Exception as e:
            self.logger.error(f"视频生成失败: {str(e)}")
            return ""


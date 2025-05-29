import numpy as np
import cv2
import matplotlib
import matplotlib.pyplot as plt
import io
import re
import logging
import traceback
from ..utils.image_utils import trim_image
from .text_renderer import render_text_as_image

logger = logging.getLogger(__name__)

def render_latex_as_image(latex, font_size=24, skip_scaling=False, debug=False):
    """
    将LaTeX公式渲染为图像
    
    Args:
        latex: LaTeX公式字符串
        font_size: 字体大小
        skip_scaling: 是否跳过缩放 (注意：此标志可能需要重新评估，但我们首先确保内部缩放逻辑正确)
        debug: 是否输出调试信息
        
    Returns:
        渲染后的图像 (已裁剪和缩放)
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
            canvas = trim_image(canvas)
            
            # 检查是否需要缩放图像
            if not skip_scaling: # This flag is important. If True, no scaling happens here.
                max_width_screen = 1920
                safe_right_factor = 0.40 # Use a consistent factor
                target_max_content_width = int(max_width_screen * (1 - safe_right_factor))
                
                h_canvas, w_canvas = canvas.shape[:2]
                if debug:
                    logger.debug(f"LaTeX content (after trim): {w_canvas}x{h_canvas}. Target max width: {target_max_content_width}")
                
                if w_canvas > target_max_content_width:
                    scale = target_max_content_width / w_canvas
                    new_w = target_max_content_width
                    new_h = int(h_canvas * scale)
                    canvas = cv2.resize(canvas, (new_w, new_h), interpolation=cv2.INTER_AREA)
                    if debug:
                        logger.debug(f"LaTeX content scaled to: {new_w}x{new_h}")
            
            return canvas
        else:
            return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            
    except Exception as e:
        logger.error(f"渲染LaTeX公式时出错: {latex}")
        logger.error(str(e))
        logger.error(traceback.format_exc())
        # 创建一个默认图像，使用与黑板背景匹配的颜色
        img = np.ones((100, 300, 3), dtype=np.uint8) * np.array([30, 30, 30], dtype=np.uint8)
        cv2.putText(img, "LaTeX Error", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        return img

def render_formula(formula, font_size, debug=False):
    """
    渲染公式
    
    Args:
        formula: 公式字符串
        font_size: 字体大小
        debug: 是否输出调试信息
        
    Returns:
        公式图像 (已确保宽度不超过安全区内容限制)
    """
    try:
        logger.info(f"渲染公式: {formula}, 字体大小: {font_size}")
        
        max_width_screen = 1920
        # 使用与 render_latex_as_image 中一致的右侧安全因子，尽管最终缩放由 blackboard_video_generator 控制，
        # 但这里可以用于指导单个元素渲染时的最大期望宽度。
        # 最终的元素尺寸和位置是由 BlackboardVideoGenerator 的 _scale_step_content 和布局逻辑决定的。
        # 此处的 adjusted_max_content_width 更多是作为一个"理想最大宽度"，单个元素渲染器尽量不要超过它。
        safe_right_factor = 0.40 
        # 假设左侧也有一个安全边距，例如0.05，那么内容区大约是 1 - 0.05 - 0.40 = 0.55
        # 但单个渲染器可能不知道全局的 safe_left，所以这里仅基于 safe_right 做一个大致约束
        adjusted_max_content_width = int(max_width_screen * (1 - safe_right_factor - 0.05)) # 减去一个假设的左边距

        has_chinese = any('\u4e00' <= c <= '\u9fff' for c in formula)
        contains_dollar = '$' in formula
        contains_backslash = '\\' in formula # 基本的LaTeX命令指示

        rendered_image = None

        if formula.startswith('$') and formula.endswith('$'):
            # Case 1: 纯粹由 $...$ 包裹的 LaTeX, e.g., "$\frac{1}{2}$"
            if debug: logger.debug(f"Formula '{formula[:30]}...': Case 1 - Purely enclosed LaTeX.")
            rendered_image = render_latex_as_image(formula, font_size, skip_scaling=False, debug=debug)
        
        elif contains_dollar:
            # Case 2: 包含 '$'，因此是混合内容或需要分割的 LaTeX。
            # e.g., "Text $\alpha$", or "B. $\frac{1}{2021}$"
            if debug: logger.debug(f"Formula '{formula[:30]}...': Case 2 - Mixed content with '$', splitting.")
            components = re.split(r'(\$[^$]*\$)', formula) # $...$ 标记一个 LaTeX 部分
            rendered_parts = []
            valid_parts_found = False

            for comp_text in components:
                if not comp_text.strip(): # 跳过空字符串或纯空白字符串
                    continue
                valid_parts_found = True
                if comp_text.startswith('$') and comp_text.endswith('$'):
                    # 这是一个 LaTeX 部分
                    part_img = render_latex_as_image(comp_text, font_size, skip_scaling=False, debug=debug)
                else:
                    # 这是一个纯文本部分
                    part_img = render_text_as_image(comp_text, font_size, debug=debug)
                
                if part_img is None: # 渲染器可能返回None如果出错
                    logger.warning(f"Component '{comp_text[:30]}' from '{formula[:30]}' failed to render. Skipping.")
                    continue
                rendered_parts.append(part_img)
            
            if not rendered_parts or not valid_parts_found:
                logger.warning(f"Formula '{formula[:30]}...' resulted in no renderable parts after splitting. Rendering as plain text.")
                rendered_image = render_text_as_image(formula, font_size, debug=debug) # 回退到纯文本渲染
            else:
                # 拼接渲染后的各个部分
                total_parts_width = sum(img.shape[1] for img in rendered_parts if img is not None and img.shape[1] > 0)
                if len(rendered_parts) > 1:
                    total_parts_width += 5 * (len([p for p in rendered_parts if p is not None]) - 1)
                
                max_parts_height = 0
                if rendered_parts:
                    valid_heights = [img.shape[0] for img in rendered_parts if img is not None and img.shape[0] > 0]
                    if valid_heights: max_parts_height = max(valid_heights)
                if max_parts_height == 0: max_parts_height = 50 # 最小高度回退

                if total_parts_width <= 0 : total_parts_width = 1 # 最小宽度回退

                combined_img = np.ones((max_parts_height, total_parts_width, 3), dtype=np.uint8) * np.array([30, 30, 30], dtype=np.uint8)
                x_offset = 0
                for img_part in rendered_parts:
                    if img_part is None or img_part.shape[0] == 0 or img_part.shape[1] == 0:
                        continue
                    h_part, w_part = img_part.shape[:2]
                    y_offset = (max_parts_height - h_part) // 2
                    try:
                        combined_img[y_offset:y_offset+h_part, x_offset:x_offset+w_part] = img_part
                    except ValueError as e:
                        logger.error(f"Error combining part for '{formula[:30]}...'. Part shape: {img_part.shape}, combined_img shape: {combined_img.shape}, x_offset: {x_offset}, y_offset: {y_offset}. Error: {e}")
                        continue 
                    x_offset += w_part + 5
                rendered_image = combined_img
        
        elif contains_backslash and not has_chinese :
            # Case 3: 包含反斜杠 (可能是简单 LaTeX 命令如 \frac), 不含美元符号, 且不含中文.
            # e.g., "\frac{1}{2}" or "\alpha"
            # 这对于用户输入简单LaTeX命令但不写$时比较方便，但如果反斜杠用于非LaTeX转义则可能出问题。
            if debug: logger.debug(f"Formula '{formula[:30]}...': Case 3 - Backslash, no dollar, no Chinese. Wrapping with $.")
            formula_to_render = f'${formula}$' # 用$包裹后按纯LaTeX处理
            rendered_image = render_latex_as_image(formula_to_render, font_size, skip_scaling=False, debug=debug)
            
        else:
            # Case 4: 纯文本 (可能包含中文, 或者包含反斜杠但同时也有中文或美元符号而被前述逻辑排除)
            # e.g., "普通文本", "A", "一些中文\English"
            if debug: logger.debug(f"Formula '{formula[:30]}...': Case 4 - Rendering as plain text.")
            rendered_image = render_text_as_image(formula, font_size, debug=debug)

        # --- 后续统一处理：检查图像是否成功生成，然后裁剪和缩放 ---
        if rendered_image is None:
            logger.error(f"Formula '{formula[:30]}...' failed to produce an image through all processing cases.")
            img = np.ones((50, 200, 3), dtype=np.uint8) * np.array([30, 30, 30], dtype=np.uint8)
            cv2.putText(img, "Render Error", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 1)
            return img # 直接返回错误图像
        
        # 1. 裁剪掉边缘空白
        final_image = trim_image(rendered_image)
        h_final, w_final = final_image.shape[:2]
        if w_final == 0 or h_final == 0: # trim_image 可能返回空图像
            logger.warning(f"Formula '{formula[:30]}...' resulted in zero-dimension image after trim. Using placeholder error image.")
            img = np.ones((50, 200, 3), dtype=np.uint8) * np.array([30, 30, 30], dtype=np.uint8)
            cv2.putText(img, "Empty Image", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 1)
            return img

        if debug:
            logger.debug(f"Formula '{formula[:20]}...' (after local trim): {w_final}x{h_final}. Ideal max content width: {adjusted_max_content_width}")

        # 2. 如果裁剪后宽度仍然超出"理想最大宽度"，则缩放。
        #    注意：这里的缩放是渲染器级别的初步缩放。
        #    最终的缩放以适应步骤安全区是由 BlackboardVideoGenerator._scale_step_content 控制的。
        if w_final > adjusted_max_content_width:
            scale = adjusted_max_content_width / w_final
            new_w = adjusted_max_content_width
            new_h = max(1, int(h_final * scale)) # 确保 new_h 不为0
            final_image = cv2.resize(final_image, (new_w, new_h), interpolation=cv2.INTER_AREA)
            if debug:
                logger.debug(f"Formula '{formula[:20]}...' locally scaled to: {new_w}x{new_h} to fit ideal max width.")
        
        return final_image
        
    except Exception as e:
        logger.error(f"渲染公式时发生严重错误: {formula[:30]}..., Error: {str(e)}")
        logger.error(traceback.format_exc())
        img = np.ones((50, 200, 3), dtype=np.uint8) * np.array([30, 30, 30], dtype=np.uint8)
        cv2.putText(img, "Formula Error", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 1)
        return img 
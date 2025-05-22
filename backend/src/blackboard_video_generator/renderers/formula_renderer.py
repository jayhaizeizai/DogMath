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
        safe_right_factor = 0.40
        adjusted_max_content_width = int(max_width_screen * (1 - safe_right_factor))

        has_chinese = any('\u4e00' <= c <= '\u9fff' for c in formula)
        is_latex    = '\\' in formula or '$' in formula
        
        # ------- 新增：若检测到 LaTeX 命令但没有任何 $，直接整式转 LaTeX -------
        if is_latex and '$' not in formula:
            if not formula.startswith('$'):
                formula = f'${formula}$'
            # 直接走纯 LaTeX 分支（含中文也没问题，render_latex_as_image 已加载 ctex）
            return render_latex_as_image(formula, font_size, skip_scaling=False, debug=debug)
        # ------------------------------------------------------------------------

        rendered_image = None

        if has_chinese and is_latex: # 混合内容处理
            components = re.split(r'(\$[^$]*\$)', formula)
            rendered_parts = []
            
            for comp in components:
                if comp.strip():
                    if comp.startswith('$') and comp.endswith('$'):
                        # render_latex_as_image already handles its own scaling if skip_scaling=False
                        # For consistency in combined image, pass skip_scaling=True and scale combined later,
                        # OR ensure render_latex_as_image is robust. Let's assume it is robust for now.
                        part_img = render_latex_as_image(comp, font_size, skip_scaling=False, debug=debug)
                        rendered_parts.append(part_img)
                    else:
                        # render_text_as_image might not have internal scaling.
                        # We'll scale the combined image.
                        part_img = render_text_as_image(comp, font_size, debug=debug)
                        rendered_parts.append(part_img)
            
            if not rendered_parts: # Handle cases where splitting results in no parts
                logger.warning(f"混合公式 '{formula}' 分割后没有有效部分。")
                # Return a small error image or handle appropriately
                error_img = np.ones((50, 200, 3), dtype=np.uint8) * np.array([30, 30, 30], dtype=np.uint8)
                cv2.putText(error_img, "Empty Formula", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,0,0), 1)
                return error_img

            total_parts_width = sum(img.shape[1] for img in rendered_parts) + 5 * (len(rendered_parts) - 1 if len(rendered_parts) > 0 else 0)
            max_parts_height = max(img.shape[0] for img in rendered_parts) if rendered_parts else 50
            
            combined_img = np.ones((max_parts_height, total_parts_width, 3), dtype=np.uint8) * np.array([30, 30, 30], dtype=np.uint8)
            x_offset = 0
            for img_part in rendered_parts:
                h_part, w_part = img_part.shape[:2]
                y_offset = (max_parts_height - h_part) // 2
                combined_img[y_offset:y_offset+h_part, x_offset:x_offset+w_part] = img_part
                x_offset += w_part + 5
            
            rendered_image = combined_img

        elif is_latex: # 对于纯LaTeX公式
            if not formula.startswith('$') and not formula.endswith('$'):
                formula = f'${formula}$'
            # render_latex_as_image will handle scaling if skip_scaling=False
            rendered_image = render_latex_as_image(formula, font_size, skip_scaling=False, debug=debug)
        
        else: # 对于纯中文公式或普通文本 (covers has_chinese and not is_latex, and not has_chinese and not is_latex)
            rendered_image = render_text_as_image(formula, font_size, debug=debug)

        # 统一的最后处理：裁剪和缩放
        if rendered_image is None: # Should not happen if logic above is correct
            logger.error(f"未能渲染公式: {formula}")
            error_img = np.ones((50, 200, 3), dtype=np.uint8) * np.array([30, 30, 30], dtype=np.uint8)
            cv2.putText(error_img, "Render Error", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,0,0), 1)
            return error_img

        # 1. 裁剪掉边缘空白
        final_image = trim_image(rendered_image)
        h_final, w_final = final_image.shape[:2]
        if debug:
            logger.debug(f"公式 '{formula[:20]}...' (after trim): {w_final}x{h_final}. Target max width: {adjusted_max_content_width}")

        # 2. 如果裁剪后宽度仍然超出，则缩放
        if w_final > adjusted_max_content_width:
            scale = adjusted_max_content_width / w_final
            new_w = adjusted_max_content_width
            new_h = int(h_final * scale)
            final_image = cv2.resize(final_image, (new_w, new_h), interpolation=cv2.INTER_AREA)
            if debug:
                logger.debug(f"公式 '{formula[:20]}...' scaled to: {new_w}x{new_h}")
        
        return final_image
        
    except Exception as e:
        logger.error(f"渲染公式时出错: {formula}, Error: {str(e)}")
        logger.error(traceback.format_exc())
        # 创建一个默认图像
        img = np.ones((50, 200, 3), dtype=np.uint8) * np.array([30, 30, 30], dtype=np.uint8)
        cv2.putText(img, "Formula Error", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 1)
        return img 
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
        skip_scaling: 是否跳过缩放
        debug: 是否输出调试信息
        
    Returns:
        渲染后的图像
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
            if not skip_scaling:  # 添加此条件
                max_width = 1920  # 最大宽度
                max_height = 1080  # 最大高度
                
                h, w = canvas.shape[:2]
                logger.debug(f"LaTeX公式原始图像大小: {w}x{h}")
                
                # 如果图像太大，进行等比例缩放
                if w > max_width or h > max_height:
                    scale = min(max_width / w, max_height / h)
                    new_w = int(w * scale)
                    new_h = int(h * scale)
                    canvas = cv2.resize(canvas, (new_w, new_h), interpolation=cv2.INTER_AREA)
                    logger.debug(f"LaTeX公式缩放后图像大小: {new_w}x{new_h}")
            
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
        公式图像
    """
    try:
        logger.info(f"渲染公式: {formula}, 字体大小: {font_size}")
        # 检测是否含有中文
        has_chinese = any('\u4e00' <= c <= '\u9fff' for c in formula)
        logger.debug(f"公式是否包含中文: {has_chinese}")
        
        # 检测是否含有LaTeX格式的公式
        is_latex = '\\' in formula or '$' in formula
        logger.debug(f"公式是否为LaTeX格式: {is_latex}")
        
        # 混合内容处理（中文+LaTeX）
        if has_chinese and is_latex:
            # 分割文本和LaTeX公式
            components = re.split(r'(\$[^$]*\$)', formula)
            logger.debug(f"分割后的组件: {components}")
            
            # 处理多个LaTeX部分
            rendered_parts = []
            
            for comp in components:
                if comp.strip():  # 忽略空字符串
                    if comp.startswith('$') and comp.endswith('$'):
                        # 渲染LaTeX部分
                        latex_img = render_latex_as_image(comp, font_size, skip_scaling=True, debug=debug)
                        rendered_parts.append(latex_img)
                        logger.debug(f"渲染LaTeX部分: {comp}, 大小: {latex_img.shape}")
                    else:
                        # 渲染中文部分
                        chinese_img = render_text_as_image(comp, font_size, debug=debug)
                        rendered_parts.append(chinese_img)
                        logger.debug(f"渲染中文部分: {comp}, 大小: {chinese_img.shape}")
            
            # 计算总宽度和最大高度
            total_width = sum(img.shape[1] for img in rendered_parts) + 5 * (len(rendered_parts) - 1)
            max_height = max(img.shape[0] for img in rendered_parts)
            logger.debug(f"组合图像总宽度: {total_width}, 最大高度: {max_height}")
            
            # 创建组合图像
            combined_img = np.ones((max_height, total_width, 3), dtype=np.uint8) * np.array([30, 30, 30], dtype=np.uint8)
            
            # 放置各个部分
            x_offset = 0
            for img in rendered_parts:
                h, w = img.shape[:2]
                y_offset = (max_height - h) // 2
                combined_img[y_offset:y_offset+h, x_offset:x_offset+w] = img
                x_offset += w + 5  # 恢复为5像素的间隔
                logger.debug(f"放置图像部分，当前x_offset: {x_offset}")
            
            # 检查是否需要缩放最终图像
            max_width = 1920
            max_img_height = 1080
            
            h, w = combined_img.shape[:2]
            if debug:
                logger.info(f"组合公式原始图像大小: {w}x{h}")
            
            # 如果图像太大，进行等比例缩放
            if w > max_width or h > max_img_height:
                scale = min(max_width / w, max_height / h)
                new_w = int(w * scale)
                new_h = int(h * scale)
                combined_img = cv2.resize(combined_img, (new_w, new_h), interpolation=cv2.INTER_AREA)
                if debug:
                    logger.info(f"组合公式缩放后图像大小: {new_w}x{new_h}")
            
            # 裁剪图像
            combined_img = trim_image(combined_img)
            return combined_img
        
        # 对于纯中文公式(不含LaTeX格式)
        if has_chinese and not is_latex:
            return render_text_as_image(formula, font_size, debug=debug)
            
        # 对于纯LaTeX公式
        if is_latex:
            # 确保LaTeX公式有$符号
            if not formula.startswith('$') and not formula.endswith('$'):
                formula = f'${formula}$'
            return render_latex_as_image(formula, font_size, debug=debug)
        
        # 对于普通文本
        return render_text_as_image(formula, font_size, debug=debug)
        
    except Exception as e:
        logger.error(f"渲染公式时出错: {str(e)}")
        # 创建一个默认图像
        img = np.zeros((100, 300, 3), dtype=np.uint8)
        cv2.putText(img, "Formula Error", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        return img 
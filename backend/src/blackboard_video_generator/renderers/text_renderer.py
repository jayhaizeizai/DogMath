import numpy as np
import cv2
import matplotlib
import matplotlib.pyplot as plt
import io
import logging
from ..utils.image_utils import trim_image

logger = logging.getLogger(__name__)

def render_text_as_image(text, font_size, debug=False):
    """
    将文本渲染为图像
    
    Args:
        text: 文本内容
        font_size: 字体大小
        debug: 是否输出调试信息
        
    Returns:
        文本图像
    """
    try:
        logger.info(f"渲染文本: {text}, 字体大小: {font_size}")
        
        # 新的画布尺寸计算
        dpi = 200  # 保持高清
        char_w_inch = font_size * 0.55 / 72  # 每个字符宽度（英寸）
        fig_width = max(char_w_inch * len(text), 2)  # 最小2英寸
        fig_height = max(font_size * 1.3 / 72, 1)    # 字体高度加行距
        
        # 创建matplotlib图形，使用动态大小
        fig = plt.figure(figsize=(fig_width, fig_height), dpi=dpi, facecolor='none')
        ax = fig.add_subplot(111)
        
        # 设置背景完全透明
        fig.patch.set_alpha(0.0)
        ax.set_facecolor((0, 0, 0, 0))
        ax.patch.set_alpha(0.0)
        
        # 尝试检测可用的中文字体
        chinese_font = None
        if any('\u4e00' <= c <= '\u9fff' for c in text):
            try:
                from matplotlib.font_manager import fontManager
                font_priorities = [
                    'Noto Sans CJK SC', 
                    'Noto Sans CJK JP', 
                    'Source Han Sans CN', 
                    'WenQuanYi Micro Hei', 
                    'WenQuanYi Zen Hei', 
                    'Microsoft YaHei', 
                    'SimHei', 
                    'STHeiti'
                ]
                
                for font in font_priorities:
                    matching_fonts = [f.name for f in fontManager.ttflist if font.lower() in f.name.lower()]
                    if matching_fonts:
                        chinese_font = matching_fonts[0]
                        if debug:
                            logger.info(f"文本渲染使用中文字体: {chinese_font}")
                        break
            except Exception as e:
                if debug:
                    logger.warning(f"检测中文字体失败: {str(e)}")
            
        # 渲染文本
        if chinese_font:
            ax.text(0.5, 0.5, text, 
                   fontsize=font_size,  # 移除了 * 0.8
                   color='white',
                   ha='center', va='center',
                   transform=ax.transAxes,
                   family=chinese_font)
        else:
            # 如果没有找到合适的中文字体，尝试用sans-serif字体族
            ax.text(0.5, 0.5, text, 
                   fontsize=font_size,  # 移除了 * 0.8
                   color='white',
                   ha='center', va='center',
                   transform=ax.transAxes,
                   family='sans-serif')
            if debug and any('\u4e00' <= c <= '\u9fff' for c in text):
                logger.warning("未找到中文字体，使用sans-serif族")
        
        # 移除坐标轴和边框
        ax.axis('off')
        for spine in ax.spines.values():
            spine.set_visible(False)
        
        # 调整边距
        plt.tight_layout(pad=0)
        
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
            return canvas
        else:
            return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            
    except Exception as e:
        logger.error(f"渲染文本为图像时出错: {str(e)}")
        # 创建一个默认图像
        img = np.zeros((100, max(len(text) * 20, 200), 3), dtype=np.uint8)
        cv2.putText(img, "Text Error", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        return img

def render_text(text, font_size, debug=False):
    """
    渲染文本的外部接口函数
    
    Args:
        text: 文本内容
        font_size: 字体大小
        debug: 是否输出调试信息
        
    Returns:
        文本图像
    """
    img = render_text_as_image(text, font_size, debug)
    
    # 检查是否需要缩放图像
    max_width = 1920  # 最大宽度
    max_height = 1080  # 最大高度
    
    h, w = img.shape[:2]
    if debug:
        logger.info(f"文本原始图像大小: {w}x{h}")
    
    # 如果图像太大，进行等比例缩放
    if w > max_width or h > max_height:
        scale = min(max_width / w, max_height / h)
        new_w = int(w * scale)
        new_h = int(h * scale)
        img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
        if debug:
            logger.info(f"文本缩放后图像大小: {new_w}x{new_h}")
    
    return img 
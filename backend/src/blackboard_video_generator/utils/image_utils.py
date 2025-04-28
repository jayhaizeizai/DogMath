import numpy as np
import cv2
import logging

logger = logging.getLogger(__name__)

def trim_image(img):
    """
    裁剪图像，只保留非背景部分
    
    Args:
        img: 输入图像 (RGB或RGBA)
        
    Returns:
        裁剪后的图像
    """
    # 如果是RGBA图像，使用alpha通道
    if img.shape[2] == 4:
        # 寻找非透明区域
        mask = img[:,:,3] > 0
    else:
        # RGB图像，假设背景是暗色的(30,30,30)
        mask = np.any(img > 60, axis=2)
    
    # 寻找非零区域的边界
    coords = np.argwhere(mask)
    if len(coords) == 0:
        return img
    
    y_min, x_min = coords.min(axis=0)
    y_max, x_max = coords.max(axis=0)
    
    # 添加小边距(2像素)
    y_min = max(0, y_min - 2)
    x_min = max(0, x_min - 2)
    y_max = min(img.shape[0] - 1, y_max + 2)
    x_max = min(img.shape[1] - 1, x_max + 2)
    
    # 裁剪图像
    return img[y_min:y_max+1, x_min:x_max+1]

def blend_image_to_frame(frame, img, x, y, alpha=1.0, debug=False):
    """
    将图像混合到帧中
    
    Args:
        frame: 目标帧
        img: 要混合的图像
        x: x坐标（0-1的比例值）
        y: y坐标（0-1的比例值）
        alpha: 透明度
        debug: 是否输出调试信息
    """
    try:
        if img is None:
            return
            
        # 获取图像尺寸
        img_h, img_w = img.shape[:2]
        frame_h, frame_w = frame.shape[:2]
        
        # 将0-1的比例转换为实际像素位置
        pixel_x = int(x * frame_w)
        pixel_y = int(y * frame_h)
        
        # 计算左上角坐标（考虑图像尺寸的一半）
        x_start = pixel_x - img_w // 2
        y_start = pixel_y - img_h // 2
        
        # 确保坐标在有效范围内
        x_start = max(0, min(x_start, frame_w - img_w))
        y_start = max(0, min(y_start, frame_h - img_h))
        
        # 计算结束位置
        x_end = x_start + img_w
        y_end = y_start + img_h
        
        # 确保不超出边界
        if x_end > frame_w:
            img = img[:, :-(x_end - frame_w)]
            x_end = frame_w
        if y_end > frame_h:
            img = img[:-(y_end - frame_h), :]
            y_end = frame_h
            
        # 在开始添加日志
        if img is not None and debug:
            logger.info(f"混合图像: 位置=({x:.2f}, {y:.2f}), 尺寸={img.shape}")
            
        # 如果是RGBA图像
        if img.shape[2] == 4:
            # 提取alpha通道并应用全局alpha
            src_alpha = img[:, :, 3] / 255.0 * alpha
            src_alpha = np.expand_dims(src_alpha, axis=2)
            
            # 将源图像转换为RGB
            src_rgb = img[:, :, :3]
            
            # 提取目标区域
            dst_region = frame[y_start:y_end, x_start:x_end]
            
            # 混合图像
            blended = dst_region * (1 - src_alpha) + src_rgb * src_alpha
            frame[y_start:y_end, x_start:x_end] = blended.astype(np.uint8)
        else:
            # RGB图像的混合
            dst_region = frame[y_start:y_end, x_start:x_end]
            blended = cv2.addWeighted(dst_region, 1 - alpha, img, alpha, 0)
            frame[y_start:y_end, x_start:x_end] = blended
            
    except Exception as e:
        logger.error(f"图像混合失败: {str(e)}")
        logger.error(f"frame shape: {frame.shape}, img shape: {img.shape}, position: ({x}, {y})")

def create_blackboard_background(width, height):
    """创建黑板背景"""
    # 创建黑色背景
    background = np.ones((height, width, 3), dtype=np.uint8) * np.array([30, 30, 30], dtype=np.uint8)
    
    # 添加轻微噪点和纹理
    noise = np.random.normal(0, 5, background.shape).astype(np.int16)
    background = np.clip(background.astype(np.int16) + noise, 10, 50).astype(np.uint8)
    
    # 添加一些粉笔灰
    dust_mask = np.random.random(background.shape[:2]) > 0.995
    background[dust_mask] = np.array([70, 70, 70])
    
    return background 
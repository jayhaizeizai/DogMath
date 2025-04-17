import os
import subprocess
import logging
import traceback

logger = logging.getLogger(__name__)

def compress_video(input_path, logger=None):
    """使用ffmpeg压缩视频"""
    try:
        # 获取输入文件的目录和文件名
        input_dir = os.path.dirname(input_path)
        input_filename = os.path.basename(input_path)
        filename_without_ext = os.path.splitext(input_filename)[0]
        
        # 创建临时输出文件路径
        temp_output_path = os.path.join(input_dir, f"{filename_without_ext}_compressed.mp4")
        
        # 构建ffmpeg命令
        command = [
            'ffmpeg',
            '-i', input_path,
            '-c:v', 'libx264',
            '-preset', 'medium',
            '-crf', '23',
            '-y',
            temp_output_path
        ]
        
        # 执行ffmpeg命令
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        
        if process.returncode == 0:
            # 压缩成功，替换原文件
            os.replace(temp_output_path, input_path)
            if logger:
                logger.info("视频压缩完成")
        else:
            if logger:
                logger.error(f"视频压缩失败: {stderr.decode()}")
            
    except Exception as e:
        if logger:
            logger.error(f"压缩视频时出错: {str(e)}")
            logger.error(traceback.format_exc())

def get_z_index(element_type):
    """
    获取元素的z-index值
    
    Args:
        element_type: 元素类型
        
    Returns:
        z-index值
    """
    z_index_map = {
        'text': 1,
        'formula': 2,
        'geometry': 3
    }
    return z_index_map.get(element_type, 0) 
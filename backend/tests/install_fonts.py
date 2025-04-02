#!/usr/bin/env python3
import os
import sys
import subprocess
from pathlib import Path
import logging

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("字体安装")

def check_command(command):
    """检查命令是否可用"""
    try:
        subprocess.check_call(['which', command], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except subprocess.CalledProcessError:
        return False

def install_fonts():
    """安装必要的中文字体"""
    logger.info("检查并安装必要的中文字体")
    
    # 检查操作系统
    if sys.platform.startswith('linux'):
        # 检查包管理器
        if check_command('apt'):
            # Debian/Ubuntu
            logger.info("在Debian/Ubuntu系统上安装中文字体")
            try:
                subprocess.check_call(
                    ['sudo', 'apt', 'update'],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE
                )
                subprocess.check_call(
                    ['sudo', 'apt', 'install', '-y', 
                     'fonts-wqy-microhei', 'fonts-wqy-zenhei', 
                     'fonts-noto-cjk', 'fonts-droid-fallback'],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE
                )
                logger.info("中文字体安装成功")
            except subprocess.CalledProcessError as e:
                logger.error(f"安装中文字体失败: {str(e)}")
        elif check_command('yum') or check_command('dnf'):
            # RHEL/CentOS/Fedora
            pkg_mgr = 'dnf' if check_command('dnf') else 'yum'
            logger.info(f"在RHEL/CentOS/Fedora系统上使用{pkg_mgr}安装中文字体")
            try:
                subprocess.check_call(
                    ['sudo', pkg_mgr, 'install', '-y', 
                     'wqy-microhei-fonts', 'wqy-zenhei-fonts', 
                     'google-noto-sans-cjk-sc-fonts'],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE
                )
                logger.info("中文字体安装成功")
            except subprocess.CalledProcessError as e:
                logger.error(f"安装中文字体失败: {str(e)}")
    elif sys.platform == 'darwin':
        # macOS
        if check_command('brew'):
            logger.info("在macOS上使用Homebrew安装中文字体")
            try:
                subprocess.check_call(
                    ['brew', 'tap', 'homebrew/cask-fonts'],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE
                )
                subprocess.check_call(
                    ['brew', 'install', '--cask', 
                     'font-wqy-microhei', 'font-wqy-zenhei', 
                     'font-noto-sans-cjk-sc'],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE
                )
                logger.info("中文字体安装成功")
            except subprocess.CalledProcessError as e:
                logger.error(f"安装中文字体失败: {str(e)}")
        else:
            logger.warning("在macOS上未找到Homebrew，请手动安装中文字体")
    else:
        logger.warning(f"不支持的操作系统: {sys.platform}，请手动安装中文字体")
    
    # 刷新字体缓存
    if sys.platform.startswith('linux'):
        try:
            subprocess.check_call(['fc-cache', '-fv'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            logger.info("字体缓存刷新成功")
        except subprocess.CalledProcessError as e:
            logger.error(f"刷新字体缓存失败: {str(e)}")
    
    # 验证matplotlib可用字体
    try:
        import matplotlib.font_manager as fm
        fonts = [f.name for f in fm.fontManager.ttflist]
        chinese_fonts = [f for f in fonts if any(name in f for name in 
                         ['WenQuanYi', 'Noto Sans CJK', 'Source Han', 'Microsoft YaHei', 'SimHei'])]
        
        if chinese_fonts:
            logger.info(f"找到可用的中文字体: {', '.join(chinese_fonts[:5])}")
            return True
        else:
            logger.warning("未找到可用的中文字体，请手动安装")
            return False
    except ImportError:
        logger.error("导入matplotlib失败，请确保它已安装")
        return False

if __name__ == "__main__":
    install_fonts() 
"""
整合视频生成流程的主脚本
"""
import os
import sys
import argparse
from pathlib import Path
from loguru import logger

# 添加项目根目录到系统路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

# 导入视频合成器
from backend.src.video_composer import main as compose_video

# 配置loguru日志
log_path = Path(os.path.dirname(os.path.dirname(__file__))) / "logs" / "pipeline.log"
os.makedirs(log_path.parent, exist_ok=True)
logger.add(log_path, rotation="10 MB", retention="1 week", level="DEBUG", encoding="utf-8")

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="数学问题视频生成流程")
    parser.add_argument("json_file", help="输入的JSON数据文件路径")
    parser.add_argument("--output_dir", default="backend/output", help="输出目录")
    
    return parser.parse_args()

def main():
    """主函数"""
    args = parse_args()
    
    # 检查输入文件是否存在
    if not os.path.exists(args.json_file):
        logger.error(f"输入文件不存在: {args.json_file}")
        print(f"错误：输入文件不存在: {args.json_file}")
        sys.exit(1)
    
    # 确保输出目录存在
    os.makedirs(args.output_dir, exist_ok=True)
    
    logger.info(f"开始处理JSON文件: {args.json_file}")
    
    try:
        # 运行视频合成流程
        compose_video(args.json_file, args.output_dir)
        
        # 检查最终输出文件是否生成
        output_file = os.path.join(args.output_dir, "output.mp4")
        if os.path.exists(output_file):
            logger.info(f"视频生成成功: {output_file}")
            print(f"视频生成成功: {output_file}")
        else:
            logger.error("视频生成失败，未找到输出文件")
            print("错误：视频生成失败，未找到输出文件")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"处理过程中出现错误: {str(e)}")
        print(f"错误：处理过程中出现错误: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 
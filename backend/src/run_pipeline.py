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
        # 从输入JSON文件名构造期望的输出文件名
        # 例如: "path/to/sample_math_problem_015.json" -> "sample_math_problem_015.mp4"
        json_filename_stem = Path(args.json_file).stem
        desired_output_filename = f"{json_filename_stem}.mp4"
        
        # 运行视频合成流程，传递期望的输出文件名
        compose_video(args.json_file, args.output_dir, final_output_filename=desired_output_filename)
        
        # 检查最终输出文件是否生成
        expected_output_file_path = os.path.join(args.output_dir, desired_output_filename)
        if os.path.exists(expected_output_file_path):
            logger.info(f"视频生成成功: {expected_output_file_path}")
            print(f"视频生成成功: {expected_output_file_path}")
        else:
            logger.error(f"视频生成失败，未找到输出文件: {expected_output_file_path}")
            print(f"错误：视频生成失败，未找到输出文件: {expected_output_file_path}")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"处理过程中出现错误: {str(e)}")
        print(f"错误：处理过程中出现错误: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 
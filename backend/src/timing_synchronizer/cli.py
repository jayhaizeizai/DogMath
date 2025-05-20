#!/usr/bin/env python3
"""
时间同步器的命令行接口
"""

import argparse
import logging
import sys
import json
from pathlib import Path
from typing import Dict

from .synchronizer import TimingSynchronizer
from .config import ADJUSTMENT_STRATEGIES, DEFAULT_ADJUSTMENT_STRATEGY, LOG_LEVEL
from .utils import format_time

# 配置根日志记录器
logger = logging.getLogger(__name__)

def setup_logging(level: str) -> None:
    """设置日志级别"""
    log_level = getattr(logging, level.upper(), logging.INFO)
    
    # 配置根日志记录器
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 设置第三方库日志级别为WARNING，减少噪音
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    
    logger.debug(f"日志级别设置为: {level}")

def parse_args() -> argparse.Namespace:
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="同步音频元数据和内容JSON文件的时间")
    
    parser.add_argument(
        "-a", "--audio-metadata",
        required=True,
        help="音频元数据JSON文件的路径"
    )
    
    parser.add_argument(
        "-c", "--content-json",
        required=True,
        help="内容JSON文件的路径"
    )
    
    parser.add_argument(
        "-o", "--output",
        help="输出JSON文件的路径（默认会使用原文件名加上_synchronized后缀）"
    )
    
    parser.add_argument(
        "-s", "--strategy",
        choices=ADJUSTMENT_STRATEGIES.values(),
        default=DEFAULT_ADJUSTMENT_STRATEGY,
        help="时间调整策略"
    )
    
    parser.add_argument(
        "--log-level",
        default=LOG_LEVEL,
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="日志级别"
    )
    
    parser.add_argument(
        "--report",
        action="store_true",
        help="生成详细的同步报告文件"
    )
    
    return parser.parse_args()

def display_summary(sync_result: Dict) -> None:
    """
    显示同步结果摘要
    
    Args:
        sync_result: 同步操作的结果
    """
    print("\n===== 同步结果摘要 =====")
    print(f"原始总持续时间: {format_time(sync_result['total_blackboard_duration'])}")
    print(f"音频总持续时间: {format_time(sync_result['total_audio_duration'])}")
    
    # 显示每个步骤的时间变化
    print("\n步骤持续时间变化:")
    print("步骤ID  |  原始时间  |  调整后时间  |  差异")
    print("-" * 45)
    
    timing_analysis = sync_result["timing_analysis"]
    for step_id, diff in timing_analysis["step_differences"].items():
        original = diff["original"]
        actual = diff["actual"]
        difference = diff["difference"]
        sign = "+" if difference > 0 else ""
        
        print(f"{step_id:^7} | {format_time(original):^10} | {format_time(actual):^12} | {sign}{difference:+.2f}秒")
    
    # 显示总体差异
    total_diff = timing_analysis["total_difference"]
    sign = "+" if total_diff > 0 else ""
    print("-" * 45)
    print(f"总计    | {format_time(timing_analysis['total_original']):^10} | {format_time(timing_analysis['total_actual']):^12} | {sign}{total_diff:+.2f}秒")
    
    print(f"\n已保存到: {sync_result['saved_to']}")

def save_report(sync_result: Dict, base_path: str) -> None:
    """
    保存详细的同步报告
    
    Args:
        sync_result: 同步操作的结果
        base_path: 基础文件路径
    """
    report_path = Path(base_path).with_suffix('.report.json')
    
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(sync_result, f, ensure_ascii=False, indent=2)
    
    logger.info(f"同步报告已保存到: {report_path}")
    print(f"详细同步报告已保存到: {report_path}")

def main() -> int:
    """
    主函数
    
    Returns:
        int: 退出码，0表示成功，非0表示失败
    """
    try:
        # 解析命令行参数
        args = parse_args()
        
        # 设置日志级别
        setup_logging(args.log_level)
        
        logger.info(f"开始同步处理")
        logger.info(f"音频元数据文件: {args.audio_metadata}")
        logger.info(f"内容JSON文件: {args.content_json}")
        
        # 创建同步器实例
        synchronizer = TimingSynchronizer(args.audio_metadata, args.content_json)
        
        # 执行同步操作
        result = synchronizer.synchronize(output_path=args.output)
        
        # 显示结果摘要
        display_summary(result)
        
        # 如果请求，保存详细报告
        if args.report:
            output_path = args.output or result["saved_to"]
            save_report(result, output_path)
        
        logger.info("同步处理完成")
        return 0
        
    except FileNotFoundError as e:
        logger.error(f"文件未找到: {e}")
        print(f"错误: 文件未找到 - {e}")
        return 1
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON解析错误: {e}")
        print(f"错误: JSON格式无效 - {e}")
        return 1
        
    except KeyboardInterrupt:
        logger.warning("操作被用户中断")
        print("\n操作已取消")
        return 130
        
    except Exception as e:
        logger.exception(f"处理过程中发生错误: {e}")
        print(f"错误: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 
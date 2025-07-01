import subprocess
import os
import time
import logging

def setup_logging():
    """Configures logging to output to both console and a file."""
    log_formatter = logging.Formatter("%(asctime)s [%(levelname)s] - %(message)s")
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # File handler
    file_handler = logging.FileHandler("video_generation.log", mode='a', encoding='utf-8')
    file_handler.setFormatter(log_formatter)
    root_logger.addHandler(file_handler)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_formatter)
    root_logger.addHandler(console_handler)

def generate_video_for_file(json_file_path):
    """
    Runs the video generation pipeline for a single JSON file and logs the process.
    """
    command = [
        "python",
        "backend/src/run_pipeline.py",
        json_file_path
    ]
    start_time = time.time()
    try:
        logging.info(f"开始处理: {json_file_path}")
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        end_time = time.time()
        duration = end_time - start_time

        if process.returncode == 0:
            logging.info(f"成功: {json_file_path} (耗时: {duration:.2f} 秒)")
            if stdout:
                logging.info(f"  输出:\n{stdout.decode('utf-8', errors='ignore')}")
        else:
            logging.error(f"失败: {json_file_path} (返回码: {process.returncode}, 耗时: {duration:.2f} 秒)")
            if stderr:
                logging.error(f"  错误信息:\n{stderr.decode('utf-8', errors='ignore')}")
            if stdout: # Sometimes errors are printed to stdout
                logging.info(f"  输出 (可能包含错误信息):\n{stdout.decode('utf-8', errors='ignore')}")
        return True
    except Exception as e:
        end_time = time.time()
        duration = end_time - start_time
        logging.error(f"执行命令时发生异常 {json_file_path} (耗时: {duration:.2f} 秒): {e}")
        return False

def main():
    setup_logging() # Initialize logging

    base_path = "backend/data/samples/mvs_json/"
    start_index = 8
    end_index = 260

    total_start_time = time.time()
    processed_files_count = 0
    successful_files_count = 0

    logging.info("视频批量生成开始.")

    for i in range(start_index, end_index + 1):
        file_index_str = str(i).zfill(3)
        json_file_name = f"sample_math_problem_{file_index_str}.json"
        json_file_path = os.path.join(base_path, json_file_name)

        if os.path.exists(json_file_path):
            logging.info(f"找到文件: {json_file_path}")
            processed_files_count += 1
            if generate_video_for_file(json_file_path):
                successful_files_count +=1
            logging.info("-" * 50) # Separator for readability in logs
        else:
            # logging.debug(f"文件未找到，跳过: {json_file_path}") # Optional: log skipped files as debug
            pass

    total_end_time = time.time()
    total_duration = total_end_time - total_start_time
    logging.info("视频批量生成完成.")
    logging.info(f"总共检查文件数 (在指定范围内): {end_index - start_index + 1}")
    logging.info(f"实际找到并尝试处理的文件数: {processed_files_count}")
    logging.info(f"成功生成视频的文件数: {successful_files_count}")
    logging.info(f"总耗时: {total_duration:.2f} 秒")


if __name__ == "__main__":
    main()

"""
Google Cloud Text-to-Speech API接口封装
"""
import os
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
from loguru import logger

from .utils.audio_utils import save_audio_to_wav, merge_audio_files

# 尝试导入配置文件，如果不存在则使用默认值
try:
    from .config import GOOGLE_CLOUD, TEXT_TO_SPEECH
    logger.info("已加载配置文件")
except ImportError:
    logger.warning("未找到config.py，使用默认配置")
    GOOGLE_CLOUD = {
        "api_key": None,
        "service_account_file": None,
        "use_api_key": True,
        "project_id": None
    }
    TEXT_TO_SPEECH = {
        "default_language": "zh-CN",
        "default_voice": "zh-CN-Standard-A"
    }

class GoogleTextToSpeech:
    """
    Google Cloud TTS API 接口类
    """
    def __init__(self, 
                 language_code: Optional[str] = None, 
                 voice_name: Optional[str] = None,
                 output_dir: Optional[str] = None,
                 api_key: Optional[str] = None,
                 service_account_file: Optional[str] = None):
        """
        初始化Google TTS客户端
        
        Args:
            language_code: 语言代码，如果为None则使用配置文件中的默认值
            voice_name: 声音名称，如果为None则使用配置文件中的默认值
            output_dir: 音频输出目录
            api_key: Google Cloud API密钥，如果未提供则使用配置文件
            service_account_file: 服务账号密钥文件路径，如果未提供则使用配置文件
        """
        # 从配置或参数获取语言和声音设置
        self.language_code = language_code or TEXT_TO_SPEECH.get("default_language")
        self.voice_name = voice_name or TEXT_TO_SPEECH.get("default_voice")
        self.output_dir = output_dir or os.path.join(os.getcwd(), "output", "audio")
        
        # 认证信息 - 优先使用参数提供的值
        self.api_key = api_key
        self.service_account_file = service_account_file
        
        # 如果未提供认证信息，则使用配置文件中的值
        if not self.api_key and not self.service_account_file:
            if GOOGLE_CLOUD.get("use_api_key", True):
                self.api_key = GOOGLE_CLOUD.get("api_key")
            else:
                self.service_account_file = GOOGLE_CLOUD.get("service_account_file")
                
        # 确保输出目录存在
        os.makedirs(self.output_dir, exist_ok=True)
        
    def synthesize_speech(self, 
                          text: str, 
                          output_path: Optional[str] = None,
                          voice_name: Optional[str] = None,
                          language_code: Optional[str] = None) -> str:
        """
        将文本转换为语音
        
        Args:
            text: 要转换的文本内容
            output_path: 输出文件路径
            voice_name: 声音名称，覆盖默认设置
            language_code: 语言代码，覆盖默认设置
        
        Returns:
            生成的音频文件路径
        """
        # 使用提供的参数或默认参数
        voice_name = voice_name or self.voice_name
        language_code = language_code or self.language_code
        
        # 准备API请求数据
        request_data = {
            "input": {
                "markup": text
            },
            "voice": {
                "languageCode": language_code,
                "name": voice_name
            },
            "audioConfig": {
                "audioEncoding": "LINEAR16"
            }
        }
        
        # 如果未指定输出路径，生成一个临时路径
        if not output_path:
            tmp_filename = f"tts_{hash(text) % 10000}.wav"
            output_path = os.path.join(self.output_dir, tmp_filename)
        
        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        try:
            # 使用临时文件存储请求数据
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
                json.dump(request_data, temp_file)
                temp_file_path = temp_file.name
            
            # 构建curl命令
            curl_command = [
                'curl', '-X', 'POST', 
                '-H', 'Content-Type: application/json'
            ]
            
            # 根据提供的认证方式添加认证头
            if self.api_key:
                # 使用API密钥
                curl_command.extend(['-H', f'X-Goog-Api-Key: {self.api_key}'])
            elif self.service_account_file:
                # 使用服务账号
                if os.path.exists(self.service_account_file):
                    # 设置环境变量并使用服务账号文件
                    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = os.path.abspath(self.service_account_file)
                    
                    # 读取服务账号文件获取项目ID
                    try:
                        with open(self.service_account_file, 'r') as f:
                            sa_data = json.load(f)
                            project_id = sa_data.get('project_id')
                    except Exception as e:
                        logger.warning(f"无法读取服务账号文件获取项目ID: {str(e)}")
                        project_id = GOOGLE_CLOUD.get("project_id")
                    
                    # 使用gcloud命令获取访问令牌
                    try:
                        # 直接使用Google应用默认凭据
                        import google.auth
                        from google.auth.transport.requests import Request as GoogleRequest
                        
                        # 获取凭据
                        credentials, project = google.auth.default()
                        
                        # 确保凭据有效
                        if credentials.expired:
                            credentials.refresh(GoogleRequest())
                        
                        # 获取访问令牌
                        token = credentials.token
                        
                        # 添加认证头
                        curl_command.extend([
                            '-H', f'Authorization: Bearer {token}'
                        ])
                        
                        if project_id:
                            curl_command.extend([
                                '-H', f'X-Goog-User-Project: {project_id}'
                            ])
                    except ImportError:
                        logger.warning("未安装google-auth库，回退到使用gcloud命令")
                        # 使用gcloud命令获取访问令牌
                        curl_command.extend([
                            '-H', f'Authorization: Bearer $(gcloud auth application-default print-access-token)'
                        ])
                        if project_id:
                            curl_command.extend([
                                '-H', f'X-Goog-User-Project: {project_id}'
                            ])
                else:
                    logger.warning(f"服务账号文件不存在: {self.service_account_file}，使用默认认证")
                    curl_command.extend([
                        '-H', f'X-Goog-User-Project: $(gcloud config list --format=\'value(core.project)\')',
                        '-H', f'Authorization: Bearer $(gcloud auth print-access-token)'
                    ])
            else:
                # 使用默认的gcloud认证
                curl_command.extend([
                    '-H', f'X-Goog-User-Project: $(gcloud config list --format=\'value(core.project)\')',
                    '-H', f'Authorization: Bearer $(gcloud auth print-access-token)'
                ])
                
            # 添加数据和URL
            curl_command.extend([
                '--data', f'@{temp_file_path}',
                'https://texttospeech.googleapis.com/v1/text:synthesize'
            ])
            
            # 执行curl命令并获取响应
            process = subprocess.Popen(
                ' '.join(curl_command),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=True
            )
            stdout, stderr = process.communicate()
            
            # 检查是否有错误
            if process.returncode != 0:
                logger.error(f"Google TTS API请求失败: {stderr.decode('utf-8')}")
                raise Exception(f"Google TTS API请求失败: {stderr.decode('utf-8')}")
            
            # 解析响应
            response = json.loads(stdout)
            
            # 保存音频文件
            if 'audioContent' in response:
                audio_content = response['audioContent']
                save_audio_to_wav(audio_content, output_path)
                logger.info(f"音频已保存到: {output_path}")
            else:
                raise Exception(f"API响应中没有发现audioContent: {response}")
            
            # 删除临时文件
            os.unlink(temp_file_path)
            
            return output_path
            
        except Exception as e:
            logger.error(f"语音合成失败: {str(e)}")
            raise
    
    def synthesize_multiple(self, 
                            texts: List[str], 
                            output_path: str,
                            voice_name: Optional[str] = None,
                            language_code: Optional[str] = None) -> str:
        """
        将多个文本片段转换为语音并合并为一个文件
        
        Args:
            texts: 要转换的文本列表
            output_path: 最终输出文件路径
            voice_name: 声音名称，覆盖默认设置
            language_code: 语言代码，覆盖默认设置
        
        Returns:
            合并后的音频文件路径
        """
        # 创建临时目录存放单独的音频文件
        with tempfile.TemporaryDirectory() as temp_dir:
            audio_files = []
            
            # 转换每个文本片段
            for i, text in enumerate(texts):
                temp_output = os.path.join(temp_dir, f"part_{i}.wav")
                audio_file = self.synthesize_speech(
                    text=text,
                    output_path=temp_output,
                    voice_name=voice_name,
                    language_code=language_code
                )
                audio_files.append(audio_file)
            
            # 合并所有音频文件
            merged_file = merge_audio_files(audio_files, output_path)
            
            return merged_file 
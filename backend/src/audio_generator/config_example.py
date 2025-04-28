"""
配置文件示例 - 复制为 config.py 并填写你的API密钥
注意: config.py 不会被提交到Git仓库
"""

# Google Cloud API配置
GOOGLE_CLOUD = {
    # API密钥方式 (优先)
    "api_key": "YOUR_API_KEY_HERE",
    
    # 或者服务账号文件路径
    "service_account_file": "/path/to/service-account.json",
    
    # 优先使用API密钥还是服务账号 (True使用API密钥，False使用服务账号)
    "use_api_key": True,
    
    # 项目ID
    "project_id": "your-project-id"
}

# 文本转语音默认配置
TEXT_TO_SPEECH = {
    "default_language": "zh-CN",
    "default_voice": "zh-CN-Standard-A"
} 
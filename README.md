# 数学题视频生成系统

这个系统可以根据数学题的JSON格式数据，生成包含黑板视频和语音解说的教学视频。

## 系统功能

1. 读取数学题的JSON格式数据
2. 生成黑板教学视频
3. 生成语音解说
4. 将黑板视频和语音解说合成为完整的教学视频

## 目录结构

```
.
├── backend/
│   ├── data/                # 数据文件
│   │   └── samples/         # 样本数据
│   ├── logs/                # 日志文件
│   ├── output/              # 输出文件
│   │   └── audio_segments/  # 音频片段
│   └── src/                 # 源代码
│       ├── audio_generator/     # 音频生成模块
│       ├── blackboard_video_generator/  # 黑板视频生成模块
│       ├── video_composer.py    # 视频合成模块
│       └── run_pipeline.py      # 流程运行脚本
└── README.md                # 说明文档
```

## 使用方法

### 前置要求

1. Python 3.8+
2. FFmpeg（用于视频合成）
3. 安装所需的Python包：
   ```
   pip install loguru google-cloud-texttospeech opencv-python numpy
   ```

### 运行流程

使用`run_pipeline.py`脚本来处理一个完整的视频生成流程：

```
python backend/src/run_pipeline.py <JSON文件路径> [--output_dir <输出目录>]
```

例如：

```
python backend/src/run_pipeline.py backend/data/samples/math_problems/sample_math_problem_011.json
```

默认情况下，输出文件将保存在`backend/output/`目录中。

### 单独使用各个模块

如果你想单独使用各个模块：

1. 生成音频片段：
   ```
   python backend/src/audio_generator/example.py --segmented <JSON文件路径> <输出目录>
   ```

2. 生成黑板视频：
   ```
   python backend/src/blackboard_video_generator/example.py <JSON文件路径> <输出视频文件路径>
   ```

3. 合成视频：
   ```
   python backend/src/video_composer.py <JSON文件路径>
   ```

## JSON数据格式

系统接受以下格式的JSON数据：

```json
{
  "metadata": {
    "problem_id": "示例ID",
    "source_image": "图片源文件",
    "difficulty": "难度级别",
    "estimated_duration": 120,
    "knowledge_tags": ["标签1", "标签2"],
    "created_at": "创建时间"
  },
  "blackboard": {
    "background": "背景类型",
    "resolution": [1920, 1080],
    "steps": [
      {
        "step_id": 1,
        "title": "步骤标题",
        "duration": 15,
        "elements": [
          // 各种视觉元素
        ]
      }
    ]
  },
  "audio": {
    "narration": [
      {
        "text": "解说文本",
        "start_time": 0,
        "end_time": 3,
        "voice_config": { "speed": 1.0, "pitch": 0 },
        "ssml": "<speak>SSML格式的解说</speak>"
      }
    ],
    "background_music": "背景音乐设置"
  }
}
```

## 日志

系统日志保存在`backend/logs/`目录中，包括以下日志文件：

- `audio_generator.log` - 音频生成日志
- `blackboard_video_generator.log` - 黑板视频生成日志
- `video_composer.log` - 视频合成日志
- `pipeline.log` - 流程运行日志 
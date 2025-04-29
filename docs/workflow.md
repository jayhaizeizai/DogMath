# 视频生成工作流程文档

## 系统架构

本系统由三个主要组件构成：
- 音频生成器 (audio_generator)
- 数字人视频生成器 (teacher_video_generator)
- 黑板内容视频生成器 (blackboard_video_generator)

主程序负责协调这些组件，确保生成的时间轴分段正确对齐并拼接成最终视频。

## 工作流程

### 1. 内容准备阶段

1. 解析输入JSON文件，提取以下内容：
   - 讲解文本/SSML（用于音频生成）
   - 数字人表情和动作设置
   - 黑板内容描述（公式、几何图形等）
   - 时间轴标记（确保各个部分按时间正确对齐）

2. 将内容按照时间轴分割成2-3秒的小段，每段包含：
   - 唯一的序号或时间戳标识
   - 这一时段内的文本内容
   - 这一时段内的黑板内容变更
   - 这一时段内的数字人动作/表情

### 2. 音频生成阶段

1. audio_generator组件接收分段的文本内容
2. 为每段文本生成对应的短音频片段
3. 每个音频片段使用统一的命名格式保存：`audio_{timestamp}_{segment_id}.wav`
4. 返回包含所有片段路径及时间信息的元数据

```python
# 示例代码
def generate_segmented_audio(text_segments):
    audio_segments = []
    for idx, segment in enumerate(text_segments):
        output_path = f"output/audio_{segment['timestamp']}_{idx}.wav"
        audio_file = tts.synthesize_speech(text=segment['text'], output_path=output_path)
        audio_segments.append({
            'id': idx,
            'timestamp': segment['timestamp'],
            'path': audio_file,
            'duration': get_audio_duration(audio_file)
        })
    return audio_segments
```

### 3. 数字人视频生成阶段

1. teacher_video_generator组件接收分段的音频文件和对应的表情/动作设置
2. 为每段音频生成对应的数字人短视频片段
3. 视频片段使用与音频相同的命名格式：`teacher_{timestamp}_{segment_id}.mp4`
4. 返回包含所有视频片段路径及时间信息的元数据

```python
# 示例代码
def generate_segmented_teacher_videos(audio_segments, expressions):
    video_segments = []
    for segment in audio_segments:
        output_path = f"output/teacher_{segment['timestamp']}_{segment['id']}.mp4"
        # 调用API生成数字人视频
        video_file = generate_teacher_video(
            audio_path=segment['path'],
            expression=expressions[segment['id']],
            output_path=output_path
        )
        video_segments.append({
            'id': segment['id'],
            'timestamp': segment['timestamp'],
            'path': video_file,
            'duration': get_video_duration(video_file)
        })
    return video_segments
```

### 4. 黑板内容生成阶段

1. blackboard_video_generator组件接收分段的黑板内容描述
2. 为每段内容生成对应的黑板视频片段
3. 视频片段使用与其他组件相同的命名格式：`blackboard_{timestamp}_{segment_id}.mp4`
4. 返回包含所有视频片段路径及时间信息的元数据

```python
# 示例代码
def generate_segmented_blackboard_videos(blackboard_segments):
    video_segments = []
    for segment in blackboard_segments:
        output_path = f"output/blackboard_{segment['timestamp']}_{segment['id']}.mp4"
        video_file = blackboard_generator.generate_video(
            data=segment['content'],
            output_path=output_path
        )
        video_segments.append({
            'id': segment['id'],
            'timestamp': segment['timestamp'],
            'path': video_file,
            'duration': get_video_duration(video_file)
        })
    return video_segments
```

### 5. 视频合成阶段

1. 主程序接收所有生成的片段元数据
2. 根据时间戳/序号对视频片段进行排序和对齐
3. 对于每个时间段，将数字人视频和黑板视频合成为单一视频
4. 将所有时间段的视频按顺序拼接为最终完整视频

```python
# 示例代码
def merge_video_segments(teacher_segments, blackboard_segments):
    # 按时间戳/ID排序
    teacher_segments.sort(key=lambda x: (x['timestamp'], x['id']))
    blackboard_segments.sort(key=lambda x: (x['timestamp'], x['id']))
    
    # 合成每个片段
    merged_segments = []
    for t_seg, b_seg in zip(teacher_segments, blackboard_segments):
        # 确保片段ID匹配
        assert t_seg['id'] == b_seg['id'], "片段ID不匹配"
        
        output_path = f"output/merged_{t_seg['timestamp']}_{t_seg['id']}.mp4"
        # 合成数字人和黑板视频
        merged_file = combine_videos(
            teacher_video=t_seg['path'],
            blackboard_video=b_seg['path'],
            output_path=output_path
        )
        merged_segments.append({
            'id': t_seg['id'],
            'timestamp': t_seg['timestamp'],
            'path': merged_file
        })
    
    # 拼接所有片段为最终视频
    final_output = "output/final_video.mp4"
    concat_videos([seg['path'] for seg in merged_segments], final_output)
    return final_output
```

### 6. 清理阶段

合成完成后，可选择删除中间生成的片段文件，仅保留最终输出视频文件。

## 技术实现

### 视频片段生成格式

- 使用MP4格式存储视频片段
- 使用WAV格式存储音频片段
- 考虑使用HLS格式以支持流式处理

### 视频合成技术

- 使用FFmpeg进行视频合并操作
- 使用moviepy库处理视频拼接与合成
- 确保音频与视频正确同步

### 文件命名规范

为确保片段正确对齐，所有生成的文件应遵循统一的命名规范：
- `{component_type}_{timestamp}_{segment_id}.{extension}`

其中：
- component_type: 组件类型（audio/teacher/blackboard）
- timestamp: 时间戳（毫秒级）
- segment_id: 片段序号（整数）
- extension: 文件扩展名（mp4/wav）

## 注意事项

1. 确保所有组件生成的片段长度一致，避免拼接时出现音画不同步
2. 在片段合成过程中处理好转场效果，确保视频流畅自然
3. 妥善处理最后一个片段可能产生的特殊情况
4. 使用日志记录整个过程，方便调试和故障排除
5. 考虑添加错误处理和重试机制，提高系统鲁棒性 
# 工作流程文档

## 1. 输入数据

### 1.1 数据来源
- 输入文件：`backend/data/samples/input.json`
- 包含内容：
  - 时间轴数据
  - 文本内容
  - 几何图形数据
  - LaTeX公式
  - 动画效果配置

### 1.2 数据格式
```json
{
  "timeline": [
    {
      "type": "text/geometry/formula",
      "content": "...",
      "animation": {...},
      "position": {...}
    }
  ]
}
```

## 2. 处理流程

### 2.1 入口文件：`backend/src/video_generator/example.py`
1. 加载配置文件
2. 初始化日志系统
3. 创建视频生成器实例
4. 调用生成方法

### 2.2 视频生成器：`backend/src/video_generator/blackboard_video_generator.py`
1. 初始化阶段
   - 设置视频参数（分辨率、帧率等）
   - 初始化渲染器
   - 设置黑板背景

2. 数据处理阶段
   - 解析时间轴数据
   - 处理几何图形数据
   - 处理文本和公式

3. 渲染阶段
   - 创建黑板背景
   - 逐帧渲染元素
   - 应用动画效果

### 2.3 动画处理：`backend/src/video_generator/blackboard_animator.py`
1. 动画功能实现
   - 动画效果管理
   - 帧动画控制
   - 过渡效果处理

2. 渲染方法
   - `render_text`: 文本渲染
   - `render_formula`: LaTeX公式渲染
   - `render_geometry`: 几何图形渲染

### 2.4 工具类：
1. SVG解析器：`backend/src/video_generator/svg_parser.py`
   - SVG路径解析
   - 路径命令处理
   - 坐标转换

2. 黑板纹理：`backend/src/video_generator/blackboard_texture.py`
   - 黑板背景生成
   - 纹理效果处理

3. 动画效果：`backend/src/video_generator/animations.py`
   - 动画效果定义
   - 动画参数处理

## 3. 输出处理

### 3.1 视频输出
1. 文件位置：`backend/output/`
2. 输出格式：
   - 主视频：`output.mp4`
   - 临时文件：`temp/`目录

### 3.2 日志输出
1. 日志文件：`backend/logs/`
2. 日志内容：
   - 渲染过程
   - 错误信息
   - 性能数据

## 4. 关键函数调用链

### 4.1 主要流程
```
example.py
  └── BlackboardVideoGenerator.generate()
      ├── _initialize_video()
      ├── _process_timeline()
      │   ├── render_text()
      │   ├── render_formula()
      │   └── render_geometry()
      └── _finalize_video()
```

### 4.2 渲染流程
```
_render_and_add_to_timeline()
  ├── render_text()
  │   └── BlackboardAnimator.render_text()
  ├── render_formula()
  │   └── BlackboardAnimator.render_formula()
  └── render_geometry()
      └── BlackboardAnimator.render_geometry()
```

## 5. 数据流转

### 5.1 输入数据流转
1. JSON配置文件
   → 解析为Python对象
   → 时间轴数据结构
   → 渲染元素列表

### 5.2 渲染数据流转
1. 文本数据
   → 字体处理
   → 图像生成
   → 帧合成

2. 几何数据
   → SVG解析
   → 路径处理
   → 图像生成
   → 帧合成

3. 公式数据
   → LaTeX解析
   → 图像生成
   → 帧合成

## 6. 错误处理流程

### 6.1 异常捕获
1. 文件操作异常
   → 日志记录
   → 降级处理
   → 错误报告

2. 渲染异常
   → 错误图像生成
   → 日志记录
   → 继续处理

3. 编码器异常
   → 备用编码器
   → 重试机制
   → 错误报告 
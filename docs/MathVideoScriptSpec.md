# MathVideoScript 规范文档

## 1. 概述

MathVideoScript 是一个用于生成数学题目讲解视频的标准化脚本格式。本文档详细说明了脚本的结构、格式要求和最佳实践。

## 2. 基本结构

MathVideoScript 由以下四个主要部分组成：
- 元数据 (metadata)
- 黑板内容 (blackboard)
- 音频内容 (audio)
- 知识点标注 (annotations)

### 2.1 完整结构示例

```json
{
  "metadata": {
    "problem_id": "string",         // 题目唯一标识符
    "source_image": "string",       // 原题目图片
    "difficulty": "string",         // 难度等级
    "estimated_duration": "number", // 预计时长（秒）
    "knowledge_tags": ["string"],   // 知识点标签
    "created_at": "timestamp"       // 创建时间
  },
  "blackboard": {
    "background": "string",         // 黑板样式
    "resolution": [1920, 1080],     // 视频分辨率
    "steps": []                     // 解题步骤
  },
  "audio": {
    "narration": []               // 讲解音频
  },
  "annotations": {
    "key_points": []               // 知识点标注
  }
}
```

### 2.1 坐标系统

所有元素的位置使用相对坐标系统，范围为0-1：
- x坐标：0表示最左边，1表示最右边
- y坐标：0表示最上边，1表示最下边
- 坐标原点(0,0)位于左上角
- 所有position属性都使用这个相对坐标系统，格式为 `[x, y]`

**注意：** 几何图形(geometry)类型的SVG路径内部使用的是不同的坐标系统，详见3.3节说明。

例如：
- `"position": [0.5, 0.5]` 表示元素位于画面正中心
- `"position": [0, 0]` 表示元素位于左上角
- `"position": [1, 1]` 表示元素位于右下角
- `"position": [0.2, 0.3]` 表示元素位于距左边20%、距上边30%的位置

这种相对坐标系统的优点：
- 与分辨率无关，确保内容在不同分辨率下保持一致的相对位置
- 便于进行位置的比例计算
- 简化布局设计

### 2.2 结构灵活性

脚本可以根据需要包含以下部分的一个或多个：
- 必须包含：元数据(metadata)和黑板内容(blackboard)
- 可选包含：音频内容(audio)和知识点标注(annotations)

简化版的结构示例：
```json
{
  "metadata": {
    "problem_id": "string",
    "difficulty": "string",
    "estimated_duration": number,
    "knowledge_tags": ["string"],
    "created_at": "timestamp"
  },
  "blackboard": {
    "background": "string",
    "resolution": [width, height],
    "steps": []
  }
}
```

## 3. 元素类型详解

### 3.1 文本类型 (text)

用于显示普通文字说明。

```json
{
  "type": "text",
  "content": "已知：在⊙O中，AB是弦，OC⊥AB于点D",
  "position": [0.1, 0.2],  // x=10%, y=20%的位置
  "font_size": 28,
  "animation": {
    "enter": "fade_in",
    "exit": "fade_out",
    "duration": 1
  }
}
```

### 3.2 公式类型 (formula)

用于显示数学公式，使用LaTeX语法。

```json
{
  "type": "formula",
  "content": "\\begin{cases} OA = 5 \\\\ OD = 3 \\end{cases}",
  "position": [0.3, 0.4],  // x=30%, y=40%的位置
  "font_size": 32,
  "animation": {
    "enter": "slide_in_left",
    "exit": "fade_out",
    "duration": 1.5
  }
}
```

**JSON中的LaTeX转义示例:**
```json
"content": "\\text{在直角三角形 } \\( OAD \\) \\text{ 中，} \\angle AOD = 90^{\\circ}"
```
注意每个LaTeX的反斜杠`\`在JSON中需要写为`\\`，而界定符号`\(`和`\)`需要写为`\\(`和`\\)`。

### 3.3 几何图形类型 (geometry)

用于绘制几何图形，使用SVG路径语法。几何图形可以包含多个组件：基本图形（如圆形、线段）和标签。

示例：
```json
{
  "type": "geometry",
  "content": {
    "circle": {
      "path": "M 50 50 m -40 0 a 40 40 0 1 0 80 0 a 40 40 0 1 0 -80 0",
      "style": {
        "stroke": "white",
        "stroke-width": 2,
        "fill": "none"
      }
    },
    "line": [
      {
        "path": "M 20 60 L 80 60",
        "style": {
          "stroke": "white",
          "stroke-width": 2
        }
      }
    ],
    "label": [
      {
        "text": "O",
        "position": [50, 50],
        "font_size": 12,
        "style": {
          "fill": "white"
        }
      },
      {
        "text": "A",
        "position": [20, 60],
        "font_size": 12,
        "style": {
          "fill": "white"
        }
      }
    ]
  },
  "position": [0.5, 0.5],
  "scale": 1.2
}
```

#### 3.3.1 几何图形组件说明

1. **基本图形**
   - `circle`: 圆形
   - `line`: 线段（可以是数组包含多条线）
   - `path`: 自定义路径

2. **标签 (label)**
   - 用于在几何图形上添加点的标记、文字说明等
   - 属性说明：
     - `text`: 标签文本内容
     - `position`: 标签位置 [x, y]，使用与SVG相同的坐标系统（0-100）
     - `font_size`: 字体大小
     - `style`: 样式设置
       - `fill`: 填充颜色
       - 其他可选的样式属性

3. **样式设置**
   每个图形组件都可以设置 `style` 属性：
   - `stroke`: 线条颜色
   - `stroke-width`: 线条宽度
   - `fill`: 填充颜色
   - `stroke-dasharray`: 虚线样式（空格分隔值）

### 3.4 函数图像类型 (graph)

用于绘制函数图像和坐标系。

```json
{
  "type": "graph",
  "content": {
    "function": "y = x^2",
    "domain": [-5, 5],
    "range": [-2, 10],
    "grid": {
      "show": true,
      "step": 1
    },
    "axis": {
      "x": {
        "label": "x",
        "show_numbers": true
      },
      "y": {
        "label": "y",
        "show_numbers": true
      }
    }
  },
  "position": [0.6, 0.6],  // x=60%, y=60%的位置
  "size": [0.3, 0.2],      // 宽度30%，高度20%的画面大小
  "animation": {
    "enter": "draw_path",
    "exit": "fade_out",
    "duration": 3
  }
}
```

## 4. 动画效果

支持的动画类型包括：
- `fade_in`: 淡入
- `fade_out`: 淡出
- `slide_in_left`: 从左滑入
- `slide_in_right`: 从右滑入
- `slide_in_top`: 从上滑入
- `slide_in_bottom`: 从下滑入
- `draw_path`: 路径绘制
- `highlight`: 高亮显示

## 5. 音频配置

### 5.1 语音配置

```json
{
  "narration": [
    {
      "text": "我们来解这道圆的问题",
      "start_time": 0,
      "end_time": 3,
      "voice_config": {
        "speed": 1.0,
        "pitch": 1.0
      },
      "ssml": "<speak>我们来解这道<emphasis>圆</emphasis>的问题</speak>"
    }
  ]
}
```

#### 5.1.1 语音设置说明

- `text`: 朗读文本内容
- `start_time`: 开始时间（秒）
- `end_time`: 结束时间（秒）
- `voice_config`: 语音参数配置
  - `speed`: 语速，1.0为正常速度
  - `pitch`: 音调，1.0为正常音调
- `ssml`: 语音合成标记语言(SSML)格式的文本，支持更丰富的语音表现力

**注意：** 语音合成所使用的具体声音（speaker/voice）不在JSON脚本中指定，而是由系统配置文件(`config.py`)统一控制。这样可以确保所有生成的内容保持声音的一致性，并允许在不修改内容脚本的情况下切换不同的声音。
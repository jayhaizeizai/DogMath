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
    "narration": [],               // 讲解音频
    "background_music": "string"    // 背景音乐
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

用于绘制几何图形，使用SVG路径语法。

**坐标系统说明：**

几何图形使用两种坐标系统：
1. **元素整体位置**：使用0-1范围的相对坐标系，通过`position`属性指定
2. **SVG路径内部**：使用像素坐标系（通常为0-100范围），用于定义图形的具体形状

这种双坐标系设计的理由：
- 整体位置使用相对坐标确保跨分辨率兼容性和布局一致性
- SVG路径内部使用像素坐标简化图形设计和调试，符合SVG标准惯例

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
    "line": {
      "path": "M 10 10 L 90 90",
      "style": {
        "stroke": "white",
        "stroke-width": 2,
        "stroke-dasharray": "5 5"
      }
    }
  },
  "position": [0.5, 0.5],  // 使用相对坐标(0-1)定位整个图形
  "scale": 1.0,            // 控制整体缩放
  "animation": {
    "enter": "draw_path",
    "exit": "fade_out",
    "duration": 2
  }
}
```

**最佳实践：**
- SVG路径坐标推荐使用0-100范围，以便于设置和理解
- 通常将(50,50)作为SVG路径的中心点
- 使用`position`属性调整整个图形在画面中的位置
- 使用`scale`属性控制图形的整体大小

**重要说明：**
1. SVG路径使用空格（而非逗号）分隔坐标值和参数
   - 正确: `"M 50 50 m -40 0 a 40 40 0 1 0 80 0"`
   - 错误: `"M 50 50 m -40, 0 a 40,40 0 1,0 80,0"`
   
2. 特殊样式属性如`stroke-dasharray`也需使用空格分隔值
   - 正确: `"stroke-dasharray": "5 5"`
   - 错误: `"stroke-dasharray": "5,5"`

3. SVG路径命令参考:
   - `M x y` - 移动到坐标(x,y)
   - `L x y` - 画线到坐标(x,y)
   - `A rx ry x-axis-rotation large-arc-flag sweep-flag x y` - 绘制椭圆弧
   - `Z` - 闭合路径

4. **命令支持限制:** 当前系统主要支持以下SVG命令:
   - 完全支持: `M`(移动), `L`(直线), `Z`(闭合)
   - 有限支持: `A/a`(弧形) - 会简化为直线段，可能丢失曲率

5. **绘制圆形的最佳实践:**
   - 圆形可以使用多个线段近似表示: `M 50 20 L 80 50 L 50 80 L 20 50 Z`
   - 对于更精确的圆形，可以使用更多的直线段
   - 当使用弧形命令(`a`)绘制圆时，确保参数之间使用空格而非逗号分隔

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
        "speaker": "teacher_female",
        "speed": 1.0,
        "pitch": 1.0
      },
      "ssml": "<speak>我们来解这道<emphasis>圆</emphasis>的问题</speak>"
    }
  ]
}
```

### 5.2 SSML标记

支持的SSML标记：
```xml
<speak>
  <say-as interpret-as="math">OA=5</say-as>
  <emphasis>重要概念</emphasis>
  <break time="1s"/>
</speak>
```

## 6. 最佳实践

### 6.1 步骤划分
- 每个步骤建议持续20-60秒
- 步骤之间保留2-3秒过渡时间
- 重要概念需要适当停顿

### 6.2 画面布局
- 主要内容保持在中央区域 [0.15, 0.15] 到 [0.85, 0.85] 的范围内
- 重要内容放置在黄金分割点位置 (约0.618或0.382)
- 避免内容过于密集
- 标题文字建议位置：[0.5, 0.1]（上方居中）
- 注释文字建议位置：[0.5, 0.9]（下方居中）
- 对称内容使用对称的相对坐标，如[0.3, 0.5]和[0.7, 0.5]

### 6.2.1 坐标系统使用建议
- 使用小数点表示相对位置，如0.5而不是50%
- 对齐多个元素时，保持相同的x或y坐标值
- 考虑不同屏幕比例时，建议：
  - 水平方向使用[0.1, 0.9]范围
  - 垂直方向使用[0.15, 0.85]范围
- 动态内容布局时，可以使用以下参考点：
  - 左侧起点：[0.2, y]
  - 右侧终点：[0.8, y]
  - 中心点：[0.5, 0.5]
  - 上方：[0.5, 0.2]
  - 下方：[0.5, 0.8]

### 6.3 动画时序
- 元素入场动画建议1-2秒
- 复杂图形绘制动画可延长至3-5秒
- 确保动画与语音讲解同步

### 6.4 文件命名规范
- 问题ID：`[主题]_[类型]_[序号]`
  例：`CIRCLE_CHORD_001`
- 图片文件：`[问题ID].jpeg/png`
- 视频文件：`[问题ID]_[时间戳].mp4`

## 7. 完整示例

```json
{
  "step_id": 1,
  "title": "题目分析",
  "duration": 30,
  "elements": [
    {
      "type": "geometry",
      "content": {
        "circle": {
          "path": "M 50 50 m -40, 0 a 40,40 0 1,0 80,0 a 40,40 0 1,0 -80,0",
          "style": {
            "stroke": "white",
            "stroke-width": 2,
            "fill": "none"
          }
        },
        "chord": {
          "path": "M 20 60 L 80 60",
          "style": {
            "stroke": "white",
            "stroke-width": 2
          }
        }
      },
      "position": [0.5, 0.4],
      "animation": {
        "enter": "draw_path",
        "duration": 3
      }
    },
    {
      "type": "text",
      "content": "O",
      "position": [0.5, 0.5],
      "font_size": 24,
      "animation": {
        "enter": "fade_in",
        "duration": 0.5
      }
    },
    {
      "type": "formula",
      "content": "OA = 5",
      "position": [0.15, 0.2],
      "font_size": 28,
      "animation": {
        "enter": "slide_in_left",
        "duration": 1
      }
    }
  ]
}
```

## 8. 注意事项

1. 所有文本内容必须使用UTF-8编码
2. LaTeX公式中的反斜杠需要转义
3. 坐标位置使用0-1范围的浮点数值
4. 时间戳使用秒为单位的数值
5. 动画时长不宜过长，避免影响观看体验
6. 确保所有资源文件的路径正确
7. 注意内容的逻辑顺序和衔接 
8. 在JSON文件中包含LaTeX表达式时，所有LaTeX界定符号如`\(`和`\)`必须双重转义为`\\(`和`\\)`，以避免JSON解析错误
9. 几何图形(geometry)类型使用两种坐标系：整体位置用相对坐标(0-1)，SVG路径内部使用像素坐标(通常0-100)

## 9. 中文内容支持

规范完全支持中文内容：
1. 所有文本元素均可使用中文字符
2. 公式与中文可以混合使用
3. 动画效果对中文内容同样适用
4. 建议中文显示时使用合适的字体大小与行间距

```json
{
  "type": "formula",
  "content": "直角三角形的面积计算公式：$S = \\frac{1}{2}ab$",
  "position": [0.5, 0.5],
  "font_size": 42
}
```
MathVideoScript 规范文档
1. 概述

MathVideoScript 是一个用于生成数学题目讲解视频的标准化脚本格式。本文档详细说明了脚本的结构、格式要求和最佳实践。
2. 基本结构

MathVideoScript 由以下四个主要部分组成：

    元数据 (metadata)
    黑板内容 (blackboard)
    音频内容 (audio)
    知识点标注 (annotations)

2.1 完整结构示例

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
    "steps": [
      {
        "step_id": number,      // 步骤编号
        "title": "string",      // 步骤标题
        "duration": number,     // 步骤持续时间（秒）
        "elements": []          // 步骤包含的元素列表
      }
    ]
  },
  "audio": {
    "narration": [],     // 讲解音频
    "background_music": "string"  // 需要添加背景音乐配置
  },
  "annotations": {
    "key_points": []               // 知识点标注
  }
}

2.2 坐标系统

所有元素的位置使用相对坐标系统，范围为0-1：

    x坐标：0表示最左边，1表示最右边
    y坐标：0表示最上边，1表示最下边
    坐标原点(0,0)位于左上角
    所有position属性都使用这个相对坐标系统，格式为 [x, y]

**重要提示：** 由于右侧40%区域通常用于显示教师视频，实际可用的黑板区域仅为画面宽度的60%。因此：
    - 实际黑板内容的中心点位于x=0.3处（而非0.5）
    - 所有内容应尽量保持在x<0.6的左侧区域内
    - 几何图形通常应设置position为[0.3, y]以居中显示在可用区域

例如：

    "position": [0.3, 0.5] 表示元素位于黑板区域正中心（注意不是[0.5, 0.5]）
    "position": [0, 0] 表示元素位于左上角
    "position": [0.58, 1] 表示元素位于右下角但仍在可用区域内
    "position": [0.08, 0.3] 表示元素位于距左边8%、距上边30%的位置

注意： 几何图形(geometry)类型的SVG路径内部使用的是不同的坐标系统，详见3.3节说明。

2.3 布局模式 (Layout Modes)

每个步骤（`step`）支持两种布局模式来控制其内部元素的排列：

1.  **自由布局 (Free Layout)**
    -   **激活方式**：默认模式，无需任何特殊配置。
    -   **行为**：严格遵循每个元素中 `position` 属性定义的坐标进行渲染。
    -   **优点**：可以精确控制每个元素的位置。
    -   **缺点**：创作者需要手动计算每个元素的位置以避免重叠，工作量较大。

2.  **垂直堆叠布局 (Vertical Stack Layout)**
    -   **激活方式**：在步骤对象中添加 `"layout": "vertical-stack"`。
    -   **行为**：
        -   忽略所有元素自身的 `position` 属性。
        -   自动将所有元素在垂直方向上居中堆叠。
        -   自动在元素之间应用合适的、统一的垂直间距。
        -   所有元素作为一个整体，在可用黑板区域内水平居中。
    -   **优点**：完全避免元素重叠，自动处理对齐和间距，极大简化了多行文本或公式的创建过程。
    -   **推荐用法**：**强烈建议在所有包含多个文本或公式元素的步骤中使用此模式。**

**示例：**
```json
"steps": [
  {
    "step_id": 2,
    "title": "找出各项的公因数",
    "duration": 4,
    "layout": "vertical-stack", // <-- 激活垂直堆叠布局
    "elements": [
      {
        "type": "text",
        "content": "观察各项 $7a^2$ 和 $-28$。"
      },
      {
        "type": "text",
        "content": "计算系数 $7$ 和 $28$ 的最大公因数..."
      }
    ]
  }
]
```

2.4 结构灵活性

脚本可以根据需要包含以下部分的一个或多个：

    必须包含：元数据(metadata)和黑板内容(blackboard)
    可选包含：音频内容(audio)和知识点标注(annotations)

简化版的结构示例：

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
    "steps": [
      {
        "step_id": number,      // 步骤编号
        "title": "string",      // 步骤标题
        "duration": number,     // 步骤持续时间（秒）
        "elements": []          // 步骤包含的元素列表
      }
    ]
  }
}

2.5 文本排版最佳实践

为确保文本清晰可读：

1. **超长文本分段处理**：当题目或解析文本较长时，应分成多个文本元素，而不是单一长文本。

2. **字符数均衡**：每行文本应尽量保持字符数量均衡，建议每行控制在20-25个汉字（或等效字符）左右。
   - 将长句分割成字符数相近的多行
   - 分割时注意保持语义完整性，选择合适的断句位置
   - 最后一行可以作为结论，允许字符数较少

3. **字体大小一致性**：同一组相关文本元素应保持字体大小一致。
   - 同一解题步骤中的所有文本应使用相同的字体大小
   - 不同的内容类型（如题目、解析、结论）可以使用不同的字体大小，但同类内容保持一致

4. **分段示例**：
```json
// 不推荐的写法
{
  "type": "text",
  "content": "如图，⊙O的半径OA = 5，半径OC⊥弦AB于点D，且OD = 3，求弦AB的长度。",
  "position": [0.08, 0.06],
  "font_size": 48
}

// 推荐的写法
[
  {
    "type": "text",
    "content": "如图，⊙O的半径OA = 5，半径OC⊥弦AB于点D，",
    "position": [0.08, 0.05],
    "font_size": 52
  },
  {
    "type": "text",
    "content": "且OD = 3，求弦AB的长度。",
    "position": [0.08, 0.12],
    "font_size": 52
  }
]
```

5. **字符数均衡示例**：
```json
// 不均衡的写法
[
  {
    "type": "text",
    "content": "由于AC = BC且∠C = 90°，△ABC是等腰直角三角形；",
    "position": [0.08, 0.05],
    "font_size": 50
  },
  {
    "type": "text",
    "content": "AD = DB, AE = CF，且AE、CF垂直于底边。",
    "position": [0.08, 0.12],
    "font_size": 50
  },
  {
    "type": "text",
    "content": "构造△ADE和△FDC，角相等，边相等，故△ADE≌△FDC。",
    "position": [0.08, 0.19],
    "font_size": 50
  }
]

// 均衡的写法
[
  {
    "type": "text",
    "content": "由于AC = BC且∠C = 90°，",
    "position": [0.08, 0.05],
    "font_size": 50
  },
  {
    "type": "text",
    "content": "△ABC是等腰直角三角形；AD = DB，",
    "position": [0.08, 0.12],
    "font_size": 50
  },
  {
    "type": "text",
    "content": "AE = CF，且AE、CF垂直于底边。",
    "position": [0.08, 0.19],
    "font_size": 50
  },
  {
    "type": "text",
    "content": "构造△ADE和△FDC，角相等，边相等，",
    "position": [0.08, 0.26],
    "font_size": 50
  },
  {
    "type": "text",
    "content": "故△ADE≌△FDC。",
    "position": [0.08, 0.33],
    "font_size": 50
  }
]
```

6. **字体大小建议**：
   - 题目文本：48-52号字体
   - 步骤解析文本：40-44号字体
   - 公式：40-48号字体
   - 几何图形标签：12-16号字体

3. 元素类型详解
3.1 文本类型 (text)

用于显示普通文字说明。

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

3.2 公式类型 (formula)

用于显示数学公式，使用LaTeX语法。

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

JSON中的LaTeX转义示例:

"content": "\\text{在直角三角形 } \\( OAD \\) \\text{ 中，} \\angle AOD = 90^{\\circ}"

注意每个LaTeX的反斜杠\在JSON中需要写为\\，而界定符号\(和\)需要写为\\(和\\)。
- 需要漂亮排版 → 用 "formula"
- 只要符号、不上标 → 用 "text" + Unicode
- 垂直符号使用⊥
在同一元素内，所有 LaTeX 片段一律用 $$…$$ 包裹，中文与其他非 LaTeX 文字保持在 $$ 之外

3.3 几何图形类型 (geometry)

用于绘制几何图形，支持多种基本图形类型。几何图形可以包含多个组件：基本图形（如圆形、线段、弧形）和标签。

示例：

{
  "type": "geometry",
  "content": {
    // 圆形
    "circle_main": {
      "type": "circle",
      "cx": 100,          // 圆心x坐标
      "cy": 100,          // 圆心y坐标
      "r": 80,            // 半径
      "style": {
        "stroke": "white",
        "stroke-width": 2,
        "fill": "none"
      }
    },
    // 椭圆
    "ellipse_1": {
      "type": "ellipse",
      "cx": 200,          // 圆心x坐标
      "cy": 200,          // 圆心y坐标
      "rx": 80,           // x方向半径
      "ry": 40,           // y方向半径
      "style": {
        "stroke": "white",
        "stroke-width": 2,
        "fill": "none"
      }
    },
    // 扇形
    "sector_1": {
      "type": "sector",
      "cx": 300,          // 圆心x坐标
      "cy": 300,          // 圆心y坐标
      "r": 60,            // 半径
      "startAngle": 0,    // 起始角度（度）
      "endAngle": 135,    // 结束角度（度）
      "style": {
        "stroke": "white",
        "stroke-width": 2,
        "fill": "none"
      }
    },
    // 圆弧
    "arc_1": {
      "type": "arc",
      "cx": 400,          // 圆心x坐标
      "cy": 400,          // 圆心y坐标
      "r": 50,            // 半径
      "startAngle": 45,   // 起始角度（度）
      "endAngle": 225,    // 结束角度（度）
      "style": {
        "stroke": "white",
        "stroke-width": 2
      }
    },
    // 线段
    "line": [
      {
        "type": "line",
        "x1": 20,         // 起点x坐标
        "y1": 60,         // 起点y坐标
        "x2": 80,         // 终点x坐标
        "y2": 60,         // 终点y坐标
        "style": {
          "stroke": "white",
          "stroke-width": 2
        }
      }
    ],
    // 标签
    "label": [
      {
        "text": "O",
        "position": [50, 50],
        "font_size": 12,
        "style": {
          "fill": "white"
        }
      }
    ]
  },
  "position": [0.3, 0.5],
  "scale": 1.2,
  "animation": {
    "enter": "draw_path",
    "exit": "fade_out",
    "duration": 1
  }
}

3.3.1 几何图形组件说明

    基本图形类型：
        circle: 圆形
            cx, cy: 圆心坐标
            r: 半径
        ellipse: 椭圆
            cx, cy: 圆心坐标
            rx: x方向半径
            ry: y方向半径
        sector: 扇形
            cx, cy: 圆心坐标
            r: 半径
            startAngle: 起始角度（度）
            endAngle: 结束角度（度）
        arc: 圆弧
            cx, cy: 圆心坐标
            r: 半径
            startAngle: 起始角度（度）
            endAngle: 结束角度（度）
        line: 线段
            x1, y1: 起点坐标
            x2, y2: 终点坐标
        path: 自定义路径（兼容旧格式）
            path: SVG路径字符串

    角度说明：
        所有角度均以度为单位
        逆时针方向为正方向
        0度指向正右方
        90度指向正上方

    标签 (label)
        用于在几何图形上添加点的标记、文字说明等
        属性说明：
            text: 标签文本内容
            position: 标签位置 [x, y]，使用与SVG相同的坐标系统（0-100）
            font_size: 字体大小
            style: 样式设置
                fill: 填充颜色
                其他可选的样式属性

    样式设置 每个图形组件都可以设置 style 属性：
        stroke: 线条颜色
        stroke-width: 线条宽度
        fill: 填充颜色
        stroke-dasharray: 虚线样式（空格分隔值）

注意：为了兼容旧格式，系统会自动将SVG路径中的弧形命令(A/a)转换为arc对象。建议新脚本直接使用上述图形类型定义。

3.4 函数图像类型 (graph)

用于绘制函数图像和坐标系。

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

4. 动画效果

支持的动画类型包括：

    fade_in: 淡入
    fade_out: 淡出
    slide_in_left: 从左滑入
    slide_in_right: 从右滑入
    slide_in_top: 从上滑入
    slide_in_bottom: 从下滑入
    draw_path: 路径绘制
    highlight: 高亮显示

5. 音频配置
5.1 语音配置

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

5.1.1 语音设置说明

    text: 朗读文本内容。**重要规则：此字段必须是纯粹的、口语化的文本，严禁包含LaTeX公式（如`$...$`）或任何其他标记语言。** 这是因为文本会直接输入给文本转语音（TTS）引擎，该引擎无法解析公式代码。
        -   **错误示范**：`"text": "我们来分解因式 $7a^2 - 28$。"`
        -   **正确示范**：`"text": "我们来分解因式 7a方 减 28。"`
    start_time: 开始时间（秒）
    end_time: 结束时间（秒）
    voice_config: 语音参数配置
        speed: 语速，1.0为正常速度
        pitch: 音调，1.0为正常音调
    ssml: 语音合成标记语言(SSML)格式的文本，支持更丰富的语音表现力

5.1.2 SSML 标签规范

火山引擎TTS支持的标签和属性：

1. **`<speak>`**: 包裹整个SSML内容的根标签
    - 所有SSML内容必须包含在`<speak></speak>`标签内

2. **`<break>`**: 插入停顿
    - 支持属性:
      - `time`: 停顿时长，以秒为单位，如"0.5s"（不支持毫秒"ms"）
      - `strength`: 停顿强度，可选值为"x-weak", "weak", "medium", "strong", "x-strong"
    - 用法: `<break time="0.5s"/>`
    - 注意: 不能同时使用time和strength属性

3. **`<say-as>`**: 指定文本的读法
    - 支持属性:
      - `interpret-as`: 解释方式，常用值为"characters"（逐字读出）
    - 用法: `<say-as interpret-as="characters">ABC</say-as>`

4. **`<prosody>`**: 控制语速和音量
    - 支持属性:
      - `rate`: 语速，可选值为"x-slow", "slow", "medium", "fast", "x-fast"
      - `volume`: 音量，可选值为"x-soft", "soft", "medium", "loud", "x-loud"
    - 用法: `<prosody rate="slow" volume="loud">重点内容</prosody>`

5. **`<phoneme>`**: 指定发音
    - 支持属性:
      - `alphabet`: 拼音系统，可选值为"py"（汉语拼音）, "ipa"（国际音标）
      - `ph`: 音标文本
    - 用法: `<phoneme alphabet="py" ph="zhong1">中</phoneme>国`

5.1.3 SSML 使用最佳实践

1. **数学符号和变量读法**:
   - 使用`<say-as interpret-as="characters">`使字母逐个读出
   - 正确示例: `<say-as interpret-as="characters">ABC</say-as>`中，角`<say-as interpret-as="characters">C</say-as>`

2. **停顿控制**:
   - 停顿时间单位必须使用秒(s)，不支持毫秒(ms)
   - 正确示例: `<break time="0.5s"/>`
   - 错误示例: `<break time="500ms"/>`

3. **不要使用不支持的标签**:
   - 火山引擎不支持`<emphasis>`等标签
   - 替代方案: 使用`<prosody>`或`<say-as>`实现强调效果

4. **避免内容嵌套错误**:
   - `<break>`标签不能包含文本
   - 正确示例: `这里停顿<break time="0.3s"/>然后继续`
   - 错误示例: `<break time="0.3s">停顿中</break>`

5. **教学语气建议**:
   - 添加自然的提问和引导: "这里需要注意什么呢？"
   - 使用停顿增强节奏感: "让我们来看看<break time=\"0.3s\"/>这个问题"
   - 逐步解释关键概念: "角边角判定是指..."

5.1.4 时间轴同步

1. **视频与音频同步原则**:
   - 每个步骤的`duration`总和应与音频的`end_time`匹配
   - 最后一段音频的`end_time`不应超过视频总时长
   - 建议为每个主要动画元素配置相应的解说

2. **同步检查**:
   - 步骤时长: step_id为1的步骤时长 + step_id为2的步骤时长 = 音频最后end_time
   - 示例: 第一步13秒 + 第二步57秒 = 总时长70秒，应与最后音频end_time匹配

5.1.5 教学语音风格指南

为使语音内容更贴近真实教师讲解风格，建议采用以下策略：

1. **开场引导式语言**:
   - 使用引导性开场: "好，我们现在来看看这个几何证明题"
   - 提示关注重点: "这里需要注意什么呢？"
   - 示例: `"好，同学们，让我们一起来看这道方程问题"`

2. **过程中的互动元素**:
   - 添加思考提示: "大家想一想，这里能用什么性质？"
   - 使用反问句: "这个结论是不是很简洁？"
   - 强调关键步骤: "这一步很关键哦"
   - 示例: `"我们看到这个等式，它告诉我们什么呢？"`

3. **教学节奏控制**:
   - 在重要概念前使用停顿: `<break time="0.3s"/>`
   - 在复杂推导后给予思考时间: `<break time="0.5s"/>`
   - 示例: `"首先<break time=\"0.3s\"/>我们需要理解题目条件"`

4. **总结和收尾技巧**:
   - 简洁明了的结论: "所以最后得出结论：DE 等于 DF。"
   - 提示思考延伸: "大家可以思考一下，如果条件变为..."
   - 示例: `"通过以上分析，我们证明了这个性质。"`

5. **口语化表达**:
   - 使用"我们"而非"我"，增强参与感
   - 适当使用口头禅: "那么"、"接下来"、"大家跟上我的思路"
   - 示例: `"接下来，我们通过构造全等三角形来完成证明，大家跟上我的思路"`

6. **层次分明的讲解结构**:
   - 明确的步骤标识: "第一步"、"接着"、"最后"
   - 每个关键点后给予小结: "因此我们得到..."
   - 示例: `"第一步，我们需要明确题目条件。第二步，我们来分析几何关系。"`

7. **语言匹配原则**:
   - 系统应根据题目描述的语言自动选择响应语言
   - 如果题目描述为中文，则使用中文进行讲解
   - 如果题目描述为英文或其他语言，则使用相应语言进行讲解
   - 确保语言一致性，避免在同一视频中混合使用不同语言

注意： 语音合成所使用的具体声音（speaker/voice）不在JSON脚本中指定，而是由系统配置文件(config.py)统一控制。这样可以确保所有生成的内容保持声音的一致性，并允许在不修改内容脚本的情况下切换不同的声音。

"animation": {
  "enter": "string",    // 入场动画类型
  "exit": "string",     // 退场动画类型（可选）
  "duration": number    // 动画持续时间（秒）
}

"background": "string"  // 黑板背景类型，例如："classic_blackboard"
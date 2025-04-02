# 开发测试数据

本目录包含用于开发和测试的示例数据。

## 目录结构

- `math_problems/`: 数学题目示例
  - `sample_math_problem_001.jpeg`: 示例数学题目图片
  - `sample_math_problem_001.json`: 示例MathVideoScript格式的讲解方案

## 使用说明

这些示例数据主要用于：
1. 开发过程中的功能测试
2. 在没有前端界面时的后端开发测试
3. 系统集成测试

## 数据格式说明

### MathVideoScript格式
`sample_math_problem_001.json` 是一个完整的MathVideoScript格式示例，包含：
- 元数据（题目信息、难度等）
- 黑板内容布局和动画
- 数字人动作序列
- 语音讲解脚本
- 知识点标注

## 注意事项

- 这些是示例数据，不要用于生产环境
- 实际用户上传的数据将存储在 `backend/data/problems/` 目录中
- JSON文件中的时间戳和动画时间仅供参考，实际开发中可能需要调整 
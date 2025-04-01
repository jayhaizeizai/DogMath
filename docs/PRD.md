# DogMath - 智能数学题目讲解视频生成系统 PRD

## 1. 产品概述

### 1.1 产品定位
DogMath是一个基于AI的智能数学题目讲解视频生成系统，通过图片输入数学题目，自动生成包含黑板内容、数字人和讲解音频的教学视频。

### 1.2 目标用户
- 学生：需要数学题目讲解
- 家长：低价、实时、快速的真人在线视频内容


### 1.3 核心价值
- 快速生成高质量数学教学视频，提供类似真人的教学体验
- 降低教学视频制作成本
- 提供个性化的学习体验

## 2. 功能需求

### 2.1 用户功能
#### 2.1.1 用户认证
- 注册/登录
- 第三方账号登录

- 手机验证码登录

#### 2.1.2 题目上传
- 支持文字输入
- 支持图片上传
- 支持多种图片格式
- 图片预处理和优化

#### 2.1.3 视频生成
- 题目分析
- 解题步骤生成
- 视频下载

#### 2.1.4 个人中心
- 历史记录
- 收藏夹
- 个人设置

### 2.2 系统功能
#### 2.2.1 图片处理
- 图片预处理（基础优化）
- DeepSeek模型直接识别数学公式和文字
- 结果标准化处理

#### 2.2.2 AI分析
- 题目类型识别
- 难度评估
- 解题思路生成
- 生成MathVideoScript格式的讲解方案，包含：
  - 黑板内容布局和动画
  - 数字人动作序列
  - 语音讲解脚本
  - 知识点标注

#### 2.2.3 视频生成
- 解析MathVideoScript格式
- 黑板内容渲染
  - 支持文本、LaTeX公式、几何图形、函数图像
  - 实现动态动画效果
  - 精确控制元素位置和时序
- 数字人动画
  - 基于EchoMimicV2的半身数字人
  - 手部动作库（指向、手势）
  - 视线方向控制
  - 表情反馈
- 语音合成
  - SSML增强语音表现力
  - 精确的时间轴同步
  - 背景音乐和音效
- 视频合成
  - 多轨道合成
  - 音视频同步
  - 质量控制
- 视频管理
  - 自动设置72小时过期时间
  - 定时任务清理过期视频
  - 视频访问权限检查

## 3. 非功能需求

### 3.1 性能需求
- 图片上传响应时间 < 2s
- 视频生成时间 < 30s
- 系统并发用户数 > 20
- 视频播放延迟 < 1s

### 3.2 安全需求
- 用户数据加密存储
- 传输加密
- 访问权限控制
- 防SQL注入
- 视频访问权限验证
- 过期视频自动清理

### 3.3 可用性需求
- 系统可用性 > 99.9%
- 友好的错误提示
- 操作引导
- 响应式设计

### 3.4 可扩展性需求
- 支持水平扩展
- 模块化设计
- 微服务架构

## 4. 技术架构

### 4.1 前端技术栈
- React Native
- Redux Toolkit
- React Navigation
- Axios
- AsyncStorage

### 4.2 后端技术栈
- Python FastAPI
- DeepSeek LLM
- EchoMimicV2（数字人动画）
- PostgreSQL
- Redis
- RabbitMQ
- FFmpeg

### 4.3 基础设施
- Docker
- Kubernetes
- AWS/阿里云
- CDN

## 5. 数据模型

### 5.1 用户模型
```json
{
  "user": {
    "id": "string",
    "username": "string",
    "email": "string",
    "password_hash": "string",
    "created_at": "timestamp",
    "updated_at": "timestamp"
  }
}
```

### 5.2 题目模型
```json
{
  "problem": {
    "id": "string",
    "user_id": "string",
    "image_url": "string",
    "content": "string",
    "type": "string",
    "difficulty": "number",
    "status": "string",
    "created_at": "timestamp"
  }
}
```

### 5.3 视频模型
```json
{
  "video": {
    "id": "string",
    "problem_id": "string",
    "url": "string",
    "duration": "number",
    "status": "string",
    "expires_at": "timestamp",    // 视频过期时间（创建时间+72小时）
    "created_at": "timestamp"
  }
}
```

### 5.4 讲解方案模型（MathVideoScript）
```json
{
  "metadata": {
    "problem_id": "string",
    "source_image": "string",        // base64缩略图
    "difficulty": "string",          // easy/medium/hard
    "estimated_duration": "number",  // 单位：秒
    "knowledge_tags": ["string"],    // 知识点标签
    "created_at": "timestamp"
  },
  "blackboard": {
    "background": "string",          // 黑板样式
    "resolution": [number, number],  // 视频分辨率
    "steps": [
      {
        "step_id": "number",
        "title": "string",
        "duration": "number",        // 本步骤时长
        "elements": [
          {
            "type": "string",        // text/formula/geometry/graph
            "content": "string",     // 内容
            "position": [number, number], // 归一化坐标 [x%, y%]
            "font_size": "number",
            "animation": {
              "enter": "string",     // 入场动画
              "exit": "string",      // 退场动画
              "duration": "number"   // 动画时长
            }
          }
        ]
      }
    ]
  },
  "avatar": {
    "model": "echomimic_v2",        // 使用EchoMimicV2模型
    "position": "right_bottom",     // 屏幕位置
    "style": "teacher",             // 教师风格
    "animations": [
      {
        "timestamp": "number",      // 触发时间点
        "action": "string",         // 动作类型：point_to, write, gesture
        "target": "string",         // 关联黑板元素
        "duration": "number",       // 动作时长
        "hand_gesture": {           // 手部动作配置
          "type": "string",         // 手势类型
          "position": [number, number], // 手势位置
          "intensity": "number"     // 动作强度
        }
      }
    ]
  },
  "audio": {
    "narration": [
      {
        "text": "string",           // 讲解文本
        "start_time": "number",     // 开始时间
        "end_time": "number",       // 结束时间
        "voice_config": {
          "speaker": "string",      // 语音类型
          "speed": "number",        // 语速
          "pitch": "number"         // 音调
        },
        "ssml": "string"           // SSML增强语音
      }
    ],
    "background_music": "string"    // 背景音乐
  },
  "annotations": {
    "key_points": [
      {
        "timestamp": "number",      // 时间点
        "concept": "string",        // 概念
        "reference_link": "string"  // 参考链接
      }
    ]
  }
}
```

## 6. API接口

### 6.1 用户接口
- POST /api/v1/auth/register - 用户注册
- POST /api/v1/auth/login - 用户登录
- POST /api/v1/auth/logout - 用户登出

### 6.2 题目接口
- POST /api/v1/problems - 上传数学题目（支持图片）
- GET /api/v1/problems/{id} - 获取题目详情
- GET /api/v1/problems - 获取题目列表

### 6.3 讲解方案接口
- POST /api/v1/problems/{problem_id}/solution-plans - 生成讲解方案
- GET /api/v1/problems/{problem_id}/solution-plans/{plan_id} - 获取讲解方案详情
- GET /api/v1/problems/{problem_id}/solution-plans - 获取题目的讲解方案列表
- POST /api/v1/problems/{problem_id}/solution-plans/{plan_id}/regenerate - 重新生成讲解方案

### 6.4 视频接口
- POST /api/v1/problems/{problem_id}/solution-plans/{plan_id}/videos - 生成视频
- GET /api/v1/problems/{problem_id}/solution-plans/{plan_id}/videos/{video_id} - 获取视频详情
- GET /api/v1/problems/{problem_id}/solution-plans/{plan_id}/videos - 获取方案的所有视频
- GET /api/v1/problems/{problem_id}/solution-plans/{plan_id}/videos/{video_id}/status - 检查视频状态（包括是否过期）

### 6.5 管理接口（仅管理员）
- DELETE /api/v1/problems/{id} - 删除题目（级联删除相关资源）
- DELETE /api/v1/problems/{problem_id}/solution-plans/{plan_id}/videos/{video_id} - 删除视频文件

### 6.6 接口响应格式
```json
{
  "code": "number",      // 状态码
  "message": "string",   // 响应消息
  "data": "object"       // 响应数据
}
```

### 6.7 接口状态码
- 200: 成功
- 400: 请求参数错误
- 401: 未授权
- 403: 禁止访问
- 404: 资源不存在
- 500: 服务器错误

## 7. 项目规划

### 7.1 开发阶段
1. 需求分析和设计（2周）
2. 前端开发（4周）
3. 后端开发（4周）
4. 测试和优化（2周）
5. 部署上线（1周）

### 7.2 里程碑
- M1: 完成基础架构搭建
- M2: 完成核心功能开发
- M3: 完成测试和优化
- M4: 系统上线

## 8. 风险评估

### 8.1 技术风险
- AI模型准确性
- 视频生成性能
- 系统扩展性

### 8.2 业务风险
- 用户接受度
- 市场竞争
- 成本控制

## 9. 成功指标

### 9.1 核心指标
- 日活跃用户数
- 视频生成成功率
- 用户满意度

### 9.2 质量指标
- 系统响应时间
- 视频生成时间
- 错误率

## 10. 附录

### 10.1 术语表
- OCR: 光学字符识别
- LLM: 大语言模型
- TTS: 文本转语音

### 10.2 参考文档
- React Native文档
- FastAPI文档
- DeepSeek API文档
- EchoMimicV2文档

### 10.3 数字人技术说明
- EchoMimicV2：蚂蚁集团开源的音频驱动数字人技术
  - 支持半身数字人动画
  - 支持中英文语音驱动
  - 支持手部动作生成
  - 支持表情和视线控制
  - 支持自定义动作库 
# DogMath - 智能数学题目讲解视频生成系统

DogMath是一个基于AI的智能数学题目讲解视频生成系统，通过图片输入数学题目，自动生成包含黑板内容、数字人和讲解音频的教学视频。

## 功能特点

- 图片输入数学题目
- AI智能分析题目
- 自动生成解题步骤
- 生成教学视频
- 支持多平台（Web、Android、iOS）

## 技术栈

### 前端
- React Native
- Redux Toolkit
- React Navigation
- Axios
- AsyncStorage

### 后端
- Python FastAPI
- DeepSeek LLM
- PostgreSQL
- Redis
- RabbitMQ
- FFmpeg

## 项目结构

```
DogMath/
├── frontend/           # React Native前端项目
├── backend/           # FastAPI后端项目
├── docs/             # 项目文档
└── scripts/          # 部署和工具脚本
```

## 快速开始

### 前端开发

```bash
cd frontend
npm install
npm start
```

### 后端开发

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
.\venv\Scripts\activate  # Windows
pip install -r requirements.txt
uvicorn src.main:app --reload
```

## 环境要求

- Node.js >= 16
- Python >= 3.8
- PostgreSQL >= 13
- Redis >= 6
- FFmpeg >= 4.4

## 文档

详细文档请查看 `docs/` 目录：
- [产品需求文档](docs/PRD.md)
- [API文档](docs/API.md)
- [部署文档](docs/DEPLOY.md)

## 贡献指南

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

## 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情 
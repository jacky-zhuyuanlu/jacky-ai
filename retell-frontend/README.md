# Retell AI 中文仿站前端

本项目为仿 retell.ai 官网的 Vue3 + Vite + Element Plus 前端，面向全国商用，支持与 FastAPI 后端接口对接。

## 启动方式

```bash
cd retell-frontend
npm install
npm run dev
```

## 目录结构
- `src/`：主源码目录
- `src/views/`：页面组件（首页、产品、价格、登录、注册、控制台等）
- `src/components/`：通用组件
- `src/api/`：API 封装
- `src/router/`：前端路由

## 对接后端
- 后端接口地址建议为 `http://localhost:8000/api/retell/`
- 相关接口文档见 [http://localhost:8000/api/retell/docs](http://localhost:8000/api/retell/docs)

## UI 框架
- [Element Plus](https://element-plus.org/zh-CN/)

## 备注
- 本前端与原有项目完全独立，不影响任何现有功能。
- 如需部署到生产环境，建议用 Nginx 代理。

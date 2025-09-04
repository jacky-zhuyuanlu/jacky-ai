# 聊天室 GraphQL API

这是一个简单的聊天室 GraphQL API 项目，用于演示频道和消息管理功能。

## 功能特点

- 创建和管理聊天频道
- 在频道中发送和管理消息
- 按时间倒序列出频道中的消息
- 删除频道和消息

## 技术栈

- Node.js
- GraphQL (Apollo Server)
- SQLite 数据库
- Express.js

## 安装和运行

```bash
npm install
npm run start:dev
```

服务将在 http://localhost:3000 启动，GraphQL Playground 可用于测试 API。

## GraphQL 操作示例

### 创建频道
```graphql
mutation {
  createChannel(input: { name: "技术讨论", description: "讨论技术相关话题" }) {
    id
    name
    description
    createdAt
  }
}
```

### 在频道中发送消息
```graphql
mutation {
  createMessage(input: { 
    title: "Hello World", 
    content: "这是我的第一条消息", 
    channelId: "1" 
  }) {
    id
    title
    content
    createdAt
  }
}
```

### 获取频道列表
```graphql
query {
  channels {
    id
    name
    description
    createdAt
  }
}
```

### 获取频道中的消息
```graphql
query {
  messages(channelId: "1") {
    id
    title
    content
    createdAt
  }
}
```

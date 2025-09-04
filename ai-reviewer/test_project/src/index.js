const { ApolloServer } = require('@apollo/server');
const { startStandaloneServer } = require('@apollo/server/standalone');
const { typeDefs } = require('./schema');
const { resolvers } = require('./resolvers');
const { createDatabase } = require('./database');

async function startServer() {
  // 初始化数据库
  await createDatabase();
  
  // 创建Apollo Server
  const server = new ApolloServer({
    typeDefs,
    resolvers,
  });

  // 启动服务器
  const { url } = await startStandaloneServer(server, {
    listen: { port: 3000 },
  });

  console.log(`🚀 Server ready at: ${url}`);
  console.log(`📊 GraphQL Playground available at: ${url}`);
}

startServer().catch((error) => {
  console.error('启动服务器失败:', error);
  process.exit(1);
});

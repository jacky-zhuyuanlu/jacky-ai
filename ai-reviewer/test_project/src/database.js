const sqlite3 = require('sqlite3').verbose();
const path = require('path');

let db = null;

// 创建和初始化数据库
async function createDatabase() {
  return new Promise((resolve, reject) => {
    // 创建内存数据库用于测试
    db = new sqlite3.Database(':memory:', (err) => {
      if (err) {
        console.error('数据库连接失败:', err);
        reject(err);
        return;
      }
      
      console.log('✅ 数据库连接成功');
      
      // 创建表结构
      db.serialize(() => {
        // 创建频道表
        db.run(`
          CREATE TABLE channels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            createdAt TEXT NOT NULL
          )
        `);
        
        // 创建消息表
        db.run(`
          CREATE TABLE messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            channelId INTEGER NOT NULL,
            createdAt TEXT NOT NULL,
            FOREIGN KEY (channelId) REFERENCES channels (id)
          )
        `);
        
        // 插入示例数据
        db.run(`
          INSERT INTO channels (name, description, createdAt) 
          VALUES ('通用频道', '默认的聊天频道', '2024-01-01T00:00:00.000Z')
        `);
        
        db.run(`
          INSERT INTO messages (title, content, channelId, createdAt) 
          VALUES ('欢迎消息', '欢迎来到聊天室！', 1, '2024-01-01T00:01:00.000Z')
        `, (err) => {
          if (err) {
            reject(err);
          } else {
            console.log('✅ 数据库初始化完成');
            resolve();
          }
        });
      });
    });
  });
}

// 获取数据库实例
function getDatabase() {
  if (!db) {
    throw new Error('数据库未初始化，请先调用 createDatabase()');
  }
  return db;
}

// 关闭数据库连接
function closeDatabase() {
  if (db) {
    db.close((err) => {
      if (err) {
        console.error('关闭数据库失败:', err);
      } else {
        console.log('✅ 数据库连接已关闭');
      }
    });
  }
}

module.exports = {
  createDatabase,
  getDatabase,
  closeDatabase
};

const { getDatabase } = require('./database');

const resolvers = {
  Query: {
    // 获取所有频道
    channels: async () => {
      const db = getDatabase();
      return new Promise((resolve, reject) => {
        db.all('SELECT * FROM channels ORDER BY createdAt DESC', (err, rows) => {
          if (err) reject(err);
          else resolve(rows);
        });
      });
    },

    // 根据ID获取频道
    channel: async (_, { id }) => {
      const db = getDatabase();
      return new Promise((resolve, reject) => {
        db.get('SELECT * FROM channels WHERE id = ?', [id], (err, row) => {
          if (err) reject(err);
          else resolve(row);
        });
      });
    },

    // 获取频道中的所有消息
    messages: async (_, { channelId }) => {
      const db = getDatabase();
      return new Promise((resolve, reject) => {
        db.all(
          'SELECT * FROM messages WHERE channelId = ? ORDER BY createdAt DESC',
          [channelId],
          (err, rows) => {
            if (err) reject(err);
            else resolve(rows);
          }
        );
      });
    },

    // 根据ID获取消息
    message: async (_, { id }) => {
      const db = getDatabase();
      return new Promise((resolve, reject) => {
        db.get('SELECT * FROM messages WHERE id = ?', [id], (err, row) => {
          if (err) reject(err);
          else resolve(row);
        });
      });
    },
  },

  Mutation: {
    // 创建频道
    createChannel: async (_, { input }) => {
      const db = getDatabase();
      const { name, description } = input;
      const createdAt = new Date().toISOString();
      
      return new Promise((resolve, reject) => {
        db.run(
          'INSERT INTO channels (name, description, createdAt) VALUES (?, ?, ?)',
          [name, description || '', createdAt],
          function(err) {
            if (err) reject(err);
            else {
              // 返回新创建的频道
              db.get('SELECT * FROM channels WHERE id = ?', [this.lastID], (err, row) => {
                if (err) reject(err);
                else resolve(row);
              });
            }
          }
        );
      });
    },

    // 在频道中创建消息
    createMessage: async (_, { input }) => {
      const db = getDatabase();
      const { title, content, channelId } = input;
      const createdAt = new Date().toISOString();
      
      return new Promise((resolve, reject) => {
        db.run(
          'INSERT INTO messages (title, content, channelId, createdAt) VALUES (?, ?, ?, ?)',
          [title, content, channelId, createdAt],
          function(err) {
            if (err) reject(err);
            else {
              // 返回新创建的消息
              db.get('SELECT * FROM messages WHERE id = ?', [this.lastID], (err, row) => {
                if (err) reject(err);
                else resolve(row);
              });
            }
          }
        );
      });
    },

    // 删除频道
    deleteChannel: async (_, { id }) => {
      const db = getDatabase();
      return new Promise((resolve, reject) => {
        // 先删除频道中的所有消息
        db.run('DELETE FROM messages WHERE channelId = ?', [id], (err) => {
          if (err) reject(err);
          else {
            // 然后删除频道
            db.run('DELETE FROM channels WHERE id = ?', [id], (err) => {
              if (err) reject(err);
              else resolve(true);
            });
          }
        });
      });
    },

    // 删除消息
    deleteMessage: async (_, { id }) => {
      const db = getDatabase();
      return new Promise((resolve, reject) => {
        db.run('DELETE FROM messages WHERE id = ?', [id], (err) => {
          if (err) reject(err);
          else resolve(true);
        });
      });
    },
  },

  // 关联字段解析器
  Channel: {
    messages: async (parent) => {
      const db = getDatabase();
      return new Promise((resolve, reject) => {
        db.all(
          'SELECT * FROM messages WHERE channelId = ? ORDER BY createdAt DESC',
          [parent.id],
          (err, rows) => {
            if (err) reject(err);
            else resolve(rows);
          }
        );
      });
    },
  },

  Message: {
    channel: async (parent) => {
      const db = getDatabase();
      return new Promise((resolve, reject) => {
        db.get('SELECT * FROM channels WHERE id = ?', [parent.channelId], (err, row) => {
          if (err) reject(err);
          else resolve(row);
        });
      });
    },
  },
};

module.exports = { resolvers };

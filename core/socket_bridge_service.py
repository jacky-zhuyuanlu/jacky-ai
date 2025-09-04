import asyncio
import websockets
import socket
import threading
import time
import sys
import json  # 添加JSON模块

__wss = None

def new_instance():
    global __wss
    if __wss is None:
        __wss = SocketBridgeService()
    return __wss

class SocketBridgeService:
    def __init__(self):
        self.websockets = {}
        self.sockets = {}
        self.message_queue = asyncio.Queue()
        self.running = True
        self.loop = None
        self.tasks = set()
        self.server = None
        # 移除username_to_ws映射，简化为广播模式

    async def handler(self, websocket, path):
        ws_id = id(websocket)
        self.websockets[ws_id] = websocket
        # 添加连接建立日志
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}][系统] WebSocket客户端已连接: ID={ws_id}, 地址={websocket.remote_address}")
        try:
            if ws_id not in self.sockets:
                sock = await self.create_socket_client()
                if sock:
                    self.sockets[ws_id] = sock
                else:
                    print(f"Failed to connect TCP socket for WebSocket {ws_id}")
                    await websocket.close()
                    return
            receive_task = asyncio.create_task(self.receive_from_socket(ws_id))
            self.tasks.add(receive_task)
            receive_task.add_done_callback(self.tasks.discard)

            # 添加心跳任务
            heartbeat_task = asyncio.create_task(self.send_heartbeat(ws_id))
            self.tasks.add(heartbeat_task)
            heartbeat_task.add_done_callback(self.tasks.discard)

            async for message in websocket:
                await self.send_to_socket(ws_id, message)
        except websockets.ConnectionClosed:
            pass
        except Exception as e:
            pass
        finally:
            self.close_socket_client(ws_id)
            self.websockets.pop(ws_id, None)
            # 添加连接关闭日志
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}][系统] WebSocket客户端已断开: ID={ws_id}, 地址={websocket.remote_address}")

    async def create_socket_client(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.connect(('127.0.0.1', 10001))
            # 添加TCP连接成功日志
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}][系统] TCP服务端连接成功: 127.0.0.1:10001")
            sock.setblocking(True)
            return sock
        except Exception as e:
            # 添加TCP连接失败日志
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}][错误] TCP服务端连接失败: 127.0.0.1:10001, 错误={str(e)}")
            return None

    async def send_to_socket(self, ws_id, message):
        sock = self.sockets.get(ws_id)
        if sock:
            try:
                await asyncio.to_thread(sock.sendall, message)
            except Exception as e:
                self.close_socket_client(ws_id)

    async def receive_from_socket(self, ws_id):
        sock = self.sockets.get(ws_id)
        if not sock:
            return
        try:
            while self.running:
                data = await asyncio.to_thread(sock.recv, 4096)
                if data:
                    await self.message_queue.put((ws_id, data))
                else:
                    break
        except Exception as e:
            pass
        finally:
            self.close_socket_client(ws_id)

    async def process_message_queue(self):
        while self.running or not self.message_queue.empty():
            try:
                ws_id, data = await asyncio.wait_for(self.message_queue.get(), timeout=1.0)
                websocket = self.websockets.get(ws_id)
                if websocket and websocket.open:
                    try:
                        await websocket.send(data)
                    except Exception as e:
                        pass
                self.message_queue.task_done()
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                pass

    def close_socket_client(self, ws_id):
        sock = self.sockets.pop(ws_id, None)
        if sock:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except Exception as e:
                pass
                # print(f"Error shutting down socket for WebSocket {ws_id}: {e}", file=sys.stderr)
            sock.close()

    async def start(self, host='0.0.0.0', port=9001):
        self.server = await websockets.serve(self.handler, host, port)
        process_task = asyncio.create_task(self.process_message_queue())
        self.tasks.add(process_task)
        process_task.add_done_callback(self.tasks.discard)
        try:
            await self.server.wait_closed()
        except asyncio.CancelledError:
            pass
        finally:
            await self.shutdown()

    async def shutdown(self):
        if not self.running:
            return
        self.running = False

        for ws_id, ws in list(self.websockets.items()):
            try:
                await ws.close()
            except Exception as e:
                pass
                # print(f"Error closing WebSocket {ws_id}: {e}", file=sys.stderr)
        self.websockets.clear()

        for ws_id, sock in list(self.sockets.items()):
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except Exception as e:
                pass
                # print(f"Error shutting down socket for WebSocket {ws_id}: {e}", file=sys.stderr)
            sock.close()
        self.sockets.clear()

        await self.message_queue.join()

        for task in self.tasks:
            task.cancel()
        await asyncio.gather(*self.tasks, return_exceptions=True)
        self.tasks.clear()

        if self.server:
            self.server.close()
            await self.server.wait_closed()


    def start_service(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        try:
            self.loop.run_until_complete(self.start(host='0.0.0.0', port=9001))
        except Exception as e:
            print(f"SocketBridgeService exception: {e}")
        finally:
            # 不要关闭事件循环，让它保持运行
            pass

    async def send_heartbeat(self, ws_id):
        """每5秒发送一次心跳包保持连接"""
        while self.running and ws_id in self.websockets:
            websocket = self.websockets.get(ws_id)
            if websocket and websocket.open:
                try:
                    # 发送简单的心跳包内容
                    await websocket.send(b'heartbeat')
                except Exception as e:
                    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}][错误] 心跳发送失败: {str(e)}")
                    break
            await asyncio.sleep(5)  # 每5秒发送一次

    # 删除原有 push_message，改为支持任意字段
    async def push_message(self, **kwargs):
        """发送自定义消息体到所有WebSocket连接，支持任意字段（如panelMsg、panelReply等）"""
        if not kwargs:
            return
        json_message = json.dumps(kwargs, ensure_ascii=False)
        # 兼容原有 text_message 日志
        if kwargs.get("type") == "text_message":
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}][系统] 发送text_message: {json_message}")
        for ws in self.websockets.values():
            if ws.open:
                try:
                    await ws.send(json_message)
                except Exception as e:
                    print(f"消息推送失败: {str(e)}")

    # 修改ASR结果推送方法，使用统一接口
    async def push_asr_result(self, content, role, timestamp=None):
        """推送ASR结果，支持用户和AI角色"""
        await self.push_message(
            message_type="asr_result",
            role=role,
            content=content,
            timestamp=timestamp or int(time.time() * 1000)
        )


    async def broadcast(self, message):
        """向所有连接的WebSocket客户端广播文本消息"""
        for ws in self.websockets.values():
            if ws.open:
                try:
                    await ws.send(message)  # 确保使用文本发送
                except Exception as e:
                    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}][错误] 广播消息失败: {str(e)}")

if __name__ == '__main__':
    service = new_instance()
    service_thread = threading.Thread(target=service.start_service, daemon=True)
    service_thread.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        # 在服务的事件循环中运行 shutdown 协程
        print("Initiating shutdown...")
        if service.loop and service.loop.is_running():
            future = asyncio.run_coroutine_threadsafe(service.shutdown(), service.loop)
            try:
                future.result()  # 等待关闭完成
                print("Shutdown coroutine completed.")
            except Exception as e:
                print(f"Shutdown exception: {e}", file=sys.stderr)
        service_thread.join()
        print("Service has been shut down.")

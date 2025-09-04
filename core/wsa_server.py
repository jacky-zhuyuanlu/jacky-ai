from asyncio import AbstractEventLoop

import websockets
import asyncio
import json
import os
from abc import abstractmethod
from websockets.legacy.server import Serve
import time  # 添加此行导入time模块
import traceback  # 新增导入

from utils import util
from scheduler.thread_manager import MyThread
from core.interview_manager import InterviewManager
interview_mgr = InterviewManager()

class MyServer:
    def __init__(self, host='0.0.0.0', port=10000):
        self.lock = asyncio.Lock()
        self.__host = host  # ip
        self.__port = port  # 端口号
        self.__listCmd = []  # 要发送的信息的列表
        self.__clients = list()
        self.__server: Serve = None
        self.__event_loop: AbstractEventLoop = None
        self.__running = True
        self.__pending = None
        self.isConnect = False
        self.TIMEOUT = 3  # 设置任何超时时间为 3 秒
        self.__tasks = {}  # 记录任务和开始时间的字典

    # 接收处理
    async def __consumer_handler(self, websocket, path):
        print(f"[Fay][consumer_handler] 等待消息... 端口={self.__port}")
        username = None
        interview_questions = None  # 新增：面试题
        output_setting = None
        first_message = True  # 标记是否为首条消息
        # 为每个连接维护独立的用户信息
        connection_username = None
        try:
            print(f"[Fay][consumer_handler] 进入消息循环，准备接收消息... 端口={self.__port}")
            async for message in websocket:
                # print(f"[Fay][consumer_handler] 收到消息原文: {repr(message)} (type={type(message)})")
                await asyncio.sleep(0.01)
                remote_address = websocket.remote_address
                unique_id = f"{remote_address[0]}:{remote_address[1]}"
                # 新增：每条消息原样打印
                # print(f"[Fay][{time.strftime('%Y-%m-%d %H:%M:%S')}] 收到消息原文: {repr(message)} (from {unique_id})")
                # 1. 区分二进制和文本消息
                if isinstance(message, bytes):
                    # 处理音频流
                    if first_message:
                        print(f"[Fay][{time.strftime('%Y-%m-%d %H:%M:%S')}] 首条消息为二进制音频流，跳过greet解析 (from {unique_id})")
                    # 不再打印原文，避免控制台乱码
                    await self.__consumer(message, connection_username)
                    first_message = False
                    continue
                # 2. 处理文本消息
                try:
                    data = json.loads(message)
                    if first_message:
                        print(f"[Fay][{time.strftime('%Y-%m-%d %H:%M:%S')}] 首条消息解析后: {data}")
                    # 兼容旧协议：如果只有大写 Username 字段且没有 type 字段，自动转为 greet 协议
                    if first_message and "Username" in data and "type" not in data:
                        print(f"[Fay][{time.strftime('%Y-%m-%d %H:%M:%S')}] 检测到旧协议 Username 字段，自动转为 greet 协议")
                        data = {
                            "type": "greet",
                            "username": data["Username"],
                            "interviewQuestions": data.get("interviewQuestions")
                        }
                    # 2.1 识别greet消息
                    if data.get("type") == "greet":
                        print(f"[Fay][greet] >>> 进入greet分支，收到消息: {data}")
                        username_in_msg = data.get("username")
                        if username_in_msg is not None:
                            username = username_in_msg
                        
                        # 设置录音器的活跃用户，让该用户能够使用语音识别
                        try:
                            import fay_booter
                            if fay_booter.recorderListener:
                                fay_booter.recorderListener.set_active_user(username)
                                print(f"[Fay][{time.strftime('%Y-%m-%d %H:%M:%S')}] 设置录音器活跃用户: {username}")
                            
                            # 设置WebServer的当前用户名，用于音频流转发
                            if self.__port == 10003:  # WebServer
                                connection_username = username  # 为当前连接设置用户名
                                print(f"[Fay][{time.strftime('%Y-%m-%d %H:%M:%S')}] 设置连接用户: {username}")
                                
                                # 设置WebSocketAudioListener的活跃用户
                                try:
                                    if fay_booter.websocket_audio_listener is not None:
                                        fay_booter.websocket_audio_listener.set_active_user(username)
                                        print(f"[Fay][{time.strftime('%Y-%m-%d %H:%M:%S')}] 设置WebSocketAudioListener活跃用户: {username}")
                                except Exception as e:
                                    print(f"[Fay][{time.strftime('%Y-%m-%d %H:%M:%S')}] 设置WebSocketAudioListener活跃用户失败: {e}")
                        except Exception as e:
                            print(f"[Fay][{time.strftime('%Y-%m-%d %H:%M:%S')}] 设置录音器活跃用户失败: {e}")
                        
                        try:
                            dynamic_data_path = os.path.join(os.path.dirname(__file__), '../dynamic_data.json')
                            session = interview_mgr.get_session(username, dynamic_data_path=dynamic_data_path, name=username)
                            welcome_text = session.get_next_prompt()
                            print(f"[Fay][greet] welcome_text内容: {repr(welcome_text)}")
                        except Exception as e:
                            print(f"[Fay][greet] 读取 dynamic_data.json 失败: {e}")
                            welcome_text = f"欢迎 {username or 'User'} 加入！"
                        # 通过 websocket 发送 welcome_text
                        msg_obj = {
                            "panelMsg": welcome_text,
                            "Username": username,
                            "timestamp": int(time.time() * 1000)
                        }
                        await websocket.send(json.dumps(msg_obj, ensure_ascii=False))
                        # TTS链路同原逻辑
                        try:
                            import fay_booter
                            from core.interact import Interact
                            interact = Interact("greet", 2, {"user": username, "text": welcome_text, "isfirst": True, "isend": True})
                            print(f"[Fay][greet] 调用 Fay on_interact, username={username}, text={welcome_text}")
                            if fay_booter.feiFei is not None:
                                fay_booter.feiFei.on_interact(interact)
                                print(f"[Fay][greet] 已调用 Fay on_interact 触发TTS合成: {welcome_text}")
                            else:
                                print(f"[Fay][greet] feiFei 实例未初始化，跳过TTS合成")
                        except Exception as e:
                            print(f"[Fay][greet] 调用 Fay on_interact 触发TTS合成失败: {e}")
                        # 存储到客户端会话
                        async with self.lock:
                            for i in range(len(self.__clients)):
                                if self.__clients[i]["id"] == unique_id:
                                    old_username = self.__clients[i]["username"]
                                    self.__clients[i]["username"] = username or old_username
                                    print(f"[Fay][{time.strftime('%Y-%m-%d %H:%M:%S')}] greet同步: 用户名 {old_username} -> {self.__clients[i]['username']}")
                        # 跳过后续的__consumer调用，避免重复处理
                        continue
                    # 新增：处理用户回答后推进面试流程
                    elif data.get("type") == "interview_answer":
                        username = data.get("username", "User")
                        user_input = data.get("answer", "")
                        dynamic_data_path = os.path.join(os.path.dirname(__file__), '../dynamic_data.json')
                        session = interview_mgr.get_session(username, dynamic_data_path=dynamic_data_path, name=username)
                        next_prompt = session.get_next_prompt(user_input)
                        msg_obj = {
                            "panelMsg": next_prompt,
                            "Username": username,
                            "timestamp": int(time.time() * 1000)
                        }
                        await websocket.send(json.dumps(msg_obj, ensure_ascii=False))
                        # TTS链路同 greet
                        try:
                            import fay_booter
                            from core.interact import Interact
                            interact = Interact("interview", 2, {"user": username, "text": next_prompt, "isfirst": True, "isend": True})
                            if fay_booter.feiFei is not None:
                                fay_booter.feiFei.on_interact(interact)
                        except Exception as e:
                            print(f"[Fay][interview_answer] 调用 Fay on_interact 触发TTS合成失败: {e}")
                    # 兼容旧协议：首条消息直接带username
                    elif first_message:
                        username_in_msg = data.get("username")
                        output_setting = data.get("output")
                        if username_in_msg is not None:
                            username = username_in_msg
                        if output_setting is not None:
                            async with self.lock:
                                for i in range(len(self.__clients)):
                                    if self.__clients[i]["id"] == unique_id:
                                        self.__clients[i]["output"] = output_setting
                except json.JSONDecodeError as e:
                    if first_message:
                        print(f"[Fay][{time.strftime('%Y-%m-%d %H:%M:%S')}] 首条消息解析失败: {e} (from {unique_id})")
                    pass  # Ignore invalid JSON messages
                if first_message:
                    # 明确提示用户名声明情况
                    if username is None:
                        print(f"[Fay][{time.strftime('%Y-%m-%d %H:%M:%S')}] 首条消息未声明用户名（username字段缺失或为null），from {unique_id}")
                    else:
                        print(f"[Fay][{time.strftime('%Y-%m-%d %H:%M:%S')}] 用户名校验通过: {username} (from {unique_id})")
                    first_message = False
                await self.__consumer(message)
        except websockets.exceptions.ConnectionClosedError as e:
            # 从客户端列表中移除已断开的连接
            await self.remove_client(websocket)
            print(f"[Fay][{time.strftime('%Y-%m-%d %H:%M:%S')}] WebSocket连接断开: {unique_id}, 用户名: {username}, 原因: {e}")
            util.printInfo(1, "User" if username is None else username, f"WebSocket 连接关闭: {e}")
        except websockets.exceptions.ConnectionClosed as e:
            await self.remove_client(websocket)
            print(f"[Fay][{time.strftime('%Y-%m-%d %H:%M:%S')}] WebSocket连接断开(ConnectionClosed): {unique_id}, 用户名: {username}, 原因: {e}")
            util.printInfo(1, "User" if username is None else username, f"WebSocket 连接关闭(ConnectionClosed): {e}")
        except Exception as e:
            await self.remove_client(websocket)
            unique_id_safe = unique_id if 'unique_id' in locals() else '未知'
            print(f"[Fay][{time.strftime('%Y-%m-%d %H:%M:%S')}] WebSocket连接断开(未知异常): {unique_id_safe}, 用户名: {username}, 原因: {e}")
            util.printInfo(1, "User" if username is None else username, f"WebSocket 连接关闭(未知异常): {e}")

    def get_client_output(self, username):
        clients_with_username = [c for c in self.__clients if c.get("username") == username]
        if not clients_with_username:
            return False
        for client in clients_with_username:
            output = client.get("output", 1)
            if output != 0 and output != '0':
                return True
        return False

    # 发送处理
    async def __producer_handler(self, websocket, path):
        try:
            while self.__running:
                await asyncio.sleep(0.01)
                if len(self.__listCmd) > 0:
                    message = await self.__producer()
                    if message:
                        try:
                            username = json.loads(message).get("Username")
                            if username is None:
                                # 群发消息
                                async with self.lock:
                                    wsclients = [c["websocket"] for c in self.__clients]
                                tasks = [self.send_message_with_timeout(client, message, username, timeout=3) for client in wsclients]
                                await asyncio.gather(*tasks)
                            else:
                                # 向指定用户发送消息
                                async with self.lock:
                                    target_clients = [c["websocket"] for c in self.__clients if c.get("username") == username]
                                tasks = [self.send_message_with_timeout(client, message, username, timeout=3) for client in target_clients]
                                await asyncio.gather(*tasks)
                        except json.JSONDecodeError as e:
                            print(f"[Fay][producer] JSON解析失败: {e}, message: {message}")
                        except Exception as e:
                            print(f"[Fay][producer] 发送消息异常: {e}")
        except Exception as e:
            print(f"[Fay][producer] producer_handler异常: {e}")
            # 不要在这里调用 remove_client，让 consumer_handler 处理连接断开

    # 发送消息（设置超时）
    async def send_message_with_timeout(self, client, message, username, timeout=3):
        try:
            await asyncio.wait_for(self.send_message(client, message, username), timeout=timeout)
        except asyncio.TimeoutError:
            util.printInfo(1, "User" if username is None else username, f"发送消息超时: 用户名 {username}")
        except websockets.exceptions.ConnectionClosed as e:
            # 从客户端列表中移除已断开的连接
            await self.remove_client(client)
            util.printInfo(1, "User" if username is None else username, f"WebSocket 连接关闭: {e}")

    # 发送消息
    async def send_message(self, client, message, username):
        try:
            await client.send(message)
        except websockets.exceptions.ConnectionClosed as e:
            # 从客户端列表中移除已断开的连接
            await self.remove_client(client)
            util.printInfo(1, "User" if username is None else username, f"WebSocket 连接关闭: {e}")


    async def __handler(self, websocket, path):
        print(f"[Fay][handler] 新连接: {websocket.remote_address}, 端口={self.__port}")
        self.isConnect = True
        remote_address = websocket.remote_address
        unique_id = f"{remote_address[0]}:{remote_address[1]}"
        # 修改现有连接日志为详细格式
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}][系统] 远程音频输入输出设备连接上: {unique_id}, 端口={self.__port}")
        util.log(1,"websocket连接上:{}".format(self.__port))
        self.on_connect_handler()
        remote_address = websocket.remote_address
        unique_id = f"{remote_address[0]}:{remote_address[1]}"
        async with self.lock:
            self.__clients.append({"id" : unique_id, "websocket" : websocket, "username" : "User"})
        consumer_task = asyncio.create_task(self.__consumer_handler(websocket, path))#接收
        producer_task = asyncio.create_task(self.__producer_handler(websocket, path))#发送
        done, self.__pending = await asyncio.wait([consumer_task, producer_task], return_when=asyncio.FIRST_COMPLETED)

        for task in self.__pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        # 从客户端列表中移除已断开的连接
        await self.remove_client(websocket)
        util.log(1, "websocket连接断开:{}".format(unique_id))

    async def __consumer(self, message, connection_username=None):
        self.on_revice_handler(message, connection_username)

    async def __producer(self):
        if len(self.__listCmd) > 0:
            message = self.on_send_handler(self.__listCmd.pop(0))
            return message
        else:
            return None

    async def remove_client(self, websocket):
        async with self.lock:
            self.__clients = [c for c in self.__clients if c["websocket"] != websocket]
            if len(self.__clients) == 0:
                self.isConnect = False
        # 新增详细日志（移除堆栈跟踪）
        print(f"[Fay][{time.strftime('%Y-%m-%d %H:%M:%S')}] remove_client 被调用，websocket: {websocket}")
        self.on_close_handler()

    def is_connected(self, username):
        if username is None:
            username = "User"
        if len(self.__clients) == 0:
            return False
        clients = [c for c in self.__clients if c["username"] == username]
        if len(clients) > 0:
            return True
        return False


    #Edit by xszyou on 20230113:通过继承此类来实现服务端的接收后处理逻辑
    @abstractmethod
    def on_revice_handler(self, message, connection_username=None):
        # 新增：音频流和文本消息日志
        if isinstance(message, bytes):
            print(f"[Fay][{time.strftime('%Y-%m-%d %H:%M:%S')}] 收到音频帧，长度: {len(message)}")
            # 可扩展：为每个用户维护音频帧缓存，便于后续对接 ASR
            # 这里只做日志和缓存，不影响原有业务逻辑
            if not hasattr(self, '_audio_buffer'):
                self._audio_buffer = {}
            # 获取当前活跃用户名
            username = None
            if hasattr(self, '_current_username'):
                username = self._current_username
            if username is not None:
                if username not in self._audio_buffer:
                    self._audio_buffer[username] = []
                self._audio_buffer[username].append(message)
        else:
            print(f"[Fay][{time.strftime('%Y-%m-%d %H:%M:%S')}] 收到文本消息: {message}")
        # 保持原有逻辑不变

    #Edit by xszyou on 20230114:通过继承此类来实现服务端的连接处理逻辑
    @abstractmethod
    def on_connect_handler(self):
        pass

    #Edit by xszyou on 20230804:通过继承此类来实现服务端的发送前的处理逻辑
    @abstractmethod
    def on_send_handler(self, message):
        return message

    #Edit by xszyou on 20230816:通过继承此类来实现服务端的断开后的处理逻辑
    @abstractmethod
    def on_close_handler(self):
        pass

    # 创建server
    def __connect(self):
        self.__event_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.__event_loop)
        self.__isExecute = True
        if self.__server:
            util.log(1, 'server already exist')
            return
        self.__server = websockets.serve(self.__handler, self.__host, self.__port)
        asyncio.get_event_loop().run_until_complete(self.__server)
        asyncio.get_event_loop().run_forever()

    # 往要发送的命令列表中，添加命令
    def add_cmd(self, content):
        if not self.__running:
            return
        jsonStr = json.dumps(content)
        self.__listCmd.append(jsonStr)
        # util.log('命令 {}'.format(content))

    # 开启服务
    def start_server(self):
        MyThread(target=self.__connect).start()

    # 关闭服务
    def stop_server(self):
        self.__running = False
        self.isConnect = False
        if self.__server is None:
            return
        self.__server.close()
        self.__server = None
        self.__clients = []
        util.log(1, "WebSocket server stopped.")


#ui端server
class WebServer(MyServer):
    def __init__(self, host='0.0.0.0', port=10003):
        super().__init__(host, port)

    def on_revice_handler(self, message, connection_username=None):
        # 处理音频流
        if isinstance(message, bytes):
            # 将音频流转发给WebSocketAudioListener处理
            try:
                import fay_booter
                # 使用连接特定的用户名
                username = connection_username
                
                # 确保WebSocketAudioListener单例存在
                if fay_booter.websocket_audio_listener is None:
                    # 确保feiFei已经初始化
                    if fay_booter.feiFei is None:
                        print(f"[Fay][{time.strftime('%Y-%m-%d %H:%M:%S')}] feiFei未初始化，等待初始化完成...")
                        # 等待feiFei初始化
                        while fay_booter.feiFei is None:
                            time.sleep(0.1)
                        print(f"[Fay][{time.strftime('%Y-%m-%d %H:%M:%S')}] feiFei初始化完成")
                    
                    fay_booter.websocket_audio_listener = fay_booter.WebSocketAudioListener(fay_booter.feiFei)
                    print(f"[Fay][{time.strftime('%Y-%m-%d %H:%M:%S')}] 创建WebSocketAudioListener单例")
                    # 确保录音线程启动
                    fay_booter.websocket_audio_listener.start()
                    print(f"[Fay][{time.strftime('%Y-%m-%d %H:%M:%S')}] WebSocketAudioListener录音线程已启动")
                
                if username:
                    # 确保当前用户是活跃用户
                    fay_booter.websocket_audio_listener.set_active_user(username)
                    fay_booter.websocket_audio_listener.write_audio_data(message)
                else:
                    # 如果connection_username为None，使用默认用户名
                    default_username = "User"
                    print(f"[Fay][{time.strftime('%Y-%m-%d %H:%M:%S')}] connection_username为None，使用默认用户名: {default_username}")
                    
                    # 确保当前用户是活跃用户
                    fay_booter.websocket_audio_listener.set_active_user(default_username)
                    fay_booter.websocket_audio_listener.write_audio_data(message)
            except Exception as e:
                print(f"[Fay][{time.strftime('%Y-%m-%d %H:%M:%S')}] 转发音频流失败: {e}")
        else:
            print(f"[Fay][{time.strftime('%Y-%m-%d %H:%M:%S')}] WebServer收到文本消息: {message}")

    def on_connect_handler(self):
        self.add_cmd({"panelMsg": "使用提示：杰克的MCP可以独立使用，启动数字人将自动对接。"})

    def on_send_handler(self, message):
        return message

    def on_close_handler(self):
        pass

#数字人端server
class HumanServer(MyServer):
    def __init__(self, host='0.0.0.0', port=10002):
        super().__init__(host, port)

    def on_revice_handler(self, message, connection_username=None):
        pass

    def on_connect_handler(self):
        web_server_instance = get_web_instance()
        web_server_instance.add_cmd({"is_connect": self.isConnect})


    def on_send_handler(self, message):
        # util.log(1, '向human发送 {}'.format(message))
        if not self.isConnect:
            return None
        return message

    def on_close_handler(self):
        web_server_instance = get_web_instance()
        web_server_instance.add_cmd({"is_connect": self.isConnect})
        # 修改现有断开日志为详细格式
        # 使用连接数代替unique_id，避免未定义错误
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}][User] 远程音频输入输出设备已经断开: 连接数={len(self.__clients)}")
        

#测试
class TestServer(MyServer):
    def __init__(self, host='0.0.0.0', port=10000):
        super().__init__(host, port)

    def on_revice_handler(self, message, connection_username=None):
        print(message)
    
    def on_connect_handler(self):
        print("连接上了")
    
    def on_send_handler(self, message):
        return message
    
    def on_close_handler(self):
        pass



#单例

__instance: MyServer = None
__web_instance: MyServer = None


def new_instance(host='0.0.0.0', port=10002) -> MyServer:
    global __instance
    if __instance is None:
        __instance = HumanServer(host, port)
    return __instance


def new_web_instance(host='0.0.0.0', port=10003) -> MyServer:
    global __web_instance
    if __web_instance is None:
        __web_instance = WebServer(host, port)
    return __web_instance


def get_instance() -> MyServer:
    return __instance


def get_web_instance() -> MyServer:
    return __web_instance

if __name__ == '__main__':
    testServer = TestServer(host='0.0.0.0', port=10000)
    testServer.start_server()
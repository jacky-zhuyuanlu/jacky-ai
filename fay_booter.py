#核心启动模块
import time
import re
import pyaudio
import socket
import requests
from core.interact import Interact
from core.recorder import Recorder
from scheduler.thread_manager import MyThread
from utils import util, config_util, stream_util
from core.wsa_server import MyServer
from core import wsa_server
from core import socket_bridge_service
from llm.nlp_cognitive_stream import save_agent_memory
import threading
import numpy as np

# 全局变量声明
feiFei = None
recorderListener = None
__running = False
deviceSocketServer = None
DeviceInputListenerDict = {}
ngrok = None
socket_service_instance = None

# 延迟导入fay_core
def get_fay_core():
    from core import fay_core
    return fay_core

#启动状态
def is_running():
    return __running

#录制麦克风音频输入并传给aliyun
class RecorderListener(Recorder):

    def __init__(self, device, fei):
        self.__device = device
        self.__FORMAT = pyaudio.paInt16
        self.__running = False
        self.username = 'User'
        # 这两个参数会在 get_stream 中根据实际设备更新
        self.channels = None
        self.sample_rate = None
        self.answer_buffer = []
        self.last_speaking_end_time = time.time()
        super().__init__(fei)
        self._check_silence_thread = threading.Thread(target=self._check_silence_loop, daemon=True)
        self._check_silence_thread.start()

    def set_active_user(self, username):
        """重写父类方法，支持多用户录音"""
        super().set_active_user(username)
        # 重置当前用户的缓冲区
        self.answer_buffer = []
        self.last_speaking_end_time = time.time()
        util.printInfo(1, username, f"录音器已切换到用户: {username}")

    def on_speaking(self, text):
        if text and text.strip():
            self.answer_buffer.append(text.strip())
            self.last_speaking_end_time = time.time()
            # 检查是否说了"回答完毕"
            if "回答完毕" in text or "结束" in text:
                self._flush_answer_buffer_to_ai()
        # 检查长静音（如10秒）自动触发AI
        if len(self.answer_buffer) > 0 and time.time() - self.last_speaking_end_time > 10:
            self._flush_answer_buffer_to_ai()

    def _flush_answer_buffer_to_ai(self):
        if not self.answer_buffer:
            return
        full_answer = " ".join(self.answer_buffer)
        interact = Interact("mic", 1, {'user': self.username, 'msg': full_answer})
        util.printInfo(3, "语音", '{}'.format(interact.data["msg"]), time.time())
        self._fay.on_interact(interact)
        self.answer_buffer.clear()

    def _check_silence_loop(self):
        while True:
            if len(self.answer_buffer) > 0 and time.time() - self.last_speaking_end_time > 10:
                self._flush_answer_buffer_to_ai()
            time.sleep(1)

    def get_stream(self):
        # 只使用本地麦克风，WebSocket音频由WebSocketAudioListener处理
        try:
            while True:
                config_util.load_config()
                record = config_util.config['source']['record']
                if record['enabled']:
                    break
                time.sleep(0.1)
    
            self.paudio = pyaudio.PyAudio()
            
            # 获取默认输入设备的信息
            default_device = self.paudio.get_default_input_device_info()
            self.channels = min(int(default_device.get('maxInputChannels', 1)), 2)  # 最多使用2个通道
            # self.sample_rate = int(default_device.get('defaultSampleRate', 16000))
            
            util.printInfo(1, "系统", f"默认麦克风信息 - 采样率: {self.sample_rate}Hz, 通道数: {self.channels}")
            
            # 使用系统默认麦克风
            self.stream = self.paudio.open(
                format=self.__FORMAT,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=1024
            )
            
            self.__running = True
            MyThread(target=self.__pyaudio_clear).start()
            
        except Exception as e:
            util.log(1, f"打开麦克风时出错: {str(e)}")
            util.printInfo(1, self.username, "请检查录音设备是否有误，再重新启动!")
            time.sleep(10)
            self.stream = None
        
        print(f"[RecorderListener] 创建本地麦克风流: stream={self.stream is not None}")
        return self.stream

    def __pyaudio_clear(self):
        try:
            while self.__running:
                time.sleep(30)
        except Exception as e:
            util.log(1, f"音频清理线程出错: {str(e)}")
        finally:
            if hasattr(self, 'stream') and self.stream:
                try:
                    self.stream.stop_stream()
                    self.stream.close()
                except Exception as e:
                    util.log(1, f"关闭音频流时出错: {str(e)}")
    
    def stop(self):
        super().stop()
        self.__running = False
        time.sleep(0.1)#给清理线程一点处理时间
        try:
            while self.is_reading:#是为了确保停止的时候麦克风没有刚好在读取音频的
                time.sleep(0.1)
            if hasattr(self, 'stream') and self.stream is not None:
                self.stream.stop_stream()
                self.stream.close()
                if hasattr(self, 'paudio'):
                    self.paudio.terminate()
        except Exception as e:
                print(e)
                util.log(1, "请检查设备是否有误，再重新启动!")

    def is_remote(self):
        return False
                    
        


#Edit by xszyou on 20230113:录制远程设备音频输入并传给aliyun
class DeviceInputListener(Recorder):
    def __init__(self, deviceConnector, fei):
        super().__init__(fei)
        self.__running = True
        self.streamCache = None
        self.thread = MyThread(target=self.run)
        self.thread.start()  #启动远程音频输入设备监听线程
        self.username = 'User'
        self.isOutput = True
        self.deviceConnector = deviceConnector

    def set_active_user(self, username):
        """重写父类方法，支持多用户录音"""
        super().set_active_user(username)
        util.printInfo(1, username, f"远程录音器已切换到用户: {username}")

    def run(self):
        #启动ngork
        self.streamCache = stream_util.StreamCache(1024*1024*20)
        addr = None
        while self.__running:
            try:
                
                data = b""
                while self.deviceConnector:
                    data = self.deviceConnector.recv(2048)
                    if b"<username>" in data:
                        data_str = data.decode("utf-8")
                        match = re.search(r"<username>(.*?)</username>", data_str)
                        if match:
                            self.username = match.group(1)
                        else:
                            self.streamCache.write(data)
                    if b"<output>" in data:
                        data_str = data.decode("utf-8")
                        match = re.search(r"<output>(.*?)<output>", data_str)
                        if match:
                            self.isOutput = (match.group(1) == "True")
                        else:
                            self.streamCache.write(data)
                    if not b"<username>" in data and not b"<output>" in data:
                        self.streamCache.write(data)
                    time.sleep(0.005)
                self.streamCache.clear()
         
            except Exception as err:
                pass
            time.sleep(1)

    def on_speaking(self, text):
        global feiFei
        if len(text) > 1:
            interact = Interact("socket", 1, {"user": self.username, "msg": text, "socket": self.deviceConnector})
            util.printInfo(3, "(" + self.username + ")远程音频输入", '{}'.format(interact.data["msg"]), time.time())
            feiFei.on_interact(interact)

    #recorder会等待stream不为空才开始录音
    def get_stream(self):
        while not self.deviceConnector:
            time.sleep(1)
            pass
        return self.streamCache

    def stop(self):
        super().stop()
        self.__running = False

    def is_remote(self):
        return True

#检查远程音频连接状态
def device_socket_keep_alive():
    global DeviceInputListenerDict
    while __running:
        delkey = None
        for key, value in DeviceInputListenerDict.items():
            try:
                value.deviceConnector.send(b'\xf0\xf1\xf2\xf3\xf4\xf5\xf6\xf7\xf8')#发送心跳包
                if wsa_server.get_web_instance().is_connected(value.username):
                    wsa_server.get_web_instance().add_cmd({"remote_audio_connect": True, "Username" : value.username}) 
            except Exception as serr:
                util.printInfo(1, value.username, "远程音频输入输出设备已经断开：{}".format(key))
                print(f"[Fay][{time.strftime('%Y-%m-%d %H:%M:%S')}] 断开详细日志（心跳检测）：用户名={value.username}，key={key}，异常={serr}")
                value.stop()
                delkey = key
                break
        if delkey:
             value =  DeviceInputListenerDict.pop(delkey)
             if wsa_server.get_web_instance().is_connected(value.username):
                wsa_server.get_web_instance().add_cmd({"remote_audio_connect": False, "Username" : value.username})
        time.sleep(10)

# WebSocket音频处理器单例
websocket_audio_listener = None

# 全局音频缓冲区，用于WebSocket音频数据
global_audio_buffer = stream_util.StreamCache(1024*1024*20)

# WebSocket音频处理器
class WebSocketAudioListener(Recorder):
    """WebSocket音频监听器，处理来自WebSocket的音频数据"""
    
    def __init__(self, fay):
        super().__init__(fay)  # 修复：传递fay参数给基类
        self.username = 'User'  # 默认用户名
        self.streamCache = stream_util.StreamCache(1024*1024*20)  # 修复：添加maxbytes参数
        self.__running = True
        
        # 添加缺失的属性初始化
        self.answer_buffer = []
        self.last_speaking_end_time = time.time()
        self._check_silence_thread = threading.Thread(target=self._check_silence_loop, daemon=True)
        self._check_silence_thread.start()
        
        # 录音线程状态标记
        self._record_thread_started = False
        
        print(f"[WebSocketAudioListener.__init__] 初始化完成，用户: {self.username}")
        print(f"[WebSocketAudioListener.__init__] streamCache: {self.streamCache}")
        print(f"[WebSocketAudioListener.__init__] 静音检测线程已启动")
        # 注意：录音线程需要手动调用start()方法启动

    def set_active_user(self, username):
        """设置当前活跃用户"""
        if self.username != username:
            print(f"[WebSocketAudioListener.set_active_user] 切换用户: {self.username} -> {username}")
            self.username = username
            print(f"[WebSocketAudioListener.set_active_user] 用户切换完成: {username}")
        # 如果用户名相同，不输出日志

    def start(self):
        """启动录音线程"""
        print(f"[WebSocketAudioListener.start] 启动录音线程，用户: {self.username}")
        if not hasattr(self, '_record_thread_started') or not self._record_thread_started:
            super().start()  # 使用基类的start方法
            self._record_thread_started = True
            print(f"[WebSocketAudioListener.start] 录音线程已启动，用户: {self.username}")
        else:
            print(f"[WebSocketAudioListener.start] 录音线程已经启动，用户: {self.username}")

    def write_audio_data(self, audio_data):
        """接收WebSocket音频数据并写入缓存"""
        print(f"[WebSocketAudioListener.write_audio_data] 接收到音频数据: {len(audio_data)} 字节")
        if self.__running and audio_data:
            try:
                self.streamCache.write(audio_data)
                print(f"[WebSocketAudioListener.write_audio_data] 音频数据已写入缓存")
            except Exception as e:
                print(f"[WebSocketAudioListener.write_audio_data] 写入音频数据失败: {e}")
        else:
            print(f"[WebSocketAudioListener.write_audio_data] 跳过音频数据: running={self.__running}, data={audio_data is not None}")

    def get_stream(self):
        """返回音频流，供基类__record方法使用"""
        print(f"[WebSocketAudioListener.get_stream] 返回streamCache: {self.streamCache}")
        if self.streamCache is None:
            print(f"[WebSocketAudioListener.get_stream] streamCache为None，重新初始化")
            self.streamCache = stream_util.StreamCache(1024*1024*20)
        return self.streamCache

    def on_speaking(self, text):
        """处理ASR结果，使用缓冲机制"""
        print(f"[WebSocketAudioListener.on_speaking] 收到ASR结果: '{text}', 当前缓冲区: {self.answer_buffer}")
        
        if text and text.strip():
            self.answer_buffer.append(text.strip())
            self.last_speaking_end_time = time.time()
            print(f"[WebSocketAudioListener.on_speaking] 添加到缓冲区，当前缓冲区: {self.answer_buffer}")
            
            # 推送用户语音转文字到前端
            try:
                from core import socket_bridge_service
                import time
                bridge = socket_bridge_service.new_instance()
                loop = getattr(bridge, 'loop', None)
                if loop and loop.is_running():
                    import asyncio
                    future = asyncio.run_coroutine_threadsafe(
                        bridge.push_message(
                            message_type="text_message",
                            role="user",
                            content=text,
                            username=self.username,
                            timestamp=int(time.time() * 1000)
                        ),
                        loop
                    )
                    print(f"[WebSocketAudioListener.on_speaking] 已推送用户文本到前端")
            except Exception as e:
                print(f"[WebSocketAudioListener.on_speaking] 推送用户语音转文字到前端失败: {e}")
            
            # 检查是否说了"回答完毕"
            if "回答完毕" in text or "结束" in text:
                print(f"[WebSocketAudioListener.on_speaking] 检测到结束关键词，准备发送完整答案")
                self._flush_answer_buffer_to_ai()
        else:
            print(f"[WebSocketAudioListener.on_speaking] ASR结果为空或无效")

    def _flush_answer_buffer_to_ai(self):
        """将缓冲的答案发送给AI"""
        print(f"[WebSocketAudioListener._flush_answer_buffer_to_ai] 开始处理，缓冲区内容: {self.answer_buffer}")
        
        if not self.answer_buffer:
            print(f"[WebSocketAudioListener._flush_answer_buffer_to_ai] 缓冲区为空，跳过")
            return
            
        full_answer = " ".join(self.answer_buffer)
        print(f"[WebSocketAudioListener._flush_answer_buffer_to_ai] 合并完整答案: '{full_answer}'")
        
        try:
            interact = Interact("websocket", 1, {'user': self.username, 'msg': full_answer})
            util.printInfo(3, "WebSocket语音", '{}'.format(interact.data["msg"]), time.time())
            
            print(f"[WebSocketAudioListener._flush_answer_buffer_to_ai] 调用AI处理: {interact.data}")
            self._fay.on_interact(interact)
            
            self.answer_buffer.clear()
            print(f"[WebSocketAudioListener._flush_answer_buffer_to_ai] 缓冲区已清空")
        except Exception as e:
            print(f"[WebSocketAudioListener._flush_answer_buffer_to_ai] 处理完整答案失败: {e}")
            import traceback
            traceback.print_exc()

    def _check_silence_loop(self):
        """检查静音超时，自动触发AI"""
        print(f"[WebSocketAudioListener._check_silence_loop] 开始静音检测线程，用户: {self.username}")
        while self.__running:
            try:
                if len(self.answer_buffer) > 0 and time.time() - self.last_speaking_end_time > 10:
                    print(f"[WebSocketAudioListener._check_silence_loop] 检测到静音超时，自动发送完整答案")
                    self._flush_answer_buffer_to_ai()
                time.sleep(1)
            except Exception as e:
                print(f"[WebSocketAudioListener._check_silence_loop] 静音检测异常: {e}")
                time.sleep(1)
        print(f"[WebSocketAudioListener._check_silence_loop] 静音检测线程结束，用户: {self.username}")

    def stop(self):
        """停止录音线程"""
        print(f"[WebSocketAudioListener.stop] 停止录音线程，用户: {self.username}")
        self.__running = False
        if hasattr(self, '_record_thread_started') and self._record_thread_started:
            super().stop()
            self._record_thread_started = False
            print(f"[WebSocketAudioListener.stop] 录音线程已停止，用户: {self.username}")
        else:
            print(f"[WebSocketAudioListener.stop] 录音线程未启动，用户: {self.username}")

    def is_remote(self):
        """标识为远程音频"""
        return True

#远程音频连接
def accept_audio_device_output_connect():
    global deviceSocketServer
    global __running
    global DeviceInputListenerDict
    deviceSocketServer = socket.socket(socket.AF_INET,socket.SOCK_STREAM) 
    deviceSocketServer.bind(("0.0.0.0",10001))   
    deviceSocketServer.listen(1)
    MyThread(target = device_socket_keep_alive).start() # 开启心跳包检测
    addr = None        
    
    while __running:
        try:
            deviceConnector,addr = deviceSocketServer.accept()   #接受TCP连接，并返回新的套接字与IP地址
            deviceInputListener = DeviceInputListener(deviceConnector, feiFei)  # 设备音频输入输出麦克风
            deviceInputListener.start()

            #把DeviceInputListenner对象记录下来
            peername = str(deviceConnector.getpeername()[0]) + ":" + str(deviceConnector.getpeername()[1])
            DeviceInputListenerDict[peername] = deviceInputListener
            util.log(1,"远程音频{}输入输出设备连接上：{}".format(len(DeviceInputListenerDict), addr))
        except Exception as e:
            pass

#数字人端请求获取最新的自动播报消息，若自动播报服务关闭会自动退出自动播报
def start_auto_play_service(): #TODO 评估一下有无优化的空间
    if config_util.config['source'].get('automatic_player_url') is None or config_util.config['source'].get('automatic_player_status') is None:
        return
    url = f"{config_util.config['source']['automatic_player_url']}/get_auto_play_item"
    user = "User" #TODO 临时固死了
    is_auto_server_error = False
    while __running:
        if config_util.config['source']['wake_word_enabled'] and config_util.config['source']['wake_word_type'] == 'common' and recorderListener.wakeup_matched == True:
            time.sleep(0.01)
            continue
        if is_auto_server_error:
            util.printInfo(1, user, '60s后重连自动播报服务器')
            time.sleep(60)
        # 请求自动播报服务器
        with get_fay_core().auto_play_lock:
            if config_util.config['source']['automatic_player_status'] and config_util.config['source']['automatic_player_url'] is not None and get_fay_core().can_auto_play == True and (config_util.config["interact"]["playSound"] or wsa_server.get_instance().is_connected(user)):
                get_fay_core().can_auto_play = False
                post_data = {"user": user}
                try:
                    response = requests.post(url, json=post_data, timeout=5)
                    if response.status_code == 200:
                        is_auto_server_error = False
                        data = response.json()
                        audio_url = data.get('audio')
                        if not audio_url or audio_url.strip()[0:4] != "http":
                            audio_url = None   
                        response_text = data.get('text')
                        if audio_url is None and (response_text is None or '' == response_text.strip()):
                            continue
                        timestamp = data.get('timestamp')
                        interact = Interact("auto_play", 2, {'user': user, 'text': response_text, 'audio': audio_url})
                        util.printInfo(1, user, '自动播报：{}，{}'.format(response_text, audio_url), time.time())
                        feiFei.on_interact(interact)
                    else:
                        is_auto_server_error = True
                        get_fay_core().can_auto_play = True
                        util.printInfo(1, user, '请求自动播报服务器失败，错误代码是：{}'.format(response.status_code))
                except requests.exceptions.RequestException as e:
                    is_auto_server_error = True
                    get_fay_core().can_auto_play = True
                    util.printInfo(1, user, '请求自动播报服务器失败，错误信息是：{}'.format(e))
        time.sleep(0.01)
     


#停止服务
def stop():
    global feiFei
    global recorderListener
    global __running
    global DeviceInputListenerDict
    global ngrok
    global socket_service_instance
    global deviceSocketServer

    util.log(1, '正在关闭服务...')
    __running = False
    
    # 保存代理记忆
    util.log(1, '正在保存代理记忆...')
    try:
        save_agent_memory()
        util.log(1, '代理记忆保存成功')
    except Exception as e:
        util.log(1, f'保存代理记忆失败: {str(e)}')
    
    if recorderListener is not None:
        util.log(1, '正在关闭录音服务...')
        recorderListener.stop()
        time.sleep(0.1)
    util.log(1, '正在关闭远程音频输入输出服务...')
    try:
        if len(DeviceInputListenerDict) > 0:
            for key in list(DeviceInputListenerDict.keys()):
                value = DeviceInputListenerDict.pop(key)
                value.stop()
        deviceSocketServer.close()
        if socket_service_instance is not None:
            socket_service_instance.stop_server()
            socket_service_instance = None 
    except:
        pass

    util.log(1, '正在关闭核心服务...')
    feiFei.stop()
    util.log(1, '服务已关闭！')


#开启服务
def start():
    global feiFei
    global recorderListener
    global __running
    global socket_service_instance
    
    util.log(1, '开启服务...')
    __running = True

    #读取配置
    util.log(1, '读取配置...')
    config_util.load_config()

    #开启核心服务
    util.log(1, '开启核心服务...')
    feiFei = get_fay_core().FeiFei()
    feiFei.start()

    #初始化定时保存记忆的任务
    util.log(1, '初始化定时保存记忆及反思的任务...')
    from llm.nlp_cognitive_stream import init_memory_scheduler
    init_memory_scheduler()

    #初始化知识库
    util.log(1, '初始化本地知识库...')
    from llm.nlp_cognitive_stream import init_knowledge_base
    init_knowledge_base()

    #开启录音服务
    record = config_util.config['source']['record']
    if record['enabled']:
        util.log(1, '开启录音服务...')
    recorderListener = RecorderListener('device', feiFei)  # 监听麦克风
    recorderListener.start()

    #启动声音沟通接口服务
    util.log(1,'启动声音沟通接口服务...')
    deviceSocketThread = MyThread(target=accept_audio_device_output_connect)
    deviceSocketThread.start()
    socket_service_instance = socket_bridge_service.new_instance()
    socket_bridge_service_Thread = MyThread(target=socket_service_instance.start_service)
    socket_bridge_service_Thread.start()

    #启动自动播报服务
    util.log(1,'启动自动播报服务...')
    MyThread(target=start_auto_play_service).start()
        
    util.log(1, '服务启动完成!')
    
if __name__ == '__main__':
    ws_server: MyServer = None
    feiFei: get_fay_core().FeiFei = None
    recorderListener: Recorder = None
    start()

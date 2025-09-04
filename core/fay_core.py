#作用是处理交互逻辑，文字输入，语音、文字及情绪的发送、播放及展示输出
import math
from operator import index
import os
import time
import socket
import requests
import asyncio  
from pydub import AudioSegment
from queue import Queue
import re  # 添加正则表达式模块用于过滤表情符号

# 适应模型使用
import numpy as np
from ai_module import baidu_emotion
from core import wsa_server
from core.interact import Interact
from tts.tts_voice import EnumVoice
from scheduler.thread_manager import MyThread
from tts import tts_voice
from utils import util, config_util
from core import qa_service
from utils import config_util as cfg
from core import content_db
from ai_module import nlp_cemotion
from llm import nlp_cognitive_stream
from core import stream_manager

from core import member_db
import threading

from core import socket_bridge_service
import json
from core.interview_manager import InterviewManager
interview_mgr = InterviewManager()

#加载配置
cfg.load_config()
if cfg.tts_module =='ali':
    from tts.ali_tss import Speech
elif cfg.tts_module == 'gptsovits':
    from tts.gptsovits import Speech
elif cfg.tts_module == 'gptsovits_v3':
    from tts.gptsovits_v3 import Speech    
elif cfg.tts_module == 'volcano':
    from tts.volcano_tts import Speech
else:
    from tts.ms_tts_sdk import Speech

#windows运行推送唇形数据
import platform
if platform.system() == "Windows":
    import sys
    sys.path.append("test/ovr_lipsync")
    from test_olipsync import LipSyncGenerator
    

#可以使用自动播报的标记    
can_auto_play = True
auto_play_lock = threading.RLock()

class FeiFei:
    def __init__(self):
        self.lock = threading.Lock()
        self.nlp_streams = {} # 存储用户ID到句子缓存的映射
        self.nlp_stream_lock = threading.Lock() # 保护nlp_streams字典的锁
        self.mood = 0.0  # 情绪值
        self.old_mood = 0.0
        self.item_index = 0
        self.X = np.array([1, 0, 0, 0, 0, 0, 0, 0]).reshape(1, -1)  # 适应模型变量矩阵
        # self.W = np.array([0.01577594,1.16119452,0.75828,0.207746,1.25017864,0.1044121,0.4294899,0.2770932]).reshape(-1,1) #适应模型变量矩阵
        self.W = np.array([0.0, 0.6, 0.1, 0.7, 0.3, 0.0, 0.0, 0.0]).reshape(-1, 1)  # 适应模型变量矩阵

        self.wsParam = None
        self.wss = None
        self.sp = Speech()
        self.speaking = False #声音是否在播放
        self.__running = True
        self.sp.connect()  #TODO 预连接
        self.cemotion = None
        self.timer = None
        self.sound_query = Queue()
        self.think_mode_users = {}  # 使用字典存储每个用户的think模式状态
        self.interview_questions = []
        self.current_question_idx = 0
        self.in_interview = False
    
    def __remove_emojis(self, text):
        """
        改进的表情包过滤，避免误删除正常Unicode字符
        """
        # 更精确的emoji范围，避免误删除正常字符
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"  # 表情符号 (Emoticons)
            "\U0001F300-\U0001F5FF"  # 杂项符号和象形文字 (Miscellaneous Symbols and Pictographs)
            "\U0001F680-\U0001F6FF"  # 交通和地图符号 (Transport and Map Symbols)
            "\U0001F1E0-\U0001F1FF"  # 区域指示符号 (Regional Indicator Symbols)
            "\U0001F900-\U0001F9FF"  # 补充符号和象形文字 (Supplemental Symbols and Pictographs)
            "\U0001FA70-\U0001FAFF"  # 扩展A符号和象形文字 (Symbols and Pictographs Extended-A)
            "\U00002600-\U000026FF"  # 杂项符号 (Miscellaneous Symbols)
            "\U00002700-\U000027BF"  # 装饰符号 (Dingbats)
            "\U0000FE00-\U0000FE0F"  # 变体选择器 (Variation Selectors)
            "\U0001F000-\U0001F02F"  # 麻将牌 (Mahjong Tiles)
            "\U0001F0A0-\U0001F0FF"  # 扑克牌 (Playing Cards)
            "]+",
            flags=re.UNICODE,
        )

        # 保护常用的中文标点符号和特殊字符
        protected_chars = ["。", "，", "！", "？", "：", "；", "、", """, """, "'", "'", "（", "）", "【", "】", "《", "》"]

        # 先保存保护字符的位置
        protected_positions = {}
        for i, char in enumerate(text):
            if char in protected_chars:
                protected_positions[i] = char

        # 执行emoji过滤
        filtered_text = emoji_pattern.sub('', text)

        # 如果过滤后文本长度变化太大，可能误删了正常字符，返回原文本
        if len(filtered_text) < len(text) * 0.5:  # 如果删除了超过50%的内容
            return text

        return filtered_text

    def __process_qa_stream(self, text, username):
        """
        按流式方式分割和发送Q&A答案
        使用安全的流式文本处理器和状态管理器
        """
        if not text or text.strip() == "":
            return

        # 使用安全的流式文本处理器
        from utils.stream_text_processor import get_processor
        from utils.stream_state_manager import get_state_manager

        processor = get_processor()
        state_manager = get_state_manager()

        # 处理Q&A流式文本，is_qa=True表示Q&A模式
        success = processor.process_stream_text(text, username, is_qa=True, session_type="qa")

        if success:
            # Q&A模式结束会话（不再需要发送额外的结束标记）
            state_manager.end_session(username)
        else:
            util.log(1, f"Q&A流式处理失败，文本长度: {len(text)}")
            # 失败时也要确保结束会话
            state_manager.force_reset_user_state(username)

    #语音消息处理检查是否命中q&a
    def __get_answer(self, interleaver, text):
        answer = None
        # 全局问答
        answer, type = qa_service.QAService().question('qa',text)
        if answer is not None:
            return answer, type
        else:
            return None, None
        
       
    #语音消息处理
    def __process_interact(self, interact: Interact):
        if self.__running:
            try:
                username = interact.data.get("user", "User")
                uid = member_db.new_instance().find_user(username)
                user_input = interact.data.get("msg", None)
                
                print(f"[fay_core.__process_interact] 处理用户交互: 用户={username}, 输入='{user_input}'")
                
                # 设置录音器的活跃用户，确保语音识别结果能正确关联到当前用户
                try:
                    import fay_booter
                    if fay_booter.recorderListener:
                        fay_booter.recorderListener.set_active_user(username)
                except Exception as e:
                    print(f"设置录音器活跃用户失败: {e}")
                
                # 1. 推送用户输入到面板/前端
                if user_input:
                    print(f"[fay_core.__process_interact] 推送用户输入到前端: '{user_input}'")
                    self.__process_text_output(user_input, username, uid, role="user")
                # 2. 推进面试流程
                session = interview_mgr.get_session(username, dynamic_data_path="dynamic_data.json", name=username)
                reply = session.get_next_prompt(user_input)
                print(f"[fay_core.__process_interact] 面试回复: '{reply}'")
                self.__process_text_output(reply, username, uid, role="assistant")
                # 构造带 is_first/is_end 的 AI回复Interact
                ai_interact = Interact("ai", 2, {"user": username, "msg": reply, "isfirst": True, "isend": True})
                print(f"[fay_core.__process_interact] 开始语音合成: '{reply}'")
                self.say(ai_interact, reply)
                return reply
            except BaseException as e:
                print(f"[fay_core.__process_interact] 处理交互异常: {e}")
                import traceback
                traceback.print_exc()
                return e
        else:
            return "还没有开始运行"

    #记录问答到log
    def write_to_file(self, path, filename, content):
        if not os.path.exists(path):
            os.makedirs(path)
        full_path = os.path.join(path, filename)
        with open(full_path, 'w', encoding='utf-8') as file:
            file.write(content)
            file.flush()  
            os.fsync(file.fileno()) 

    #触发语音交互
    def on_interact(self, interact: Interact):
        MyThread(target=self.__update_mood, args=[interact]).start()
        #创建用户
        username = interact.data.get("user", "User")
        if member_db.new_instance().is_username_exist(username)  == "notexists":
            member_db.new_instance().add_user(username)
        MyThread(target=self.__process_interact, args=[interact]).start()
        return None

    # 发送情绪
    def __send_mood(self):
         while self.__running:
            time.sleep(3)
            if wsa_server.get_instance().is_connected("User"):
                if  self.old_mood != self.mood:
                    content = {'Topic': 'human', 'Data': {'Key': 'mood', 'Value': self.mood}}
                    wsa_server.get_instance().add_cmd(content)
                    self.old_mood = self.mood

    #TODO 考虑重构这个逻辑  
    # 更新情绪
    def __update_mood(self, interact):
        perception = config_util.config["interact"]["perception"]
        if interact.interact_type == 1:
            try:
                if cfg.ltp_mode == "cemotion":
                    result = nlp_cemotion.get_sentiment(self.cemotion, interact.data["msg"])
                    chat_perception = perception["chat"]
                    if result >= 0.5 and result <= 1:
                       self.mood = self.mood + (chat_perception / 150.0)
                    elif result <= 0.2:
                       self.mood = self.mood - (chat_perception / 100.0)
                else:
                    if str(cfg.baidu_emotion_api_key) == '' or str(cfg.baidu_emotion_app_id) == '' or str(cfg.baidu_emotion_secret_key) == '':
                        self.mood = 0
                    else:
                        result = int(baidu_emotion.get_sentiment(interact.data["msg"]))
                        chat_perception = perception["chat"]
                        if result >= 2:
                            self.mood = self.mood + (chat_perception / 150.0)
                        elif result == 0:
                            self.mood = self.mood - (chat_perception / 100.0)
            except BaseException as e:
                self.mood = 0
                print("[System] 情绪更新错误！")
                print(e)

        elif interact.interact_type == 2:
            self.mood = self.mood + (perception["join"] / 100.0)

        elif interact.interact_type == 3:
            self.mood = self.mood + (perception["gift"] / 100.0)

        elif interact.interact_type == 4:
            self.mood = self.mood + (perception["follow"] / 100.0)

        if self.mood >= 1:
            self.mood = 1
        if self.mood <= -1:
            self.mood = -1

    #获取不同情绪声音
    def __get_mood_voice(self):
        voice = tts_voice.get_voice_of(config_util.config["attribute"]["voice"])
        if voice is None:
            voice = EnumVoice.XIAO_XIAO
        styleList = voice.value["styleList"]
        sayType = styleList["calm"]
        if -1 <= self.mood < -0.5:
            sayType = styleList["angry"]
        if -0.5 <= self.mood < -0.1:
            sayType = styleList["lyrical"]
        if -0.1 <= self.mood < 0.1:
            sayType = styleList["calm"]
        if 0.1 <= self.mood < 0.5:
            sayType = styleList["assistant"]
        if 0.5 <= self.mood <= 1:
            sayType = styleList["cheerful"]
        return sayType

    # 合成声音
    def say(self, interact, text, type = ""):
        try:
            uid = member_db.new_instance().find_user(interact.data.get('user'))
            is_end = interact.data.get("isend", False)
            is_first = interact.data.get("isfirst", False)

            if not is_first and not is_end and (text is None or text.strip() == ""):
                util.printInfo(1, interact.data.get('user'), "say: 跳过空文本")
                return None

            self.__send_panel_message(text, interact.data.get('user'), uid, 0, type)

            # 处理think标签
            is_start_think = False
            if "</think>" in text:
                self.think_mode_users[uid] = False
                parts = text.split("</think>")
                text = parts[-1].strip()
                if text == "":
                    util.printInfo(1, interact.data.get('user'), "say: 跳过think空文本")
                    return None
            if "<think>" in text:
                is_start_think = True
                self.think_mode_users[uid] = True
                text = "请稍等..."
            elif "</think>" not in text and "<think>" not in text and self.think_mode_users.get(uid, False):
                util.printInfo(1, interact.data.get('user'), "say: 跳过think中间流")
                return None
            if self.think_mode_users.get(uid, False) and is_start_think:
                if wsa_server.get_web_instance().is_connected(interact.data.get('user')):
                    wsa_server.get_web_instance().add_cmd({"panelMsg": "思考中...", "Username" : interact.data.get('user'), 'robot': f'{cfg.fay_url}/robot/Thinking.jpg'})
                if wsa_server.get_instance().is_connected(interact.data.get("user")):
                    content = {'Topic': 'human', 'Data': {'Key': 'log', 'Value': "思考中..."}, 'Username' : interact.data.get('user'), 'robot': f'{cfg.fay_url}/robot/Thinking.jpg'}
                    wsa_server.get_instance().add_cmd(content)
            if self.think_mode_users.get(uid, False) and not is_start_think:
                util.printInfo(1, interact.data.get('user'), "say: think模式中不合成")
                return None

            result = None
            audio_url = interact.data.get('audio')
            if audio_url is not None:
                file_name = 'sample-' + str(int(time.time() * 1000)) + audio_url[-4:]
                result = self.download_wav(audio_url, './samples/', file_name)
                util.printInfo(1, interact.data.get('user'), f"say: 透传音频下载 {result}")
            elif config_util.config["interact"]["playSound"] or wsa_server.get_instance().is_connected(interact.data.get("user")) or self.__is_send_remote_device_audio(interact):
                if text != None and text.replace("*", "").strip() != "":
                    filtered_text = self.__remove_emojis(text.replace("*", ""))
                    if filtered_text is not None and filtered_text.strip() != "":
                        util.printInfo(1,  interact.data.get('user'), f'say: 合成音频... {filtered_text}')
                        tm = time.time()
                        result = self.sp.to_sample(filtered_text, self.__get_mood_voice())
                        util.printInfo(1,  interact.data.get("user"), f"say: 合成音频完成. 耗时: {math.floor((time.time() - tm) * 1000)} ms 文件:{result}")
            else:
                if is_end and wsa_server.get_web_instance().is_connected(interact.data.get('user')):
                    wsa_server.get_web_instance().add_cmd({"panelMsg": "", 'Username' : interact.data.get('user'), 'robot': f'{cfg.fay_url}/robot/Normal.jpg'})

            if result is not None or is_first or is_end:
                if is_end:
                    time.sleep(1)
                util.printInfo(1, interact.data.get('user'), f"say: 入队 sound_query, file={result}, is_first={is_first}, is_end={is_end}")
                MyThread(target=self.__process_output_audio, args=[result, interact, text]).start()
                return result
            else:
                util.printInfo(1, interact.data.get('user'), f"say: 未生成音频，未入队")
        except BaseException as e:
            util.printInfo(1, interact.data.get('user'), f"say: 异常 {e}")
            print(e)
        return None
    
    #下载wav
    def download_wav(self, url, save_directory, filename):
        try:
            # 发送HTTP GET请求以获取WAV文件内容
            response = requests.get(url, stream=True)
            response.raise_for_status()  # 检查请求是否成功

            # 确保保存目录存在
            if not os.path.exists(save_directory):
                os.makedirs(save_directory)

            # 构建保存文件的路径
            save_path = os.path.join(save_directory, filename)

            # 将WAV文件内容保存到指定文件
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=1024):
                    if chunk:
                        f.write(chunk)

            return save_path
        except requests.exceptions.RequestException as e:
            print(f"[Error] Failed to download file: {e}")
            return None


    #面板播放声音
    def __play_sound(self):
        try:
            import pygame
            pygame.mixer.init()
        except Exception as e:
            util.printInfo(1, "System", "音频播放初始化失败,本机无法播放音频")
            return

        while self.__running:
            try:
                time.sleep(0.01)
                if not self.sound_query.empty():
                    file_url, audio_length, interact = self.sound_query.get()
                    is_first = interact.data.get('isfirst') is True
                    is_end = interact.data.get('isend') is True
                    util.printInfo(1, interact.data.get('user'), f"play_sound: 取出 file={file_url}, is_first={is_first}, is_end={is_end}")
                    if file_url is not None:
                        util.printInfo(1, interact.data.get('user'), 'play_sound: 播放音频...')
                        if is_first:
                            self.speaking = True
                        elif not is_end:
                            self.speaking = True
                        try:
                            pygame.mixer.music.load(file_url)
                            pygame.mixer.music.play()
                            length = 0
                            while length < audio_length:
                                length += 0.01
                                time.sleep(0.01)
                        except Exception as e:
                            util.printInfo(1, interact.data.get('user'), f"play_sound: 播放异常 {e}")
                    if is_end:
                        util.printInfo(1, interact.data.get('user'), "play_sound: 播放结束，调用 play_end")
                        self.play_end(interact)
                    if wsa_server.get_web_instance().is_connected(interact.data.get('user')):
                        wsa_server.get_web_instance().add_cmd({"panelMsg": "", "Username" : interact.data.get('user'), 'robot': f'{cfg.fay_url}/robot/Normal.jpg'})
                    if wsa_server.get_web_instance().is_connected(interact.data.get("user")):
                        wsa_server.get_web_instance().add_cmd({"panelMsg": "", 'Username': interact.data.get('user')})
            except Exception as e:
                util.printInfo(1, "System", f"play_sound: 循环异常 {e}")
                continue

    #推送远程音频
    def __send_remote_device_audio(self, file_url, interact):
        if file_url is None:
            return
        delkey = None    
        for key, value in fay_booter.DeviceInputListenerDict.items():
            if value.username == interact.data.get("user") and value.isOutput: #按username选择推送，booter.devicelistenerdice按用户名记录
                try:
                    value.deviceConnector.send(b"\x00\x01\x02\x03\x04\x05\x06\x07\x08") # 发送音频开始标志，同时也检查设备是否在线
                    wavfile = open(os.path.abspath(file_url), "rb")
                    data = wavfile.read(102400)
                    total = 0
                    while data:
                        total += len(data)
                        value.deviceConnector.send(data)
                        data = wavfile.read(102400)
                        time.sleep(0.0001)
                    value.deviceConnector.send(b'\x08\x07\x06\x05\x04\x03\x02\x01\x00')# 发送音频结束标志
                    util.printInfo(1, value.username, "远程音频发送完成：{}".format(total))
                except socket.error as serr:
                    util.printInfo(1, value.username, f"远程音频输入输出设备已经断开：{key}，异常信息：{serr}") 
                    print(f"[Fay][{time.strftime('%Y-%m-%d %H:%M:%S')}] 断开详细日志：用户名={value.username}，key={key}，异常={serr}")
                    value.stop()
                    delkey = key
        if delkey:
             value =  fay_booter.DeviceInputListenerDict.pop(delkey)
             if wsa_server.get_web_instance().is_connected(interact.data.get('user')):
                wsa_server.get_web_instance().add_cmd({"remote_audio_connect": False, "Username" : interact.data.get('user')})

    def __is_send_remote_device_audio(self, interact):
        for key, value in fay_booter.DeviceInputListenerDict.items():
            if value.username == interact.data.get("user") and value.isOutput:
                return True
        return False 

    #输出音频处理
    def __process_output_audio(self, file_url, interact, text):
        try:
            try:
                if file_url is None:
                    audio_length = 0
                elif file_url.endswith('.wav'):
                    audio = AudioSegment.from_wav(file_url)
                    audio_length = len(audio) / 1000.0  # 时长以秒为单位
                elif file_url.endswith('.mp3'):
                    audio = AudioSegment.from_mp3(file_url)
                    audio_length = len(audio) / 1000.0  # 时长以秒为单位
            except Exception as e:
                audio_length = 3
            
            # 新增：获取当前时间戳（与音频同步）
            # Author: 杰克
            current_timestamp = int(time.time() * 1000)
            # 新增：调用文本推送方法（与音频发送并行）
            # Author: 杰克
            if text:
                self.__send_web_socket_text(
                    text=text,
                    username=interact.data.get('user'),
                    timestamp=current_timestamp
                )

            #推送远程音频
            if file_url is not None:
                MyThread(target=self.__send_remote_device_audio, args=[file_url, interact]).start()       

            #发送音频给数字人接口
            if file_url is not None and wsa_server.get_instance().is_connected(interact.data.get("user")):
                content = {'Topic': 'human', 'Data': {'Key': 'audio', 'Value': os.path.abspath(file_url), 'HttpValue': f'{cfg.fay_url}/audio/' + os.path.basename(file_url),  'Text': text, 'Time': audio_length, 'Type': interact.interleaver, 'IsFirst': 1 if interact.data.get("isfirst", False) else 0,  'IsEnd': 1 if interact.data.get("isend", False) else 0}, 'Username' : interact.data.get('user'), 'robot': f'{cfg.fay_url}/robot/Speaking.jpg'}
                #计算lips
                if platform.system() == "Windows":
                    try:
                        lip_sync_generator = LipSyncGenerator()
                        viseme_list = lip_sync_generator.generate_visemes(os.path.abspath(file_url))
                        consolidated_visemes = lip_sync_generator.consolidate_visemes(viseme_list)
                        content["Data"]["Lips"] = consolidated_visemes
                    except Exception as e:
                        print(e)
                        util.printInfo(1, interact.data.get("user"),  "唇型数据生成失败")
                wsa_server.get_instance().add_cmd(content)
                util.printInfo(1, interact.data.get("user"),  "数字人接口发送音频数据成功")

            #面板播放
            config_util.load_config()
            if config_util.config["interact"]["playSound"]:
                  self.sound_query.put((file_url, audio_length, interact))
            else:
                if wsa_server.get_web_instance().is_connected(interact.data.get('user')):
                    wsa_server.get_web_instance().add_cmd({"panelMsg": "", 'Username' : interact.data.get('user'), 'robot': f'{cfg.fay_url}/robot/Normal.jpg'})
            
        except Exception as e:
            print(e)

    def play_end(self, interact):
        self.speaking = False
        global can_auto_play
        global auto_play_lock
        with auto_play_lock:
            if self.timer:
                self.timer.cancel()
                self.timer = None
            if interact.interleaver != 'auto_play': #交互后暂停自动播报30秒
                self.timer = threading.Timer(30, self.set_auto_play)
                self.timer.start()
            else:
                can_auto_play = True

    #恢复自动播报(如果有)   
    def set_auto_play(self):
        global auto_play_lock
        global can_auto_play
        with auto_play_lock:
            can_auto_play = True
            self.timer = None

    #启动核心服务
    def start(self):
        if cfg.ltp_mode == "cemotion":
            from cemotion import Cemotion
            self.cemotion = Cemotion()
        MyThread(target=self.__send_mood).start()
        MyThread(target=self.__play_sound).start()

    #停止核心服务
    def stop(self):
        self.__running = False
        self.speaking = False
        self.sp.close()
        wsa_server.get_web_instance().add_cmd({"panelMsg": ""})
        content = {'Topic': 'human', 'Data': {'Key': 'log', 'Value': ""}}
        wsa_server.get_instance().add_cmd(content)

    def __record_response(self, text, username, uid):
        """
        记录AI的回复内容
        :param text: 回复文本
        :param username: 用户名
        :param uid: 用户ID
        :return: content_id
        """
        self.write_to_file("./logs", "answer_result.txt", text)
        return content_db.new_instance().add_content('fay', 'speak', text, username, uid)

    def __send_panel_message(self, text, username, uid, content_id=None, type=None):
        """
        发送消息到Web面板
        :param text: 消息文本
        :param username: 用户名
        :param uid: 用户ID
        :param content_id: 内容ID
        :param type: 消息类型
        """
        if not wsa_server.get_web_instance().is_connected(username):
            return
            
        # 发送基本消息
        wsa_server.get_web_instance().add_cmd({
            "panelMsg": text,
            "Username": username
        })
        
        # 如果有content_id，发送回复消息
        if content_id is not None:
            wsa_server.get_web_instance().add_cmd({
                "panelReply": {
                    "type": "fay",
                    "content": text,
                    "username": username,
                    "uid": uid,
                    "id": content_id,
                    "is_adopted": type == 'qa'
                },
                "Username": username
            })

    def __send_digital_human_message(self, text, username):
        """
        发送消息到数字人（语音应该在say方法驱动数字人输出）
        :param text: 消息文本
        :param username: 用户名
        """
        full_text = self.__remove_emojis(text.replace("*", ""))
        if wsa_server.get_instance().is_connected(username):
            content = {
                'Topic': 'human',
                'Data': {
                    'Key': 'text',
                    'Value': full_text
                },
                "Username": username
            }
            wsa_server.get_instance().add_cmd(content)

    def __process_text_output(self, text, username, uid, role="assistant"):
        """
        处理文本输出到各个终端
        :param text: 主要回复文本
        :param username: 用户名
        :param uid: 用户ID
        :param role: 消息角色（user/assistant）
        """
        if text:
            text = text.strip()
        # 记录主回复
        content_id = self.__record_response(text, username, uid)
        # 发送主回复到面板和数字人
        self.__send_digital_human_message(text, username)
        # 新增：推送到WebSocket前端
        self.__send_web_socket_text(
            text=text,
            username=username,
            timestamp=int(time.time() * 1000),
            role=role
        )
        # 打印日志
        util.printInfo(1, username, '({}) {}'.format(self.__get_mood_voice(), text))

    # 新增文本推送方法，支持role参数
    def __send_web_socket_text(self, text: str, username: str, timestamp: int, role: str = "assistant"):
        """
        通过WebSocket推送文本消息（与音频同步），线程安全
        :param text: 要推送的文本内容
        :param username: 用户标识
        :param timestamp: 时间戳（毫秒级）
        :param role: 消息角色（user/assistant）
        """
        bridge = socket_bridge_service.new_instance()
        try:
            loop = getattr(bridge, 'loop', None)
            if loop and loop.is_running():
                future = asyncio.run_coroutine_threadsafe(
                    bridge.push_message(
                        message_type="text_message",
                        role=role,
                        content=text,
                        username=username,
                        timestamp=timestamp
                    ),
                    loop
                )
                # 可选：future.result() 等待完成或异常
            else:
                print("WebSocket主事件循环未运行，消息未发送")
        except Exception as e:
            print(f"WebSocket消息推送异常: {e}")

    # 禁止自动主问题推进，主问题只能由 interview_manager.py 控制
    # def start_interview(self, username="User"):
    #     try:
    #         with open('dynamic_data.json', 'r', encoding='utf-8') as f:
    #             data = json.load(f)
    #             self.interview_questions = [q['question'] for q in data.get('interview_questions', [])]
    #         self.current_question_idx = 0
    #         self.in_interview = True
    #         self.ask_next_question(username)
    #     except Exception as e:
    #         print(f"[FeiFei] 面试题读取失败: {e}")
    #         self.in_interview = False

    # def ask_next_question(self, username="User"):
    #     if self.current_question_idx < len(self.interview_questions):
    #         question = self.interview_questions[self.current_question_idx]
    #         self.current_question_idx += 1
    #         from core.interact import Interact
    #         interact = Interact("mic", 1, {'user': username, 'msg': question})
    #         self.on_interact(interact)
    #     else:
    #         self.in_interview = False
    #         from core.interact import Interact
    #         interact = Interact("mic", 1, {'user': username, 'msg': "本次面试结束，谢谢您的作答。"})
    #         self.on_interact(interact)

    # def on_user_answer(self, text, username="User"):
    #     # 用户每次回答后自动问下一个
    #     if self.in_interview:
    #         self.ask_next_question(username)

import importlib
fay_booter = importlib.import_module('fay_booter')

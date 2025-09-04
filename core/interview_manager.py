import json
from threading import Lock

class InterviewSession:
    def __init__(self, dynamic_data_path="dynamic_data.json", mins=10, objective="技术面试", name=None):
        with open(dynamic_data_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.questions = [q["question"] for q in data.get("interview_questions", [])]
        self.index = 0
        self.in_followup = False
        self.finished = False
        self.mins = mins
        self.objective = objective
        self.name = name or "候选人"
        self.followup_count = 0
        self.max_followup = 2

    def get_next_prompt(self, user_input=None):
        if self.index >= len(self.questions):
            self.finished = True
            return "面试结束，感谢您的作答。"

        # 主问题
        if not self.in_followup and user_input is None:
            self.followup_count = 0
            return f"{self.name}，请回答：{self.questions[self.index]}"

        # 不会/跳过
        if user_input is not None and self._is_skip_answer(user_input):
            self.index += 1
            self.in_followup = False
            self.followup_count = 0
            if self.index >= len(self.questions):
                self.finished = True
                return "面试结束，感谢您的作答。"
            return f"{self.name}，请回答：{self.questions[self.index]}"

        # 追问
        if self.followup_count < self.max_followup:
            from utils.openai_api.openai_api import call_llm
            main_q = self.questions[self.index]
            followup_prompt = (
                f"你是IT面试官，主问题是：“{main_q}”，候选人回答：“{user_input}”。\n"
                "请生成一个不超过25字的开放式追问，只输出追问本身。"
            )
            followup = call_llm(followup_prompt).strip()
            self.in_followup = True
            self.followup_count += 1
            return followup

        # 追问次数已满，进入下一个主问题
        self.index += 1
        self.in_followup = False
        self.followup_count = 0
        if self.index >= len(self.questions):
            self.finished = True
            return "面试结束，感谢您的作答。"
        return f"{self.name}，请回答：{self.questions[self.index]}"

    def _is_skip_answer(self, user_input):
        skip_words = ["不知道", "不会", "不清楚", "不了解", "不太懂", "不明白", "忘了", "没做过", "没有", "不记得", "下一个", "换一个", "跳过"]
        return any(word in user_input.strip() for word in skip_words)

class InterviewManager:
    def __init__(self):
        self.sessions = {}
        self.lock = Lock()

    def get_session(self, user_id, **kwargs):
        with self.lock:
            if user_id not in self.sessions or self.sessions[user_id].finished:
                self.sessions[user_id] = InterviewSession(**kwargs)
            return self.sessions[user_id]

    def reset_session(self, user_id, **kwargs):
        with self.lock:
            self.sessions[user_id] = InterviewSession(**kwargs)
            return self.sessions[user_id] 
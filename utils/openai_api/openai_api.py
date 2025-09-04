import os
import openai
from utils.config_util import get_llm_config
 
# 设置OpenAI API的密钥
# openai.api_key = os.getenv("OPENAI_API_KEY")
openai.base_url = "http://127.0.0.1:8000/v1/chat/completions"

def call_llm(prompt, temperature=0.7, max_tokens=1024):
    from openai import OpenAI
    cfg = get_llm_config()
    client = OpenAI(api_key=cfg["api_key"], base_url=cfg["base_url"])
    model = cfg["model_engine"]
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
        max_tokens=max_tokens,
        stream=False
    )
    return response.choices[0].message.content
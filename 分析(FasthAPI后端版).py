import json
from openai import OpenAI
from typing import List, Dict, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# 配置
DEEPSEEK_API_KEY = ""   # 请替换为真实api key
DEEPSEEK_BASE_URL = "https://api.deepseek.com"



# 核心
import json
from typing import List, Dict, Optional

def load_chat_data(file_path: str) -> List[Dict]:
    """安全读取聊天文件，异常时返回空列表"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, UnicodeDecodeError) as e:
        print(f"读取文件失败：{e}")
        return []
    
    messages = data.get("messages")
    if not isinstance(messages, list):
        print(f"警告：messages 字段不是列表，类型为 {type(messages)}，已返回空列表")
        return []
    
    return messages

def format_chat_text(messages: List[Dict]) -> str:
    chat_text = ""
    for msg in messages:
        content = msg.get("content", "")
        if not content:
            continue
        sender = msg.get("senderDisplayName", "未知")
        time = msg.get("formattedTime", "")
        msg_type = msg.get("type", "")
        chat_text += f"[{time}] {sender} ({msg_type}): {content}\n"
    return chat_text

def build_prompt(chat_text: str) -> str:
    """
	   根据聊天记录构建分析提示词
	   """
    prompt = f"""
    请你作为专业的关系分析AI。
    分析以下微信聊天记录：
    请详细分析：
    1. 双方关系
    2. 暧昧程度（0~100）
    3. 谁更主动
    4. 情绪变化
    5. 双方性格特点
    6. 是否存在冷淡期
    7. 聊天氛围
    8. 关系发展趋势
    9. 双方依赖感
    10. 是否存在隐藏情绪
    聊天记录：
    {chat_text}
    """
    return prompt

def call_deepseek(prompt: str, api_key: str = DEEPSEEK_API_KEY) -> Optional[str]:
    client = OpenAI(api_key=api_key, base_url=DEEPSEEK_BASE_URL)
    try:
        response = client.chat.completions.create(
            model="deepseek-v4-flash",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"API调用失败: {e}")
        return None

def analyze_chat_from_file(file_path: str) -> Optional[str]:
    """整个流程：读取文件 -> 格式化 -> 构建 prompt -> 调用 API -> 返回结果"""
    messages = load_chat_data(file_path)
    if not messages:
        return None
    chat_text = format_chat_text(messages)
    if not chat_text.strip():
        return None
    prompt = build_prompt(chat_text)
    result = call_deepseek(prompt)
    return result

# ---------- FastAPI 接口 ----------
app = FastAPI()

class AnalyzeRequest(BaseModel):
    file_path: str   # 前端传入聊天文件的路径

@app.post("/analyze")
async def analyze(request: AnalyzeRequest):
    result = analyze_chat_from_file(request.file_path)
    if result is None:
        raise HTTPException(status_code=400, detail="分析失败，请检查文件内容或格式")
    return {"result": result}

# ---------- 启动服务（直接运行此文件）----------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
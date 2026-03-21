import time
import requests
import asyncio
import os
import json
from datetime import datetime
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from dotenv import load_dotenv

# ========== 清除代理环境变量 ==========
os.environ['HTTP_PROXY'] = ''
os.environ['HTTPS_PROXY'] = ''
os.environ['http_proxy'] = ''
os.environ['https_proxy'] = ''

load_dotenv()
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
if not DEEPSEEK_API_KEY:
    print("=" * 60)
    print("❌ 错误：未找到 DeepSeek API 密钥！")
    print("请按照以下步骤操作：")
    print("1. 在项目根目录下创建 .env 文件")
    print("2. 在 .env 文件中添加一行：DEEPSEEK_API_KEY=你的密钥")
    print("3. 保存文件后重新启动服务")
    print("=" * 60)
    raise ValueError("请设置环境变量 DEEPSEEK_API_KEY")

BASE_URL = "https://api.deepseek.com/v1/chat/completions"

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

# 硬编码 RAG 服务地址，避免环境变量污染
RAG_ADD_URL = "http://127.0.0.1:8003/add_document"

CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
character_name = "默认角色"
character_background = "你是一个普通的AI助手，请友好地回应用户。"

if os.path.exists(CONFIG_PATH):
    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            config = json.load(f)
            character_name = config.get("character_name", character_name)
            character_background = config.get("character_background", character_background)
        print(f"✅ 已加载角色配置：{character_name}")
    except Exception as e:
        print(f"⚠️ 读取配置文件失败，将使用默认角色。错误：{e}")
else:
    print("ℹ️ 未找到 config.json，将使用默认角色设定。")

print("=" * 60)
print("正在启动 DeepSeek 服务...")
print(f"项目根目录: {BASE_DIR}")
print(f"日志目录: {LOG_DIR}")
print(f"RAG 服务地址: {RAG_ADD_URL}")
print(f"当前角色: {character_name}")
print("=" * 60)

app = FastAPI(title="DeepSeek 服务", description="处理对话生成，集成 RAG 动态记忆")

class Message(BaseModel):
    role: str
    content: str

class GenerateRequest(BaseModel):
    messages: List[Message]
    rag_context: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 2000
    save_conversation: bool = True
    conversation_id: Optional[str] = None
    auto_add_to_rag: bool = False
    current_round: Optional[int] = None

class GenerateResponse(BaseModel):
    reply: str
    usage: Optional[dict] = None
    conversation_id: Optional[str] = None

def add_to_rag_sync(text: str, metadata: Optional[dict] = None):
    try:
        print(f"[RAG添加] 准备添加，文本长度 {len(text)}")
        payload = {"chunks": [text]}
        if metadata:
            payload["metadata"] = [metadata]
        # 禁用代理，防止被转发到错误端口
        resp = requests.post(RAG_ADD_URL, json=payload, timeout=10, proxies={"http": None, "https": None})
        if resp.status_code == 200:
            print(f"[RAG添加] 成功，响应: {resp.json()}")
        else:
            print(f"[RAG添加] 失败，状态码: {resp.status_code}, 响应: {resp.text}")
    except requests.exceptions.ConnectionError:
        print("[RAG添加] 无法连接到 RAG 服务，请确保 RAG 服务已启动")
    except Exception as e:
        print(f"[RAG添加] 异常: {e}")

def sync_rag_search(query):
    try:
        resp = requests.post(
            "http://127.0.0.1:8003/search_hybrid",
            json={"query": query, "top_k": 10},
            timeout=5,
            proxies={"http": None, "https": None}
        )
        if resp.status_code == 200:
            data = resp.json()
            results = data.get("results", [])
            return "\n".join([r["text"] for r in results])
    except Exception as e:
        print(f"RAG 检索异常: {e}")
    return None

@app.get("/health")
async def health():
    return {"status": "ok", "service": "deepseek", "character": character_name}

@app.get("/config")
async def get_config():
    return {
        "character_name": character_name,
        "character_background": character_background[:100] + "..."
    }

@app.post("/generate", response_model=GenerateResponse)
async def generate(req: GenerateRequest):
    print(f"收到请求: auto_add_to_rag={req.auto_add_to_rag}, conversation_id={req.conversation_id}, current_round={req.current_round}")

    conv_id = req.conversation_id
    if not conv_id and req.save_conversation:
        conv_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        print(f"生成新会话ID: {conv_id}")

    full_messages = []
    original_len = 0
    if conv_id:
        log_path = os.path.join(LOG_DIR, f"conv_{conv_id}.json")
        if os.path.exists(log_path):
            try:
                with open(log_path, 'r', encoding='utf-8') as f:
                    history = json.load(f)
                for msg in history.get("messages", []):
                    full_messages.append(Message(**msg))
                original_len = len(full_messages)
                print(f"加载历史 {original_len} 条消息")
            except Exception as e:
                print(f"加载历史消息失败: {e}")
        else:
            print("新会话，无历史")

    for msg in req.messages:
        full_messages.append(msg)
    print(f"添加请求消息后，总消息数: {len(full_messages)}")

    messages_for_api = []

    if req.rag_context:
        system_content = f"""{character_background}

【情境记忆】（过往对话片段，供分析参考）：
{req.rag_context}

【当前用户消息】
用户说：“{full_messages[-1].content if full_messages and full_messages[-1].role == 'user' else ''}”

【分析任务】
请你按照以下步骤进行推理（请将分析过程写在 `<analysis>` 标签内，确保清晰展现思考链）：
用一句话（50字内）快速概括：根据情境记忆，当前对话采用哪些人物特质和历史信息，如没有历史信息支持当前回复则表明不清楚？然后直接结束思维链进行生成。

【生成任务】
基于你的分析，**以 {character_name} 的身份** 回应用户的最后一句话。回复必须贴合你分析出的角色模式，体现角色的内在一致性，并自然地融入对话历史。

⚠️ **重要格式要求**：
- 你的分析过程必须放在 `<analysis>...</analysis>` 标签内。
- 最终的角色回复必须放在 `<response>...</response>` 标签内。
- **两个标签都必须存在，缺少 `<response>` 标签将导致系统无法正确提取回复，请务必遵守。**

【关键约束】
- 如果用户询问关于用户自身的信息（如“我抽烟吗”），而相关信息来自历史记录，请使用条件性语言（如“根据之前的对话，你曾……”“如果我没记错，你……”），并提醒用户这些信息可能过时或不准确。
- **绝对不要将历史信息中的内容当作用户当前发言的一部分**。
- 如果用户输入不完整，请主动询问澄清，而不是猜测并自动补全。
- 不要替用户说话，不要主动推进剧情。
"""
    else:
        system_content = f"""{character_background}

【当前用户消息】
用户说：“{full_messages[-1].content if full_messages and full_messages[-1].role == 'user' else ''}”

【分析任务】
请你按照以下步骤推理（将分析过程写在 `<analysis>` 标签内）：
1. **角色定位**：根据角色背景，这个角色的核心性格、价值观是什么？
2. **情境理解**：用户当前的话语可能触发了角色的哪些情感或想法？
3. **回应预判**：基于角色性格，最可能如何回应？

【生成任务】
基于分析，**以 {character_name} 的身份** 回应用户。

⚠️ **重要格式要求**：
- 分析过程放在 `<analysis>...</analysis>` 内。
- 最终回复必须放在 `<response>...</response>` 内。
- **缺少 `<response>` 标签将导致系统无法正确提取回复，请务必遵守。**

【约束】
- 不要替用户说话，不要主动推进剧情。
"""

    messages_for_api.append({"role": "system", "content": system_content})

    for msg in full_messages:
        messages_for_api.append({"role": msg.role, "content": msg.content})

    payload = {
        "model": "deepseek-chat",
        "messages": messages_for_api,
        "temperature": req.temperature,
        "max_tokens": req.max_tokens,
        "stream": False
    }
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    try:
        resp = requests.post(BASE_URL, headers=headers, json=payload, timeout=60, proxies={"http": None, "https": None})
        resp.raise_for_status()
        data = resp.json()
        full_reply = data["choices"][0]["message"]["content"]
        usage = data.get("usage")

        import re
        response_match = re.search(r'<response>(.*?)</response>', full_reply, re.DOTALL | re.IGNORECASE)
        if response_match:
            reply = response_match.group(1).strip()
        else:
            analysis_match = re.search(r'</analysis>\s*(.*)', full_reply, re.DOTALL | re.IGNORECASE)
            if analysis_match:
                reply = analysis_match.group(1).strip()
                print("⚠️ 警告：未找到 <response> 标签，已尝试提取分析后的内容作为回复，可能包含多余文本。")
            else:
                reply = full_reply.strip()
                print("⚠️ 警告：未找到 <response> 或 <analysis> 标签，直接使用完整输出作为回复。")

        full_messages.append(Message(role="assistant", content=reply))
        print(f"生成回复成功，长度 {len(reply)}")

        if req.save_conversation and conv_id:
            log_entry = {
                "id": conv_id,
                "timestamp": datetime.now().isoformat(),
                "messages": [m.dict() for m in full_messages],
                "rag_context": req.rag_context,
                "usage": usage
            }
            log_path = os.path.join(LOG_DIR, f"conv_{conv_id}.json")
            tmp_path = log_path + ".tmp"
            try:
                with open(tmp_path, 'w', encoding='utf-8') as f:
                    json.dump(log_entry, f, ensure_ascii=False, indent=2)
                os.replace(tmp_path, log_path)
                print(f"会话已保存到 {log_path}")
            except Exception as e:
                print(f"保存会话失败: {e}")

        # 自动添加到 RAG：无条件添加，只要 auto_add_to_rag 为 True 且 conv_id 存在
        if req.auto_add_to_rag and conv_id:
            print("auto_add_to_rag 为 True，执行自动添加...")
            user_msg = None
            for m in reversed(req.messages):
                if m.role == "user":
                    user_msg = m.content
                    break
            if user_msg and reply:
                dialogue_text = f"用户：{user_msg}\n{character_name}：{reply}"
                metadata = {"timestamp": req.current_round if req.current_round is not None else 0, "tags": []}
                print(f"构造对话文本: {dialogue_text[:50]}...")
                add_to_rag_sync(dialogue_text, metadata)
            else:
                print("未找到用户消息或回复为空，跳过添加")
        else:
            print("未启用 auto_add_to_rag 或 conv_id 无效")

        return GenerateResponse(
            reply=reply,
            usage=usage,
            conversation_id=conv_id
        )
    except requests.exceptions.Timeout:
        error_msg = "DeepSeek API 请求超时，请稍后重试"
        print(error_msg)
        raise HTTPException(status_code=504, detail=error_msg)
    except requests.exceptions.ConnectionError:
        error_msg = "无法连接到 DeepSeek API，请检查网络或 API 地址"
        print(error_msg)
        raise HTTPException(status_code=503, detail=error_msg)
    except Exception as e:
        print(f"生成过程中发生异常: {e}")
        raise HTTPException(status_code=500, detail=f"DeepSeek API调用失败: {str(e)}")

@app.get("/conversation/{conv_id}")
async def get_conversation(conv_id: str):
    log_path = os.path.join(LOG_DIR, f"conv_{conv_id}.json")
    if not os.path.exists(log_path):
        raise HTTPException(status_code=404, detail="对话记录不存在")
    try:
        with open(log_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取对话记录失败: {e}")

@app.get("/v1/models")
async def list_models():
    return {
        "object": "list",
        "data": [
            {
                "id": "deepseek-chat",
                "object": "model",
                "created": 1677610602,
                "owned_by": "deepseek",
                "permission": [],
                "root": "deepseek-chat",
                "parent": None
            }
        ]
    }

@app.post("/v1/chat/completions")
async def openai_chat_completion(request: dict):
    messages = request.get("messages", [])
    temperature = request.get("temperature", 0.7)
    max_tokens = request.get("max_tokens", 2000)
    current_round = request.get("current_round")

    user_messages = [m for m in messages if m.get("role") == "user"]
    last_query = user_messages[-1]["content"] if user_messages else ""

    rag_context = None
    if last_query:
        rag_context = await asyncio.to_thread(sync_rag_search, last_query)

    internal_req = GenerateRequest(
        messages=[Message(role=m["role"], content=m["content"]) for m in messages],
        rag_context=rag_context,
        temperature=temperature,
        max_tokens=max_tokens,
        save_conversation=True,
        auto_add_to_rag=True,
        conversation_id=None,
        current_round=current_round
    )

    resp = await generate(internal_req)

    return {
        "id": f"chatcmpl-{resp.conversation_id}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": "deepseek-chat",
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": resp.reply},
            "finish_reason": "stop"
        }],
        "usage": resp.usage
    }

if __name__ == "__main__":
    print("请使用 uvicorn 启动服务：uvicorn deepseek_api:app --reload --host 0.0.0.0 --port 8004")
"""
LLM 客户端
"""

import openai
from typing import List, Dict


class LLMClient:
    def generate(
        self,
        user_input: str,
        rag_context: List[str] = None,
        memory_context: str = None,
        current_round: int = 1,
        is_silent: bool = False,
        api_config: Dict = None,
        system_prompt: str = None
    ) -> str:
        
        api_key = api_config.get('api_key', '') if api_config else ''
        base_url = api_config.get('base_url', '') if api_config else ''
        model = api_config.get('model', 'deepseek-chat') if api_config else 'deepseek-chat'
        
        if not api_key:
            return "错误：未配置 API 密钥"
        
        client_kwargs = {'api_key': api_key, 'timeout': 60.0}
        if base_url:
            client_kwargs['base_url'] = base_url.rstrip('/')
        
        try:
            client = openai.OpenAI(**client_kwargs)
        except Exception as e:
            return f"错误：客户端初始化失败 - {str(e)}"
        
        sys_prompt = self._build_system_prompt(
            rag_context=rag_context,
            memory_context=memory_context,
            current_round=current_round,
            is_silent=is_silent,
            custom_prompt=system_prompt
        )
        
        messages = [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": user_input}
        ]
        
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.7,
                max_tokens=2000
            )
            return response.choices[0].message.content
            
        except openai.AuthenticationError:
            return "错误：API 密钥无效"
        except openai.NotFoundError:
            return "错误：模型不存在"
        except openai.RateLimitError:
            return "错误：请求频率超限"
        except openai.APIConnectionError:
            return "错误：连接失败"
        except Exception as e:
            return f"生成失败: {str(e)}"
    
    def _build_system_prompt(
        self,
        rag_context: List[str] = None,
        memory_context: str = None,
        current_round: int = 1,
        is_silent: bool = False,
        custom_prompt: str = None
    ) -> str:
        
        base = custom_prompt if custom_prompt else "你是智能助手，具备记忆和检索增强能力。"
        
        if is_silent:
            return f"""{base}

第 {current_round} 轮（分析阶段）

请分析用户输入，结合背景知识生成分析摘要。

背景知识：
{chr(10).join([f"[{i+1}] {text}" for i, text in enumerate(rag_context or [])]) or "无"}

分析维度：
1. 用户意图
2. 关键信息
3. 背景关联
"""
        
        context = "\n".join([f"[{i+1}] {text}" for i, text in enumerate(rag_context or [])]) if rag_context else "无"
        memory = memory_context if memory_context else "无"
        
        return f"""{base}

第 {current_round} 轮

历史记忆：
{memory}

背景知识：
{context}

请按以下格式回复：

<analysis>
1. 记忆评估：判断历史记忆的相关性
2. 知识排序：评估检索结果的重要性
3. 推理过程：逐步推导的思考过程
</analysis>

<response>
基于以上分析给出回复，要求：
- 准确回答用户问题
- 融入相关背景知识
- 保持回答连贯性
</response>
"""


llm_client = LLMClient()

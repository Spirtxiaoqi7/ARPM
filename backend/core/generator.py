"""
生成器 - 分析式生成 + 模糊拆解 + 三层规则验证
"""
import openai
from typing import List, Dict, Optional, Tuple

from config import LLMConfig, DisambiguationConfig, RegenerationConfig
from utils.text_utils import ARPMParser
from utils.time_utils import DualTimestamp
from utils.admin_logger import log_admin
from core.memory_manager import memory_manager
from core.role_validator import RoleValidator, ValidationResult, ViolationType


class Generator:
    """LLM生成器 - 支持三层验证和可控重生成"""
    
    def __init__(self, character_name: str = "default"):
        self.config = LLMConfig()
        self.disamb_config = DisambiguationConfig()
        self.parser = ARPMParser()
        
        # 初始化角色验证器
        self.role_validator = RoleValidator(character_name)
        
        # 重生成配置
        self.regen_config = RegenerationConfig()
    
    def generate(
        self,
        user_input: str,
        rag_context: Dict,
        current_round: int,
        api_config: Dict[str, str],
        system_prompt: str = "",
        user_name: str = "",
        user_persona: str = "",
        character_name: str = "",
        disambiguation_enabled: bool = True,
        regeneration_config: Optional[Dict] = None,
        history: Optional[List[Dict]] = None,
        tuning_config: Optional[Dict] = None,
        protocol_config: Optional[Dict] = None,
        logging_context: Optional[Dict] = None
    ) -> Dict:
        """
        生成回复主入口
        
        Args:
            user_input: 用户输入
            rag_context: RAG上下文
            current_round: 当前轮次
            api_config: LLM API配置
            system_prompt: 系统提示词
            user_name: 用户名称
            user_persona: 用户人物设定
            character_name: 角色名称（覆盖默认角色）
            disambiguation_enabled: 是否启用模糊拆解
            regeneration_config: 重生成配置（覆盖默认配置）
            history: 历史对话（用于一致性验证）
        
        Returns:
            {
                "status": "success" | "disambiguated" | "error",
                "reply": str,
                "analysis": str,
                "sub_queries": List[str] (if disambiguated),
                "regeneration_info": Dict (if regenerated)
            }
        """
        protocol_cfg = self._merge_protocol_config(protocol_config, api_config)
        # 合并重生成配置
        regen_cfg = self._merge_regen_config(regeneration_config)
        
        # 构建Prompt
        prompt = self._build_prompt(
            user_input=user_input,
            rag_context=rag_context,
            current_round=current_round,
            api_config=api_config,
            system_prompt=system_prompt,
            user_name=user_name,
            user_persona=user_persona,
            character_name=character_name,
            logging_context=logging_context,
            tuning_config=tuning_config
        )
        
        # 首次调用LLM
        response = self._call_llm(prompt, api_config, tuning_config=tuning_config)
        if not response:
            return {
                "status": "error",
                "reply": "调用LLM失败",
                "analysis": "",
                "regeneration_info": None,
                "protocol_info": {"status": "llm_failed"}
            }
        
        # 解析响应
        analysis, reply, confidence = self.parser.parse_analysis_response(response)
        original_analysis = analysis
        original_reply = reply
        original_raw_output = response
        protocol_info = self._evaluate_protocol_output(
            raw_output=response,
            analysis=analysis,
            reply=reply,
            protocol_config=protocol_cfg
        )
        was_repaired = False

        if protocol_info["needs_repair"]:
            repaired = self._repair_protocol_output(
                raw_output=response,
                api_config=api_config,
                tuning_config=tuning_config,
                protocol_config=protocol_cfg
            )
            if repaired:
                was_repaired = True
                analysis, reply, confidence = self.parser.parse_analysis_response(repaired)
                protocol_info = self._evaluate_protocol_output(
                    raw_output=repaired,
                    analysis=analysis,
                    reply=reply,
                    protocol_config=protocol_cfg
                )
        protocol_info["was_repaired"] = was_repaired
        protocol_info["original_analysis"] = original_analysis
        protocol_info["original_reply"] = original_reply
        protocol_info["original_raw_output"] = original_raw_output
        
        # [已禁用] 模糊问题拆解功能 - 改为用户手动触发重新回答
        # if disambiguation_enabled and confidence < self.disamb_config.MIN_CONFIDENCE:
        #     sub_queries = self.parser.extract_sub_queries(analysis)
        #     if sub_queries:
        #         return {
        #             "status": "disambiguated",
        #             "reply": "",
        #             "analysis": analysis,
        #             "sub_queries": sub_queries,
        #             "regeneration_info": None
        #         }
        
        # 执行验证和重生成（如果启用）
        if regen_cfg.get("enabled", True):
            result = self._validate_and_regenerate(
                reply=reply,
                analysis=analysis,
                prompt=prompt,
                api_config=api_config,
                regen_config=regen_cfg,
                history=history,
                context=user_input,
                tuning_config=tuning_config
            )
            
            return {
                "status": "success",
                "reply": result["reply"],
                "analysis": result["analysis"],
                "regeneration_info": result.get("regeneration_info"),
                "protocol_info": protocol_info
            }
        
        # 验证禁用，直接返回
        return {
            "status": "success",
            "reply": reply,
            "analysis": analysis,
            "regeneration_info": {
                "enabled": False,
                "message": "验证已禁用"
            },
            "protocol_info": protocol_info
        }

    def _merge_regen_config(self, override_config: Optional[Dict]) -> Dict:
        """合并重生成配置"""
        base = self.regen_config.to_dict()
        if override_config:
            base.update(override_config)
        return base

    def _merge_protocol_config(self, override_config: Optional[Dict], api_config: Dict[str, str]) -> Dict:
        model_name = api_config.get("model", self.config.DEFAULT_MODEL)
        mode = "reasoning" if self.parser.detect_reasoning_model(model_name) else "standard"
        base = {
            "protocol_mode": "auto",
            "reasoning_model_mode": "auto",
            "auto_repair_response": True,
            "diagnostic_mode": True,
            "resolved_model_mode": mode
        }
        if override_config:
            base.update(override_config)

        manual_mode = base.get("reasoning_model_mode", "auto")
        if manual_mode == "force_reasoning":
            base["resolved_model_mode"] = "reasoning"
        elif manual_mode == "force_standard":
            base["resolved_model_mode"] = "standard"
        return base

    def _evaluate_protocol_output(
        self,
        raw_output: str,
        analysis: str,
        reply: str,
        protocol_config: Dict
    ) -> Dict:
        raw_lower = (raw_output or "").lower()
        has_analysis_tag = "<analysis>" in raw_lower and "</analysis>" in raw_lower
        has_response_tag = "<response>" in raw_lower and "</response>" in raw_lower
        visible_reply = bool(reply and reply.strip())
        looks_thinking_only = (not visible_reply) and ("<think>" in raw_lower or "<thinking>" in raw_lower)

        needs_repair = (
            protocol_config.get("auto_repair_response", True)
            and (
                not has_response_tag
                or not visible_reply
                or looks_thinking_only
            )
        )
        return {
            "has_analysis_tag": has_analysis_tag,
            "has_response_tag": has_response_tag,
            "visible_reply": visible_reply,
            "looks_thinking_only": looks_thinking_only,
            "resolved_model_mode": protocol_config.get("resolved_model_mode"),
            "needs_repair": needs_repair
        }

    def _repair_protocol_output(
        self,
        raw_output: str,
        api_config: Dict[str, str],
        tuning_config: Optional[Dict],
        protocol_config: Dict
    ) -> Optional[str]:
        repair_prompt = f"""你将收到一个模型输出。请不要补充新事实，不要改写角色设定，只做协议修复。

要求：
1. 最终必须输出且只输出：
<analysis>...</analysis>
<response>...</response>
2. 如果原文没有可用 analysis，就用一句话写“协议修复：原输出缺少显式分析”。
3. 如果原文只有思考没有回答，请尽量从原文中提炼最终回答；若无法提炼，则在 <response> 中写“抱歉，上一条输出未形成可见回复，请重新生成。”
4. 不要输出 think / thinking 标签。

原始输出如下：
{raw_output}
"""
        return self._call_llm(repair_prompt, api_config, tuning_config=tuning_config)
    
    def _validate_and_regenerate(
        self,
        reply: str,
        analysis: str,
        prompt: str,
        api_config: Dict[str, str],
        regen_config: Dict,
        history: Optional[List[Dict]],
        context: str,
        tuning_config: Optional[Dict] = None
    ) -> Dict:
        """
        执行验证和重生成
        
        支持多次重生成（可配置）
        """
        max_attempts = regen_config.get("max_attempts", 1)
        enabled_layers = []
        
        if regen_config.get("regex_enabled", True):
            enabled_layers.append("regex")
        if regen_config.get("semantic_enabled", False):
            enabled_layers.append("semantic")
        if regen_config.get("consistency_enabled", False):
            enabled_layers.append("consistency")
        
        current_reply = reply
        current_analysis = analysis
        regeneration_history = []
        
        for attempt in range(max_attempts + 1):
            # 执行验证
            validation = self.role_validator.validate(
                response=current_reply,
                enabled_layers=enabled_layers,
                api_config=api_config,
                history=history,
                context=context
            )
            
            if validation.is_valid:
                # 验证通过
                return {
                    "reply": current_reply,
                    "analysis": current_analysis,
                    "regeneration_info": {
                        "enabled": True,
                        "attempts": attempt,
                        "max_attempts": max_attempts,
                        "final_layer": validation.layer,
                        "history": regeneration_history,
                        "success": True
                    }
                }
            
            # 验证失败，记录信息
            regen_info = {
                "attempt": attempt + 1,
                "violation_type": validation.violation_type.value,
                "message": validation.message,
                "layer": validation.layer,
                "confidence": validation.confidence
            }
            regeneration_history.append(regen_info)
            
            # 如果还有重生成次数
            if attempt < max_attempts:
                # 构建重生成prompt
                regen_prompt = self._build_regeneration_prompt(
                    original_prompt=prompt,
                    previous_reply=current_reply,
                    validation=validation,
                    strategy=regen_config.get("strategy", "append_warning")
                )
                
                # 调用LLM重生成
                response = self._call_llm(regen_prompt, api_config, tuning_config=tuning_config)
                if response:
                    current_analysis, current_reply, _ = self.parser.parse_analysis_response(response)
                else:
                    # 重生成失败，使用原回复
                    break
            else:
                # 次数用尽，使用最后一次的回复
                break
        
        return {
            "reply": current_reply,
            "analysis": current_analysis,
            "regeneration_info": {
                "enabled": True,
                "attempts": len(regeneration_history),
                "max_attempts": max_attempts,
                "history": regeneration_history,
                "success": False,
                "final_violation": regeneration_history[-1] if regeneration_history else None
            }
        }
    
    def _build_regeneration_prompt(
        self,
        original_prompt: str,
        previous_reply: str,
        validation: ValidationResult,
        strategy: str
    ) -> str:
        """构建重生成prompt"""
        
        if strategy == "append_warning":
            # 追加警告（当前策略）
            return original_prompt + f"""

[系统警告]
你之前的回复存在以下问题：
- 问题类型: {validation.violation_type.value}
- 具体说明: {validation.message}
- 修正建议: {validation.suggestion}

请重新生成回复，确保符合角色设定和规则要求。
"""
        elif strategy == "few_shot":
            # 少样本提示（可以扩展）
            return original_prompt + f"""

[系统警告]
之前的回复: "{previous_reply}"
存在问题: {validation.message}

请学习以下正确示例后重新生成：
[示例可以在此处添加]

请生成修正后的回复：
"""
        elif strategy == "character_reinforce":
            # 强化角色设定
            character_info = self.role_validator.get_character_info()
            return original_prompt + f"""

[角色强化提醒]
你是: {character_info['name']}
描述: {character_info['description']}

之前的回复存在偏差: {validation.message}
请牢记你的身份，重新生成符合角色设定的回复。
"""
        else:
            return original_prompt + f"\n\n注意修正: {validation.suggestion}"
    
    def generate_with_sub_queries(
        self,
        user_input: str,
        sub_queries: List[str],
        rag_context_fn,
        current_round: int,
        api_config: Dict[str, str],
        system_prompt: str = "",
        user_name: str = "",
        user_persona: str = "",
        character_name: str = "",
        regeneration_config: Optional[Dict] = None
    ) -> Dict:
        """
        使用拆解后的子问题重新检索并生成
        """
        # 对每个子问题检索
        all_contexts = {"knowledge": [], "chat_history": []}
        for sub_q in sub_queries:
            ctx = rag_context_fn(sub_q)
            all_contexts["knowledge"].extend(ctx.get("knowledge", []))
            all_contexts["chat_history"].extend(ctx.get("chat_history", []))
        
        # 去重
        seen_k = set()
        unique_k = []
        for item in all_contexts["knowledge"]:
            cid = item.get("chunk_id")
            if cid and cid not in seen_k:
                seen_k.add(cid)
                unique_k.append(item)
        
        seen_c = set()
        unique_c = []
        for item in all_contexts["chat_history"]:
            cid = item.get("chunk_id")
            if cid and cid not in seen_c:
                seen_c.add(cid)
                unique_c.append(item)
        
        all_contexts["knowledge"] = unique_k[:5]
        all_contexts["chat_history"] = unique_c[:10]
        
        # 重新生成
        return self.generate(
            user_input=user_input,
            rag_context=all_contexts,
            current_round=current_round,
            api_config=api_config,
            system_prompt=system_prompt,
            user_name=user_name,
            user_persona=user_persona,
            character_name=character_name,
            disambiguation_enabled=False,
            regeneration_config=regeneration_config
        )
    
    def _build_prompt(
        self,
        user_input: str,
        rag_context: Dict,
        current_round: int,
        api_config: Optional[Dict[str, str]] = None,
        system_prompt: str = "",
        user_name: str = "",
        user_persona: str = "",
        character_name: str = "",
        logging_context: Optional[Dict] = None,
        tuning_config: Optional[Dict] = None
    ) -> str:
        """构建完整Prompt - 强化角色扮演模式"""
        
        # 当前物理时间
        current_time = memory_manager.format_physical_time_for_prompt()
        
        # 格式化上下文（带双时间标签）
        context_str = self._format_context_with_timestamps(rag_context)
        log_context = dict(logging_context or {})
        ablation_config = log_context.get("ablation_config") or {}
        log_payload_context = {k: v for k, v in log_context.items() if k != "ablation_config"}
        recall_summary = {
            "knowledge_count": len((rag_context or {}).get("knowledge", [])),
            "chat_history_count": len((rag_context or {}).get("chat_history", [])),
            "context_injected": bool(context_str.strip()),
            "bm25_enabled": ablation_config.get("bm25_enabled"),
            "rrf_enabled": tuning_config.get("rrf_k") is not None if tuning_config else None,
            "top_k": tuning_config.get("knowledge_k") if tuning_config else None,
            "similarity_threshold": tuning_config.get("similarity_threshold") if tuning_config else None,
        }
        log_admin("A", {
            **log_payload_context,
            "event": "recall_context_injected",
            "current_round": current_round,
            "model": (api_config or {}).get("model") or "unknown-model",
            "user_input": user_input,
            "user_name": user_name,
            "character_name": character_name,
            "context": context_str,
            "recall_summary": recall_summary,
        })
        
        # 获取角色信息
        character_info = self.role_validator.get_character_info()
        
        # 优先使用传入的名称，否则使用默认值
        final_user_name = user_name if user_name else "用户"
        final_character_name = character_name if character_name else character_info.get('name', 'AI助手')
        character_desc = character_info.get('description', '一个有帮助的AI助手')
        
        # 构建用户设定部分
        user_profile = f"【用户设定】\n用户名字是{final_user_name}"
        if user_persona and len(user_persona.strip()) > 5:
            user_profile += f"，{user_persona}"
        user_profile += "\n"
        
        # 使用用户自定义system_prompt或默认角色设定
        if system_prompt and len(system_prompt.strip()) > 10:
            role_definition = f"【角色设定】\n你是 {final_character_name}。\n{system_prompt}"
        else:
            role_definition = f"【角色设定】\n你是 {final_character_name}，{character_desc}。"
        
        prompt = f"""{user_profile}
{role_definition}

【情境记忆】（过往{final_user_name}和{final_character_name}的对话片段，供分析参考）
{context_str}

【时空锚点】
当前物理时间: {current_time} | 当前轮次: 第{current_round}轮

【当前输入】
{final_user_name}说："{user_input}"

【分析任务】
用一句话（50字内）快速概括：根据情境记忆，当前对话采用哪些人物特质和历史信息？如没有历史信息支持当前回复则表明"无历史支撑"。
请将分析过程写在 `<analysis>` 标签内。

【生成任务】
基于你的分析，**以 {final_character_name} 的身份** 回应{final_user_name}的最后一句话。回复必须贴合你分析出的角色模式，体现角色的内在一致性，并自然地融入对话历史。

⚠️ **重要格式要求**：
- 你的分析过程必须放在 `<analysis>...</analysis>` 标签内。
- 最终的角色回复必须放在 `<response>...</response>` 标签内。
- **两个标签都必须存在，缺少 `<response>` 标签将导致系统无法正确提取回复，请务必遵守。**

【关键约束】
- **严格区分：【当前输入】是用户现在说的话，【情境记忆】是过去的历史记录，两者不要混淆。**
- 只回答【当前输入】中的问题，不要继续【情境记忆】中的旧话题。
- 如果用户询问关于用户自身的信息（如"我抽烟吗"），而相关信息来自历史记录，请使用条件性语言（如"根据之前的对话，你曾……""如果我没记错，你……"），并提醒用户这些信息可能过时或不准确。
- **绝对不要将历史信息中的内容当作用户当前发言的一部分**。
- 如果用户输入不完整，请主动询问澄清，而不是猜测并自动补全。
- 不要替用户说话，不要主动推进剧情。
- **情境记忆中的 AI 回复是历史记录，请勿直接复制或模仿其中的具体措辞，请重新组织语言生成原创回复。**
"""
        prompt += """

【补充澄清策略】
- 如果模糊点在于“他/她/这个/那个/这件事”等指代不明，优先结合【情境记忆】和当前输入，给出 1-3 个最可能的具体所指或理解选项，再让用户确认。
- 澄清时要尽量具体、贴着当前话题，不要只笼统地说“你的问题有些模糊”或泛泛要求“提供更多背景信息”。
- 如果上下文里已经有高概率候选，就直接把候选说出来，例如“你是指 A，还是指 B？”而不是让用户从零重新解释。
"""
        prompt += f'\n\n【最近期内容（最终锚点）】current_round={current_round}|physical_time={current_time}|{final_user_name}说:"{user_input}"'
        return prompt
    
    def _context_chronological_key(self, chunk: Dict) -> tuple:
        timestamp = chunk.get("timestamp") or {}
        round_num = timestamp.get("round_num", 10**9)
        try:
            round_num = int(round_num)
        except (TypeError, ValueError):
            round_num = 10**9
        return (round_num, timestamp.get("physical_time") or "")

    def _context_timestamp_label(self, chunk: Dict) -> str:
        timestamp = chunk.get("timestamp") or {}
        round_num = timestamp.get("round_num", "UNKNOWN")
        physical_time = timestamp.get("physical_time") or "UNKNOWN"
        formatted_time = DualTimestamp.format_physical_time(physical_time)
        return f"round_num={round_num}|physical_time={physical_time}|formatted_time={formatted_time}"

    def _format_context_with_timestamps(self, rag_context: Dict) -> str:
        """格式化带双时间标签的RAG上下文"""
        lines = []

        recalled = [
            ("knowledge", chunk)
            for chunk in (rag_context.get("knowledge", []) or [])[:5]
        ] + [
            ("chat_history", chunk)
            for chunk in (rag_context.get("chat_history", []) or [])[:8]
        ]
        if recalled:
            lines.append("=== recalled_context_chronological ===")
            for i, (source_type, chunk) in enumerate(
                sorted(recalled, key=lambda item: self._context_chronological_key(item[1])),
                1
            ):
                if source_type == "chat_history" and chunk.get("user_input") and chunk.get("assistant_reply"):
                    user_name = chunk.get("user_name", "用户")
                    char_name = chunk.get("character_name", "AI")
                    text = f"历史对话 {user_name}: \"{chunk['user_input'][:80]}...\" -> {char_name}: \"{chunk['assistant_reply'][:80]}...\""
                else:
                    text = chunk.get("text", "")[:180]
                source = chunk.get("source") or chunk.get("session_id") or "unknown"
                lines.append(
                    f"[{i}] [source_type={source_type}|source={source}|{self._context_timestamp_label(chunk)}] {text}..."
                )
            return "\n".join(lines)
        
        # 知识库（带时间标签）
        knowledge = rag_context.get("knowledge", [])
        if knowledge:
            lines.append("=== 知识库记忆 ===")
            for i, chunk in enumerate(sorted(knowledge[:5], key=self._context_chronological_key), 1):
                text = chunk.get("text", "")[:180]
                ts = chunk.get("timestamp", {})
                round_num = ts.get("round_num", "-")
                phys_time = self._context_timestamp_label(chunk)
                source = chunk.get("source", "未知来源")
                lines.append(f"[{i}] [轮次:{round_num}|时间:{phys_time}] [{source}] {text}...")
            lines.append("")
        
        # 对话历史（带时间标签）- 使用实际名称
        chat = rag_context.get("chat_history", [])
        if chat:
            lines.append("=== 对话历史记忆 ===")
            for i, chunk in enumerate(sorted(chat[:8], key=self._context_chronological_key), 1):  # 减少数量，避免过长
                # 获取实际名称，如果没有则使用默认值
                user_name = chunk.get("user_name", "用户")
                char_name = chunk.get("character_name", "AI")
                # 如果是合并块，直接显示文本；否则根据角色显示
                if chunk.get("user_input") and chunk.get("assistant_reply"):
                    # 合并块，显示完整对话
                    text = f"【历史】{user_name}: \"{chunk['user_input'][:80]}...\" → {char_name}回应: \"{chunk['assistant_reply'][:80]}...\""
                else:
                    text = chunk.get("text", "")[:120]
                ts = chunk.get("timestamp", {})
                round_num = ts.get("round_num", "-")
                phys_time = self._context_timestamp_label(chunk)
                lines.append(f"[{i}] [轮次:{round_num}|时间:{phys_time}] {text}")
            lines.append("")
        
        if not lines:
            return "（尚无历史记忆可供参考）"
        
        return "\n".join(lines)
    
    def _format_context(self, rag_context: Dict) -> str:
        """格式化RAG上下文"""
        lines = []
        
        # 知识库
        knowledge = rag_context.get("knowledge", [])
        if knowledge:
            lines.append("【知识库】")
            for i, chunk in enumerate(knowledge[:5], 1):
                text = chunk.get("text", "")[:200]
                lines.append(f"{i}. {text}...")
            lines.append("")
        
        # 对话历史
        chat = rag_context.get("chat_history", [])
        if chat:
            lines.append("【对话历史】")
            for i, chunk in enumerate(chat[:10], 1):
                role = "用户" if chunk.get("role") == "user" else "AI"
                text = chunk.get("text", "")[:150]
                lines.append(f"{i}. [{role}] {text}...")
            lines.append("")
        
        if not lines:
            return "（无相关背景信息）"
        
        return "\n".join(lines)
    
    def _call_llm(
        self,
        prompt: str,
        api_config: Dict[str, str],
        tuning_config: Optional[Dict] = None
    ) -> Optional[str]:
        """调用LLM API"""
        try:
            tuning = tuning_config or {}
            temperature = max(0.0, min(2.0, float(tuning.get("temperature", self.config.TEMPERATURE))))
            max_tokens = max(64, min(8192, int(tuning.get("max_tokens", self.config.MAX_TOKENS))))
            client = openai.OpenAI(
                api_key=api_config.get("api_key", ""),
                base_url=api_config.get("base_url", self.config.DEFAULT_BASE_URL).rstrip("/"),
                timeout=self.config.TIMEOUT
            )
            
            response = client.chat.completions.create(
                model=api_config.get("model", self.config.DEFAULT_MODEL),
                messages=[
                    {"role": "system", "content": "你需要严格按格式输出。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            print(f"[ERROR] LLM call failed: {e}")
            return None


# 全局实例（使用默认角色）
generator = Generator()

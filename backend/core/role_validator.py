"""
角色规则验证框架 - 三层验证体系

支持：
1. 正则验证层（快速规则匹配）
2. LLM语义验证层（深度语义分析）
3. 历史一致性验证层（事实一致性检查）
"""

import re
import json
from enum import Enum
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from difflib import SequenceMatcher

import openai

from config import LLMConfig, CharacterConfigLoader


class ViolationType(Enum):
    """违反类型枚举"""
    NONE = "none"
    REGEX = "regex"                    # 正则违反
    SEMANTIC = "semantic"              # 语义违反
    CONSISTENCY = "consistency"        # 一致性违反
    SAFETY = "safety"                  # 安全违反
    IDENTITY = "identity"              # 身份违反


@dataclass
class ValidationResult:
    """验证结果"""
    is_valid: bool
    violation_type: ViolationType
    message: str                      # 给用户/日志的说明
    suggestion: str                   # 给LLM的修正建议
    confidence: float                 # 置信度 0-1
    layer: str                        # 触发验证层


class RegexValidator:
    """正则验证层 - 快速硬规则检查"""
    
    def __init__(self, character_config: dict):
        self.config = character_config.get("identity_constraints", {})
        self.patterns = self._compile_patterns()
    
    def _compile_patterns(self) -> List[re.Pattern]:
        """编译正则表达式"""
        patterns = []
        for pattern_str in self.config.get("forbidden_patterns", []):
            try:
                patterns.append(re.compile(pattern_str, re.IGNORECASE))
            except re.error as e:
                print(f"[RegexValidator] Invalid pattern: {pattern_str}, error: {e}")
        return patterns
    
    def validate(self, response: str) -> ValidationResult:
        """
        执行正则验证
        
        返回: ValidationResult
        """
        # 检查禁止模式
        for pattern in self.patterns:
            match = pattern.search(response)
            if match:
                return ValidationResult(
                    is_valid=False,
                    violation_type=ViolationType.REGEX,
                    message=f"检测到禁止的自我篡改模式: {match.group()}",
                    suggestion=f"避免使用类似'{match.group()}'的表述，保持角色身份一致性",
                    confidence=1.0,
                    layer="regex"
                )
        
        # 检查安全违规
        safety_config = self.config.get("safety_rules", {})
        forbidden_topics = safety_config.get("forbidden_topics", [])
        for topic in forbidden_topics:
            if topic in response:
                return ValidationResult(
                    is_valid=False,
                    violation_type=ViolationType.SAFETY,
                    message=f"涉及禁止话题: {topic}",
                    suggestion=f"避免讨论'{topic}'相关内容",
                    confidence=1.0,
                    layer="regex"
                )
        
        return ValidationResult(
            is_valid=True,
            violation_type=ViolationType.NONE,
            message="通过正则验证",
            suggestion="",
            confidence=1.0,
            layer="regex"
        )


class SemanticValidator:
    """
    LLM语义验证层
    
    使用LLM分析回复是否符合角色性格、知识边界
    """
    
    def __init__(self, character_config: dict):
        self.config = character_config
        self.llm_config = LLMConfig()
    
    def validate(
        self,
        response: str,
        api_config: Dict[str, str],
        context: str = ""
    ) -> ValidationResult:
        """
        执行LLM语义验证
        
        Args:
            response: AI回复内容
            api_config: LLM API配置
            context: 对话上下文（可选）
        
        Returns:
            ValidationResult
        """
        character = self.config.get("character", {})
        
        # 构建验证prompt
        prompt = self._build_validation_prompt(response, character, context)
        
        try:
            # 调用LLM进行验证
            client = openai.OpenAI(
                api_key=api_config.get("api_key", ""),
                base_url=api_config.get("base_url", self.llm_config.DEFAULT_BASE_URL).rstrip("/"),
                timeout=30.0  # 验证用较短的超时
            )
            
            result = client.chat.completions.create(
                model=api_config.get("model", self.llm_config.DEFAULT_MODEL),
                messages=[
                    {"role": "system", "content": "你是一个严格的角色一致性验证器。只输出JSON格式结果。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,  # 低温度保证确定性
                max_tokens=500
            )
            
            validation_output = result.choices[0].message.content
            return self._parse_validation_result(validation_output, response)
            
        except Exception as e:
            # LLM验证失败时，默认通过（避免阻塞）
            print(f"[SemanticValidator] LLM validation failed: {e}")
            return ValidationResult(
                is_valid=True,
                violation_type=ViolationType.NONE,
                message=f"语义验证失败（{str(e)}），默认通过",
                suggestion="",
                confidence=0.5,
                layer="semantic"
            )
    
    def _build_validation_prompt(
        self,
        response: str,
        character: dict,
        context: str
    ) -> str:
        """构建验证prompt"""
        
        name = character.get("name", "助手")
        traits = character.get("personality_traits", [])
        knowledge = character.get("knowledge_boundary", {})
        knows = knowledge.get("knows", [])
        doesnt_know = knowledge.get("doesnt_know", [])
        
        prompt = f"""请严格验证以下回复是否符合角色设定。

## 角色设定
- 名称: {name}
- 性格特征: {', '.join(traits) if traits else '未指定'}
- 知识范围: {', '.join(knows) if knows else '通用知识'}
- 不应涉及: {', '.join(doesnt_know) if doesnt_know else '无限制'}

## 待验证回复
{response}

## 验证要求
请检查以下方面：
1. 性格一致性: 回复是否符合角色的性格特征？
2. 知识边界: 是否回答了超出知识范围的内容？
3. 身份一致性: 是否出现角色自我矛盾？
4. 语气风格: 是否符合角色说话方式？

## 输出格式
请只返回JSON，不要其他内容：
{{
    "is_valid": true/false,
    "violation_type": "none/identity/knowledge/style",
    "message": "违规的具体描述",
    "suggestion": "给AI的修正建议",
    "confidence": 0-1之间的置信度
}}
"""
        return prompt
    
    def _parse_validation_result(
        self,
        output: str,
        original_response: str
    ) -> ValidationResult:
        """解析LLM验证结果"""
        try:
            # 提取JSON
            json_match = re.search(r'\{[\s\S]*\}', output)
            if json_match:
                result = json.loads(json_match.group())
                
                is_valid = result.get("is_valid", True)
                violation_type_str = result.get("violation_type", "none")
                
                # 映射违反类型
                type_mapping = {
                    "none": ViolationType.NONE,
                    "identity": ViolationType.IDENTITY,
                    "knowledge": ViolationType.SEMANTIC,
                    "style": ViolationType.SEMANTIC,
                    "safety": ViolationType.SAFETY
                }
                
                return ValidationResult(
                    is_valid=is_valid,
                    violation_type=type_mapping.get(violation_type_str, ViolationType.SEMANTIC),
                    message=result.get("message", ""),
                    suggestion=result.get("suggestion", ""),
                    confidence=result.get("confidence", 0.8),
                    layer="semantic"
                )
        except Exception as e:
            print(f"[SemanticValidator] Parse error: {e}, output: {output[:200]}")
        
        # 解析失败，默认通过
        return ValidationResult(
            is_valid=True,
            violation_type=ViolationType.NONE,
            message="解析验证结果失败，默认通过",
            suggestion="",
            confidence=0.5,
            layer="semantic"
        )


class ConsistencyValidator:
    """
    历史一致性验证层
    
    检查当前回复是否与历史对话中的事实矛盾
    """
    
    def __init__(self, character_config: dict):
        self.config = character_config.get("consistency_rules", {})
        self.threshold = self.config.get("max_contradiction_score", 0.3)
    
    def validate(
        self,
        response: str,
        history: List[Dict],
        api_config: Optional[Dict] = None
    ) -> ValidationResult:
        """
        执行一致性验证
        
        Args:
            response: 当前回复
            history: 历史对话列表
            api_config: 可选，用于LLM-based一致性检查
        
        Returns:
            ValidationResult
        """
        if not history or len(history) < 2:
            return ValidationResult(
                is_valid=True,
                violation_type=ViolationType.NONE,
                message="历史记录不足，跳过一致性检查",
                suggestion="",
                confidence=1.0,
                layer="consistency"
            )
        
        # V1: 简单的文本相似度检查
        # V2: 可以扩展为LLM-based事实抽取和对比
        
        # 获取历史回复
        previous_responses = [
            msg.get("content", "") 
            for msg in history[-5:]  # 只检查最近5轮
            if msg.get("role") == "assistant"
        ]
        
        if not previous_responses:
            return ValidationResult(
                is_valid=True,
                violation_type=ViolationType.NONE,
                message="无历史AI回复",
                suggestion="",
                confidence=1.0,
                layer="consistency"
            )
        
        # 检查与历史回复的相似度（检测风格突变）
        similarity_scores = [
            SequenceMatcher(None, response, prev).ratio()
            for prev in previous_responses
        ]
        avg_similarity = sum(similarity_scores) / len(similarity_scores)
        
        # 风格突变检测（相似度过低可能表示角色切换）
        if avg_similarity < 0.1 and len(response) > 50:
            return ValidationResult(
                is_valid=False,
                violation_type=ViolationType.CONSISTENCY,
                message=f"检测到风格突变（相似度{avg_similarity:.2f}），可能存在角色不一致",
                suggestion="保持与之前对话一致的语气和风格",
                confidence=0.6,
                layer="consistency"
            )
        
        return ValidationResult(
            is_valid=True,
            violation_type=ViolationType.NONE,
            message=f"通过一致性检查（相似度{avg_similarity:.2f}）",
            suggestion="",
            confidence=0.8,
            layer="consistency"
        )


class RoleValidator:
    """
    角色规则验证主框架
    
    整合三层验证，支持独立开关
    """
    
    def __init__(self, character_name: str = "default"):
        self.character_config = CharacterConfigLoader.load(character_name)
        self.character_name = character_name
        
        # 初始化各验证层
        self.regex_validator = RegexValidator(self.character_config)
        self.semantic_validator = SemanticValidator(self.character_config)
        self.consistency_validator = ConsistencyValidator(self.character_config)
    
    def validate(
        self,
        response: str,
        enabled_layers: List[str],
        api_config: Optional[Dict] = None,
        history: Optional[List[Dict]] = None,
        context: str = ""
    ) -> ValidationResult:
        """
        执行启用的验证层
        
        Args:
            response: AI回复
            enabled_layers: 启用的验证层 ["regex", "semantic", "consistency"]
            api_config: LLM API配置（语义验证需要）
            history: 历史对话（一致性验证需要）
            context: 上下文信息
        
        Returns:
            ValidationResult
        """
        enabled = enabled_layers or ["regex"]
        
        # L1: 正则验证（快速，先做）
        if "regex" in enabled:
            result = self.regex_validator.validate(response)
            if not result.is_valid:
                return result
        
        # L2: LLM语义验证（需要API调用）
        if "semantic" in enabled and api_config:
            result = self.semantic_validator.validate(response, api_config, context)
            if not result.is_valid:
                return result
        
        # L3: 历史一致性验证
        if "consistency" in enabled and history:
            result = self.consistency_validator.validate(response, history, api_config)
            if not result.is_valid:
                return result
        
        # 全部通过
        return ValidationResult(
            is_valid=True,
            violation_type=ViolationType.NONE,
            message="通过所有启用的验证层",
            suggestion="",
            confidence=1.0,
            layer="all"
        )
    
    def get_character_info(self) -> dict:
        """获取当前角色信息"""
        character = self.character_config.get("character", {})
        return {
            "name": character.get("name", "默认助手"),
            "description": character.get("description", ""),
            "version": character.get("version", "1.0")
        }

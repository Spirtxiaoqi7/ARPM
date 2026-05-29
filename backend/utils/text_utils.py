"""
Text processing helpers.
"""

import re
from typing import List, Optional, Tuple


class TextProcessor:
    """Basic text utilities."""

    @staticmethod
    def clean_text(text: str) -> str:
        """Collapse whitespace and remove control characters."""
        text = re.sub(r"\s+", " ", text)
        text = re.sub(r"[\x00-\x08\x0b-\x0c\x0e-\x1f]", "", text)
        return text.strip()

    @staticmethod
    def split_sentences(text: str) -> List[str]:
        """Split text by common Chinese punctuation."""
        sentences = re.split(r"(?<=[。！？；\n])\s*", text)
        return [s.strip() for s in sentences if s.strip()]

    @staticmethod
    def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
        """Truncate text to a max length."""
        if len(text) <= max_length:
            return text
        return text[: max_length - len(suffix)] + suffix


class ARPMParser:
    """Parse model output into state_update/analysis/response sections."""

    THINKING_MODEL_KEYWORDS = (
        "reason",
        "thinking",
        "r1",
        "qwq",
        "qwq-",
        "o1",
        "o3",
        "o4",
        "deepseek-reasoner",
    )

    @staticmethod
    def detect_reasoning_model(model_name: str) -> bool:
        name = (model_name or "").lower()
        return any(keyword in name for keyword in ARPMParser.THINKING_MODEL_KEYWORDS)

    @staticmethod
    def parse_analysis_response(text: str) -> Tuple[str, str, float]:
        """
        Return: (analysis, response, confidence)
        """
        state_update, analysis, response, confidence = ARPMParser.parse_state_analysis_response(text)
        return analysis, response, confidence

    @staticmethod
    def parse_state_analysis_response(text: str) -> Tuple[str, str, str, float]:
        """
        Return: (state_update, analysis, response, confidence)
        """
        text = (text or "").strip()

        state_match = re.search(r"<state_update>(.*?)</state_update>", text, re.DOTALL | re.IGNORECASE)
        state_update = state_match.group(1).strip() if state_match else ""

        analysis_match = re.search(r"<analysis>(.*?)</analysis>", text, re.DOTALL | re.IGNORECASE)
        analysis = analysis_match.group(1).strip() if analysis_match else ""

        response_match = re.search(r"<response>(.*?)</response>", text, re.DOTALL | re.IGNORECASE)
        response = response_match.group(1).strip() if response_match else ""

        # Fallback: if there is analysis but no response tag, use the tail after analysis.
        if not response and analysis_match:
            tail = text[analysis_match.end() :].strip()
            tail = re.sub(r"^[:：\-\s]+", "", tail)
            if tail:
                response = tail

        # Fallback: plain text without tags is treated as the response.
        if not response and not analysis_match:
            response = text

        # Remove hidden protocol blocks that leaked into the visible response.
        response = re.sub(r"<state_update>.*?</state_update>", "", response, flags=re.DOTALL | re.IGNORECASE).strip()
        response = re.sub(r"<analysis>.*?</analysis>", "", response, flags=re.DOTALL | re.IGNORECASE).strip()
        response = re.sub(r"</?response>", "", response, flags=re.IGNORECASE).strip()
        analysis = re.sub(r"</?analysis>", "", analysis, flags=re.IGNORECASE).strip()
        state_update = re.sub(r"</?state_update>", "", state_update, flags=re.IGNORECASE).strip()
        analysis = analysis.strip()

        confidence_match = re.search(r"置信度[:：]?\s*(\d+\.?\d*)", analysis, re.IGNORECASE)
        confidence = float(confidence_match.group(1)) if confidence_match else 0.8

        if not confidence_match:
            vague_keywords = ["不清晰", "不明确", "模糊", "歧义", "难以理解"]
            if any(kw in analysis for kw in vague_keywords):
                confidence = 0.4

        return state_update, analysis, response, confidence

    @staticmethod
    def extract_sub_queries(analysis: str) -> List[str]:
        """
        Extract decomposed sub-queries from analysis text.
        """
        pattern = r"(?:子问题|拆解|分解)[\d一二三四五]?[:：]?\s*([^\n；;]+)"
        matches = re.findall(pattern, analysis, re.IGNORECASE)

        if matches:
            return [q.strip() for q in matches if len(q.strip()) > 5]

        lines = analysis.split("\n")
        sub_queries = []
        for line in lines:
            line = line.strip()
            if re.match(r"^\d+[.．、\s]+", line):
                query = re.sub(r"^\d+[.．、\s]*", "", line)
                if len(query) > 5:
                    sub_queries.append(query)

        return sub_queries[:3]


class RuleValidator:
    """Simple role-consistency validator."""

    FORBIDDEN_PATTERNS = [
        r"我是[^，。！？\n]{0,10}的(父亲|母亲|创造者|作者)",
        r"我的背景故事是",
        r"实际上我不是",
        r"我的真实身份是",
    ]

    @classmethod
    def validate_response(cls, response: str) -> Tuple[bool, Optional[str]]:
        """
        Return: (is_valid, violation_reason)
        """
        for pattern in cls.FORBIDDEN_PATTERNS:
            if re.search(pattern, response, re.IGNORECASE):
                return False, f"Detected forbidden self-rewrite pattern: {pattern}"
        return True, None

"""
ARPM-v4 配置中心
"""
import os
import yaml
from typing import Dict, Any
from dataclasses import dataclass, asdict
from pathlib import Path

# 基础路径
BASE_DIR = Path(__file__).resolve().parent
APP_DIR = BASE_DIR.parent
WORKSPACE_DIR = APP_DIR.parent.parent
RUNTIME_DIR = Path(os.environ.get("ARPM_RUNTIME_DIR", str(WORKSPACE_DIR / "runtime" / "arpm-app")))
MODEL_ROOT_DIR = Path(os.environ.get("ARPM_MODEL_ROOT", str(WORKSPACE_DIR / "assets" / "models")))
DATA_DIR = RUNTIME_DIR / "data"
LOGS_DIR = RUNTIME_DIR / "logs"
CONFIG_DIR = APP_DIR / "config"

# 数据子目录
VECTOR_DB_PATH = DATA_DIR / "vector_db"
MEMORY_DB_PATH = DATA_DIR / "memory_db"
UPLOADS_PATH = DATA_DIR / "uploads"

# 模型路径
MODEL_PATH = MODEL_ROOT_DIR / "shibing624" / "text2vec-base-chinese"

# Flask配置
class FlaskConfig:
    SECRET_KEY = os.environ.get("SECRET_KEY", os.urandom(24))
    PORT = int(os.environ.get("PORT", 5000))
    DEBUG = os.environ.get("DEBUG", "True").lower() == "true"

# 检索配置
class RetrievalConfig:
    KNOWLEDGE_K = 5
    CHAT_HISTORY_K = 10
    RRF_K = 60.0
    DECAY_RATE_ROUND = 20.0
    DECAY_RATE_HOURS = 168.0
    SCENE_DECAY_FACTOR = 0.5
    
    # 相似度阈值配置（前端可调节）
    # 默认0.5，范围0-1，低于此值的召回结果会被过滤
    SIMILARITY_THRESHOLD: float = 0.5

# 分块配置
class ChunkConfig:
    CHILD_SIZE = 200
    PARENT_SIZE = 600
    OVERLAP_SENTENCES = 1

# LLM配置
class LLMConfig:
    DEFAULT_MODEL = "deepseek-chat"
    DEFAULT_BASE_URL = "https://api.deepseek.com"
    TIMEOUT = 120.0
    MAX_TOKENS = 2000
    TEMPERATURE = 0.7

# 模糊拆解配置
class DisambiguationConfig:
    MIN_CONFIDENCE = 0.6
    MAX_SUB_QUERIES = 3


# ==========================================
# 重生成控制配置 (Regeneration Control)
# ==========================================

@dataclass
class RegenerationConfig:
    """
    重生成控制配置
    
    支持三层验证的独立开关和参数配置
    """
    # 总开关
    ENABLED: bool = True
    
    # 最大重生成次数 (0-3)
    MAX_ATTEMPTS: int = 1
    
    # 各验证层开关
    REGEX_ENABLED: bool = True
    SEMANTIC_ENABLED: bool = False  # 默认关闭（需要额外LLM调用）
    CONSISTENCY_ENABLED: bool = False  # 默认关闭（需要历史数据）
    
    # 重生成策略
    STRATEGY: str = "append_warning"  # append_warning/few_shot/character_reinforce
    
    # 语义验证阈值
    SEMANTIC_THRESHOLD: float = 0.7
    
    # 一致性阈值
    CONSISTENCY_THRESHOLD: float = 0.3
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> "RegenerationConfig":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# ==========================================
# 消融实验开关配置 (Ablation Study)
# ==========================================

def get_ablation_config(
    rag_enabled: bool = True,
    kb_enabled: bool = True,
    chat_enabled: bool = True,
    temporal_enabled: bool = True,
    bm25_enabled: bool = True,
    disambiguation_enabled: bool = True,
    # 重生成相关
    regeneration_enabled: bool = True,
    regen_regex: bool = True,
    regen_semantic: bool = False,
    regen_consistency: bool = False,
    regen_max_attempts: int = 1
) -> dict:
    """
    获取消融实验配置
    
    优先级: 主开关 > 子开关
    """
    rag_active = rag_enabled
    
    return {
        # RAG主开关
        "rag_enabled": rag_enabled,
        
        # 双源召回（仅在rag_enabled=True时生效）
        "kb_enabled": kb_enabled and rag_active,
        "chat_enabled": chat_enabled and rag_active,
        
        # 时态权重（仅在rag_enabled=True时生效）
        "temporal_enabled": temporal_enabled and rag_active,
        
        # 算法开关
        "bm25_enabled": bm25_enabled and rag_active,
        "disambiguation_enabled": disambiguation_enabled,
        
        # 重生成控制
        "regeneration": {
            "enabled": regeneration_enabled,
            "max_attempts": regen_max_attempts,
            "regex_enabled": regen_regex and regeneration_enabled,
            "semantic_enabled": regen_semantic and regeneration_enabled,
            "consistency_enabled": regen_consistency and regeneration_enabled
        }
    }


# 默认消融配置（全开）
DEFAULT_ABLATION_CONFIG = get_ablation_config()


DEFAULT_TUNING_CONFIG = {
    "knowledge_k": RetrievalConfig.KNOWLEDGE_K,
    "chat_history_k": RetrievalConfig.CHAT_HISTORY_K,
    "similarity_threshold": RetrievalConfig.SIMILARITY_THRESHOLD,
    "decay_rate_round": RetrievalConfig.DECAY_RATE_ROUND,
    "decay_rate_hours": RetrievalConfig.DECAY_RATE_HOURS,
    "rrf_k": RetrievalConfig.RRF_K,
    "role_query_prefix_enabled": True,
    "kb_user_name_boost": 0.08,
    "kb_character_name_boost": 0.08,
    "kb_source_name_boost": 0.05,
    "chat_same_session_boost": 0.15,
    "chat_exact_name_boost": 0.10,
    "chat_text_name_boost": 0.04,
    "temperature": LLMConfig.TEMPERATURE,
    "max_tokens": LLMConfig.MAX_TOKENS,
}


def sanitize_tuning_config(raw: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Merge user overrides into the tuning config and clamp unsafe values."""
    config = dict(DEFAULT_TUNING_CONFIG)
    raw = raw or {}
    config.update({k: v for k, v in raw.items() if k in config})

    config["knowledge_k"] = max(1, min(20, int(config["knowledge_k"])))
    config["chat_history_k"] = max(1, min(30, int(config["chat_history_k"])))
    config["similarity_threshold"] = max(0.0, min(1.0, float(config["similarity_threshold"])))
    config["decay_rate_round"] = max(1.0, min(500.0, float(config["decay_rate_round"])))
    config["decay_rate_hours"] = max(1.0, min(24 * 365.0, float(config["decay_rate_hours"])))
    config["rrf_k"] = max(1.0, min(200.0, float(config["rrf_k"])))
    config["role_query_prefix_enabled"] = bool(config["role_query_prefix_enabled"])

    for key in (
        "kb_user_name_boost",
        "kb_character_name_boost",
        "kb_source_name_boost",
        "chat_same_session_boost",
        "chat_exact_name_boost",
        "chat_text_name_boost",
    ):
        config[key] = max(0.0, min(1.0, float(config[key])))

    config["temperature"] = max(0.0, min(2.0, float(config["temperature"])))
    config["max_tokens"] = max(64, min(8192, int(config["max_tokens"])))
    return config


# ==========================================
# 角色规则配置加载
# ==========================================

class CharacterConfigLoader:
    """角色规则配置加载器"""
    
    DEFAULT_CONFIG = {
        "character": {
            "name": "默认助手",
            "description": "一个有帮助的AI助手",
            "identity_constraints": {
                "forbidden_patterns": [
                    r"我是.*的父亲",
                    r"我是.*的母亲",
                    r"我是.*的创造者",
                    r"我的背景故事是",
                    r"实际上我不是",
                    r"我的真实身份是"
                ],
                "required_pronouns": ["我", "本人", "助手"],
                "forbidden_topics": []
            },
            "knowledge_boundary": {
                "knows": [],
                "doesnt_know": [],
                "default_response": "这个问题我不太清楚，但我可以帮你查资料。"
            },
            "personality_traits": ["有帮助的", "友好的"],
            "speech_patterns": {
                "sentence_length": "medium",
                "emoji_usage": "occasional",
                "formality": "neutral"
            },
            "consistency_rules": {
                "check_previous_facts": True,
                "max_contradiction_score": 0.3
            },
            "safety_rules": {
                "forbidden_topics": ["暴力", "色情"],
                "response_for_violation": "这个问题不太合适呢..."
            }
        }
    }
    
    @classmethod
    def load(cls, character_name: str = "default") -> dict:
        """加载角色配置"""
        config_path = CONFIG_DIR / f"character_{character_name}.yaml"
        
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        
        return cls.DEFAULT_CONFIG
    
    @classmethod
    def save(cls, config: dict, character_name: str):
        """保存角色配置"""
        os.makedirs(CONFIG_DIR, exist_ok=True)
        config_path = CONFIG_DIR / f"character_{character_name}.yaml"
        
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, allow_unicode=True, default_flow_style=False)


# 创建目录
def ensure_directories():
    """确保所有数据目录存在"""
    dirs = [
        DATA_DIR, VECTOR_DB_PATH, MEMORY_DB_PATH, UPLOADS_PATH, LOGS_DIR, CONFIG_DIR,
        VECTOR_DB_PATH / "knowledge",
        VECTOR_DB_PATH / "chat"
    ]
    for d in dirs:
        os.makedirs(d, exist_ok=True)

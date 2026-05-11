"""
pytest 配置和 fixtures
"""
import pytest
import sys
from pathlib import Path

# 添加 backend 到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))


@pytest.fixture
def sample_character_config():
    """示例角色配置"""
    return {
        "character": {
            "name": "测试角色",
            "description": "用于测试的角色",
            "identity_constraints": {
                "forbidden_patterns": ["我是.*的神"],
                "required_pronouns": ["我"]
            },
            "knowledge_boundary": {
                "knows": ["Python"],
                "doesnt_know": ["Java"],
                "default_response": "不知道"
            },
            "personality_traits": ["友好"],
            "consistency_rules": {
                "check_previous_facts": True,
                "max_contradiction_score": 0.3
            }
        }
    }


@pytest.fixture
def sample_api_config():
    """示例API配置"""
    return {
        "api_key": "test-key",
        "base_url": "https://test.example.com",
        "model": "test-model"
    }


@pytest.fixture
def sample_rag_context():
    """示例RAG上下文"""
    return {
        "knowledge": [
            {
                "chunk_id": "k1",
                "text": "Python是一种编程语言",
                "timestamp": {"round_num": 1, "physical_time": "2024-01-01T00:00:00"},
                "score": 0.9
            }
        ],
        "chat_history": [
            {
                "chunk_id": "c1",
                "text": "你好",
                "role": "user",
                "timestamp": {"round_num": 1, "physical_time": "2024-01-01T00:00:00"},
                "score": 0.8
            }
        ]
    }


@pytest.fixture
def sample_history():
    """示例对话历史"""
    return [
        {"role": "user", "content": "你好", "timestamp": "2024-01-01T00:00:00"},
        {"role": "assistant", "content": "你好！我是AI助手。", "timestamp": "2024-01-01T00:00:01"},
        {"role": "user", "content": "你会什么？", "timestamp": "2024-01-01T00:00:02"},
    ]

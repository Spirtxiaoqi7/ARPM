"""
配置系统单元测试
"""
import pytest
from config import (
    get_ablation_config,
    RegenerationConfig,
    CharacterConfigLoader
)


class TestAblationConfig:
    """测试消融实验配置"""
    
    def test_default_config(self):
        """测试默认配置"""
        config = get_ablation_config()
        
        assert config["rag_enabled"] is True
        assert config["kb_enabled"] is True
        assert config["chat_enabled"] is True
        assert config["temporal_enabled"] is True
        assert config["bm25_enabled"] is True
    
    def test_rag_disabled(self):
        """测试RAG关闭时子开关自动关闭"""
        config = get_ablation_config(rag_enabled=False)
        
        assert config["rag_enabled"] is False
        assert config["kb_enabled"] is False  # 自动关闭
        assert config["chat_enabled"] is False  # 自动关闭
        assert config["temporal_enabled"] is False  # 自动关闭
        assert config["bm25_enabled"] is False  # 自动关闭
        
        # 但模糊拆解保持原样（非RAG依赖）
        assert "disambiguation" in config
    
    def test_kb_only_disabled(self):
        """测试仅关闭知识库"""
        config = get_ablation_config(kb_enabled=False)
        
        assert config["rag_enabled"] is True
        assert config["kb_enabled"] is False
        assert config["chat_enabled"] is True  # 保持开启
    
    def test_regeneration_config(self):
        """测试重生成配置"""
        config = get_ablation_config(
            regeneration_enabled=True,
            regen_max_attempts=2,
            regen_regex=True,
            regen_semantic=True
        )
        
        regen = config["regeneration"]
        assert regen["enabled"] is True
        assert regen["max_attempts"] == 2
        assert regen["regex_enabled"] is True
        assert regen["semantic_enabled"] is True


class TestRegenerationConfig:
    """测试重生成配置类"""
    
    def test_default_values(self):
        """测试默认值"""
        config = RegenerationConfig()
        
        assert config.ENABLED is True
        assert config.MAX_ATTEMPTS == 1
        assert config.REGEX_ENABLED is True
        assert config.SEMANTIC_ENABLED is False
        assert config.CONSISTENCY_ENABLED is False
    
    def test_to_dict(self):
        """测试转换为字典"""
        config = RegenerationConfig()
        d = config.to_dict()
        
        assert isinstance(d, dict)
        assert d["ENABLED"] is True
    
    def test_from_dict(self):
        """测试从字典创建"""
        data = {"ENABLED": False, "MAX_ATTEMPTS": 3}
        config = RegenerationConfig.from_dict(data)
        
        assert config.ENABLED is False
        assert config.MAX_ATTEMPTS == 3


class TestCharacterConfigLoader:
    """测试角色配置加载器"""
    
    def test_default_character(self):
        """测试加载默认角色"""
        config = CharacterConfigLoader.load("default")
        
        assert "character" in config
        assert "name" in config["character"]
        assert "identity_constraints" in config["character"]
    
    def test_nonexistent_character(self):
        """测试加载不存在的角色返回默认"""
        config = CharacterConfigLoader.load("nonexistent_xyz")
        
        # 应该返回默认配置
        assert "character" in config
    
    def test_character_structure(self):
        """测试角色配置结构"""
        config = CharacterConfigLoader.load()
        char = config["character"]
        
        # 检查必需字段
        assert "name" in char
        assert "identity_constraints" in char
        assert "knowledge_boundary" in char
        assert "personality_traits" in char
        assert "speech_patterns" in char
        assert "consistency_rules" in char
        assert "safety_rules" in char
        assert "validation" in char


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

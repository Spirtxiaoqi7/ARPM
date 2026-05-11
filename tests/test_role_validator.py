"""
角色验证框架单元测试
"""
import pytest
from core.role_validator import (
    RegexValidator, 
    SemanticValidator, 
    ConsistencyValidator,
    RoleValidator,
    ViolationType
)


class TestRegexValidator:
    """测试正则验证层"""
    
    def test_valid_response(self, sample_character_config):
        """测试正常回复通过验证"""
        validator = RegexValidator(sample_character_config)
        result = validator.validate("你好，我是AI助手。")
        
        assert result.is_valid is True
        assert result.violation_type == ViolationType.NONE
    
    def test_forbidden_pattern(self, sample_character_config):
        """测试检测禁止模式"""
        validator = RegexValidator(sample_character_config)
        result = validator.validate("我是这个世界的神。")
        
        assert result.is_valid is False
        assert result.violation_type == ViolationType.REGEX
        assert "神" in result.message
    
    def test_safety_violation(self):
        """测试安全违规检测"""
        config = {
            "identity_constraints": {
                "forbidden_patterns": [],
                "safety_rules": {
                    "forbidden_topics": ["暴力"]
                }
            }
        }
        validator = RegexValidator(config)
        result = validator.validate("我喜欢暴力。")
        
        assert result.is_valid is False
        assert result.violation_type == ViolationType.SAFETY


class TestConsistencyValidator:
    """测试一致性验证层"""
    
    def test_no_history(self):
        """测试无历史记录时跳过"""
        config = {"consistency_rules": {"max_contradiction_score": 0.3}}
        validator = ConsistencyValidator(config)
        result = validator.validate("你好", [])
        
        assert result.is_valid is True
        assert "历史记录不足" in result.message
    
    def test_style_consistency(self):
        """测试风格一致性检查"""
        config = {"consistency_rules": {"max_contradiction_score": 0.3}}
        validator = ConsistencyValidator(config)
        
        history = [
            {"role": "assistant", "content": "你好，很高兴见到你。今天过得怎么样？"},
            {"role": "assistant", "content": "我觉得这个观点很有道理。"}
        ]
        
        # 风格相似的回复应该通过
        result = validator.validate("我也有同样的感觉。", history)
        assert result.is_valid is True


class TestRoleValidatorIntegration:
    """测试验证框架集成"""
    
    def test_all_layers_pass(self, sample_character_config, sample_api_config, sample_history):
        """测试所有验证层通过"""
        validator = RoleValidator()
        result = validator.validate(
            response="你好，我是AI助手。",
            enabled_layers=["regex"],
            api_config=sample_api_config,
            history=sample_history
        )
        
        assert result.is_valid is True
    
    def test_layer_selection(self, sample_api_config):
        """测试验证层选择"""
        validator = RoleValidator()
        
        # 只启用正则层
        result = validator.validate(
            response="我是神。",
            enabled_layers=["regex"]
        )
        assert result.is_valid is False
        assert result.layer == "regex"
    
    def test_character_info(self):
        """测试获取角色信息"""
        validator = RoleValidator()
        info = validator.get_character_info()
        
        assert "name" in info
        assert "description" in info


class TestEdgeCases:
    """测试边界情况"""
    
    def test_empty_response(self):
        """测试空回复"""
        validator = RegexValidator({"identity_constraints": {}})
        result = validator.validate("")
        
        assert result.is_valid is True
    
    def test_very_long_response(self):
        """测试超长回复"""
        long_text = "A" * 10000
        validator = RegexValidator({"identity_constraints": {}})
        result = validator.validate(long_text)
        
        assert result.is_valid is True
    
    def test_special_characters(self):
        """测试特殊字符"""
        validator = RegexValidator({"identity_constraints": {}})
        result = validator.validate("<>&\"'\\n\\t")
        
        assert result.is_valid is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

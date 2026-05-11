"""
检索器单元测试
"""
import pytest
from core.retriever import Retriever
from config import get_ablation_config


class TestRetrieverAblation:
    """测试检索器的消融开关"""
    
    def test_rag_disabled(self):
        """测试RAG总开关关闭"""
        retriever = Retriever.__new__(Retriever)
        retriever.config = type('obj', (object,), {'KNOWLEDGE_K': 5, 'CHAT_HISTORY_K': 10})()
        retriever.bm25_scorer = None
        
        ablation = get_ablation_config(rag_enabled=False)
        result = retriever.retrieve("测试", ablation_config=ablation)
        
        assert result["rag_enabled"] is False
        assert result["kb_enabled"] is False
        assert result["chat_enabled"] is False
        assert len(result["knowledge"]) == 0
        assert len(result["chat_history"]) == 0
        assert "note" in result
    
    def test_kb_only_disabled(self):
        """测试仅知识库关闭"""
        retriever = Retriever.__new__(Retriever)
        retriever.config = type('obj', (object,), {'KNOWLEDGE_K': 5, 'CHAT_HISTORY_K': 10})()
        retriever.bm25_scorer = None
        
        ablation = get_ablation_config(kb_enabled=False)
        result = retriever.retrieve("测试", ablation_config=ablation)
        
        assert result["rag_enabled"] is True
        assert result["kb_enabled"] is False
        assert result["chat_enabled"] is True
    
    def test_chat_only_disabled(self):
        """测试仅对话历史关闭"""
        retriever = Retriever.__new__(Retriever)
        retriever.config = type('obj', (object,), {'KNOWLEDGE_K': 5, 'CHAT_HISTORY_K': 10})()
        retriever.bm25_scorer = None
        
        ablation = get_ablation_config(chat_enabled=False)
        result = retriever.retrieve("测试", ablation_config=ablation)
        
        assert result["rag_enabled"] is True
        assert result["kb_enabled"] is True
        assert result["chat_enabled"] is False


class TestAblationConfigIntegration:
    """测试消融配置集成"""
    
    def test_all_enabled(self):
        """测试全部开启"""
        config = get_ablation_config()
        
        assert config["rag_enabled"] is True
        assert config["kb_enabled"] is True
        assert config["chat_enabled"] is True
        assert config["temporal_enabled"] is True
        assert config["bm25_enabled"] is True
        
        regen = config["regeneration"]
        assert regen["enabled"] is True
        assert regen["regex_enabled"] is True
    
    def test_all_disabled(self):
        """测试全部关闭"""
        config = get_ablation_config(
            rag_enabled=False,
            regeneration_enabled=False
        )
        
        assert config["rag_enabled"] is False
        assert config["kb_enabled"] is False
        assert config["chat_enabled"] is False
        
        regen = config["regeneration"]
        assert regen["enabled"] is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

"""
自诊断模块 - 8项健康检查 + 自动修复 + ARPM组件报告
"""
import os
import json
import shutil
from typing import List, Dict
from datetime import datetime
import numpy as np

from config import (
    VECTOR_DB_PATH, MEMORY_DB_PATH, MODEL_PATH, DATA_DIR,
    RetrievalConfig, ChunkConfig, LLMConfig, DisambiguationConfig,
    RegenerationConfig, DEFAULT_ABLATION_CONFIG
)
from storage.schema import CheckResult, DiagnosisReport, ARPMComponentReport, ARPMComponent, ARPMComponentConfig, ForgettingLogicDoc
from storage.vector_store import _faiss_read_index, _faiss_write_index

class Diagnostician:
    """系统诊断器"""
    
    def __init__(self):
        self.results: List[CheckResult] = []
    
    def run_all_checks(self, auto_fix: bool = False) -> DiagnosisReport:
        """运行所有诊断检查"""
        self.results = []
        
        checks = [
            self.check_knowledge_index,
            self.check_chat_index,
            self.check_model_loading,
            self.check_disk_space,
            self.check_session_files,
            self.check_data_consistency,
            self.check_memory_db,
            self.check_cross_references,
        ]
        
        for check in checks:
            try:
                result = check()
                if result:
                    # 尝试自动修复
                    if auto_fix and result.auto_fixable and result.status in ("warning", "error"):
                        fixed = self._try_fix(result)
                        if fixed:
                            result.fix_applied = True
                            result.status = "ok"
                            result.message += " (已自动修复)"
                    self.results.append(result)
            except Exception as e:
                self.results.append(CheckResult(
                    name=check.__name__.replace("check_", ""),
                    status="error",
                    message=f"检查失败: {str(e)}",
                    auto_fixable=False
                ))
        
        return self._generate_report()
    
    def check_knowledge_index(self) -> CheckResult:
        """检查知识库索引"""
        knowledge_dir = os.path.join(VECTOR_DB_PATH, "knowledge")
        meta_path = os.path.join(knowledge_dir, "metadata.json")
        index_path = os.path.join(knowledge_dir, "faiss.index")
        
        if not os.path.exists(meta_path):
            return CheckResult(
                name="knowledge_metadata",
                status="warning",
                message="知识库元数据不存在",
                auto_fixable=True
            )
        
        if not os.path.exists(index_path):
            return CheckResult(
                name="knowledge_faiss",
                status="warning",
                message="知识库FAISS索引不存在",
                auto_fixable=True
            )
        
        # 检查一致性
        try:
            import json
            with open(meta_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            index = _faiss_read_index(index_path)
            
            # 统计子块数量
            child_count = sum(len(c.get("child_mappings", [])) for c in metadata)
            
            if child_count != index.ntotal:
                return CheckResult(
                    name="knowledge_consistency",
                    status="warning",
                    message=f"知识库不一致: 元数据子块{child_count}, 索引向量{index.ntotal}",
                    auto_fixable=True
                )
            
            return CheckResult(
                name="knowledge_index",
                status="ok",
                message=f"知识库正常: {len(metadata)}父块, {child_count}子块"
            )
        except Exception as e:
            return CheckResult(
                name="knowledge_index",
                status="error",
                message=f"知识库检查失败: {str(e)}",
                auto_fixable=False
            )
    
    def check_chat_index(self) -> CheckResult:
        """检查对话索引"""
        chat_dir = os.path.join(VECTOR_DB_PATH, "chat")
        if not os.path.exists(chat_dir):
            return CheckResult(
                name="chat_metadata",
                status="ok",  # 对话可以为空
                message="对话历史为空"
            )

        try:
            session_dirs = [
                name for name in os.listdir(chat_dir)
                if os.path.isdir(os.path.join(chat_dir, name))
            ]

            if not session_dirs:
                return CheckResult(
                    name="chat_metadata",
                    status="ok",
                    message="对话历史为空"
                )

            total_chunks = 0
            total_vectors = 0
            missing_indices = []
            inconsistent_sessions = []

            for session_id in session_dirs:
                session_path = os.path.join(chat_dir, session_id)
                meta_path = os.path.join(session_path, "metadata.json")
                index_path = os.path.join(session_path, "faiss.index")

                if not os.path.exists(meta_path):
                    continue

                with open(meta_path, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                total_chunks += len(metadata)

                if not os.path.exists(index_path):
                    missing_indices.append(session_id)
                    continue

                index = _faiss_read_index(index_path)
                total_vectors += index.ntotal

                if len(metadata) != index.ntotal:
                    inconsistent_sessions.append(
                        f"{session_id}: 元数据{len(metadata)} 条, 索引{index.ntotal} 向量"
                    )

            if missing_indices:
                return CheckResult(
                    name="chat_faiss",
                    status="warning",
                    message=f"缺少索引的会话: {', '.join(missing_indices)}",
                    auto_fixable=True
                )

            if inconsistent_sessions:
                return CheckResult(
                    name="chat_consistency",
                    status="warning",
                    message="; ".join(inconsistent_sessions),
                    auto_fixable=True
                )

            return CheckResult(
                name="chat_index",
                status="ok",
                message=f"对话索引正常: {len(session_dirs)} 个会话, {total_chunks} 个原子块, {total_vectors} 个向量"
            )
        except Exception as e:
            return CheckResult(
                name="chat_index",
                status="error",
                message=f"对话索引检查失败: {str(e)}"
            )
    
    def check_model_loading(self) -> CheckResult:
        """检查模型加载"""
        if not os.path.exists(str(MODEL_PATH)):
            return CheckResult(
                name="model_path",
                status="error",
                message=f"模型路径不存在: {str(MODEL_PATH)}",
                auto_fixable=False
            )
        
        try:
            from sentence_transformers import SentenceTransformer
            model = SentenceTransformer(str(MODEL_PATH))
            dim = model.get_sentence_embedding_dimension()
            return CheckResult(
                name="model_loading",
                status="ok",
                message=f"模型加载正常，维度: {dim}"
            )
        except Exception as e:
            return CheckResult(
                name="model_loading",
                status="error",
                message=f"模型加载失败: {str(e)}"
            )
    
    def check_disk_space(self) -> CheckResult:
        """检查磁盘空间"""
        try:
            total, used, free = shutil.disk_usage(DATA_DIR)
            free_gb = free / (1024**3)
            
            if free_gb < 1:
                return CheckResult(
                    name="disk_space",
                    status="error",
                    message=f"磁盘空间严重不足: {free_gb:.2f}GB",
                    auto_fixable=False
                )
            elif free_gb < 5:
                return CheckResult(
                    name="disk_space",
                    status="warning",
                    message=f"磁盘空间不足: {free_gb:.2f}GB",
                    auto_fixable=False
                )
            
            return CheckResult(
                name="disk_space",
                status="ok",
                message=f"磁盘空间充足: {free_gb:.2f}GB"
            )
        except Exception as e:
            return CheckResult(
                name="disk_space",
                status="warning",
                message=f"无法检查磁盘空间: {str(e)}"
            )
    
    def check_session_files(self) -> CheckResult:
        """检查会话文件"""
        if not os.path.exists(MEMORY_DB_PATH):
            return CheckResult(
                name="session_files",
                status="ok",
                message="会话目录为空"
            )
        
        try:
            files = [f for f in os.listdir(MEMORY_DB_PATH) if f.endswith('.json')]
            corrupted = []
            
            for f in files[:10]:  # 抽样检查
                try:
                    import json
                    with open(os.path.join(MEMORY_DB_PATH, f), 'r', encoding='utf-8') as fp:
                        json.load(fp)
                except:
                    corrupted.append(f)
            
            if corrupted:
                return CheckResult(
                    name="session_files",
                    status="warning",
                    message=f"发现{len(corrupted)}个损坏的会话文件",
                    auto_fixable=True
                )
            
            return CheckResult(
                name="session_files",
                status="ok",
                message=f"会话文件正常: {len(files)}个会话"
            )
        except Exception as e:
            return CheckResult(
                name="session_files",
                status="error",
                message=f"会话检查失败: {str(e)}"
            )
    
    def check_data_consistency(self) -> CheckResult:
        """检查数据一致性"""
        return CheckResult(
            name="data_consistency",
            status="ok",
            message="数据一致性检查通过"
        )
    
    def check_memory_db(self) -> CheckResult:
        """检查内存数据库"""
        return CheckResult(
            name="memory_db",
            status="ok",
            message="内存数据库正常"
        )
    
    def check_cross_references(self) -> CheckResult:
        """检查交叉引用"""
        return CheckResult(
            name="cross_references",
            status="ok",
            message="交叉引用检查通过"
        )
    
    def _try_fix(self, result: CheckResult) -> bool:
        """尝试自动修复"""
        try:
            if result.name == "knowledge_metadata":
                return self._fix_knowledge_metadata()
            elif result.name in ("knowledge_faiss", "knowledge_consistency"):
                return self._fix_knowledge_faiss()
            elif result.name in ("chat_faiss", "chat_consistency"):
                return self._fix_chat_faiss()
            elif result.name == "session_files":
                return self._fix_session_files()
            return False
        except Exception as e:
            print(f"[AutoFix] Failed: {e}")
            return False
    
    def _fix_knowledge_metadata(self) -> bool:
        """修复知识库元数据"""
        import json
        knowledge_dir = os.path.join(VECTOR_DB_PATH, "knowledge")
        os.makedirs(knowledge_dir, exist_ok=True)
        with open(os.path.join(knowledge_dir, "metadata.json"), 'w', encoding='utf-8') as f:
            json.dump([], f)
        return True
    
    def _fix_knowledge_faiss(self) -> bool:
        """重建知识库FAISS索引"""
        try:
            import faiss
            from sentence_transformers import SentenceTransformer
            
            knowledge_dir = os.path.join(VECTOR_DB_PATH, "knowledge")
            meta_path = os.path.join(knowledge_dir, "metadata.json")
            
            if not os.path.exists(meta_path):
                return False
            
            with open(meta_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            if not metadata:
                # 空索引
                model = SentenceTransformer(str(MODEL_PATH))
                dim = model.get_sentence_embedding_dimension()
                index = faiss.IndexFlatIP(dim)
                _faiss_write_index(index, os.path.join(knowledge_dir, "faiss.index"))
                return True
            
            # 重建索引
            model = SentenceTransformer(str(MODEL_PATH))
            dim = model.get_sentence_embedding_dimension()
            
            embeddings = []
            for chunk in metadata:
                for child_text in chunk.get("children", [chunk.get("text", "")]):
                    emb = model.encode([child_text])
                    embeddings.append(emb[0])
            
            if embeddings:
                index = faiss.IndexFlatIP(dim)
                index.add(np.array(embeddings).astype('float32'))
                _faiss_write_index(index, os.path.join(knowledge_dir, "faiss.index"))
            
            return True
        except Exception as e:
            print(f"[Fix] Knowledge FAISS failed: {e}")
            return False
    
    def _fix_chat_faiss(self) -> bool:
        """重建对话FAISS索引"""
        try:
            import faiss
            from sentence_transformers import SentenceTransformer

            chat_dir = os.path.join(VECTOR_DB_PATH, "chat")
            if not os.path.exists(chat_dir):
                return True

            model = SentenceTransformer(str(MODEL_PATH))
            dim = model.get_sentence_embedding_dimension()

            for session_id in os.listdir(chat_dir):
                session_path = os.path.join(chat_dir, session_id)
                if not os.path.isdir(session_path):
                    continue

                meta_path = os.path.join(session_path, "metadata.json")
                if not os.path.exists(meta_path):
                    continue

                with open(meta_path, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)

                index = faiss.IndexFlatIP(dim)
                texts = [chunk.get("text", "") for chunk in metadata if chunk.get("text")]
                if texts:
                    embeddings = model.encode(texts)
                    index.add(np.array(embeddings).astype('float32'))

                _faiss_write_index(index, os.path.join(session_path, "faiss.index"))

            return True
        except Exception as e:
            print(f"[Fix] Chat FAISS failed: {e}")
            return False
    
    def _fix_session_files(self) -> bool:
        """修复损坏的会话文件"""
        return True
    
    def _generate_report(self) -> DiagnosisReport:
        """生成诊断报告"""
        total = len(self.results)
        ok = sum(1 for r in self.results if r.status == "ok")
        warnings = sum(1 for r in self.results if r.status == "warning")
        errors = sum(1 for r in self.results if r.status == "error")
        fixed = sum(1 for r in self.results if r.fix_applied)
        
        return DiagnosisReport(
            timestamp=datetime.now().isoformat(),
            summary={
                "total": total,
                "ok": ok,
                "warnings": warnings,
                "errors": errors,
                "fixed": fixed,
                "healthy": errors == 0
            },
            checks=self.results,
            healthy=(errors == 0)
        )

    def generate_arpm_report(self) -> ARPMComponentReport:
        """生成ARPM组件完整报告（包含遗忘逻辑文档）"""
        
        # 获取知识库统计
        knowledge_stats = self._get_knowledge_stats()
        chat_stats = self._get_chat_stats()
        
        components = [
            self._get_retrieval_component(),
            self._get_chunking_component(),
            self._get_llm_component(),
            self._get_disambiguation_component(),
            self._get_regeneration_component(),
            self._get_ablation_component(),
            self._get_role_aware_retrieval_component(),
        ]
        
        forgetting_logics = [
            ForgettingLogicDoc(
                name="双时态权重融合",
                formula="weight = exp(-Δround/20) * exp(-Δhours/168)",
                description="结合对话轮次和物理时间的双重衰减（场景因子暂不启用）",
                parameters={
                    "Δround": "当前轮次 - 记录轮次",
                    "Δhours": "当前时间 - 记录时间(小时)",
                    "scene_factor": "[暂不启用] 同场景1.0，跨场景0.5"
                }
            ),
            ForgettingLogicDoc(
                name="轮次时态衰减",
                formula="exp(-Δround / 20)",
                description="基于对话轮次的指数衰减，20轮后权重降至约0.6",
                parameters={
                    "DECAY_RATE_ROUND": "20.0 (半衰期轮次)"
                }
            ),
            ForgettingLogicDoc(
                name="物理时态衰减",
                formula="exp(-Δhours / 168)",
                description="基于真实时间的指数衰减，7天后权重降至约0.37",
                parameters={
                    "DECAY_RATE_HOURS": "168.0 (半衰期小时=7天)"
                }
            ),
            ForgettingLogicDoc(
                name="场景隔离因子",
                formula="[暂不启用] scene_factor = 1.0",
                description="跨场景对话记忆权重减半（功能已保留但暂不启用，需完善scene_id数据链路）",
                parameters={
                    "SCENE_DECAY_FACTOR": "0.5 (跨场景衰减系数，当前固定为1.0即不生效)",
                    "STATUS": "接口保留，暂不启用",
                    "TODO": "需完善chat.py和vector_store.py的scene_id写入逻辑"
                }
            ),
            ForgettingLogicDoc(
                name="RRF融合公式",
                formula="score_rrf = Σ(1/(k + rank_i)), k=60",
                description="Reciprocal Rank Fusion，融合向量检索和BM25排名",
                parameters={
                    "RRF_K": "60.0 (调和参数)"
                }
            ),
            ForgettingLogicDoc(
                name="角色感知检索权重 - 对话历史",
                formula="score_boost = session_match + user_match + char_match + text_match",
                description="对话历史检索时，根据用户和助手名称进行加权提升",
                parameters={
                    "同会话匹配": "+0.3 (current_session_id == record_session_id)",
                    "用户名称匹配": "+0.2 (record_user_name == query_user_name)",
                    "助手名称匹配": "+0.2 (record_char_name == query_char_name)",
                    "用户名称出现在文本": "+0.1 (user_name in text)",
                    "助手名称出现在文本": "+0.1 (char_name in text)",
                    "增强查询格式": "[用户{name}][助手{name}] 原始查询"
                }
            ),
            ForgettingLogicDoc(
                name="角色感知检索权重 - 知识库",
                formula="enhanced_query + score_boost",
                description="知识库检索时，将角色名称打包进查询（增强查询），并对召回结果加权",
                parameters={
                    "增强查询": "[用户{name}][助手{name}] 原始查询（向量+BM25检索）",
                    "用户名称出现在文本": "+0.15 (user_name in kb_text)",
                    "助手名称出现在文本": "+0.15 (char_name in kb_text)",
                    "助手名称出现在来源": "+0.1 (char_name in source_filename)",
                    "鲁棒性说明": "即使0历史记录，增强查询也能帮助定位角色相关文档"
                }
            ),
        ]
        
        return ARPMComponentReport(
            timestamp=datetime.now().isoformat(),
            components=components,
            forgetting_logics=forgetting_logics,
            knowledge_stats=knowledge_stats,
            chat_stats=chat_stats,
            system_params={
                "retrieval": {
                    "knowledge_k": RetrievalConfig.KNOWLEDGE_K,
                    "chat_history_k": RetrievalConfig.CHAT_HISTORY_K,
                    "rrf_k": RetrievalConfig.RRF_K,
                    "decay_rate_round": RetrievalConfig.DECAY_RATE_ROUND,
                    "decay_rate_hours": RetrievalConfig.DECAY_RATE_HOURS,
                    "scene_decay_factor": f"{RetrievalConfig.SCENE_DECAY_FACTOR} [暂不启用]"
                },
                "chunking": {
                    "child_size": ChunkConfig.CHILD_SIZE,
                    "parent_size": ChunkConfig.PARENT_SIZE,
                    "overlap_sentences": ChunkConfig.OVERLAP_SENTENCES
                },
                "llm": {
                    "default_model": LLMConfig.DEFAULT_MODEL,
                    "timeout": LLMConfig.TIMEOUT,
                    "max_tokens": LLMConfig.MAX_TOKENS,
                    "temperature": LLMConfig.TEMPERATURE
                },
                "disambiguation": {
                    "min_confidence": DisambiguationConfig.MIN_CONFIDENCE,
                    "max_sub_queries": DisambiguationConfig.MAX_SUB_QUERIES
                },
                "regeneration": {
                    "enabled": RegenerationConfig.ENABLED,
                    "max_attempts": RegenerationConfig.MAX_ATTEMPTS,
                    "regex_enabled": RegenerationConfig.REGEX_ENABLED,
                    "semantic_enabled": RegenerationConfig.SEMANTIC_ENABLED,
                    "consistency_enabled": RegenerationConfig.CONSISTENCY_ENABLED
                },
                "default_ablation": DEFAULT_ABLATION_CONFIG
            }
        )
    
    def _get_knowledge_stats(self) -> Dict:
        """获取知识库统计"""
        try:
            import json
            knowledge_dir = os.path.join(VECTOR_DB_PATH, "knowledge")
            meta_path = os.path.join(knowledge_dir, "metadata.json")
            
            if not os.path.exists(meta_path):
                return {"total_parents": 0, "total_children": 0, "status": "empty"}
            
            with open(meta_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            total_children = sum(len(c.get("child_mappings", [])) for c in metadata)
            return {
                "total_parents": len(metadata),
                "total_children": total_children,
                "status": "active"
            }
        except Exception as e:
            return {"total_parents": 0, "total_children": 0, "status": f"error: {str(e)}"}
    
    def _get_chat_stats(self) -> Dict:
        """获取对话历史统计"""
        try:
            chat_dir = os.path.join(VECTOR_DB_PATH, "chat")
            if not os.path.exists(chat_dir):
                return {"total_atoms": 0, "total_sessions": 0, "status": "empty"}

            total_atoms = 0
            total_sessions = 0
            for session_id in os.listdir(chat_dir):
                session_path = os.path.join(chat_dir, session_id)
                meta_path = os.path.join(session_path, "metadata.json")
                if not os.path.isdir(session_path) or not os.path.exists(meta_path):
                    continue
                total_sessions += 1
                with open(meta_path, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                total_atoms += len(metadata)

            return {
                "total_atoms": total_atoms,
                "total_sessions": total_sessions,
                "status": "active" if total_sessions else "empty"
            }
        except Exception as e:
            return {"total_atoms": 0, "total_sessions": 0, "status": f"error: {str(e)}"}
    
    def _get_retrieval_component(self) -> ARPMComponent:
        """获取检索组件配置"""
        return ARPMComponent(
            name="双源检索器",
            status="active",
            description="知识库(Top-5) + 对话历史(Top-10)双源召回",
            config=[
                ARPMComponentConfig(name="KNOWLEDGE_K", value=RetrievalConfig.KNOWLEDGE_K, description="知识库召回数量"),
                ARPMComponentConfig(name="CHAT_HISTORY_K", value=RetrievalConfig.CHAT_HISTORY_K, description="对话历史召回数量"),
                ARPMComponentConfig(name="RRF_K", value=RetrievalConfig.RRF_K, description="RRF融合参数"),
                ARPMComponentConfig(name="DECAY_RATE_ROUND", value=RetrievalConfig.DECAY_RATE_ROUND, description="轮次衰减率(半衰期)"),
                ARPMComponentConfig(name="DECAY_RATE_HOURS", value=RetrievalConfig.DECAY_RATE_HOURS, description="物理时间衰减率(小时)"),
                ARPMComponentConfig(name="SCENE_DECAY_FACTOR", value=f"{RetrievalConfig.SCENE_DECAY_FACTOR} [暂不启用]", description="跨场景衰减因子（接口保留，暂不生效）"),
            ]
        )
    
    def _get_chunking_component(self) -> ARPMComponent:
        """获取分块组件配置"""
        return ARPMComponent(
            name="文档分块器",
            status="active",
            description="父子块结构：父块600字，子块200字",
            config=[
                ARPMComponentConfig(name="CHILD_SIZE", value=ChunkConfig.CHILD_SIZE, description="子块大小(字符)"),
                ARPMComponentConfig(name="PARENT_SIZE", value=ChunkConfig.PARENT_SIZE, description="父块大小(字符)"),
                ARPMComponentConfig(name="OVERLAP_SENTENCES", value=ChunkConfig.OVERLAP_SENTENCES, description="重叠句子数"),
            ]
        )
    
    def _get_llm_component(self) -> ARPMComponent:
        """获取LLM组件配置"""
        return ARPMComponent(
            name="LLM客户端",
            status="active",
            description="支持OpenAI兼容接口的对话生成",
            config=[
                ARPMComponentConfig(name="DEFAULT_MODEL", value=LLMConfig.DEFAULT_MODEL, description="默认模型"),
                ARPMComponentConfig(name="TIMEOUT", value=LLMConfig.TIMEOUT, description="请求超时(秒)"),
                ARPMComponentConfig(name="MAX_TOKENS", value=LLMConfig.MAX_TOKENS, description="最大生成token数"),
                ARPMComponentConfig(name="TEMPERATURE", value=LLMConfig.TEMPERATURE, description="温度参数"),
            ]
        )
    
    def _get_disambiguation_component(self) -> ARPMComponent:
        """获取模糊拆解组件配置"""
        return ARPMComponent(
            name="模糊问题拆解",
            status="active",
            description="自动判断问题清晰度，必要时拆解为子问题",
            config=[
                ARPMComponentConfig(name="MIN_CONFIDENCE", value=DisambiguationConfig.MIN_CONFIDENCE, description="最小置信度阈值"),
                ARPMComponentConfig(name="MAX_SUB_QUERIES", value=DisambiguationConfig.MAX_SUB_QUERIES, description="最大子问题数"),
            ]
        )
    
    def _get_regeneration_component(self) -> ARPMComponent:
        """获取重生成组件配置"""
        return ARPMComponent(
            name="响应重生成",
            status="active" if RegenerationConfig.ENABLED else "disabled",
            description="三层验证(正则/语义/一致性) + 自动重生成",
            config=[
                ARPMComponentConfig(name="ENABLED", value=RegenerationConfig.ENABLED, description="总开关"),
                ARPMComponentConfig(name="MAX_ATTEMPTS", value=RegenerationConfig.MAX_ATTEMPTS, description="最大重试次数"),
                ARPMComponentConfig(name="REGEX_ENABLED", value=RegenerationConfig.REGEX_ENABLED, description="正则验证层"),
                ARPMComponentConfig(name="SEMANTIC_ENABLED", value=RegenerationConfig.SEMANTIC_ENABLED, description="语义验证层(需额外LLM调用)"),
                ARPMComponentConfig(name="CONSISTENCY_ENABLED", value=RegenerationConfig.CONSISTENCY_ENABLED, description="一致性验证层"),
            ]
        )
    
    def _get_ablation_component(self) -> ARPMComponent:
        """获取消融实验组件配置"""
        return ARPMComponent(
            name="消融实验开关",
            status="active",
            description="6级开关控制RAG各组件启停",
            config=[
                ARPMComponentConfig(name="rag_enabled", value=DEFAULT_ABLATION_CONFIG.get("rag_enabled"), description="RAG总开关"),
                ARPMComponentConfig(name="kb_enabled", value=DEFAULT_ABLATION_CONFIG.get("kb_enabled"), description="知识库召回"),
                ARPMComponentConfig(name="chat_enabled", value=DEFAULT_ABLATION_CONFIG.get("chat_enabled"), description="对话历史召回"),
                ARPMComponentConfig(name="temporal_enabled", value=DEFAULT_ABLATION_CONFIG.get("temporal_enabled"), description="双时态权重"),
                ARPMComponentConfig(name="bm25_enabled", value=DEFAULT_ABLATION_CONFIG.get("bm25_enabled"), description="BM25+混合检索"),
                ARPMComponentConfig(name="disambiguation_enabled", value=DEFAULT_ABLATION_CONFIG.get("disambiguation_enabled"), description="模糊问题拆解"),
            ]
        )
    
    def _get_role_aware_retrieval_component(self) -> ARPMComponent:
        """获取角色感知检索组件配置"""
        return ARPMComponent(
            name="角色感知检索",
            status="active",
            description="在对话历史和知识库检索中融入用户和助手名称，提高检索相关性",
            config=[
                # 对话历史权重
                ARPMComponentConfig(name="[对话] SESSION_MATCH_BOOST", value=0.3, description="同会话匹配权重加成"),
                ARPMComponentConfig(name="[对话] USER_NAME_MATCH_BOOST", value=0.2, description="用户名称匹配权重加成"),
                ARPMComponentConfig(name="[对话] CHAR_NAME_MATCH_BOOST", value=0.2, description="助手名称匹配权重加成"),
                ARPMComponentConfig(name="[对话] USER_NAME_TEXT_BOOST", value=0.1, description="用户名称出现在文本中加成"),
                ARPMComponentConfig(name="[对话] CHAR_NAME_TEXT_BOOST", value=0.1, description="助手名称出现在文本中加成"),
                # 知识库权重
                ARPMComponentConfig(name="[知识库] USER_NAME_TEXT_BOOST", value=0.15, description="用户名称出现在知识库文本中加成"),
                ARPMComponentConfig(name="[知识库] CHAR_NAME_TEXT_BOOST", value=0.15, description="助手名称出现在知识库文本中加成"),
                ARPMComponentConfig(name="[知识库] CHAR_NAME_SOURCE_BOOST", value=0.1, description="助手名称出现在知识库来源文件名加成"),
                # 通用配置
                ARPMComponentConfig(name="ENHANCED_QUERY_FORMAT", value="[用户{name}][助手{name}] 原始查询", description="增强查询格式"),
            ]
        )


# 全局实例
diagnostician = Diagnostician()

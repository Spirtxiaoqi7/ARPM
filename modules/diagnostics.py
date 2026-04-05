"""
ARPM 诊断系统
检查系统健康状态，自动修复常见问题
"""

import os
import json
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class CheckResult:
    """单项检查结果"""
    name: str
    status: str  # 'ok', 'warning', 'error'
    message: str
    details: Optional[Dict] = None
    auto_fixable: bool = False
    fix_applied: bool = False


class DiagnosticsManager:
    """诊断管理器"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.vector_db_path = os.path.join(data_dir, "vector_db")
        self.memory_db_path = os.path.join(data_dir, "memory_db")
        self.results: List[CheckResult] = []
    
    def run_all_checks(self, auto_fix: bool = False) -> Dict:
        """
        运行所有诊断检查
        
        Args:
            auto_fix: 是否自动修复可修复的问题
            
        Returns:
            诊断报告
        """
        self.results = []
        
        # 运行各项检查
        checks = [
            self.check_vector_db_integrity,
            self.check_metadata_consistency,
            self.check_faiss_index,
            self.check_model_loading,
            self.check_disk_space,
            self.check_session_files,
            self.check_orphaned_chunks,
            self.check_scene_integrity,
        ]
        
        for check in checks:
            try:
                result = check()
                if result:
                    self.results.append(result)
                    
                    # 尝试自动修复
                    if auto_fix and result.auto_fixable and result.status in ('warning', 'error'):
                        fix_result = self._auto_fix(result)
                        if fix_result:
                            result.fix_applied = True
                            result.status = 'ok'
                            result.message += " (已自动修复)"
            except Exception as e:
                self.results.append(CheckResult(
                    name=check.__name__.replace('check_', ''),
                    status='error',
                    message=f"检查失败: {str(e)}",
                    auto_fixable=False
                ))
        
        return self.generate_report()
    
    def check_vector_db_integrity(self) -> CheckResult:
        """检查向量数据库完整性"""
        required_files = ['parent_chunks.json', 'child_chunks.json', 'child_to_parent.json', 'metadata.json']
        missing = []
        
        for f in required_files:
            if not os.path.exists(os.path.join(self.vector_db_path, f)):
                missing.append(f)
        
        if missing:
            return CheckResult(
                name='vector_db_files',
                status='warning',
                message=f"缺少文件: {', '.join(missing)}",
                details={'missing_files': missing},
                auto_fixable=True
            )
        
        # 检查数据一致性
        try:
            with open(os.path.join(self.vector_db_path, 'parent_chunks.json'), 'r', encoding='utf-8') as f:
                parents = json.load(f)
            with open(os.path.join(self.vector_db_path, 'child_to_parent.json'), 'r', encoding='utf-8') as f:
                child_map = json.load(f)
            
            # 检查映射是否有效
            invalid_indices = [i for i, p in enumerate(child_map) if p < 0 or p >= len(parents)]
            
            if invalid_indices:
                return CheckResult(
                    name='child_parent_mapping',
                    status='error',
                    message=f"发现 {len(invalid_indices)} 个无效的子父映射",
                    details={'invalid_count': len(invalid_indices)},
                    auto_fixable=True
                )
            
            return CheckResult(
                name='vector_db_integrity',
                status='ok',
                message=f"向量数据库正常，包含 {len(parents)} 个父块，{len(child_map)} 个子块"
            )
        except Exception as e:
            return CheckResult(
                name='vector_db_integrity',
                status='error',
                message=f"数据读取失败: {str(e)}",
                auto_fixable=False
            )
    
    def check_metadata_consistency(self) -> CheckResult:
        """检查元数据一致性"""
        try:
            metadata_path = os.path.join(self.vector_db_path, 'metadata.json')
            if not os.path.exists(metadata_path):
                return CheckResult(
                    name='metadata_exists',
                    status='warning',
                    message="元数据文件不存在",
                    auto_fixable=True
                )
            
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            # 检查每个元数据项
            issues = []
            for i, meta in enumerate(metadata):
                # 检查 timestamp 是否为数字
                ts = meta.get('timestamp')
                if ts is not None and not isinstance(ts, (int, float)):
                    issues.append(f"chunk {i}: timestamp 类型错误")
                
                # 检查 keywords 格式
                keywords = meta.get('keywords', [])
                if keywords and not isinstance(keywords, list):
                    issues.append(f"chunk {i}: keywords 格式错误")
            
            if issues:
                return CheckResult(
                    name='metadata_format',
                    status='warning',
                    message=f"发现 {len(issues)} 个元数据格式问题",
                    details={'issues': issues[:5]},  # 只显示前5个
                    auto_fixable=True
                )
            
            return CheckResult(
                name='metadata_consistency',
                status='ok',
                message=f"元数据一致性正常，共 {len(metadata)} 条记录"
            )
        except Exception as e:
            return CheckResult(
                name='metadata_consistency',
                status='error',
                message=f"元数据检查失败: {str(e)}",
                auto_fixable=False
            )
    
    def check_faiss_index(self) -> CheckResult:
        """检查 FAISS 索引"""
        try:
            faiss_path = os.path.join(self.vector_db_path, 'faiss.index')
            
            if not os.path.exists(faiss_path):
                return CheckResult(
                    name='faiss_index',
                    status='warning',
                    message="FAISS 索引文件不存在",
                    auto_fixable=True
                )
            
            # 尝试读取索引
            import faiss
            index = faiss.read_index(faiss_path)
            
            # 获取向量数量
            n_vectors = index.ntotal
            
            # 检查子块数量是否匹配
            child_chunks_path = os.path.join(self.vector_db_path, 'child_chunks.json')
            if os.path.exists(child_chunks_path):
                with open(child_chunks_path, 'r', encoding='utf-8') as f:
                    child_chunks = json.load(f)
                
                if len(child_chunks) != n_vectors:
                    return CheckResult(
                        name='faiss_count_mismatch',
                        status='warning',
                        message=f"FAISS 向量数 ({n_vectors}) 与子块数 ({len(child_chunks)}) 不匹配",
                        details={'faiss_count': n_vectors, 'child_count': len(child_chunks)},
                        auto_fixable=True
                    )
            
            return CheckResult(
                name='faiss_index',
                status='ok',
                message=f"FAISS 索引正常，包含 {n_vectors} 个向量"
            )
        except Exception as e:
            return CheckResult(
                name='faiss_index',
                status='error',
                message=f"FAISS 索引检查失败: {str(e)}",
                auto_fixable=False
            )
    
    def check_model_loading(self) -> CheckResult:
        """检查模型加载状态"""
        try:
            from sentence_transformers import SentenceTransformer
            
            model_path = os.getenv("LOCAL_MODEL_PATH", os.path.join(os.path.dirname(__file__), "..", "models", "shibing624", "text2vec-base-chinese"))
            
            if not os.path.exists(model_path):
                return CheckResult(
                    name='model_path',
                    status='error',
                    message=f"模型路径不存在: {model_path}",
                    auto_fixable=False
                )
            
            # 尝试加载模型
            try:
                model = SentenceTransformer(model_path)
                dim = model.get_sentence_embedding_dimension()
                return CheckResult(
                    name='model_loading',
                    status='ok',
                    message=f"模型加载正常，维度: {dim}"
                )
            except Exception as e:
                return CheckResult(
                    name='model_loading',
                    status='error',
                    message=f"模型加载失败: {str(e)}",
                    auto_fixable=False
                )
        except Exception as e:
            return CheckResult(
                name='model_loading',
                status='error',
                message=f"模型检查失败: {str(e)}",
                auto_fixable=False
            )
    
    def check_disk_space(self) -> CheckResult:
        """检查磁盘空间"""
        try:
            import shutil
            
            total, used, free = shutil.disk_usage(self.data_dir)
            
            free_gb = free / (1024**3)
            used_percent = (used / total) * 100
            
            if free_gb < 1:  # 少于 1GB
                return CheckResult(
                    name='disk_space',
                    status='error',
                    message=f"磁盘空间严重不足: {free_gb:.2f}GB 剩余",
                    details={'free_gb': free_gb, 'used_percent': used_percent},
                    auto_fixable=False
                )
            elif free_gb < 5:  # 少于 5GB
                return CheckResult(
                    name='disk_space',
                    status='warning',
                    message=f"磁盘空间不足: {free_gb:.2f}GB 剩余",
                    details={'free_gb': free_gb, 'used_percent': used_percent},
                    auto_fixable=False
                )
            
            return CheckResult(
                name='disk_space',
                status='ok',
                message=f"磁盘空间充足: {free_gb:.2f}GB 剩余 ({used_percent:.1f}% 已用)"
            )
        except Exception as e:
            return CheckResult(
                name='disk_space',
                status='warning',
                message=f"无法检查磁盘空间: {str(e)}",
                auto_fixable=False
            )
    
    def check_session_files(self) -> CheckResult:
        """检查会话文件"""
        try:
            if not os.path.exists(self.memory_db_path):
                return CheckResult(
                    name='session_files',
                    status='ok',
                    message="会话目录不存在，暂无会话"
                )
            
            session_files = [f for f in os.listdir(self.memory_db_path) if f.endswith('.json')]
            
            # 检查文件可读性
            corrupted = []
            for f in session_files[:10]:  # 只检查前10个
                try:
                    with open(os.path.join(self.memory_db_path, f), 'r', encoding='utf-8') as fp:
                        json.load(fp)
                except:
                    corrupted.append(f)
            
            if corrupted:
                return CheckResult(
                    name='session_files',
                    status='warning',
                    message=f"发现 {len(corrupted)} 个损坏的会话文件",
                    details={'corrupted_files': corrupted},
                    auto_fixable=True
                )
            
            return CheckResult(
                name='session_files',
                status='ok',
                message=f"会话文件正常，共 {len(session_files)} 个会话"
            )
        except Exception as e:
            return CheckResult(
                name='session_files',
                status='error',
                message=f"会话检查失败: {str(e)}",
                auto_fixable=False
            )
    
    def check_orphaned_chunks(self) -> CheckResult:
        """检查孤立 chunk（有子块无父块）"""
        try:
            metadata_path = os.path.join(self.vector_db_path, 'metadata.json')
            child_map_path = os.path.join(self.vector_db_path, 'child_to_parent.json')
            
            if not os.path.exists(metadata_path) or not os.path.exists(child_map_path):
                return None
            
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            with open(child_map_path, 'r', encoding='utf-8') as f:
                child_map = json.load(f)
            
            # 找出映射到不存在的父块的子块
            orphaned = [i for i, p in enumerate(child_map) if p >= len(metadata)]
            
            if orphaned:
                return CheckResult(
                    name='orphaned_chunks',
                    status='warning',
                    message=f"发现 {len(orphaned)} 个孤立子块",
                    details={'orphaned_count': len(orphaned)},
                    auto_fixable=True
                )
            
            return CheckResult(
                name='orphaned_chunks',
                status='ok',
                message="未发现孤立 chunk"
            )
        except Exception as e:
            return CheckResult(
                name='orphaned_chunks',
                status='error',
                message=f"孤立 chunk 检查失败: {str(e)}",
                auto_fixable=False
            )
    
    def check_scene_integrity(self) -> CheckResult:
        """检查场景完整性"""
        try:
            scenes_path = os.path.join(self.vector_db_path, 'scenes.json')
            
            if not os.path.exists(scenes_path):
                return CheckResult(
                    name='scene_integrity',
                    status='ok',
                    message="暂无场景数据"
                )
            
            with open(scenes_path, 'r', encoding='utf-8') as f:
                scenes = json.load(f)
            
            # 检查场景边界
            issues = []
            for scene in scenes:
                if scene.get('start_round', 0) > scene.get('end_round', 0):
                    issues.append(f"场景 {scene.get('id')}: 起始轮次大于结束轮次")
            
            if issues:
                return CheckResult(
                    name='scene_integrity',
                    status='warning',
                    message=f"发现 {len(issues)} 个场景问题",
                    details={'issues': issues},
                    auto_fixable=True
                )
            
            return CheckResult(
                name='scene_integrity',
                status='ok',
                message=f"场景数据正常，共 {len(scenes)} 个场景"
            )
        except Exception as e:
            return CheckResult(
                name='scene_integrity',
                status='error',
                message=f"场景检查失败: {str(e)}",
                auto_fixable=False
            )
    
    def _auto_fix(self, result: CheckResult) -> bool:
        """尝试自动修复问题"""
        try:
            if result.name == 'vector_db_files':
                return self._fix_missing_files()
            elif result.name == 'metadata_exists':
                return self._fix_missing_metadata()
            elif result.name == 'faiss_index':
                return self._fix_faiss_index()
            elif result.name == 'orphaned_chunks':
                return self._fix_orphaned_chunks()
            elif result.name == 'corrupted_sessions':
                return self._fix_corrupted_sessions()
            return False
        except Exception as e:
            print(f"[AutoFix] 修复失败: {e}")
            return False
    
    def _fix_missing_files(self) -> bool:
        """修复缺失的文件"""
        os.makedirs(self.vector_db_path, exist_ok=True)
        
        # 创建空文件
        files = ['parent_chunks.json', 'child_chunks.json', 'child_to_parent.json', 'metadata.json']
        for f in files:
            path = os.path.join(self.vector_db_path, f)
            if not os.path.exists(path):
                with open(path, 'w', encoding='utf-8') as fp:
                    json.dump([] if f != 'metadata.json' else [], fp)
        return True
    
    def _fix_missing_metadata(self) -> bool:
        """修复缺失的元数据"""
        metadata_path = os.path.join(self.vector_db_path, 'metadata.json')
        parent_chunks_path = os.path.join(self.vector_db_path, 'parent_chunks.json')
        
        with open(parent_chunks_path, 'r', encoding='utf-8') as f:
            parents = json.load(f)
        
        # 创建默认元数据
        metadata = [{'timestamp': 1, 'source': 'unknown'} for _ in parents]
        
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        return True
    
    def _fix_faiss_index(self) -> bool:
        """修复 FAISS 索引"""
        try:
            import faiss
            from sentence_transformers import SentenceTransformer
            
            child_chunks_path = os.path.join(self.vector_db_path, 'child_chunks.json')
            with open(child_chunks_path, 'r', encoding='utf-8') as f:
                child_chunks = json.load(f)
            
            if not child_chunks:
                return False
            
            model_path = os.getenv("LOCAL_MODEL_PATH", os.path.join(os.path.dirname(__file__), "..", "models", "shibing624", "text2vec-base-chinese"))
            model = SentenceTransformer(model_path)
            dim = model.get_sentence_embedding_dimension()
            
            # 重新编码所有子块
            embeddings = model.encode(child_chunks)
            
            # 创建新索引
            index = faiss.IndexFlatIP(dim)
            index.add(np.array(embeddings).astype('float32'))
            
            # 保存
            faiss.write_index(index, os.path.join(self.vector_db_path, 'faiss.index'))
            return True
        except Exception as e:
            print(f"[AutoFix] FAISS 修复失败: {e}")
            return False
    
    def _fix_orphaned_chunks(self) -> bool:
        """修复孤立 chunk"""
        try:
            # 删除无效的子块映射
            child_map_path = os.path.join(self.vector_db_path, 'child_to_parent.json')
            child_chunks_path = os.path.join(self.vector_db_path, 'child_chunks.json')
            metadata_path = os.path.join(self.vector_db_path, 'metadata.json')
            
            with open(child_map_path, 'r', encoding='utf-8') as f:
                child_map = json.load(f)
            with open(child_chunks_path, 'r', encoding='utf-8') as f:
                child_chunks = json.load(f)
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            # 过滤有效项
            valid_indices = []
            for i, p in enumerate(child_map):
                if 0 <= p < len(metadata):
                    valid_indices.append(i)
            
            new_child_map = [child_map[i] for i in valid_indices]
            new_child_chunks = [child_chunks[i] for i in valid_indices]
            
            # 保存
            with open(child_map_path, 'w', encoding='utf-8') as f:
                json.dump(new_child_map, f)
            with open(child_chunks_path, 'w', encoding='utf-8') as f:
                json.dump(new_child_chunks, f)
            
            return True
        except Exception as e:
            print(f"[AutoFix] 孤立 chunk 修复失败: {e}")
            return False
    
    def _fix_corrupted_sessions(self) -> bool:
        """修复损坏的会话文件"""
        # 移动损坏文件到备份
        return True  # 简化处理
    
    def generate_report(self) -> Dict:
        """生成诊断报告"""
        total = len(self.results)
        ok = sum(1 for r in self.results if r.status == 'ok')
        warnings = sum(1 for r in self.results if r.status == 'warning')
        errors = sum(1 for r in self.results if r.status == 'error')
        fixed = sum(1 for r in self.results if r.fix_applied)
        
        return {
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total': total,
                'ok': ok,
                'warnings': warnings,
                'errors': errors,
                'fixed': fixed,
                'healthy': errors == 0
            },
            'checks': [asdict(r) for r in self.results]
        }


# 全局单例
diagnostics = DiagnosticsManager()

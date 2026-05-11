"""
ARPM-v4 数据结构定义 (Pydantic Models)
"""
from typing import List, Dict, Optional, Literal, Any
from datetime import datetime
from pydantic import BaseModel, Field

# ==================== 基础类型 ====================

class Timestamp(BaseModel):
    """双时态时间戳"""
    round_num: int = Field(..., description="对话轮次编号")
    physical_time: str = Field(..., description="物理时间 ISO格式")
    
    class Config:
        json_schema_extra = {
            "example": {
                "round_num": 5,
                "physical_time": "2026-04-07T22:31:00"
            }
        }

class SceneInfo(BaseModel):
    """场景信息（扁平结构）"""
    scene_id: str
    start_round: int
    end_round: Optional[int] = None  # None表示进行中
    title: str = ""
    summary: str = ""
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())

# ==================== 存储实体 ====================

class TextChunk(BaseModel):
    """文本块（父块/原子块）"""
    chunk_id: str = Field(..., description="唯一ID")
    text: str
    source: Literal["knowledge", "chat"]  # 来源区分
    timestamp: Timestamp
    # 知识库特有
    children: Optional[List[str]] = None  # 子块文本列表（仅知识库父块）
    # 对话特有
    session_id: Optional[str] = None
    role: Optional[Literal["user", "assistant"]] = None
    # 场景标记
    scene_id: Optional[str] = None
    # 向量（可选，用于缓存）
    embedding: Optional[List[float]] = None

class MemoryEntry(BaseModel):
    """记忆条目（对话历史中的完整轮次）"""
    entry_id: str
    session_id: str
    round_num: int
    user_input: str
    assistant_response: str
    analysis: Optional[str] = None  # ARPM分析内容
    timestamp: Timestamp
    rag_context_indices: List[int] = []  # 引用的知识库块ID

class SessionData(BaseModel):
    """会话完整数据"""
    session_id: str
    session_name: Optional[str] = None
    created_at: str
    last_round: int = 0
    current_scene_id: Optional[str] = None
    messages: List[Dict] = []  # 前端格式消息
    memories: List[MemoryEntry] = []  # 结构化记忆

# ==================== API 请求/响应 ====================

class ChatRequest(BaseModel):
    """对话请求"""
    message: str
    session_id: Optional[str] = None
    round: int = 1
    api_config: Dict[str, str] = Field(default_factory=dict)
    system_prompt: str = ""
    ablation_config: Dict[str, bool] = Field(default_factory=dict)

class ChatResponse(BaseModel):
    """对话响应"""
    session_id: str
    round: int
    status: Literal["success", "disambiguated", "error"]
    reply: str
    analysis: Optional[str] = None
    rag_context: List[str] = []
    sub_queries: Optional[List[str]] = None  # 拆解的子问题

class RetrievalResult(BaseModel):
    """检索结果"""
    chunk_id: str
    text: str
    source: Literal["knowledge", "chat"]
    score: float
    timestamp: Timestamp
    metadata: Dict = Field(default_factory=dict)

# ==================== 诊断 ====================

class CheckResult(BaseModel):
    """诊断检查结果"""
    name: str
    status: Literal["ok", "warning", "error"]
    message: str
    auto_fixable: bool = False
    fix_applied: bool = False
    details: Optional[Dict] = None

class DiagnosisReport(BaseModel):
    """诊断报告"""
    timestamp: str
    summary: Dict[str, int]  # total, ok, warning, error, fixed
    checks: List[CheckResult]
    healthy: bool


# ==================== ARPM组件报告 ====================

class ARPMComponentConfig(BaseModel):
    """ARPM组件配置"""
    name: str
    value: Any
    description: str


class ARPMComponent(BaseModel):
    """ARPM组件信息"""
    name: str
    status: Literal["active", "disabled", "error"]
    description: str
    config: List[ARPMComponentConfig] = []


class ForgettingLogicDoc(BaseModel):
    """遗忘逻辑文档"""
    name: str
    formula: str
    description: str
    parameters: Dict[str, str]


class ARPMComponentReport(BaseModel):
    """ARPM组件完整报告"""
    timestamp: str
    components: List[ARPMComponent]
    forgetting_logics: List[ForgettingLogicDoc]
    knowledge_stats: Dict
    chat_stats: Dict
    system_params: Dict

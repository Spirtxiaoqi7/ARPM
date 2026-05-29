"""Prompt builders for LOCOMO QA baselines.

The LOCOMO task prompt is an evaluation wrapper. It does not replace the ARPM
system prompt or analysis protocol; for ARPM methods, the project protocol is
placed before the benchmark-specific QA instruction.
"""
from __future__ import annotations

from typing import Dict, Iterable, List


DEFAULT_ARPM_PROTOCOL = """\
ARPM analysis protocol:
1. Treat retrieved memory as the only factual source for this benchmark answer.
2. Keep the chronological order of memory blocks: earlier rounds first, later rounds last.
3. Preserve physical time, round number, speaker, and dia_id for each block.
4. Use the required <analysis>/<response> format when requested.
"""


LOCOMO_QA_INSTRUCTION = """\
LOCOMO QA task:
You are answering a question about a long conversation.
Use only the retrieved conversation evidence.
If the evidence is insufficient, answer "I don't know".
The final answer must be a short factual phrase.
Do not explain.
"""


LOCOMO_ARPM_TAGGED_INSTRUCTION = """\
LOCOMO-ARPM QA task:
You are answering a question about a long conversation using retrieved memory.
Use only the retrieved conversation evidence.
If the evidence is insufficient, answer "I don't know".

Analysis requirement:
Write exactly one short sentence inside <analysis>...</analysis>.
The analysis must summarize which retrieved evidence is relevant to the question.
If no retrieved evidence supports the answer, state that the answer is unclear.
Do not reveal step-by-step reasoning.

Answer requirement:
Write the final benchmark answer inside <response>...</response>.
The response must be a short factual phrase only.

Required output format:
<analysis>one-sentence evidence summary</analysis>
<response>short factual answer</response>
"""


def sort_chunks_chronologically(chunks: Iterable[Dict]) -> List[Dict]:
    return sorted(
        chunks,
        key=lambda c: (
            int((c.get("timestamp") or {}).get("round_num", 0) or 0),
            str((c.get("timestamp") or {}).get("physical_time", "")),
            str(c.get("dia_id", "")),
        ),
    )


def format_memory_blocks(chunks: Iterable[Dict], max_chars_per_chunk: int = 700) -> str:
    lines = []
    for i, chunk in enumerate(sort_chunks_chronologically(chunks), start=1):
        ts = chunk.get("timestamp") or {}
        round_num = ts.get("round_num", "")
        physical_time = ts.get("physical_time", "")
        speaker = chunk.get("speaker") or chunk.get("user_name") or ""
        dia_id = chunk.get("dia_id") or chunk.get("chunk_id") or ""
        text = chunk.get("text_raw") or chunk.get("text") or ""
        if len(text) > max_chars_per_chunk:
            text = text[:max_chars_per_chunk] + "..."
        lines.append(
            f"[{i}] round={round_num} physical_time={physical_time} "
            f"speaker={speaker} dia_id={dia_id}\n{text}"
        )
    return "\n\n".join(lines) if lines else "(no retrieved evidence)"


def _format_optional_chat_history(chat_history_chunks: List[Dict] | None) -> str:
    if not chat_history_chunks:
        return ""
    return f"""\

Retrieved conversation-history route:
{format_memory_blocks(chat_history_chunks)}
"""


def build_plain_rag_prompt(question: str, retrieved_chunks: List[Dict], chat_history_chunks: List[Dict] | None = None) -> str:
    return f"""\
{LOCOMO_QA_INSTRUCTION}

Retrieved LOCOMO evidence route:
{format_memory_blocks(retrieved_chunks)}
{_format_optional_chat_history(chat_history_chunks)}

Question:
{question}

Final answer:
"""


def build_arpm_protocol_prompt(
    question: str,
    retrieved_chunks: List[Dict],
    system_prompt: str = "",
    analysis_protocol: str = DEFAULT_ARPM_PROTOCOL,
    chat_history_chunks: List[Dict] | None = None,
) -> str:
    prefix = "\n\n".join(part for part in [system_prompt.strip(), analysis_protocol.strip()] if part)
    return f"""\
{prefix}

{LOCOMO_QA_INSTRUCTION}

Retrieved LOCOMO evidence route:
{format_memory_blocks(retrieved_chunks)}
{_format_optional_chat_history(chat_history_chunks)}

Question:
{question}

Final answer:
"""


def build_arpm_full_prompt(
    question: str,
    retrieved_chunks: List[Dict],
    system_prompt: str = "",
    analysis_protocol: str = DEFAULT_ARPM_PROTOCOL,
    chat_history_chunks: List[Dict] | None = None,
) -> str:
    arpm_memory_rule = """\
ARPM memory injection rule:
The retrieved blocks below are injected as memory context through two routes.
Route A is the LOCOMO evidence route and remains the benchmark retrieval set.
Route B is the conversation-history route and follows the original ARPM-style
chat memory recall. Earlier rounds must appear first and later rounds must
appear last within each route. Every block must keep physical time. The last
memory block the model reads within a route should be the most recent retrieved
content among that route's selected evidence blocks.
"""
    user_protocol = system_prompt.strip()
    has_custom_tag_protocol = "<analysis>" in user_protocol.lower() and "<response>" in user_protocol.lower()
    protocol_parts = [user_protocol, arpm_memory_rule.strip()] if has_custom_tag_protocol else [
        user_protocol,
        analysis_protocol.strip(),
        arpm_memory_rule.strip(),
        LOCOMO_ARPM_TAGGED_INSTRUCTION,
    ]
    prefix = "\n\n".join(part for part in protocol_parts if part)
    return f"""\
{prefix}

Chronological LOCOMO evidence route:
{format_memory_blocks(retrieved_chunks)}
{_format_optional_chat_history(chat_history_chunks)}

Question:
{question}

Required output:
"""


def build_prompt(
    method: str,
    question: str,
    retrieved_chunks: List[Dict],
    system_prompt: str = "",
    chat_history_chunks: List[Dict] | None = None,
) -> str:
    if method == "plain_rag":
        return build_plain_rag_prompt(question, retrieved_chunks, chat_history_chunks=chat_history_chunks)
    if method == "arpm_protocol":
        return build_arpm_protocol_prompt(question, retrieved_chunks, system_prompt=system_prompt, chat_history_chunks=chat_history_chunks)
    if method == "arpm_full":
        return build_arpm_full_prompt(question, retrieved_chunks, system_prompt=system_prompt, chat_history_chunks=chat_history_chunks)
    raise ValueError(f"Unknown prompt method: {method}")

from __future__ import annotations

from collections.abc import Generator
from dataclasses import dataclass
from time import perf_counter
from typing import Any

from app.kongming_agent.backend.app.core.config import settings
from app.kongming_agent.backend.app.services.deepseek_client import deepseek_client
from app.kongming_agent.backend.app.services.knowledge_base import FourClassicsKnowledgeBase
from app.kongming_agent.backend.app.services.session_service import session_service


# 四大名著实体关键词 — 问题必须命中至少一个才算相关
_FOUR_CLASSICS_ENTITIES: set[str] = {
    # === 书名 ===
    "三国演义", "三国", "红楼梦", "石头记", "西游记", "水浒传", "水浒",
    # === 三国 ===
    "诸葛亮", "孔明", "卧龙", "刘备", "玄德", "关羽", "云长", "关公", "关二爷",
    "张飞", "翼德", "曹操", "孟德", "曹孟德", "孙权", "仲谋", "周瑜", "公瑾",
    "司马懿", "仲达", "赵云", "子龙", "黄忠", "汉升", "马超", "孟起",
    "吕布", "奉先", "貂蝉", "董卓", "袁绍", "刘表", "庞统", "凤雏",
    "姜维", "魏延", "张辽", "许褚", "典韦", "鲁肃", "陆逊",
    "荆州", "赤壁", "官渡", "夷陵", "长坂坡", "五丈原", "街亭",
    "桃园结义", "三顾茅庐", "草船借箭", "空城计", "七擒孟获",
    "隆中对", "出师表", "蜀汉", "曹魏", "东吴",
    # === 红楼梦 ===
    "贾宝玉", "宝玉", "林黛玉", "黛玉", "薛宝钗", "宝钗", "王熙凤", "凤姐",
    "贾母", "刘姥姥", "晴雯", "袭人", "史湘云", "探春", "迎春", "惜春",
    "贾政", "王夫人", "尤二姐", "尤三姐", "秦可卿", "李纨", "妙玉",
    "贾府", "大观园", "荣国府", "宁国府", "怡红院", "潇湘馆",
    "金陵十二钗", "葬花吟",
    # === 西游记 ===
    "孙悟空", "行者", "美猴王", "唐僧", "唐三藏", "玄奘",
    "猪八戒", "悟能", "沙僧", "沙和尚", "悟净",
    "如来", "如来佛", "观音", "白骨精", "牛魔王", "铁扇公主",
    "红孩儿", "哪吒", "二郎神", "玉皇大帝", "太白金星",
    "花果山", "天宫", "西天取经", "大闹天宫", "三打白骨精",
    "金箍棒", "紧箍咒", "八十一难", "蟠桃会",
    # === 水浒传 ===
    "宋江", "及时雨", "武松", "林冲", "鲁智深", "鲁达", "花和尚",
    "李逵", "吴用", "卢俊义", "晁盖", "燕青", "石秀", "杨志",
    "孙二娘", "扈三娘", "高俅", "西门庆", "潘金莲",
    "梁山", "梁山泊", "聚义厅", "忠义堂", "水泊梁山",
    "一百零八将", "一百单八将",
}


def _is_four_classics_query(question: str) -> bool:
    """检查问题是否涉及四大名著的人物、事件、地名或书名。"""
    return any(entity in question for entity in _FOUR_CLASSICS_ENTITIES)


def _build_context(sources: list[dict[str, Any]]) -> str:
    if not sources:
        return ""
    parts = []
    for idx, source in enumerate(sources, start=1):
        parts.append(
            f"[{idx}] 《{source['doc_title']}》/ score={source['score']}\n{source['excerpt']}"
        )
    return "\n\n".join(parts)


def _estimate_tokens(text: str) -> int:
    return len(text) // 2 + len([c for c in text if ord(c) > 127])


@dataclass
class KongmingAnswer:
    answer: str
    sources: list[dict[str, Any]]
    usage: dict[str, int]


class KongmingAgentService:
    def __init__(self) -> None:
        self.knowledge_base = FourClassicsKnowledgeBase()

    def answer(self, session_id: str, question: str, top_k: int | None = None, use_rag: bool = True) -> KongmingAnswer:
        top_k = top_k or settings.knowledge_top_k
        session = session_service.get_session(session_id)
        if not session:
            raise ValueError(f"session not found: {session_id}")

        session_service.add_message(session_id, "user", question)

        # 知识库检索 —— 先做实体匹配，问题不涉及四大名著则直接跳过 RAG
        if use_rag and _is_four_classics_query(question):
            start = perf_counter()
            raw_sources = self.knowledge_base.search(question, top_k=top_k)
            latency_ms = int((perf_counter() - start) * 1000)
            session_service.record_retrieval(session_id, question, top_k, raw_sources, latency_ms)

            max_score = max((s.get("score", 0) for s in raw_sources), default=0)
            if max_score < 0.48:
                sources = []
            else:
                MIN_SCORE = 0.45
                sources = [s for s in raw_sources if s.get("score", 0) >= MIN_SCORE]
        else:
            sources = []

        # 构建 messages 并调用 DeepSeek
        answer = self._generate_answer(session_id, question, sources)
        assistant_message = session_service.add_message(
            session_id, "assistant", answer, "rag" if sources else "manual", sources
        )

        prompt_tokens = _estimate_tokens(question) + _estimate_tokens(_build_context(sources))
        completion_tokens = _estimate_tokens(answer)
        usage = {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        }
        return KongmingAnswer(answer=assistant_message["content"], sources=sources, usage=usage)

    def _build_system_prompt(self, session_id: str, context: str) -> str:
        session = session_service.get_session(session_id)
        agent_code = session.get("agent_code", settings.default_agent_code) if session else settings.default_agent_code

        # 读取 Agent 人设
        agent_config = session_service.get_agent_config(agent_code)
        persona_desc = agent_config.get("persona_desc", "")
        persona_name = agent_config.get("persona_name", "诸葛孔明")

        # 读取 prompt 模板
        template = session_service.get_prompt_template(f"{agent_code}_default")
        system_prompt = ""
        if template:
            system_prompt = template.get("system_prompt", "")

        lines = [f"你是{persona_name}。{persona_desc}"]
        if system_prompt:
            lines.append(system_prompt)

        if context:
            lines.append(
                f"回答要求：\n"
                f"- 以{persona_name}的口吻回答，文雅稳重，略带古意\n"
                f"- 必须严格依据以下参考资料回答，不得编造或使用外部知识\n"
                f"- 若参考资料不足以回答问题，应明确说明\n"
                f"- 不使用现代网络流行语"
            )
            lines.append(f"\n参考资料：\n{context}")
        else:
            lines.append(
                f"回答要求：\n"
                f"- 以{persona_name}的口吻回答，文雅稳重，略带古意\n"
                f"- 你通晓四大名著，可以依据自身学识回答\n"
                f"- 不使用现代网络流行语"
            )

        return "\n\n".join(lines)

    def _generate_answer(self, session_id: str, question: str, sources: list[dict[str, Any]]) -> str:
        context = _build_context(sources)
        system_prompt = self._build_system_prompt(session_id, context)

        # 构建多轮对话历史（最近 N 条）
        history_limit = settings.chat_history_limit
        all_messages = session_service.list_messages(session_id)

        history_messages: list[dict[str, str]] = [
            {"role": "system", "content": system_prompt}
        ]

        # 取最近 history_limit 条 user/assistant 对话作为上下文
        conversation_pairs: list[dict[str, str]] = []
        for msg in all_messages:
            role = msg["role"]
            if role in ("user", "assistant"):
                conversation_pairs.append(
                    {"role": role, "content": msg["content"]}
                )

        # 只保留最后 N 轮（不包括最新那条 user 消息，因为它就是当前问题）
        history_pairs = conversation_pairs[-(history_limit * 2 + 1):-1] if len(conversation_pairs) > 1 else []
        history_messages.extend(history_pairs)

        # 当前问题
        history_messages.append({"role": "user", "content": question})

        try:
            answer = deepseek_client.chat(
                messages=history_messages,
                temperature=settings.default_temperature,
                max_tokens=settings.default_max_tokens,
            )
            return answer.strip()
        except Exception as exc:
            return f"孔明一时未能作答。{exc}"


    def answer_stream(
        self, session_id: str, question: str, top_k: int | None = None, use_rag: bool = True
    ) -> Generator[tuple[str, Any], None, None]:
        top_k = top_k or settings.knowledge_top_k
        session = session_service.get_session(session_id)
        if not session:
            raise ValueError(f"session not found: {session_id}")

        session_service.add_message(session_id, "user", question)

        # 知识库检索 —— 先做实体匹配
        if use_rag and _is_four_classics_query(question):
            start = perf_counter()
            raw_sources = self.knowledge_base.search(question, top_k=top_k)
            latency_ms = int((perf_counter() - start) * 1000)
            session_service.record_retrieval(session_id, question, top_k, raw_sources, latency_ms)

            max_score = max((s.get("score", 0) for s in raw_sources), default=0)
            if max_score < 0.48:
                sources = []
            else:
                MIN_SCORE = 0.45
                sources = [s for s in raw_sources if s.get("score", 0) >= MIN_SCORE]
        else:
            sources = []

        context = _build_context(sources)
        system_prompt = self._build_system_prompt(session_id, context)

        history_limit = settings.chat_history_limit
        all_messages = session_service.list_messages(session_id)

        history_messages: list[dict[str, str]] = [
            {"role": "system", "content": system_prompt}
        ]

        conversation_pairs: list[dict[str, str]] = []
        for msg in all_messages:
            role = msg["role"]
            if role in ("user", "assistant"):
                conversation_pairs.append(
                    {"role": role, "content": msg["content"]}
                )

        history_pairs = conversation_pairs[-(history_limit * 2 + 1):-1] if len(conversation_pairs) > 1 else []
        history_messages.extend(history_pairs)
        history_messages.append({"role": "user", "content": question})

        full_answer = ""
        try:
            for chunk in deepseek_client.chat_stream(
                messages=history_messages,
                temperature=settings.default_temperature,
                max_tokens=settings.default_max_tokens,
            ):
                full_answer += chunk
                yield ("chunk", chunk)

            session_service.add_message(
                session_id, "assistant", full_answer, "rag" if sources else "manual", sources
            )

            prompt_tokens = _estimate_tokens(question) + _estimate_tokens(context)
            completion_tokens = _estimate_tokens(full_answer)
            usage = {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
            }
            yield ("done", {"sources": sources, "usage": usage})
        except Exception as exc:
            yield ("error", {"message": f"孔明一时未能作答。{exc}"})


kongming_agent_service = KongmingAgentService()

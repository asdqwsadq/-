from __future__ import annotations

import json

from app.kongming_agent.backend.app.services.knowledge_base import FourClassicsKnowledgeBase


if __name__ == "__main__":
    result = FourClassicsKnowledgeBase().rebuild_vector_store()
    print(json.dumps(result, ensure_ascii=False, indent=2))

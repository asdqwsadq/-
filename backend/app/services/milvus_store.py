from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from pymilvus import Collection, CollectionSchema, DataType, FieldSchema, MilvusException, connections, utility

from app.core.config import settings


@dataclass
class MilvusChunkRecord:
    chunk_id: str
    corpus_name: str
    doc_title: str
    chunk_text: str
    metadata: dict[str, Any]
    vector: list[float]


class MilvusStore:
    def __init__(self) -> None:
        self.collection_name = settings.milvus_collection
        self.dim = settings.embedding_dim
        self._connected = False

    def connect(self) -> None:
        if self._connected:
            return
        connections.connect(
            alias="default",
            host=settings.milvus_host,
            port=str(settings.milvus_port),
        )
        self._connected = True

    def ensure_collection(self) -> Collection:
        self.connect()
        if utility.has_collection(self.collection_name):
            collection = Collection(self.collection_name)
            collection.load()
            return collection


        fields = [
            FieldSchema(name="chunk_id", dtype=DataType.VARCHAR, is_primary=True, auto_id=False, max_length=128),
            FieldSchema(name="corpus_name", dtype=DataType.VARCHAR, max_length=128),
            FieldSchema(name="doc_title", dtype=DataType.VARCHAR, max_length=255),
            FieldSchema(name="chunk_text", dtype=DataType.VARCHAR, max_length=65535),
            FieldSchema(name="metadata_json", dtype=DataType.VARCHAR, max_length=4096),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=self.dim),
        ]
        schema = CollectionSchema(fields, description="Four classics knowledge chunks")
        collection = Collection(name=self.collection_name, schema=schema)
        collection.create_index(
            field_name="embedding",
            index_params={
                "index_type": "AUTOINDEX",
                "metric_type": "COSINE",
            },
        )
        collection.load()
        return collection

    def drop_collection(self) -> None:
        self.connect()
        if utility.has_collection(self.collection_name):
            utility.drop_collection(self.collection_name)

    def upsert(self, records: list[MilvusChunkRecord]) -> None:
        if not records:
            return
        collection = self.ensure_collection()
        payload = [
            [record.chunk_id for record in records],
            [record.corpus_name for record in records],
            [record.doc_title for record in records],
            [record.chunk_text for record in records],
            [json.dumps(record.metadata, ensure_ascii=False) for record in records],
            [record.vector for record in records],
        ]
        try:
            collection.insert(payload)
            collection.flush()
        except MilvusException:
            raise

    def search(self, vector: list[float], top_k: int = 4, corpus_name: str | None = None) -> list[dict[str, Any]]:
        collection = self.ensure_collection()
        expr = None
        if corpus_name:
            expr = f'corpus_name == "{corpus_name}"'
        results = collection.search(
            data=[vector],
            anns_field="embedding",
            param={"metric_type": "COSINE", "params": {}},
            limit=top_k,
            expr=expr,
            output_fields=["corpus_name", "doc_title", "chunk_text", "metadata_json"],
        )
        output: list[dict[str, Any]] = []
        if not results:
            return output
        for hit in results[0]:
            output.append(
                {
                    "chunk_id": hit.id,
                    "corpus_name": hit.entity.get("corpus_name"),
                    "doc_title": hit.entity.get("doc_title"),
                    "chunk_text": hit.entity.get("chunk_text"),
                    "score": float(hit.score),
                    "metadata": json.loads(hit.entity.get("metadata_json") or "{}"),
                }
            )
        return output

    def has_data(self) -> bool:
        try:
            self.connect()
            if not utility.has_collection(self.collection_name):
                return False
            collection = Collection(self.collection_name)
            return collection.num_entities > 0
        except Exception:
            return False


@lru_cache(maxsize=1)
def get_milvus_store() -> MilvusStore:
    return MilvusStore()

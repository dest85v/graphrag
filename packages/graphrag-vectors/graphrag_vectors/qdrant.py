# Copyright (c) 2024 Microsoft Corporation.
# Licensed under the MIT License

"""A package containing the Qdrant vector store implementation."""

from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.http.models import (
    Distance,
    ExtendedPointId,
    FieldCondition,
    Filter,
    FilterSelector,
    HasIdCondition,
    IsNullCondition,
    MatchAny,
    MatchText,
    MatchValue,
    PointStruct,
    Range,
    VectorParams,
)

from graphrag_vectors.filtering import (
    AndExpr,
    Condition,
    FilterExpr,
    NotExpr,
    Operator,
    OrExpr,
)
from graphrag_vectors.vector_store import (
    VectorStore,
    VectorStoreDocument,
    VectorStoreSearchResult,
)


def _qdrant_id(id_val: str | int) -> ExtendedPointId:
    """Convert a document ID to a Qdrant-compatible point ID.

    Qdrant local mode requires integer or UUID string IDs.
    If the ID looks like an integer, use it as int.
    Otherwise, wrap it as a string (works with remote Qdrant).
    """
    try:
        return int(id_val)  # type: ignore[return-value]
    except (ValueError, TypeError):
        return str(id_val)


class QdrantVectorStore(VectorStore):
    """Qdrant vector storage implementation."""

    def __init__(
        self,
        url: str | None = None,
        api_key: str | None = None,
        db_uri: str | None = None,
        distance: str | None = "cosine",
        hnsw_m: int | None = None,
        hnsw_ef_construct: int | None = None,
        hnsw_ef: int | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)

        if not url and not db_uri:
            msg = "url or db_uri must be provided for Qdrant."
            raise ValueError(msg)

        # Resolve connection: db_uri takes precedence for local modes (:memory:, /path)
        if db_uri and (db_uri.startswith(":") or "/" in db_uri):
            self._connection_args: dict[str, Any] = {"path": db_uri}
        else:
            self._connection_args = {"url": url or db_uri}  # type: ignore[arg-type]

        if api_key:
            self._connection_args["api_key"] = api_key

        self._distance = distance
        self._hnsw_m = hnsw_m
        self._hnsw_ef_construct = hnsw_ef_construct
        self._hnsw_ef = hnsw_ef
        self._client: QdrantClient | None = None
        self._collection_exists: bool = False

    def connect(self) -> None:
        """Connect to Qdrant vector storage."""
        self._client = QdrantClient(**self._connection_args)
        self._collection_exists = self._client.collection_exists(self.index_name)

    def create_index(self) -> None:
        """Create or recreate the Qdrant collection."""
        if not self.index_name:
            msg = "index_name must be provided for Qdrant."
            raise ValueError(msg)

        if self._client is None:
            msg = "Must call connect() before create_index()."
            raise ValueError(msg)

        # Delete existing collection if present (overwrite semantics)
        if self._client.collection_exists(self.index_name):
            self._client.delete_collection(collection_name=self.index_name)

        # Build HNSW config
        hnsw_config_kwargs: dict[str, Any] = {}
        if self._hnsw_m is not None:
            hnsw_config_kwargs["m"] = self._hnsw_m
        if self._hnsw_ef_construct is not None:
            hnsw_config_kwargs["ef_construct"] = self._hnsw_ef_construct

        # Map distance string to Distance enum
        distance_map: dict[str, Distance] = {
            "cosine": Distance.COSINE,
            "dot": Distance.DOT,
            "euclidean": Distance.EUCLID,
            "manhattan": Distance.MANHATTAN,
        }
        distance = distance_map.get(self._distance, Distance.COSINE)

        self._client.create_collection(
            collection_name=self.index_name,
            vectors_config=VectorParams(
                size=self.vector_size,
                distance=distance,
            ),
            **({"hnsw_config": hnsw_config_kwargs} if hnsw_config_kwargs else {}),
        )
        self._collection_exists = True

    def load_documents(self, documents: list[VectorStoreDocument]) -> None:
        """Load documents into Qdrant as points with vectors and payloads."""
        if not documents:
            return

        # Build points in batches of 1000
        batch_size = 1000
        for batch_start in range(0, len(documents), batch_size):
            batch = documents[batch_start : batch_start + batch_size]
            points = []
            for doc in batch:
                self._prepare_document(doc)
                if doc.vector is None:
                    continue

                # Map payload data fields
                payload: dict[str, Any] = {}
                if doc.data:
                    for field_name in self.fields:
                        if field_name in doc.data:
                            value = doc.data[field_name]
                            # Ensure proper types for Qdrant
                            if self.fields.get(field_name) == "int" and isinstance(
                                value, (float, str),
                            ):
                                value = int(float(value))
                            elif self.fields.get(field_name) == "float" and isinstance(
                                value, (int, str),
                            ):
                                value = float(value)
                            elif self.fields.get(field_name) == "bool" and isinstance(
                                value, str,
                            ):
                                value = value.lower() in {"true", "1", "yes"}
                            payload[field_name] = value

                points.append(
                    PointStruct(
                        id=_qdrant_id(doc.id),
                        vector=doc.vector,
                        payload=payload,
                    ),
                )

            if points:
                self._client.upsert(  # type: ignore[union-attr]
                    collection_name=self.index_name,
                    points=points,
                )

    def _compile_filter(self, expr: FilterExpr | None) -> Filter | None:
        """Compile a FilterExpr into a Qdrant Filter."""
        if expr is None:
            return None

        match expr:
            case Condition() if expr.operator == Operator.ne:
                # NOT EQUAL: wrap in must_not
                return Filter(
                    must_not=[
                        FieldCondition(
                            key=expr.field, match=MatchValue(value=expr.value),
                        ),
                    ],
                )
            case Condition() if expr.operator == Operator.exists:
                if expr.value:
                    return Filter(must_not=[IsNullCondition(key=expr.field)])
                return Filter(must=[IsNullCondition(key=expr.field)])
            case Condition():
                return Filter(must=[self._compile_condition(expr)])
            case AndExpr():
                must = [
                    self._compile_filter(e)
                    for e in expr.and_
                    if self._compile_filter(e)
                ]
                return Filter(must=must) if must else None
            case OrExpr():
                should = [
                    self._compile_filter(e) for e in expr.or_ if self._compile_filter(e)
                ]
                return Filter(should=should) if should else None
            case NotExpr():
                must_not = [self._compile_filter(expr.not_)]
                return Filter(must_not=must_not) if must_not else None
            case _:
                msg = f"Unsupported filter expression type: {type(expr)}"
                raise ValueError(msg)

    def _compile_condition(self, cond: Condition) -> FieldCondition:
        """Compile a single Condition to a Qdrant FieldCondition."""
        field = cond.field
        value = cond.value

        match cond.operator:
            case Operator.eq:
                return FieldCondition(key=field, match=MatchValue(value=value))
            case Operator.ne:
                return FieldCondition(key=field, match=MatchValue(value=value))
            case Operator.gt:
                return FieldCondition(key=field, range=Range(gt=value))
            case Operator.gte:
                return FieldCondition(key=field, range=Range(gte=value))
            case Operator.lt:
                return FieldCondition(key=field, range=Range(lt=value))
            case Operator.lte:
                return FieldCondition(key=field, range=Range(lte=value))
            case Operator.in_:
                return FieldCondition(key=field, match=MatchAny(any=value))
            case Operator.not_in:
                return FieldCondition(key=field, match=MatchAny(any=value))
            case Operator.contains:
                return FieldCondition(key=field, match=MatchText(text=value))
            case Operator.startswith:
                return FieldCondition(key=field, match=MatchText(text=f"{value}"))
            case Operator.endswith:
                return FieldCondition(key=field, match=MatchText(text=value))
            case Operator.exists:
                # Handled at _compile_filter level with Filter wrapping
                return FieldCondition(key=field, match=MatchValue(value=None))
            case _:
                msg = f"Unsupported operator for Qdrant: {cond.operator}"
                raise ValueError(msg)

    def similarity_search_by_vector(
        self,
        query_embedding: list[float],
        k: int = 10,
        select: list[str] | None = None,
        filters: FilterExpr | None = None,
        include_vectors: bool = True,
    ) -> list[VectorStoreSearchResult]:
        """Perform a vector-based similarity search."""
        qdrant_filter = self._compile_filter(filters)

        with_payload = select if select is not None else True  # type: ignore[assignment]
        with_vectors = include_vectors

        hits = self._client.query_points(  # type: ignore[union-attr]
            collection_name=self.index_name,
            query=query_embedding,
            query_filter=qdrant_filter,
            limit=k,
            with_payload=with_payload,
            with_vectors=with_vectors,
        )

        results = []
        for point in hits.points:
            vector = None
            if include_vectors and point.vector is not None:
                if isinstance(point.vector, list):
                    vector = point.vector
                elif hasattr(point.vector, "vector"):
                    vector = point.vector.vector  # type: ignore[attr-defined]

            point_id = point.payload.get(self.id_field) if point.payload else point.id
            results.append(
                VectorStoreSearchResult(
                    document=VectorStoreDocument(
                        id=str(point_id) if point_id is not None else str(point.id),
                        vector=vector,
                        data=point.payload or {},
                        create_date=point.payload.get(self.create_date_field)
                        if point.payload
                        else None,
                        update_date=point.payload.get(self.update_date_field)
                        if point.payload
                        else None,
                    ),
                    score=point.score or 0.0,
                ),
            )

        return results

    def search_by_id(
        self,
        id: str,
        select: list[str] | None = None,
        include_vectors: bool = True,
    ) -> VectorStoreDocument:
        """Search for a document by id."""
        with_payload = select if select is not None else True  # type: ignore[assignment]
        with_vectors = include_vectors

        qdrant_id = _qdrant_id(id)
        result = self._client.retrieve(  # type: ignore[union-attr]
            collection_name=self.index_name,
            ids=[qdrant_id],
            with_payload=with_payload,
            with_vectors=with_vectors,
        )

        if not result:
            msg = f"Document with id '{id}' not found."
            raise IndexError(msg)

        point = result[0]
        vector = None
        if include_vectors and point.vector is not None:
            if isinstance(point.vector, list):
                vector = point.vector
            elif hasattr(point.vector, "vector"):
                vector = point.vector.vector  # type: ignore[attr-defined]

        point_id = point.payload.get(self.id_field) if point.payload else point.id
        return VectorStoreDocument(
            id=str(point_id) if point_id is not None else str(point.id),
            vector=vector,
            data=point.payload or {},
            create_date=point.payload.get(self.create_date_field)
            if point.payload
            else None,
            update_date=point.payload.get(self.update_date_field)
            if point.payload
            else None,
        )

    def count(self) -> int:
        """Return the total number of documents in the store."""
        result = self._client.count(  # type: ignore[union-attr]
            collection_name=self.index_name,
            exact=True,
        )
        return result.count

    def remove(self, ids: list[str]) -> None:
        """Remove documents by their IDs."""
        qdrant_ids = [_qdrant_id(id_val) for id_val in ids]
        self._client.delete(  # type: ignore[union-attr]
            collection_name=self.index_name,
            points_selector=FilterSelector(
                filter=Filter(must=[HasIdCondition(has_id=qdrant_ids)]),
            ),
        )

    def update(self, document: VectorStoreDocument) -> None:
        """Update an existing document in the store."""
        self._prepare_update(document)

        # Read the existing document
        existing = self.search_by_id(str(document.id), include_vectors=True)

        # Update fields
        if document.vector is not None:
            existing.vector = document.vector

        if document.data:
            for field_name in self.fields:
                if field_name in document.data:
                    existing.data[field_name] = document.data[field_name]

        if document.update_date:
            existing.update_date = document.update_date

        # Upsert the updated document
        self.load_documents([existing])

"""For documents processing"""
from enum import Enum
import logging
import warnings
import os
from pathlib import Path, PosixPath
from typing import Any

from haystack import Document
from haystack.dataclasses import SparseEmbedding
from haystack.document_stores.types import DuplicatePolicy
from haystack.components.converters import MultiFileConverter
from haystack.components.converters.image import ImageFileToDocument
from haystack.components.routers import FileTypeRouter, DocumentTypeRouter
from haystack.components.preprocessors import DocumentCleaner
from haystack_integrations.document_stores.qdrant import QdrantDocumentStore

from qdrant_client.conversions.common_types import PointId
from fastembed import TextEmbedding, SparseTextEmbedding, ImageEmbedding

from localassistant.utils import LocasException, Constant, UtilsMethod, PATH

LOGGER = logging.getLogger(__name__)

class EmbeddingMode(Enum):
    """Mode used to extract docs."""
    DENSE = TextEmbedding
    SPARSE = SparseTextEmbedding
    IMAGE = ImageEmbedding

class LocasDocs:
    """Everything about documenting."""
    def __init__(
        self,
        port: int = Constant.DEFAULT_QDRANT_PORT,
        top_k: int = Constant.DEFAULT_TOP_K,
        score_threshold: float = Constant.DEFAULT_SCORE_THRESHOLD,
        dense_model_path: Path | None = None,
        sparse_model_path: Path | None = None,
        image_model_path: Path | None = None,
    ) -> None:
        self.file_container: Path = PATH.docs / "file_container"
        self.file_container.mkdir(parents=True, exist_ok=True)

        self.document_store: QdrantDocumentStore
        self.embedder: dict = {}
        self.retriever: Any | None = None

        self.set_models(port, top_k, score_threshold,
                        dense_model_path, sparse_model_path, image_model_path)

    def __del__(self):
        if hasattr(self, "document_store"):
            self.document_store.close()

    @staticmethod
    def analyze_docs(sources: list[str]) -> dict:
        "Do not repeat yourself - As I disgust my codebase."
        router: dict = FileTypeRouter(
            mime_types=["image/.*", "application/json"]
        ).run(sources) # type: ignore

        documents: list[Document] = []

        file_docs_path = router.get("unclassified")
        file_docs_unclassified: list[str] = []
        if file_docs_path:
            file_docs = MultiFileConverter(json_content_key="*").run(sources=file_docs_path) #pylint:disable=E1111:assignment-from-no-return
            documents += file_docs.get("documents", [])
            file_docs_unclassified = file_docs.get("unclassified", []) #type:ignore

        unclassified: list[str] = [] # Last try.
        for unclassified_path in file_docs_unclassified + router.get("application/json", []):
            path = Path(unclassified_path)
            try:
                with path.open("r", encoding="utf-8") as f:
                    documents.append(Document(
                        content=f.read(),
                        meta={"file_path": path.name}
                    ))
                    f.close()
            except UnicodeDecodeError:
                unclassified.append(unclassified_path)

        return {
            "images": router.get("image/.*", []),
            "documents": documents,
            "unclassified": unclassified
        }

    @staticmethod
    def __path_to_kwargs(path: Path) -> dict:
        qdrant_repo_id: str = os.path.join(path.parent.name, path.name)
         #pylint:disable=W0212:protected-access
        for model in TextEmbedding._list_supported_models() +\
                     SparseTextEmbedding._list_supported_models() +\
                     ImageEmbedding._list_supported_models():
            if qdrant_repo_id == model.sources.hf:
                return {
                    "model_name": model.model,
                    "dim": getattr(model, "dim") if hasattr(model, "dim") else None,
                    "local_files_only": True,
                    "specific_model_path": str(path)
                }
        raise LocasException("Invalid model path.")

    def __init_embedder(
        self,
        dense_path: Path | None,
        sparse_path: Path | None,
        image_path: Path | None
    ):
        assert dense_path or sparse_path or image_path, "Need at least one embedder."

        embedder: dict = {}
        for mode in EmbeddingMode:
            path = locals().get(f"{mode.name.lower()}_path")
            if path:
                embedder_kwargs: dict = self.__path_to_kwargs(path)
                embedder_kwargs.pop("dim")
                embedder.update({mode.name: mode.value(**embedder_kwargs)})
            else:
                if embedder.get(mode.name):
                    embedder.pop(mode.name)
        self.embedder = embedder

    #pylint:disable=C0415:import-outside-toplevel W0201:attribute-defined-outside-init
    def __init_retriever(self, top_k: int, score_threshold: float):
        using_dense: bool = bool(self.embedder.get(EmbeddingMode.DENSE.name)\
                              or self.embedder.get(EmbeddingMode.IMAGE.name))
        using_sparse: bool = bool(self.embedder.get(EmbeddingMode.SPARSE.name))

        if using_dense and using_sparse:
            from haystack_integrations.components.retrievers.qdrant import (
                QdrantHybridRetriever as Retriever
            )
        elif using_dense:
            from haystack_integrations.components.retrievers.qdrant import (
                QdrantEmbeddingRetriever as Retriever
            )
        elif using_sparse:
            from haystack_integrations.components.retrievers.qdrant import (
                QdrantSparseEmbeddingRetriever as Retriever
            )
        else:
            raise LocasException("Cannot access to a valid retriever.")
        self.retriever = Retriever(
            document_store=self.document_store,
            top_k=top_k,
            score_threshold=score_threshold
        )

    def set_models(self,
        port: int = Constant.DEFAULT_QDRANT_PORT,
        top_k: int = Constant.DEFAULT_TOP_K,
        score_threshold: float = Constant.DEFAULT_SCORE_THRESHOLD,
        dense_model_path: Path | None = None,
        sparse_model_path: Path | None = None,
        image_model_path: Path | None = None,
    ) -> None:
        """So that embed and retrieve functions can be used."""
        for embedding in EmbeddingMode:
            model_path = locals().get(f"{embedding.name.lower()}_model_path")
            if model_path:
                LOGGER.info("Load %s models: %s", embedding.name.lower(), model_path)

        if dense_model_path and image_model_path:
            dense_dim = self.__path_to_kwargs(dense_model_path).get("dim")
            image_dim = self.__path_to_kwargs(image_model_path).get("dim")
            if dense_dim != image_dim:
                msg: str = ("Dense and image embedder's dimension is mismatched. "
                            "Fail back to dense only.")
                LOGGER.warning(msg)
                warnings.warn(msg)
                image_model_path = None
        elif image_model_path:
            raise LocasException("LocalAssistant only support text retrieve images, "
                                 "not image retrieve image.")

        self.__init_embedder(dense_model_path, sparse_model_path, image_model_path)
        self.load_document_store(port)
        self.__init_retriever(top_k, score_threshold)

    def load_document_store(self, port: int):
        """Load the document store. Use to reload with a different embedding mode or dimension."""
        embedding_dim: int = Constant.DEFAULT_EMBEDDING_DIM

        dense_model = self.embedder.get(EmbeddingMode.DENSE.name)
        image_model = self.embedder.get(EmbeddingMode.IMAGE.name)
        if isinstance(dense_model, TextEmbedding):
            embedding_dim = dense_model.embedding_size
        elif isinstance(image_model, ImageEmbedding):
            embedding_dim = image_model.embedding_size
        LOGGER.info("Loaded document store with dim '%i'", embedding_dim)

        recreate_index: bool = False
        try:
            meta = UtilsMethod.read_json(PATH.docs / "meta.json")
            if isinstance(meta, dict):
                recreate_index = meta["collections"]["Document"]["vectors"]["size"] != embedding_dim
                if recreate_index:
                    LOGGER.info("Due to mismatched in past dimension size. Recreated the index.")
        except KeyError:
            pass

        self.document_store = QdrantDocumentStore(
            path=str(PATH.docs),
            port=port,
            embedding_dim=embedding_dim,
            recreate_index=recreate_index,
            use_sparse_embeddings=True,
        )

        if recreate_index:
            self.re_embed_all()

    def _embed(
        self,
        embedding_mode: EmbeddingMode,
        embed_input: str | list[Document] | list[PosixPath]
    ):
        LOGGER.debug("Embedded as %s for: %s", embedding_mode.name, embed_input)

        embedder: dict | None = self.embedder.get(embedding_mode.name)
        if embedder:
            if isinstance(embed_input, str): # just a single query
                match embedding_mode:
                    case EmbeddingMode.DENSE:
                        return list(embedder.embed(embed_input))[0].tolist()
                    case EmbeddingMode.SPARSE:
                        sparse_embed = list(embedder.embed(embed_input))[0]
                        return SparseEmbedding(indices=sparse_embed.indices.tolist(),
                                               values=sparse_embed.values.tolist())
            else: # are documents that need to be embedded
                match embedding_mode:
                    case EmbeddingMode.DENSE:
                        documents: list[Document] = embed_input #type:ignore
                        for document in documents:
                            if not isinstance(document, Document):
                                continue
                            if document.content:
                                document.embedding = list(
                                    embedder.embed(document.content)
                                )[0].tolist()
                    case EmbeddingMode.SPARSE:
                        documents: list[Document] = embed_input #type:ignore
                        for document in documents:
                            if not isinstance(document, Document):
                                continue
                            if document.content:
                                sparse_embed = list(
                                    embedder.embed(document.content)
                                )[0]
                                document.sparse_embedding = SparseEmbedding(
                                    indices=sparse_embed.indices.tolist(),
                                    values=sparse_embed.values.tolist()
                                )
                    case EmbeddingMode.IMAGE:
                        embed_input = list(map(str, filter( # `list[str]`
                            lambda embed: isinstance(embed, PosixPath), embed_input #type:ignore
                        )))
                        documents: list[Document] = ImageFileToDocument().run(
                            sources=embed_input # pyright: ignore[reportArgumentType]
                        ).get("documents", [])
                        if documents:
                            for index, embedded in enumerate(list(embedder.embed(embed_input))):
                                documents[index].embedding = embedded.tolist()
                return documents
        raise LocasException(f"Cannot embed '{embed_input}' as '{embedding_mode.name.lower()}'.")

    def get_all_docs(self) -> list[Document]:
        """Via the client, get the docs."""
        #pylint:disable=W0212:protected-access
        self.document_store._initialize_client()
        client = self.document_store._client
        if not client:
            return []

        haystack_documents: list[Document] = []

        next_offset: PointId | None = -1
        while next_offset:
            all_records, next_offset = client.scroll(
                collection_name=self.document_store.index,
                offset=next_offset,
                with_payload=True
            )

            for point in all_records:
                payload = point.payload
                if not payload:
                    continue

                doc = Document.from_dict(payload)
                haystack_documents.append(doc)

        LOGGER.info("Get all documents: %s", haystack_documents)
        return haystack_documents

    def write_docs(self, docs_paths: list[str], containing: bool = True) -> list:
        """Write the docs for further proceed."""
        if containing:
            contained_docs: list[str] = []
            for docs_path in docs_paths:
                path = Path(docs_path)
                if not path.exists():
                    continue
                contained_path = UtilsMethod.validate_filename(self.file_container / path.name)
                path.copy(contained_path)
                contained_docs.append(str(contained_path))
        else:
            contained_docs: list[str] = docs_paths
        del docs_paths

        analyzed_docs: dict = self.analyze_docs(contained_docs)

        documents: list[Document] = analyzed_docs.get("documents", [])

        if documents:
            if self.embedder.get(EmbeddingMode.DENSE.name):
                documents = self._embed(EmbeddingMode.DENSE, documents) #type:ignore
            if self.embedder.get(EmbeddingMode.SPARSE.name):
                documents = self._embed(EmbeddingMode.SPARSE, documents) #type:ignore
        if self.embedder.get(EmbeddingMode.IMAGE.name):
            documents += self._embed(
                EmbeddingMode.IMAGE, analyzed_docs.get("images", []) #type:ignore
            )

        if documents:
            documents = DocumentCleaner().run(documents).get("documents", [])
            self.document_store.write_documents(documents, DuplicatePolicy.OVERWRITE)

        LOGGER.info("Write documents: %s", documents)

        return analyzed_docs.get("unclassified", [])

    def retrieve(self, query: str) -> list:
        """Retrieve the content via text query.

        Args:
            query (str): The query.
        """
        if not self.retriever:
            raise LocasException("Cannot find the retriever model.")

        kwargs: dict = {}
        if self.embedder.get(EmbeddingMode.DENSE.name):
            kwargs.update({"query_embedding": \
                                self._embed(EmbeddingMode.DENSE, query)})
        if self.embedder.get(EmbeddingMode.SPARSE.name):
            kwargs.update({"query_sparse_embedding": \
                                self._embed(EmbeddingMode.SPARSE, query)})
        result = self.retriever.run(**kwargs)

        documents = result.get("documents", [])
        LOGGER.info("Retrieved document from '%s': %s", query, documents)
        return documents

    def retrieve_for_chat(self, query: str) -> dict:
        """Also retrieve the content for query, but specifically made for chatting

        Args:
            query (str): The query.
        """
        retrieved_docs = DocumentTypeRouter(
            mime_type_meta_field="mime_type",
            file_path_meta_field="file_path",
            mime_types=["image/.*"]
        ).run(self.retrieve(query))

        image_paths: list[Path] = list(map(
            lambda path: self.file_container / path, #type:ignore
            filter(
                lambda path: isinstance(path, str) and (self.file_container / path).exists(),
                [doc.meta.get("file_path") for doc in retrieved_docs.get("image/.*", [])]
            )
        ))

        return {
            "images": image_paths,
            "documents": retrieved_docs.get("unclassified", [])
        }

    def re_embed_all(self):
        """Make it freshly new"""
        LOGGER.info("Re-embed all documents.")
        self.document_store.delete_all_documents()

        docs_path = list(map(str, filter(
            lambda file: file.is_file(), self.file_container.iterdir()
        )))
        self.write_docs(docs_path, containing=False)

    def delete_docs(self, filename: str, doc_id: str):
        """Delete the document."""
        LOGGER.info("Delete document: %s", filename)
        doc_file = self.file_container / filename
        if doc_file.exists():
            doc_file.unlink()
        self.document_store.delete_documents([doc_id])

    def delete_all_docs(self):
        """Delete all documents."""
        LOGGER.info("Deleted all documents.")
        for doc_file in self.file_container.iterdir():
            if doc_file.is_file():
                doc_file.unlink()
                LOGGER.debug("Deleted document: %s", doc_file.name)
        self.document_store.delete_all_documents()

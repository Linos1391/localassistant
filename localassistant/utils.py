"""Utils file."""
import logging
import warnings
import shutil
from dataclasses import dataclass, fields, field
from enum import Enum
from pathlib import Path
from typing import Literal, Any
import os
import json

from fastembed import TextEmbedding, SparseTextEmbedding, ImageEmbedding

class LocasException(Exception):
    """For common errors in LocalAssistant"""

@dataclass
class PathConstant:
    """So that no more scare of variable disappearing (C ptsd)"""
    project: Path
    env: Path
    histories: Path
    models: Path
    docs: Path

    @staticmethod
    def init_path(max_step: int = 100):
        "Init the path, I make it here for more organized code."
        project_path: Path = Path(__file__).parent
        env_path: Path = project_path
        while env_path.name != ".venv": # goes back until reach .venv
            if max_step == 0:
                warnings.warn(f"Cannot detect '.venv', set main path to {project_path}. "
                              "Remember it is recommended to use the installer. ")
                env_path = project_path.parent / "local_venv"
                break
            env_path = env_path.parent
            max_step -= 1
        if env_path.name == ".venv":
            env_path = env_path.parent

        constant_path: PathConstant = PathConstant(
            project=project_path,
            env=env_path,
            histories=env_path / "histories",
            models=env_path / "models",
            docs=env_path / "docs",
        )
        for field_path in fields(constant_path):
            os.makedirs(getattr(constant_path, field_path.name), exist_ok=True)
        return constant_path
PATH: PathConstant = PathConstant.init_path()

LOGGER = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO,
                    filemode="w",
                    filename=PATH.env / "locas.log",
                    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')

class UIFiles:
    """All of the .ui files for managing."""
    # Main.
    APP = "app.ui"
    ERROR = "error.ui"

    # Chat tab.
    CHAT_USER = "chat_user.ui"
    CHAT_ASSISTANT = "chat_assistant.ui"

    # Download tab.
    DOWNLOAD_MODEL = "download_model.ui"

    # Setting tab.
    SETTING_MODEL = "setting_model.ui"

class Constant:
    """Easier to manage."""
    # ___For_treeview_button___
    BUTTON_DELETE = "Delete"
    BUTTON_DELETE_ALL = "Delete All"
    BUTTON_MINIMUM_WIDTH = 56

    # ___For_model_loading_button___
    BUTTON_LOAD_MODEL = "Load models"
    BUTTON_RELOAD_MODEL = "Reload models"
    BUTTON_UNLOAD_MODEL = "Unload models"

    # ___For_download_process___
    UNCLASSIFIED = "unclassified"

    # ___For_chat_function___
    NEW_HISTORY = "New History"
    STAR = "Star"
    UNSTAR = "Unstar"
    STAR_FORMAT = "(starred) {history_file}"
    STARRED_DIR = PATH.histories / "starred"

    DEFAULT_LLAMA_PORT = 8000

    TEMPLATE = (
        "Provide response with the following information (or access the tools for more)."
        "\n"
        "\nThese are the text-only documents:"
        "\n{%- if documents|length > 0 %}"
        "\n{%- for doc in documents %}"
        "\nText Document ({{ doc.meta.get('file_path') }}) [{{ loop.index }}] :"
        "\n{{ doc.content }}"
        "\n{% endfor -%}"
        "\n{%- else %}"
        "\nNo relevant text documents were found."
        "\n{% endif %}"
        "\nEnd of text documents."
        "\n"
        "\nYour current emotion: {{emotion}}."
        "\n"
        "\nQuery: {{query}}"
        "\n"
        "\nResponse:"
    )
    DEFAULT_SYSTEM_MESSAGE = (
        "Imagine being a supremely smart assistant that can do everything. Your task is to "
        "fulfill my satisfaction. Always assume that you are in the wrong and recheck "
        "the answer until it is accurate."
        "\n\n"
        "My input can be a question, or a statement solely given to you or someone else. "
        "Provide an appropriate answer to query, make it simple unless the query demand "
        "otherwise."
    )

    REQUIRED_SYSTEM_MESSAGE = (
        "\n\n"
        "You are built with emotion that was given via my input. Act on according to your "
        "emotion, or ignore if you do not understand the emotion. Do not mention the current "
        "emotion unless I told you so."
    )

    # ___For_agent_tools___
    INTERVAL_PER_SEARCH = 1.0 # second

    # ___For_docs_function___
    DEFAULT_QDRANT_PORT = 6333
    DEFAULT_EMBEDDING_DIM = 512
    DEFAULT_TOP_K = 5
    DEFAULT_SCORE_THRESHOLD = 0.5

    # ___For_setting___
    DEFAULT_MAX_CHAT_MESSAGE = 25
    DEFAULT_MAX_HISTORY = 5


@dataclass
class ModelMetadata:
    """The metadata for `ModelGuide`

    Args:
        tag: List of valid pipeline tags.
        role: Specific role in Locas.
        url: Where to install the models.
        glob: Glob syntax for searching, leave "*.gguf" to get all the GGUF files.
        allow_group: Via `get_models()`, only return those belong to this group.
                     If not specific, return everything as usual.
        is_multiple_combobox: Is multiple combo box. (for gui)
    """
    tag: list[str]
    role: list[str]
    url: str
    glob: Literal["", "*.gguf"] = ""
    allow_group: list = field(default_factory=list)
    is_multiple_combobox: bool = False

    @staticmethod
    def tag_to_models(tag: str, glob: str = "") -> list:
        """Give the tag, get the current existed models."""
        path: Path = PATH.models / tag
        if not path.exists():
            return []
        model_list: list[str] = []
        for repo_owner in path.iterdir():
            if not repo_owner.is_dir():
                continue
            for repo_model in repo_owner.iterdir():
                if glob:
                    model_list += list(map(str, map(lambda file: file.relative_to(path),
                                                    repo_model.glob(glob))))
                else:
                    model_list.append(os.path.join(repo_owner.name, repo_model.name))
        return model_list

    @staticmethod
    def define_allow_group(embedding: Any):
        """Cuz im too lazy, and do not repeat yourself u know."""
        #pylint:disable=W0212:protected-access
        assert embedding in (TextEmbedding, SparseTextEmbedding, ImageEmbedding), "?"
        return list(map(lambda model: model.sources.hf, embedding._list_supported_models()))

    def get_models(self) -> list[str]:
        """Authentic way to get all models serving this."""
        models: list[str] = ModelMetadata.tag_to_models(Constant.UNCLASSIFIED, self.glob)
        for tag in self.tag:
            models += ModelMetadata.tag_to_models(tag, self.glob)

        if self.allow_group:
            allowed_models: list[str] = []
            for model in models:
                if model in self.allow_group:
                    allowed_models.append(model)
            return allowed_models
        return models

class ModelGuide(Enum):
    """The guideline for model experts like me (type shi)"""
    AGENT = ModelMetadata(
        tag=["image-text-to-text"],
        role=["agent", "agent-mmproj"],
        url="https://huggingface.co/models?pipeline_tag=image-text-to-text&apps=llama.cpp",
        glob="*.gguf"
    )
    AGENT_LORA = ModelMetadata(
        tag=["image-text-to-text"],
        role=["agent-lora"],
        url="https://huggingface.co/blog/ngxson/gguf-my-lora",
        glob="*.gguf",
        is_multiple_combobox=True,
    )
    DOCS_DENSE = ModelMetadata(
        tag=["feature-extraction", "sentence-similarity"],
        role=["dense-embedder"],
        url=("https://qdrant.github.io/fastembed/examples/Supported_Models/#supported-text-"
             "embedding-models"),
        allow_group=ModelMetadata.define_allow_group(TextEmbedding)
    )
    DOCS_SPARSE = ModelMetadata(
        tag=["feature-extraction", "sentence-similarity"],
        role=["sparse-embedder"],
        url=("https://qdrant.github.io/fastembed/examples/Supported_Models/#supported-sparse-"
             "text-embedding-models"),
        allow_group=ModelMetadata.define_allow_group(SparseTextEmbedding)
    )
    DOCS_IMAGE = ModelMetadata(
        tag=["image-classification", "image-feature-extraction"],
        role=["image-embedder"],
        url=("https://qdrant.github.io/fastembed/examples/Supported_Models/#supported-image-"
             "embedding-models"),
        allow_group=ModelMetadata.define_allow_group(ImageEmbedding)
    )

class UtilsMethod:
    """Sum up all good stuffs."""
    @staticmethod
    def set_lower(tag: str):
        """Eg: `Text Generation` -> `text-generation`"""
        return tag.replace(" ", "-").lower()

    @staticmethod
    def set_upper(tag: str):
        """Eg: `text-generation` -> `Text Generation`"""
        return tag.replace("-", " ").title()

    @staticmethod
    def read_json(path: Path) -> dict | list:
        """Read json."""
        if not path.exists():
            return {}

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            f.close()
        LOGGER.debug("Read JSON: %s", path)
        return data

    @staticmethod
    def write_json(path: Path, data: dict | list) -> None:
        """Write json."""
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
            f.close()
        LOGGER.debug("Write JSON: %s", path)

    @staticmethod
    def validate_filename(file_path: Path):
        """Try again and again until its correct."""
        parent: Path = file_path.parent
        stem: str = file_path.stem
        ext: str = file_path.suffix

        while file_path.exists():
            try:
                index: int = int(stem.split("_")[-1])
            except ValueError:
                stem = f"{stem}_1"
            else:
                stem = f"{stem}_{index + 1}"
            finally:
                file_path = parent / f"{stem}{ext}"
        return file_path

    @staticmethod
    def delete_cache() -> None:
        """Just delete those yummy cache."""
        for walk_path in (PATH.env, PATH.project):
            for parent, folders, _ in walk_path.walk():
                for folder in folders:
                    if folder in ("__pycache__", ".cache", "tmp"):
                        path: Path =parent / folder
                        shutil.rmtree(path)
                        LOGGER.debug("Delete cache: %s", path)
        LOGGER.info("Complete deleting cache.")

class SettingKey:
    """No reason, just that my future self may thanks me later.""" #OMG TYSM WTF?????
    TOKEN = "token"
    THEME = "theme"
    LLAMA_CPP_BIN = "llama_cpp_bin"
    LLAMA_PORT = "llama_port"
    LLAMA_PORT_KILL = "llama_port_kill"
    MAX_CHAT_MESSAGE = "max_chat_message"
    MAX_HISTORY = "max_history"
    QDRANT_PORT = "qdrant_port"
    QDRANT_LOAD = "qdrant_load"
    TOP_K = "top_k"
    SCORE_THRESHOLD = "score_threshold"
    MODELS = "models"

class Setting:
    """Everything about setting."""
    def __init__(self) -> None:
        self.path: Path = PATH.env / "setting.json"
        self.data: dict = {}
        self.init_setting_file()

    def init_setting_file(self):
        """User can destroy it, user will destroy it."""
        LOGGER.debug("Init setting file: %s", self.path)
        if self.path.exists():
            self.get_setting_file()
        else:
            self.update_setting_file()

    def get_setting_file(self):
        """Get all data from `setting.json` file."""
        LOGGER.info("Load settings from %s", self.path)
        self.data.update(UtilsMethod.read_json(self.path))

    def update_setting_file(self):
        """Update all data into `setting.json` file."""
        LOGGER.info("Save settings to %s", self.path)
        UtilsMethod.write_json(self.path, self.data)

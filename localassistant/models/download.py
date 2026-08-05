"""Download model."""
import os
import logging
from pathlib import Path

from huggingface_hub import snapshot_download, hf_hub_download, model_info
from fastembed import TextEmbedding, SparseTextEmbedding, ImageEmbedding

from localassistant.utils import Constant, ModelGuide, UtilsMethod, PATH

LOGGER = logging.getLogger(__name__)

def download(repo_id: str, parent_dir: Path, token: str | None = None):
    """Download model from HuggingFace.

    Args:
        repo_id (str): Model repo. (Ex: meta-llama/Llama-3.2-1B-Instruct)
        parent_dir (Path): The dir where models are download to.
        token (str | None, optional): The token to be used. (Some repo need)
    """
    repo_id = repo_id.split()[-1]
    for (current, replace) in ((r"hf://", ""),
                               (r"https://", ""),
                               (r"huggingface.co/", ""),
                               (r"?show_file_info=", "/")):
        repo_id = repo_id.replace(current, replace)

    repo_split = repo_id.split("/")
    repo_file: str = ""
    if len(repo_split) > 2:
        repo_id = os.path.join(repo_split[0], repo_split[1])
        repo_file = repo_split[-1]
    del repo_split

    tag = model_info(repo_id, expand=["pipeline_tag"], token=token).pipeline_tag
    if not tag:
        tag = Constant.UNCLASSIFIED

    for (model_tag, embedding) in ((ModelGuide.DOCS_DENSE.value.tag, TextEmbedding),
                                   (ModelGuide.DOCS_SPARSE.value.tag, SparseTextEmbedding),
                                   (ModelGuide.DOCS_IMAGE.value.tag, ImageEmbedding)):
        if tag in model_tag:
            for model in embedding._list_supported_models(): #pylint:disable=W0212:protected-access
                if repo_id == model.model and model.sources.hf:
                    LOGGER.info("Found the FastEmbed model '%s', switch to '%s'",
                                repo_id, model.sources.hf)
                    repo_id = model.sources.hf
                    break

    kwargs: dict = {
        "repo_type": "model",
        "local_dir": parent_dir / tag / repo_id,
        "token": token,
        "force_download": True
    }
    if repo_file:
        hf_hub_download(repo_id, repo_file, **kwargs)
    else:
        snapshot_download(repo_id, **kwargs)
    UtilsMethod.delete_cache()

def download_starter_models():
    """Download starter models."""
    for model in (
        "unsloth/Qwen3.5-0.8B-GGUF/Qwen3.5-0.8B-BF16.gguf",
        "unsloth/Qwen3.5-0.8B-GGUF/mmproj-BF16.gguf",
        "Qdrant/clip-ViT-B-32-text",
        "Qdrant/bm25",
        "Qdrant/clip-ViT-B-32-vision"
    ):
        print(f"\nDownload {model}")
        download(model, parent_dir=PATH.models)

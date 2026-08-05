**Notice:** These are found and switchable within the Setting tabs. After the `locas_installer.py` script, all models are made available. (with the sole exception of [Agent LoRA](#agent-lora))

## Agent

The main Image Text to Text model used for communication, has to be gguf for compatible with Llama.cpp.

**Recommendation:** [unsloth/Qwen3.5-0.8B-GGUF/Qwen3.5-0.8B-BF16.gguf](https://huggingface.co/unsloth/Qwen3.5-0.8B-GGUF/blob/main/Qwen3.5-0.8B-BF16.gguf).

*(Choose other models from [here](https://huggingface.co/models?pipeline_tag=image-text-to-text&apps=llama.cpp).)*


## Agent Mmproj

The mmproj of the Image Text to Text model, essential for vision-enabled agent, has to be gguf for compatible with Llama.cpp.

**Recommendation:** [unsloth/Qwen3.5-0.8B-GGUF/mmproj-BF16.gguf](https://huggingface.co/unsloth/Qwen3.5-0.8B-GGUF/blob/main/mmproj-BF16.gguf).

*(Choose other models from [here](https://huggingface.co/models?pipeline_tag=image-text-to-text&apps=llama.cpp).)*


## Agent Lora

The LoRA for the Image Text to Text model, for easily modifying the agent, has to be gguf for compatible with Llama.cpp.

**Recommendation:** None.

*(Make your own LoRA from [here](https://huggingface.co/blog/ngxson/gguf-my-lora).)*


## Dense Embedder

Fastembed dense text embedder, should only in the supported list.

**Recommendation:** [Qdrant/clip-ViT-B-32-text](https://huggingface.co/Qdrant/clip-ViT-B-32-text).

*(Choose other models from [here](https://qdrant.github.io/fastembed/examples/Supported_Models/#supported-text-embedding-models).)*


## Sparse Embedder

Fastembed sparse text embedder, should only in the supported list.

**Recommendation:** [Qdrant/bm25](https://huggingface.co/Qdrant/bm25).

*(Choose other models from [here](https://qdrant.github.io/fastembed/examples/Supported_Models/#supported-sparse-text-embedding-models).)*


## Image Embedder

Fastembed image embedder, currently only support multimodel (text retrieve image) since unimodel(image retrieve image) is too expensive, should only in the supported list.

**Recommendation:** [Qdrant/clip-ViT-B-32-vision](https://huggingface.co/Qdrant/clip-ViT-B-32-vision).

*(Choose other models from [here](https://qdrant.github.io/fastembed/examples/Supported_Models/#supported-image-embedding-models).)*
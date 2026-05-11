"""
Tools Universe — the operational catalog of 300+ tools the Auto-Coder can
**actually activate, invoke and combine**.

This is the *upgraded* successor of the bare list-of-strings `tools_registry.py`.
Each entry carries real metadata:

  • category, type (lib_py / lib_js / cli / service_free / service_paid / infra / runtime / info)
  • install_cmd        — exact shell command to install (or None if managed-service)
  • env_keys           — env vars / credentials the tool needs (resolved via credentials_vault)
  • docs_url           — canonical docs link
  • invoke_hint        — one-line "how to actually use it" snippet

The AI gets six new callable tools:

  1. tool_universe_search    — search the catalog by keyword / category
  2. tool_universe_info      — full metadata for a single tool
  3. tool_universe_install   — actually run the install command (uses run_command)
  4. tool_universe_status    — installed? configured? what's missing?
  5. tool_universe_plan      — generate a multi-tool execution plan for a goal
  6. tool_universe_credentials_required — list every tool that still needs a key

Plus credential vault helpers (vault_get/set/list/delete) wired up as AI tools.
"""
from __future__ import annotations
import os
import re
import shutil
import asyncio
import importlib
import importlib.util
from typing import Any, Dict, List, Optional, Tuple

from .credentials_vault import vault_get, vault_set, vault_delete, vault_list

# ────────────────────────────────────────────────────────────────────────
# Catalog data model
# ────────────────────────────────────────────────────────────────────────
#   type:
#     lib_py        — Python library (pip install)
#     lib_js        — JS/TS library (yarn add)
#     cli           — CLI binary (apt-get / curl install)
#     service_free  — hosted service, has free tier (may need signup key)
#     service_paid  — hosted service, paid (always needs key)
#     framework     — multi-step / multi-package framework
#     runtime       — language runtime / container engine
#     infra         — infrastructure (DBs, queues, search engines)
#     info          — reference/knowledge only (no install path here)

CATALOG: Dict[str, Dict[str, Any]] = {}


def _t(id_: str, name: str, category: str, type_: str,
       install: Optional[str] = None, keys: Optional[List[str]] = None,
       docs: Optional[str] = None, hint: Optional[str] = None,
       check: Optional[str] = None, runtime: Optional[str] = None,
       free: bool = True) -> None:
    """Register a tool in the catalog (compact form)."""
    CATALOG[id_.lower()] = {
        "id": id_.lower(),
        "name": name,
        "category": category,
        "type": type_,
        "install_cmd": install,
        "check_cmd": check,           # shell cmd to verify installed
        "env_keys": keys or [],
        "docs_url": docs,
        "invoke_hint": hint,
        "runtime": runtime,           # python / node / shell / web
        "free": free,
    }


# ════════════════════════════════════════════════════════════════════════
# 🤖 LLM PROVIDERS  (need API keys — service_paid/free)
# ════════════════════════════════════════════════════════════════════════
_t("openai", "OpenAI (GPT-5.5/4o/o3)", "LLM Providers", "lib_py",
   install="pip install openai", keys=["OPENAI_API_KEY"],
   docs="https://platform.openai.com/docs", free=False,
   hint="from openai import OpenAI; OpenAI().chat.completions.create(model='gpt-4o',messages=[…])")
_t("anthropic", "Anthropic Claude (Sonnet 4.5/Opus/Haiku)", "LLM Providers", "lib_py",
   install="pip install anthropic", keys=["ANTHROPIC_API_KEY"], free=False,
   docs="https://docs.anthropic.com",
   hint="anthropic.Anthropic().messages.create(model='claude-sonnet-4-20250514',…)")
_t("gemini", "Google Gemini (2.5 Flash/Pro, 3 Pro)", "LLM Providers", "lib_py",
   install="pip install google-genai", keys=["GEMINI_API_KEY"], free=True,
   docs="https://ai.google.dev/gemini-api/docs",
   hint="genai.Client(api_key=KEY).models.generate_content(model='gemini-2.5-flash',contents=…)")
_t("groq", "Groq (Llama 3.3 70B, Mixtral)", "LLM Providers", "lib_py",
   install="pip install groq", keys=["GROQ_API_KEY"], free=True,
   docs="https://console.groq.com/docs",
   hint="Groq().chat.completions.create(model='llama-3.3-70b-versatile',…)")
_t("mistral", "Mistral AI (Large, Codestral)", "LLM Providers", "lib_py",
   install="pip install mistralai", keys=["MISTRAL_API_KEY"], free=False,
   docs="https://docs.mistral.ai")
_t("deepseek", "DeepSeek (V3, Coder)", "LLM Providers", "service_paid",
   keys=["DEEPSEEK_API_KEY"], docs="https://platform.deepseek.com", free=False,
   hint="OpenAI-compatible: base_url='https://api.deepseek.com/v1'")
_t("cohere", "Cohere (Command R+, Embed v3)", "LLM Providers", "lib_py",
   install="pip install cohere", keys=["COHERE_API_KEY"], free=False,
   docs="https://docs.cohere.com")
_t("xai-grok", "xAI Grok (Grok-2/3)", "LLM Providers", "service_paid",
   keys=["XAI_API_KEY"], free=False, docs="https://docs.x.ai",
   hint="OpenAI-compatible: base_url='https://api.x.ai/v1'")
_t("perplexity", "Perplexity Sonar", "LLM Providers", "service_paid",
   keys=["PPLX_API_KEY"], free=False, docs="https://docs.perplexity.ai")
_t("you.com", "You.com Smart/Genius", "LLM Providers", "service_paid",
   keys=["YOU_API_KEY"], free=False, docs="https://documentation.you.com")
_t("poe", "Poe multi-model", "LLM Providers", "service_paid",
   keys=["POE_API_KEY"], free=False, docs="https://creator.poe.com")

# ════════════════════════════════════════════════════════════════════════
# 🚪 LLM GATEWAYS & ROUTERS
# ════════════════════════════════════════════════════════════════════════
_t("openrouter", "OpenRouter (300+ models)", "LLM Gateways", "service_paid",
   keys=["OPENROUTER_API_KEY"], free=False, docs="https://openrouter.ai/docs",
   hint="OpenAI-compatible: base_url='https://openrouter.ai/api/v1'")
_t("together", "Together AI (open-source)", "LLM Gateways", "lib_py",
   install="pip install together", keys=["TOGETHER_API_KEY"], free=False,
   docs="https://docs.together.ai")
_t("replicate", "Replicate (any model as API)", "LLM Gateways", "lib_py",
   install="pip install replicate", keys=["REPLICATE_API_TOKEN"], free=False,
   docs="https://replicate.com/docs")
_t("baseten", "Baseten (deploy custom models)", "LLM Gateways", "lib_py",
   install="pip install baseten", keys=["BASETEN_API_KEY"], free=False,
   docs="https://docs.baseten.co")
_t("fireworks", "Fireworks AI (fast inference)", "LLM Gateways", "lib_py",
   install="pip install fireworks-ai", keys=["FIREWORKS_API_KEY"], free=False,
   docs="https://docs.fireworks.ai")
_t("inference.net", "Inference.net (cheap GPU)", "LLM Gateways", "service_paid",
   keys=["INFERENCE_API_KEY"], free=False, docs="https://inference.net/docs")
_t("huggingface", "Hugging Face Hub + Inference", "LLM Gateways", "lib_py",
   install="pip install huggingface_hub", keys=["HF_TOKEN"], free=True,
   docs="https://huggingface.co/docs")
_t("litellm", "LiteLLM router/proxy", "LLM Gateways", "lib_py",
   install="pip install litellm", docs="https://docs.litellm.ai",
   hint="from litellm import completion; completion(model='gpt-4o',messages=[…])")
_t("portkey", "Portkey AI Gateway", "LLM Gateways", "lib_py",
   install="pip install portkey-ai", keys=["PORTKEY_API_KEY"], free=False,
   docs="https://docs.portkey.ai")
_t("cloudflare-ai-gw", "Cloudflare AI Gateway", "LLM Gateways", "service_free",
   keys=["CLOUDFLARE_API_TOKEN", "CLOUDFLARE_ACCOUNT_ID"], free=True,
   docs="https://developers.cloudflare.com/ai-gateway")

# ════════════════════════════════════════════════════════════════════════
# 🤖 AGENT FRAMEWORKS
# ════════════════════════════════════════════════════════════════════════
_t("langchain", "LangChain", "Agent Frameworks", "lib_py",
   install="pip install langchain langchain-core langchain-community",
   docs="https://python.langchain.com")
_t("langgraph", "LangGraph", "Agent Frameworks", "lib_py",
   install="pip install langgraph", docs="https://langchain-ai.github.io/langgraph")
_t("langsmith", "LangSmith (tracing)", "Agent Frameworks", "lib_py",
   install="pip install langsmith", keys=["LANGSMITH_API_KEY"], free=True,
   docs="https://docs.smith.langchain.com")
_t("llamaindex", "LlamaIndex", "Agent Frameworks", "lib_py",
   install="pip install llama-index", docs="https://docs.llamaindex.ai")
_t("haystack", "Haystack", "Agent Frameworks", "lib_py",
   install="pip install haystack-ai", docs="https://docs.haystack.deepset.ai")
_t("crewai", "CrewAI", "Agent Frameworks", "lib_py",
   install="pip install crewai", docs="https://docs.crewai.com")
_t("autogen", "Microsoft AutoGen", "Agent Frameworks", "lib_py",
   install="pip install pyautogen", docs="https://microsoft.github.io/autogen")
_t("semantic-kernel", "Semantic Kernel", "Agent Frameworks", "lib_py",
   install="pip install semantic-kernel", docs="https://learn.microsoft.com/semantic-kernel")
_t("dspy", "DSPy", "Agent Frameworks", "lib_py",
   install="pip install dspy-ai", docs="https://dspy-docs.vercel.app")
_t("pydanticai", "PydanticAI", "Agent Frameworks", "lib_py",
   install="pip install pydantic-ai", docs="https://ai.pydantic.dev")
_t("openai-agents", "OpenAI Agents SDK", "Agent Frameworks", "lib_py",
   install="pip install openai-agents", keys=["OPENAI_API_KEY"], free=False,
   docs="https://openai.github.io/openai-agents-python")
_t("mastra", "Mastra AI", "Agent Frameworks", "lib_js",
   install="yarn add @mastra/core", docs="https://mastra.ai/docs")
_t("superagi", "SuperAGI", "Agent Frameworks", "info",
   docs="https://superagi.com")
_t("agentgpt", "AgentGPT", "Agent Frameworks", "info",
   docs="https://docs.reworkd.ai")
_t("babyagi", "BabyAGI", "Agent Frameworks", "info",
   docs="https://github.com/yoheinakajima/babyagi")
_t("metagpt", "MetaGPT", "Agent Frameworks", "lib_py",
   install="pip install metagpt", docs="https://docs.deepwisdom.ai")
_t("camel", "CAMEL AI", "Agent Frameworks", "lib_py",
   install="pip install camel-ai", docs="https://docs.camel-ai.org")
_t("openagents", "OpenAgents", "Agent Frameworks", "info",
   docs="https://github.com/xlang-ai/OpenAgents")
_t("swarms", "Swarms AI", "Agent Frameworks", "lib_py",
   install="pip install swarms", docs="https://docs.swarms.world")
_t("autogpt", "AutoGPT", "Agent Frameworks", "info",
   docs="https://docs.agpt.co")
_t("openhands", "OpenHands (OpenDevin)", "Agent Frameworks", "info",
   docs="https://docs.all-hands.dev")

# ════════════════════════════════════════════════════════════════════════
# 💻 AI CODE ASSISTANTS  (mostly IDE plugins / hosted apps — info only)
# ════════════════════════════════════════════════════════════════════════
for _id, _nm, _docs in [
    ("continue.dev", "Continue.dev", "https://docs.continue.dev"),
    ("aider", "Aider", "https://aider.chat"),
    ("cursor", "Cursor IDE", "https://docs.cursor.com"),
    ("windsurf", "Windsurf IDE", "https://docs.codeium.com/windsurf"),
    ("copilot", "GitHub Copilot", "https://docs.github.com/copilot"),
    ("codeium", "Codeium", "https://codeium.com/docs"),
    ("tabnine", "Tabnine", "https://docs.tabnine.com"),
    ("cody", "Sourcegraph Cody", "https://sourcegraph.com/docs/cody"),
    ("blackbox", "Blackbox AI", "https://docs.blackbox.ai"),
    ("mutableai", "Mutable AI", "https://mutable.ai/docs"),
    ("sweepai", "Sweep AI", "https://docs.sweep.dev"),
    ("gpt-engineer", "GPT Engineer", "https://gptengineer.app"),
    ("smol-developer", "Smol Developer", "https://github.com/smol-ai/developer"),
    ("open-interpreter", "Open Interpreter", "https://docs.openinterpreter.com"),
    ("devin", "Devin AI", "https://docs.devin.ai"),
    ("opendevin", "OpenDevin", "https://docs.all-hands.dev"),
    ("replit", "Replit AI", "https://docs.replit.com"),
    ("bolt.new", "Bolt.new", "https://bolt.new"),
    ("lovable", "Lovable", "https://lovable.dev"),
    ("v0", "v0 by Vercel", "https://v0.dev/docs"),
]:
    _t(_id, _nm, "AI Code Assistants", "info", docs=_docs)

# Aider is installable
CATALOG["aider"].update({"type": "lib_py", "install_cmd": "pip install aider-chat"})

# ════════════════════════════════════════════════════════════════════════
# 🖥️ DEV ENVIRONMENTS & NOTEBOOKS
# ════════════════════════════════════════════════════════════════════════
_t("jupyter", "JupyterLab", "Dev Environments", "lib_py",
   install="pip install jupyterlab", docs="https://docs.jupyter.org",
   check="jupyter --version")
_t("colab", "Google Colab", "Dev Environments", "info",
   docs="https://colab.research.google.com")
_t("kaggle", "Kaggle Notebooks", "Dev Environments", "info",
   docs="https://www.kaggle.com/docs/notebooks")
_t("vscode", "VS Code", "Dev Environments", "info", docs="https://code.visualstudio.com/docs")
_t("jetbrains", "JetBrains IDEs", "Dev Environments", "info", docs="https://www.jetbrains.com")
_t("neovim", "NeoVim", "Dev Environments", "cli",
   install="apt-get install -y neovim", check="nvim --version", docs="https://neovim.io/doc")

# ════════════════════════════════════════════════════════════════════════
# 🧠 LOCAL / SELF-HOSTED LLM RUNTIMES
# ════════════════════════════════════════════════════════════════════════
_t("ollama", "Ollama", "Local LLM Runtimes", "cli",
   install="curl -fsSL https://ollama.com/install.sh | sh",
   check="ollama --version", docs="https://github.com/ollama/ollama")
_t("lm-studio", "LM Studio", "Local LLM Runtimes", "info", docs="https://lmstudio.ai")
_t("open-webui", "Open WebUI", "Local LLM Runtimes", "cli",
   install="pip install open-webui", check="open-webui --version",
   docs="https://docs.openwebui.com")
_t("anythingllm", "AnythingLLM", "Local LLM Runtimes", "info", docs="https://docs.anythingllm.com")
_t("librechat", "LibreChat", "Local LLM Runtimes", "info", docs="https://www.librechat.ai/docs")
_t("jan", "Jan AI", "Local LLM Runtimes", "info", docs="https://jan.ai/docs")
_t("vllm", "vLLM", "Local LLM Runtimes", "lib_py",
   install="pip install vllm", docs="https://docs.vllm.ai")
_t("llama.cpp", "llama.cpp", "Local LLM Runtimes", "cli",
   install="apt-get install -y build-essential cmake && git clone https://github.com/ggerganov/llama.cpp && cd llama.cpp && make",
   docs="https://github.com/ggerganov/llama.cpp")
_t("gpt4all", "GPT4All", "Local LLM Runtimes", "lib_py",
   install="pip install gpt4all", docs="https://docs.gpt4all.io")
_t("flowise", "Flowise", "Local LLM Runtimes", "cli",
   install="npm install -g flowise", check="flowise --version", docs="https://docs.flowiseai.com")
_t("dify", "Dify", "Local LLM Runtimes", "info", docs="https://docs.dify.ai")
_t("langflow", "Langflow", "Local LLM Runtimes", "lib_py",
   install="pip install langflow", docs="https://docs.langflow.org")

# ════════════════════════════════════════════════════════════════════════
# 🛡️ LLM OPS / EVAL / GUARDRAILS
# ════════════════════════════════════════════════════════════════════════
_t("humanloop", "Humanloop", "LLM Ops & Eval", "lib_py",
   install="pip install humanloop", keys=["HUMANLOOP_API_KEY"], free=False, docs="https://docs.humanloop.com")
_t("promptlayer", "PromptLayer", "LLM Ops & Eval", "lib_py",
   install="pip install promptlayer", keys=["PROMPTLAYER_API_KEY"], free=True, docs="https://docs.promptlayer.com")
_t("promptfoo", "Promptfoo", "LLM Ops & Eval", "cli",
   install="npm install -g promptfoo", check="promptfoo --version", docs="https://www.promptfoo.dev/docs")
_t("ragas", "Ragas", "LLM Ops & Eval", "lib_py",
   install="pip install ragas", docs="https://docs.ragas.io")
_t("deepeval", "DeepEval", "LLM Ops & Eval", "lib_py",
   install="pip install deepeval", docs="https://docs.confident-ai.com")
_t("trulens", "TruLens", "LLM Ops & Eval", "lib_py",
   install="pip install trulens-eval", docs="https://www.trulens.org")
_t("guardrails-ai", "Guardrails AI", "LLM Ops & Eval", "lib_py",
   install="pip install guardrails-ai", docs="https://www.guardrailsai.com")
_t("outlines", "Outlines (structured gen)", "LLM Ops & Eval", "lib_py",
   install="pip install outlines", docs="https://dottxt-ai.github.io/outlines")
_t("instructor", "Instructor (structured)", "LLM Ops & Eval", "lib_py",
   install="pip install instructor", docs="https://python.useinstructor.com")

# ════════════════════════════════════════════════════════════════════════
# 🧮 ML / DL FRAMEWORKS
# ════════════════════════════════════════════════════════════════════════
_t("pytorch", "PyTorch", "ML/DL Frameworks", "lib_py",
   install="pip install torch torchvision torchaudio", docs="https://pytorch.org/docs")
_t("tensorflow", "TensorFlow", "ML/DL Frameworks", "lib_py",
   install="pip install tensorflow", docs="https://www.tensorflow.org/api_docs")
_t("keras", "Keras", "ML/DL Frameworks", "lib_py",
   install="pip install keras", docs="https://keras.io")
_t("jax", "JAX", "ML/DL Frameworks", "lib_py",
   install="pip install jax", docs="https://jax.readthedocs.io")
_t("onnx", "ONNX", "ML/DL Frameworks", "lib_py",
   install="pip install onnx onnxruntime", docs="https://onnx.ai")
_t("cuda", "NVIDIA CUDA", "ML/DL Frameworks", "info", docs="https://docs.nvidia.com/cuda")
_t("tensorrt", "TensorRT", "ML/DL Frameworks", "info", docs="https://docs.nvidia.com/deeplearning/tensorrt")
_t("openvino", "OpenVINO", "ML/DL Frameworks", "lib_py",
   install="pip install openvino", docs="https://docs.openvino.ai")
_t("triton", "Triton Inference Server", "ML/DL Frameworks", "info", docs="https://docs.nvidia.com/deeplearning/triton-inference-server")
_t("wandb", "Weights & Biases", "ML/DL Frameworks", "lib_py",
   install="pip install wandb", keys=["WANDB_API_KEY"], free=True, docs="https://docs.wandb.ai")
_t("mlflow", "MLflow", "ML/DL Frameworks", "lib_py",
   install="pip install mlflow", docs="https://mlflow.org/docs/latest")
_t("clearml", "ClearML", "ML/DL Frameworks", "lib_py",
   install="pip install clearml", keys=["CLEARML_API_HOST", "CLEARML_API_ACCESS_KEY", "CLEARML_API_SECRET_KEY"], free=True, docs="https://clear.ml/docs")
_t("comet", "Comet ML", "ML/DL Frameworks", "lib_py",
   install="pip install comet_ml", keys=["COMET_API_KEY"], free=True, docs="https://www.comet.com/docs")

# ════════════════════════════════════════════════════════════════════════
# 🔤 NLP & EMBEDDINGS
# ════════════════════════════════════════════════════════════════════════
_t("fastembed", "FastEmbed", "NLP & Embeddings", "lib_py",
   install="pip install fastembed", docs="https://qdrant.github.io/fastembed")
_t("sentence-transformers", "Sentence Transformers", "NLP & Embeddings", "lib_py",
   install="pip install sentence-transformers", docs="https://www.sbert.net")
_t("spacy", "spaCy", "NLP & Embeddings", "lib_py",
   install="pip install spacy", docs="https://spacy.io/api")
_t("nltk", "NLTK", "NLP & Embeddings", "lib_py",
   install="pip install nltk", docs="https://www.nltk.org")
_t("gensim", "Gensim", "NLP & Embeddings", "lib_py",
   install="pip install gensim", docs="https://radimrehurek.com/gensim")

# ════════════════════════════════════════════════════════════════════════
# 🗃️ VECTOR DBs & SEARCH
# ════════════════════════════════════════════════════════════════════════
_t("faiss", "FAISS", "Vector Databases", "lib_py",
   install="pip install faiss-cpu", docs="https://faiss.ai")
_t("annoy", "Annoy", "Vector Databases", "lib_py",
   install="pip install annoy", docs="https://github.com/spotify/annoy")
_t("pinecone", "Pinecone", "Vector Databases", "lib_py",
   install="pip install pinecone-client", keys=["PINECONE_API_KEY"], free=True, docs="https://docs.pinecone.io")
_t("qdrant", "Qdrant", "Vector Databases", "lib_py",
   install="pip install qdrant-client", docs="https://qdrant.tech/documentation")
_t("weaviate", "Weaviate", "Vector Databases", "lib_py",
   install="pip install weaviate-client", docs="https://weaviate.io/developers")
_t("milvus", "Milvus", "Vector Databases", "lib_py",
   install="pip install pymilvus", docs="https://milvus.io/docs")
_t("chromadb", "ChromaDB", "Vector Databases", "lib_py",
   install="pip install chromadb", docs="https://docs.trychroma.com")
_t("redis-vss", "Redis Vector Similarity", "Vector Databases", "lib_py",
   install="pip install redis", docs="https://redis.io/docs/stack/search/reference/vectors")
_t("pgvector", "pgvector", "Vector Databases", "lib_py",
   install="pip install pgvector psycopg2-binary", docs="https://github.com/pgvector/pgvector")

_t("elasticsearch", "Elasticsearch", "Search Engines", "lib_py",
   install="pip install elasticsearch", docs="https://www.elastic.co/guide")
_t("opensearch", "OpenSearch", "Search Engines", "lib_py",
   install="pip install opensearch-py", docs="https://opensearch.org/docs")
_t("meilisearch", "Meilisearch", "Search Engines", "lib_py",
   install="pip install meilisearch", docs="https://www.meilisearch.com/docs")
_t("typesense", "Typesense", "Search Engines", "lib_py",
   install="pip install typesense", docs="https://typesense.org/docs")
_t("algolia", "Algolia", "Search Engines", "lib_py",
   install="pip install algoliasearch", keys=["ALGOLIA_APP_ID", "ALGOLIA_API_KEY"], free=True, docs="https://www.algolia.com/doc")

# ════════════════════════════════════════════════════════════════════════
# 🛢️ DATABASES
# ════════════════════════════════════════════════════════════════════════
_t("postgresql", "PostgreSQL", "Databases", "lib_py",
   install="pip install psycopg2-binary asyncpg", docs="https://www.postgresql.org/docs",
   keys=["DATABASE_URL"])
_t("mongodb", "MongoDB", "Databases", "lib_py",
   install="pip install motor pymongo", docs="https://www.mongodb.com/docs", keys=["MONGO_URL"])
_t("mysql", "MySQL", "Databases", "lib_py",
   install="pip install pymysql", docs="https://dev.mysql.com/doc")
_t("redis", "Redis", "Databases", "lib_py",
   install="pip install redis", docs="https://redis.io/docs", keys=["REDIS_URL"])
_t("supabase", "Supabase", "Databases", "lib_py",
   install="pip install supabase", keys=["SUPABASE_URL", "SUPABASE_KEY"], free=True, docs="https://supabase.com/docs")
_t("firebase", "Firebase", "Databases", "lib_py",
   install="pip install firebase-admin", keys=["FIREBASE_CREDENTIALS_JSON"], free=True, docs="https://firebase.google.com/docs")
_t("appwrite", "Appwrite", "Databases", "lib_py",
   install="pip install appwrite", keys=["APPWRITE_ENDPOINT", "APPWRITE_PROJECT_ID", "APPWRITE_API_KEY"], free=True, docs="https://appwrite.io/docs")
_t("pocketbase", "PocketBase", "Databases", "cli",
   install="curl -L https://github.com/pocketbase/pocketbase/releases/latest/download/pocketbase_linux_amd64.zip -o /tmp/pb.zip && unzip -o /tmp/pb.zip -d /usr/local/bin",
   check="pocketbase --version", docs="https://pocketbase.io/docs")
_t("planetscale", "PlanetScale", "Databases", "service_paid",
   keys=["PLANETSCALE_DATABASE_URL"], free=False, docs="https://planetscale.com/docs")
_t("neon", "Neon (serverless Postgres)", "Databases", "service_free",
   keys=["NEON_DATABASE_URL"], free=True, docs="https://neon.tech/docs")
_t("prisma", "Prisma ORM", "Databases", "lib_js",
   install="yarn add prisma @prisma/client", docs="https://www.prisma.io/docs")
_t("drizzle", "Drizzle ORM", "Databases", "lib_js",
   install="yarn add drizzle-orm", docs="https://orm.drizzle.team/docs")

# ════════════════════════════════════════════════════════════════════════
# 🐳 DEVOPS & IAC
# ════════════════════════════════════════════════════════════════════════
_t("docker", "Docker", "DevOps & IaC", "cli",
   check="docker --version", install="curl -fsSL https://get.docker.com | sh",
   docs="https://docs.docker.com")
_t("kubernetes", "Kubernetes", "DevOps & IaC", "cli",
   install="curl -LO https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl && install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl",
   check="kubectl version --client", docs="https://kubernetes.io/docs")
_t("helm", "Helm", "DevOps & IaC", "cli",
   install="curl https://baltocdn.com/helm/signing.asc | gpg --dearmor | tee /usr/share/keyrings/helm.gpg > /dev/null && echo 'deb [arch=amd64 signed-by=/usr/share/keyrings/helm.gpg] https://baltocdn.com/helm/stable/debian/ all main' | tee /etc/apt/sources.list.d/helm-stable-debian.list && apt-get update && apt-get install -y helm",
   check="helm version", docs="https://helm.sh/docs")
_t("terraform", "Terraform", "DevOps & IaC", "cli",
   install="apt-get install -y wget gnupg software-properties-common && wget -O- https://apt.releases.hashicorp.com/gpg | gpg --dearmor | tee /usr/share/keyrings/hashicorp-archive-keyring.gpg && apt-get update && apt-get install -y terraform",
   check="terraform --version", docs="https://developer.hashicorp.com/terraform/docs")
_t("pulumi", "Pulumi", "DevOps & IaC", "cli",
   install="curl -fsSL https://get.pulumi.com | sh", check="pulumi version",
   docs="https://www.pulumi.com/docs")
_t("ansible", "Ansible", "DevOps & IaC", "lib_py",
   install="pip install ansible", check="ansible --version", docs="https://docs.ansible.com")
_t("jenkins", "Jenkins", "DevOps & IaC", "info", docs="https://www.jenkins.io/doc")
_t("github-actions", "GitHub Actions", "DevOps & IaC", "info", docs="https://docs.github.com/actions")
_t("gitlab-ci", "GitLab CI/CD", "DevOps & IaC", "info", docs="https://docs.gitlab.com/ee/ci")
_t("argocd", "Argo CD", "DevOps & IaC", "info", docs="https://argo-cd.readthedocs.io")

# ════════════════════════════════════════════════════════════════════════
# 📊 OBSERVABILITY
# ════════════════════════════════════════════════════════════════════════
_t("prometheus", "Prometheus", "Observability", "info", docs="https://prometheus.io/docs")
_t("grafana", "Grafana", "Observability", "info", docs="https://grafana.com/docs")
_t("datadog", "Datadog", "Observability", "lib_py",
   install="pip install datadog ddtrace", keys=["DD_API_KEY"], free=False, docs="https://docs.datadoghq.com")
_t("sentry", "Sentry", "Observability", "lib_py",
   install="pip install sentry-sdk", keys=["SENTRY_DSN"], free=True, docs="https://docs.sentry.io")
_t("opentelemetry", "OpenTelemetry", "Observability", "lib_py",
   install="pip install opentelemetry-api opentelemetry-sdk", docs="https://opentelemetry.io/docs")
_t("jaeger", "Jaeger", "Observability", "info", docs="https://www.jaegertracing.io/docs")
_t("zipkin", "Zipkin", "Observability", "info", docs="https://zipkin.io")
_t("loki", "Grafana Loki", "Observability", "info", docs="https://grafana.com/docs/loki")
_t("victoriametrics", "VictoriaMetrics", "Observability", "info", docs="https://docs.victoriametrics.com")

# ════════════════════════════════════════════════════════════════════════
# ☁️ CLOUD PLATFORMS & DEPLOYMENT
# ════════════════════════════════════════════════════════════════════════
_t("aws", "AWS (boto3)", "Cloud Platforms", "lib_py",
   install="pip install boto3", keys=["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_REGION"], free=False,
   docs="https://docs.aws.amazon.com")
_t("gcp", "Google Cloud", "Cloud Platforms", "lib_py",
   install="pip install google-cloud-storage google-cloud-aiplatform",
   keys=["GOOGLE_APPLICATION_CREDENTIALS"], free=False, docs="https://cloud.google.com/docs")
_t("azure", "Microsoft Azure", "Cloud Platforms", "lib_py",
   install="pip install azure-identity azure-storage-blob",
   keys=["AZURE_CLIENT_ID", "AZURE_TENANT_ID", "AZURE_CLIENT_SECRET"], free=False, docs="https://learn.microsoft.com/azure")
_t("bedrock", "Amazon Bedrock", "Cloud Platforms", "lib_py",
   install="pip install boto3", keys=["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"], free=False,
   docs="https://docs.aws.amazon.com/bedrock")
_t("vertex-ai", "Google Vertex AI", "Cloud Platforms", "lib_py",
   install="pip install google-cloud-aiplatform", keys=["GOOGLE_APPLICATION_CREDENTIALS"], free=False,
   docs="https://cloud.google.com/vertex-ai/docs")
_t("azure-ai", "Azure AI", "Cloud Platforms", "lib_py",
   install="pip install azure-ai-ml", keys=["AZURE_OPENAI_API_KEY", "AZURE_OPENAI_ENDPOINT"], free=False,
   docs="https://learn.microsoft.com/azure/ai-services")
_t("cloudflare", "Cloudflare API", "Cloud Platforms", "lib_py",
   install="pip install cloudflare", keys=["CLOUDFLARE_API_TOKEN"], free=True, docs="https://developers.cloudflare.com")
_t("cloudflare-workers", "Cloudflare Workers", "Cloud Platforms", "cli",
   install="npm install -g wrangler", check="wrangler --version", keys=["CLOUDFLARE_API_TOKEN"], free=True,
   docs="https://developers.cloudflare.com/workers")
_t("vercel", "Vercel", "Cloud Platforms", "cli",
   install="npm install -g vercel", check="vercel --version", keys=["VERCEL_TOKEN"], free=True, docs="https://vercel.com/docs")
_t("netlify", "Netlify", "Cloud Platforms", "cli",
   install="npm install -g netlify-cli", check="netlify --version", keys=["NETLIFY_AUTH_TOKEN"], free=True, docs="https://docs.netlify.com")
_t("railway", "Railway", "Cloud Platforms", "cli",
   install="npm install -g @railway/cli", check="railway --version", keys=["RAILWAY_TOKEN"], free=True, docs="https://docs.railway.app")
_t("render", "Render", "Cloud Platforms", "info", keys=["RENDER_API_KEY"], free=True, docs="https://render.com/docs")
_t("fly.io", "Fly.io", "Cloud Platforms", "cli",
   install="curl -L https://fly.io/install.sh | sh", check="flyctl version", keys=["FLY_API_TOKEN"], free=True, docs="https://fly.io/docs")
_t("digitalocean", "DigitalOcean", "Cloud Platforms", "lib_py",
   install="pip install python-digitalocean", keys=["DO_API_TOKEN"], free=False, docs="https://docs.digitalocean.com")

# ════════════════════════════════════════════════════════════════════════
# 🌐 WEB SERVERS & REVERSE PROXIES
# ════════════════════════════════════════════════════════════════════════
_t("nginx", "NGINX", "Web Servers", "cli",
   install="apt-get install -y nginx", check="nginx -v", docs="https://nginx.org/en/docs")
_t("apache", "Apache HTTP", "Web Servers", "cli",
   install="apt-get install -y apache2", check="apache2 -v", docs="https://httpd.apache.org/docs")
_t("caddy", "Caddy Server", "Web Servers", "cli",
   install="apt-get install -y debian-keyring debian-archive-keyring apt-transport-https && curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg && curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | tee /etc/apt/sources.list.d/caddy-stable.list && apt-get update && apt-get install -y caddy",
   check="caddy version", docs="https://caddyserver.com/docs")
_t("traefik", "Traefik", "Web Servers", "info", docs="https://doc.traefik.io/traefik")
_t("linux", "Linux", "Web Servers", "info", docs="https://www.kernel.org/doc")
_t("ubuntu", "Ubuntu Server", "Web Servers", "info", docs="https://ubuntu.com/server/docs")

# ════════════════════════════════════════════════════════════════════════
# 💾 STORAGE
# ════════════════════════════════════════════════════════════════════════
_t("minio", "MinIO", "Storage", "lib_py",
   install="pip install minio", keys=["MINIO_ENDPOINT", "MINIO_ACCESS_KEY", "MINIO_SECRET_KEY"], free=True, docs="https://min.io/docs")
_t("seaweedfs", "SeaweedFS", "Storage", "info", docs="https://github.com/seaweedfs/seaweedfs/wiki")
_t("ceph", "Ceph Storage", "Storage", "info", docs="https://docs.ceph.com")

# ════════════════════════════════════════════════════════════════════════
# 📬 QUEUES & WORKFLOWS
# ════════════════════════════════════════════════════════════════════════
_t("rabbitmq", "RabbitMQ", "Queues & Workflows", "lib_py",
   install="pip install pika aio-pika", docs="https://www.rabbitmq.com/documentation.html", keys=["RABBITMQ_URL"])
_t("kafka", "Apache Kafka", "Queues & Workflows", "lib_py",
   install="pip install confluent-kafka", docs="https://kafka.apache.org/documentation")
_t("kafka-connect", "Kafka Connect", "Queues & Workflows", "info", docs="https://kafka.apache.org/documentation/#connect")
_t("nats", "NATS", "Queues & Workflows", "lib_py",
   install="pip install nats-py", docs="https://docs.nats.io")
_t("bullmq", "BullMQ", "Queues & Workflows", "lib_js",
   install="yarn add bullmq", docs="https://docs.bullmq.io")
_t("temporal", "Temporal", "Queues & Workflows", "lib_py",
   install="pip install temporalio", docs="https://docs.temporal.io")
_t("celery", "Celery", "Queues & Workflows", "lib_py",
   install="pip install celery[redis]", docs="https://docs.celeryq.dev")
_t("spark", "Apache Spark (PySpark)", "Queues & Workflows", "lib_py",
   install="pip install pyspark", docs="https://spark.apache.org/docs/latest")
_t("flink", "Apache Flink", "Queues & Workflows", "info", docs="https://flink.apache.org/docs")
_t("beam", "Apache Beam", "Queues & Workflows", "lib_py",
   install="pip install apache-beam", docs="https://beam.apache.org/documentation")
_t("airflow", "Apache Airflow", "Queues & Workflows", "lib_py",
   install="pip install apache-airflow", docs="https://airflow.apache.org/docs")
_t("dagster", "Dagster", "Queues & Workflows", "lib_py",
   install="pip install dagster dagster-webserver", docs="https://docs.dagster.io")
_t("prefect", "Prefect", "Queues & Workflows", "lib_py",
   install="pip install prefect", docs="https://docs.prefect.io")
_t("dbt", "dbt", "Queues & Workflows", "lib_py",
   install="pip install dbt-core", docs="https://docs.getdbt.com")
_t("ray", "Ray", "Queues & Workflows", "lib_py",
   install="pip install ray[default]", docs="https://docs.ray.io")

# ════════════════════════════════════════════════════════════════════════
# 🔌 API TOOLS & PROTOCOLS
# ════════════════════════════════════════════════════════════════════════
_t("postman", "Postman", "API Tools", "info", docs="https://learning.postman.com")
_t("insomnia", "Insomnia", "API Tools", "info", docs="https://docs.insomnia.rest")
_t("swagger", "Swagger / OpenAPI", "API Tools", "lib_py",
   install="pip install pyswagger", docs="https://swagger.io/docs")
_t("grpc", "gRPC", "API Tools", "lib_py",
   install="pip install grpcio grpcio-tools", docs="https://grpc.io/docs")
_t("graphql", "GraphQL (Strawberry)", "API Tools", "lib_py",
   install="pip install strawberry-graphql", docs="https://strawberry.rocks/docs")
_t("apollo", "Apollo GraphQL", "API Tools", "lib_js",
   install="yarn add @apollo/client graphql", docs="https://www.apollographql.com/docs")
_t("hasura", "Hasura GraphQL", "API Tools", "info", docs="https://hasura.io/docs")
_t("socket.io", "Socket.IO", "API Tools", "lib_py",
   install="pip install python-socketio", docs="https://socket.io/docs")
_t("peerjs", "PeerJS", "API Tools", "lib_js",
   install="yarn add peerjs", docs="https://peerjs.com")
_t("webrtc", "WebRTC", "API Tools", "info", docs="https://webrtc.org")

# ════════════════════════════════════════════════════════════════════════
# 🎙️ REALTIME A/V
# ════════════════════════════════════════════════════════════════════════
_t("livekit", "LiveKit", "Realtime A/V", "lib_py",
   install="pip install livekit", keys=["LIVEKIT_API_KEY", "LIVEKIT_API_SECRET", "LIVEKIT_URL"], free=True, docs="https://docs.livekit.io")
_t("agora", "Agora", "Realtime A/V", "lib_js",
   install="yarn add agora-rtc-sdk-ng", keys=["AGORA_APP_ID"], free=True, docs="https://docs.agora.io")
_t("twilio", "Twilio", "Realtime A/V", "lib_py",
   install="pip install twilio", keys=["TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN"], free=False, docs="https://www.twilio.com/docs")
_t("vonage", "Vonage", "Realtime A/V", "lib_py",
   install="pip install vonage", keys=["VONAGE_API_KEY", "VONAGE_API_SECRET"], free=False, docs="https://developer.vonage.com")
_t("daily.co", "Daily.co", "Realtime A/V", "lib_js",
   install="yarn add @daily-co/daily-js", keys=["DAILY_API_KEY"], free=True, docs="https://docs.daily.co")
_t("mux", "Mux Video", "Realtime A/V", "lib_py",
   install="pip install mux-python", keys=["MUX_TOKEN_ID", "MUX_TOKEN_SECRET"], free=False, docs="https://docs.mux.com")
_t("cloudflare-stream", "Cloudflare Stream", "Realtime A/V", "service_paid",
   keys=["CLOUDFLARE_API_TOKEN"], free=False, docs="https://developers.cloudflare.com/stream")

# ════════════════════════════════════════════════════════════════════════
# 🎬 COMPUTER VISION
# ════════════════════════════════════════════════════════════════════════
_t("ffmpeg", "FFmpeg", "Computer Vision", "cli",
   install="apt-get install -y ffmpeg", check="ffmpeg -version", docs="https://ffmpeg.org/documentation.html")
_t("opencv", "OpenCV", "Computer Vision", "lib_py",
   install="pip install opencv-python", docs="https://docs.opencv.org")
_t("mediapipe", "MediaPipe", "Computer Vision", "lib_py",
   install="pip install mediapipe", docs="https://ai.google.dev/edge/mediapipe")
_t("roboflow", "Roboflow", "Computer Vision", "lib_py",
   install="pip install roboflow", keys=["ROBOFLOW_API_KEY"], free=True, docs="https://docs.roboflow.com")
_t("ultralytics", "Ultralytics YOLO", "Computer Vision", "lib_py",
   install="pip install ultralytics", docs="https://docs.ultralytics.com")
_t("detectron2", "Detectron2", "Computer Vision", "lib_py",
   install="pip install 'git+https://github.com/facebookresearch/detectron2.git'", docs="https://detectron2.readthedocs.io")
_t("sam", "Segment Anything (SAM)", "Computer Vision", "lib_py",
   install="pip install 'git+https://github.com/facebookresearch/segment-anything.git'", docs="https://segment-anything.com")
_t("sam2", "SAM 2", "Computer Vision", "lib_py",
   install="pip install 'git+https://github.com/facebookresearch/sam2.git'", docs="https://github.com/facebookresearch/sam2")
_t("grounding-dino", "Grounding DINO", "Computer Vision", "info", docs="https://github.com/IDEA-Research/GroundingDINO")
_t("openmmlab", "OpenMMLab", "Computer Vision", "info", docs="https://openmmlab.com")
_t("cvat", "CVAT", "Computer Vision", "info", docs="https://docs.cvat.ai")
_t("label-studio", "Label Studio", "Computer Vision", "lib_py",
   install="pip install label-studio", docs="https://labelstud.io/guide")

# ════════════════════════════════════════════════════════════════════════
# 🎨 IMAGE GENERATION
# ════════════════════════════════════════════════════════════════════════
_t("stable-diffusion", "Stable Diffusion (diffusers)", "Image Generation", "lib_py",
   install="pip install diffusers transformers accelerate", docs="https://huggingface.co/docs/diffusers")
_t("comfyui", "ComfyUI", "Image Generation", "info", docs="https://github.com/comfyanonymous/ComfyUI")
_t("automatic1111", "AUTOMATIC1111 WebUI", "Image Generation", "info", docs="https://github.com/AUTOMATIC1111/stable-diffusion-webui")
_t("fooocus", "Fooocus", "Image Generation", "info", docs="https://github.com/lllyasviel/Fooocus")
_t("invokeai", "InvokeAI", "Image Generation", "info", docs="https://invoke-ai.github.io/InvokeAI")
_t("midjourney", "Midjourney", "Image Generation", "info", docs="https://docs.midjourney.com")
_t("leonardo", "Leonardo AI", "Image Generation", "service_paid",
   keys=["LEONARDO_API_KEY"], free=False, docs="https://docs.leonardo.ai")
_t("ideogram", "Ideogram", "Image Generation", "info", docs="https://docs.ideogram.ai")
_t("firefly", "Adobe Firefly", "Image Generation", "service_paid",
   keys=["ADOBE_CLIENT_ID", "ADOBE_CLIENT_SECRET"], free=False, docs="https://developer.adobe.com/firefly-services")
_t("canva", "Canva", "Image Generation", "info", docs="https://www.canva.dev/docs")
_t("controlnet", "ControlNet", "Image Generation", "info", docs="https://huggingface.co/docs/diffusers/using-diffusers/controlnet")
_t("ip-adapter", "IP-Adapter", "Image Generation", "info", docs="https://huggingface.co/docs/diffusers/using-diffusers/ip_adapter")
_t("lora", "LoRA", "Image Generation", "info", docs="https://huggingface.co/docs/peft/conceptual_guides/lora")
_t("dreambooth", "DreamBooth", "Image Generation", "info", docs="https://huggingface.co/docs/diffusers/training/dreambooth")
_t("photomaker", "PhotoMaker", "Image Generation", "info", docs="https://github.com/TencentARC/PhotoMaker")
_t("instantid", "InstantID", "Image Generation", "info", docs="https://instantid.github.io")
_t("facefusion", "FaceFusion", "Image Generation", "info", docs="https://docs.facefusion.io")
_t("roop", "Roop", "Image Generation", "info", docs="https://github.com/s0md3v/roop")
_t("fal.ai", "Fal.ai (image/video models)", "Image Generation", "lib_py",
   install="pip install fal-client", keys=["FAL_KEY"], free=False, docs="https://fal.ai/docs")
_t("stability", "Stability AI", "Image Generation", "lib_py",
   install="pip install stability-sdk", keys=["STABILITY_API_KEY"], free=False, docs="https://platform.stability.ai/docs")

# ════════════════════════════════════════════════════════════════════════
# 🎥 VIDEO GENERATION
# ════════════════════════════════════════════════════════════════════════
_t("runway", "Runway", "Video Generation", "service_paid", keys=["RUNWAY_API_KEY"], free=False, docs="https://docs.runwayml.com")
_t("pika", "Pika Labs", "Video Generation", "info", docs="https://pika.art")
_t("luma", "Luma AI", "Video Generation", "service_paid", keys=["LUMAAI_API_KEY"], free=False, docs="https://docs.lumalabs.ai")
_t("synthesia", "Synthesia", "Video Generation", "service_paid", keys=["SYNTHESIA_API_KEY"], free=False, docs="https://docs.synthesia.io")
_t("heygen", "HeyGen", "Video Generation", "service_paid", keys=["HEYGEN_API_KEY"], free=False, docs="https://docs.heygen.com")
_t("kaiber", "Kaiber", "Video Generation", "info", docs="https://kaiber.ai")
_t("animatediff", "AnimateDiff", "Video Generation", "info", docs="https://huggingface.co/docs/diffusers/api/pipelines/animatediff")
_t("animate-anyone", "Animate Anyone", "Video Generation", "info", docs="https://humanaigc.github.io/animate-anyone")
_t("sora", "OpenAI Sora 2", "Video Generation", "service_paid", keys=["OPENAI_API_KEY"], free=False, docs="https://platform.openai.com/docs/guides/video-generation")

# ════════════════════════════════════════════════════════════════════════
# 🎮 3D / GAMES / ANIMATION
# ════════════════════════════════════════════════════════════════════════
_t("blender", "Blender", "Games & 3D", "cli",
   install="apt-get install -y blender", check="blender --version", docs="https://docs.blender.org")
_t("unity", "Unity", "Games & 3D", "info", docs="https://docs.unity.com")
_t("unreal", "Unreal Engine", "Games & 3D", "info", docs="https://dev.epicgames.com/documentation")
_t("godot", "Godot Engine", "Games & 3D", "info", docs="https://docs.godotengine.org")
_t("omniverse", "NVIDIA Omniverse", "Games & 3D", "info", docs="https://docs.omniverse.nvidia.com")
_t("meshy", "Meshy AI", "Games & 3D", "service_paid", keys=["MESHY_API_KEY"], free=False, docs="https://docs.meshy.ai")
_t("spline", "Spline 3D", "Games & 3D", "info", docs="https://docs.spline.design")
_t("three.js", "Three.js", "Games & 3D", "lib_js",
   install="yarn add three", docs="https://threejs.org/docs")
_t("babylon", "Babylon.js", "Games & 3D", "lib_js",
   install="yarn add @babylonjs/core", docs="https://doc.babylonjs.com")
_t("r3f", "React Three Fiber", "Games & 3D", "lib_js",
   install="yarn add @react-three/fiber @react-three/drei three", docs="https://r3f.docs.pmnd.rs")
_t("rive", "Rive", "Games & 3D", "lib_js",
   install="yarn add @rive-app/react-canvas", docs="https://rive.app/docs")
_t("lottie", "LottieFiles", "Games & 3D", "lib_js",
   install="yarn add lottie-react", docs="https://lottiefiles.com/docs")
_t("framer-motion", "Framer Motion", "Games & 3D", "lib_js",
   install="yarn add framer-motion", docs="https://motion.dev/docs")
_t("gsap", "GSAP", "Games & 3D", "lib_js",
   install="yarn add gsap", docs="https://gsap.com/docs")
_t("anime.js", "Anime.js", "Games & 3D", "lib_js",
   install="yarn add animejs", docs="https://animejs.com/documentation")

# ════════════════════════════════════════════════════════════════════════
# 🎨 FRONTEND
# ════════════════════════════════════════════════════════════════════════
_t("react", "React", "Frontend", "lib_js", install="yarn add react react-dom", docs="https://react.dev")
_t("nextjs", "Next.js", "Frontend", "lib_js", install="npx create-next-app@latest", docs="https://nextjs.org/docs")
_t("vue", "Vue.js", "Frontend", "lib_js", install="yarn add vue", docs="https://vuejs.org/guide")
_t("nuxt", "Nuxt", "Frontend", "lib_js", install="npx nuxi@latest init", docs="https://nuxt.com/docs")
_t("sveltekit", "SvelteKit", "Frontend", "lib_js", install="npx sv create", docs="https://kit.svelte.dev/docs")
_t("angular", "Angular", "Frontend", "lib_js", install="npm install -g @angular/cli", docs="https://angular.dev/overview")
_t("astro", "Astro", "Frontend", "lib_js", install="npm create astro@latest", docs="https://docs.astro.build")
_t("remix", "Remix", "Frontend", "lib_js", install="npx create-remix@latest", docs="https://remix.run/docs")
_t("tailwindcss", "Tailwind CSS", "Frontend", "lib_js",
   install="yarn add -D tailwindcss postcss autoprefixer", docs="https://tailwindcss.com/docs")
_t("shadcn", "Shadcn UI", "Frontend", "lib_js",
   install="npx shadcn@latest init", docs="https://ui.shadcn.com/docs")

# ════════════════════════════════════════════════════════════════════════
# 📱 MOBILE
# ════════════════════════════════════════════════════════════════════════
_t("expo", "Expo", "Mobile", "lib_js",
   install="npm install -g expo-cli", check="expo --version", docs="https://docs.expo.dev")
_t("react-native", "React Native", "Mobile", "lib_js",
   install="npx react-native@latest init", docs="https://reactnative.dev/docs")
_t("flutter", "Flutter", "Mobile", "cli",
   install="git clone https://github.com/flutter/flutter.git -b stable --depth 1 /opt/flutter",
   check="flutter --version", docs="https://docs.flutter.dev")
_t("capacitor", "Capacitor", "Mobile", "lib_js",
   install="yarn add @capacitor/core @capacitor/cli", docs="https://capacitorjs.com/docs")
_t("electron", "Electron", "Mobile", "lib_js",
   install="yarn add electron", docs="https://www.electronjs.org/docs/latest")
_t("tauri", "Tauri", "Mobile", "lib_js",
   install="yarn add @tauri-apps/cli", docs="https://tauri.app/v1/guides")

# ════════════════════════════════════════════════════════════════════════
# 🟢 BACKEND
# ════════════════════════════════════════════════════════════════════════
_t("nodejs", "Node.js", "Backend", "runtime",
   install="curl -fsSL https://deb.nodesource.com/setup_lts.x | bash - && apt-get install -y nodejs",
   check="node --version", docs="https://nodejs.org/docs")
_t("bun", "Bun", "Backend", "runtime",
   install="curl -fsSL https://bun.sh/install | bash", check="bun --version", docs="https://bun.sh/docs")
_t("deno", "Deno", "Backend", "runtime",
   install="curl -fsSL https://deno.land/install.sh | sh", check="deno --version", docs="https://docs.deno.com")
_t("fastapi", "FastAPI", "Backend", "lib_py",
   install="pip install fastapi uvicorn", docs="https://fastapi.tiangolo.com")
_t("nestjs", "NestJS", "Backend", "lib_js",
   install="npm install -g @nestjs/cli", check="nest --version", docs="https://docs.nestjs.com")
_t("express", "Express.js", "Backend", "lib_js",
   install="yarn add express", docs="https://expressjs.com")
_t("hono", "Hono", "Backend", "lib_js",
   install="yarn add hono", docs="https://hono.dev")
_t("trpc", "tRPC", "Backend", "lib_js",
   install="yarn add @trpc/server @trpc/client", docs="https://trpc.io/docs")
_t("typescript", "TypeScript", "Backend", "lib_js",
   install="yarn add -D typescript", check="tsc --version", docs="https://www.typescriptlang.org/docs")
_t("zod", "Zod", "Backend", "lib_js",
   install="yarn add zod", docs="https://zod.dev")

# ════════════════════════════════════════════════════════════════════════
# 🧪 QUALITY / TESTING
# ════════════════════════════════════════════════════════════════════════
_t("eslint", "ESLint", "Quality", "lib_js",
   install="yarn add -D eslint", docs="https://eslint.org/docs/latest")
_t("prettier", "Prettier", "Quality", "lib_js",
   install="yarn add -D prettier", docs="https://prettier.io/docs")
_t("vitest", "Vitest", "Quality", "lib_js",
   install="yarn add -D vitest", docs="https://vitest.dev/guide")
_t("playwright", "Playwright", "Quality", "lib_js",
   install="yarn add -D @playwright/test && npx playwright install", docs="https://playwright.dev/docs")
_t("cypress", "Cypress", "Quality", "lib_js",
   install="yarn add -D cypress", docs="https://docs.cypress.io")
_t("jest", "Jest", "Quality", "lib_js",
   install="yarn add -D jest", docs="https://jestjs.io/docs")
_t("storybook", "Storybook", "Quality", "lib_js",
   install="npx storybook@latest init", docs="https://storybook.js.org/docs")
_t("pytest", "pytest", "Quality", "lib_py",
   install="pip install pytest pytest-asyncio", docs="https://docs.pytest.org")

# ════════════════════════════════════════════════════════════════════════
# 🛠️ BUILD TOOLS
# ════════════════════════════════════════════════════════════════════════
_t("vite", "Vite", "Build Tools", "lib_js", install="yarn add -D vite", docs="https://vitejs.dev/guide")
_t("rspack", "Rspack", "Build Tools", "lib_js", install="yarn add -D @rspack/cli", docs="https://www.rspack.dev/guide")
_t("webpack", "Webpack", "Build Tools", "lib_js", install="yarn add -D webpack webpack-cli", docs="https://webpack.js.org/concepts")
_t("parcel", "Parcel", "Build Tools", "lib_js", install="yarn add -D parcel", docs="https://parceljs.org/docs")
_t("babel", "Babel", "Build Tools", "lib_js", install="yarn add -D @babel/core @babel/cli", docs="https://babeljs.io/docs")
_t("turbopack", "Turbopack", "Build Tools", "info", docs="https://turbo.build/pack/docs")
_t("turborepo", "Turborepo", "Build Tools", "lib_js", install="yarn add -D turbo", docs="https://turbo.build/repo/docs")
_t("nx", "Nx", "Build Tools", "lib_js", install="npm install -g nx", docs="https://nx.dev")
_t("pnpm", "pnpm", "Build Tools", "cli", install="npm install -g pnpm", check="pnpm --version", docs="https://pnpm.io/installation")
_t("yarn", "Yarn", "Build Tools", "cli", install="npm install -g yarn", check="yarn --version", docs="https://yarnpkg.com/getting-started")
_t("biome", "Biome", "Build Tools", "lib_js", install="yarn add -D @biomejs/biome", docs="https://biomejs.dev")
_t("swc", "SWC", "Build Tools", "lib_js", install="yarn add -D @swc/core @swc/cli", docs="https://swc.rs/docs")

# ════════════════════════════════════════════════════════════════════════
# 🔄 NO-CODE / AUTOMATION
# ════════════════════════════════════════════════════════════════════════
_t("n8n", "n8n", "No-Code", "cli", install="npm install -g n8n", check="n8n --version", docs="https://docs.n8n.io")
_t("zapier", "Zapier AI", "No-Code", "info", docs="https://zapier.com/developer")
_t("make", "Make (Integromat)", "No-Code", "info", docs="https://www.make.com/en/help")
_t("pipedream", "Pipedream", "No-Code", "info", docs="https://pipedream.com/docs")
_t("retool", "Retool", "No-Code", "info", docs="https://docs.retool.com")
_t("tooljet", "ToolJet", "No-Code", "info", docs="https://docs.tooljet.com")
_t("bubble", "Bubble", "No-Code", "info", docs="https://manual.bubble.io")
_t("flutterflow", "FlutterFlow", "No-Code", "info", docs="https://docs.flutterflow.io")
_t("framer", "Framer AI", "No-Code", "info", docs="https://www.framer.com/learn")
_t("webflow", "Webflow AI", "No-Code", "info", docs="https://university.webflow.com")
_t("figma", "Figma AI", "No-Code", "info", docs="https://www.figma.com/developers")
_t("penpot", "Penpot", "No-Code", "info", docs="https://help.penpot.app")
_t("uizard", "Uizard", "No-Code", "info", docs="https://uizard.io/docs")
_t("galileo", "Galileo AI", "No-Code", "info", docs="https://www.usegalileo.ai")
_t("locofy", "Locofy", "No-Code", "info", docs="https://docs.locofy.ai")
_t("builder.io", "Builder.io", "No-Code", "info", docs="https://www.builder.io/c/docs/intro")

# ════════════════════════════════════════════════════════════════════════
# 📝 CMS & DOCS
# ════════════════════════════════════════════════════════════════════════
_t("sanity", "Sanity CMS", "CMS", "lib_js", install="yarn add @sanity/client", docs="https://www.sanity.io/docs")
_t("strapi", "Strapi", "CMS", "lib_js", install="npx create-strapi-app@latest", docs="https://docs.strapi.io")
_t("contentful", "Contentful", "CMS", "lib_js", install="yarn add contentful", keys=["CONTENTFUL_SPACE_ID", "CONTENTFUL_ACCESS_TOKEN"], free=True, docs="https://www.contentful.com/developers/docs")
_t("directus", "Directus", "CMS", "info", docs="https://docs.directus.io")
_t("payload", "Payload CMS", "CMS", "lib_js", install="npx create-payload-app@latest", docs="https://payloadcms.com/docs")
_t("ghost", "Ghost", "CMS", "info", docs="https://ghost.org/docs")
_t("wp-headless", "WordPress Headless", "CMS", "info", docs="https://developer.wordpress.org/rest-api")
_t("docusaurus", "Docusaurus", "Docs", "lib_js", install="npx create-docusaurus@latest", docs="https://docusaurus.io/docs")
_t("mintlify", "Mintlify", "Docs", "cli", install="npm install -g mintlify", check="mintlify --version", docs="https://mintlify.com/docs")
_t("nextra", "Nextra", "Docs", "lib_js", install="yarn add nextra nextra-theme-docs", docs="https://nextra.site/docs")
_t("starlight", "Astro Starlight", "Docs", "lib_js", install="npm create astro@latest -- --template starlight", docs="https://starlight.astro.build")

# ════════════════════════════════════════════════════════════════════════
# 🔐 AUTH
# ════════════════════════════════════════════════════════════════════════
_t("clerk", "Clerk", "Auth", "lib_js", install="yarn add @clerk/clerk-react", keys=["CLERK_PUBLISHABLE_KEY", "CLERK_SECRET_KEY"], free=True, docs="https://clerk.com/docs")
_t("auth0", "Auth0", "Auth", "lib_js", install="yarn add @auth0/auth0-react", keys=["AUTH0_DOMAIN", "AUTH0_CLIENT_ID"], free=True, docs="https://auth0.com/docs")
_t("better-auth", "Better Auth", "Auth", "lib_js", install="yarn add better-auth", docs="https://www.better-auth.com/docs")
_t("fusionauth", "FusionAuth", "Auth", "info", docs="https://fusionauth.io/docs")
_t("keycloak", "Keycloak", "Auth", "info", docs="https://www.keycloak.org/documentation")
_t("magic", "Magic.link", "Auth", "lib_js", install="yarn add magic-sdk", keys=["MAGIC_PUBLISHABLE_KEY"], free=True, docs="https://magic.link/docs")

# ════════════════════════════════════════════════════════════════════════
# 💳 PAYMENTS
# ════════════════════════════════════════════════════════════════════════
_t("stripe", "Stripe", "Payments", "lib_py", install="pip install stripe", keys=["STRIPE_SECRET_KEY"], free=False, docs="https://stripe.com/docs/api")
_t("paypal", "PayPal", "Payments", "lib_py", install="pip install paypalrestsdk", keys=["PAYPAL_CLIENT_ID", "PAYPAL_CLIENT_SECRET"], free=False, docs="https://developer.paypal.com/docs")
_t("lemon-squeezy", "Lemon Squeezy", "Payments", "service_paid", keys=["LEMONSQUEEZY_API_KEY"], free=False, docs="https://docs.lemonsqueezy.com")
_t("shopify-hydrogen", "Shopify Hydrogen", "Payments", "lib_js", install="npm create @shopify/hydrogen", docs="https://shopify.dev/docs/custom-storefronts/hydrogen")
_t("woocommerce", "WooCommerce", "Payments", "info", docs="https://woocommerce.com/documentation")
_t("saleor", "Saleor", "Payments", "info", docs="https://docs.saleor.io")
_t("magento", "Magento (Adobe Commerce)", "Payments", "info", docs="https://developer.adobe.com/commerce/docs")
_t("medusajs", "MedusaJS", "Payments", "lib_js", install="npx create-medusa-app@latest", docs="https://docs.medusajs.com")
_t("razorpay", "Razorpay", "Payments", "lib_py", install="pip install razorpay", keys=["RAZORPAY_KEY_ID", "RAZORPAY_KEY_SECRET"], free=False, docs="https://razorpay.com/docs")

# ════════════════════════════════════════════════════════════════════════
# 📋 PRODUCTIVITY
# ════════════════════════════════════════════════════════════════════════
_t("airtable", "Airtable", "Productivity", "lib_py", install="pip install pyairtable", keys=["AIRTABLE_API_KEY"], free=True, docs="https://airtable.com/developers/web/api")
_t("notion", "Notion AI", "Productivity", "lib_py", install="pip install notion-client", keys=["NOTION_TOKEN"], free=True, docs="https://developers.notion.com")
_t("obsidian", "Obsidian", "Productivity", "info", docs="https://help.obsidian.md")
_t("clickup", "ClickUp AI", "Productivity", "service_paid", keys=["CLICKUP_API_TOKEN"], free=False, docs="https://clickup.com/api")
_t("slack", "Slack AI", "Productivity", "lib_py", install="pip install slack-sdk", keys=["SLACK_BOT_TOKEN"], free=False, docs="https://api.slack.com")
_t("discord", "Discord Developer", "Productivity", "lib_py", install="pip install discord.py", keys=["DISCORD_BOT_TOKEN"], free=True, docs="https://discord.com/developers/docs")
_t("linear", "Linear", "Productivity", "service_paid", keys=["LINEAR_API_KEY"], free=False, docs="https://developers.linear.app")
_t("jira", "Jira", "Productivity", "lib_py", install="pip install atlassian-python-api", keys=["JIRA_TOKEN"], free=False, docs="https://developer.atlassian.com/cloud/jira")
_t("confluence", "Confluence", "Productivity", "lib_py", install="pip install atlassian-python-api", keys=["CONFLUENCE_TOKEN"], free=False, docs="https://developer.atlassian.com/cloud/confluence")
_t("trello", "Trello", "Productivity", "lib_py", install="pip install py-trello", keys=["TRELLO_KEY", "TRELLO_TOKEN"], free=True, docs="https://developer.atlassian.com/cloud/trello")
_t("asana", "Asana", "Productivity", "lib_py", install="pip install asana", keys=["ASANA_TOKEN"], free=True, docs="https://developers.asana.com")
_t("monday", "Monday.com", "Productivity", "service_paid", keys=["MONDAY_API_TOKEN"], free=False, docs="https://developer.monday.com")

# ════════════════════════════════════════════════════════════════════════
# 📈 ANALYTICS
# ════════════════════════════════════════════════════════════════════════
_t("posthog", "PostHog", "Analytics", "lib_py", install="pip install posthog", keys=["POSTHOG_API_KEY"], free=True, docs="https://posthog.com/docs")
_t("plausible", "Plausible Analytics", "Analytics", "info", docs="https://plausible.io/docs")
_t("umami", "Umami Analytics", "Analytics", "info", docs="https://umami.is/docs")
_t("mixpanel", "Mixpanel", "Analytics", "lib_py", install="pip install mixpanel", keys=["MIXPANEL_TOKEN"], free=True, docs="https://docs.mixpanel.com")
_t("amplitude", "Amplitude", "Analytics", "lib_py", install="pip install amplitude-analytics", keys=["AMPLITUDE_API_KEY"], free=True, docs="https://amplitude.com/docs")
_t("hotjar", "Hotjar", "Analytics", "info", docs="https://help.hotjar.com")
_t("logrocket", "LogRocket", "Analytics", "lib_js", install="yarn add logrocket", keys=["LOGROCKET_APP_ID"], free=True, docs="https://docs.logrocket.com")
_t("fullstory", "FullStory", "Analytics", "info", docs="https://developer.fullstory.com")

# ════════════════════════════════════════════════════════════════════════
# 🗺️ MAPS & GEO
# ════════════════════════════════════════════════════════════════════════
_t("mapbox", "Mapbox", "Maps & Geo", "lib_js", install="yarn add mapbox-gl", keys=["MAPBOX_ACCESS_TOKEN"], free=True, docs="https://docs.mapbox.com")
_t("leaflet", "Leaflet", "Maps & Geo", "lib_js", install="yarn add leaflet", docs="https://leafletjs.com/reference.html")
_t("cesium", "CesiumJS", "Maps & Geo", "lib_js", install="yarn add cesium", docs="https://cesium.com/learn")
_t("osm", "OpenStreetMap", "Maps & Geo", "info", docs="https://wiki.openstreetmap.org")
_t("qgis", "QGIS", "Maps & Geo", "info", docs="https://docs.qgis.org")
_t("arcgis", "ArcGIS", "Maps & Geo", "info", docs="https://developers.arcgis.com")
_t("opendronemap", "OpenDroneMap", "Maps & Geo", "info", docs="https://docs.opendronemap.org")

# ════════════════════════════════════════════════════════════════════════
# 🤖 ROBOTICS / RL
# ════════════════════════════════════════════════════════════════════════
_t("ros", "ROS Robotics", "Robotics", "info", docs="https://docs.ros.org")
_t("isaac-sim", "NVIDIA Isaac Sim", "Robotics", "info", docs="https://docs.omniverse.nvidia.com/isaacsim")
_t("openai-gym", "OpenAI Gym (Gymnasium)", "Robotics", "lib_py", install="pip install gymnasium", docs="https://gymnasium.farama.org")
_t("sb3", "Stable Baselines3", "Robotics", "lib_py", install="pip install stable-baselines3", docs="https://stable-baselines3.readthedocs.io")
_t("rllib", "RLlib", "Robotics", "lib_py", install="pip install ray[rllib]", docs="https://docs.ray.io/en/latest/rllib")
_t("pybullet", "PyBullet", "Robotics", "lib_py", install="pip install pybullet", docs="https://pybullet.org")
_t("mujoco", "MuJoCo", "Robotics", "lib_py", install="pip install mujoco", docs="https://mujoco.readthedocs.io")
_t("isaac-gym", "Isaac Gym", "Robotics", "info", docs="https://developer.nvidia.com/isaac-gym")
_t("habitat", "Habitat AI", "Robotics", "info", docs="https://aihabitat.org/docs")

# ════════════════════════════════════════════════════════════════════════
# 🥽 AR / VR / XR
# ════════════════════════════════════════════════════════════════════════
_t("arcore", "ARCore", "AR/VR/XR", "info", docs="https://developers.google.com/ar")
_t("arkit", "ARKit", "AR/VR/XR", "info", docs="https://developer.apple.com/augmented-reality")
_t("visionos", "Vision Pro SDK", "AR/VR/XR", "info", docs="https://developer.apple.com/visionos")
_t("openxr", "OpenXR", "AR/VR/XR", "info", docs="https://www.khronos.org/openxr")
_t("webxr", "WebXR", "AR/VR/XR", "info", docs="https://developer.mozilla.org/en-US/docs/Web/API/WebXR_Device_API")

# ════════════════════════════════════════════════════════════════════════
# ⛓️ WEB3 / BLOCKCHAIN
# ════════════════════════════════════════════════════════════════════════
_t("ethereum", "Ethereum (web3.py)", "Web3", "lib_py", install="pip install web3", docs="https://web3py.readthedocs.io")
_t("solidity", "Solidity", "Web3", "info", docs="https://docs.soliditylang.org")
_t("hardhat", "Hardhat", "Web3", "lib_js", install="yarn add -D hardhat", docs="https://hardhat.org/docs")
_t("foundry", "Foundry", "Web3", "cli", install="curl -L https://foundry.paradigm.xyz | bash && foundryup", check="forge --version", docs="https://book.getfoundry.sh")
_t("thirdweb", "Thirdweb", "Web3", "lib_js", install="yarn add thirdweb", keys=["THIRDWEB_CLIENT_ID"], free=True, docs="https://portal.thirdweb.com")
_t("moralis", "Moralis", "Web3", "lib_py", install="pip install moralis", keys=["MORALIS_API_KEY"], free=True, docs="https://docs.moralis.io")
_t("walletconnect", "WalletConnect", "Web3", "lib_js", install="yarn add @walletconnect/web3wallet", docs="https://docs.walletconnect.com")
_t("rainbowkit", "RainbowKit", "Web3", "lib_js", install="yarn add @rainbow-me/rainbowkit wagmi viem", docs="https://www.rainbowkit.com/docs")
_t("web3.js", "Web3.js", "Web3", "lib_js", install="yarn add web3", docs="https://docs.web3js.org")
_t("ethers", "Ethers.js", "Web3", "lib_js", install="yarn add ethers", docs="https://docs.ethers.org")

# ════════════════════════════════════════════════════════════════════════
# 📨 EMAIL / SMS / MESSAGING
# ════════════════════════════════════════════════════════════════════════
_t("sendgrid", "SendGrid", "Messaging", "lib_py", install="pip install sendgrid", keys=["SENDGRID_API_KEY"], free=True, docs="https://docs.sendgrid.com")
_t("resend", "Resend", "Messaging", "lib_py", install="pip install resend", keys=["RESEND_API_KEY"], free=True, docs="https://resend.com/docs")
_t("mailgun", "Mailgun", "Messaging", "lib_py", install="pip install mailgun.py", keys=["MAILGUN_API_KEY", "MAILGUN_DOMAIN"], free=True, docs="https://documentation.mailgun.com")
_t("postmark", "Postmark", "Messaging", "lib_py", install="pip install postmarker", keys=["POSTMARK_SERVER_TOKEN"], free=False, docs="https://postmarkapp.com/developer")
_t("telegram", "Telegram Bot API", "Messaging", "lib_py", install="pip install python-telegram-bot", keys=["TELEGRAM_BOT_TOKEN"], free=True, docs="https://core.telegram.org/bots/api")

# ════════════════════════════════════════════════════════════════════════
# 🎙️ VOICE / TTS / STT
# ════════════════════════════════════════════════════════════════════════
_t("elevenlabs", "ElevenLabs TTS", "Voice", "lib_py", install="pip install elevenlabs", keys=["ELEVENLABS_API_KEY"], free=True, docs="https://elevenlabs.io/docs")
_t("openai-tts", "OpenAI TTS", "Voice", "lib_py", install="pip install openai", keys=["OPENAI_API_KEY"], free=False, docs="https://platform.openai.com/docs/guides/text-to-speech")
_t("whisper", "OpenAI Whisper", "Voice", "lib_py", install="pip install openai-whisper", docs="https://github.com/openai/whisper")
_t("deepgram", "Deepgram STT", "Voice", "lib_py", install="pip install deepgram-sdk", keys=["DEEPGRAM_API_KEY"], free=True, docs="https://developers.deepgram.com")
_t("assemblyai", "AssemblyAI", "Voice", "lib_py", install="pip install assemblyai", keys=["ASSEMBLYAI_API_KEY"], free=True, docs="https://www.assemblyai.com/docs")
_t("speechmatics", "Speechmatics", "Voice", "service_paid", keys=["SPEECHMATICS_API_KEY"], free=False, docs="https://docs.speechmatics.com")

# ════════════════════════════════════════════════════════════════════════
# Index helpers
# ════════════════════════════════════════════════════════════════════════
def get_categories() -> List[str]:
    return sorted({t["category"] for t in CATALOG.values()})


def get_tools_by_category(category: str) -> List[Dict[str, Any]]:
    cat_lc = (category or "").lower().strip()
    return [t for t in CATALOG.values() if cat_lc in t["category"].lower()]


def find_tool(name_or_id: str) -> Optional[Dict[str, Any]]:
    """Resolve a tool by id, name, or fuzzy substring."""
    if not name_or_id:
        return None
    key = name_or_id.lower().strip()
    if key in CATALOG:
        return CATALOG[key]
    # exact name match
    for t in CATALOG.values():
        if t["name"].lower() == key:
            return t
    # substring match
    for t in CATALOG.values():
        if key in t["id"] or key in t["name"].lower():
            return t
    return None


def search_catalog(query: str, limit: int = 20) -> List[Dict[str, Any]]:
    if not query:
        return list(CATALOG.values())[:limit]
    q = query.lower().strip()
    scored: List[Tuple[int, Dict[str, Any]]] = []
    for t in CATALOG.values():
        score = 0
        if q == t["id"]:
            score = 100
        elif q in t["id"]:
            score = 80
        elif q in t["name"].lower():
            score = 70
        elif q in t["category"].lower():
            score = 50
        elif t["invoke_hint"] and q in t["invoke_hint"].lower():
            score = 30
        if score > 0:
            scored.append((score, t))
    scored.sort(key=lambda x: -x[0])
    return [t for _, t in scored[:limit]]


# ════════════════════════════════════════════════════════════════════════
# Installation / status detection
# ════════════════════════════════════════════════════════════════════════
async def _shell(cmd: str, timeout: int = 90) -> Dict[str, Any]:
    try:
        proc = await asyncio.create_subprocess_shell(
            cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        out, err = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        return {
            "exit_code": proc.returncode,
            "stdout": (out or b"").decode("utf-8", errors="replace")[-4000:],
            "stderr": (err or b"").decode("utf-8", errors="replace")[-2000:],
        }
    except asyncio.TimeoutError:
        return {"exit_code": -1, "stdout": "", "stderr": f"timeout after {timeout}s"}
    except Exception as e:
        return {"exit_code": -1, "stdout": "", "stderr": str(e)}


def _py_module_for(tool: Dict[str, Any]) -> Optional[str]:
    """Best-guess Python module name for `lib_py` tools."""
    if tool["type"] != "lib_py" or not tool.get("install_cmd"):
        return None
    # extract first non-flag package name after 'pip install'
    m = re.search(r"pip\s+install\s+(?:-U\s+|--upgrade\s+)?([^\s\[\]'\"]+)", tool["install_cmd"])
    if not m:
        return None
    pkg = m.group(1).split("[")[0].split("==")[0].split(">=")[0]
    # normalize package → module name (best-effort)
    fixes = {
        "psycopg2-binary": "psycopg2", "google-genai": "google.genai",
        "google-cloud-storage": "google.cloud.storage",
        "google-cloud-aiplatform": "google.cloud.aiplatform",
        "opencv-python": "cv2", "huggingface_hub": "huggingface_hub",
        "sentence-transformers": "sentence_transformers",
        "python-socketio": "socketio", "python-telegram-bot": "telegram",
        "pinecone-client": "pinecone", "qdrant-client": "qdrant_client",
        "weaviate-client": "weaviate", "pyairtable": "pyairtable",
        "stable-baselines3": "stable_baselines3", "py-trello": "trello",
        "amplitude-analytics": "amplitude", "fal-client": "fal_client",
        "stability-sdk": "stability_sdk", "label-studio": "label_studio",
        "open-webui": "open_webui", "openai-whisper": "whisper",
        "deepgram-sdk": "deepgram", "discord.py": "discord",
        "atlassian-python-api": "atlassian", "azure-identity": "azure.identity",
        "azure-storage-blob": "azure.storage.blob", "azure-ai-ml": "azure.ai.ml",
        "python-digitalocean": "digitalocean", "apache-beam": "apache_beam",
        "apache-airflow": "airflow", "dagster-webserver": "dagster_webserver",
        "openai-agents": "agents", "pydantic-ai": "pydantic_ai",
        "aio-pika": "aio_pika", "firebase-admin": "firebase_admin",
        "supabase": "supabase", "appwrite": "appwrite", "twilio": "twilio",
        "mux-python": "mux_python", "datadog": "datadog",
        "sentry-sdk": "sentry_sdk", "opentelemetry-api": "opentelemetry",
        "opentelemetry-sdk": "opentelemetry.sdk", "confluent-kafka": "confluent_kafka",
        "comet_ml": "comet_ml", "guardrails-ai": "guardrails",
        "llama-index": "llama_index", "haystack-ai": "haystack",
        "semantic-kernel": "semantic_kernel", "dspy-ai": "dspy",
        "swarms": "swarms", "metagpt": "metagpt", "camel-ai": "camel",
        "pyautogen": "autogen", "trulens-eval": "trulens_eval",
        "ragas": "ragas", "deepeval": "deepeval",
        "diffusers": "diffusers", "transformers": "transformers",
        "boto3": "boto3", "cloudflare": "cloudflare",
        "vllm": "vllm", "open-interpreter": "interpreter",
        "humanloop": "humanloop",
        "elevenlabs": "elevenlabs", "openai": "openai",
        "anthropic": "anthropic", "groq": "groq", "mistralai": "mistralai",
        "cohere": "cohere", "together": "together", "replicate": "replicate",
        "baseten": "baseten", "fireworks-ai": "fireworks",
        "litellm": "litellm", "portkey-ai": "portkey_ai",
    }
    return fixes.get(pkg, pkg.replace("-", "_"))


def _check_installed(tool: Dict[str, Any]) -> Dict[str, Any]:
    """Synchronous best-effort check whether a tool is already installed."""
    typ = tool["type"]
    if typ == "lib_py":
        mod = _py_module_for(tool)
        if mod:
            try:
                spec = importlib.util.find_spec(mod.split(".")[0])
                return {"installed": spec is not None, "method": f"importlib({mod})"}
            except Exception as e:
                return {"installed": False, "method": f"importlib failed: {e}"}
    if typ == "cli" and tool.get("check_cmd"):
        bin_name = tool["check_cmd"].split()[0]
        return {"installed": shutil.which(bin_name) is not None, "method": f"which({bin_name})"}
    if typ in ("info", "framework", "service_free", "service_paid", "infra"):
        return {"installed": None, "method": "n/a"}  # not directly installable
    return {"installed": None, "method": "unknown"}


# ════════════════════════════════════════════════════════════════════════
# AI-callable tool functions
# ════════════════════════════════════════════════════════════════════════
async def tool_universe_search(query: str = "", category: str = "", limit: int = 20) -> Dict[str, Any]:
    """Search the 300+ tool catalog by query and/or category."""
    if category:
        items = get_tools_by_category(category)
        if query:
            q = query.lower()
            items = [t for t in items if q in t["name"].lower() or q in t["id"]]
        items = items[:limit]
    else:
        items = search_catalog(query, limit=limit)
    return {
        "ok": True,
        "query": query, "category": category,
        "count": len(items),
        "total_in_catalog": len(CATALOG),
        "tools": [
            {"id": t["id"], "name": t["name"], "category": t["category"],
             "type": t["type"], "free": t["free"], "needs_keys": t["env_keys"]}
            for t in items
        ],
    }


async def tool_universe_info(tool: str) -> Dict[str, Any]:
    """Get full metadata + live install status for a tool."""
    t = find_tool(tool)
    if not t:
        # suggest fuzzy matches
        hits = search_catalog(tool, limit=5)
        return {
            "ok": False,
            "error": f"ما لقيت أداة باسم '{tool}'",
            "did_you_mean": [{"id": h["id"], "name": h["name"]} for h in hits],
        }
    status = _check_installed(t)
    keys_status = [
        {"key": k, "set": bool(vault_get(k)), "source": "env" if os.environ.get(k) else ("vault" if vault_get(k) else "missing")}
        for k in t["env_keys"]
    ]
    return {
        "ok": True,
        "tool": t,
        "installed": status["installed"],
        "install_check_method": status["method"],
        "credentials": keys_status,
        "ready_to_use": (status["installed"] is True or t["type"] == "service_free") and all(s["set"] for s in keys_status),
    }


async def tool_universe_install(tool: str, dry_run: bool = False, timeout: int = 180) -> Dict[str, Any]:
    """Actually install a tool. Returns shell output. Won't reinstall if already present."""
    t = find_tool(tool)
    if not t:
        return {"ok": False, "error": f"ما لقيت أداة باسم '{tool}'"}
    cmd = t.get("install_cmd")
    if not cmd:
        return {"ok": False, "error": f"الأداة '{t['name']}' من نوع '{t['type']}' وما عندها أمر تثبيت مباشر — راجع docs: {t.get('docs_url')}"}
    pre = _check_installed(t)
    if pre.get("installed") is True:
        return {"ok": True, "already_installed": True, "tool": t["id"],
                "check_method": pre["method"]}
    if dry_run:
        return {"ok": True, "dry_run": True, "would_run": cmd, "tool": t["id"]}
    sh = await _shell(cmd, timeout=timeout)
    post = _check_installed(t)
    return {
        "ok": sh["exit_code"] == 0,
        "tool": t["id"],
        "install_cmd": cmd,
        "exit_code": sh["exit_code"],
        "stdout_tail": sh["stdout"][-1500:],
        "stderr_tail": sh["stderr"][-1500:],
        "installed_after": post.get("installed"),
    }


async def tool_universe_status(tool: str = "") -> Dict[str, Any]:
    """Quick status: if `tool` given → that one; else summary of all categories."""
    if tool:
        return await tool_universe_info(tool)
    cats: Dict[str, Dict[str, int]] = {}
    for t in CATALOG.values():
        c = t["category"]
        cats.setdefault(c, {"total": 0, "free": 0, "needs_keys": 0, "installable": 0})
        cats[c]["total"] += 1
        if t["free"]:
            cats[c]["free"] += 1
        if t["env_keys"]:
            cats[c]["needs_keys"] += 1
        if t.get("install_cmd"):
            cats[c]["installable"] += 1
    return {
        "ok": True,
        "total_tools": len(CATALOG),
        "categories": cats,
        "vault_keys": len(vault_list()),
    }


async def tool_universe_credentials_required(tool: str = "", set_key: str = "", set_value: str = "") -> Dict[str, Any]:
    """List missing credentials, or set one in the vault."""
    # Setter mode
    if set_key and set_value:
        vault_set(set_key, set_value)
        return {"ok": True, "set": set_key, "stored_in": "vault"}
    # Specific tool
    if tool:
        t = find_tool(tool)
        if not t:
            return {"ok": False, "error": f"ما لقيت '{tool}'"}
        missing = [k for k in t["env_keys"] if not vault_get(k)]
        return {
            "ok": True,
            "tool": t["id"],
            "required_keys": t["env_keys"],
            "missing_keys": missing,
            "ready": not missing,
            "docs_url": t["docs_url"],
        }
    # All tools
    needs: List[Dict[str, Any]] = []
    for t in CATALOG.values():
        if not t["env_keys"]:
            continue
        missing = [k for k in t["env_keys"] if not vault_get(k)]
        if missing:
            needs.append({"id": t["id"], "name": t["name"], "missing": missing, "docs": t["docs_url"]})
    return {
        "ok": True,
        "tools_needing_keys": len(needs),
        "items": needs[:80],  # cap to avoid bloating LLM context
    }


# ════════════════════════════════════════════════════════════════════════
# Multi-tool planner — give the AI structured chain suggestions
# ════════════════════════════════════════════════════════════════════════
PLAN_TEMPLATES = {
    # canonical multi-tool recipes the AI can reference / extend
    "rag-pipeline": {
        "goal": "Retrieval-Augmented Generation pipeline",
        "steps": ["sentence-transformers", "faiss", "fastapi", "openai"],
        "notes": "Embed → store in FAISS → query top-k → feed to GPT-4o.",
    },
    "image-saas": {
        "goal": "Image generation SaaS",
        "steps": ["fastapi", "stripe", "supabase", "stable-diffusion", "minio", "vercel"],
        "notes": "Frontend on Vercel, backend FastAPI, Stripe payments, Supabase auth+db, SD generation, MinIO storage.",
    },
    "video-saas": {
        "goal": "Video generation SaaS",
        "steps": ["fastapi", "ffmpeg", "fal.ai", "stripe", "supabase", "cloudflare-stream"],
        "notes": "FAL for generation, FFmpeg for post-processing, Cloudflare Stream for delivery.",
    },
    "agent-platform": {
        "goal": "Agent orchestration platform",
        "steps": ["langgraph", "redis", "postgresql", "langsmith", "fastapi", "react"],
        "notes": "LangGraph + Redis for state, Postgres for persistence, LangSmith tracing.",
    },
    "mobile-app": {
        "goal": "Cross-platform mobile app",
        "steps": ["expo", "react-native", "supabase", "stripe"],
        "notes": "Expo + RN with Supabase backend.",
    },
    "ecommerce-store": {
        "goal": "Headless e-commerce store",
        "steps": ["nextjs", "medusajs", "stripe", "sanity", "vercel"],
        "notes": "Next.js storefront, Medusa backend, Sanity for content.",
    },
    "ai-coder": {
        "goal": "AI coding agent",
        "steps": ["anthropic", "openai", "groq", "gemini", "langgraph", "aider"],
        "notes": "Multi-LLM coder with LangGraph orchestration.",
    },
    "web3-dapp": {
        "goal": "Web3 dApp",
        "steps": ["nextjs", "rainbowkit", "ethers", "hardhat", "thirdweb"],
        "notes": "Wallet connect, smart contract dev, on-chain interactions.",
    },
}


async def tool_universe_plan(goal: str = "", template: str = "") -> Dict[str, Any]:
    """Get a recommended multi-tool execution plan. Either use a known
    template (rag-pipeline, image-saas, video-saas, agent-platform, mobile-app,
    ecommerce-store, ai-coder, web3-dapp) or pass a free-form `goal` to get
    keyword-based recommendations."""
    if template and template in PLAN_TEMPLATES:
        plan = PLAN_TEMPLATES[template]
        steps_detailed = []
        for sid in plan["steps"]:
            t = find_tool(sid)
            if t:
                steps_detailed.append({
                    "id": t["id"], "name": t["name"], "category": t["category"],
                    "install_cmd": t["install_cmd"], "env_keys": t["env_keys"],
                })
        return {"ok": True, "template": template, "goal": plan["goal"],
                "steps": steps_detailed, "notes": plan["notes"]}
    if not goal:
        return {"ok": True, "available_templates": list(PLAN_TEMPLATES.keys())}

    # keyword-driven recommendation
    g = goal.lower()
    KEYWORDS = {
        "rag": "rag-pipeline", "search": "rag-pipeline", "knowledge": "rag-pipeline",
        "image": "image-saas", "صورة": "image-saas", "صور": "image-saas",
        "video": "video-saas", "فيديو": "video-saas",
        "agent": "agent-platform", "وكيل": "agent-platform",
        "mobile": "mobile-app", "تطبيق": "mobile-app", "android": "mobile-app", "ios": "mobile-app",
        "shop": "ecommerce-store", "متجر": "ecommerce-store", "ecommerce": "ecommerce-store",
        "coder": "ai-coder", "code": "ai-coder", "برمجة": "ai-coder",
        "web3": "web3-dapp", "blockchain": "web3-dapp", "crypto": "web3-dapp",
    }
    suggested = None
    for kw, tpl in KEYWORDS.items():
        if kw in g:
            suggested = tpl
            break
    # also free-form keyword hits across catalog
    hits = search_catalog(goal, limit=10)
    if suggested:
        plan = PLAN_TEMPLATES[suggested]
        return {
            "ok": True,
            "matched_template": suggested,
            "goal": plan["goal"],
            "suggested_tools": plan["steps"],
            "notes": plan["notes"],
            "extra_matches": [{"id": h["id"], "name": h["name"]} for h in hits[:5]],
        }
    return {
        "ok": True,
        "goal": goal,
        "no_template_matched": True,
        "candidates": [{"id": h["id"], "name": h["name"], "category": h["category"]} for h in hits],
        "hint": "نقدر نبني plan مخصّص؛ راجع المرشّحات أعلاه واختر مزيج مناسب.",
    }


# ════════════════════════════════════════════════════════════════════════
# Vault tool wrappers
# ════════════════════════════════════════════════════════════════════════
async def tool_vault_list() -> Dict[str, Any]:
    return {"ok": True, "items": vault_list()}


async def tool_vault_set(key: str, value: str) -> Dict[str, Any]:
    if not key or not value:
        return {"ok": False, "error": "key وvalue مطلوبين"}
    vault_set(key, value)
    return {"ok": True, "set": key}


async def tool_vault_delete(key: str) -> Dict[str, Any]:
    return {"ok": vault_delete(key), "deleted": key}


# ════════════════════════════════════════════════════════════════════════
# Anthropic tool schema for the AI
# ════════════════════════════════════════════════════════════════════════
UNIVERSE_ANTHROPIC_TOOLS: List[Dict[str, Any]] = [
    {
        "name": "tool_universe_search",
        "description": ("Search the catalog of 300+ tools (LLMs, DBs, cloud, payments, image/video gen, agents, ...). "
                       "Pass `query` (e.g. 'vector db', 'payments', 'whisper') and/or `category`. Returns id/name/type/needs_keys."),
        "input_schema": {"type": "object", "properties": {
            "query": {"type": "string"}, "category": {"type": "string"},
            "limit": {"type": "integer", "description": "1-50, default 20"},
        }, "required": []},
    },
    {
        "name": "tool_universe_info",
        "description": "Full metadata for a single tool: install_cmd, env_keys, docs_url, install status, credential status, ready_to_use.",
        "input_schema": {"type": "object", "properties": {"tool": {"type": "string"}}, "required": ["tool"]},
    },
    {
        "name": "tool_universe_install",
        "description": ("Actually install a tool (pip / yarn / apt / curl). Set dry_run=true to preview. "
                       "Skips if already installed."),
        "input_schema": {"type": "object", "properties": {
            "tool": {"type": "string"},
            "dry_run": {"type": "boolean"},
            "timeout": {"type": "integer", "description": "seconds, default 180"},
        }, "required": ["tool"]},
    },
    {
        "name": "tool_universe_status",
        "description": "Overall ecosystem status (categories, counts, vault). Pass `tool` to get info for one specific tool.",
        "input_schema": {"type": "object", "properties": {"tool": {"type": "string"}}, "required": []},
    },
    {
        "name": "tool_universe_credentials_required",
        "description": ("List tools whose required API keys are missing. Or check one specific tool. "
                       "Or set a credential (set_key + set_value)."),
        "input_schema": {"type": "object", "properties": {
            "tool": {"type": "string"},
            "set_key": {"type": "string"},
            "set_value": {"type": "string"},
        }, "required": []},
    },
    {
        "name": "tool_universe_plan",
        "description": ("Get a ready-made multi-tool execution plan for common goals. "
                       "Either pass `template` (rag-pipeline | image-saas | video-saas | agent-platform | "
                       "mobile-app | ecommerce-store | ai-coder | web3-dapp) or a free-form `goal`."),
        "input_schema": {"type": "object", "properties": {
            "goal": {"type": "string"}, "template": {"type": "string"},
        }, "required": []},
    },
    {
        "name": "vault_list",
        "description": "List credential entries (env + vault). Never returns raw values — only key/source/length.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "vault_set",
        "description": "Store a credential (API key / token) in the on-disk vault. Persists across restarts.",
        "input_schema": {"type": "object", "properties": {
            "key": {"type": "string"}, "value": {"type": "string"},
        }, "required": ["key", "value"]},
    },
    {
        "name": "vault_delete",
        "description": "Delete a credential from the vault.",
        "input_schema": {"type": "object", "properties": {"key": {"type": "string"}}, "required": ["key"]},
    },
]

UNIVERSE_TOOL_DEFS: List[Dict[str, Any]] = [
    {"name": "tool_universe_search", "desc": "search 300+ catalog", "args": ["query?", "category?", "limit?"]},
    {"name": "tool_universe_info", "desc": "single tool details", "args": ["tool"]},
    {"name": "tool_universe_install", "desc": "actually install pkg/cli", "args": ["tool", "dry_run?", "timeout?"]},
    {"name": "tool_universe_status", "desc": "global / per-tool status", "args": ["tool?"]},
    {"name": "tool_universe_credentials_required", "desc": "missing keys / set key", "args": ["tool?", "set_key?", "set_value?"]},
    {"name": "tool_universe_plan", "desc": "multi-tool plan / templates", "args": ["goal?", "template?"]},
    {"name": "vault_list", "desc": "list creds", "args": []},
    {"name": "vault_set", "desc": "store credential", "args": ["key", "value"]},
    {"name": "vault_delete", "desc": "delete credential", "args": ["key"]},
]


# Map name → coroutine handler (registered in __init__.py)
UNIVERSE_TOOL_HANDLERS = {
    "tool_universe_search": tool_universe_search,
    "tool_universe_info": tool_universe_info,
    "tool_universe_install": tool_universe_install,
    "tool_universe_status": tool_universe_status,
    "tool_universe_credentials_required": tool_universe_credentials_required,
    "tool_universe_plan": tool_universe_plan,
    "vault_list": tool_vault_list,
    "vault_set": tool_vault_set,
    "vault_delete": tool_vault_delete,
}


# ════════════════════════════════════════════════════════════════════════
# Summarize / preview hooks
# ════════════════════════════════════════════════════════════════════════
def universe_summarize(name: str, result: Dict[str, Any]) -> Optional[str]:
    if not result.get("ok", True):
        return f"فشل: {(result.get('error') or '')[:120]}"
    if name == "tool_universe_search":
        return f"{result.get('count', 0)} أداة (من {result.get('total_in_catalog', 0)})"
    if name == "tool_universe_info":
        t = result.get("tool", {})
        return f"{t.get('name')} • {t.get('type')} • installed={result.get('installed')} • ready={result.get('ready_to_use')}"
    if name == "tool_universe_install":
        if result.get("already_installed"):
            return f"{result.get('tool')} — مثبّت مسبقاً ✓"
        if result.get("dry_run"):
            return f"dry-run: {result.get('would_run', '')[:80]}"
        return f"exit={result.get('exit_code')} • installed_after={result.get('installed_after')}"
    if name == "tool_universe_status":
        return f"{result.get('total_tools')} أداة في {len(result.get('categories', {}))} فئة"
    if name == "tool_universe_credentials_required":
        if result.get("missing_keys") is not None:
            return f"missing={len(result.get('missing_keys', []))} • ready={result.get('ready')}"
        if result.get("set"):
            return f"حُفظ المفتاح: {result.get('set')}"
        return f"{result.get('tools_needing_keys', 0)} أداة تحتاج مفاتيح"
    if name == "tool_universe_plan":
        if result.get("matched_template"):
            return f"plan: {result['matched_template']} ({len(result.get('suggested_tools', []))} أدوات)"
        if result.get("template"):
            return f"template {result['template']}: {len(result.get('steps', []))} خطوات"
        if result.get("candidates"):
            return f"{len(result['candidates'])} مرشّح"
        return "قائمة قوالب جاهزة"
    if name == "vault_list":
        return f"{len(result.get('items', []))} مفتاح في الخزنة"
    if name in ("vault_set", "vault_delete"):
        return f"تم — {result.get('set') or result.get('deleted')}"
    return None


def universe_preview(name: str, result: Dict[str, Any]) -> Optional[str]:
    if not result.get("ok") and result.get("error"):
        return result["error"][:300]
    if name == "tool_universe_search":
        return "\n".join(
            f"• {t['id']} — {t['name']} [{t['category']}] {'🔑' if t.get('needs_keys') else ''}"
            for t in result.get("tools", [])[:10]
        )
    if name == "tool_universe_info":
        t = result.get("tool", {})
        lines = [f"📦 {t.get('name')} ({t.get('id')})", f"   category: {t.get('category')} • type: {t.get('type')}"]
        if t.get("install_cmd"):
            lines.append(f"   install: {t['install_cmd'][:100]}")
        if t.get("env_keys"):
            lines.append(f"   keys: {', '.join(t['env_keys'])}")
        if t.get("docs_url"):
            lines.append(f"   docs: {t['docs_url']}")
        return "\n".join(lines)
    if name == "tool_universe_install":
        return ((result.get("stdout_tail") or "") + "\n--\n" + (result.get("stderr_tail") or ""))[:600]
    if name == "tool_universe_plan":
        ks = result.get("steps") or result.get("suggested_tools") or []
        if ks and isinstance(ks[0], dict):
            return "\n".join(f"  {i+1}. {s['name']} — {s.get('install_cmd', '—')[:60]}" for i, s in enumerate(ks))
        return "\n".join(f"  {i+1}. {sid}" for i, sid in enumerate(ks))
    if name == "tool_universe_credentials_required":
        items = result.get("items", [])
        if items:
            return "\n".join(f"• {it['name']}: missing {', '.join(it['missing'])}" for it in items[:10])
        if result.get("missing_keys"):
            return "missing: " + ", ".join(result["missing_keys"])
        return None
    if name == "vault_list":
        return "\n".join(f"• {it['key']} [{it['source']}]" for it in result.get("items", [])[:12])
    return None


# ════════════════════════════════════════════════════════════════════════
# System-prompt builder (compact)
# ════════════════════════════════════════════════════════════════════════
def build_universe_for_prompt(max_lines: int = 100) -> str:
    """Compact summary injected into the AI's system prompt."""
    cats: Dict[str, int] = {}
    for t in CATALOG.values():
        cats[t["category"]] = cats.get(t["category"], 0) + 1
    lines = [
        "",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"🧰 Tools Universe — {len(CATALOG)} أداة عملية مسجّلة في {len(cats)} فئة",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "تقدر تثبّت أي أداة وتشغّلها فعلياً عبر:",
        "  • tool_universe_search(query, category?)   — استكشاف",
        "  • tool_universe_info(tool)                 — تفاصيل + هل مثبّتة",
        "  • tool_universe_install(tool)              — تثبيت حقيقي (pip/yarn/apt/curl)",
        "  • tool_universe_credentials_required(tool) — هل ناقصها مفتاح؟",
        "  • tool_universe_plan(goal=...)             — خطة متعددة الأدوات جاهزة",
        "  • vault_set(key, value)                    — خزن المفتاح في خزنة محلية",
        "",
        "الفئات المتاحة (مع العدد):",
    ]
    for cat in sorted(cats.keys()):
        lines.append(f"  • {cat} ({cats[cat]})")
    lines += [
        "",
        "قواعد ذكية:",
        "  1. قبل ما تكتب كود يدوي لتكامل، نادي tool_universe_search لتشوف إذا فيه أداة جاهزة.",
        "  2. الأدوات اللي type=service_paid أو لها env_keys تحتاج مفتاح — اطلبه من المالك.",
        "  3. مفاتيح env أولاً، بعدها vault، بعدها اطلب من المالك صراحة.",
        "  4. لأي مشروع كبير، نادي tool_universe_plan(goal=...) عشان تحصل خطة متعددة الأدوات.",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "",
    ]
    return "\n".join(lines[:max_lines * 3])

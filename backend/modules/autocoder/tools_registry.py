"""
Tools Registry — comprehensive catalog of 300+ tools the AI knows about.

This registry is loaded into the system prompt so the AI has structural
knowledge of every tool available in the modern dev/AI ecosystem.
The AI doesn't need each one wired as a callable tool — it can build
integrations on-the-fly using `web_search` + `fetch_url` + `run_command`
(yarn add / pip install) when a task requires a specific service.

Categories are grouped to keep token cost low while preserving discoverability.
"""

# ════════════════════════════════════════════════════════════════════════
# 🤖 LLM PROVIDERS — main brains
# ════════════════════════════════════════════════════════════════════════
LLM_PROVIDERS = [
    "OpenAI (GPT-5.5, GPT-5.4-codex, GPT-4o, o3, o4-mini)",
    "Anthropic Claude (Sonnet 4.5, Opus 4.5, Haiku 4.5)",
    "Google Gemini (2.5 Flash, 2.5 Pro, 3 Pro)",
    "Meta Llama (3.3 70B, 3.1 405B)",
    "Mistral AI (Large, Codestral, Mixtral)",
    "DeepSeek (V3, Coder)",
    "Cohere (Command R+, Embed v3)",
    "xAI Grok (Grok-2, Grok-3)",
    "Perplexity AI (Sonar)",
    "You.com (Smart, Genius)",
    "Poe (multi-model platform)",
]

# ════════════════════════════════════════════════════════════════════════
# 🚪 LLM GATEWAYS & ROUTERS — unified access to many models
# ════════════════════════════════════════════════════════════════════════
LLM_GATEWAYS = [
    "OpenRouter (300+ models via 1 API)",
    "Groq (free Llama/Mixtral, ultra-fast)",
    "Together AI (open-source models)",
    "Replicate (any model as API)",
    "Baseten (deploy custom models)",
    "Fireworks AI (fast inference)",
    "Inference.net (cheap GPU)",
    "Hugging Face (model hub + inference)",
    "LiteLLM (router/proxy layer)",
    "Portkey AI Gateway (cost optim + routing)",
    "Cloudflare AI Gateway",
]

# ════════════════════════════════════════════════════════════════════════
# 🤖 AGENT FRAMEWORKS — multi-step autonomous AI
# ════════════════════════════════════════════════════════════════════════
AGENT_FRAMEWORKS = [
    "LangChain", "LangGraph", "LangSmith",
    "LlamaIndex", "Haystack",
    "CrewAI", "CrewAI AMP",
    "AutoGen", "Semantic Kernel",
    "DSPy", "PydanticAI",
    "OpenAI Agents SDK", "Mastra AI",
    "SuperAGI", "AgentGPT", "BabyAGI",
    "MetaGPT", "CAMEL AI", "OpenAgents", "Swarms AI",
    "AutoGPT", "OpenHands",
]

# ════════════════════════════════════════════════════════════════════════
# 💻 AI CODE ASSISTANTS & CODER AGENTS
# ════════════════════════════════════════════════════════════════════════
CODE_AGENTS = [
    "Continue.dev", "Aider", "Cursor", "Windsurf",
    "GitHub Copilot", "Codeium", "Tabnine",
    "Sourcegraph Cody", "Blackbox AI", "Mutable AI",
    "Sweep AI", "GPT Engineer", "Smol Developer",
    "Open Interpreter",
    "Devin AI", "OpenDevin",
    "Replit AI", "Bolt.new", "Lovable", "v0 by Vercel",
]

# ════════════════════════════════════════════════════════════════════════
# 🖥️ IDEs & DEV ENVIRONMENTS
# ════════════════════════════════════════════════════════════════════════
DEV_ENVIRONMENTS = [
    "VS Code", "JetBrains IDEs", "NeoVim",
    "Jupyter", "Google Colab", "Kaggle",
]

# ════════════════════════════════════════════════════════════════════════
# 🧠 LOCAL/SELF-HOSTED LLM RUNTIMES
# ════════════════════════════════════════════════════════════════════════
LOCAL_LLM_RUNTIMES = [
    "Ollama", "LM Studio", "Open WebUI",
    "AnythingLLM", "LibreChat", "Jan AI",
    "vLLM", "llama.cpp", "GPT4All",
    "Flowise", "Dify", "Langflow",
]

# ════════════════════════════════════════════════════════════════════════
# 🛡️ LLM OBSERVABILITY, EVAL & GUARDRAILS
# ════════════════════════════════════════════════════════════════════════
LLM_OPS = [
    "Humanloop", "PromptLayer", "Promptfoo",
    "Ragas", "DeepEval", "TruLens",
    "Guardrails AI", "Outlines", "Instructor",
]

# ════════════════════════════════════════════════════════════════════════
# 🧮 ML/DL FRAMEWORKS & TOOLING
# ════════════════════════════════════════════════════════════════════════
ML_FRAMEWORKS = [
    "PyTorch", "TensorFlow", "Keras", "JAX",
    "ONNX", "CUDA", "TensorRT", "OpenVINO",
    "Triton Inference Server",
    "Weights & Biases", "MLflow", "ClearML", "Comet ML",
]

# ════════════════════════════════════════════════════════════════════════
# 🔤 NLP & EMBEDDINGS
# ════════════════════════════════════════════════════════════════════════
NLP_TOOLS = [
    "FastEmbed", "Sentence Transformers",
    "spaCy", "NLTK", "Gensim",
]

# ════════════════════════════════════════════════════════════════════════
# 🗃️ VECTOR DATABASES & SEARCH
# ════════════════════════════════════════════════════════════════════════
VECTOR_DBS = [
    "FAISS", "Annoy",
    "Pinecone", "Qdrant", "Weaviate", "Milvus", "ChromaDB",
    "Redis Vector Similarity", "pgvector",
]

SEARCH_ENGINES = [
    "Elasticsearch", "OpenSearch", "Meilisearch", "Typesense",
    "Algolia",
]

# ════════════════════════════════════════════════════════════════════════
# 🛢️ DATABASES
# ════════════════════════════════════════════════════════════════════════
DATABASES = [
    "PostgreSQL", "MongoDB", "MySQL",
    "Redis",
    "Supabase", "Firebase", "Appwrite", "PocketBase",
    "PlanetScale", "Neon",
    "Prisma (ORM)", "Drizzle ORM",
]

# ════════════════════════════════════════════════════════════════════════
# 🐳 DEVOPS & INFRASTRUCTURE
# ════════════════════════════════════════════════════════════════════════
DEVOPS = [
    "Docker", "Kubernetes", "Helm",
    "Terraform", "Pulumi", "Ansible",
    "Jenkins", "GitHub Actions", "GitLab CI/CD", "ArgoCD",
]

# ════════════════════════════════════════════════════════════════════════
# 📊 OBSERVABILITY & MONITORING
# ════════════════════════════════════════════════════════════════════════
OBSERVABILITY = [
    "Prometheus", "Grafana", "Datadog", "Sentry",
    "OpenTelemetry", "Jaeger", "Zipkin",
    "Grafana Loki", "VictoriaMetrics",
]

# ════════════════════════════════════════════════════════════════════════
# ☁️ CLOUD PLATFORMS & DEPLOYMENT
# ════════════════════════════════════════════════════════════════════════
CLOUD_PLATFORMS = [
    "AWS", "Google Cloud", "Microsoft Azure",
    "Amazon Bedrock", "Google Vertex AI", "Azure AI",
    "Cloudflare", "Cloudflare Workers",
    "Vercel", "Netlify", "Railway", "Render", "Fly.io", "DigitalOcean",
]

# ════════════════════════════════════════════════════════════════════════
# 🌐 WEB SERVERS & REVERSE PROXIES
# ════════════════════════════════════════════════════════════════════════
WEB_SERVERS = [
    "NGINX", "Apache HTTP Server", "Caddy Server", "Traefik",
    "Linux", "Ubuntu Server",
]

# ════════════════════════════════════════════════════════════════════════
# 💾 STORAGE
# ════════════════════════════════════════════════════════════════════════
STORAGE = [
    "MinIO", "SeaweedFS", "Ceph Storage",
]

# ════════════════════════════════════════════════════════════════════════
# 📬 MESSAGE QUEUES, STREAMING & WORKFLOW ORCHESTRATION
# ════════════════════════════════════════════════════════════════════════
QUEUES_AND_WORKFLOWS = [
    "RabbitMQ", "Apache Kafka", "Kafka Connect", "NATS",
    "BullMQ", "Temporal", "Temporal Cloud", "Celery",
    "Apache Spark", "Apache Flink", "Apache Beam",
    "Airflow", "Dagster", "Prefect", "dbt", "Ray",
]

# ════════════════════════════════════════════════════════════════════════
# 🔌 API TOOLS & PROTOCOLS
# ════════════════════════════════════════════════════════════════════════
API_TOOLS = [
    "Postman", "Insomnia", "Swagger", "OpenAPI",
    "gRPC", "GraphQL", "Apollo GraphQL", "Hasura",
    "Socket.IO", "Socket Cluster", "PeerJS", "WebRTC",
]

# ════════════════════════════════════════════════════════════════════════
# 🎙️ VOICE, VIDEO & REAL-TIME COMMUNICATION
# ════════════════════════════════════════════════════════════════════════
REALTIME_AV = [
    "LiveKit", "Agora", "Twilio", "Vonage API",
    "Daily.co", "Mux Video", "Cloudflare Stream",
]

# ════════════════════════════════════════════════════════════════════════
# 🎬 COMPUTER VISION & VIDEO PROCESSING
# ════════════════════════════════════════════════════════════════════════
CV_AND_VIDEO = [
    "FFmpeg", "OpenCV", "MediaPipe",
    "Roboflow", "Ultralytics YOLO", "Detectron2",
    "Segment Anything Model", "Grounding DINO", "SAM2",
    "OpenMMLab", "CVAT", "Label Studio",
]

# ════════════════════════════════════════════════════════════════════════
# 🎨 IMAGE GENERATION & EDITING
# ════════════════════════════════════════════════════════════════════════
IMAGE_GEN = [
    "ComfyUI", "ComfyUI Manager", "Automatic1111",
    "Fooocus", "InvokeAI",
    "Stable Diffusion", "Midjourney", "Leonardo AI",
    "Ideogram", "Adobe Firefly", "Canva AI",
    "ControlNet", "IP Adapter", "LoRA", "DreamBooth",
    "PhotoMaker", "InstantID", "FaceFusion", "Roop AI",
]

# ════════════════════════════════════════════════════════════════════════
# 🎥 VIDEO GENERATION
# ════════════════════════════════════════════════════════════════════════
VIDEO_GEN = [
    "Runway", "Pika Labs", "Luma AI",
    "Synthesia", "HeyGen", "Kaiber",
    "AnimateDiff", "Animate Anyone",
]

# ════════════════════════════════════════════════════════════════════════
# 🎮 3D, GAMES & ANIMATION
# ════════════════════════════════════════════════════════════════════════
GAMES_AND_3D = [
    "Blender", "Unity", "Unreal Engine", "Godot Engine",
    "NVIDIA Omniverse", "Meshy AI", "Spline",
    "Three.js", "Babylon.js", "React Three Fiber",
    "Rive", "LottieFiles", "Framer Motion", "GSAP", "Anime.js",
]

# ════════════════════════════════════════════════════════════════════════
# 🎨 FRONTEND FRAMEWORKS & UI KITS
# ════════════════════════════════════════════════════════════════════════
FRONTEND_FRAMEWORKS = [
    "React", "Next.js", "Vue.js", "Nuxt",
    "SvelteKit", "Angular", "Astro", "Remix",
    "Tailwind CSS", "Shadcn UI",
]

# ════════════════════════════════════════════════════════════════════════
# 📱 MOBILE & CROSS-PLATFORM
# ════════════════════════════════════════════════════════════════════════
MOBILE_FRAMEWORKS = [
    "Expo", "React Native", "Flutter",
    "Capacitor", "Electron", "Tauri",
]

# ════════════════════════════════════════════════════════════════════════
# 🟢 BACKEND FRAMEWORKS & RUNTIMES
# ════════════════════════════════════════════════════════════════════════
BACKEND_FRAMEWORKS = [
    "Node.js", "Bun", "Deno",
    "FastAPI", "NestJS", "Express.js", "Hono", "tRPC",
    "TypeScript", "Zod",
]

# ════════════════════════════════════════════════════════════════════════
# 🧪 TESTING, LINTING & QA
# ════════════════════════════════════════════════════════════════════════
QUALITY_TOOLS = [
    "ESLint", "Prettier", "Vitest", "Playwright",
    "Cypress", "Jest", "Storybook",
]

# ════════════════════════════════════════════════════════════════════════
# 🛠️ BUILD TOOLS & BUNDLERS
# ════════════════════════════════════════════════════════════════════════
BUILD_TOOLS = [
    "Vite", "Rspack", "Webpack", "Parcel",
    "Babel", "TurboPack", "Turborepo", "Nx Monorepo",
    "pnpm", "Yarn", "Biome", "SWC",
]

# ════════════════════════════════════════════════════════════════════════
# 🔄 NO-CODE & WORKFLOW AUTOMATION
# ════════════════════════════════════════════════════════════════════════
NO_CODE_AUTOMATION = [
    "n8n", "Zapier AI", "Make", "Pipedream",
    "Retool AI", "ToolJet",
    "Bubble", "FlutterFlow",
    "Framer AI", "Webflow AI",
    "Figma AI", "Penpot", "Uizard",
    "Galileo AI", "Locofy", "Builder.io",
]

# ════════════════════════════════════════════════════════════════════════
# 📝 CMS & DOCUMENTATION
# ════════════════════════════════════════════════════════════════════════
CMS_AND_DOCS = [
    "Sanity CMS", "Strapi", "Contentful", "Directus",
    "Payload CMS", "Ghost CMS", "WordPress Headless",
    "Docusaurus", "Mintlify", "Nextra", "Astro Starlight",
]

# ════════════════════════════════════════════════════════════════════════
# 🔐 AUTHENTICATION
# ════════════════════════════════════════════════════════════════════════
AUTH_PROVIDERS = [
    "Clerk", "Auth0", "Better Auth",
    "FusionAuth", "Keycloak", "Magic.link",
]

# ════════════════════════════════════════════════════════════════════════
# 💳 PAYMENTS & E-COMMERCE
# ════════════════════════════════════════════════════════════════════════
PAYMENTS_AND_COMMERCE = [
    "Stripe", "PayPal Developer", "Lemon Squeezy",
    "Shopify Hydrogen", "WooCommerce", "Saleor",
    "Magento Adobe Commerce", "MedusaJS",
]

# ════════════════════════════════════════════════════════════════════════
# 📋 PRODUCTIVITY & COLLABORATION
# ════════════════════════════════════════════════════════════════════════
PRODUCTIVITY = [
    "Airtable", "Notion AI", "Obsidian", "ClickUp AI",
    "Slack AI", "Discord Developer Platform",
    "Linear", "Jira", "Confluence", "Trello",
    "Asana", "Monday.com",
]

# ════════════════════════════════════════════════════════════════════════
# 📈 ANALYTICS & SESSION REPLAY
# ════════════════════════════════════════════════════════════════════════
ANALYTICS = [
    "PostHog", "Plausible Analytics", "Umami Analytics",
    "Mixpanel", "Amplitude", "Hotjar",
    "LogRocket", "FullStory",
]

# ════════════════════════════════════════════════════════════════════════
# 🗺️ MAPS & GEOSPATIAL
# ════════════════════════════════════════════════════════════════════════
MAPS_AND_GEO = [
    "Mapbox", "Leaflet", "CesiumJS",
    "OpenStreetMap", "QGIS", "ArcGIS", "OpenDroneMap",
]

# ════════════════════════════════════════════════════════════════════════
# 🤖 ROBOTICS, RL & SIMULATION
# ════════════════════════════════════════════════════════════════════════
ROBOTICS_AND_RL = [
    "ROS Robotics", "NVIDIA Isaac Sim",
    "OpenAI Gym", "Gymnasium",
    "Stable Baselines3", "RLlib",
    "PyBullet", "MuJoCo", "Isaac Gym", "Habitat AI",
]

# ════════════════════════════════════════════════════════════════════════
# 🥽 AR / VR / XR
# ════════════════════════════════════════════════════════════════════════
AR_VR_XR = [
    "ARCore", "ARKit", "Vision Pro SDK",
    "OpenXR", "WebXR",
]

# ════════════════════════════════════════════════════════════════════════
# ⛓️ WEB3 & BLOCKCHAIN
# ════════════════════════════════════════════════════════════════════════
WEB3 = [
    "Ethereum", "Solidity",
    "Hardhat", "Foundry",
    "Thirdweb", "Moralis",
    "WalletConnect", "RainbowKit",
    "Web3.js", "Ethers.js",
]


# ════════════════════════════════════════════════════════════════════════
# 🎯 Master list — bring it all together for the system prompt
# ════════════════════════════════════════════════════════════════════════
ALL_CATEGORIES = {
    "🤖 LLM Providers": LLM_PROVIDERS,
    "🚪 LLM Gateways": LLM_GATEWAYS,
    "🤖 Agent Frameworks": AGENT_FRAMEWORKS,
    "💻 AI Code Assistants": CODE_AGENTS,
    "🖥️ Dev Environments": DEV_ENVIRONMENTS,
    "🧠 Local LLM Runtimes": LOCAL_LLM_RUNTIMES,
    "🛡️ LLM Ops & Eval": LLM_OPS,
    "🧮 ML/DL Frameworks": ML_FRAMEWORKS,
    "🔤 NLP Tools": NLP_TOOLS,
    "🗃️ Vector Databases": VECTOR_DBS,
    "🔍 Search Engines": SEARCH_ENGINES,
    "🛢️ Databases": DATABASES,
    "🐳 DevOps & IaC": DEVOPS,
    "📊 Observability": OBSERVABILITY,
    "☁️ Cloud Platforms": CLOUD_PLATFORMS,
    "🌐 Web Servers": WEB_SERVERS,
    "💾 Storage": STORAGE,
    "📬 Queues & Workflows": QUEUES_AND_WORKFLOWS,
    "🔌 API Tools": API_TOOLS,
    "🎙️ Realtime A/V": REALTIME_AV,
    "🎬 Computer Vision": CV_AND_VIDEO,
    "🎨 Image Generation": IMAGE_GEN,
    "🎥 Video Generation": VIDEO_GEN,
    "🎮 Games & 3D": GAMES_AND_3D,
    "🎨 Frontend Frameworks": FRONTEND_FRAMEWORKS,
    "📱 Mobile Frameworks": MOBILE_FRAMEWORKS,
    "🟢 Backend Frameworks": BACKEND_FRAMEWORKS,
    "🧪 Quality & Testing": QUALITY_TOOLS,
    "🛠️ Build Tools": BUILD_TOOLS,
    "🔄 No-Code & Automation": NO_CODE_AUTOMATION,
    "📝 CMS & Docs": CMS_AND_DOCS,
    "🔐 Auth Providers": AUTH_PROVIDERS,
    "💳 Payments & Commerce": PAYMENTS_AND_COMMERCE,
    "📋 Productivity": PRODUCTIVITY,
    "📈 Analytics": ANALYTICS,
    "🗺️ Maps & GeoSpatial": MAPS_AND_GEO,
    "🤖 Robotics & RL": ROBOTICS_AND_RL,
    "🥽 AR/VR/XR": AR_VR_XR,
    "⛓️ Web3 & Blockchain": WEB3,
}


def build_tools_registry_for_prompt(compact: bool = False) -> str:
    """Generate the registry section for the system prompt.

    Args:
        compact: If True, list only category names + counts (for very limited
                 context windows). If False, list all tool names grouped.
    """
    total = sum(len(items) for items in ALL_CATEGORIES.values())

    if compact:
        lines = [
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            f"🧰 سجل الأدوات المعرفية ({total} أداة في {len(ALL_CATEGORIES)} فئة)",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "أنت على علم بكل أداة من القائمة أدناه. استخدم `tools_registry_query(category)` لتفاصيل أعمق.",
            "",
        ]
        for cat in ALL_CATEGORIES.keys():
            lines.append(f"  • {cat} ({len(ALL_CATEGORIES[cat])})")
        return "\n".join(lines) + "\n"

    lines = [
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"🧰 سجل الأدوات المعرفية الشامل ({total} أداة)",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "أنت تعرف بكل أداة من القائمة أدناه. لما تحتاج تكامل جديد:",
        "  1. حدّد الأداة الصح من القائمة",
        "  2. استخدم `web_search` للحصول على وثائقها الحالية",
        "  3. استخدم `run_command` لـ`yarn add` / `pip install`",
        "  4. لو محتاج API key، اطلبه من المالك صراحةً",
        "  5. اطبّق التكامل بـ`write_file` / `edit_file`",
        "",
    ]
    for cat, items in ALL_CATEGORIES.items():
        lines.append(f"\n{cat}:")
        # Comma-separated for compactness
        lines.append("  " + " · ".join(items))
    return "\n".join(lines) + "\n"


def query_registry(category_keyword: str) -> dict:
    """Used by the `tools_registry_query` AI tool. Returns matching tools."""
    if not category_keyword:
        return {
            "ok": True,
            "categories": list(ALL_CATEGORIES.keys()),
            "total_tools": sum(len(v) for v in ALL_CATEGORIES.values()),
            "hint": "أعد الاستدعاء بـcategory_keyword (مثل 'auth', 'image', 'database')",
        }

    keyword = category_keyword.lower().strip()
    matches = {}
    for cat, items in ALL_CATEGORIES.items():
        if keyword in cat.lower():
            matches[cat] = items
        else:
            # Also search inside tool names
            matching_items = [t for t in items if keyword in t.lower()]
            if matching_items:
                matches[cat] = matching_items

    if not matches:
        return {
            "ok": False,
            "error": f"ما لقيت شي يطابق '{category_keyword}'",
            "hint": "جرّب كلمات: llm, agent, vector, db, deploy, payment, auth, image, video, 3d, mobile, web3",
        }

    return {
        "ok": True,
        "query": category_keyword,
        "matches": matches,
        "total_matches": sum(len(v) for v in matches.values()),
    }

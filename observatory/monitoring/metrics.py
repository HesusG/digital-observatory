from prometheus_client import Counter, Histogram, Gauge

items_collected = Counter(
    "observatory_items_collected_total",
    "Total items collected",
    ["source", "source_type"],
)

items_deduplicated = Counter(
    "observatory_items_deduplicated_total",
    "Items skipped as duplicates",
    ["source"],
)

items_evaluated = Counter(
    "observatory_items_evaluated_total",
    "Items evaluated by LLM",
    ["source"],
)

items_high_affinity = Counter(
    "observatory_items_high_affinity_total",
    "Items with affinity score >= 8",
    ["source"],
)

notifications_sent = Counter(
    "observatory_notifications_sent_total",
    "Notifications sent",
    ["channel"],
)

obsidian_notes_created = Counter(
    "observatory_obsidian_notes_created_total",
    "Obsidian notes created",
)

collector_errors = Counter(
    "observatory_collector_errors_total",
    "Collector errors",
    ["source", "error_type"],
)

llm_errors = Counter(
    "observatory_llm_errors_total",
    "LLM evaluation errors",
    ["provider"],
)

collection_duration = Histogram(
    "observatory_collection_duration_seconds",
    "Time to run a collector",
    ["source"],
)

llm_evaluation_duration = Histogram(
    "observatory_llm_evaluation_duration_seconds",
    "Time for LLM evaluation",
    ["provider"],
)

pipeline_duration = Histogram(
    "observatory_pipeline_duration_seconds",
    "End-to-end pipeline duration per item",
)

chromadb_items_count = Gauge(
    "observatory_chromadb_items_count",
    "Total items in ChromaDB",
)

ollama_available = Gauge(
    "observatory_ollama_available",
    "Whether Ollama is reachable (1=yes, 0=no)",
)

# LLM Integration Debugging & Refactoring Plan

This document outlines the detailed findings and a comprehensive, step-by-step refactoring plan to resolve the LLM ingestion issues and prevent error-related tags from polluting the user interface.

---

## 🔍 Steel Thread Codebase Review & Root Cause Analysis

After performing a thorough review of the codebase's ETL and ingestion pipeline, we identified **two critical issues** that caused the massive "llm-failed 208 turns" bug in the GUI:

### 1. The LLM Failure Chain Reaction (Why 208 turns & 125 URLs failed)
Our analysis of the database states (`pipeline_tasks.json`) revealed that the vast majority of LLM enrichments failed with one of two errors:
*   `Error code: 400 - {'error': {'message': "No models loaded. Please load a model in the developer page."}}`
*   `Error code: 400 - {'error': 'Context size has been exceeded.'}`

#### 🔬 How the Failure Chain Occurred:
1.  **The Settings Bug (`max_tokens`)**: In [lms_settings_service.py](file:///Users/idaneyal/DEV/personal_momory/backend/services/lms_settings_service.py), the `max_tokens` field defaults to `128000`. 
    *   *Concept Confusion*: The developer confused **Context Window Length** (which can be 128k for modern models like Gemma-2 or Llama-3) with `max_tokens` (which controls the maximum number of *generated* tokens in the response).
2.  **Context Size Exceeded**: In [llm_engine.py](file:///Users/idaneyal/DEV/personal_momory/core/llm_engine.py#L70), the OpenAI completions call passes `max_tokens=max_tokens` (resolving to `128000` from settings) to LM Studio.
    *   LM Studio attempts to reserve slot capacity for generating up to 128,000 tokens. When combined with the input prompt/text length, this exceeds the total context capacity allocated by the server, resulting in a `400 Context size has been exceeded` error.
3.  **Model Ejection & Memory Exhaustion**: Overwhelmed by excessive token-generation allocation requests, the local server (LM Studio) experienced memory exhaustion (or crashed) and ejected/unloaded the model.
4.  **No Models Loaded**: Once the model was ejected, subsequent calls failed with `No models loaded`.
5.  **Ineffective Auto-Recovery**: Although [llm_engine.py](file:///Users/idaneyal/DEV/personal_momory/core/llm_engine.py#L79) tries to detect model ejection and trigger auto-loading via `ensure_model_loaded()`, the code interprets *any* `400` status as a loading issue. Furthermore, because `max_tokens=128000` was still sent in the next attempt, the model would immediately crash/eject again, resulting in a permanent failure loop.
6.  **Fallback Tagging**: When all 3 retries failed, the pipeline fell back to returning `tags: ["error", "llm-failed"]`, saving this into the vectors and metadata.

---

### 2. Error Tag Pollution in UI Categories (Why "llm-failed" shows up in Category Densities)
In [main.py](file:///Users/idaneyal/DEV/personal_momory/main.py#L444), the vector store metadata combining segment-level tags and all webpage-level tags is defined as:
```python
"tags": ", ".join(list(set(seg.tags + all_web_tags))),
"categories": ", ".join(list(set(all_web_categories)))
```
Because 125 URLs failed LLM enrichment, they were tagged with `"llm-failed"` and `"error"`. These tags propagated up to the parent conversational segments.

In [gap_service.py](file:///Users/idaneyal/DEV/personal_momory/backend/services/gap_service.py#L19), the heatmap calculation aggregates density counts from these metadata tags:
```python
# Filter out standard system errors
ignored = {"error", "connection-failed", "scraped-web", "unparsed-json"}
for item in combined:
    if item not in ignored and not item.startswith("seg-"):
        heatmap[item] = heatmap.get(item, 0) + 1
```
*   **The UI Bug**: `"llm-failed"`, `"crawl-failed"`, `"segment-failed"`, and `"uncategorized"` are **not** present in the `ignored` set.
*   As a result, `"llm-failed"` was counted as a legitimate category, appearing at the very top of the **Category Densities** sidebar with "208 turns".

---

## 🛠️ Step-by-Step Refactoring Plan

We propose a robust, production-grade refactoring plan to fix both the root causes of the LLM failures and the UI category pollution.

### Phase 1: Fix Settings & LLM Generation Limits (Backend)
To stop the memory allocation crashes and context limit errors, we will adjust the generation token limits.

#### 1. Modify [lms_settings_service.py](file:///Users/idaneyal/DEV/personal_momory/backend/services/lms_settings_service.py)
*   Update the default `max_tokens` field from `128000` to a sensible value for text generation: `2048` tokens. This is more than enough for summaries and tags while preventing allocation overflows.
```python
# Change from:
# max_tokens: int = Field(default=128000, gt=0)
# Change to:
max_tokens: int = Field(default=2048, gt=0)
```

#### 2. Modify [llm_engine.py](file:///Users/idaneyal/DEV/personal_momory/core/llm_engine.py)
*   Enforce a defensive fallback value inside `_execute_completion_with_fallback` so that if `max_tokens` is configured too high in settings, the code limits it to `4096` to protect LM Studio from crashing.
*   Refine `is_model_error` logic to avoid treating generic bad requests (like parameter errors or context exceeded) as model-ejection events.
```python
# Ensure max_tokens is set defensively for text generation
if max_tokens is None or max_tokens > 4096:
    max_tokens = 2048
```

---

### Phase 2: Refilter Heatmap Categories (UI & Services)
To prevent system failures or fallback states from displaying as categories in the frontend dashboard, we will expand our tag filtering mechanism.

#### 1. Modify [gap_service.py](file:///Users/idaneyal/DEV/personal_momory/backend/services/gap_service.py)
*   Expand the `ignored` set in `calculate_category_heatmap()` and `detect_knowledge_gaps()` to filter out all technical errors and fallbacks:
```python
ignored = {
    "error", 
    "connection-failed", 
    "scraped-web", 
    "unparsed-json", 
    "llm-failed", 
    "crawl-failed", 
    "segment-failed", 
    "uncategorized"
}
```

---

### Phase 3: Validation & Database Rebuild (Verification)
After implementing the changes, we need to rebuild the database to clear out the polluted metadata and verify that the LLM pipeline runs successfully.

#### 1. Re-run Ingestion Pipeline with Reset
*   Run `run.sh --reset` to clear the existing pipeline state, wipe out the old ChromaDB collection, and re-trigger a clean ingest.
```bash
./run.sh --reset
```
*   Verify that:
    1. The LLM indexer runs successfully for all 224 turns without crashing.
    2. URL enrichments complete without ejection or "context size exceeded" errors.
    3. The number of failed LLM interactions drops to 0 (or near-zero).

#### 2. Verify Frontend GUI
*   Launch the web interface:
```bash
./run_web.sh
```
*   Check that:
    1. The "llm-failed" item no longer appears in the Category Densities list.
    2. Clean categories like `Software-Engineering`, `AI-Agent`, `Database`, etc., occupy the top slots.
    3. The Knowledge Gap Map visualizes meaningful categories instead of error clusters.

---

## 📈 Long-term Resiliency Recommendations
1.  **JSON Mode**: If the local LLM engine supports it (e.g. llama.cpp or latest LM Studio), configure the client to use `response_format={"type": "json_object"}` to guarantee structurally valid JSON outputs and eliminate `JSONDecodeError` fallbacks.
2.  **API Fallbacks**: Add an optional fallback route (e.g., to OpenAI API or another local model) if the primary local model remains unavailable after auto-load attempts.

# Context & Objectives: Customizable LM Studio Settings, Prompts, & Multi-Model Routing

You are continuing work on the WhatsApp Context RAG Insights Explorer app. Your task is to build Phase 2 of the LM Studio Integration: exposing customizable settings, system prompt customizers, and task-specific model routing inside the application.

---

## 1. App Context & Current Architecture
The application parses a WhatsApp chat log (`chat.txt`), groups it into chronological turns, crawls scraped webpage URLs asynchronously, serially compiles LLM summaries/tags, indexes everything into a local ChromaDB vector store, and provides a conversational RAG interface.

### Key Technologies:
* **Backend**: FastAPI, Pydantic, OpenAI Python client, official `lmstudio` SDK (for VRAM model load/unload management), ChromaDB.
* **Frontend**: Vite React, TypeScript, Glassmorphic CSS.

### Current LM Studio Integration Files:
1. **[config.py](file:///Users/idaneyal/DEV/personal_momory/config.py)**: Centralizes all settings. Default LLM name is `"google/gemma-4-e2b"`. Has `lms_sdk_enabled: bool` and `lms_model_key: str`.
2. **[core/llm_engine.py](file:///Users/idaneyal/DEV/personal_momory/core/llm_engine.py)**: Houses `LMStudioHermesClient`. Features:
   * `ensure_model_loaded()`: Uses `lmstudio` SDK to automatically load the target model if ejected.
   * `_execute_completion_with_fallback()`: centralizes inferences, catches `400`/`404` ejection errors, auto-loads the model via SDK, and transparently retries.
3. **[backend/routers/metadata.py](file:///Users/idaneyal/DEV/personal_momory/backend/routers/metadata.py)**: Exposes endpoints for client management:
   * `GET /api/lms/models`: Returns list of currently loaded and downloaded models.
   * `POST /api/lms/model/load`: Loads a model key in memory.
   * `POST /api/lms/model/unload`: Unloads a model to free VRAM.
4. **[frontend/src/App.tsx](file:///Users/idaneyal/DEV/personal_momory/frontend/src/App.tsx)**: Displays the **LM Studio Manager** sidebar widget with live load/unload actions, badges, spinners, and toast notifications.

---

## 2. Goals of the Next Phase (The Dev Plan)

### Objective A: Customizable Settings & sliders in GUI
1. **Frontend**:
   * Add a settings subsection inside the LM Studio Manager widget.
   * Expose controls for `Temperature` (slider, range 0.0 to 1.0) and `Max Output Tokens` (number input).
2. **API & Persistence**:
   * Add a `POST /api/lms/settings` endpoint.
   * Persist user-customized settings in a JSON file `output/lms_settings.json` so they survive server restarts.
   * Read this file on backend startup and override `config` defaults.
3. **Engine Integration**:
   * Update `core/llm_engine.py` methods to dynamically load these saved settings during completion calls.

### Objective B: System Prompt customization Personas
1. **Frontend**:
   * Design a premium system prompt editor inside the sidebar panel or a settings modal.
   * Allow users to write and save customized system prompts for two distinct tasks:
     * **ETL Extraction Prompt**: Used during turn summarization.
     * **RAG Search Persona Prompt**: Used during prose answer synthesis.
2. **API & Engine**:
   * Persist custom prompts inside `output/lms_settings.json`.
   * Pass custom prompts dynamically into `LMStudioHermesClient.enrich_message_segment`, `summarize_text`, and the search query synthesizers.

### Objective C: Task-Specific Multi-Model Routing
1. **Goal**: Allow users to run lightweight models for fast background tasks (scrapers/parsers) and smart models for search synthesis.
2. **Implementation**:
   * Expose dropdown selectors in the GUI to choose the **ETL Model** and the **Search Model** from the available downloaded models list.
   * Persist routing choices in `output/lms_settings.json`.
   * Update the client logic in `core/llm_engine.py` to route completion queries to the appropriate model based on the active task, triggering auto-load/unload fallbacks for whichever model is needed.

---

## 3. Implementation Steps for the Agent

### Step 1: Centralize Settings Schema & Persistence
* Create a file `backend/services/lms_settings_service.py` to manage loading, saving, and validating settings stored in `output/lms_settings.json`.
* Schema fields:
  ```json
  {
    "temperature_segment": 0.2,
    "temperature_webpage": 0.2,
    "temperature_search": 0.3,
    "max_tokens": 1024,
    "prompt_etl": "Your custom segment system prompt here...",
    "prompt_search": "Your custom search persona prompt here...",
    "routing_etl_model": "nvidia/nemotron-3-nano-4b",
    "routing_search_model": "google/gemma-4-e2b"
  }
  ```

### Step 2: Implement Backend API Routers
* Inside `backend/routers/metadata.py`:
  * Add `GET /api/lms/settings` to retrieve settings.
  * Add `POST /api/lms/settings` to update settings.
  * Update `GET /api/lms/models` to include current active routing settings.

### Step 3: Refactor the LLM Engine Wrapper
* Update `LMStudioHermesClient` in `core/llm_engine.py`:
  * Load active settings from `lms_settings_service.py` dynamically before each completions call.
  * Inject the appropriate custom system prompts and temperatures.
  * Support model routing: change target model dynamically based on the operation and run `ensure_model_loaded(target_model)` fallback dynamically before each run.

### Step 4: Expand Frontend UI Widgets
* Update `frontend/src/App.tsx`:
  * Build a collapsible "Advanced Settings" drawer or block.
  * Include sliders for temperatures, inputs for tokens, and textareas for prompt customization.
  * Expose dropdowns to map ETL vs. Search models.
  * Connect settings changes to live API triggers and verify Toast feedback.

---

## 4. Verification & Resiliency Guidelines
* **Graceful Degradation**: If `lms_sdk_enabled` is False (remote API modes), the settings inputs should still allow configuring temperatures/prompts but hide model load/unload/routing selectors.
* **Test Suite**:
  * Add unit tests in `tests/test_llm_engine.py` to verify prompt injection and routing.
  * Add integration tests in `tests/test_api.py` for `/api/lms/settings` endpoints.
  * Run `PYTHONPATH=. .venv/bin/pytest` and make sure all tests are green.
  * Verify frontend compiles cleanly using `npm run build` from the `frontend` folder.

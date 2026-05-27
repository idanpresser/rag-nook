import re
import json
import threading
from typing import Dict, Any, List
from openai import OpenAI
from config import config
from backend.services.lms_settings_service import settings_service, LMStudioSettings

class LMStudioHermesClient:
    """A resilient local LLM client designed to interface with LM Studio running Nous Hermes.

    Supports structured JSON extraction, fallback clean-up parsers, and text summarization.
    """

    def __init__(self):
        # API agnostic client initialization supporting OpenAI, LM Studio, Ollama, etc.
        self.client = OpenAI(
            base_url=config.llm_base_url,
            api_key=config.llm_api_key,
            timeout=config.llm_timeout
        )
        self.model_name = config.llm_model_name
        self._lock = threading.Lock()

    def ensure_model_loaded(self, model_name: str = None) -> bool:
        """Uses the official lmstudio Python SDK to check and programmatically load the target model if ejected."""
        if not config.lms_sdk_enabled:
            return False
            
        if model_name is None:
            settings = settings_service.load_settings()
            model_name = settings.routing_etl_model
            
        try:
            import lmstudio as lms
            # Get list of currently loaded models
            loaded = lms.list_loaded_models()
            loaded_ids = [m.identifier for m in loaded]
            
            if model_name not in loaded_ids:
                print(f"[LMStudio SDK] Target model '{model_name}' is not loaded. Loading it now...")
                lms.llm(model_name)
                print(f"[LMStudio SDK] Successfully loaded '{model_name}'!")
                return True
            return True
        except Exception as e:
            print(f"[LMStudio SDK] Failed to verify/load model '{model_name}' using SDK. Error: {str(e)}")
            return False

    def _execute_completion_with_fallback(self, messages: List[Dict[str, str]], temperature: float, model_name: str = None, max_tokens: int = None) -> Any:
        """Executes a chat completion call. If a model-ejected or model-not-loaded error occurs,
        attempts to load the model via the lmstudio SDK and retries.
        """
        settings = settings_service.load_settings()
        if model_name is None:
            model_name = settings.routing_etl_model
            
        if max_tokens is None:
            max_tokens = min(settings.max_tokens, 4096)
        else:
            max_tokens = min(max_tokens, 4096)

        # Proactively ensure the model is loaded up front if using local LM Studio with SDK enabled
        if config.lms_sdk_enabled:
            self.ensure_model_loaded(model_name)

        import openai
        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            try:
                with self._lock:
                    return self.client.chat.completions.create(
                        model=model_name,
                        messages=messages,
                        temperature=temperature,
                        max_tokens=max_tokens
                    )
            except Exception as e:
                err_str = str(e)
                # Detect standard model loaded / ejected issues
                is_model_error = any(word in err_str.lower() for word in [
                    "model not loaded", "not found", "ejected", "no model", "load a model"
                ])
                if is_model_error and config.lms_sdk_enabled and attempt < max_attempts:
                    print(f"[LMStudio SDK] Model connection issue detected ('{err_str}'). Triggering auto-load...")
                    if self.ensure_model_loaded(model_name):
                        import time
                        time.sleep(2)
                        continue
                raise e

    def summarize_text(self, text: str) -> str:
        """Sends raw text to the local LLM to generate a concise summary.

        Args:
            text: The text string to summarize (e.g. scraped HTML or Markdown).

        Returns:
            A clean summary string.
        """
        # Limit text length dynamically to avoid context overflow in small local models
        truncated_text = text[:config.max_web_text_length]
        
        settings = settings_service.load_settings()
        system_prompt = settings.prompt_etl
        if system_prompt == LMStudioSettings.model_fields['prompt_etl'].default:
            system_prompt = "You are a professional research assistant and expert text summarizer."
            
        user_prompt = (
            "Provide a highly objective, concise summary (maximum 150 words) "
            "of the following web article or document content. "
            "Focus only on key factual insights, developer tools, or specific topics discussed.\n\n"
            f"Content:\n{truncated_text}"
        )

        try:
            response = self._execute_completion_with_fallback(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=settings.temperature_webpage,
                model_name=settings.routing_etl_model
            )
            content = response.choices[0].message.content or ""
            return content.strip()
        except Exception as e:
            return f"Summary generation failed. Error: {str(e)}"

    def enrich_message_segment(self, segment_text: str) -> Dict[str, Any]:
        """Queries the local Hermes model to enrich a conversation turn with an executive summary and tags.

        Includes a multi-layered JSON recovery parser and robust 3x retries.

        Args:
            segment_text: The compiled text of a conversational turn.

        Returns:
            A dictionary containing 'executive_summary' (str) and 'tags' (list of str).
        """
        settings = settings_service.load_settings()
        system_prompt = settings.prompt_etl
        
        user_prompt = (
            "Analyze the following conversation segment (which may contain mixed Hebrew and English terms, links, or notes).\n"
            "Provide a one-sentence executive summary highlighting the primary intent (in English or Hebrew as appropriate).\n"
            "Provide a list of 3-5 tags representing key topics, projects, or categories.\n\n"
            f"Conversation Segment:\n{segment_text}\n\n"
            "Format your response EXACTLY as a valid JSON object matching this schema:\n"
            "{\n"
            '  "executive_summary": "Single sentence summarizing the segment.",\n'
            '  "tags": ["topic-1", "topic-2", "topic-3"]\n'
            "}"
        )

        import time
        max_retries = config.llm_max_retries
        last_exception = None

        for attempt in range(1, max_retries + 1):
            try:
                response = self._execute_completion_with_fallback(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=settings.temperature_segment,
                    model_name=settings.routing_etl_model
                )
                raw_content = response.choices[0].message.content or ""
                raw_content = raw_content.strip()
                
                # Attempt direct parse to verify clean JSON format
                parsed = json.loads(raw_content)
                if "executive_summary" in parsed and "tags" in parsed:
                    return parsed
                raise ValueError("JSON missing required keys 'executive_summary' or 'tags'")
            except Exception as e:
                last_exception = e
                # Fallback to resilient parser in case of minor wrapper syntax issues
                try:
                    if 'raw_content' in locals():
                        parsed = self._resilient_json_parse(raw_content, segment_text)
                        if parsed.get("tags") != ["error", "unparsed-json"]:
                            return parsed
                except Exception:
                    pass
                
                if attempt < max_retries:
                    time.sleep(config.llm_retry_backoff_factor * attempt)

        # Complete recovery fallback if all 3 retries failed
        clean_text = re.sub(r"\s+", " ", segment_text).strip()
        short_summary = clean_text[:80] + "..." if len(clean_text) > 80 else clean_text
        return {
            "executive_summary": f"Raw log review (LLM failed after {max_retries} attempts. Error: {str(last_exception)}): {short_summary}",
            "tags": ["error", "llm-failed"]
        }

    def _resilient_json_parse(self, raw_content: str, fallback_text: str) -> Dict[str, Any]:
        """A robust, multi-layer JSON extractor that handles markdown backticks and incomplete formatting."""
        try:
            # Layer 1: Try direct parse
            return json.loads(raw_content)
        except json.JSONDecodeError:
            pass

        # Layer 2: Strip markdown code blocks if the LLM wrapped the JSON
        # Pattern matches ```json ... ``` or ``` ... ```
        block_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw_content, re.DOTALL)
        if block_match:
            try:
                return json.loads(block_match.group(1))
            except json.JSONDecodeError:
                pass

        # Layer 3: Regex extract the outermost curly braces
        braces_match = re.search(r"(\{.*\})", raw_content, re.DOTALL)
        if braces_match:
            try:
                return json.loads(braces_match.group(1))
            except json.JSONDecodeError:
                pass

        # Layer 4: Complete recovery fallback
        # If everything fails, extract a simple sentence and tag it as error
        clean_text = re.sub(r"\s+", " ", fallback_text).strip()
        short_summary = clean_text[:80] + "..." if len(clean_text) > 80 else clean_text
        
        return {
            "executive_summary": f"Raw log review: {short_summary}",
            "tags": ["error", "unparsed-json"],
            "raw_response": raw_content
        }

    def enrich_webpage_content(self, webpage_markdown: str) -> Dict[str, Any]:
        """Queries the local Hermes model to analyze scraped web page markdown and generate structured metadata.

        Includes a robust 3x retry mechanism and complete parsing safeguards.

        Args:
            webpage_markdown: The markdown content of the scraped webpage.

        Returns:
            A dictionary containing 'executive_summary' (str), 'tags' (list of str), and 'categories' (list of str).
        """
        # Check if the webpage markdown represents a failed crawl
        if not webpage_markdown or "Unable to crawl webpage content" in webpage_markdown or "Crawl failed" in webpage_markdown:
            return {
                "executive_summary": "No summary available. Webpage crawl failed due to a connection or formatting issue.",
                "tags": ["error", "crawl-failed"],
                "categories": ["error"]
            }

        # Limit text length to avoid context overflow in small local models
        truncated_text = webpage_markdown[:config.max_web_text_length]

        settings = settings_service.load_settings()
        system_prompt = settings.prompt_etl
        if system_prompt == LMStudioSettings.model_fields['prompt_etl'].default:
            system_prompt = (
                "You are a structured database enrichment assistant.\n"
                "Your sole job is to analyze webpage content and return a valid JSON object.\n"
                "Do NOT include any introduction, markdown wrapping (such as ```json ... ```), explanation, or trailing text.\n"
                "Return raw, valid JSON only."
            )

        user_prompt = (
            "Analyze the following scraped webpage content.\n"
            "Provide a concise executive summary highlighting key factual insights (maximum 150 words).\n"
            "Provide a list of 3-5 tags representing specific topics, frameworks, or tools.\n"
            "Provide a list of 1-3 categories representing the broader domain (e.g. AI-Agent, Software-Engineering, Personal-Finance).\n\n"
            f"Webpage Content:\n{truncated_text}\n\n"
            "Format your response EXACTLY as a valid JSON object matching this schema:\n"
            "{\n"
            '  "executive_summary": "Concise summary of the page.",\n'
            '  "tags": ["tag-1", "tag-2", "tag-3"],\n'
            '  "categories": ["category-1", "category-2"]\n'
            "}"
        )

        import time
        max_retries = config.llm_max_retries
        last_exception = None

        for attempt in range(1, max_retries + 1):
            try:
                response = self._execute_completion_with_fallback(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=settings.temperature_webpage,
                    model_name=settings.routing_etl_model
                )
                raw_content = response.choices[0].message.content or ""
                raw_content = raw_content.strip()
                
                # Verify JSON parses correctly
                parsed = json.loads(raw_content)
                if "executive_summary" in parsed and "tags" in parsed:
                    if "categories" not in parsed:
                        parsed["categories"] = ["uncategorized"]
                    return parsed
                raise ValueError("JSON missing required keys 'executive_summary', 'tags', or 'categories'")
            except Exception as e:
                last_exception = e
                # Fallback to resilient webpage parser
                try:
                    if 'raw_content' in locals():
                        parsed = self._resilient_json_parse_webpage(raw_content, webpage_markdown)
                        if parsed.get("tags") != ["error", "unparsed-json"]:
                            return parsed
                except Exception:
                    pass
                
                if attempt < max_retries:
                    time.sleep(1.5 * attempt)

        # Complete recovery fallback if all 3 retries failed
        clean_text = re.sub(r"\s+", " ", webpage_markdown).strip()
        short_summary = clean_text[:80] + "..." if len(clean_text) > 80 else clean_text
        return {
            "executive_summary": f"Webpage review (LLM failed after {max_retries} attempts. Error: {str(last_exception)}): {short_summary}",
            "tags": ["error", "llm-failed"],
            "categories": ["error"]
        }

    def _resilient_json_parse_webpage(self, raw_content: str, fallback_text: str) -> Dict[str, Any]:
        """A robust, multi-layer JSON extractor that handles markdown backticks and incomplete formatting for webpages."""
        try:
            # Layer 1: Try direct parse
            obj = json.loads(raw_content)
            if "categories" not in obj:
                obj["categories"] = ["uncategorized"]
            return obj
        except json.JSONDecodeError:
            pass

        # Layer 2: Strip markdown code blocks if the LLM wrapped the JSON
        block_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw_content, re.DOTALL)
        if block_match:
            try:
                obj = json.loads(block_match.group(1))
                if "categories" not in obj:
                    obj["categories"] = ["uncategorized"]
                return obj
            except json.JSONDecodeError:
                pass

        # Layer 3: Regex extract the outermost curly braces
        braces_match = re.search(r"(\{.*\})", raw_content, re.DOTALL)
        if braces_match:
            try:
                obj = json.loads(braces_match.group(1))
                if "categories" not in obj:
                    obj["categories"] = ["uncategorized"]
                return obj
            except json.JSONDecodeError:
                pass

        # Layer 4: Complete recovery fallback
        clean_text = re.sub(r"\s+", " ", fallback_text).strip()
        short_summary = clean_text[:80] + "..." if len(clean_text) > 80 else clean_text
        
        return {
            "executive_summary": f"Webpage review: {short_summary}",
            "tags": ["error", "unparsed-json"],
            "categories": ["error"],
            "raw_response": raw_content
        }

    def synthesize_answer(self, query: str, context_text: str) -> str:
        """Synthesizes a RAG search answer using retrieved context and search settings."""
        settings = settings_service.load_settings()
        system_prompt = settings.prompt_search
        
        user_prompt = (
            f"User Query: {query}\n\n"
            f"Retrieved Context Sources:\n{context_text}\n\n"
            "Synthesize a cohesive, high-density Hero Answer (maximum 200 words) using these sources. "
            "Make sure to place citations [1], [2] at the end of sentences that reference each specific source."
        )

        response = self._execute_completion_with_fallback(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=settings.temperature_search,
            model_name=settings.routing_search_model
        )
        return (response.choices[0].message.content or "").strip()


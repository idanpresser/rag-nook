import re
import json
import threading
from typing import Dict, Any, List
from openai import OpenAI
from config import config

class LMStudioHermesClient:
    """A resilient local LLM client designed to interface with LM Studio running Nous Hermes.

    Supports structured JSON extraction, fallback clean-up parsers, and text summarization.
    """

    def __init__(self):
        # LM Studio exposes an OpenAI-compatible endpoint locally
        # Use a timeout of 180.0 seconds to allow local model inference time
        self.client = OpenAI(
            base_url=config.lm_studio_base_url,
            api_key=config.lm_studio_api_key,
            timeout=180.0
        )
        self.model_name = config.llm_model_name
        self._lock = threading.Lock()

    def summarize_text(self, text: str) -> str:
        """Sends raw text to the local LLM to generate a concise summary.

        Args:
            text: The text string to summarize (e.g. scraped HTML or Markdown).

        Returns:
            A clean summary string.
        """
        # Limit text length to avoid context overflow in small local models
        truncated_text = text[:8000]
        
        system_prompt = "You are a professional research assistant and expert text summarizer."
        user_prompt = (
            "Provide a highly objective, concise summary (maximum 150 words) "
            "of the following web article or document content. "
            "Focus only on key factual insights, developer tools, or specific topics discussed.\n\n"
            f"Content:\n{truncated_text}"
        )

        try:
            with self._lock:
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.3
                )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"Summary generation failed. Error: {str(e)}"

    def enrich_message_segment(self, segment_text: str) -> Dict[str, Any]:
        """Queries the local Hermes model to enrich a conversation turn with an executive summary and tags.

        Includes a multi-layered JSON recovery parser.

        Args:
            segment_text: The compiled text of a conversational turn.

        Returns:
            A dictionary containing 'executive_summary' (str) and 'tags' (list of str).
        """
        system_prompt = (
            "You are a structured database enrichment assistant. "
            "Your sole job is to analyze conversational inputs and return a valid JSON object. "
            "You must strictly follow the requested schema and do not output any surrounding conversation."
        )
        
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

        try:
            with self._lock:
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.2,
                    response_format={"type": "text"}
                )
            raw_content = response.choices[0].message.content.strip()
        except Exception as e:
            # Safe boundary fallback in case of connection errors
            return {
                "executive_summary": f"Failed to connect to local LLM server. Error: {str(e)}",
                "tags": ["error", "connection-failed"],
                "raw_response": ""
            }

        return self._resilient_json_parse(raw_content, segment_text)

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

        Args:
            webpage_markdown: The markdown content of the scraped webpage.

        Returns:
            A dictionary containing 'executive_summary' (str), 'tags' (list of str), and 'categories' (list of str).
        """
        # Limit text length to avoid context overflow in small local models
        truncated_text = webpage_markdown[:8000]

        system_prompt = (
            "You are a structured database enrichment assistant. "
            "Your sole job is to analyze webpage content and return a valid JSON object. "
            "You must strictly follow the requested schema and do not output any surrounding conversation."
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

        try:
            with self._lock:
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.2,
                    response_format={"type": "text"}
                )
            raw_content = response.choices[0].message.content.strip()
        except Exception as e:
            return {
                "executive_summary": f"Failed to connect to local LLM server. Error: {str(e)}",
                "tags": ["error", "connection-failed"],
                "categories": ["error"],
                "raw_response": ""
            }

        return self._resilient_json_parse_webpage(raw_content, webpage_markdown)

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


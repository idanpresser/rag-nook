import pytest
import json
from core.llm_engine import LMStudioHermesClient

def test_summarize_text(mocker):
    # Mock the OpenAI client completion return
    mock_choices = [
        mocker.Mock(message=mocker.Mock(content="This is a summary of the web page."))
    ]
    mock_response = mocker.Mock(choices=mock_choices)
    
    # Patch the OpenAI client's chat.completions.create method
    mocker.patch("openai.resources.chat.completions.Completions.create", return_value=mock_response)
    
    client = LMStudioHermesClient()
    summary = client.summarize_text("Raw crawled text...")
    
    assert summary == "This is a summary of the web page."

def test_enrich_message_segment_success(mocker):
    json_data = {
        "executive_summary": "Shopping notes and preparation lists for Alon.",
        "tags": ["personal-lists", "shopping", "gifts"]
    }
    mock_choices = [
        mocker.Mock(message=mocker.Mock(content=json.dumps(json_data)))
    ]
    mock_response = mocker.Mock(choices=mock_choices)
    mocker.patch("openai.resources.chat.completions.Completions.create", return_value=mock_response)
    
    client = LMStudioHermesClient()
    result = client.enrich_message_segment("מצעים\nפחים\nברכה לאלון")
    
    assert result["executive_summary"] == "Shopping notes and preparation lists for Alon."
    assert "shopping" in result["tags"]
    assert "gifts" in result["tags"]

def test_enrich_message_segment_fallback_markdown(mocker):
    # Mock a response wrapped in markdown code blocks
    markdown_response = (
        "```json\n"
        "{\n"
        '  "executive_summary": "List of books and tech articles.",\n'
        '  "tags": ["books", "github", "coding"]\n'
        "}\n"
        "```"
    )
    mock_choices = [
        mocker.Mock(message=mocker.Mock(content=markdown_response))
    ]
    mock_response = mocker.Mock(choices=mock_choices)
    mocker.patch("openai.resources.chat.completions.Completions.create", return_value=mock_response)
    
    client = LMStudioHermesClient()
    result = client.enrich_message_segment("Brave new world\nfree programming books")
    
    assert result["executive_summary"] == "List of books and tech articles."
    assert "books" in result["tags"]
    assert "coding" in result["tags"]

def test_enrich_message_segment_invalid_json(mocker):
    # Mock a completely broken text response
    mock_choices = [
        mocker.Mock(message=mocker.Mock(content="Here is your analysis: It contains list items and stuff."))
    ]
    mock_response = mocker.Mock(choices=mock_choices)
    mocker.patch("openai.resources.chat.completions.Completions.create", return_value=mock_response)
    
    client = LMStudioHermesClient()
    result = client.enrich_message_segment("מצעים\nפחים")
    
    # Verify that the system recovered gracefully without throwing an exception
    assert "executive_summary" in result
    assert "tags" in result
    assert "error" in result["tags"] or "raw_response" in result

def test_enrich_webpage_content_success(mocker):
    json_data = {
        "executive_summary": "Guide on building production-grade LLM applications.",
        "tags": ["llm", "agents", "langchain"],
        "categories": ["AI-Agent", "Software-Engineering"]
    }
    mock_choices = [
        mocker.Mock(message=mocker.Mock(content=json.dumps(json_data)))
    ]
    mock_response = mocker.Mock(choices=mock_choices)
    mocker.patch("openai.resources.chat.completions.Completions.create", return_value=mock_response)
    
    client = LMStudioHermesClient()
    result = client.enrich_webpage_content("Building agents in production...")
    
    assert result["executive_summary"] == "Guide on building production-grade LLM applications."
    assert "agents" in result["tags"]
    assert "AI-Agent" in result["categories"]

def test_enrich_webpage_content_fallback(mocker):
    # Mock completely broken JSON response to test resilient recovery
    mock_choices = [
        mocker.Mock(message=mocker.Mock(content="Unstructured raw content response from the model."))
    ]
    mock_response = mocker.Mock(choices=mock_choices)
    mocker.patch("openai.resources.chat.completions.Completions.create", return_value=mock_response)
    
    client = LMStudioHermesClient()
    result = client.enrich_webpage_content("Building agents in production...")
    
    assert "executive_summary" in result
    assert "tags" in result
    assert "categories" in result
    assert "error" in result["tags"]
    assert "error" in result["categories"]

def test_ensure_model_loaded_sdk_disabled(mocker):
    mocker.patch("core.llm_engine.config.lms_sdk_enabled", False)
    
    client = LMStudioHermesClient()
    result = client.ensure_model_loaded("google/gemma-4-e2b")
    assert result is False

def test_ensure_model_loaded_sdk_enabled_loaded(mocker):
    mocker.patch("core.llm_engine.config.lms_sdk_enabled", True)
    
    mock_loaded = [mocker.Mock(identifier="google/gemma-4-e2b")]
    mocker.patch("lmstudio.list_loaded_models", return_value=mock_loaded)
    
    client = LMStudioHermesClient()
    result = client.ensure_model_loaded("google/gemma-4-e2b")
    assert result is True

def test_ensure_model_loaded_sdk_enabled_not_loaded(mocker):
    mocker.patch("core.llm_engine.config.lms_sdk_enabled", True)
    
    mock_loaded = [mocker.Mock(identifier="nvidia/nemotron-3-nano-4b")]
    mocker.patch("lmstudio.list_loaded_models", return_value=mock_loaded)
    mock_llm = mocker.patch("lmstudio.llm", return_value=mocker.Mock())
    
    client = LMStudioHermesClient()
    result = client.ensure_model_loaded("google/gemma-4-e2b")
    assert result is True
    mock_llm.assert_called_once_with("google/gemma-4-e2b")

def test_synthesize_answer(mocker):
    mock_choices = [
        mocker.Mock(message=mocker.Mock(content="Here is a RAG search response."))
    ]
    mock_response = mocker.Mock(choices=mock_choices)
    mock_fallback = mocker.patch("core.llm_engine.LMStudioHermesClient._execute_completion_with_fallback", return_value=mock_response)
    
    client = LMStudioHermesClient()
    answer = client.synthesize_answer("test query", "retrieved context chunks")
    
    assert answer == "Here is a RAG search response."
    mock_fallback.assert_called_once()


def test_summarize_image_success(mocker, tmp_path):
    img_path = tmp_path / "test_vlm.jpg"
    img_path.write_bytes(b"dummy image bytes")

    mock_choices = [
        mocker.Mock(message=mocker.Mock(content="This image shows ענתי קרמון sitting at a clinic."))
    ]
    mock_response = mocker.Mock(choices=mock_choices)
    mocker.patch("openai.resources.chat.completions.Completions.create", return_value=mock_response)

    client = LMStudioHermesClient()
    result = client.summarize_image(img_path, prompt="Describe this image")

    assert result == "This image shows ענתי קרמון sitting at a clinic."


def test_summarize_image_non_existent():
    client = LMStudioHermesClient()
    with pytest.raises(FileNotFoundError):
        client.summarize_image("non_existent_vlm_img.avif")


def test_summarize_image_error(mocker, tmp_path):
    img_path = tmp_path / "error_vlm.jpg"
    img_path.write_bytes(b"dummy")

    mocker.patch("openai.resources.chat.completions.Completions.create", side_effect=Exception("API Timeout"))

    client = LMStudioHermesClient()
    result = client.summarize_image(img_path)

    assert "failed" in result.lower()
    assert "API Timeout" in result



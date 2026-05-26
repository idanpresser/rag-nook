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

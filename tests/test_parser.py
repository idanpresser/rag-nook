import pytest
from pathlib import Path
from core.parser import WhatsAppParser, RawMessage

def test_parse_simple_message(temp_workspace):
    chat_file = temp_workspace["chat_file"]
    content = "3/1/24, 06:56 - Idan P: מצעים\n"
    chat_file.write_text(content, encoding="utf-8")
    
    parser = WhatsAppParser()
    messages = parser.parse_file(str(chat_file))
    
    assert len(messages) == 1
    msg = messages[0]
    assert msg.date_str == "3/1/24"
    assert msg.time_str == "06:56"
    assert msg.sender == "Idan P"
    assert msg.content == "מצעים"

def test_parse_multi_line_message(temp_workspace):
    chat_file = temp_workspace["chat_file"]
    content = (
        "3/1/24, 06:56 - Idan P: מצעים\n"
        "פחים\n"
        "בקבוק שווה לאלון\n"
        "ברכה לאלון\n"
    )
    chat_file.write_text(content, encoding="utf-8")
    
    parser = WhatsAppParser()
    messages = parser.parse_file(str(chat_file))
    
    assert len(messages) == 1
    msg = messages[0]
    assert msg.date_str == "3/1/24"
    assert msg.time_str == "06:56"
    assert msg.sender == "Idan P"
    assert msg.content == "מצעים\nפחים\nבקבוק שווה לאלון\nברכה לאלון"

def test_parse_system_message(temp_workspace):
    chat_file = temp_workspace["chat_file"]
    content = "11/3/23, 00:06 - Messages to yourself are end-to-end encrypted. Learn more\n"
    chat_file.write_text(content, encoding="utf-8")
    
    parser = WhatsAppParser()
    messages = parser.parse_file(str(chat_file))
    
    assert len(messages) == 1
    msg = messages[0]
    assert msg.date_str == "11/3/23"
    assert msg.time_str == "00:06"
    assert msg.sender == "System"
    assert msg.content == "Messages to yourself are end-to-end encrypted. Learn more"

def test_parse_mixed_conversation(temp_workspace, mock_whatsapp_content):
    chat_file = temp_workspace["chat_file"]
    chat_file.write_text(mock_whatsapp_content, encoding="utf-8")
    
    parser = WhatsAppParser()
    messages = parser.parse_file(str(chat_file))
    
    # Let's count parsed messages:
    # 1. System: Messages to yourself...
    # 2. Idan P: מצעים (multiline)
    # 3. Idan P: צעיף (multiline)
    # 4. Idan P: YouTube link
    # 5. Idan P: IMG attachment
    # 6. Idan P: Media omitted
    # 7. Idan P: Painkillers (multiline with link)
    assert len(messages) == 7
    
    assert messages[0].sender == "System"
    assert messages[1].sender == "Idan P"
    assert "בקבוק שווה לאלון" in messages[1].content
    assert messages[2].sender == "Idan P"
    assert "להוריד לטל'" in messages[2].content
    assert messages[3].content == "https://youtube.com/@thenewboston?si=8ZZn2fTvXkXdSLOg"
    assert messages[4].content == "IMG-20220703-WA0000.jpg (file attached)"
    assert messages[5].content == "<Media omitted>"
    assert "תהיו Painkillers" in messages[6].content
    assert "https://www.linkedin.com/feed/" in messages[6].content

import pytest
from pathlib import Path
import os
import shutil

@pytest.fixture
def mock_whatsapp_content():
    """Returns a realistic raw WhatsApp text snippet containing system messages,

    multiline messages, Hebrew/English, links, and media attachments.
    """
    return (
        "11/3/23, 00:06 - Messages to yourself are end-to-end encrypted. No one else, not even WhatsApp, can read, listen to, or share them. Learn more\n"
        "3/1/24, 06:56 - Idan P: מצעים\n"
        "פחים\n"
        "בקבוק שווה לאלון\n"
        "ברכה לאלון\n"
        "3/1/24, 06:57 - Idan P: צעיף\n"
        "כרית\n"
        "אוזניות\n"
        "להוריד לטל'\n"
        "3/4/24, 08:17 - Idan P: https://youtube.com/@thenewboston?si=8ZZn2fTvXkXdSLOg\n"
        "4/9/24, 20:10 - Idan P: IMG-20220703-WA0000.jpg (file attached)\n"
        "9/15/24, 23:34 - Idan P: <Media omitted>\n"
        "10/10/24, 15:57 - Idan P: תהיו Painkillers 💊 לא ויטמינים\n"
        "רוצים ➕ להגיב?\n"
        "https://www.linkedin.com/feed/\n"
    )

@pytest.fixture
def temp_workspace(tmp_path):
    """Provides a temporary, clean workspace directory with a dummy chat.txt file."""
    output_dir = tmp_path / "output"
    scraped_dir = output_dir / "scraped_pages"
    vector_db_dir = output_dir / "vector_db"
    
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(scraped_dir, exist_ok=True)
    os.makedirs(vector_db_dir, exist_ok=True)
    
    chat_file = tmp_path / "chat.txt"
    
    return {
        "root": tmp_path,
        "output": output_dir,
        "scraped": scraped_dir,
        "vector_db": vector_db_dir,
        "chat_file": chat_file
    }

import pytest
import zipfile
import shutil
from pathlib import Path
from config import config
from backend.services.archive_service import ArchiveService

def test_archive_service_lifecycle(tmp_path):
    # Setup temporary paths
    workspace_dir = tmp_path / "workspace"
    workspace_dir.mkdir()
    
    chat_file = workspace_dir / "chat.txt"
    chat_file.write_text("chat content turn 1")
    
    output_dir = workspace_dir / "output"
    output_dir.mkdir()
    
    scraped_dir = output_dir / "scraped_pages"
    scraped_dir.mkdir()
    scraped_file = scraped_dir / "page1.md"
    scraped_file.write_text("scraped page content")
    
    vector_db_dir = output_dir / "vector_db"
    vector_db_dir.mkdir()
    db_file = vector_db_dir / "sqlite.db"
    db_file.write_text("database bytes")
    
    # Snapshot backups directory (which should NOT be zipped!)
    backups_dir = output_dir / "backups"
    backups_dir.mkdir()
    backup_file = backups_dir / "backup.txt"
    backup_file.write_text("backup details")
    
    # Override config paths for testing
    original_output_dir = config.output_dir
    original_chat_path = config.chat_file_path
    
    config.output_dir = output_dir
    config.chat_file_path = chat_file
    
    try:
        service = ArchiveService()
        zip_path = tmp_path / "archive.zip"
        
        # 1. Test export_archive
        service.export_archive(zip_path)
        assert zip_path.exists()
        assert zipfile.is_zipfile(zip_path)
        
        # Check zip contents
        with zipfile.ZipFile(zip_path, 'r') as zf:
            namelist = zf.namelist()
            assert "chat.txt" in namelist
            assert "output/scraped_pages/page1.md" in namelist
            assert "output/vector_db/sqlite.db" in namelist
            # backups MUST be excluded!
            assert "output/backups/backup.txt" not in namelist
            
        # 2. Modify files to verify import/restore
        chat_file.write_text("modified chat content")
        scraped_file.write_text("modified scrapings")
        db_file.write_text("modified database")
        
        # 3. Test import_archive
        service.import_archive(zip_path)
        
        # Verify original files are restored
        assert chat_file.read_text() == "chat content turn 1"
        assert scraped_file.read_text() == "scraped page content"
        assert db_file.read_text() == "database bytes"
        
    finally:
        # Restore original config paths
        config.output_dir = original_output_dir
        config.chat_file_path = original_chat_path

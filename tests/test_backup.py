import pytest
from pathlib import Path
from config import config
from backend.services.backup_service import ChromaBackupService

def test_backup_service_lifecycle(tmp_path):
    # Setup temporary paths
    vector_db_dir = tmp_path / "vector_db"
    backup_dir = tmp_path / "backups"
    
    vector_db_dir.mkdir()
    
    # Create some dummy files in vector db directory to simulate Chroma database files
    dummy_file = vector_db_dir / "sqlite3.db"
    dummy_file.write_text("dummy database content")
    
    # Override config paths for testing
    original_vector_db_dir = config.vector_db_dir
    config.vector_db_dir = vector_db_dir
    
    try:
        service = ChromaBackupService(backup_dir=backup_dir)
        
        # 1. Test create_backup
        backup_name = service.create_backup("test-label")
        assert backup_name is not None
        assert "test-label" in backup_name
        
        # Check backup directory was created and files copied
        backup_path = backup_dir / backup_name
        assert backup_path.exists()
        assert (backup_path / "sqlite3.db").exists()
        assert (backup_path / "sqlite3.db").read_text() == "dummy database content"
        
        # 2. Test list_backups
        backups = service.list_backups()
        assert len(backups) == 1
        assert backups[0]["name"] == backup_name
        assert backups[0]["label"] == "test-label"
        assert backups[0]["size_bytes"] > 0
        
        # Modify active db file to test restore later
        dummy_file.write_text("modified database content")
        
        # 3. Test restore_backup
        service.restore_backup(backup_name)
        assert dummy_file.read_text() == "dummy database content"
        
        # 4. Test delete_backup
        service.delete_backup(backup_name)
        assert not backup_path.exists()
        assert len(service.list_backups()) == 0
        
    finally:
        # Restore original config paths
        config.vector_db_dir = original_vector_db_dir

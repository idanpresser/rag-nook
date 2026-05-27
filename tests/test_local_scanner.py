import pytest
from pathlib import Path
from core.scanner import LocalFolderScanner, ScanResult

def test_scanner_success_mock(tmp_path):
    # Set up mock files in tmp_path sandbox
    chat_file = tmp_path / "sample_chat.txt"
    chat_file.touch()
    
    img_file = tmp_path / "image.jpg"
    img_file.touch()
    
    png_file = tmp_path / "photo.png"
    png_file.touch()
    
    heic_file = tmp_path / "shot.heic"
    heic_file.touch()
    
    vcf_file = tmp_path / "contact.vcf"
    vcf_file.touch()
    
    # Other files that should NOT be collected as media or vcards
    other_file = tmp_path / "notes.pdf"
    other_file.touch()

    scanner = LocalFolderScanner()
    result = scanner.scan(tmp_path)
    
    assert isinstance(result, ScanResult)
    assert result.chat_log_path == chat_file
    
    expected_media = {img_file, png_file, heic_file}
    expected_vcards = {vcf_file}
    
    assert set(result.media_files) == expected_media
    assert set(result.vcard_files) == expected_vcards


def test_scanner_success_real_anat():
    real_dir = Path("/Users/idaneyal/DEV/personal_momory/Anat")
    scanner = LocalFolderScanner()
    result = scanner.scan(real_dir)
    
    assert isinstance(result, ScanResult)
    assert result.chat_log_path.name == "WhatsApp Chat with ענתי קרמון.txt"
    assert any(f.name.endswith(".jpg") for f in result.media_files)
    assert any(f.name.endswith(".vcf") for f in result.vcard_files)


def test_scanner_dir_does_not_exist():
    scanner = LocalFolderScanner()
    non_existent = Path("/Users/idaneyal/DEV/personal_momory/non_existent_directory_12345")
    
    with pytest.raises(FileNotFoundError) as exc_info:
        scanner.scan(non_existent)
    assert "does not exist" in str(exc_info.value)


def test_scanner_no_chat_log(tmp_path):
    scanner = LocalFolderScanner()
    with pytest.raises(FileNotFoundError) as exc_info:
        scanner.scan(tmp_path)
    assert "No chat log file" in str(exc_info.value)

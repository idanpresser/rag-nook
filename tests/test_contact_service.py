import pytest
from pathlib import Path
from services.contact_service import VCardParser
from core.preprocessor import ContactMetadata

def test_parse_real_world_vcard():
    real_vcf = Path("/Users/idaneyal/DEV/personal_momory/Anat/EMobile כיכר מאירהוף.vcf")
    parser = VCardParser()
    metadata = parser.parse_file(real_vcf)
    
    assert isinstance(metadata, ContactMetadata)
    assert metadata.full_name == "EMobile כיכר מאירהוף"
    assert metadata.phones == ["048533420"]
    assert metadata.emails == []
    assert metadata.org is None


def test_parse_mock_vcard_all_fields(tmp_path):
    vcf_content = (
        "BEGIN:VCARD\n"
        "VERSION:3.0\n"
        "FN:John Doe\n"
        "TEL;type=CELL:+1-555-555-5555\n"
        "TEL;type=WORK:+1-555-555-1234\n"
        "EMAIL;type=INTERNET:john.doe@example.com\n"
        "ORG:Acme Corp\n"
        "END:VCARD\n"
    )
    vcf_file = tmp_path / "john_doe.vcf"
    vcf_file.write_text(vcf_content, encoding="utf-8")
    
    parser = VCardParser()
    metadata = parser.parse_file(vcf_file)
    
    assert metadata.full_name == "John Doe"
    assert set(metadata.phones) == {"+1-555-555-5555", "+1-555-555-1234"}
    assert metadata.emails == ["john.doe@example.com"]
    assert metadata.org == "Acme Corp"


def test_parse_mock_vcard_missing_fields(tmp_path):
    # Minimal vCard with missing optional fields
    vcf_content = (
        "BEGIN:VCARD\n"
        "VERSION:3.0\n"
        "FN:Jane Doe\n"
        "END:VCARD\n"
    )
    vcf_file = tmp_path / "jane_doe.vcf"
    vcf_file.write_text(vcf_content, encoding="utf-8")
    
    parser = VCardParser()
    metadata = parser.parse_file(vcf_file)
    
    assert metadata.full_name == "Jane Doe"
    assert metadata.phones == []
    assert metadata.emails == []
    assert metadata.org is None


def test_parse_non_existent_file():
    parser = VCardParser()
    non_existent = Path("/Users/idaneyal/DEV/personal_momory/non_existent_contact.vcf")
    
    with pytest.raises(FileNotFoundError):
        parser.parse_file(non_existent)

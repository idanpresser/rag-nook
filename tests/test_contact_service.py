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


def test_contact_repository_crud_and_search(tmp_path):
    from core.database import ContactRepository
    db_file = tmp_path / "test_contacts.db"
    repo = ContactRepository(db_path=db_file)
    
    # 1. Create parsed ContactMetadata
    c1 = ContactMetadata(
        full_name="Alice Smith",
        phones=["123-456-7890", "987-654-3210"],
        emails=["alice@example.com"],
        org="Google"
    )
    c2 = ContactMetadata(
        full_name="Bob Jones",
        phones=["555-123-4567"],
        emails=["bob@example.com"],
        org="Apple"
    )
    
    # 2. Insert into repository
    repo.save(c1)
    repo.save(c2)
    
    # 3. Search by name
    results_name = repo.search_by_name("Alice")
    assert len(results_name) == 1
    assert results_name[0].full_name == "Alice Smith"
    assert results_name[0].org == "Google"
    
    # 4. Search by phone
    results_phone = repo.search_by_phone("555")
    assert len(results_phone) == 1
    assert results_phone[0].full_name == "Bob Jones"
    
    # 5. Handle duplicate contact conflicts cleanly (upsert by unique name)
    c1_updated = ContactMetadata(
        full_name="Alice Smith",
        phones=["111-111-1111"],
        emails=["alice_new@example.com"],
        org="Google Inc"
    )
    repo.save(c1_updated)
    
    # Search again to verify upsert updated the contact instead of creating a duplicate
    all_alice = repo.search_by_name("Alice Smith")
    assert len(all_alice) == 1
    assert all_alice[0].phones == ["111-111-1111"]
    assert all_alice[0].emails == ["alice_new@example.com"]
    assert all_alice[0].org == "Google Inc"


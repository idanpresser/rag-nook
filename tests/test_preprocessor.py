import pytest
from datetime import datetime
from core.parser import RawMessage
from core.preprocessor import Preprocessor, EnrichedMessage, ConversationSegment

def test_date_normalization():
    preprocessor = Preprocessor()
    
    # 2-digit year format standard in WhatsApp export M/D/YY
    normalized = preprocessor.normalize_date("3/1/24", "06:56")
    assert normalized == "2024-03-01T06:56:00Z"
    
    # 2-digit month/day, 2-digit year
    normalized_2 = preprocessor.normalize_date("11/03/23", "00:06")
    assert normalized_2 == "2023-11-03T00:06:00Z"

def test_entity_extraction_and_classification():
    preprocessor = Preprocessor()
    
    # Test Link Extraction
    raw_link_msg = RawMessage(
        date_str="3/4/24",
        time_str="08:17",
        sender="Idan P",
        content="https://youtube.com/@thenewboston?si=8ZZn2fTvXkXdSLOg",
        raw_text="3/4/24, 08:17 - Idan P: https://youtube.com/@thenewboston?si=8ZZn2fTvXkXdSLOg"
    )
    enriched = preprocessor.enrich_message(raw_link_msg, "msg-1")
    assert enriched.media_type == "link"
    assert len(enriched.links) == 1
    assert enriched.links[0] == "https://youtube.com/@thenewboston?si=8ZZn2fTvXkXdSLOg"
    assert len(enriched.attachments) == 0

    # Test Attachment Extraction
    raw_attach_msg = RawMessage(
        date_str="4/9/24",
        time_str="20:10",
        sender="Idan P",
        content="IMG-20220703-WA0000.jpg (file attached)",
        raw_text="4/9/24, 20:10 - Idan P: IMG-20220703-WA0000.jpg (file attached)"
    )
    enriched_attach = preprocessor.enrich_message(raw_attach_msg, "msg-2")
    assert enriched_attach.media_type == "image"
    assert len(enriched_attach.attachments) == 1
    assert enriched_attach.attachments[0] == "IMG-20220703-WA0000.jpg"
    assert len(enriched_attach.links) == 0

    # Test Text Classification
    raw_text_msg = RawMessage(
        date_str="5/15/24",
        time_str="09:40",
        sender="Idan P",
        content="Brave new world",
        raw_text="5/15/24, 09:40 - Idan P: Brave new world"
    )
    enriched_text = preprocessor.enrich_message(raw_text_msg, "msg-3")
    assert enriched_text.media_type == "text"
    assert len(enriched_text.links) == 0
    assert len(enriched_text.attachments) == 0

def test_turn_segmentation():
    preprocessor = Preprocessor()
    
    # Create mock raw messages:
    # Msg 1: 3/1/24, 06:56 -> Sender: Idan P
    # Msg 2: 3/1/24, 06:57 -> Sender: Idan P (1 min gap)
    # Msg 3: 3/1/24, 11:44 -> Sender: Idan P (4h 47m gap -> new segment)
    raw_msgs = [
        RawMessage(
            date_str="3/1/24", time_str="06:56", sender="Idan P",
            content="מצעים\nפחים", raw_text="3/1/24, 06:56 - Idan P: מצעים\nפחים"
        ),
        RawMessage(
            date_str="3/1/24", time_str="06:57", sender="Idan P",
            content="צעיף\nכרית", raw_text="3/1/24, 06:57 - Idan P: צעיף\nכרית"
        ),
        RawMessage(
            date_str="3/1/24", time_str="11:44", sender="Idan P",
            content="בגד ים", raw_text="3/1/24, 11:44 - Idan P: בגד ים"
        )
    ]
    
    segments = preprocessor.segment_conversation(raw_msgs)
    
    # We expect 2 segments:
    # Segment 1: Msg 1 and Msg 2
    # Segment 2: Msg 3
    assert len(segments) == 2
    
    seg1 = segments[0]
    assert len(seg1.messages) == 2
    assert seg1.messages[0].content == "מצעים\nפחים"
    assert seg1.messages[1].content == "צעיף\nכרית"
    
    seg2 = segments[1]
    assert len(seg2.messages) == 1
    assert seg2.messages[0].content == "בגד ים"


def test_enrich_conversation_with_attachments(tmp_path, mocker):
    from core.preprocessor import ContactMetadata

    # Create mock directory and mock attachment files
    vcf_file = tmp_path / "EMobile.vcf"
    vcf_file.touch()
    img_file = tmp_path / "IMG-123.jpg"
    img_file.touch()

    raw_msgs = [
        RawMessage(
            date_str="3/1/24", time_str="06:56", sender="Idan P",
            content="EMobile.vcf (file attached)", raw_text="3/1/24, 06:56 - Idan P: EMobile.vcf (file attached)"
        ),
        RawMessage(
            date_str="3/1/24", time_str="06:57", sender="Idan P",
            content="IMG-123.jpg (file attached)", raw_text="3/1/24, 06:57 - Idan P: IMG-123.jpg (file attached)"
        )
    ]

    # Mock services
    mock_optimizer = mocker.Mock()
    mock_optimizer.optimize_image.return_value = tmp_path / "IMG-123.avif"
    
    mock_ocr = mocker.Mock()
    mock_ocr.extract_text.return_value = "extracted recipe info"

    mock_vcard = mocker.Mock()
    mock_vcard.parse_file.return_value = ContactMetadata(
        full_name="EMobile Clinic", phones=["048533420"], emails=[]
    )

    mock_repo = mocker.Mock()

    mock_llm = mocker.Mock()
    mock_llm.summarize_image.return_value = "a clinic sign with Hebrew text"

    preprocessor = Preprocessor()
    segments = preprocessor.enrich_conversation(
        raw_msgs=raw_msgs,
        directory_path=tmp_path,
        media_optimizer=mock_optimizer,
        ocr_processor=mock_ocr,
        vcard_parser=mock_vcard,
        contact_repo=mock_repo,
        llm_client=mock_llm
    )

    assert len(segments) == 1
    messages = segments[0].messages
    assert len(messages) == 2

    # Check vCard message
    assert messages[0].attachments == ["EMobile.vcf"]
    assert "EMobile Clinic" in messages[0].content
    mock_repo.save.assert_called_once()

    # Check image message
    assert messages[1].attachments == ["IMG-123.jpg"]
    assert "extracted recipe info" in messages[1].content
    assert "a clinic sign with Hebrew text" in messages[1].summary
    mock_optimizer.optimize_image.assert_called_once_with(img_file)


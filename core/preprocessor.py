from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field
from core.parser import RawMessage
from config import config

class ScrapedURLMetadata(BaseModel):
    url: str
    title: str
    slug: str
    markdown_path: str
    executive_summary: str
    tags: List[str] = Field(default_factory=list)
    categories: List[str] = Field(default_factory=list)

class ContactMetadata(BaseModel):
    full_name: str
    phones: List[str] = Field(default_factory=list)
    emails: List[str] = Field(default_factory=list)
    org: Optional[str] = None

class EnrichedMessage(BaseModel):
    message_id: str
    datetime_utc: str
    sender: str
    content: str
    media_type: str  # "text", "link", "image", "system", "media_omitted", etc.
    links: List[str] = Field(default_factory=list)
    attachments: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    summary: Optional[str] = None
    scraped_urls: List[ScrapedURLMetadata] = Field(default_factory=list)


class ConversationSegment(BaseModel):
    segment_id: str
    start_time: str
    end_time: str
    messages: List[EnrichedMessage] = Field(default_factory=list)
    summary: Optional[str] = None
    tags: List[str] = Field(default_factory=list)

class Preprocessor:
    """Handles raw message enrichment, text cleaning, entity extraction, and conversational segmentation."""

    def normalize_date(self, date_str: str, time_str: str) -> str:
        """Converts raw date and time strings from WhatsApp to ISO 8601 UTC format.

        Format assumed: Month/Day/Year (M/D/YY or M/D/YYYY) and Time (HH:MM).
        """
        parts = date_str.split('/')
        if len(parts) != 3:
            raise ValueError(f"Invalid date format: {date_str}")
        
        month, day, year = parts
        # Standardize month and day padding
        month = month.zfill(2)
        day = day.zfill(2)
        
        # Standardize year to 4 digits
        if len(year) == 2:
            year = "20" + year
            
        dt_str = f"{month}/{day}/{year} {time_str}"
        dt = datetime.strptime(dt_str, "%m/%d/%Y %H:%M")
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    def enrich_message(self, raw_msg: RawMessage, message_id: str) -> EnrichedMessage:
        """Parses entities and classifies a raw message into a highly structured EnrichedMessage."""
        datetime_utc = self.normalize_date(raw_msg.date_str, raw_msg.time_str)
        content = raw_msg.content.strip()
        
        # 1. Check for system classifications
        if raw_msg.sender == "System":
            return EnrichedMessage(
                message_id=message_id,
                datetime_utc=datetime_utc,
                sender="System",
                content=content,
                media_type="system"
            )
            
        # 2. Check for explicit media omission
        if config.media_omitted_regex.match(content):
            return EnrichedMessage(
                message_id=message_id,
                datetime_utc=datetime_utc,
                sender=raw_msg.sender,
                content=content,
                media_type="media_omitted"
            )

        # 3. Extract links
        links = config.url_regex.findall(content)
        
        # 4. Extract attachment files
        attachments = [att.strip() for att in config.attachment_regex.findall(content)]

        # Classify media_type
        if links:
            media_type = "link"
        elif attachments:
            filename = attachments[0].lower()
            if any(filename.endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".gif", ".webp"]):
                media_type = "image"
            elif any(filename.endswith(ext) for ext in [".mp4", ".mov", ".avi"]):
                media_type = "video"
            elif any(filename.endswith(ext) for ext in [".mp3", ".wav", ".aac", ".opus"]):
                media_type = "audio"
            else:
                media_type = "document"
        else:
            media_type = "text"

        return EnrichedMessage(
            message_id=message_id,
            datetime_utc=datetime_utc,
            sender=raw_msg.sender,
            content=content,
            media_type=media_type,
            links=links,
            attachments=attachments
        )

    def segment_conversation(self, raw_msgs: List[RawMessage]) -> List[ConversationSegment]:
        """Segments raw chronological messages into turns based on time deltas."""
        if not raw_msgs:
            return []

        segments: List[ConversationSegment] = []
        current_msg_list: List[EnrichedMessage] = []

        for i, raw_msg in enumerate(raw_msgs):
            enriched = self.enrich_message(raw_msg, f"msg-{i+1}")

            if not current_msg_list:
                current_msg_list.append(enriched)
                continue

            last_msg = current_msg_list[-1]
            last_dt = datetime.strptime(last_msg.datetime_utc, "%Y-%m-%dT%H:%M:%SZ")
            curr_dt = datetime.strptime(enriched.datetime_utc, "%Y-%m-%dT%H:%M:%SZ")

            # Check gap in seconds
            gap = (curr_dt - last_dt).total_seconds()

            if gap > config.max_segment_gap_seconds:
                # Save completed segment and start a new one
                segments.append(self._create_segment(current_msg_list, f"seg-{len(segments)+1}"))
                current_msg_list = [enriched]
            else:
                current_msg_list.append(enriched)

        if current_msg_list:
            segments.append(self._create_segment(current_msg_list, f"seg-{len(segments)+1}"))

        return segments

    def _create_segment(self, messages: List[EnrichedMessage], segment_id: str) -> ConversationSegment:
        return ConversationSegment(
            segment_id=segment_id,
            start_time=messages[0].datetime_utc,
            end_time=messages[-1].datetime_utc,
            messages=messages
        )

    def enrich_conversation(
        self,
        raw_msgs: List[RawMessage],
        directory_path: Path,
        media_optimizer,
        ocr_processor,
        vcard_parser,
        contact_repo,
        llm_client=None
    ) -> List[ConversationSegment]:
        """Aligns text logs with physical attachment files (images & contacts) in directory_path.

        Optionally converts/optimizes pictures to AVIF, runs OCR + Gemma-4 local VLM summarization,
        extracts contact profiles, and compiles them in a chronologically aligned turn stream.
        """
        enriched_msgs: List[EnrichedMessage] = []
        for i, raw_msg in enumerate(raw_msgs):
            enriched = self.enrich_message(raw_msg, f"msg-{i+1}")
            
            # Enrich active attachments
            for attachment in enriched.attachments:
                file_path = directory_path / attachment
                if not file_path.exists():
                    continue

                suffix = file_path.suffix.lower()
                if suffix in [".jpg", ".jpeg", ".png", ".gif", ".webp", ".heic"]:
                    # Optimize image to AVIF format
                    try:
                        opt_path = media_optimizer.optimize_image(file_path)
                    except Exception:
                        opt_path = file_path

                    # Run OCR
                    try:
                        ocr_text = ocr_processor.extract_text(file_path)
                        if ocr_text:
                            enriched.content += f"\n[OCR Text extracted from {attachment}]: {ocr_text}"
                    except Exception:
                        pass

                    # Run local Gemma-4 VLM summarization
                    if llm_client:
                        try:
                            vision_summary = llm_client.summarize_image(file_path, "Describe this image in detail.")
                            if vision_summary:
                                enriched.summary = vision_summary
                        except Exception:
                            pass

                elif suffix == ".vcf":
                    # Parse vCard profile
                    try:
                        contact = vcard_parser.parse_file(file_path)
                        if contact:
                            # Index structured contact card to SQLite repo
                            contact_repo.save(contact)
                            # Enrich turn text representation for vector db retrieval
                            phones_str = ", ".join(contact.phones) if contact.phones else "None"
                            emails_str = ", ".join(contact.emails) if contact.emails else "None"
                            enriched.content += f"\n[Parsed Contact Card {attachment}]: Name: {contact.full_name}, Phones: {phones_str}, Emails: {emails_str}, Org: {contact.org or 'None'}"
                    except Exception:
                        pass

            enriched_msgs.append(enriched)

        if not enriched_msgs:
            return []

        segments: List[ConversationSegment] = []
        current_msg_list: List[EnrichedMessage] = []

        for enriched in enriched_msgs:
            if not current_msg_list:
                current_msg_list.append(enriched)
                continue

            last_msg = current_msg_list[-1]
            last_dt = datetime.strptime(last_msg.datetime_utc, "%Y-%m-%dT%H:%M:%SZ")
            curr_dt = datetime.strptime(enriched.datetime_utc, "%Y-%m-%dT%H:%M:%SZ")

            # Check gap in seconds
            gap = (curr_dt - last_dt).total_seconds()

            if gap > config.max_segment_gap_seconds:
                segments.append(self._create_segment(current_msg_list, f"seg-{len(segments)+1}"))
                current_msg_list = [enriched]
            else:
                current_msg_list.append(enriched)

        if current_msg_list:
            segments.append(self._create_segment(current_msg_list, f"seg-{len(segments)+1}"))

        return segments


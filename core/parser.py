import os
from typing import List, Optional
from dataclasses import dataclass, field
from config import config

@dataclass
class RawMessage:
    date_str: str
    time_str: str
    sender: str
    content: str
    raw_text: str
    attachments: List[str] = field(default_factory=list)

class WhatsAppParser:
    """A streaming state-machine parser for WhatsApp chat logs.

    Handles multi-line messages, sender/system classifications, and raw log ingestion.
    """

    def parse_file(self, filepath: str) -> List[RawMessage]:
        """Parses a WhatsApp chat text file line by line using a state machine.

        Args:
            filepath: Path to the WhatsApp .txt export.

        Returns:
            A list of structured RawMessage objects.
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Chat log file not found at: {filepath}")

        messages: List[RawMessage] = []
        current_msg: Optional[RawMessage] = None

        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                # Strip right-side newlines, but preserve internal spacing
                line_str = line.rstrip("\r\n")
                
                header_match = config.whatsapp_header_regex.match(line_str)
                if header_match:
                    # Capture the completed previous message
                    if current_msg:
                        current_msg.attachments = [
                            att.strip() for att in config.attachment_regex.findall(current_msg.content)
                        ]
                        messages.append(current_msg)

                    date_str, time_str, remainder = header_match.groups()

                    # Check if this line is a sender message vs. system message
                    sender_match = config.sender_message_regex.match(remainder)
                    if sender_match:
                        sender = sender_match.group(1).strip()
                        content = sender_match.group(2).strip()
                    else:
                        sender = "System"
                        content = remainder.strip()

                    current_msg = RawMessage(
                        date_str=date_str,
                        time_str=time_str,
                        sender=sender,
                        content=content,
                        raw_text=line_str
                    )
                else:
                    # Append multi-line contents to the message in progress
                    if current_msg:
                        current_msg.content += "\n" + line_str
                        current_msg.raw_text += "\n" + line_str
                    else:
                        # Gracefully ignore leading junk lines before any message
                        pass

            # Flush the final message
            if current_msg:
                current_msg.attachments = [
                    att.strip() for att in config.attachment_regex.findall(current_msg.content)
                ]
                messages.append(current_msg)

        return messages


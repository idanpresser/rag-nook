import sqlite3
import json
from pathlib import Path
from typing import List, Optional, Union
from core.preprocessor import ContactMetadata

class ContactRepository:
    """Manages SQLite database persistence for parsed contact metadata."""

    def __init__(self, db_path: Optional[Union[str, Path]] = None):
        """Initializes the repository and creates the schema if it does not exist.

        Args:
            db_path: Path to the SQLite database. Defaults to output/contacts.db.
        """
        if db_path is None:
            db_path = Path("/Users/idaneyal/DEV/personal_momory/output/contacts.db")
        self.db_path = Path(db_path)
        
        # Ensure parent directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Creates the contacts table with a UNIQUE constraint on full_name."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS contacts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    full_name TEXT UNIQUE NOT NULL,
                    phones TEXT,
                    emails TEXT,
                    org TEXT
                )
            """)
            conn.commit()

    def save(self, contact: ContactMetadata) -> int:
        """Saves a ContactMetadata into the SQLite database.

        Performs an upsert if a contact with the same full_name already exists.

        Args:
            contact: The ContactMetadata to persist.

        Returns:
            The row ID of the inserted or updated row.
        """
        phones_json = json.dumps(contact.phones)
        emails_json = json.dumps(contact.emails)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO contacts (full_name, phones, emails, org)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(full_name) DO UPDATE SET
                    phones = excluded.phones,
                    emails = excluded.emails,
                    org = excluded.org
            """, (contact.full_name, phones_json, emails_json, contact.org))
            conn.commit()
            return cursor.lastrowid

    def search_by_name(self, name: str) -> List[ContactMetadata]:
        """Searches contacts by full name (case-insensitive substring match).

        Args:
            name: The query substring to match.

        Returns:
            A list of matching ContactMetadata objects.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT full_name, phones, emails, org FROM contacts WHERE full_name LIKE ?",
                (f"%{name}%",)
            )
            rows = cursor.fetchall()

        results = []
        for row in rows:
            results.append(ContactMetadata(
                full_name=row[0],
                phones=json.loads(row[1]) if row[1] else [],
                emails=json.loads(row[2]) if row[2] else [],
                org=row[3]
            ))
        return results

    def search_by_phone(self, phone: str) -> List[ContactMetadata]:
        """Searches contacts checking if a phone number matches any in the stored phones list.

        Args:
            phone: The phone number or substring to match.

        Returns:
            A list of matching ContactMetadata objects.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT full_name, phones, emails, org FROM contacts")
            rows = cursor.fetchall()

        results = []
        for row in rows:
            phones_list = json.loads(row[1]) if row[1] else []
            if any(phone in p for p in phones_list):
                results.append(ContactMetadata(
                    full_name=row[0],
                    phones=phones_list,
                    emails=json.loads(row[2]) if row[2] else [],
                    org=row[3]
                ))
        return results

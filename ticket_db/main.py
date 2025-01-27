import sqlite3
from typing import List, Dict
import logging
import sys

class TicketDB:
    def __init__(self, db_path: str = "tickets.db"):
        logging.basicConfig(
            level=logging.INFO,
            format='[%(levelname)s - %(asctime)s] %(message)s',
            handlers=[logging.StreamHandler(sys.stdout)]
        )
        self.logger = logging.getLogger()
        
        self.db_path = db_path
        self.create_table()


    def create_table(self):
        """Create tickets table if it doesn't exist"""
        with sqlite3.connect(self.db_path) as conn:
            self.logger.info("Creating tickets table")
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tickets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticket_name TEXT,
                    question TEXT,
                    level TEXT CHECK(level IN ('LOW', 'MEDIUM', 'HIGH')),
                    person TEXT
                )
            ''')
            conn.commit()

    def add_ticket(self, ticket_data: Dict) -> int:
        """Add a new ticket to the database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            self.logger.info(f"Adding ticket: {ticket_data}")
            cursor.execute('''
                INSERT INTO tickets (ticket_name, question, level, person)
                VALUES (?, ?, ?, ?)
            ''', (
                f"HOOLI-{self.get_latest_id() + 1}",
                ticket_data['question'],
                ticket_data['level'],
                ticket_data['person']
            ))
            conn.commit()
            return cursor.lastrowid
        
    def get_latest_id(self) -> int:
        """Get the latest ticket ID from the database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT MAX(id) FROM tickets')
            result = cursor.fetchone()[0]
            self.logger.info(f"Latest ticket ID: {result}")
            return result if result is not None else 0


    def get_all_tickets(self) -> List[Dict]:
        """Retrieve all tickets from the database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM tickets')
            return [dict(row) for row in cursor.fetchall()]

# Example usage:
if __name__ == "__main__":
    # Initialize the database
    db = TicketDB()

    # Example ticket data
    sample_ticket = {
        'question': 'Need help with printer setup',
        'level': 'MEDIUM',
        'person': 'John Doe',
        'ticket_name': f"HOOLI-{db.get_latest_id() + 1}"
    }

    # Add a ticket
    ticket_id = db.add_ticket(sample_ticket)
    print(f"Added ticket with ID: {ticket_id}")

    # Get all tickets
    all_tickets = db.get_all_tickets()
    print("\nAll tickets:")
    for ticket in all_tickets:
        print(ticket)

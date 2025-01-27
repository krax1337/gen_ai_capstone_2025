import requests
from typing import Dict, Any
import environ
import logging
import sys

env = environ.Env()
environ.Env.read_env('.env')

class TelegramHandler:
    def __init__(self):
        logging.basicConfig(
            level=logging.INFO,
            format='[%(levelname)s - %(asctime)s] %(message)s',
            handlers=[logging.StreamHandler(sys.stdout)]
        )
        self.logger = logging.getLogger()
        self.bot_token = env('TELEGRAM_API_TOKEN')
        self.channel_id = env('TELEGRAM_CHAT_ID')
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
        


    def format_ticket_message(self, ticket: Dict[str, Any]) -> str:
        return (
            f"🎫 New Ticket\n\n"
            f"🔗 Ticket Name: {ticket['ticket_name']}\n"
            f"👤 From: {ticket['person']}\n"
            f"🔍 Level: {ticket['level']}\n"
            f"❓ Question: {ticket['question']}"
        )

    def send_message(self, text: str) -> Dict[str, Any]:
        endpoint = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": self.channel_id,
            "text": text,
            "parse_mode": "HTML"
        }
        response = requests.post(endpoint, json=payload)
        return response.json()

    def send_ticket(self, ticket: Dict[str, Any]) -> Dict[str, Any]:
        message = self.format_ticket_message(ticket)
        self.logger.info(f"Sending ticket message: {message}")
        return self.send_message(message)

if __name__ == "__main__":
    telegram_handler = TelegramHandler()
    ticket = {
        'question': 'Need help with printer setup',
        'level': 'MEDIUM',
        'person': 'John Doe',
        'ticket_name': "HOOLI-1"
    }
    print(telegram_handler.send_ticket(ticket))

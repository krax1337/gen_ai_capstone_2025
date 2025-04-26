import streamlit as st
import numpy as np
from ticket_db.main import TicketDB
from chroma.main import ChromaKnowledgeBase
from telegram_handler.main import TelegramHandler
import pandas as pd
from pydantic import BaseModel, Field
from openai import OpenAI, pydantic_function_tool
import json
import environ
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s - %(asctime)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger()

st.set_page_config(layout="wide", page_title="EPAM reference", page_icon="🤩")

env = environ.Env()
environ.Env.read_env('.env')

def get_answer(question: str) -> str:
    logger.info(f"Searching knowledge base for question: {question}")
    kb = ChromaKnowledgeBase()
    kb.initialize_database(env('CSV_KNOWLEDGE_BASE_PATH'))
    result = kb.search_knowledge(question)
    logger.info("Knowledge base search completed")
    return result

class GetAnswer(BaseModel):
    question: str = Field(..., description="Helpdesk question to be answered.")

answer_tool = pydantic_function_tool(
    GetAnswer,
    name="get_answer",
    description="Get the answer to the helpdesk question.",
)

def create_ticket(question: str, level: str, person: str) -> str:
    logger.info(f"Creating ticket for {person} with level {level}")
    ticket_db = TicketDB()
    ticket = {
        'question': question,
        'level': level,
        'person': person,
        'ticket_name': f"HOOLI-{ticket_db.get_latest_id() + 1}"
    }
    ticket_db.add_ticket(ticket)
    telegram_handler = TelegramHandler()
    telegram_handler.send_ticket(ticket)
    logger.info(f"Ticket created successfully: {ticket['ticket_name']}")
    return ticket

class CreateTicket(BaseModel):
    question: str = Field(..., description="User question to be answered.")
    level: str = Field(..., description="Must be LOW, MEDIUM, or HIGH")
    person: str = Field(..., description="Name of the person asking the question")

create_ticket_tool = pydantic_function_tool(
    CreateTicket,
    name="create_ticket",
    description="Create a ticket for the helpdesk.",
)

tools = [answer_tool, create_ticket_tool]

# Constants and Config
SYSTEM_PROMPT = """
You are a helpful assistant for Hooli helpdesk that answers helpdesk questions. Work as humanly as possible.
You have access to the Hooli helpdesk knowledge base.
When you are asked a question, you will first search the knowledge base for the answer.
For the answer, you will use the `get_answer` tool.
After you have answered the question, you will ask the user if they would like to create a ticket.
If they would like to create a ticket, you should get the user's name. DO NOT ASK FOR THE NAME IF YOU ALREADY HAVE IT.
And you should determine the level of the ticket based on the question. Based on the question, the level should be LOW, MEDIUM, or HIGH.
Do not ask the user for the level of the ticket. Just determine it based on the question.
Also you should rework the question to make it more concise and clear.
After you have all the information, you will use the `create_ticket` tool to create the ticket.
Answer the question in a friendly and helpful manner.
Irrelevant queries should be ignored. Do not answer them and tell the user that you are not able to answer them.
PLEASE DO NOT CALL MORE THAN ONE TOOL AT A TIME.
IF THE USER USES CURSES OR ANY OTHER OFFENSIVE LANGUAGE, IGNORE THE MESSAGE AND DO NOT RESPOND.
IF THE PROMPT FROM USER HAVE ANY CURSING OR OFFENSIVE LANGUAGE, IGNORE THE MESSAGE AND DO NOT RESPOND.
"""

class ChatBot:
    def __init__(self):
        self.client = OpenAI(api_key=env('OPENAI_API_KEY'))
        self.tools = [answer_tool, create_ticket_tool]
        self.initial_messages = [{"role": "developer", "content": SYSTEM_PROMPT}]

    def process_tool_call(self, tool_call, messages):
        args = json.loads(tool_call.function.arguments)
        
        if tool_call.function.name == "get_answer":
            result = get_answer(args["question"])
        elif tool_call.function.name == "create_ticket":
            result = create_ticket(args["question"], args["level"], args["person"])

        temp_messages = messages + [
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [tool_call]
            },
            {
                "role": "tool",
                "tool_call_id": tool_call.id,
                "name": tool_call.function.name,
                "content": str(result)
            }
        ]
        
        completion = self.client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0,
            tools=self.tools,
            messages=temp_messages,
        )
        tickets = TicketDB().get_all_tickets()
        st.session_state.tickets_container.dataframe(tickets)
        return completion.choices[0].message.content

    def get_response(self, messages):
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0,
            tools=self.tools,
            messages=messages,
        )
        
        tool_calls = response.choices[0].message.tool_calls or []
        
        if tool_calls:
            logger.info(f"Processing tool call: {tool_calls[0].function.name}")
            return self.process_tool_call(tool_calls[0], messages)
        
        return response.choices[0].message.content

def main():
    chatbot = ChatBot()
    
    # Layout setup
    col1, col2 = st.columns([3, 2])
    
    with col2:
        render_sidebar()
    
    with col1:
        render_chat_interface(chatbot)

def render_sidebar():
    st.header("How to use the chatbot")
    st.markdown("""
        1. **Ask a Question**: You can ask the chatbot any question related to the helpdesk.  
        2. **Chatbot Response**:  
            - If the question is relevant and the chatbot knows the answer, it will provide a response based on the knowledge base.  
            - If the chatbot cannot answer the question or if you are unsatisfied with the response, it will prompt you to create a support ticket.  
        3. **Create a Ticket**:  
            - To create a ticket, you will be asked to provide your name.  
            - Once submitted, the ticket will be sent to the designated Telegram channel and added to the "Opened Tickets" section.  
        4. **Helpdesk Notification**: The helpdesk team will be notified about the new ticket and will work to address it as soon as possible.  
    """)
    
    st.header("Opened tickets")
    st.session_state.tickets_container = st.empty()
    db = TicketDB()
    st.session_state.tickets_container.dataframe(db.get_all_tickets())
    st.write("https://t.me/s/gen_ai_capstone_2025")

def render_chat_interface(chatbot):
    st.header("Try our new AI chatbot!")
    chat_messages = st.container(height=500)
    
    if "messages" not in st.session_state:
        st.session_state.messages = chatbot.initial_messages

    # Display existing messages
    for message in st.session_state.messages:
        if message["role"] in ["developer", "tool"]:
            continue
        with chat_messages.chat_message(message["role"]):
            st.markdown(message["content"])

    spin_me = st.status("System is ready", state="complete")

    # Handle new messages
    if prompt := st.chat_input("Ask a question to get started"):
        handle_new_message(prompt, chat_messages, spin_me, chatbot)

def handle_new_message(prompt, chat_messages, spin_me, chatbot):
    logger.info(f"New user prompt received: {prompt}")
    spin_me.update(label="Thinking...", state="running")
    
    st.session_state.messages.append({"role": "user", "content": prompt})
    with chat_messages.chat_message("user"):
        st.markdown(prompt)

    with chat_messages.chat_message("assistant"):
        logger.info("Making API call to OpenAI")
        assistant_message = chatbot.get_response([
            {"role": m["role"], "content": m["content"]}
            for m in st.session_state.messages
        ])
        st.markdown(assistant_message)
        logger.info("Chat interaction completed")

    st.session_state.messages.append({"role": "assistant", "content": assistant_message})
    spin_me.update(label="System is ready", state="complete")

if __name__ == "__main__":
    main()




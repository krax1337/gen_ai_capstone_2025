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
    kb = ChromaKnowledgeBase()
    kb.initialize_database(env('CSV_KNOWLEDGE_BASE_PATH'))
    result = kb.search_knowledge(question)
    return result

class GetAnswer(BaseModel):
    question: str = Field(..., description="Helpdesk question to be answered.")

answer_tool = pydantic_function_tool(
    GetAnswer,
    name="get_answer",
    description="Get the answer to the helpdesk question.",
)

def create_ticket(question: str, level: str, person: str) -> str:
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

messages = [
    {"role": "developer", "content": """
    You are a helpful assistant for Hooli helpdesk that answers helpdesk questions. Work as humanly as possible.
    You have access to the Hooli helpdesk knowledge base.
    When you are asked a question, you will first search the knowledge base for the answer.
    For the answer, you will use the `get_answer` tool.
    After you have answered the question, you will ask the user if they would like to create a ticket.
    If they would like to create a ticket, you should get the user's name.
    And you should determine the level of the ticket based on the question. Based on the question, the level should be LOW, MEDIUM, or HIGH.
    Do not ask the user for the level of the ticket. Just determine it based on the question.
    Also you should rework the question to make it more concise and clear.
    After you have all the information, you will use the `create_ticket` tool to create the ticket.
    Answer the question in a friendly and helpful manner.
    Irrelevant queries should be ignored. Do not answer them and tell the user that you are not able to answer them.
    """},
]

client = OpenAI(api_key=env('OPENAI_API_KEY'))

st.title("Hooli Helpdesk")  
st.logo("./images/hooli.jpeg", size="large")

col1, col2 = st.columns([3, 2])


with col2:
    st.header("Opened tickets")
    tickets_container = st.empty()  # Create a container for tickets that can be updated
    
    # Initial display of tickets
    db = TicketDB()
    tickets = db.get_all_tickets()
    tickets_container.dataframe(tickets)
    st.write("https://t.me/s/gen_ai_capstone_2025")

with col1:
    st.header("Try our new AI chatbot!")
    chat_messages = st.container(height=900)
    
    if "messages" not in st.session_state:
        st.session_state.messages = messages

    for message in st.session_state.messages:
        if message["role"] == "developer":
            continue
        if message["role"] == "tool":
            continue
        with chat_messages.chat_message(message["role"]):
            st.markdown(message["content"])

    spin_me = st.status("System is ready", state="complete")

    if prompt := st.chat_input("Ask a question to get started"):
        spin_me.update(label="Thinking...", state="running")
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        with chat_messages.chat_message("user"):
            st.markdown(prompt)

        with chat_messages.chat_message("assistant"):
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                temperature=0,
                tools=tools,
                messages=[
                    {"role": m["role"], "content": m["content"]}
                    for m in st.session_state.messages
                ],
            )
            
            tool_calls = response.choices[0].message.tool_calls or []
            
            if tool_calls:
                if tool_calls[0].function.name == "get_answer":
                    args = json.loads(tool_calls[0].function.arguments)
                    answer_result = get_answer(args["question"])
                    temp_messages = [
                            {"role": m["role"], "content": m["content"]}
                            for m in st.session_state.messages
                        ]
                    
                    temp_messages.append(response.choices[0].message)
                    temp_messages.append({"role": "tool", "tool_call_id": tool_calls[0].id, "content": str(answer_result)})
                    inside_completion = client.chat.completions.create(
                        model="gpt-4o-mini",
                        temperature=0,
                        tools=tools,
                        messages=temp_messages,
                    )
                    assistant_message = inside_completion.choices[0].message.content
                    st.markdown(assistant_message)
                if tool_calls[0].function.name == "create_ticket":
                    args = json.loads(tool_calls[0].function.arguments)
                    answer_result = create_ticket(args["question"], args["level"], args["person"])
                    
                    # Update tickets display after creating a new ticket
                    tickets = db.get_all_tickets()
                    tickets_container.dataframe(tickets)
                    
                    temp_messages = [
                            {"role": m["role"], "content": m["content"]}
                            for m in st.session_state.messages
                        ]
                    
                    temp_messages.append(response.choices[0].message)
                    temp_messages.append({"role": "tool", "tool_call_id": tool_calls[0].id, "content": str(answer_result)})
                    inside_completion = client.chat.completions.create(
                        model="gpt-4o-mini",
                        temperature=0,
                        tools=tools,
                        messages=temp_messages,
                    )
                    assistant_message = inside_completion.choices[0].message.content
                    st.markdown(assistant_message)
            else:
                assistant_message = response.choices[0].message.content
                st.markdown(assistant_message)
            
        st.session_state.messages.append({"role": "assistant", "content": assistant_message})
        spin_me.update(label="System is ready", state="complete")

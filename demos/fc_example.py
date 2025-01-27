from pydantic import BaseModel, Field
from openai import OpenAI, pydantic_function_tool
import json
import environ
from chroma.main import ChromaKnowledgeBase

env = environ.Env()
environ.Env.read_env('.env')
client = OpenAI(api_key=env('OPENAI_API_KEY'))

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

tools = [answer_tool]

messages = [
    {"role": "developer", "content": """
    You are a helpful assistant for Hooli helpdesk that answers helpdesk questions.
    You have access to the Hooli helpdesk knowledge base.
    When you are asked a question, you will first search the knowledge base for the answer.
    For the answer, you will use the `get_answer` tool.
    """},
    {"role": "user", "content": "How do I reset my password?"}
]

completion_1 = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=messages,
    temperature=0,
    tools=tools
)

print(completion_1.choices[0].message.content)
tool_calls = completion_1.choices[0].message.tool_calls or []
print("Tool Calls:", tool_calls)


if tool_calls:
    # There might be multiple tool calls; let's handle just the first one for simplicity
    tool_call = tool_calls[0]
    
    # This will give you the parsed pydantic object for the arguments
    args = json.loads(tool_call.function.arguments)
    # Call the actual Python function
    answer_result = get_answer(args["question"])
    
    # Print or log the results
    print(f"Model requested for {tool_call.function.name} with {args}")
    print(f"Function result: {answer_result}")
    
    # ---- Append the tool's output back to the conversation ----
    # 1. The model's function call (tool usage)
    messages.append(completion_1.choices[0].message)
    
    # 2. The actual tool's response as a new "tool" role message
    messages.append({
        "role": "tool",
        "tool_call_id": tool_call.id,
        "content": str(answer_result)
    })

    completion_2 = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        tools=tools,
        temperature=0
    )

    # Print the final user-facing response
    final_answer = completion_2.choices[0].message.content
    print("Final Answer:", final_answer)
else:
    # If the model did not call the tool, just print the output as is
    print("No tool calls. Model's response:", completion_1.choices[0].message.content)

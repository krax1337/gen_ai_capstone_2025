import json
import requests
import environ

# read environment variables
env = environ.Env()
environ.Env.read_env('.env')

# ---- Pydantic & OpenAI setup ----
from pydantic import BaseModel, Field
from openai import OpenAI, pydantic_function_tool

client = OpenAI(api_key=env('OPENAI_API_KEY'))

# ---- Define the function and the Pydantic model for the function's arguments ----
def get_weather(latitude, longitude):
    response = requests.get(f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&current=temperature_2m,wind_speed_10m&hourly=temperature_2m,relative_humidity_2m,wind_speed_10m")
    data = response.json()
    return data['current']['temperature_2m']

class GetWeather(BaseModel):
    """
    Pydantic model describing the parameters required by our `get_weather` function.
    """
    latitude: float = Field(..., description="Latitude in decimal degrees.")
    longitude: float = Field(..., description="Longitude in decimal degrees.")

# Create a tool using pydantic_function_tool
weather_tool = pydantic_function_tool(
    GetWeather,
    name="get_weather",
    description="Get the current temperature (C) at the specified coordinates.",
)

tools = [weather_tool]

# ---- Conversation (messages) setup ----
messages = [
    {"role": "user", "content": "What's the weather like in Paris today?"}
]

# ---- First completion: model will decide if it needs to call the function ----
completion_1 = client.chat.completions.create(
    model="gpt-4o",
    messages=messages,
    tools=tools
)

# Inspect tool calls from the model's response (if any)
tool_calls = completion_1.choices[0].message.tool_calls or []
print("Tool Calls:", tool_calls)

if tool_calls:
    # There might be multiple tool calls; let's handle just the first one for simplicity
    tool_call = tool_calls[0]
    
    # This will give you the parsed pydantic object for the arguments
    args = json.loads(tool_call.function.arguments)
    # Call the actual Python function
    weather_result = get_weather(args["latitude"], args["longitude"])
    
    # Print or log the results
    print(f"Model requested weather for lat={args["latitude"]}, lon={args["longitude"]}")
    print(f"Weather result: {weather_result}°C")
    
    # ---- Append the tool's output back to the conversation ----
    # 1. The model's function call (tool usage)
    messages.append(completion_1.choices[0].message)
    
    # 2. The actual tool's response as a new "tool" role message
    messages.append({
        "role": "tool",
        "tool_call_id": tool_call.id,
        "content": str(weather_result)
    })

    # ---- Second completion: now the model has the weather info, 
    #      it can generate a final answer for the user ----
    completion_2 = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        tools=tools
    )

    # Print the final user-facing response
    final_answer = completion_2.choices[0].message.content
    print("Final Answer:", final_answer)
else:
    # If the model did not call the tool, just print the output as is
    print("No tool calls. Model's response:", completion_1.choices[0].message.content)

from pydantic_ai import Agent
import asyncio
from dotenv import load_dotenv

load_dotenv()

agent = Agent(
    model="gpt-4o-mini",
    system_prompt="You are a helpful assistant.",
    output_type=str
)

result = agent.run_sync("What is the capital of France?")
print(result.output)
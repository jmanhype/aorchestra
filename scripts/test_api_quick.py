import asyncio, time, sys
from openai import AsyncOpenAI

async def main():
    key = sys.argv[1]
    c = AsyncOpenAI(api_key=key, base_url='https://api.z.ai/api/paas/v4/')
    print("Testing API...", flush=True)
    start = time.time()
    r = await c.chat.completions.create(
        model='glm-4.7',
        messages=[{'role':'user','content':'What is 2+2? Just the number.'}],
        max_tokens=50
    )
    print(f"Response in {time.time()-start:.1f}s: {r.choices[0].message.content}", flush=True)
    
    # Now test with tools
    print("Testing with tools...", flush=True)
    start = time.time()
    tools = [{'type': 'function', 'function': {'name': 'calc', 'description': 'calc', 'parameters': {'type': 'object', 'properties': {'a': {'type': 'number'}}, 'required': ['a']}}}]
    r = await c.chat.completions.create(
        model='glm-4.7',
        messages=[{'role':'user','content':'Call calc with a=5'}],
        tools=tools,
        max_tokens=100
    )
    print(f"Tool response in {time.time()-start:.1f}s", flush=True)
    print(f"Tool calls: {r.choices[0].message.tool_calls}", flush=True)

asyncio.run(main())

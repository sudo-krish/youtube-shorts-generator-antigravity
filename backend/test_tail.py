import asyncio
import os

async def tail_file(file_path):
    while not os.path.exists(file_path):
        await asyncio.sleep(0.1)
    
    with open(file_path, 'r') as f:
        # Read initial content
        print(f.read())
        
        while True:
            line = f.read()
            if not line:
                await asyncio.sleep(0.1)
                continue
            print(line, end='')


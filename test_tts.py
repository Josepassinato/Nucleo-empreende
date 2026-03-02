import asyncio, os
from dotenv import load_dotenv
load_dotenv()
from nucleo.sala_reuniao.backend import gerar_audio

async def t():
    r = await gerar_audio('Olá, sou Pedro, CFO da empresa.', 'pedro')
    print('Audio gerado:', len(r) if r else 'FALHOU - None')

asyncio.run(t())

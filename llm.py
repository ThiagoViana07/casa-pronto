from dotenv import load_dotenv
from google import genai
import asyncio
import json
import os

MODELO = "gemini-3.5-flash-lite"

async def iniciar_llm():
    iniciado, llm = False, None

    try:
        load_dotenv()
        llm = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])

        iniciado = True
    except Exception as e:
        print(f"erro iniciando conexão com IA: {e}")

    return iniciado, llm


async def obter_resposta(llm, mensagens, ferramentas, modelo=MODELO):
    sucesso, resposta = False, None
    
    try:
        resposta = await llm.aio.interactions.create(
                input=mensagens, tools=ferramentas, model=modelo
            )
        sucesso = True
    except Exception as e:
        print(f"ocorreu um erro ao obter resposta: {e}")
        
    
    
    return sucesso, resposta


async def executar():
    iniciado, llm = await iniciar_llm()
    if not iniciado:
        print("Erro ao iniciar LLM")
        return
    print("LLM iniciada")

    mensagens = [
        {
            "type": "user_input",
            "content": [
                {
                    "type": "text",
                    "text": "Elabore uma reposta curta para uma saudação. NA sua resposta, se identifique com um sistema especialista dedicado a dar dicas e tirar dúvidas sobre manutenção de casas e apartamentos.",
                }
            ],
        },
        {
            "type": "user_input",
            "content": [
                {
                    "type": "text",
                    "text": "O seu nome é CasaProntoBot, e você é um sistema especialista dedicado a dar dicas e tirar dúvidas sobre manutenção de casas e apartamentos. Você deve se identificar como CasaProntoBot em todas as suas respostas.",
                }
            ],
        },
        {"type": "user_input", "content": [{"type": "text", "text": "olá, tudo bem?"}]},
    ]
    sucesso, resposta = await obter_resposta(llm, mensagens, None)
    if sucesso:
        print(f"resposta do llm: {resposta.output_text}")
    else:
        print("não foi possível obter uma resposta do llm")


if __name__ == "__main__":
    asyncio.run(executar())

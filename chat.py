from mcp.client.streamable_http import streamable_http_client
from mcp import ClientSession
from contextlib import AsyncExitStack

import asyncio
import json
from llm import *
from cache import *

NOME_ESPECIALISTA = "CasaProntoBot"
BASE_CONHECIMENTO = "conhecimento/conhecimento.json"
MODELO = "gemini-3.5-flash-lite"

CACHE = "cache"
MODELO_CACHE = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
NOME_CACHE = "casaprontobot_cache"
URL_FERRAMENTAS = "http://localhost:8000/mcp"


def iniciar_persona_assistente(conhecimento):
    persona = [
        {
            "type": "user_input",
            "content": [
                {
                    "type": "text",
                    "text": (
                        f"Você é um especialista virtual em serviços domésticos, chamado "
                        f"{NOME_ESPECIALISTA}. Você atende pelo Casa Pronto e ajuda o usuário "
                        "a como realizar serviços de pintura, alvenaria, elétrica, hidráulica e limpeza doméstica."
                    ),
                }
            ],
        },
        {
            "type": "user_input",
            "content": [
                {
                    "type": "text",
                    "text": (
                        "Sempre que uma mensagem relacionada a serviços domésticos for recebida, voce deve consultar as ferramentas para identificar a categoria do serviço e os possíveis riscos associados, e fornecer uma resposta detalhada ao usuário. Forneça informações sobre o perfil profissional adequado para cada categoria de serviço, e destaque quaisquer riscos potenciais que possam estar presentes na descrição do serviço. Caso não seja possivel identificar qual o profissional adequado, informe que não é possível identificar a categoria de serviço doméstico com confiança suficiente e peça mais detalhes ao usuário. Caso as ferramentas não consigam identificar os riscos associados, apenas não transmita a resposta sobre os riscos, mas continue fornecendo informações sobre a categoria do serviço e o perfil profissional adequado."
                    ),
                }
            ],
        },
        {
            "type": "user_input",
            "content": [
                {
                    "type": "text",
                    "text": (
                        "Se o usuário fizer uma saudação, responda de forma cordial e informe "
                        "que você é um software do Casa Pronto, não um ser humano, e que pode "
                        "ajudar com dúvidas sobre pintura, alvenaria, serviços elétricos, "
                        "hidráulicos e limpeza doméstica."
                    ),
                }
            ],
        },
        {
            "type": "user_input",
            "content": [
                {
                    "type": "text",
                    "text": (
                        "Se o usuário fizer uma pergunta que não seja uma saudação, responda "
                        "diretamente à dúvida, sem repetir seu nome ou propósito, a menos que "
                        "essa informação seja solicitada."
                    ),
                }
            ],
        },
        {
            "type": "user_input",
            "content": [
                {
                    "type": "text",
                    "text": (
                        "Responda somente a perguntas relacionadas a serviços domésticos nas "
                        "áreas de pintura, alvenaria, elétrica, hidráulica e limpeza doméstica. "
                        "Se a pergunta estiver fora desse escopo, diga: "
                        "'Não posso responder a essa pergunta. Posso ajudar com dúvidas sobre "
                        "pintura, alvenaria, serviços elétricos, hidráulicos e limpeza doméstica.'"
                    ),
                }
            ],
        },
        {
            "type": "user_input",
            "content": [
                {
                    "type": "text",
                    "text": (
                        "Para cada solicitação dentro do escopo, forneça uma resposta de"
                        "como o serviço costuma ser feito. Se faltarem informações para "
                        "classificar o pedido, faça perguntas objetivas antes de recomendar."
                    ),
                }
            ],
        },
        {
            "type": "user_input",
            "content": [
                {
                    "type": "text",
                    "text": (
                        "Não invente diagnósticos, preços ou garantias. Deixe claro quando "
                        "uma avaliação presencial for necessária. Em situações com risco "
                        "elétrico, suspeita de gás, risco estrutural, vazamento grave ou "
                        "perigo imediato, priorize a segurança e recomende procurar um "
                        "profissional qualificado ou serviço de emergência apropriado. "
                        "Não instrua o usuário a executar reparos perigosos por conta própria."
                    ),
                }
            ],
        },
    ]
    for mensagem, resposta in conhecimento:
        persona.append(
            {
                "type": "user_input",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            f"Caso o usuário diga ou pergunte '{mensagem}' ou algo parecido, "
                            f"sua resposta deve ser '{resposta}'"
                        ),
                    }
                ],
            }
        )
    return persona


async def carregar_conhecimento(base_conhecimento=BASE_CONHECIMENTO):
    carregado, conhecimento = False, []

    try:
        with open(base_conhecimento, "r", encoding="utf-8") as arquivo:
            conteudo = json.load(arquivo)
            arquivo.close()

        for pergunta_resposta in conteudo:
            pergunta = pergunta_resposta["pergunta"]
            resposta = pergunta_resposta["resposta"]
            conhecimento.append((pergunta, resposta))

        carregado = True

    except Exception as e:
        print(f"erro carregando conhecimento: {e}")

    return carregado, conhecimento



async def conectar_ferramentas(contexto, url_ferramentas = URL_FERRAMENTAS):
    conexao_mcp, ferramentas = None, []
    try:
        stream_leitura, stream_escrita = await contexto.enter_async_context(streamable_http_client(url_ferramentas))
        conexao_mcp = await contexto.enter_async_context(ClientSession(stream_leitura, stream_escrita))
        await conexao_mcp.initialize()
        
        listagem_ferramentas = await conexao_mcp.list_tools()
        for f in listagem_ferramentas.tools:
            ferramentas.append({
                "type": "function",
                "name": f.name,
                "description": f.description,
                "parameters": f.input_schema
            })
    except Exception as e:
        print(f"erro conectando as ferramentas: {e}")    

    return conexao_mcp, ferramentas

def extrair_texto_execucao(resultado):
    if resultado.structured_content:
        return json.dumps(resultado.structured_content, ensure_ascii = False)

    conteudo = []
    for c in resultado.content:
        if hasattr(c, "text"):
            conteudo.append(c.text)
        else:
            conteudo.append(str(c))

    return "\n".join(conteudo)

async def executar_ferramentas(conexao_mcp, resposta, mensagens):
    ferramentas_para_executar = [passo for passo in resposta.steps if passo.type == "function_call"]
    if ferramentas_para_executar:
            for ferramenta in ferramentas_para_executar:
                print(f"Chamando MCP: {ferramenta.name}({ferramenta.arguments})")
                execucao = await conexao_mcp.call_tool(ferramenta.name, arguments = ferramenta.arguments)
                print(f"Resultado da execução: {extrair_texto_execucao(execucao)}")
                
                mensagens.append({
                    "type": "function_result",
                    "name": ferramenta.name,
                    "call_id": ferramenta.id,
                    "result": [
                        {
                            "type": "text",
                            "text": extrair_texto_execucao(execucao)
                        }
                    ]
                })
    
    return ferramentas_para_executar != None and len(ferramentas_para_executar) > 0

async def executar():
    contexto = AsyncExitStack()
    conexao_mcp, ferramentas = await conectar_ferramentas(contexto)
    
    if not ferramentas:
            print("não foram encontradas ferramentas")
    else:
        for ferramenta in ferramentas:
            print(f"ferramenta encontrada: {ferramenta['name']}, descrição: {ferramenta['description']}")
            
    iniciado, llm = await iniciar_llm()
    if not iniciado:
        await contexto.aclose()
        print("erro iniciando llm")
        return

    carregado, conhecimento = await carregar_conhecimento()
    if not carregado:
        await contexto.aclose()
        print("erro carregando conhecimento")
        return

    iniciado, modelo_cache, colecao_cache = iniciar_cache(
        MODELO_CACHE, CACHE, NOME_CACHE
    )

    if not iniciado:
        await contexto.aclose()
        print("Erro ao iniciar cache")
        return

    persona = iniciar_persona_assistente(conhecimento)

    while True:
        mensagem = input("👤 ")
        if mensagem in ["sair", "/s"]:
            await contexto.aclose()
            break
        persona.append(
            {"type": "user_input", "content": [{"type": "text", "text": mensagem}]}
        )

        encontrada, resposta = buscar_cache(mensagem, modelo_cache, colecao_cache)

        if encontrada:
            persona.append({"type": "model_output", "text": resposta})

            print(f"🤖 {resposta} [resposta do cache]")
        else:
            ferramentas_executadas = False
            
            while True:
                sucesso, resposta = await obter_resposta(llm, persona, ferramentas, modelo=MODELO)
                if sucesso:
                    persona.extend(resposta.steps)
                    if not await executar_ferramentas(conexao_mcp, resposta, persona):
                        resposta = resposta.output_text
                        break
                    else:
                        ferramentas_executadas = True

            print(f"🤖 {resposta} [resposta do llm]")
            if not ferramentas_executadas:
                gravar_cache(mensagem, resposta, modelo_cache, colecao_cache)
    await contexto.aclose()

if __name__ == "__main__":
    asyncio.run(executar())

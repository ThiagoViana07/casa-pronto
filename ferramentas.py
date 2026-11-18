from sentence_transformers import SentenceTransformer
import numpy as np
from mcp.server.mcpserver import MCPServer

NOME = "analisador_servicos_domesticos"

mcp = MCPServer(NOME, "Um analisador de serviços domésticos, capaz de identificar a categoria do serviço a partir de uma descrição fornecida pelo usuário e identificar os possiveis riscos associados a essa descrição.")

MODELO_EMBEDDING = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

modelo = SentenceTransformer(MODELO_EMBEDDING)

EXEMPLOS_CATEGORIA = {
    "pintura": [
        "Quero pintar uma parede da sala.",
        "A tinta está descascando.",
        "Preciso pintar o portão.",
    ],
    "alvenaria": [
        "Surgiu uma trinca na parede.",
        "O reboco está soltando.",
        "Preciso trocar um piso quebrado.",
    ],
    "eletrica": [
        "Uma tomada parou de funcionar.",
        "O disjuntor está desarmando.",
        "Preciso instalar uma luminária.",
    ],
    "hidraulica": [
        "A torneira está vazando.",
        "A pia está entupida.",
        "A descarga não para de encher.",
    ],
    "limpeza": [
        "Preciso de uma faxina na casa.",
        "Quero higienizar o sofá.",
        "Há mofo numa parede.",
    ],
}

PERFIS_PROFISSIONAIS = {
    "pintura": "pintor residencial",
    "alvenaria": "pedreiro ou profissional de acabamentos",
    "eletrica": "eletricista qualificado",
    "hidraulica": "encanador ou profissional de hidráulica",
    "limpeza": "profissional de limpeza residencial",
}

EXEMPLOS_RISCO = {
    "possível risco com gás": [
        "Estou sentindo cheiro de gás na cozinha.",
        "A tubulação de gás parece estar vazando.",
    ],
    "possível risco elétrico": [
        "Saem faíscas da tomada.",
        "Há fumaça e cheiro de queimado no interruptor.",
        "Levei um choque ao tocar no equipamento.",
    ],
    "possível risco estrutural": [
        "A trinca está aumentando e a parede está cedendo.",
        "O teto está deformado e parece que pode cair.",
    ],
    "possível vazamento grave": [
        "Está jorrando muita água de um cano.",
        "O imóvel está alagando por causa de um vazamento.",
    ],
}

def gerar_embeddings(texto):
    return modelo.encode(texto,normalize_embeddings=True)

# Calculados uma vez, quando o servidor inicia.
VETORES_CATEGORIA = {
    categoria: modelo.encode(exemplos, normalize_embeddings=True)
    for categoria, exemplos in EXEMPLOS_CATEGORIA.items()
}
VETORES_RISCO = {
    risco: modelo.encode(exemplos, normalize_embeddings=True)
    for risco, exemplos in EXEMPLOS_RISCO.items()
}

def maior_similaridade(vetor_consulta, vetores_exemplo):
    # Como os vetores estão normalizados, o produto escalar equivale
    # à similaridade cosseno.
    return float(np.max(vetores_exemplo @ vetor_consulta))

@mcp.tool(name = "classificar_solicitacao", 
          title = "Classificação de Solicitação", 
          description = "Compara a descrição com exemplos de serviços domésticos e retorna a categoria mais provável. Se houver ambiguidade, retorna insuficiente")
def classificar_solicitacao(descricao):
    consulta = gerar_embeddings(descricao)
    
    pontuacoes = {
        categoria: maior_similaridade(consulta, vetores)
        for categoria, vetores in VETORES_CATEGORIA.items()
    }
    
    ranking = sorted(pontuacoes.items(), key=lambda item: item[1], reverse=True)
    categoria, similaridade = ranking[0]
    segunda_similaridade = ranking[1][1]   
    
    # Valores ilustrativos: ajuste-os usando exemplos do seu projeto.
    if similaridade < 0.55 or similaridade - segunda_similaridade < 0.05:
        return (
            "Não foi possível identificar uma categoria de serviço doméstico com confiança suficiente."
        )

    perfil = PERFIS_PROFISSIONAIS[categoria]
    return (
        f"Categoria provável: {categoria}. "
        f"Perfil profissional sugerido: {perfil}. "
    )

@mcp.tool(name = "identificar_riscos", 
          title = "Identificação de Riscos", 
          description = "Compara a descrição com exemplos de situações potencialmente perigosas "
        "e retorna os sinais de risco mais semelhantes.")

def identificar_riscos(descricao):
    consulta = gerar_embeddings(descricao)
    
    pontuacoes = {
        risco: maior_similaridade(consulta, vetores)
        for risco, vetores in VETORES_RISCO.items()
    }
    
    encontrados = [
        risco for risco, pontuacao in pontuacoes.items()
        if pontuacao >= 0.55
    ]
    
    if not encontrados:
        return (
            "Nenhum sinal configurado foi identificado com similaridade suficiente. "
            "Isso não confirma que o local esteja seguro."
        )
        
    return (
        ", ".join(encontrados)
        + ". Priorize a segurança, peça uma avaliação profissional. "
    )    
    

if __name__ == "__main__":
    
    descricao = "Quero pintar uma parede da cozinha."
    resultado = classificar_solicitacao(descricao)
    print(f"Classificação da solicitação: {resultado}")
    
    mcp.run(transport = "streamable-http", host = "0.0.0.0", streamable_http_path = "/mcp")

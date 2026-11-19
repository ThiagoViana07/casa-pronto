# Casa Pronto

O **Casa Pronto** é um assistente virtual de linha de comando para dúvidas sobre manutenção residencial. Ele conversa em português e ajuda a identificar serviços de pintura, alvenaria, elétrica, hidráulica e limpeza doméstica, sugerindo o perfil profissional adequado e apontando sinais de risco quando encontrados.

O projeto foi desenvolvido em Python e integra o modelo Gemini, ferramentas disponibilizadas por um servidor MCP, uma base local de conhecimento e um cache semântico para reutilizar respostas a perguntas semelhantes.

## Como funciona

1. `chat.py` inicia a conversa e envia as mensagens ao Gemini, usando as instruções do assistente e os exemplos da base `conhecimento/conhecimento.json`.
2. Para solicitações sobre serviços domésticos, o modelo pode chamar as ferramentas MCP oferecidas por `ferramentas.py`:
   - `classificar_solicitacao`: compara a descrição com exemplos e sugere uma categoria e um perfil profissional;
   - `identificar_riscos`: procura sinais configurados de risco elétrico, gás, estrutural ou de vazamento grave.
3. As ferramentas usam embeddings do modelo multilíngue `paraphrase-multilingual-MiniLM-L12-v2` para comparar os textos por similaridade.
4. `cache.py` mantém respostas em um banco Chroma local. Perguntas semelhantes podem receber uma resposta já armazenada, sem nova chamada ao Gemini.

O assistente funciona no terminal; este repositório não contém uma interface web.

## Requisitos

- Python 3.10 ou superior.
- Uma chave de API do Google AI Studio com acesso ao modelo Gemini configurado no código (`gemini-3.5-flash-lite`).
- Acesso à internet na primeira execução para baixar dependências e os modelos de embeddings.

## Instalação e execução

Abra um terminal na pasta `casa-pronto` e crie um ambiente virtual:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

No Windows (PowerShell), ative-o com:

```powershell
.venv\Scripts\Activate.ps1
```

Instale as dependências:

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Configure a chave da API. Copie o arquivo de exemplo e substitua o valor de `GOOGLE_API_KEY` pela sua chave:

```bash
cp .env.example .env
```

No Windows, copie `.env.example` para `.env` pelo Explorador de Arquivos ou PowerShell. Não compartilhe nem versione o arquivo `.env`.

### Inicie o servidor de ferramentas

Com o ambiente virtual ativado, abra um primeiro terminal na pasta do projeto e execute:

```bash
python ferramentas.py
```

O servidor MCP fica disponível em `http://localhost:8000/mcp`. Mantenha esse terminal aberto.

### Inicie o assistente

Abra um segundo terminal na mesma pasta, ative o ambiente virtual e execute:

```bash
python chat.py
```

Digite suas dúvidas após o prompt `👤`. Para encerrar, digite `sair` ou `/s`.

## Arquivos principais

- `chat.py`: interface de conversa no terminal, conexão ao Gemini e chamada das ferramentas MCP.
- `ferramentas.py`: servidor MCP com classificação de serviços e identificação de riscos.
- `llm.py`: inicialização do cliente Gemini e envio de solicitações ao modelo.
- `cache.py`: armazenamento e consulta de respostas semelhantes com Chroma.
- `conhecimento/conhecimento.json`: exemplos de perguntas e respostas usados nas instruções do assistente.
- `conhecimento/conhecimento_menor.json`: base reduzida usada por `julgamento.py`.
- `julgamento.py`: script de avaliação de respostas usando o Gemini.

## Observações

- A primeira inicialização pode demorar porque o Sentence Transformers baixa o modelo de embeddings. O cache local é criado na pasta `cache/`.
- A classificação depende de similaridade com exemplos e limiares definidos no código; ela é uma sugestão, não um diagnóstico ou uma inspeção do imóvel.
- Em situações perigosas, siga as orientações de segurança do assistente e procure um profissional qualificado ou o serviço de emergência apropriado.
- `julgamento.py` faz chamadas ao Gemini e pode ser executado, com o ambiente configurado, por `python julgamento.py` para avaliar exemplos da base menor.

# Agente de Atendimento — Empório da Música

Protótipo de um agente de atendimento por mensagens de texto para a Empório da Música, uma loja fictícia de instrumentos musicais em Campo Grande/MS. Desenvolvido como desafio técnico para a vaga de AI Engineer na Artefact.

O agente:
- conversa com a persona e o tom definidos no manual da loja (informal, mas profissional);
- consulta o catálogo (preços, estoque, promoções) e os pedidos por meio de ferramentas (function calling);
- responde dúvidas de políticas (horário, pagamento, frete, trocas, garantia) com base no manual da loja;
- recusa com educação o que está fora do escopo (acessórios, assuntos sem relação com a loja) e tentativas de manipulação.

## Sumário

1. [Como rodar](#como-rodar)
2. [Exemplos de conversa](#exemplos-de-conversa)
3. [Arquitetura](#arquitetura)
4. [Decisões técnicas](#decisões-técnicas)
5. [Tratamento dos dados e suposições](#tratamento-dos-dados-e-suposições)
6. [Testes](#testes)
7. [Limitações conhecidas e próximos passos](#limitações-conhecidas-e-próximos-passos)
8. [Uso de assistentes de IA](#uso-de-assistentes-de-ia)

## Como rodar

### Pré-requisitos

- Python 3.10 ou superior
- Uma chave da API do Gemini (gratuita): crie em [Google AI Studio](https://aistudio.google.com) em "Get API key". Não é preciso cadastrar forma de pagamento.

### Passo a passo

```bash
# 1. Clonar o repositório
git clone https://github.com/SEU_USUARIO/NOME_DO_REPO.git
cd NOME_DO_REPO

# 2. Criar e ativar o ambiente virtual
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Linux/macOS

# 3. Instalar as dependências
pip install -r requirements.txt

# 4. Configurar a chave
copy .env.example .env         # Windows
# cp .env.example .env         # Linux/macOS
```

Abra o `.env` e preencha a chave:

```env
GEMINI_API_KEY=sua-chave-aqui
GEMINI_MODELS=gemini-3.5-flash,gemini-3.5-flash-lite,gemini-2.5-flash,gemini-2.5-flash-lite
```

`GEMINI_MODELS` é uma lista em ordem de preferência: o primeiro é o modelo principal e os demais são reservas, usados automaticamente se o anterior estiver sobrecarregado ou sem cota.

```bash
# 5. Iniciar o chat
python main.py
```

Ao abrir, o chat mostra uma saudação fixa (sem chamar o modelo). Digite `sair` (ou Ctrl+C) para encerrar.

> Se existir uma variável de ambiente `GOOGLE_API_KEY` no sistema, o SDK do Google dá preferência a ela e mostra o aviso "Both GOOGLE_API_KEY and GEMINI_API_KEY are set". Nesse caso, remova a `GOOGLE_API_KEY` ou use a mesma chave nas duas.

### Verificações sem gastar cota

```bash
python -m src.data_loader   # carrega e trata os CSVs
python -m src.tools         # testa as ferramentas sem o modelo
python -m src.prompts       # mostra o início do system prompt montado
```

O manual de políticas já está extraído em `docs/politicas.md`. Para gerar de novo a partir do PDF: `python -m scripts.extrair_politicas`.

### Dados para testar a consulta de pedidos

A consulta de pedidos exige número do pedido, nome e e-mail do cadastro. Alguns exemplos da base fornecida (dados fictícios):

| Pedido | Status | Nome | E-mail |
|---|---|---|---|
| 5 | Entregue | Rafael Augusto Pereira | rafael.pereira@jmail.com |
| 8 | Enviado | Ana Carolina Ferreira | anacarol.ferreira@coldmail.com |
| 19 | Cancelado | Pedro Henrique Oliveira | pedro.oliveira@jmail.com |

## Exemplos de conversa

As conversas de exemplo estão na pasta [`testes/`](testes/):

| Arquivo | Cenário |
|---|---|
| `01_catalogo_e_historico.md` | Preço do Takamine GD20, pergunta de continuação ("o mais barato desses") e filtro por tipo de corda |
| `02_violoes_ate_1000.md` | Busca por faixa de preço, com aviso do total de opções |
| `03_informacoes_da_loja.md` | Endereço, horário (usando a data e hora atuais) e WhatsApp |
| `04_devolucao_de_pedido.md` | Direito de arrependimento: verificação de identidade, consulta do pedido e aplicação do prazo do manual |
| `05_fora_do_escopo_e_seguranca.md` | Acessório (amplificador), pergunta sem relação com a loja e tentativa de manipulação |

As linhas `[ferramenta]` mostram quando o agente consultou os dados, com nome e e-mail mascarados.

## Arquitetura

```
Cliente digita uma mensagem
        │
        ▼
main.py (chat no terminal)
        │
        ▼
src/agent.py ── histórico da conversa + system prompt + declaração das ferramentas ──► Gemini
        ▲                                                                                │
        │        o modelo responde com texto (fim) OU pede uma ferramenta                │
        │                                                                                ▼
        └──── resultado da ferramenta ◄──── src/tools.py ◄──── src/data_loader.py ◄─ data/*.csv
```

O loop de function calling:
1. A mensagem do cliente entra no histórico.
2. O histórico, o system prompt e a descrição das ferramentas vão para o Gemini.
3. Se o modelo pedir uma ferramenta, o código executa a função Python e devolve o resultado ao modelo.
4. O ciclo se repete até o modelo responder com texto (limite de 5 passos por mensagem).

### Estrutura do projeto

```
├── data/                      # CSVs e PDF fornecidos (não alterados)
├── docs/politicas.md          # manual de políticas extraído do PDF
├── scripts/
│   └── extrair_politicas.py   # extração do PDF para Markdown (roda uma vez)
├── src/
│   ├── config.py              # leitura do .env e caminhos do projeto
│   ├── data_loader.py         # carrega e trata os CSVs (uma vez, com cache)
│   ├── tools.py               # ferramentas: buscar_produtos e consultar_pedido
│   ├── prompts.py             # persona, regras, data atual e manual
│   ├── agent.py               # loop de function calling, novas tentativas e modelos reserva
│   └── spinner.py             # indicador "Pensando..." no terminal
├── testes/                    # conversas de exemplo e planilha de cenários de teste
├── main.py                    # ponto de entrada (chat no terminal)
├── requirements.txt
└── .env.example
```

## Decisões técnicas

### Abordagem: function calling + manual no contexto

O desafio pede que o agente saiba quando consultar **dados** e quando consultar **políticas**. Tratei os dois tipos de informação de forma diferente, porque têm naturezas diferentes:

- **Dados (CSVs): ferramentas com function calling.** Perguntas de preço, estoque e pedido exigem valores exatos e filtros numéricos ("violões até R$1000", "pedido 15"). Busca por similaridade (vetores) é ruim nisso. O modelo decide quando chamar `buscar_produtos` ou `consultar_pedido` e com quais parâmetros.
- **Políticas (PDF): o manual inteiro no system prompt, sem RAG.** O manual tem 8 páginas, cerca de 5 mil tokens com as regras. Isso cabe com folga no contexto e traz vantagens: não há risco de recuperar o trecho errado, perguntas que cruzam seções (arrependimento, defeito e garantia) ficam cobertas e as contradições do manual ficam visíveis para serem resolvidas no prompt. Eu migraria para RAG se a base crescesse (vários manuais, FAQs, catálogo com centenas de descrições) ou se o custo por chamada passasse a pesar.

### Funções prontas em vez de text-to-SQL

O modelo não escreve consultas livres: ele só chama funções com parâmetros definidos. É mais seguro (não há como gerar uma consulta destrutiva ou acessar dados de outro cliente) e mais previsível. O custo é a flexibilidade: perguntas que as funções não cobrem (por exemplo, filtrar por cor) não são respondidas.

### Sem framework (LangChain etc.)

O loop de function calling foi escrito à mão, com o SDK oficial do Google (`google-genai`). São poucas linhas, cada passo é visível e o projeto fica com menos dependências. Para um agente deste tamanho, um framework acrescentaria abstrações sem ganho real. Em um sistema maior (vários agentes, memória persistente, observabilidade), eu avaliaria o LangGraph.

### Modelo e provedor: Gemini

- **Por que o Gemini:** tem cota gratuita (o avaliador roda o projeto sem custo), suporta function calling e tem um SDK oficial simples.
- **Modelos `flash`:** rápidos e baratos, suficientes para atendimento. Modelos "pro" são mais lentos e têm cota gratuita bem menor; versões `preview` e aliases `-latest` foram evitados para que o comportamento seja reproduzível.
- **Modelo configurável pelo `.env`:** trocar de modelo não exige mudar o código.

### Contas no código, não no modelo

Tudo o que é cálculo fica na ferramenta, e o modelo só apresenta o resultado:
- preço final com a promoção ativa, já formatado em reais (`R$ 1.299,90`);
- preço no PIX (5% de desconto), já como frase pronta, inclusive quando o desconto não se aplica porque o produto já está em promoção;
- total de produtos encontrados, para o agente dizer "temos 12 opções";
- dias desde o pedido e desde a entrega prevista, para comparar com os prazos do manual;
- se a entrega está atrasada (pedido enviado com previsão vencida).

Nos primeiros testes, quando essas informações não vinham prontas, o modelo deduzia errado (por exemplo, afirmou que um pedido "enviado" já tinha sido entregue).

### Verificação de identidade nos pedidos

Para consultar um pedido, o cliente informa **número do pedido, nome e e-mail do cadastro**.
- A verificação acontece no código: a ferramenta só devolve os dados se o nome e o e-mail baterem com o cliente do pedido. O modelo não tem como liberar um pedido por conta própria.
- Pedido inexistente, nome errado ou e-mail errado recebem a mesma resposta ("nenhum pedido encontrado com esses dados"), para não revelar se um pedido existe ou a quem pertence.
- O nome é flexível (ignora acentos e maiúsculas e aceita "Rafael Pereira" para "Rafael Augusto Pereira"); o e-mail precisa ser igual.
- A resposta da ferramenta não traz e-mail, telefone nem cidade, apenas o primeiro nome para cumprimentar.

Considerei usar CPF, mas a base fornecida não tem esse dado, e a regra adotada foi usar apenas o que está nos documentos.

### Estratégia de prompt

O system prompt é montado em `src/prompts.py` a partir de quatro blocos:
1. **Persona**, tirada da seção 7.1 do manual ("como um amigo que entende de música").
2. **Data e hora atuais**, para responder "estão abertos agora?" e calcular prazos.
3. **Regras**, divididas em seções: quando consultar cada fonte, produtos, pedidos, escopo, segurança e formato.
4. **O manual completo**, entre as tags `<manual>` e `</manual>`, separando o que é instrução do que é material de referência.

As regras foram escritas a partir das falhas encontradas nos testes. O aprendizado principal: **regras genéricas fazem o modelo adivinhar; regras com informação concreta funcionam.** Exemplo: a regra "avise quando o cliente pedir algo que a loja não vende" fazia o modelo buscar "amplificador" no catálogo para descobrir. Ao listar explicitamente os acessórios que a loja não vende e proibir a busca para eles, a resposta passou a ser direta.

O prompt também tem uma seção de **esclarecimentos** que resolve as contradições do manual (ver [suposições](#tratamento-dos-dados-e-suposições)).

### Resiliência a falhas do provedor

Na cota gratuita, o Gemini às vezes responde "sobrecarregado" (503) ou "cota esgotada" (429). O agente:
- tem timeout de 30 segundos por chamada;
- em caso de 503, tenta de novo com espera crescente (2s, 4s);
- em caso de 429, troca imediatamente para o próximo modelo da lista (esperar não resolve um limite diário);
- se tudo falhar, responde ao cliente com uma mensagem amigável, desfaz a rodada no histórico e mantém o chat aberto.

### Privacidade

- Proteção em duas camadas para dados de clientes: o prompt proíbe informar dados de terceiros e a ferramenta nem devolve esses dados.
- O log do terminal mascara nome e e-mail (`Rafael ***`, `ra***@jmail.com`).
- Erros de ferramenta aparecem no log (`[erro na ferramenta]`), para que uma falha não pareça um problema do modelo.

### Histórico da conversa

O histórico fica em memória durante a sessão e é reenviado ao modelo a cada mensagem, o que permite perguntas de continuação ("e o mais barato desses?"). Não há persistência entre sessões: para um protótipo de terminal, isso não traria ganho para o cliente, e guardar conversas com nome e e-mail exigiria cuidados adicionais de LGPD.

### Interface

Chat no terminal (`main.py`). Ao iniciar, mostra uma saudação fixa, sem chamar o modelo; enquanto o modelo responde, aparece um indicador "Pensando...". As linhas `[ferramenta]` e `[aviso]` são logs de depuração que mostram quando o agente consultou os dados ou trocou de modelo; numa interface para o cliente, elas não apareceriam. O foco do desafio é o agente; a lógica está separada da interface, então uma API ou interface web reaproveitaria o `src/agent.py` sem mudanças.

## Tratamento dos dados e suposições

### Tratamento feito

- `specs`: o texto JSON de cada produto vira um dicionário, permitindo filtrar por tipo de corda (`strings`) e captação (`electronics`).
- Datas convertidas para o tipo data.
- Nome da categoria incluído na tabela de produtos.
- Busca sem diferenciar acentos e maiúsculas ("violao" encontra "Violão").
- Por padrão, a busca mostra só produtos à venda e com estoque; para um produto específico, o agente busca também os esgotados, descontinuados e "em breve", para explicar a situação.
- Promoções: só as ativas (`is_active = 1`) entram no preço; as encerradas são informadas para o agente avisar com transparência, como o manual pede.
- Status de pedido e forma de pagamento traduzidos (`credit_12x` vira "Cartão de crédito em 12x").
- Os arquivos em `data/` não são alterados; todo o tratamento é feito em memória.

### Inconsistências encontradas e como foram tratadas

| Inconsistência | Decisão |
|---|---|
| Manual com dois WhatsApps: (67) 3341-4444 e (67) 3321-4500 | Usar (67) 3341-4444, que aparece nos dados oficiais da empresa |
| E-mail com acento na tabela do manual (`empóriodamusica`) | Usar `contato@emporiodamusica.com.br` |
| Parcela mínima: R$ 100 na tabela, mas faixas diferentes na seção 3.1 | Valem as faixas da seção 3.1; a frase ambígua de até 3x foi lida como parcela mínima de R$ 50 |
| Direito de arrependimento vale só para compras online, mas os pedidos não indicam o canal | Pedidos do sistema tratados como compras online |
| Manual cita sopros e cordas orquestrais, mas o catálogo não tem nenhum | O agente informa que no momento não há esses instrumentos |
| Manual fala em "mais de 300 instrumentos"; o catálogo tem 65 | O agente não cita quantidade de itens do catálogo |
| Status `coming_soon` sem regra no manual | Informar que ainda não está disponível e sugerir alternativas |
| Manual sugere indicar lojas parceiras, mas não cita nenhuma | Não indicar lojas |
| Sem data real de recebimento dos pedidos | A previsão de entrega é usada como aproximação do recebimento |
| Os pedidos vão até março de 2026 e o agente usa a data de hoje | Todos os prazos de devolução e troca aparecem como vencidos; pedidos "enviados" com previsão vencida são sinalizados como atrasados |
| Produtos 135 a 144: nome, descrição e specs não batem (ex.: "Korg" descrito como Roland de 88 teclas, specs com 61) | Não corrigido; registrado como problema dos dados de origem |
| Totais dos pedidos 3 e 20 diferentes da soma dos itens; desconto do PIX não refletido nos totais; parcelamentos abaixo da parcela mínima (pedidos 7, 9 e 16) | Não usados pelo agente; registrados como problemas dos dados |
| Pedido 3 entregue com produto `coming_soon` | Registrado como problema dos dados |
| Clientes 11 e 43 com o mesmo e-mail | Sem impacto na verificação, que compara o e-mail com o cliente do próprio pedido |

## Testes

Mapeei 30 cenários de teste ([`testes/Cenário de Teste - Agente IA Conversa.csv`](testes/Cenário%20de%20Teste%20-%20Agente%20IA%20Conversa.csv)), cada um com a pergunta, a ferramenta esperada, o que precisa aparecer na resposta e o que não pode acontecer. **29 foram validados manualmente no chat** e 1 ficou parcial (ver abaixo), cobrindo catálogo, histórico, promoções ativas e encerradas, produtos esgotados, descontinuados e em breve, políticas, pedidos, escopo e segurança. Vários passaram só depois de ajustes na ferramenta ou no prompt; a coluna "Observação" registra o antes e o depois.

Alguns ciclos de teste e correção que moldaram o projeto:
- **O agente inventava características** (chamou um violão sem captação de eletroacústico e inventou "cutaway"). Correção: filtros estruturados por tipo de corda e captação na ferramenta e uma regra para descrever só o que vem nos dados.
- **Promoção encerrada tratada como inexistente** ("sem desconto de Páscoa cadastrado"). Causa: a ferramenta só devolvia promoções ativas. Correção: incluir as promoções encerradas no retorno, para o agente avisar que a promoção acabou.
- **Uma ferramenta quebrada parecia problema do modelo:** o agente chamava a busca 5 vezes seguidas sem sucesso. O erro (um parâmetro faltando na assinatura da função) estava escondido pelo tratamento de exceções. Correção: erros de ferramenta passaram a aparecer no log, e cada ferramenta é testada isolada (`python -m src.tools`) antes de ir para o chat.
- **Preço no PIX:** com o modelo calculando os 5%, ele errou o valor. Com o valor pronto na ferramenta, mas num campo que podia ser um preço ou vazio (produto em promoção), ele acertou o valor e se confundiu na explicação. A correção foi a ferramenta devolver a frase pronta. Ainda assim, o modelo reserva (`flash-lite`) arredondou um preço promocional ao escrever (R$ 439,00 em vez de R$ 439,20), e por isso esse cenário ficou como parcial.
- **Resposta que prometia antes de verificar** ("Com certeza!" para uma devolução fora do prazo). Correção: regra para explicar a política e só concluir depois de consultar o pedido.

## Limitações conhecidas e próximos passos

**Limitações**
- **Cota gratuita do Gemini:** o limite diário por modelo é baixo (por exemplo, 20 requisições por dia) e cada mensagem consome de 2 a 4 requisições. A lista de modelos reserva reduz o problema, mas não o elimina.
- **Dados pessoais enviados ao provedor:** o nome e o e-mail informados pelo cliente vão para o Gemini, que na cota gratuita pode usar os dados para melhorar os modelos. Aceitável com dados fictícios, não em produção.
- **Busca por texto simples:** procura palavras no nome e na descrição. Não há filtro por cor ou marca, nem busca por significado.
- **O modelo varia entre execuções:** a mesma pergunta pode ter respostas um pouco diferentes.
- **Precisão dos modelos reserva:** os preços vêm prontos da ferramenta, mas os modelos `lite` às vezes erram ao transcrevê-los (por exemplo, R$ 439,00 em vez de R$ 439,20).

**O que eu faria com mais tempo**
- Automatizar os 30 cenários de teste com um script que roda as perguntas e verifica as respostas.
- Verificar automaticamente se todo valor em reais na resposta do agente aparece nos dados retornados pelas ferramentas, antes de enviar a resposta ao cliente.
- Proteger dados pessoais antes do envio ao modelo e usar um plano pago do provedor, que não usa os dados para treino.
- Adicionar filtros por marca e cor e busca semântica nas descrições, combinada com os filtros.
- Expor o agente por uma API e integrar com um canal real, como o WhatsApp.

## Uso de assistentes de IA
 
Utilizei o Claude (Anthropic) como ferramenta de apoio durante o desenvolvimento do projeto, desde a análise dos dados e definição da arquitetura até a implementação, os testes e a documentação.
 
O uso foi dividido em três etapas principais:
 
- **Análise e arquitetura:** discussão das abordagens possíveis (RAG, function calling, ReAct e text-to-SQL), análise dos dados fornecidos e avaliação das decisões técnicas. As decisões finais foram tomadas considerando os requisitos do desafio.
- **Desenvolvimento:** implementação dos componentes com apoio de explicações e sugestões de código. Cada etapa foi executada e testada localmente, com análise dos erros e ajustes necessários.
- **Validação:** elaboração dos cenários de teste, análise das respostas do agente e correção de falhas identificadas no comportamento, nas ferramentas e nos prompts.
O README e a documentação também foram elaborados com apoio do Claude, a partir das anotações e dos resultados dos testes, e revisados por mim.
# Decisões e suposições sobre os dados

Ao analisar os CSVs e o manual de políticas (`data/políticas_da_loja.pdf`), encontrei contradições, lacunas e erros. Este documento registra cada um, a decisão tomada e a justificativa. Os arquivos originais em `data/` não foram alterados.

## Contradições e lacunas do manual

| Ponto | O que o manual diz | Decisão | Justificativa |
|---|---|---|---|
| WhatsApp | (67) 3341-4444 na capa e nos dados da empresa; (67) 3321-4500 na seção 7 | Informar (67) 3341-4444 | Aparece duas vezes, inclusive nos dados oficiais da empresa |
| E-mail | `contato@emporiodamusica.com.br` na capa; `contato@empóriodamusica.com.br` na tabela | Informar a versão sem acento | Com acento não é um endereço de e-mail válido |
| Parcela mínima | Tabela: R$ 100,00 para o cartão de crédito. Seção 3.1: faixas diferentes por número de parcelas | Valem as faixas da seção 3.1 | É a seção específica e mais detalhada sobre parcelamento |
| Parcelamento até 3x | "Sem valor mínimo de parcela (exceto abaixo de R$ 50,00)" | Parcela mínima de R$ 50,00 | A frase é ambígua; esta é a leitura mais conservadora |
| Direito de arrependimento | Vale para compras online | Pedidos do sistema tratados como compras online | Os pedidos não têm coluna de canal de venda, e todos têm entrega e rastreio |
| Categorias | Cita instrumentos de sopro e cordas orquestrais | Informar que no momento não há esses instrumentos | O catálogo não tem nenhum produto nas categorias 6, 7 e 8 |
| Tamanho do catálogo | "Mais de 300 instrumentos" | O agente não cita a quantidade de itens | O catálogo tem 65 produtos |
| Produtos `coming_soon` | Não há regra | Informar que ainda não está disponível e sugerir alternativas | Segue a lógica das regras de produto esgotado e descontinuado (seção 7.3) |
| Lojas parceiras | Sugere indicar lojas parceiras para acessórios | Não indicar lojas | Nenhuma loja parceira é citada; o agente inventaria |
| Reclamações e "consultar a gerência" | Registrar e encaminhar; consultar a gerência em caso de dúvida | Orientar o contato com a equipe pelo WhatsApp ou e-mail | O agente não tem como registrar reclamações nem falar com a gerência |

## Lacunas dos dados que afetam o agente

| Ponto | Decisão | Consequência |
|---|---|---|
| Não há data real de recebimento do pedido | A previsão de entrega (`estimated_delivery`) é usada como data de recebimento para o prazo de arrependimento | O prazo pode ter alguns dias de diferença em relação ao real |
| Os pedidos vão até março de 2026, e o agente usa a data de hoje | Manter a data real | Todos os prazos de devolução, troca e garantia legal aparecem como vencidos; pedidos "enviados" com previsão vencida (ex.: pedido 8) são sinalizados como atrasados, e o agente orienta o contato com a equipe |
| A base de clientes não tem CPF | Verificação de identidade por número do pedido, nome e e-mail | Usa apenas dados que existem na base |
| Clientes 11 e 43 têm o mesmo e-mail | Nenhuma | Sem impacto: a verificação compara o e-mail com o cliente do próprio pedido |

## Problemas dos dados registrados, mas não corrigidos

Estes problemas não afetam as respostas do agente, porque ele exibe os valores gravados sem recalcular. Ficam registrados para a equipe da loja.

- **Nome, descrição e especificações não batem nos produtos 135 a 144** (baixos, baterias e teclados). Exemplos: "Music Man Bass 1X" descrito como Fender Jazz Bass; "Teclado Sintetizador Korg Synth 1 Pro" descrito como um Roland de 88 teclas, com `specs` de 61 teclas; "Yamaha Bass 3X" descrito como um Ibanez de 5 cordas, com `specs` de 4 cordas.
- **Totais de pedidos diferentes da soma dos itens:** pedido 3 (R$ 3.450,00 contra R$ 3.498,00 dos itens) e pedido 20 (R$ 1.400,00 contra R$ 1.488,00).
- **Desconto do PIX não aplicado:** os pedidos pagos com PIX (1, 5, 10, 13 e 17) têm o preço cheio, sem os 5% previstos no manual. Nenhum deles é de produto em promoção.
- **Parcelamentos abaixo da parcela mínima:** pedido 7 (R$ 159,90 em 12x), pedido 9 (R$ 349,90 em 6x) e pedido 16 (R$ 429,90 em 6x).
- **Pedido 3 entregue em 2025 com um produto marcado como `coming_soon`** (Kala barítono, produto 130).
- **Produto ativo com estoque zero** (Giannini GF-3D, produto 96): tratado como esgotado.
- **Promoções fora das faixas do manual:** por exemplo, Aniversário da Loja com 30% (o manual fala em 10% a 25%) e Semana do Músico com 40%; e campanhas no CSV que não existem no manual ("Promoção de Páscoa", "Liquidação de Inverno", "Desconto Exclusivo", "Oferta Especial"). Só as promoções ativas (`is_active = 1`) são usadas no preço.

# Consulta de preço e continuação da conversa

O cliente pergunta o preço de um produto específico e depois faz perguntas que dependem do histórico ("o mais barato desses", "nessa linha de aço"). O agente consulta o catálogo a cada pergunta e usa filtros estruturados (tipo de corda).

Você: Quanto custa o Takamine GD20?
  [aviso] cota do gemini-3.5-flash esgotada, trocando de modelo...
  [ferramenta] buscar_produtos({'termo': 'Takamine GD20', 'apenas_disponiveis': False})
  [aviso] cota do gemini-3.5-flash esgotada, trocando de modelo...
                  
Atendente: O Takamine GD20 Dreadnought Natural custa R$ 2.199,00. Ele tem tampo sólido em cedro e cordas de aço.

Você: E qual é o mais barato desses?
  [aviso] cota do gemini-3.5-flash esgotada, trocando de modelo...
  [ferramenta] buscar_produtos({'termo': 'Takamine GD20', 'apenas_disponiveis': True})
  [aviso] cota do gemini-3.5-flash esgotada, trocando de modelo...
                  
Atendente: No momento, o Takamine GD20 que temos disponível é esse mesmo modelo que custa R$ 2.199,00. 

Se quiser ver outras opções de violões ou de outros instrumentos em conta, é só me falar a faixa de preço que você procura.

Você: Quero opções mais em conta nessa linha de aço
  [aviso] cota do gemini-3.5-flash esgotada, trocando de modelo...
  [ferramenta] buscar_produtos({'apenas_disponiveis': True, 'preco_max': 2000, 'cordas': 'aço'})
  [aviso] cota do gemini-3.5-flash esgotada, trocando de modelo...
                  
Atendente: Temos várias opções de violões com cordas de aço mais em conta. Encontrei 11 opções no total, aqui estão as 5 mais em conta:

- Shelby SN-100 Folk Aço Preto por R$ 549,00
- Giannini GF-1R Aço Folk Sunburst por R$ 579,90 - Visual elegante com tampo em Spruce.
- Yamaha F310 Aço Natural por R$ 699,90 - Um dos modelos mais vendidos do mundo para iniciantes e intermediários.
- Tagima Dallas Tuner Aço Natural por R$ 749,00 - Corpo confortável e som brilhante.
- Shelby SGD-195E Elétrico Aço Sunburst por R$ 799,00 - Opção eletroacústica com captação e afinador.

Se quiser, posso filtrar por preço máximo ou por modelos eletroacústicos.
from src.agent import Agente

SAUDACAO = """Atendente: Oi! Aqui é o assistente virtual da Empório da Música 🎸 Sua música começa aqui!

Como posso te ajudar?
"""

def main():
    agente = Agente()
    print("🎸 Empório da Música — atendimento virtual (digite 'sair' para encerrar)\n")
    print(SAUDACAO)

    while True:
        mensagem = input("Você: ").strip()
        if not mensagem:
            continue
        if mensagem.lower() in {"sair", "exit", "quit"}:
            print("Até mais! 🎶")
            break

        resposta = agente.responder(mensagem)
        print(f"\nAtendente: {resposta}\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nAté mais! 🎶")
from src.agent import Agente


def main():
    agente = Agente()
    print("🎸 Empório da Música — atendimento virtual (digite 'sair' para encerrar)\n")

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
    main()
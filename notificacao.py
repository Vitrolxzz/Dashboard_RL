import requests

def enviar_notificacao(gols_jogador, gols_adversario):

    url = "https://ntfy.sh/rocket_league"

    if gols_jogador > gols_adversario:
        titulo = "Vitoria!"
        prioridade = "4"
        emoji = "🏆"

    elif gols_jogador < gols_adversario:
        titulo = "Derrota!"
        prioridade = "3"
        emoji = "❌"

    else:
        titulo = "Empate!"
        prioridade = "3"
        emoji = "🤝"

    mensagem = (
        f"{emoji} Partida encerrada!\n"
        f"Resultado: {gols_jogador} x {gols_adversario}"
    )

    cabecalho = {
        "Title": titulo,
        "Priority": prioridade
    }

    try:
        resposta = requests.post(
            url,
            data=mensagem.encode("utf-8"),
            headers=cabecalho,
            timeout=10
        )

        if resposta.status_code == 200:
            print("Notificacao enviada!")
        else:
            print("Erro:", resposta.text)

    except requests.RequestException as erro:
        print("Falha na conexao:", erro)


# Simulacao de partida
# enviar_notificacao(4, 3)

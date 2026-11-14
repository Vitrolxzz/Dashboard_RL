
import socket
import json
import requests
import time

HOST = "127.0.0.1"
PORTA = 49123

URL_NTFY = "https://ntfy.sh/rocket_league"

ultimo_relogio = 0
ultima_partida_notificada = None


def enviar_notificacao(mensagem):
    cabecalho = {
        "Title": "Rocket League Dashboard",
        "Priority": "4"
    }

    try:
        resposta = requests.post(
            URL_NTFY,
            data=mensagem.encode("utf-8"),
            headers=cabecalho,
            timeout=10
        )

        if resposta.status_code == 200:
            print("Notificação enviada!")
        else:
            print("Erro ao enviar:", resposta.text)

    except requests.RequestException as erro:
        print("Erro no ntfy:", erro)


def formatar_tempo(segundos):
    minutos = segundos // 60
    segundos = segundos % 60

    return f"{minutos:02d}:{segundos:02d}"


def processar_evento(evento):
    global ultimo_relogio
    global ultima_partida_notificada

    nome_evento = evento.get("Event")
    conteudo = evento.get("Data", {})

    if isinstance(conteudo, str):
        try:
            conteudo = json.loads(conteudo)
        except json.JSONDecodeError:
            return

    # Detectar início de uma nova partida
    if nome_evento == "UpdateState":

        match_guid = conteudo.get("MatchGuid")
        jogo = conteudo.get("Game", {})
        jogadores = conteudo.get("Players", [])
        equipes = jogo.get("Teams", [])

        if (
            match_guid
            and isinstance(jogo, dict)
            and jogadores
            and len(equipes) == 2
            and match_guid != ultima_partida_notificada
        ):

            ultima_partida_notificada = match_guid
            ultimo_relogio = jogo.get("TimeSeconds", 0)

            mensagem = (
                "🏁 NOVA PARTIDA!\n"
                "Rocket League iniciado!\n"
                f"👥 Jogadores: {len(jogadores)}"
            )

            print("\n" + mensagem)
            enviar_notificacao(mensagem)

    # Atualizar cronômetro
    elif nome_evento == "ClockUpdatedSeconds":
        ultimo_relogio = conteudo.get("TimeSeconds", 0)

    # Detectar gols
    elif nome_evento == "GoalScored":

        jogador = conteudo.get("Scorer", {}).get("Name", "")

        if jogador:
            assistente = conteudo.get("Assister", {}).get("Name")
            tempo = formatar_tempo(ultimo_relogio)

            mensagem = f"⚽ GOL DE {jogador}!\n"

            if assistente:
                mensagem += f"🎯 Assistência: {assistente}\n"

            mensagem += f"⏱️ Tempo: {tempo}"

            print("\n" + mensagem)
            enviar_notificacao(mensagem)

    # Detectar defesas
    elif nome_evento == "StatfeedEvent":

        tipo = conteudo.get("EventName")
        jogador = conteudo.get("MainTarget", {}).get("Name")

        tempo = formatar_tempo(ultimo_relogio)

        if tipo == "Save":
            mensagem = (
                f"🧤 DEFESA!\n"
                f"Jogador: {jogador}\n"
                f"⏱️ Tempo: {tempo}"
            )

            print("\n" + mensagem)
            enviar_notificacao(mensagem)

        elif tipo == "EpicSave":
            mensagem = (
                f"🔥 DEFESA ÉPICA!\n"
                f"Jogador: {jogador}\n"
                f"⏱️ Tempo: {tempo}"
            )

            print("\n" + mensagem)
            enviar_notificacao(mensagem)


print("Rocket League Dashboard iniciado!")

while True:

    cliente = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        print("\nTentando conectar ao Rocket League...")

        cliente.connect((HOST, PORTA))

        print("Conectado! Aguardando eventos...\n")

        buffer = ""
        decodificador = json.JSONDecoder()

        while True:
            dados = cliente.recv(8192)

            if not dados:
                print("Conexão encerrada pelo Rocket League.")
                break

            buffer += dados.decode("utf-8", errors="replace")

            while buffer.strip():
                buffer = buffer.lstrip()

                try:
                    evento, posicao = decodificador.raw_decode(buffer)
                    buffer = buffer[posicao:]

                except json.JSONDecodeError:
                    break

                processar_evento(evento)

    except ConnectionRefusedError:
        print("Rocket League indisponível. Tentando novamente...")

    except OSError as erro:
        print("Conexão perdida:", erro)

    except KeyboardInterrupt:
        print("\nDashboard encerrado.")
        break

    finally:
        cliente.close()

    time.sleep(3)

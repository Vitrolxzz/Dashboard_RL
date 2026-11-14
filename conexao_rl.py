import socket
import json
import requests
import time

HOST = "127.0.0.1"
PORTA = 49123

URL_NTFY = "https://ntfy.sh/rocket_league"

ultimo_relogio = 0
ultima_partida_notificada = None

placar_azul = 0
placar_laranja = 0
partida_finalizada = False


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
            print("Notificacao enviada!")
        else:
            print("Erro ao enviar:", resposta.text)

    except requests.RequestException as erro:
        print("Erro no ntfy:", erro)


def formatar_tempo(segundos):
    segundos = int(segundos or 0)
    minutos = segundos // 60
    segundos = segundos % 60

    return f"{minutos:02d}:{segundos:02d}"


def processar_evento(evento):
    global ultimo_relogio
    global ultima_partida_notificada
    global placar_azul
    global placar_laranja
    global partida_finalizada

    nome_evento = evento.get("Event")
    conteudo = evento.get("Data", {})

    if isinstance(conteudo, str):
        try:
            conteudo = json.loads(conteudo)
        except json.JSONDecodeError:
            return

    if not isinstance(conteudo, dict):
        return

    # Atualizacoes do estado da partida
    if nome_evento == "UpdateState":
        match_guid = conteudo.get("MatchGuid")
        jogo = conteudo.get("Game", {})
        jogadores = conteudo.get("Players", [])
        equipes = jogo.get("Teams", []) if isinstance(jogo, dict) else []

        # Identifica uma nova partida uma unica vez
        if (
            match_guid
            and isinstance(jogo, dict)
            and jogadores
            and len(equipes) == 2
            and match_guid != ultima_partida_notificada
        ):
            ultima_partida_notificada = match_guid
            partida_finalizada = False
            placar_azul = 0
            placar_laranja = 0
            ultimo_relogio = jogo.get("TimeSeconds", 0)

            mensagem = (
                "🏁 NOVA PARTIDA!\n"
                "Rocket League iniciado!\n"
                f"👥 Jogadores: {len(jogadores)}"
            )

            print("\n" + mensagem)
            enviar_notificacao(mensagem)

        # Mantem o placar atualizado
        if len(equipes) == 2:
            for equipe in equipes:
                if equipe.get("TeamNum") == 0:
                    placar_azul = equipe.get("Score", 0)
                elif equipe.get("TeamNum") == 1:
                    placar_laranja = equipe.get("Score", 0)

        # Atualiza o relogio quando esse dado estiver disponivel
        if isinstance(jogo, dict) and "TimeSeconds" in jogo:
            ultimo_relogio = jogo.get("TimeSeconds", ultimo_relogio)

    # Atualizar cronometro
    elif nome_evento == "ClockUpdatedSeconds":
        ultimo_relogio = conteudo.get("TimeSeconds", ultimo_relogio)

    # Detectar gols
    elif nome_evento == "GoalScored":
        jogador = conteudo.get("Scorer", {}).get("Name", "")

        # Alguns eventos podem chegar sem o nome do autor do gol
        if jogador:
            assistente = conteudo.get("Assister", {}).get("Name")
            tempo = formatar_tempo(ultimo_relogio)

            mensagem = f"⚽ GOL DE {jogador}!\n"

            if assistente:
                mensagem += f"🎯 Assistencia: {assistente}\n"

            mensagem += f"⏱️ Tempo: {tempo}"

            print("\n" + mensagem)
            enviar_notificacao(mensagem)

    # Detectar encerramento da partida
    elif nome_evento == "MatchEnded":
        if not partida_finalizada:
            partida_finalizada = True

            vencedor = conteudo.get("WinnerTeamNum")

            if vencedor == 0:
                resultado = "🔵 EQUIPE AZUL VENCEU!"
            elif vencedor == 1:
                resultado = "🟠 EQUIPE LARANJA VENCEU!"
            else:
                resultado = "Resultado do vencedor indisponivel."

            mensagem = (
                "🏁 PARTIDA ENCERRADA!\n\n"
                f"{resultado}\n"
                f"🔵 Azul: {placar_azul}\n"
                f"🟠 Laranja: {placar_laranja}"
            )

            print("\n" + mensagem)
            enviar_notificacao(mensagem)

    # Detectar defesas
    elif nome_evento == "StatfeedEvent":
        tipo = conteudo.get("EventName")
        jogador = conteudo.get("MainTarget", {}).get("Name")

        if not jogador:
            return

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

        # Sem limite de tempo para receber dados
        cliente.connect((HOST, PORTA))

        print("Conectado! Aguardando eventos...\n")

        buffer = ""
        decodificador = json.JSONDecoder()

        while True:
            dados = cliente.recv(8192)

            if not dados:
                print("Conexao encerrada pelo Rocket League.")
                break

            buffer += dados.decode("utf-8", errors="replace")

            while buffer.strip():
                buffer = buffer.lstrip()

                try:
                    evento, posicao = decodificador.raw_decode(buffer)
                    buffer = buffer[posicao:]

                except json.JSONDecodeError:
                    # Aguarda o restante do JSON chegar pelo socket
                    break

                processar_evento(evento)

    except ConnectionRefusedError:
        print("Rocket League indisponivel. Tentando novamente...")

    except OSError as erro:
        print("Conexao perdida:", erro)

    except KeyboardInterrupt:
        print("\nDashboard encerrado.")
        break

    finally:
        cliente.close()

    time.sleep(3)


import socket
import json
import requests

HOST = "127.0.0.1"
PORTA = 49123

URL_NTFY = "https://ntfy.sh/rocket_league"

ultimo_relogio = 0


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
        print("Erro de conexão com ntfy:", erro)


def formatar_tempo(segundos):
    minutos = segundos // 60
    segundos = segundos % 60

    return f"{minutos:02d}:{segundos:02d}"


cliente = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
cliente.settimeout(10)

buffer = ""
decodificador = json.JSONDecoder()

try:
    cliente.connect((HOST, PORTA))

    print("Conectado ao Rocket League!")
    print("Aguardando eventos...\n")

    while True:
        dados = cliente.recv(8192)

        if not dados:
            break

        buffer += dados.decode("utf-8", errors="replace")

        while buffer.strip():
            buffer = buffer.lstrip()

            try:
                evento, posicao = decodificador.raw_decode(buffer)
                buffer = buffer[posicao:]

            except json.JSONDecodeError:
                break

            nome_evento = evento.get("Event")
            conteudo = evento.get("Data", {})

            if isinstance(conteudo, str):
                try:
                    conteudo = json.loads(conteudo)
                except json.JSONDecodeError:
                    continue

            # Atualizar cronômetro
            if nome_evento == "ClockUpdatedSeconds":
                ultimo_relogio = conteudo.get("TimeSeconds", 0)

            # Detectar gols
            elif nome_evento == "GoalScored":

                jogador = conteudo.get("Scorer", {}).get("Name", "")

                if jogador:
                    assistente = conteudo.get("Assister", {}).get("Name")

                    tempo = formatar_tempo(ultimo_relogio)

                    mensagem = (
                        f"⚽ GOL DE {jogador}!\n"
                    )

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

except socket.timeout:
    print("Tempo limite de conexão ou recebimento excedido.")

except ConnectionRefusedError:
    print("Conexão recusada. Verifique se o Rocket League está em uma partida.")

except KeyboardInterrupt:
    print("\nPrograma encerrado.")

except OSError as erro:
    print("Erro de conexão:", erro)

finally:
    cliente.close()

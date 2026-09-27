import socket
import sys
import threading
from datetime import datetime

HOST_PADRAO = "10.10.10.10"
PORTA_PADRAO = 7070

# Fase 1 e proposital: credenciais em texto claro, e o proprio ponto que a
# Fase 3 vai eliminar trocando por hash + TLS.
USUARIOS = {
    "aluno": "senha123",
    "professor": "acesso2026",
}


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def enviar(conexao, texto):
    conexao.sendall((texto + "\r\n").encode("ascii"))


def receber_linha(conexao):
    # Le byte a byte ate CRLF: simples de acompanhar no Wireshark, e as
    # mensagens do protocolo SLAP sao curtas o suficiente pra isso nao pesar.
    dados = b""
    while not dados.endswith(b"\r\n"):
        pedaco = conexao.recv(1)
        if not pedaco:
            return None
        dados += pedaco
    return dados.decode("ascii", errors="replace").strip()


def atender_cliente(conexao, endereco):
    log(f"Conexao aberta por {endereco[0]}:{endereco[1]}")
    try:
        enviar(conexao, "220 slap-server pronto")

        linha = receber_linha(conexao)
        if linha is None or not linha.upper().startswith("USER "):
            enviar(conexao, "500 esperado USER <usuario>")
            return
        usuario = linha[5:].strip()
        enviar(conexao, "331 senha requerida")

        linha = receber_linha(conexao)
        if linha is None or not linha.upper().startswith("PASS "):
            enviar(conexao, "500 esperado PASS <senha>")
            return
        senha = linha[5:].strip()

        if USUARIOS.get(usuario) == senha:
            enviar(conexao, "230 login bem-sucedido")
            log(f"Login OK: usuario={usuario!r} de {endereco[0]}")
        else:
            enviar(conexao, "530 usuario ou senha invalidos")
            log(f"Login FALHOU: usuario={usuario!r} senha={senha!r} de {endereco[0]}")

        linha = receber_linha(conexao)
        if linha and linha.upper().startswith("QUIT"):
            enviar(conexao, "221 ate mais")
    except (ConnectionResetError, BrokenPipeError):
        log(f"Conexao com {endereco[0]}:{endereco[1]} encerrada abruptamente")
    finally:
        conexao.close()
        log(f"Conexao fechada com {endereco[0]}:{endereco[1]}")


def main():
    host = sys.argv[1] if len(sys.argv) > 1 else HOST_PADRAO
    porta = int(sys.argv[2]) if len(sys.argv) > 2 else PORTA_PADRAO

    servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    servidor.bind((host, porta))
    servidor.listen()
    log(f"Servidor SLAP escutando em {host}:{porta}")

    try:
        while True:
            conexao, endereco = servidor.accept()
            threading.Thread(target=atender_cliente, args=(conexao, endereco), daemon=True).start()
    except KeyboardInterrupt:
        log("Encerrando servidor")
    finally:
        servidor.close()


if __name__ == "__main__":
    main()

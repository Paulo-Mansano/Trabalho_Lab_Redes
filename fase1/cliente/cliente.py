import socket
import sys

HOST_PADRAO = "10.10.10.10"
PORTA_PADRAO = 7070


def enviar(conexao, texto):
    conexao.sendall((texto + "\r\n").encode("ascii"))


def receber_linha(conexao):
    dados = b""
    while not dados.endswith(b"\r\n"):
        pedaco = conexao.recv(1)
        if not pedaco:
            return None
        dados += pedaco
    return dados.decode("ascii", errors="replace").strip()


def main():
    host = sys.argv[1] if len(sys.argv) > 1 else HOST_PADRAO
    porta = int(sys.argv[2]) if len(sys.argv) > 2 else PORTA_PADRAO
    usuario = sys.argv[3] if len(sys.argv) > 3 else input("usuario: ")
    senha = sys.argv[4] if len(sys.argv) > 4 else input("senha: ")

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as conexao:
        conexao.connect((host, porta))
        print("<", receber_linha(conexao))

        print(">", f"USER {usuario}")
        enviar(conexao, f"USER {usuario}")
        print("<", receber_linha(conexao))

        print(">", "PASS " + "*" * len(senha))
        enviar(conexao, f"PASS {senha}")
        print("<", receber_linha(conexao))

        enviar(conexao, "QUIT")
        print("<", receber_linha(conexao))


if __name__ == "__main__":
    main()

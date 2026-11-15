"""
Cliente SLAP protegido (Fase 3).

Conecta ao servidor por TLS e VALIDA o certificado apresentado contra uma CA de
confiança (o certificado do servidor legítimo). Se o certificado não for
confiável — por exemplo, um MITM tentando se passar pelo servidor — o handshake
falha e o cliente ABORTA antes de enviar qualquer credencial. Essa validação é a
defesa contra o ataque da Fase 2 e o mecanismo de detecção do MITM.

Uso:
    python cliente_tls.py [host] [porta] [usuario] [senha] [caminho_ca]
    (padrões: localhost 7070 <pergunta> <pergunta> ../cert/servidor.crt)
"""
import os
import socket
import ssl
import sys

HOST_PADRAO = "localhost"
PORTA_PADRAO = 7070
BASE = os.path.dirname(os.path.abspath(__file__))
CA_PADRAO = os.path.join(BASE, "..", "cert", "servidor.crt")


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
    ca = sys.argv[5] if len(sys.argv) > 5 else CA_PADRAO

    if not os.path.exists(ca):
        print(f"CA de confianca nao encontrada: {ca}")
        print("Gere os certificados com: bash ../cert/gerar_cert.sh")
        sys.exit(1)

    # Contexto que exige certificado valido E confiavel (assinado pela CA dada)
    # e que o nome do servidor bata com o do certificado (check_hostname).
    contexto = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile=ca)
    contexto.check_hostname = True
    contexto.verify_mode = ssl.CERT_REQUIRED

    bruto = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    bruto.connect((host, porta))
    try:
        # O handshake TLS valida o certificado AQUI, antes de qualquer dado.
        conexao = contexto.wrap_socket(bruto, server_hostname=host)
    except ssl.SSLCertVerificationError as erro:
        print("!!! ATAQUE DETECTADO / CONEXAO ABORTADA !!!")
        print(f"    O certificado do servidor NAO e confiavel: {erro.verify_message}")
        print("    Possivel man-in-the-middle se passando pelo servidor.")
        print("    Nenhuma credencial foi enviada.")
        bruto.close()
        sys.exit(2)
    except ssl.SSLError as erro:
        print(f"!!! Falha no handshake TLS: {erro}")
        bruto.close()
        sys.exit(2)

    cifra, versao, _ = conexao.cipher()
    print(f"[TLS estabelecido: {versao} / {cifra} - certificado do servidor validado]")

    with conexao:
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

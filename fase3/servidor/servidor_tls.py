"""
Servidor SLAP protegido (Fase 3) — defesa contra sniffing e MITM.

Diferenças em relação à Fase 1:
  1. CONFIDENCIALIDADE + INTEGRIDADE: o socket TCP é encapsulado em TLS
     (módulo ssl). O conteúdo trafega cifrado — o sniffer da Fase 1 passa a ver
     apenas bytes ilegíveis, e o proxy da Fase 2 não consegue ler nem alterar.
  2. AUTENTICAÇÃO DO SERVIDOR: o servidor apresenta um certificado. O cliente
     valida esse certificado; um MITM que tente se passar pelo servidor é
     detectado (o cliente recusa o certificado não confiável).
  3. SENHAS COM HASH: as credenciais são guardadas como PBKDF2-HMAC-SHA256
     (salt + hash), nunca em texto claro.

Uso:
    python servidor_tls.py [host] [porta] [caminho_cert] [caminho_chave]
    (padrões: 0.0.0.0  7070  ../cert/servidor.crt  ../cert/servidor.key)
"""
import hashlib
import hmac
import os
import socket
import ssl
import sys
import threading
from datetime import datetime

HOST_PADRAO = "0.0.0.0"
PORTA_PADRAO = 7070
BASE = os.path.dirname(os.path.abspath(__file__))
CERT_PADRAO = os.path.join(BASE, "..", "cert", "servidor.crt")
CHAVE_PADRAO = os.path.join(BASE, "..", "cert", "servidor.key")

PBKDF2_ITERS = 200_000

# Credenciais guardadas como (salt_hex, hash_hex) — PBKDF2-HMAC-SHA256.
# Nunca em texto claro. Mesmos usuários/senhas das fases anteriores
# (aluno/senha123, professor/acesso2026), mas aqui só o hash é armazenado.
USUARIOS = {
    "aluno": ("3866eb69424a95b13ed2e695897f064b", "9078d99ac336b72e16b0ab4398bed9ffa391e050098c66eafd953e4e1d589f9c"),
    "professor": ("531568cbdb9d3aba525de38018eaa371", "3f32645115f1ee2bbbd7a4e7e2f7e13c6a2706d80806593117e6cd767e4f9ac8"),
}


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def senha_confere(usuario, senha):
    registro = USUARIOS.get(usuario)
    if registro is None:
        return False
    salt_hex, hash_hex = registro
    calculado = hashlib.pbkdf2_hmac("sha256", senha.encode(), bytes.fromhex(salt_hex), PBKDF2_ITERS)
    # compare_digest evita timing attack na comparação do hash.
    return hmac.compare_digest(calculado, bytes.fromhex(hash_hex))


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


def atender_cliente(conexao, endereco):
    log(f"Conexao TLS aberta por {endereco[0]}:{endereco[1]}")
    try:
        enviar(conexao, "220 slap-server pronto (TLS)")

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

        if senha_confere(usuario, senha):
            enviar(conexao, "230 login bem-sucedido")
            log(f"Login OK: usuario={usuario!r} de {endereco[0]}")
        else:
            enviar(conexao, "530 usuario ou senha invalidos")
            # Nao logamos a senha: diferente da Fase 1, aqui nao expomos segredo.
            log(f"Login FALHOU: usuario={usuario!r} de {endereco[0]}")

        linha = receber_linha(conexao)
        if linha and linha.upper().startswith("QUIT"):
            enviar(conexao, "221 ate mais")
    except (ConnectionResetError, BrokenPipeError, ssl.SSLError) as erro:
        log(f"Conexao com {endereco[0]}:{endereco[1]} encerrada: {erro}")
    finally:
        try:
            conexao.close()
        except OSError:
            pass
        log(f"Conexao fechada com {endereco[0]}:{endereco[1]}")


def main():
    host = sys.argv[1] if len(sys.argv) > 1 else HOST_PADRAO
    porta = int(sys.argv[2]) if len(sys.argv) > 2 else PORTA_PADRAO
    cert = sys.argv[3] if len(sys.argv) > 3 else CERT_PADRAO
    chave = sys.argv[4] if len(sys.argv) > 4 else CHAVE_PADRAO

    if not (os.path.exists(cert) and os.path.exists(chave)):
        print(f"Certificado/chave nao encontrados:\n  {cert}\n  {chave}")
        print("Gere-os antes com: bash ../cert/gerar_cert.sh")
        sys.exit(1)

    contexto = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    contexto.load_cert_chain(certfile=cert, keyfile=chave)

    servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    servidor.bind((host, porta))
    servidor.listen()
    log(f"Servidor SLAP/TLS escutando em {host}:{porta} (cert: {os.path.basename(cert)})")

    try:
        while True:
            bruto, endereco = servidor.accept()
            try:
                # Handshake TLS antes de tratar o protocolo.
                conexao = contexto.wrap_socket(bruto, server_side=True)
            except ssl.SSLError as erro:
                # Cliente sem TLS (ex.: sniffer/cliente antigo em texto claro) falha aqui.
                log(f"Handshake TLS falhou com {endereco[0]}:{endereco[1]}: {erro}")
                bruto.close()
                continue
            threading.Thread(target=atender_cliente, args=(conexao, endereco), daemon=True).start()
    except KeyboardInterrupt:
        log("Encerrando servidor")
    finally:
        servidor.close()


if __name__ == "__main__":
    main()

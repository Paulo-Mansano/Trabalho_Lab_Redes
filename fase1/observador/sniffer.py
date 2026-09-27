import ctypes
import os
import socket
import struct
import sys
from datetime import datetime

PORTA_ALVO = 7070


def eh_administrador():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def montar_socket_raw(ip_interface):
    s = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_IP)
    s.bind((ip_interface, 0))
    s.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)
    s.ioctl(socket.SIO_RCVALL, socket.RCVALL_ON)
    return s


def interpretar_ip(pacote):
    cabecalho = pacote[:20]
    versao_ihl, _, _, _, _, ttl, protocolo, _, origem, destino = struct.unpack(
        "!BBHHHBBH4s4s", cabecalho
    )
    tamanho_cabecalho = (versao_ihl & 0x0F) * 4
    return {
        "protocolo": protocolo,
        "origem": socket.inet_ntoa(origem),
        "destino": socket.inet_ntoa(destino),
        "tamanho_cabecalho": tamanho_cabecalho,
    }


def interpretar_tcp(pacote, offset):
    porta_origem, porta_destino, _, _, offset_flags = struct.unpack(
        "!HHIIH", pacote[offset:offset + 14]
    )
    tamanho_cabecalho_tcp = ((offset_flags >> 12) & 0xF) * 4
    return porta_origem, porta_destino, offset + tamanho_cabecalho_tcp


def formatar_payload(bruto):
    texto = bruto.decode("ascii", errors="replace").strip()
    if not texto:
        return None
    if "USER " in texto.upper() or "PASS " in texto.upper():
        return f"*** CREDENCIAL CAPTURADA *** {texto!r}"
    return repr(texto)


def main():
    if os.name != "nt":
        print("Este sniffer usa SIO_RCVALL, disponivel apenas no Windows.")
        sys.exit(1)

    if len(sys.argv) < 2:
        print("uso: python sniffer.py <ip-da-interface-do-observador>")
        sys.exit(1)
    ip_interface = sys.argv[1]

    if not eh_administrador():
        print("Execute como Administrador: SIO_RCVALL exige privilegio elevado no Windows.")
        sys.exit(1)

    try:
        s = montar_socket_raw(ip_interface)
    except OSError as erro:
        print(f"Nao foi possivel abrir o socket raw em {ip_interface}: {erro}")
        print("Confira se o IP pertence a uma interface ativa desta VM.")
        sys.exit(1)

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Sniffer ativo em {ip_interface}, "
          f"observando a porta {PORTA_ALVO}...")

    contador = 0
    try:
        while True:
            pacote, _ = s.recvfrom(65535)
            ip = interpretar_ip(pacote)
            if ip["protocolo"] != 6:  # 6 = TCP
                continue

            porta_origem, porta_destino, offset_payload = interpretar_tcp(
                pacote, ip["tamanho_cabecalho"]
            )
            if PORTA_ALVO not in (porta_origem, porta_destino):
                continue

            payload = formatar_payload(pacote[offset_payload:])
            if not payload:
                continue

            contador += 1
            hora = datetime.now().strftime("%H:%M:%S")
            print(f"[{contador:04d} {hora}] {ip['origem']}:{porta_origem} -> "
                  f"{ip['destino']}:{porta_destino}  {payload}")
    except KeyboardInterrupt:
        print("Encerrando sniffer")
    finally:
        s.ioctl(socket.SIO_RCVALL, socket.RCVALL_OFF)
        s.close()


if __name__ == "__main__":
    main()

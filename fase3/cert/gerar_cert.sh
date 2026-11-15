#!/usr/bin/env bash
# Gera os certificados da Fase 3 (defesa com TLS).
#
# Cria DOIS pares de chave/certificado auto-assinados:
#   servidor.key / servidor.crt  -> o servidor LEGITIMO (confiavel pelo cliente)
#   atacante.key / atacante.crt  -> um certificado do ATACANTE (NAO confiavel),
#                                   usado para demonstrar a DETECCAO do MITM.
#
# Os SAN (Subject Alternative Names) cobrem localhost e os IPs do laboratorio,
# para funcionar tanto na demo em um so computador quanto nas VMs.
# Se o servidor usar outro IP, adicione-o na variavel SAN abaixo e gere de novo.
#
# Uso (no Terminal, dentro de fase3/cert/):
#     bash gerar_cert.sh
set -eu

# Evita que o Git-bash do Windows converta "/CN=..." em caminho de arquivo.
# Inofensivo no macOS/Linux.
export MSYS_NO_PATHCONV=1
export MSYS2_ARG_CONV_EXCL="*"

cd "$(dirname "$0")"
SAN="subjectAltName=DNS:slap-server,DNS:localhost,IP:127.0.0.1,IP:10.10.10.10"

echo "== Gerando certificado do SERVIDOR LEGITIMO =="
openssl req -x509 -newkey rsa:2048 -nodes \
    -keyout servidor.key -out servidor.crt -days 365 \
    -subj "/CN=slap-server" -addext "$SAN"

echo
echo "== Gerando certificado do ATACANTE (para a demo de deteccao) =="
openssl req -x509 -newkey rsa:2048 -nodes \
    -keyout atacante.key -out atacante.crt -days 365 \
    -subj "/CN=slap-server" -addext "$SAN"

echo
echo "Pronto. Arquivos gerados em $(pwd):"
ls -1 servidor.key servidor.crt atacante.key atacante.crt
echo
echo "O cliente confia APENAS em servidor.crt (passado como CA)."
echo "atacante.crt tem o mesmo nome, mas chave diferente -> o cliente o rejeita."

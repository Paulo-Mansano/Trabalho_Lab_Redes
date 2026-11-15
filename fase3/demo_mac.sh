#!/usr/bin/env bash
# Demonstracao automatica da Fase 3 (defesa com TLS), em localhost, SEM VMs.
# Mostra, em sequencia:
#   1. Login protegido por TLS funcionando (confidencialidade + senha com hash).
#   2. Deteccao de MITM: um "servidor" com certificado de atacante e RECUSADO
#      pelo cliente antes de qualquer credencial ser enviada.
#
# Uso (no Terminal, na raiz do repositorio):
#     bash fase3/demo_mac.sh         # se o Mac so tiver "python": PY=python bash fase3/demo_mac.sh
set -u

cd "$(dirname "$0")"                 # pasta fase3/
PY="${PY:-python3}"

if ! $PY --version >/dev/null 2>&1; then
    echo "ERRO: 'python3' nao encontrado. Instale em https://www.python.org/downloads/"
    exit 1
fi

# Garante que os certificados existem.
if [ ! -f cert/servidor.crt ] || [ ! -f cert/atacante.crt ]; then
    echo "== Gerando certificados (primeira execucao) =="
    bash cert/gerar_cert.sh >/dev/null 2>&1
fi

LOG=$(mktemp)
SRV=""
parar(){ [ -n "$SRV" ] && kill "$SRV" 2>/dev/null; rm -f "$LOG"; }
trap parar EXIT

echo
echo "############################################################"
echo "# DEMO 1 - Canal protegido por TLS (defesa funcionando)    #"
echo "############################################################"
$PY -u servidor/servidor_tls.py 127.0.0.1 7070 cert/servidor.crt cert/servidor.key >"$LOG" 2>&1 & SRV=$!
sleep 1.5
$PY cliente/cliente_tls.py localhost 7070 aluno senha123 cert/servidor.crt
echo
echo "-- log do servidor --"; grep -E "Login|escutando" "$LOG"
kill "$SRV" 2>/dev/null; SRV=""; sleep 0.5

echo
echo "############################################################"
echo "# DEMO 2 - MITM detectado (servidor com cert de atacante)  #"
echo "############################################################"
echo "Um atacante se passa pelo servidor, apresentando SEU proprio certificado."
$PY -u servidor/servidor_tls.py 127.0.0.1 7070 cert/atacante.crt cert/atacante.key >"$LOG" 2>&1 & SRV=$!
sleep 1.5
$PY cliente/cliente_tls.py localhost 7070 aluno senha123 cert/servidor.crt || true
kill "$SRV" 2>/dev/null; SRV=""

echo
echo "############################################################"
echo "# RESUMO                                                   #"
echo "# 1) Com o certificado certo: login TLS funciona.          #"
echo "# 2) Com certificado de atacante: cliente ABORTA antes de  #"
echo "#    enviar a senha -> MITM detectado.                     #"
echo "# (A Fase 1 - sniffer - so veria bytes cifrados; prova     #"
echo "#  antes/depois no Wireshark esta no RELATORIO.)           #"
echo "############################################################"

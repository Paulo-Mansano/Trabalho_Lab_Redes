#!/usr/bin/env bash
# Auto-teste da Fase 2 no macOS (ou Linux), em localhost, SEM VMs.
# Serve para a apresentadora confirmar, ANTES da aula, que o MITM funciona na
# maquina dela. Sobe servidor + proxy + cliente automaticamente e mostra a prova.
#
# Como rodar (no Terminal do Mac, dentro da pasta do repositorio):
#     bash fase2/demo_mac.sh
set -u

cd "$(dirname "$0")/.."              # raiz do repositorio
PY="${PY:-python3}"                  # usa python3 por padrao; sobrescreva com: PY=python bash fase2/demo_mac.sh

TMP=$(mktemp -d)
SRV=""; PRX=""
cleanup(){ [ -n "$SRV" ] && kill "$SRV" 2>/dev/null; [ -n "$PRX" ] && kill "$PRX" 2>/dev/null; rm -rf "$TMP"; }
trap cleanup EXIT

echo "== Fase 2 - auto-teste (localhost, sem VMs) =="
if ! $PY --version >/dev/null 2>&1; then
    echo "ERRO: 'python3' nao encontrado. Instale o Python 3 em https://www.python.org/downloads/"
    exit 1
fi
$PY --version

# 1) servidor real em 127.0.0.1:7071
$PY -u fase1/servidor/servidor.py 127.0.0.1 7071 >"$TMP/srv.log" 2>&1 & SRV=$!
sleep 1
# 2) proxy MITM em 127.0.0.1:7070 -> encaminha para 127.0.0.1:7071, adulterando
$PY -u fase2/proxy/proxy_mitm.py 7070 127.0.0.1 7071 --modificar >"$TMP/proxy.log" 2>&1 & PRX=$!
sleep 1

echo
echo "-- CLIENTE: faz login como aluno/senha123, apontando para o PROXY --"
$PY fase1/cliente/cliente.py 127.0.0.1 7070 aluno senha123
sleep 1

echo
echo "-- PROXY: adulteracao em transito --"
grep -E "MODIFICADO|sessao 01" "$TMP/proxy.log" || cat "$TMP/proxy.log"

echo
echo "-- SERVIDOR: quem foi REALMENTE autenticado --"
grep "Login" "$TMP/srv.log" || cat "$TMP/srv.log"

echo
echo "============================================================"
echo "Se acima aparece: cliente enviou 'USER aluno' e recebeu 230,"
echo "mas o servidor registrou \"Login OK: usuario='professor'\","
echo "entao o MITM esta funcionando nesta maquina. Pronto para a aula."
echo "============================================================"

# Fase 1 — Aplicação alvo e sniffer passivo

Protocolo próprio de login em texto claro (**SLAP** — Simple Login Access
Protocol), inspirado deliberadamente no fluxo de autenticação do FTP (códigos
`220`/`331`/`230`/`530`/`221`), para que a captura fique legível e reconhecível
no Wireshark. Credenciais viajam em texto claro por design — é exatamente essa
fragilidade que este entregável demonstra, e que a Fase 3 vai eliminar.

## Protocolo SLAP

Texto ASCII, uma linha por mensagem, terminada em `\r\n`. Porta padrão: `7070/tcp`.

```
Servidor                          Cliente
   |--- 220 slap-server pronto ---->|
   |<-------- USER <usuario> -------|
   |--- 331 senha requerida ------->|
   |<-------- PASS <senha> ---------|
   |--- 230 login bem-sucedido ---->|   (ou 530 usuario ou senha invalidos)
   |<-------- QUIT ------------------|
   |--- 221 ate mais --------------->|
```

Usuários válidos (hardcoded em `servidor/servidor.py`, de propósito em texto
claro nesta fase): `aluno:senha123`, `professor:acesso2026`.

## Estrutura

```
fase1/
  servidor/servidor.py     # serviço alvo (TCP, multi-thread)
  cliente/cliente.py       # cliente SLAP
  observador/sniffer.py    # interceptador passivo (socket raw, Windows)
```

## Topologia

Um único PC Windows físico, hospedando 3 VMs no VirtualBox em uma rede
interna isolada (sem saída para a internet), com modo promíscuo habilitado
para que a VM-observador enxergue o tráfego entre as outras duas.

```
                 Rede Interna VirtualBox "labredes" (promíscuo: Permitir Tudo)
                 ┌─────────────────────────────────────────────────┐
 VM-cliente      │                                                 │      VM-servidor
 10.10.10.20 ────┼────────────────── switch virtual ────────────────┼──── 10.10.10.10:7070
                 │                        │                        │
                 │                 VM-observador                   │
                 │                 10.10.10.30                     │
                 └─────────────────────────────────────────────────┘
```

## Configuração das VMs (VirtualBox)

1. Crie 3 VMs (Windows, a versão que tiverem disponível é suficiente — não
   precisa de placa gráfica dedicada nem de muita RAM, 2 GB bastam).
2. Em cada VM: **Configurações → Rede → Adaptador 1**, mude para **Rede
   Interna**, nome `labredes` (mesmo nome nas 3 VMs).
3. Ainda no adaptador, expanda **Avançado → Modo Promíscuo** e selecione
   **Permitir Tudo** — nas 3 VMs (o observador precisa disso pra receber, mas
   deixar nas 3 evita esquecimento e não tem custo).
4. Dentro de cada VM Windows, configure IP fixo na interface (Painel de
   Controle → Rede → Propriedades do adaptador → IPv4):
   - VM-servidor: `10.10.10.10`, máscara `255.255.255.0`
   - VM-cliente: `10.10.10.20`, máscara `255.255.255.0`
   - VM-observador: `10.10.10.30`, máscara `255.255.255.0`
   - Gateway/DNS: deixe em branco (rede interna, sem saída — isso é proposital).
5. Teste conectividade entre as VMs com `ping` antes de rodar qualquer coisa.

## Como rodar

**VM-servidor:**
```
python servidor\servidor.py
```
(usa os padrões `10.10.10.10:7070`; para testar localmente antes de montar as
VMs, rode `python servidor\servidor.py 127.0.0.1 7070`)

**VM-observador** (PowerShell/CMD como Administrador — `SIO_RCVALL` exige
privilégio elevado no Windows):
```
python observador\sniffer.py 10.10.10.30
```

**VM-cliente:**
```
python cliente\cliente.py 10.10.10.10 7070 aluno senha123
```
(omita usuário/senha para digitar interativamente)

## Evidência com Wireshark

Capture na VM-observador (ou na VM-servidor, para comparar) com o filtro:
```
tcp.port == 7070
```
Clique com o botão direito em qualquer pacote da conversa → **Follow → TCP
Stream** para visualizar a troca completa em texto claro, exatamente como o
sniffer próprio exibe. Anote os números dos pacotes de `USER` e `PASS` para o
relatório — é a evidência pedida na entrega ("com evidência de captura,
número dos pacotes").

## Aviso de uso

Ferramenta de prova de conceito para uso exclusivo dentro da rede interna
isolada descrita acima. Não deve ser executada fora deste ambiente de
laboratório.

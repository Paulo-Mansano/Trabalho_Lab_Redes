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

Caminho mais rápido: não instale o Windows 3 vezes. Baixe a VM gratuita
"Windows 11 dev environment" da Microsoft (pronta em formato VirtualBox,
avaliação renovável), importe uma vez, configure (rede + Python) e depois
**Máquina → Clonar → Clonagem Completa** (marcando "reinicializar MAC") duas
vezes para gerar as outras duas VMs, em vez de rodar o instalador do zero.

1. Nomeie as 3 VMs como `VM-servidor`, `VM-cliente`, `VM-observador` (ou ajuste
   os nomes no topo de `infra/configurar_rede_vms.ps1`).
2. Com as 3 VMs **desligadas**, rode no PowerShell do host Windows:
   ```
   fase1\infra\configurar_rede_vms.ps1
   ```
   Isso aplica nas 3 de uma vez: adaptador 1 em **Rede Interna** `labredes` +
   **Modo Promíscuo: Permitir Tudo** (via `VBoxManage`, sem precisar abrir a
   tela de Configurações de cada VM na mão).
3. Dentro de cada VM Windows já ligada, configure o IP fixo (o script imprime
   o comando `netsh` de cada uma ao final; ou faça manualmente em Painel de
   Controle → Rede → Propriedades do adaptador → IPv4):
   - VM-servidor: `10.10.10.10`, máscara `255.255.255.0`
   - VM-cliente: `10.10.10.20`, máscara `255.255.255.0`
   - VM-observador: `10.10.10.30`, máscara `255.255.255.0`
   - Gateway/DNS: deixe em branco (rede interna, sem saída — isso é proposital).
4. **Libere a porta 7070 no firewall da VM-servidor.** Por padrão o Firewall do
   Windows bloqueia conexões de entrada: sem isso o cliente não conecta e parece
   "bug no código" — é o erro nº 1 ao montar o laboratório. Na VM-servidor, no
   PowerShell como Administrador:
   ```
   netsh advfirewall firewall add rule name="SLAP 7070" dir=in action=allow protocol=TCP localport=7070
   ```
   (Como a rede é interna e isolada, sem saída, alternativamente pode-se desativar
   o Firewall do Windows nessa interface.)
5. Teste conectividade entre as VMs com `ping` antes de rodar qualquer coisa.
   Se as VMs estiverem muito lentas, desligue a "Integridade de memória"
   (Segurança do Windows → Segurança do dispositivo → Isolamento de núcleo): VBS
   /Hyper-V conflita com o VirtualBox e o derruba para o modo lento.

## Como rodar

**VM-servidor:**
```
python servidor\servidor.py
```
(usa os padrões `10.10.10.10:7070`; para testar localmente antes de montar as
VMs, rode `python servidor\servidor.py 127.0.0.1 7070`)

**VM-observador** (PowerShell como Administrador — `SIO_RCVALL` exige
privilégio elevado no Windows):
```
python observador\sniffer.py 10.10.10.30
```

> ⚠️ **Essencial:** desligue o Firewall do Windows na VM-observador antes de
> rodar o sniffer. Com ele ligado, o Defender descarta os pacotes capturados
> antes de chegarem ao socket raw e o sniffer captura **zero** (sintoma clássico:
> "Sniffer ativo" mas nenhuma linha aparece). Como a rede é isolada, é seguro:
> ```
> netsh advfirewall set allprofiles state off
> ```

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

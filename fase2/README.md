# Fase 2 — Interceptação ativa (Proxy Man-in-the-Middle)

Proxy MITM concorrente que se posiciona entre cliente e servidor do protocolo
**SLAP** (Fase 1), faz o *relay* das mensagens nos dois sentidos e é capaz de
**ler e alterar** o conteúdo em trânsito. Demonstra a quebra de **integridade** e
de **autenticação**: sem proteção de integridade, o conteúdo pode ser adulterado
sem que cliente ou servidor percebam.

O servidor e o cliente são **os mesmos da Fase 1** (`../fase1/`), sem alteração —
o ataque é viabilizado apenas **redirecionando o cliente para o proxy**.

## Topologia de redirecionamento

Na Fase 1 o cliente falava direto com o servidor. Na Fase 2, o cliente é
**configurado para apontar ao proxy** (que roda na VM-observador, agora no papel
de atacante ativo), e o proxy repassa para o servidor real:

```
   Fase 1 (direto):     cliente ───────────────► servidor
                        .20                       .10:7070

   Fase 2 (MITM):       cliente ──► PROXY MITM ──► servidor
                        .20         .30:7070       .10:7070
                                    (lê e altera)
```

| VM | IP | Papel na Fase 2 |
|---|---|---|
| VM-servidor | `10.10.10.10:7070` | Servidor SLAP real (igual à Fase 1) |
| VM-observador | `10.10.10.30:7070` | **Proxy MITM** (`proxy_mitm.py`) |
| VM-cliente | `10.10.10.20` | Cliente apontado para **o proxy** (`.30`), não para o servidor |

> O redirecionamento é feito "por configuração do próprio serviço", como pede o
> enunciado: basta o cliente usar o IP do proxy como destino. Nenhuma linha do
> cliente ou do servidor muda.

## Estrutura

```
fase2/
  proxy/proxy_mitm.py     # proxy MITM concorrente (lê e altera o tráfego)
  README.md               # este arquivo
  CONCORRENCIA.md         # modelo de concorrência e regiões críticas
  RELATORIO.md            # relatório da fase (demonstração + evidências)
```

## Como rodar

**1. VM-servidor** — suba o servidor da Fase 1 (inalterado):
```
cd ..\fase1
python servidor\servidor.py
```

**2. VM-observador** — suba o proxy MITM. Dois modos:

- **Modo observação** (relay transparente — só lê/registra o tráfego):
  ```
  python proxy\proxy_mitm.py 7070 10.10.10.10 7070
  ```
- **Modo modificação** (adultera o tráfego conforme as regras):
  ```
  python proxy\proxy_mitm.py 7070 10.10.10.10 7070 --modificar
  ```

Argumentos: `porta_escuta  host_servidor  porta_servidor  [--modificar]`
(padrões: `7070 10.10.10.10 7070`).

**3. VM-cliente** — aponte o cliente **para o proxy** (`.30`), não para o servidor:
```
cd ..\fase1
python cliente\cliente.py 10.10.10.30 7070 aluno senha123
```

## Demonstração sugerida (arco do ataque)

1. **MITM transparente:** suba o proxy em modo observação e rode o cliente. O
   login funciona normalmente — provando que o proxy está no caminho e lê tudo
   (usuário e senha aparecem no log do proxy), sem o cliente perceber.
2. **Adulteração (troca de identidade):** reinicie o proxy com `--modificar` e
   rode o cliente de novo com `aluno`/`senha123`. O proxy reescreve a credencial
   em trânsito para `professor`/`acesso2026`:
   - O **cliente** envia `USER aluno` e recebe `230 login bem-sucedido` → acredita
     estar logado como **aluno**.
   - O **servidor** registra `Login OK: usuario='professor'` → autenticou
     **professor**.
   - Nenhum dos dois detecta a adulteração: quebra de integridade e autenticação.
3. **Concorrência:** com o proxy no ar, rode **dois ou mais clientes ao mesmo
   tempo** (de dois terminais). O proxy atende as sessões em paralelo, cada uma
   com seu `sessao NN` no log, sem uma interferir na outra.

As regras de adulteração ficam no topo de `proxy/proxy_mitm.py`
(`REGRAS_C2S` / `REGRAS_S2C`) e são fáceis de trocar — por exemplo, há uma regra
alternativa comentada que forja a resposta do servidor (`530` → `230`), fazendo o
cliente acreditar em um login que o servidor recusou.

## Rodando no macOS, sem VMs (para a apresentação)

O proxy, o servidor e o cliente são **Python puro multiplataforma** — rodam
nativamente no macOS. Como a Fase 2 trata do proxy MITM (e não do sniffer de
socket raw, que é o único componente preso ao Windows e pertence à Fase 1), a
demonstração pode ser feita **em um único Mac, via `localhost`**, sem VirtualBox e
sem rede isolada. Três papéis, três abas do Terminal.

**Pré-requisito:** Python 3 instalado (`python3 --version`). Se faltar, instale em
<https://www.python.org/downloads/>. Baixe o repositório (`git clone` ou o ZIP do
GitHub) e abra o Terminal na pasta dele.

**Autoteste (faça isto ANTES da aula, para garantir que funciona no Mac):**
```
bash fase2/demo_mac.sh
```
Ele sobe tudo sozinho e, no fim, confirma se o MITM funcionou. Se o Mac só tiver
o comando `python` (sem o `3`), rode: `PY=python bash fase2/demo_mac.sh`.

**Demo ao vivo (3 abas do Terminal, na raiz do repositório):**

| Aba | Comando | Papel |
|---|---|---|
| 1 — Servidor | `python3 fase1/servidor/servidor.py 127.0.0.1 7071` | servidor real |
| 2 — Proxy | `python3 fase2/proxy/proxy_mitm.py 7070 127.0.0.1 7071 --modificar` | MITM |
| 3 — Cliente | `python3 fase1/cliente/cliente.py 127.0.0.1 7070 aluno senha123` | vítima |

> As portas em `localhost` substituem os IPs das VMs: o **proxy** escuta em `7070`
> (o endereço que a vítima usa) e encaminha para o **servidor** em `7071`. A
> narrativa do ataque é idêntica à das VMs — mostre que o cliente envia
> `USER aluno` e recebe `230`, mas o servidor autentica `professor`.
> Para **concorrência**, abra uma 4ª aba e rode outro cliente ao mesmo tempo.

> Se o macOS perguntar "deseja permitir conexões de entrada?" para o Python na
> primeira execução, clique em **Permitir** (é só o firewall local).

## Observações

- Toda a comunicação usa **sockets diretamente** (sem frameworks que escondam o
  socket), conforme o requisito.
- O modelo de concorrência e as regiões críticas estão detalhados em
  `CONCORRENCIA.md`.
- Ambiente: a mesma rede interna isolada `labredes` da Fase 1 (ver
  `../fase1/README.md` para a montagem das VMs). Lembre de liberar/na dúvida
  desligar o firewall do Windows na VM que roda o proxy, para a porta de escuta
  aceitar conexões.

# Relatório — Fase 2: Interceptação Ativa (Man-in-the-Middle)

**Disciplina:** Laboratório de Redes de Computadores — PUCRS
**Trabalho:** Interceptação e Defesa de um Protocolo de Aplicação
**Fase:** 2 — Proxy MITM concorrente (T2)

> **[PREENCHER — identificação do grupo]**
> - **Integrantes:** [nome 1], [nome 2], [nome 3]
> - **Data da entrega:** [__/__/2026]

---

## 1. Objetivo

Demonstrar a **quebra de integridade e de autenticação** de um protocolo de
aplicação sem proteção. Um proxy **man-in-the-middle** se posiciona entre cliente
e servidor, repassa as mensagens nos dois sentidos e **altera o conteúdo em
trânsito** sem que nenhuma das pontas detecte, atendendo múltiplas sessões
simultâneas.

## 2. Topologia de redirecionamento

O cliente é **configurado para apontar ao proxy** (na VM-observador), que repassa
ao servidor real. Cliente e servidor são os mesmos da Fase 1, sem alteração.

```
   Fase 1 (direto):     cliente ───────────────► servidor
                        .20                       .10:7070

   Fase 2 (MITM):       cliente ──► PROXY MITM ──► servidor
                        .20         .30:7070       .10:7070
                                    (lê e altera)
```

| VM | IP | Papel |
|---|---|---|
| VM-servidor | `10.10.10.10:7070` | Servidor SLAP real |
| VM-observador | `10.10.10.30:7070` | Proxy MITM (`proxy_mitm.py`) |
| VM-cliente | `10.10.10.20` | Cliente apontado para o proxy (`.30`) |

## 3. Arquitetura do proxy

- **Sockets diretos**, sem frameworks que escondam o socket.
- **Concorrente:** uma thread de sessão por cliente; duas threads de relay por
  sessão (sentido cliente→servidor e servidor→cliente). Detalhes e regiões
  críticas em `CONCORRENCIA.md`.
- **Leitura e modificação:** o tráfego é processado linha a linha (SLAP termina
  cada mensagem em `\r\n`); regras de substituição (`REGRAS_C2S`/`REGRAS_S2C`)
  podem reescrever qualquer mensagem em trânsito.
- **Dois modos:** *observação* (relay transparente, só lê) e *modificação*
  (`--modificar`, adultera o tráfego).

## 4. Demonstração 1 — MITM transparente (leitura)

Proxy em modo observação; o login funciona normalmente, provando que o proxy está
no caminho e **lê** usuário e senha sem o cliente perceber.

```
[..][sessao 01][+] cliente ... conectado; abrindo servidor 10.10.10.10:7070
[..][sessao 01][S->C] '220 slap-server pronto'
[..][sessao 01][C->S] CREDENCIAL LIDA  'USER aluno'
[..][sessao 01][S->C] '331 senha requerida'
[..][sessao 01][C->S] CREDENCIAL LIDA  'PASS senha123'
[..][sessao 01][S->C] '230 login bem-sucedido'
```

> **[TAREFA DO GRUPO — print]** Print do proxy em modo observação rodando na
> VM-observador. `![MITM transparente](evidencias/print_mitm_observacao.png)`

## 5. Demonstração 2 — Adulteração (quebra de integridade/autenticação)

Proxy com `--modificar`. O cliente faz login como `aluno`/`senha123`, mas o proxy
**reescreve a credencial em trânsito** para `professor`/`acesso2026`.

**Log do proxy (adulteração em trânsito):**
```
[..][sessao 01][C->S] *** MODIFICADO *** b'USER aluno\r\n' -> b'USER professor\r\n'
[..][sessao 01][C->S] *** MODIFICADO *** b'PASS senha123\r\n' -> b'PASS acesso2026\r\n'
[..][sessao 01][S->C] '230 login bem-sucedido'
```

**O que cada ponta "enxerga" — nenhuma detecta a troca:**

| Ponta | Observa | Conclui |
|---|---|---|
| **Cliente** | enviou `USER aluno`; recebeu `230 login bem-sucedido` | "estou logado como **aluno**" |
| **Servidor** | recebeu `USER professor` + senha válida | `Login OK: usuario='professor'` |

Saídas reais capturadas:
```
# CLIENTE (acredita ser aluno)
> USER aluno
< 230 login bem-sucedido

# SERVIDOR (autenticou professor)
[..] Login OK: usuario='professor' de 10.10.10.20
```

A **identidade da sessão foi trocada** sem conhecimento de cliente ou servidor:
como o protocolo não tem proteção de integridade nem autenticação mútua, a
adulteração é aceita como legítima pelas duas pontas.

> **[TAREFA DO GRUPO — prints]**
> - Terminal do **cliente** mostrando `USER aluno` + `230`.
>   `![Cliente enganado](evidencias/print_cliente.png)`
> - Terminal do **servidor** mostrando `Login OK: usuario='professor'`.
>   `![Servidor adulterado](evidencias/print_servidor.png)`
> - Terminal do **proxy** com as linhas `*** MODIFICADO ***`.
>   `![Proxy adulterando](evidencias/print_proxy_modificando.png)`

> **[OPCIONAL — evidência com Wireshark]**
> Capturar na VM-observador (ou servidor) com filtro `tcp.port == 7070` e mostrar,
> no trecho servidor↔proxy, que o pacote que chega ao servidor contém
> `USER professor` — enquanto o cliente nunca enviou isso. Anexar o `.pcapng` e o
> número do pacote em `evidencias/`.

## 6. Demonstração 3 — Concorrência

Com o proxy no ar, dois (ou mais) clientes conectam ao mesmo tempo. O proxy
atende as sessões em paralelo, cada uma identificada por `sessao NN`, sem
interferência entre elas:

```
[..][sessao 01][+] cliente ... conectado
[..][sessao 02][+] cliente ... conectado      ← segunda sessão inicia antes de a 1ª terminar
[..][sessao 01][C->S] CREDENCIAL LIDA  'USER aluno'
[..][sessao 02][C->S] CREDENCIAL LIDA  'USER professor'
[..][sessao 01][-] sessao encerrada
[..][sessao 02][-] sessao encerrada
```

O modelo de threads e a proteção das regiões críticas (contador de sessões e
saída de log) estão descritos em `CONCORRENCIA.md`.

> **[TAREFA DO GRUPO — print]** Print do log do proxy com duas sessões
> simultâneas. `![Concorrência](evidencias/print_concorrencia.png)`

## 7. Análise

Sem **integridade** (garantia de que a mensagem não foi alterada) e sem
**autenticação** das pontas, um intermediário na rede pode:

- **Ler** todo o conteúdo (como na Fase 1), agora também como parte ativa do fluxo;
- **Alterar** comandos, valores, credenciais e respostas em trânsito;
- Fazer isso de forma **transparente**: cliente e servidor completam a conversa
  normalmente e aceitam o conteúdo adulterado como legítimo.

A troca de identidade demonstrada (`aluno` → `professor`) é uma quebra combinada
de integridade (a mensagem foi alterada) e de autenticação (o servidor
autenticou uma identidade que o cliente nunca pediu). A mesma técnica permitiria
forjar respostas (ex.: transformar `530` em `230`) ou adulterar qualquer valor.

## 8. Conclusão

A Fase 2 mostrou que, sem proteção de integridade/autenticação, um proxy MITM
concorrente lê e **altera** o tráfego do SLAP sem detecção, atendendo várias
sessões ao mesmo tempo. Isso motiva a defesa da **Fase 3**: ao adotar **TLS** com
**certificado do servidor**, (a) o conteúdo passa a ser cifrado (o MITM não lê
nem altera de forma coerente) e (b) a autenticação do certificado impede o proxy
de se passar pelo servidor — a adulteração passa a ser detectada no handshake.

## Anexos

- `proxy/proxy_mitm.py` — código do proxy MITM concorrente.
- `CONCORRENCIA.md` — modelo de concorrência e regiões críticas.
- Prints e capturas em `evidencias/` (a preencher).

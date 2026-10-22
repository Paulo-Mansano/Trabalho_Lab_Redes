# Modelo de concorrência e regiões críticas — Proxy MITM

Documento exigido na entrega da Fase 2: explica como o proxy atende múltiplas
sessões simultâneas e quais são as regiões críticas (estado compartilhado entre
threads e como ele é protegido).

## 1. Modelo de concorrência

O proxy usa **threads** (não `select`/assíncrono), por clareza didática e porque
o SLAP é um protocolo de linhas simples. Há três níveis de threads:

```
Thread principal ── accept() em laço
   │  (para cada cliente que conecta)
   └──► Thread de sessão  (atender_sessao)
           │  abre a conexão ao servidor real
           ├──► Thread de relay  C->S  (repassar: cliente  → servidor)
           └──► Thread de relay  S->C  (repassar: servidor → cliente)
```

- A **thread principal** só aceita conexões e dispara uma **thread de sessão** por
  cliente. Assim, N clientes são atendidos em paralelo (requisito de
  concorrência).
- Cada **sessão** usa **duas threads de relay**, uma por sentido, porque o tráfego
  é full-duplex: o servidor pode falar (ex.: `220`) antes de o cliente responder.
  Ler os dois sentidos em paralelo evita bloqueio e trata cada direção de forma
  independente.
- Todas são `daemon=True`: não impedem o encerramento do processo com Ctrl+C.

Cada sessão é **totalmente isolada**: suas duas threads só manipulam os dois
sockets daquela sessão e um buffer local de leitura. **Não há estado
compartilhado entre sessões diferentes** — é isso que garante que uma falha em uma
sessão não afete as demais.

## 2. Regiões críticas (estado compartilhado)

Só existe estado compartilhado entre threads em **dois pontos**, ambos protegidos
por `threading.Lock`:

| Recurso compartilhado | Proteção | Por quê |
|---|---|---|
| `_contador_sessoes` (numera as sessões) | `_lock_contador` | `contador += 1` **não é atômico**: duas sessões iniciando ao mesmo tempo poderiam ler o mesmo valor e gerar IDs repetidos. |
| Saída padrão (`print` do log) | `_lock_saida` | Sem o lock, `print` de threads diferentes **intercala caracteres** na mesma linha, embaralhando o log. O lock serializa uma linha inteira por vez. |

Trecho correspondente no código:

```python
_lock_saida = threading.Lock()
_lock_contador = threading.Lock()
_contador_sessoes = 0

def proximo_id():
    global _contador_sessoes
    with _lock_contador:               # região crítica: incremento atômico
        _contador_sessoes += 1
        return _contador_sessoes

def log(sid, rotulo, msg):
    hora = datetime.now().strftime("%H:%M:%S")
    with _lock_saida:                  # região crítica: uma linha por vez
        print(f"[{hora}][sessao {sid:02d}][{rotulo}] {msg}", flush=True)
```

### Estado NÃO compartilhado (não precisa de lock)

- **Os dois sockets de cada sessão e o buffer de `ler_linha`:** são locais à
  sessão/thread. Nenhuma outra thread os acessa.
- **As regras `REGRAS_C2S` / `REGRAS_S2C`:** são definidas na inicialização e
  depois apenas **lidas** (nunca modificadas em runtime). Estrutura imutável e
  somente-leitura **não exige lock**.

## 3. Ausência de deadlock

- Existem apenas **dois locks**, e eles são **"folha"**: nenhuma thread segura um
  lock enquanto tenta adquirir o outro (não há aninhamento `with lock_a: with
  lock_b:`). Sem ordenação de locks, não há ciclo de espera → **não há deadlock**.
- Cada lock é mantido por um intervalo **mínimo** (um incremento, um `print`),
  então também não há contenção relevante de desempenho.

## 4. Encerramento e robustez

- **Desconexão:** quando um lado fecha a conexão, `ler_linha` retorna `None`, a
  thread de relay daquele sentido sai do laço e chama `fechar()`, que faz
  `shutdown` nos **dois** sockets. Isso **desbloqueia** o `recv` da thread do
  sentido oposto, que também termina. A thread de sessão então dá `join` nas duas
  e registra o fim. Não ficam threads penduradas.
- **Mensagens malformadas:** o relay **não assume** nenhuma estrutura do conteúdo
  — repassa os bytes da linha como estão (aplicando as regras de substituição, se
  houver). Dados binários ou linhas sem sentido são repassados sem quebrar a
  sessão. A decodificação para exibição usa `errors="replace"`, então nunca
  lança exceção.
- **Isolamento de falhas:** cada sessão roda em suas próprias threads, e o laço de
  relay captura `OSError`. Uma exceção, uma desconexão abrupta ou uma mensagem
  malformada em **uma** sessão não derruba o proxy nem as **outras** sessões —
  atende ao requisito de robustez da Fase 2.

## 5. Resumo

| Requisito da Fase 2 | Como é atendido |
|---|---|
| Concorrência (múltiplas sessões) | Uma thread de sessão por cliente; sessões independentes. |
| Relay nos dois sentidos | Duas threads de relay por sessão (C→S e S→C). |
| Regiões críticas controladas | Dois locks de folha: contador de sessões e saída de log. |
| Robustez a desconexão/malformado | `ler_linha` tolerante, `shutdown` cruzado, `OSError` tratado, sessões isoladas. |

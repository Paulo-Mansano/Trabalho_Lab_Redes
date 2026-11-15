# Fase 3 — Defesa e detecção (TLS)

Versão protegida do serviço SLAP. O mesmo protocolo das Fases 1 e 2, agora
encapsulado em **TLS** e com **senhas armazenadas como hash**. Resultado:

- **Confidencialidade + integridade:** o conteúdo trafega cifrado. O **sniffer
  passivo da Fase 1** passa a ver apenas bytes ilegíveis; o **proxy MITM da Fase
  2** não consegue mais ler nem alterar as mensagens.
- **Autenticação do servidor:** o servidor apresenta um **certificado**; o cliente
  o **valida**. Um MITM que tente se passar pelo servidor é **detectado** (o
  cliente recusa o certificado e aborta antes de enviar credenciais).
- **Senhas com hash:** o servidor guarda **PBKDF2-HMAC-SHA256** (salt + hash),
  nunca a senha em texto claro.

## Estrutura

```
fase3/
  cert/gerar_cert.sh       # gera os certificados (servidor legítimo + atacante)
  servidor/servidor_tls.py # servidor SLAP sobre TLS, senhas com hash
  cliente/cliente_tls.py   # cliente que VALIDA o certificado do servidor
  demo_mac.sh              # demonstração automática (localhost)
  README.md
  RELATORIO.md             # relatório final consolidado das 3 fases
```

## 1. Geração e instalação dos certificados

A defesa usa certificados X.509 (auto-assinados, suficientes para o laboratório).
Gere-os uma vez (requer `openssl`, já presente no macOS/Linux e no Git para
Windows):

```
bash cert/gerar_cert.sh
```

Isso cria em `cert/`:

| Arquivo | O que é |
|---|---|
| `servidor.crt` / `servidor.key` | certificado e chave do **servidor legítimo** |
| `atacante.crt` / `atacante.key` | certificado de um **atacante** (só para a demo de detecção) |

- **"Instalação" no servidor:** o `servidor_tls.py` carrega `servidor.crt`+`servidor.key`.
- **"Instalação" no cliente:** o `cliente_tls.py` recebe `servidor.crt` como **CA de
  confiança** — ele só aceita um servidor que apresente exatamente esse certificado.

> Os certificados **não** são versionados no Git (chave privada é segredo). Cada
> máquina gera os seus com o script. Os SAN do certificado cobrem `localhost`,
> `127.0.0.1` e `10.10.10.10`; para outro IP de servidor, edite a variável `SAN`
> em `cert/gerar_cert.sh` e gere novamente.

## 2. Como rodar

Credenciais válidas (as mesmas das fases anteriores): `aluno`/`senha123`,
`professor`/`acesso2026`.

### Caminho A — um computador só (localhost, ideal para o Mac)

**Demonstração automática (mais rápido):**
```
bash fase3/demo_mac.sh        # se o Mac só tiver "python": PY=python bash fase3/demo_mac.sh
```

**Manual, em 2 terminais (na pasta `fase3/`):**
```
# Terminal 1 — servidor protegido
python3 servidor/servidor_tls.py 127.0.0.1 7070 cert/servidor.crt cert/servidor.key

# Terminal 2 — cliente (valida o certificado)
python3 cliente/cliente_tls.py localhost 7070 aluno senha123 cert/servidor.crt
```

### Caminho B — com VMs (rede isolada)

Mesma topologia das fases anteriores. Na **VM-servidor** (`10.10.10.10`), gere os
certificados e suba o servidor; copie o `servidor.crt` para a **VM-cliente**
(`10.10.10.20`) e rode o cliente apontando o IP do servidor:

```
# VM-servidor
bash cert/gerar_cert.sh
python servidor\servidor_tls.py 10.10.10.10 7070 cert\servidor.crt cert\servidor.key

# VM-cliente  (precisa do servidor.crt copiado da VM-servidor)
python cliente\cliente_tls.py 10.10.10.10 7070 aluno senha123 servidor.crt
```

## 3. Demonstrações da defesa

| # | Cenário | Resultado esperado |
|---|---|---|
| 1 | Cliente + servidor legítimos | `TLS estabelecido` + `230 login bem-sucedido` |
| 2 | **Sniffer da Fase 1** observando | só **bytes cifrados** — nenhum `USER`/`PASS` legível |
| 3 | **Proxy MITM da Fase 2** no caminho | fica **cego** (vê só ciphertext) e **quebra** a conexão TLS |
| 4 | MITM se passando pelo servidor (cert próprio) | cliente **aborta**: `ATAQUE DETECTADO` (certificado não confiável) |

**Prova antes/depois com Wireshark:** capture a porta 7070 antes (Fases 1–2, texto
claro: `USER aluno`/`PASS senha123` legíveis) e depois (Fase 3, TLS: apenas
`Application Data` cifrado + o handshake TLS). Ver `RELATORIO.md`.

## 4. O que a defesa cobre e o que não cobre

Resumo (análise completa no `RELATORIO.md`):

- **Mitiga:** sniffing (confidencialidade), adulteração em trânsito (integridade),
  MITM se passando pelo servidor (autenticação via certificado), e replay dentro
  da sessão (TLS numera os registros).
- **Não cobre:** **metadados** ainda visíveis (IPs, portas, tamanho e horário dos
  pacotes — dá para ver *que* houve um login, não o conteúdo); confiança no
  certificado auto-assinado depende de distribuí-lo com segurança; e não há
  autenticação **do cliente** (poderia ser adicionada com certificado de cliente).

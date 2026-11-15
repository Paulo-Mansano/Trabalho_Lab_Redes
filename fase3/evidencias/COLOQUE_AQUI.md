# Evidências da Fase 3

Coloque aqui as capturas referenciadas pelo `RELATORIO.md`:

- `antes_texto_claro.png` — Wireshark ANTES (Fases 1–2): `USER aluno` / `PASS
  senha123` legíveis no payload (`tcp.port == 7070`).
- `depois_tls.png` — Wireshark DEPOIS (Fase 3): handshake `TLSv1.3` e
  `Application Data` cifrado; o conteúdo antes legível tornou-se ilegível.
- (opcional) `deteccao_mitm.png` — print do cliente com `ATAQUE DETECTADO` ao
  enfrentar um servidor com certificado de atacante.
- (opcional) `captura_tls.pcapng` — captura bruta do cenário protegido.

(Pode apagar este arquivo depois de preencher a pasta.)

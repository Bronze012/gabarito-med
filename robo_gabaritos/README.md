# 🤖 Robô de gabaritos · Missão Medicina

Este robô confere sozinho, **a cada 15 minutos**, os sites oficiais das bancas e publica tudo num arquivo público (`docs/gabaritos.json`).
O app **Missão Medicina** baixa esse arquivo e, quando sai gabarito:

- avisa você (dentro do app e, se você permitir, também no computador);
- corrige o seu cartão-resposta na hora;
- mostra as anuladas, as alteradas e as notícias de correções extraoficiais.

As **resoluções comentadas** continuam sendo feitas no chat: é só pedir *"comenta a prova da UFPR"*.

| Prova | Fonte que o robô lê | Começa a vigiar | O que ele entrega |
|---|---|---|---|
| UFPR 2027 | NC-UFPR (`Geral.pdf` provisório/definitivo + relatório de anuladas) | 01/11/2026 | gabarito preliminar (03/11, meio-dia) → definitivo (23/11, 18h), questões do caderno, línguas |
| ENEM 2026 | Inep (PDF de gabarito de cada cor) | 08/11/2026 | gabarito oficial de todas as cores, inglês/espanhol, anuladas |
| UFRGS 2027 | Coperse (`vestibular.ufrgs.br/cv2027/gabaritos/`) | 28/11/2026 | preliminar (30/11, 9h) → final (04/12, 15h), 5 línguas |
| PUCRS 2027 | página do vestibular (procura PDF de gabarito) | 05/12/2026 | melhor esforço (formato ainda desconhecido) |
| FMV Moinhos 2027 | Vunesp `FSMV2602` | 06/12/2026 | ⚠️ a Vunesp costuma bloquear robôs: provavelmente só notícias |
| PSS 3 UFSM 2027 | `ufsm.br/pss` | 10/01/2027 | melhor esforço + notícias |

Testado com as provas do ano passado (`testes/test_ano_passado.py`):
- **UFPR 2026:** anulada Q15, 7 línguas.
- **ENEM 2025:** 12 cadernos, anuladas 115/121/178.
- **UFRGS 2026:** Bio Q47 anulada, Geo Q49 D→A, Hist Q39 D→B.

---

## Como ligar (uma vez só, uns 10 minutos)

1. **Crie o repositório.** Entre em <https://github.com/new>, dê um nome (ex.: `gabaritos-medicina`) e marque **Public**. O repositório precisa ser público para o Pages ser grátis e os minutos do Actions serem ilimitados. Clique em *Create repository*.
2. **Envie os arquivos.** Na página do repositório, clique em *uploading an existing file* e arraste **todo o conteúdo** desta pasta: `robo/`, `docs/`, `testes/`, `requirements.txt`, `README.md`.
   - A pasta `.github` costuma não ir pelo arrastar, porque começa com ponto. Se ela não aparecer, crie o arquivo à mão: *Add file → Create new file*, nome `.github/workflows/gabaritos.yml`, e cole o conteúdo do arquivo de mesmo nome desta pasta.
3. **Ligue o site (Pages).** Vá em *Settings → Pages*. Em *Source* escolha **Deploy from a branch**, depois a branch **main** e a pasta **/docs**, e clique em *Save*. Em 1–2 minutos aparece o endereço `https://SEU-USUARIO.github.io/gabaritos-medicina/`.
4. **Ligue o robô (Actions).**
   1. Abra a aba *Actions* e, se aparecer o aviso, clique em *I understand… enable*.
   2. Clique em **Gabaritos automáticos → Run workflow**. Ele deve terminar verde ✅ em ~1 min.
   3. Se der erro de permissão no push: *Settings → Actions → General → Workflow permissions → Read and write*.
5. **Conecte o app.** Abra o Missão Medicina → aba **Gabaritos 2027** → card **🤖 Robô** → *Configurar* → cole `https://SEU-USUARIO.github.io/gabaritos-medicina/` → **Salvar**. Deve aparecer **🟢 Robô conectado**.
   - Opcional: clique em **🔔 Avisar no computador** e permita.

Pronto. O app confere o robô ao abrir e a cada 10 minutos, e o botão **🔄 Verificar agora** força na hora.

### Opção: abrir o app direto pelo GitHub

O arquivo `docs/index.html` é uma cópia do app: ele fica em `https://SEU-USUARIO.github.io/gabaritos-medicina/` e já encontra o robô sozinho, sem configurar nada.

> ⚠️ Seu progresso (jornada, XP, flashcards, caderno de erros) fica salvo **no navegador, separado por endereço**. Para trocar o arquivo local pelo endereço do GitHub, leve o progresso antes:
> 1. No app antigo: ⚙️ → **📥 Baixar Backup (.json)**.
> 2. No novo: ⚙️ → **📤 Restaurar Backup**.
>
> Quem continuar abrindo o arquivo do computador não precisa fazer nada: só colar o endereço do robô (passo 5).

---

## Bom saber

- **Atrasos:** o GitHub às vezes atrasa o agendamento em 5–20 minutos em horário de pico. No dia do gabarito, se tiver pressa: *Actions → Run workflow*.
- **60 dias:** o GitHub pausa robôs agendados em repositórios sem atividade por 60 dias. Este robô grava um "batimento" a cada 3 h, o que conta como atividade. Se mesmo assim pausar, aparece um botão *Enable workflow* na aba Actions.
- **Depois do gabarito final,** o robô para de baixar os PDFs daquela prova (10 dias depois), para não sobrecarregar as bancas.
- **UFPR, caderno:** o gabarito automático é o do caderno **Geral (ordem A)**. Se a capa do seu caderno for de outra ordem ou língua, confira no [Gabarito Individual do NC](https://servicos.nc.ufpr.br/GabaritoIndividual/).
- **ENEM:** escolha no app a **cor do seu caderno** de cada dia e a sua língua; a chave muda conforme isso.
- **Notícias** são de correções extraoficiais (Google Notícias, filtradas por banca). Servem de aviso, não de gabarito.
- **Rodar no seu PC (opcional):**

  ```
  pip install -r requirements.txt
  python robo/robo.py --saida docs/gabaritos.json
  ```

  Opções:
  - `--forcar` ignora as datas de início;
  - `--so ufpr27` confere uma prova só;
  - `--config testes/config_ano_passado.json` usa as provas do ano passado.
- **Teste com dados reais do ano passado:** `python testes/test_ano_passado.py` (baixa os PDFs de 2025/2026 e confere com os fatos publicados).

## Arquivos

```
robo/robo.py          robô principal (leitores nc_ufpr, inep, ufrgs_html, watch + notícias)
robo/parsers.py       leitura dos PDFs (► do NC-UFPR, tabelas do Inep, relatório de anuladas)
robo/config.json      provas, datas, endereços e filtros (edite aqui para 2028)
docs/gabaritos.json   o que o app lê (o robô atualiza)
docs/index.html       cópia do app (opcional)
.github/workflows/gabaritos.yml   agenda do robô (a cada 15 min)
testes/               teste com as provas do ano passado
```

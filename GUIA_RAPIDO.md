# Guia Rápido — ProvaLivre 🇧🇷

Olá! Este programa cria **provas diferentes para cada aluno** (mesma matéria e
dificuldade, mas questões e números diferentes) para dificultar a cola. Ele também
monta o **gabarito** automaticamente.

## Jeito mais fácil de começar
Se você usa um assistente de IA (como o Codex ou o Claude), basta abrir esta pasta com
ele e dizer:

> *"Me ajude a instalar e rodar este aplicativo, passo a passo, em português."*

O assistente já está configurado para te responder em português e te guiar.

## Passo a passo manual
1. **Instale o Python** (versão 3.10 ou mais nova) em https://www.python.org/downloads/
   — ao instalar no Windows, marque a caixinha **"Add Python to PATH"**.
2. Abra o **Prompt de Comando** (ou Terminal) dentro desta pasta e digite:
   ```
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   python app.py
   ```
3. Abra o navegador em **http://127.0.0.1:5000**

Pronto! O programa já vem com um **banco de questões de exemplo**, então você consegue
gerar provas na hora.

## Como usar
1. **Banco de Questões** → envie o material da sua aula (PDF, PowerPoint ou texto) e
   clique em gerar. A IA cria questões fáceis, médias e difíceis.
2. **Questões de cálculo** aparecem como *"Pendente de revisão"*. Confira o exemplo
   calculado e, se estiver certo, clique em **"Aprovar"**. ⚠️ *Sempre confira a conta —
   a IA pode errar a fórmula.*
3. **Gerar Provas** → escolha quantas questões fáceis, médias e difíceis, e quantos
   alunos. Baixe as provas e os gabaritos e é só imprimir.

## Para gerar questões novas (opcional)
É preciso uma **chave de API**. Copie o arquivo `.env.example` para `.env` e cole a
chave depois de `PORTKEY_API_KEY=`. Sem a chave, o programa ainda funciona com o banco
de exemplo.

Qualquer dúvida, peça ajuda ao assistente de IA — ele responde em português. 😊

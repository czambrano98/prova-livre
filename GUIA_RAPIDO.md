# Guia Rápido — ProvaLivre 🇧🇷

Olá! Este programa cria **provas diferentes para cada aluno** (mesma matéria e
dificuldade, mas questões e números diferentes) para dificultar a cola. Ele também
monta o **gabarito** automaticamente.

O ProvaLivre é **bilíngue** (Português / Inglês) — é só usar o botão **PT / EN** no
canto superior direito.

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

## ⚠️ Avisos importantes (leia antes de usar)
- **Confira sempre as questões de cálculo.** A IA escreve a fórmula, mas pode errar.
  Por isso as questões numéricas ficam como *"Pendente de revisão"* até você conferir o
  exemplo calculado e clicar em **"Aprovar"**. Só depois elas entram nas provas.
- **Revise também as outras questões.** A IA ajuda muito, mas pode cometer erros de
  conteúdo. Dê uma olhada nas questões antes de aplicar a prova.
- **O custo é uma estimativa.** Os valores abaixo são aproximados e dependem da cotação
  do dólar e do modelo de IA usado.

## Quanto custa?
Gerar as **provas de uma turma inteira** custa **R$ 0,00** — isso é feito pelo próprio
programa, sem usar IA. A IA só é usada para **criar questões novas**, e é muito barato:

| O que você faz | Custo aproximado |
|---|---|
| Criar um banco de questões a partir de uma aula | ~US$ 0,007 ≈ **R$ 0,04** |
| Uso típico por mês (uns 2 bancos) | ≈ **R$ 0,08** |
| Gerar as provas de todos os alunos | **R$ 0,00** |

*(Câmbio aproximado de R$ 5,40 por US$ 1 — confira a cotação atual. O valor exato
depende do modelo de IA.)*

## Como colocar a chave de API
Para **criar questões novas** o programa precisa de uma chave.

**Por enquanto, use a chave que a Carine vai te passar.** É só colocá-la no arquivo de
configuração:
1. Na pasta do programa, copie o arquivo `.env.example` e renomeie a cópia para `.env`.
2. Abra o `.env` num editor de texto simples e cole a linha que a Carine te mandar, por
   exemplo:
   ```
   OPENAI_API_KEY=cole-a-chave-que-a-carine-passou
   ```
3. Salve o arquivo e rode o programa de novo.

Sem nenhuma chave, o programa ainda abre e gera provas com o **banco de exemplo**.

### Mais tarde: criar sua própria chave (opcional)
Se um dia quiser uma chave só sua (você paga o uso, bem baratinho):
1. Acesse https://platform.openai.com/api-keys e faça login.
2. Em **Billing**, adicione um crédito (US$ 5 dura bastante neste uso).
3. Clique em **"Create new secret key"**, copie a chave (começa com `sk-`) e coloque no
   `.env` como acima, na linha `OPENAI_API_KEY=`.

🔒 **Nunca compartilhe a chave** nem a coloque em prints, e-mails ou mensagens.

Qualquer dúvida, peça ajuda ao assistente de IA — ele responde em português. 😊

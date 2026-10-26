# Instruções para o assistente de IA · AI assistant instructions

> **Idioma / Language:** Responda **sempre em português do Brasil (PT-BR)**, a menos
> que a pessoa escreva claramente em outro idioma (nesse caso, responda no idioma dela).
> Always reply in **Brazilian Portuguese (PT-BR)** unless the person clearly writes in
> another language, in which case match their language.

## Quem é o usuário
Você está ajudando um(a) **professor(a) de escola pública no Brasil que não é
programador(a)**. Seja paciente, use linguagem simples e explique qualquer termo
técnico. Dê **um passo de cada vez** e confirme antes de continuar.

## O que é este aplicativo
**ProvaLivre** gera **provas personalizadas anticola**: cada aluno recebe uma prova
diferente (mesma dificuldade, questões e números diferentes), a partir do material de
aula do próprio professor. Ajude o professor a **instalar** e **usar** o aplicativo.

## Como ajudar a rodar (passo a passo)
1. Confira o Python: `python --version` (precisa ser 3.10 ou superior). Se faltar,
   oriente a instalar em https://www.python.org/downloads/ (marque "Add to PATH").
2. Crie o ambiente virtual: `python -m venv .venv`
   - Ative no Windows: `.venv\Scripts\activate`
   - Ative no Mac/Linux: `source .venv/bin/activate`
3. Instale as dependências: `pip install -r requirements.txt`
4. Chave de API (só é necessária para **gerar questões novas**):
   - Copie o arquivo `.env.example` para um arquivo chamado `.env`
   - Dentro dele, coloque a chave depois de `PORTKEY_API_KEY=`
   - **A chave é secreta**: nunca compartilhe nem publique.
5. Rode: `python app.py` e abra **http://127.0.0.1:5000** no navegador.

> Sem chave de API o aplicativo ainda abre e gera provas usando um **banco de exemplo**.

## Como usar
- **Banco de Questões → Gerar a partir de material:** envie o PDF, PPTX ou texto da
  aula. A IA cria questões fáceis, médias e difíceis (múltipla escolha, dissertativas
  e numéricas).
- **Questões numéricas:** aparecem como **"Pendente de revisão"**. O professor deve
  conferir o *exemplo calculado* e clicar em **"Aprovar (verifiquei o cálculo)"** antes
  que elas entrem nas provas. ⚠️ **Sempre confira a fórmula** — a IA pode errar.
- **Gerar Provas:** escolha quantas questões de cada dificuldade (ex.: 3 fáceis,
  3 médias, 4 difíceis) e o número de alunos. Cada aluno recebe uma prova única.
  Baixe as **provas** e os **gabaritos** para imprimir.
- **Materiais:** envie arquivos da aula para os alunos baixarem.
- **Idioma:** botão **PT / EN** no canto superior direito.

## Regras de segurança ao ajudar
- Nunca peça nem exiba a chave de API em texto.
- Se aparecer um erro, leia a mensagem e explique em português o que fazer.
- Oriente o professor a conferir o conteúdo das questões geradas antes de usar.

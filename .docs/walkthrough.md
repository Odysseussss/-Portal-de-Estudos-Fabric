# Walkthrough do Projeto - Portal de Estudos Fabric

Este documento descreve os passos realizados para configurar e manter o projeto.

## 28/03/2026 - Configuração Inicial e Reativação do Interpretador

1. **Análise de Diretório**: Foi identificado que apenas o arquivo `app_estudps.py` está presente.
2. **Criação de Docs**: Estrutura de `/docs` criada conforme as regras do projeto.
3. **Instalação do UV**: O `uv` foi instalado via pip (`python -m pip install uv`) para garantir o funcionamento estável no Windows.
4. **Configuração de Projeto**: O projeto foi inicializado (`uv init`) e as dependências (`streamlit`, `pandas`, `plotly`) foram adicionadas.
5. **Pronto para Uso**: O ambiente `.venv` foi gerado automaticamente.

## Integração com IA (Groq / Llama 3)
1. **Instalação das Extensões**: Adicionado `groq` e `python-dotenv` ao projeto através do comando `uv add` (removido dependência antiga do Gemini devido à incompatibilidade de modelo).
2. **Cofre de Chaves Seguras**: Configuração do arquivo local `.env` contendo a `GROQ_API_KEY`. (Nota: `.env` não deve ser enviado para repositórios públicos).
3. **App de Questões Aprimorado**: Agora o Streamlit conta com abas reestruturadas: 'Responder', 'Cadastro Manual' e 'Gerar com Groq (Llama 3)'. A base está gerando `json_object` nativo via Llama3-70b-8192 focado totalmente no simulado para a prova DP-700.

### Como Executar o Projeto
1. Selecione o interpretador `.\.venv\Scripts\python.exe` no VS Code.
2. No terminal, execute:
   ```bash
   uv run streamlit run app_estudps.py
   ```

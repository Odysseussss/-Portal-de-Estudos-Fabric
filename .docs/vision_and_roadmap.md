# Visão de Futuro e Overview do Projeto - Portal de Estudos Fabric

Este documento resume as capacidades atuais e propõe melhorias estratégicas para transformar o portal em uma ferramenta de aprendizado completa.

## 📊 Estado Atual (v0.4)
- **Interpretador**: Gerenciado via `uv` (ambiente isolado e rápido).
- **Dados**: Persistência em CSV local (`dados_questoes.csv`, `dados_tarefas.csv`).
- **IA**: Groq API (Llama 3.3) gerando questões estruturadas com Gabarito e Explicação.
- **Interface**: Streamlit com Dashboard de métricas, Sistema de Tarefas e Simulador de Questões.

## 🚀 Propostas v0.5+ (Roadmap)

### Curto Prazo (UX & Polish)
- [ ] **Simulado Real**: Modo de prova com tempo contado e X questões limitadas.
- [ ] **Feedback Sonoro**: Sons sutis para Acerto/Erro (opcional).
- [ ] **Exportação**: Gerar CSV/Excel consolidado dos seus erros para revisão offline.

### Médio Prazo (Funcionalidades de Estudos)
- [ ] **AI Mentor Tab**: Interface de chat direta com a IA para explicar conceitos complexos ("Ant, me explique Direct Lake como se eu tivesse 5 anos").
- [ ] **Recomendação Dinâmica**: Sistema que linka documentações do MS Learn baseada nos seus erros.
- [ ] **Timer Pomodoro**: Auxílio de foco integrado na barra lateral.

### Longo Prazo (Arquitetura)
- [ ] **Banco de Dados Relacional**: Migrar de CSV para SQLite se a base de questões ficar muito grande (>1000 questões).
- [ ] **Múltiplos Perfis**: Suporte para outros usuários ou diferentes certificações (ex: DP-203, DP-600).

---
*Gerado por Ant em 29/03/2026*

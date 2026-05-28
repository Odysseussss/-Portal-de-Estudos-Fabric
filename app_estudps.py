import streamlit as st
import pandas as pd
import datetime
import plotly.express as px
import os
import json

# --- CONFIGURAÇÃO INICIAL ---
st.set_page_config(page_title="Portal de Estudos DP-700", page_icon="📊", layout="wide")

# --- DETECÇÃO DE MODO: ADMIN (local) vs PÚBLICO (produção) ---
# Se existir .env com GROQ_API_KEY, estamos em modo admin (sua máquina).
# Em produção (Streamlit Cloud), não haverá .env nem chave → modo público.
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # Em produção, python-dotenv pode não estar instalado

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MODO_ADMIN = bool(GROQ_API_KEY)

# Groq client só é criado no modo admin
groq_client = None
if MODO_ADMIN:
    from groq import Groq
    
    @st.cache_resource
    def get_groq_client():
        return Groq(api_key=os.getenv("GROQ_API_KEY"))
    
    groq_client = get_groq_client()


# --- SCHEMA E ARQUIVOS DE DADOS ---
ARQUIVO_QUESTOES = "dados_questoes.csv"
COLUNAS_QUESTOES = ["ID", "Topico", "Pergunta", "Alt_A", "Alt_B", "Alt_C", "Alt_D",
                    "Resposta_Correta", "Explicacao", "Sua_Resposta", "Confianca", "Data_Resposta"]

def _garantir_arquivo_questoes():
    if not os.path.exists(ARQUIVO_QUESTOES):
        pd.DataFrame(columns=COLUNAS_QUESTOES).to_csv(ARQUIVO_QUESTOES, index=False)
    else:
        df = pd.read_csv(ARQUIVO_QUESTOES)
        for col in COLUNAS_QUESTOES:
            if col not in df.columns:
                df[col] = ""
        df.to_csv(ARQUIVO_QUESTOES, index=False)

_garantir_arquivo_questoes()


# --- KANBAN: DADOS EM SESSION_STATE (por sessão do navegador) ---
# Cada usuário terá seu próprio Kanban isolado na memória do navegador.
# Os dados NÃO são persistidos em disco — só existem enquanto a aba estiver aberta.
def _inicializar_kanban():
    if "kanban_tarefas" not in st.session_state:
        st.session_state.kanban_tarefas = []

_inicializar_kanban()


# --- RESPOSTAS EM SESSION_STATE (por sessão do navegador) ---
# Em produção, as respostas do usuário ficam na sessão (não no CSV global).
# Em modo admin, as respostas são salvas no CSV (para seu uso pessoal).
def _inicializar_respostas():
    if "respostas_usuario" not in st.session_state:
        st.session_state.respostas_usuario = {}  # {ID: {"resposta": "A", "confianca": "...", "data": "..."}}

_inicializar_respostas()


# --- CACHE DE DADOS ---
@st.cache_data(ttl=30)
def carregar_dados_questoes():
    return pd.read_csv(ARQUIVO_QUESTOES)

def salvar_questoes(df: pd.DataFrame):
    """Só usado em modo admin para persistência no CSV."""
    df.to_csv(ARQUIVO_QUESTOES, index=False)
    st.cache_data.clear()


# --- INTEGRAÇÃO COM IA (Apenas modo admin) ---
def gerar_lote_questoes_com_ia(topico: str, quantidade: int):
    if not groq_client:
        return None, "A chave GROQ_API_KEY não está configurada no arquivo .env."

    prompt = f"""
    Você é um especialista certificado na prova Microsoft DP-700 (Data Engineering on Microsoft Fabric).
    Crie exatamente {quantidade} questões de múltipla escolha complexas e práticas focadas no tópico: '{topico}'.
    Gere questões bastante variadas dentro desse tópico.

    A saída DEVE ser estritamente um JSON no formato:
    {{
        "questoes": [
            {{
                "pergunta": "Texto do enunciado da questão (apenas o cenário/problema, SEM as alternativas)",
                "alternativa_a": "Texto completo da alternativa A",
                "alternativa_b": "Texto completo da alternativa B",
                "alternativa_c": "Texto completo da alternativa C",
                "alternativa_d": "Texto completo da alternativa D",
                "resposta_correta": "Letra da resposta correta (A, B, C ou D)",
                "explicacao": "Explicação detalhada de por que a resposta correta está certa e porque as outras estão erradas"
            }}
        ]
    }}
    """
    try:
        response = groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": "Você gera exclusivamente JSON válido contendo uma lista de questões de prova em um objeto com a chave 'questoes'."},
                {"role": "user", "content": prompt}
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.7,
            response_format={"type": "json_object"}
        )
        dados = json.loads(response.choices[0].message.content.strip())
        return dados.get("questoes", []), None
    except Exception as e:
        return None, f"Erro ao chamar a API do Groq: {str(e)}"


# --- SIDEBAR ---
with st.sidebar:
    st.image("https://img.icons8.com/fluency/144/database.png", width=80)
    st.title("Portal de Estudos")

    data_prova = st.date_input("🎯 Data da sua Prova:", value=st.session_state.get('data_prova_cache', datetime.date(2026, 5, 23)))
    st.session_state.data_prova_cache = data_prova

    dias_restantes = (data_prova - datetime.date.today()).days
    if dias_restantes > 0:
        st.metric(label="⌛ Dias restantes", value=dias_restantes)
    elif dias_restantes == 0:
        st.success("🚀 É HOJE! Boa prova!")
    else:
        st.info("Boa sorte na prova! 🍀")

    st.divider()

    # Menu: público vê 3 opções, admin vê 5
    menu_opcoes = ["📊 Dashboard", "✍️ Praticar Questões", "📋 Minhas Metas"]
    if MODO_ADMIN:
        menu_opcoes.extend(["🚀 Gerar Questões (IA)", "⚙️ Configurações"])

    opcao = st.radio("Navegação:", menu_opcoes)

    st.divider()
    if MODO_ADMIN:
        st.success("🔓 Modo Administrador")
    st.caption("Desenvolvido por Ulisses de Pinho")
    st.markdown("[Me siga no LinkedIn](https://www.linkedin.com/in/ulisses-de-pinho/)")


# ══════════════════════════════════════════════════════════════
# PÁGINAS PÚBLICAS (Dashboard, Praticar, Kanban)
# ══════════════════════════════════════════════════════════════

def pagina_dashboard():
    st.title("📊 Painel Geral de Desempenho")
    
    df_q = carregar_dados_questoes()
    respostas = st.session_state.respostas_usuario

    if df_q.empty:
        st.warning("Nenhuma questão disponível no banco. Aguarde novas questões!")
        return

    # Total de questões no banco (Global)
    total_banco = len(df_q)
    # Preparar dados consolidados (Mesclar Banco + Histórico CSV + Sessão Atual)
    dados_consolidados = []
    for _, row in df_q.iterrows():
        qid = row['ID']
        resp_viva = None
        conf_viva = "N/A"
        
        # 1. Prioridade para a sessão atual
        if qid in respostas:
            resp_viva = respostas[qid]['resposta']
            conf_viva = respostas[qid]['confianca']
        # 2. Backup: histórico gravado no CSV
        elif str(row.get('Sua_Resposta', "")).strip() != "" and str(row.get('Sua_Resposta', "")).strip() != "nan":
            resp_viva = str(row['Sua_Resposta']).strip()
            conf_viva = str(row.get('Confianca', 'Confiante')).strip()

        if resp_viva:
            dados_consolidados.append({
                "Tópico": row['Topico'],
                "Resultado": "✅ Acerto" if resp_viva.upper() == str(row['Resposta_Correta']).strip().upper() else "❌ Erro",
                "Confiança": conf_viva
            })
    
    total_respondidas = len(dados_consolidados)
    
    # ── MÉTRICAS DE TOPO ──
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("📚 Questões no Banco", total_banco)
    col2.metric("✍️ Respondidas", total_respondidas)
    
    if total_respondidas == 0:
        col3.metric("🏆 Taxa de Acerto", "0%")
        col4.metric("📈 Cobertura", "0%")
        st.info("👋 O banco está pronto! Comece a praticar para ver os gráficos de desempenho aqui.")
        return

    df_result = pd.DataFrame(dados_consolidados)
    acertos = len(df_result[df_result['Resultado'] == "✅ Acerto"])
    taxa_acerto = (acertos / total_respondidas) * 100

    col3.metric("🏆 Taxa de Acerto", f"{taxa_acerto:.1f}%")
    col4.metric("📈 Cobertura", f"{(total_respondidas/total_banco)*100:.1f}%")

    st.divider()

    # ── GRÁFICOS ──
    c1, c2 = st.columns(2)

    with c1:
        st.subheader("🎯 Precisão por Tópico")
        # Gráfico de barras horizontais empilhadas
        fig_barra = px.histogram(
            df_result, 
            y="Tópico", 
            color="Resultado", 
            barmode="group",
            orientation='h',
            color_discrete_map={"✅ Acerto": "#22c55e", "❌ Erro": "#ef4444"},
            category_orders={"Resultado": ["✅ Acerto", "❌ Erro"]}
        )
        st.plotly_chart(fig_barra, use_container_width=True)

    with c2:
        st.subheader("🧠 Análise de Confiança")
        fig_pizza = px.pie(
            df_result, 
            names="Confiança", 
            hole=0.4,
            color_discrete_sequence=px.colors.sequential.RdBu
        )
        st.plotly_chart(fig_pizza, use_container_width=True)

    st.divider()
    
    # Tabela de progresso detalhado
    st.subheader("📋 Resumo por Conhecimento")
    progresso_topico = df_result.groupby("Tópico").size().reset_index(name="Respondidas")
    acertos_topico = df_result[df_result['Resultado'] == "✅ Acerto"].groupby("Tópico").size().reset_index(name="Acertos")
    
    resumo = pd.merge(progresso_topico, acertos_topico, on="Tópico", how="left").fillna(0)
    resumo['Precisão'] = (resumo['Acertos'] / resumo['Respondidas'] * 100).round(1).astype(str) + '%'
    
    st.table(resumo)


def pagina_questoes():
    st.title("✍️ Praticar Questões")

    df_q = carregar_dados_questoes()

    if df_q.empty:
        st.info("Ainda não há questões no banco. Aguarde novas questões serem adicionadas!")
        return

    # Filtro de Tópico
    topicos_unicos = df_q['Topico'].dropna().unique().tolist()
    opcoes_topicos = ["Todos os tópicos"] + sorted(topicos_unicos)
    topico_selecionado = st.selectbox("🎯 Filtrar por Tópico:", opcoes_topicos, key="select_topico_responder")

    if topico_selecionado != "Todos os tópicos":
        df_q_filtrado = df_q[df_q['Topico'] == topico_selecionado]
    else:
        df_q_filtrado = df_q.copy()

    # Filtrar não respondidas usando session_state
    respostas = st.session_state.respostas_usuario
    ids_respondidas = set(respostas.keys())
    df_nao_resp = df_q_filtrado[~df_q_filtrado['ID'].isin(ids_respondidas)]

    pendentes = len(df_nao_resp)
    total_filtrado = len(df_q_filtrado)

    if total_filtrado > 0:
        respondidas_count = total_filtrado - pendentes
        st.progress(respondidas_count / total_filtrado,
                    text=f"{respondidas_count}/{total_filtrado} questões respondidas ({topico_selecionado})")
    else:
        st.info(f"Não há questões cadastradas para o tópico '{topico_selecionado}'.")
        return

    if df_nao_resp.empty:
        st.success("🎉 Você zerou a fila deste tópico! Altere o filtro para praticar outros assuntos.")
        return

    q = df_nao_resp.iloc[0]
    st.divider()
    st.caption(f"📌 Questão #{int(q['ID'])} — {q['Topico']}")
    st.markdown(f"### {q['Pergunta']}")
    st.divider()

    # Montar as opções com o texto das alternativas
    def _alt(letra):
        col_map = {"A": "Alt_A", "B": "Alt_B", "C": "Alt_C", "D": "Alt_D"}
        texto = str(q.get(col_map[letra], "")).strip()
        return f"{letra}) {texto}" if texto and texto != "nan" else letra

    opcoes = [_alt("A"), _alt("B"), _alt("C"), _alt("D")]

    # Se a questão atual acabou de ser respondida (para mostrar a explicação)
    estado_resp = st.session_state.get("questao_atual_respondida")
    
    if estado_resp and estado_resp["id"] == q['ID']:
        letra_escolhida = estado_resp["resposta"]
        correta = estado_resp["correta"]
        explicacao = estado_resp["explicacao"]

        st.radio("Sua resposta:", opcoes, index=["A", "B", "C", "D"].index(letra_escolhida[0]), disabled=True)
        st.select_slider("Nível de Confiança:", options=["Chute", "Pouco Confiante", "Confiante", "Certeza"], value=estado_resp["confianca"], disabled=True)
        
        if letra_escolhida[0] == correta:
            st.success(f"✅ Correto! A resposta é **{correta})**")
        else:
            st.error(f"❌ Errou! Você marcou **{letra_escolhida[0]})**, mas a correta é **{correta})**")

        if explicacao and explicacao not in ("", "nan"):
            st.info(f"💡 **Explicação:**\n\n{explicacao}")
            
        if st.button("➡️ Próxima Questão"):
            # Salvar resposta no session_state (por sessão do navegador) e avançar
            st.session_state.respostas_usuario[q['ID']] = {
                "resposta": letra_escolhida[0],
                "confianca": estado_resp["confianca"],
                "data": str(datetime.date.today())
            }
            st.session_state.questao_atual_respondida = None
            st.rerun()

    else:
        with st.form("form_responder"):
            escolha = st.radio("Sua resposta:", opcoes, horizontal=False)
            confianca = st.select_slider("Nível de Confiança:", options=["Chute", "Pouco Confiante", "Confiante", "Certeza"])
            enviar = st.form_submit_button("📨 Enviar Resposta")

            if enviar:
                correta = str(q['Resposta_Correta']).strip().upper()
                explicacao = str(q.get("Explicacao", "")).strip()

                st.session_state.questao_atual_respondida = {
                    "id": q['ID'],
                    "resposta": escolha,
                    "confianca": confianca,
                    "correta": correta,
                    "explicacao": explicacao
                }
                st.rerun()


def pagina_kanban():
    st.title("📋 Minhas Metas de Estudo")
    st.caption("Suas metas são pessoais e ficam salvas na sua sessão do navegador.")

    tarefas = st.session_state.kanban_tarefas

    # --- SCORECARDS ---
    if tarefas:
        total = len(tarefas)
        concluidas = sum(1 for t in tarefas if t['status'] == 'Concluído')
        em_andamento = sum(1 for t in tarefas if t['status'] == 'Em Andamento')
        pendentes = sum(1 for t in tarefas if t['status'] == 'Pendente')

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("📌 Total", total)
        col2.metric("✅ Concluídas", concluidas)
        col3.metric("⏳ Em Andamento", em_andamento)
        col4.metric("📝 Pendentes", pendentes)
        st.divider()

    # --- NOVA TAREFA ---
    with st.expander("➕ Adicionar Nova Meta"):
        with st.form("form_nova_tarefa", clear_on_submit=True):
            tarefa = st.text_input("Sua Meta de Estudo (Ex: Ler Docs OneLake)")
            desc = st.text_area("Detalhes adicionais")
            c1, c2 = st.columns(2)
            prioridade = c1.selectbox("Prioridade", ["Alta", "Média", "Baixa"])
            status_inicial = c2.selectbox("Status Inicial", ["Pendente", "Em Andamento", "Concluído"])

            if st.form_submit_button("💾 Salvar Meta"):
                if tarefa.strip():
                    st.session_state.kanban_tarefas.append({
                        "tarefa": tarefa,
                        "descricao": desc,
                        "status": status_inicial,
                        "prioridade": prioridade,
                        "data": str(datetime.date.today())
                    })
                    st.success("Meta adicionada!")
                    st.rerun()
                else:
                    st.warning("Digite o nome da sua meta.")

    if not tarefas:
        st.info("Nenhuma meta cadastrada. Adicione uma acima para organizar seus estudos!")
        return

    # --- KANBAN BOARD ---
    st.subheader("Visualização Kanban")
    col_pendente, col_andamento, col_concluido = st.columns(3)

    def criar_card(tarefa_dict, idx):
        cor_pri = {"Alta": "🔴", "Média": "🟡", "Baixa": "🟢"}.get(tarefa_dict['prioridade'], "⚪")
        with st.container(border=True):
            st.markdown(f"**{cor_pri} {tarefa_dict['tarefa']}**")
            if tarefa_dict['descricao'].strip():
                st.caption(tarefa_dict['descricao'])

            col_a, col_b = st.columns([3, 1])
            novo_status = col_a.selectbox("Mover para:", ["Pendente", "Em Andamento", "Concluído"],
                                          index=["Pendente", "Em Andamento", "Concluído"].index(tarefa_dict['status']),
                                          key=f"status_{idx}", label_visibility="collapsed")

            if col_b.button("🗑️", key=f"del_{idx}"):
                st.session_state.kanban_tarefas.pop(idx)
                st.rerun()

            if novo_status != tarefa_dict['status']:
                st.session_state.kanban_tarefas[idx]['status'] = novo_status
                st.rerun()

    with col_pendente:
        st.markdown("### 📝 Pendente")
        for idx, t in enumerate(tarefas):
            if t['status'] == 'Pendente':
                criar_card(t, idx)

    with col_andamento:
        st.markdown("### ⏳ Em Andamento")
        for idx, t in enumerate(tarefas):
            if t['status'] == 'Em Andamento':
                criar_card(t, idx)

    with col_concluido:
        st.markdown("### ✅ Concluído")
        for idx, t in enumerate(tarefas):
            if t['status'] == 'Concluído':
                criar_card(t, idx)


# ══════════════════════════════════════════════════════════════
# PÁGINAS ADMINISTRATIVAS (Só aparecem quando GROQ_API_KEY existe)
# ══════════════════════════════════════════════════════════════

def pagina_gerar_ia():
    st.title("🚀 Gerar Questões com IA")
    st.write("Abasteça seu banco de questões local. Crie lotes sobre os tópicos da prova DP-700.")

    col1, col2 = st.columns(2)
    topico_ia = col1.selectbox("Tópico da questão:", [
        "1. Planejar Ambiente", "2. Ingestão de Dados",
        "3. Transformação Spark", "4. Modelagem Direct Lake",
        "5. Segurança e Governança", "6. Monitoramento e Otimização",
        "7. RLS (Row-Level Security)", "8. OLS (Object-Level Security)",
        "9. T-SQL no Warehouse", "10. Configuração de Tenant e Capacidade",
        "11. Shortcuts e Espelhamento (Mirroring)"
    ], key="top_ia")
    quantidade = col2.slider("Quantidade de questões:", min_value=10, max_value=30, value=10, step=5)

    if st.button("✨ Gerar e Salvar Lote"):
        with st.spinner(f"Llama 3.3 elaborando {quantidade} questões sobre '{topico_ia}'..."):
            questoes_geradas, erro = gerar_lote_questoes_com_ia(topico_ia, quantidade)

        if erro:
            st.error(erro)
        elif questoes_geradas:
            df_q = carregar_dados_questoes()
            novo_id_inicial = int(df_q["ID"].max()) + 1 if not df_q.empty and df_q["ID"].notna().any() else 1

            novas_linhas = []
            for i, dados in enumerate(questoes_geradas):
                nova = {
                    "ID": novo_id_inicial + i,
                    "Topico": topico_ia,
                    "Pergunta": dados.get("pergunta", ""),
                    "Alt_A": dados.get("alternativa_a", ""),
                    "Alt_B": dados.get("alternativa_b", ""),
                    "Alt_C": dados.get("alternativa_c", ""),
                    "Alt_D": dados.get("alternativa_d", ""),
                    "Resposta_Correta": dados.get("resposta_correta", "A").upper().strip(),
                    "Explicacao": dados.get("explicacao", ""),
                    "Sua_Resposta": "", "Confianca": "", "Data_Resposta": ""
                }
                novas_linhas.append(nova)

            salvar_questoes(pd.concat([df_q, pd.DataFrame(novas_linhas)], ignore_index=True))
            st.success(f"✅ {len(questoes_geradas)} questões geradas e salvas!")

            with st.expander("👁️ Preview (primeira do lote)"):
                primeira = questoes_geradas[0]
                st.markdown(f"**Enunciado:** {primeira.get('pergunta', '')}")
                st.info(f"**Gabarito:** {primeira.get('resposta_correta', '').upper()}")
                st.markdown(f"**Explicação:** {primeira.get('explicacao', '')}")

    # Estatísticas do banco
    st.divider()
    st.subheader("📦 Banco de Questões Atual")
    df_q = carregar_dados_questoes()
    if not df_q.empty:
        st.metric("Total de questões no banco", len(df_q))
        st.dataframe(df_q[['ID', 'Topico', 'Pergunta']].head(20), width=900)
    else:
        st.info("Banco vazio.")


def pagina_configuracoes():
    st.title("⚙️ Configurações do Portal")
    st.subheader("Gerenciar Dados Locais")
    st.warning("⚠️ Atenção: as ações abaixo apagam dados permanentemente.")

    col1, col2 = st.columns(2)
    if col1.button("🔥 Resetar Questões"):
        if os.path.exists(ARQUIVO_QUESTOES):
            os.remove(ARQUIVO_QUESTOES)
            _garantir_arquivo_questoes()
            st.cache_data.clear()
            st.success("Dados de questões resetados.")

    if col2.button("🔥 Limpar Respostas da Sessão"):
        st.session_state.respostas_usuario = {}
        st.success("Suas respostas foram limpas.")
        st.rerun()


# --- ROTEAMENTO ---
if opcao == "📊 Dashboard":
    pagina_dashboard()
elif opcao == "✍️ Praticar Questões":
    pagina_questoes()
elif opcao == "📋 Minhas Metas":
    pagina_kanban()
elif opcao == "🚀 Gerar Questões (IA)" and MODO_ADMIN:
    pagina_gerar_ia()
elif opcao == "⚙️ Configurações" and MODO_ADMIN:
    pagina_configuracoes()
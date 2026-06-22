import streamlit as st
import pandas as pd
import datetime
import plotly.express as px
import os

# --- CONFIGURAÇÃO INICIAL ---
st.set_page_config(page_title="Portal de Estudos DP-700", page_icon="📊", layout="wide")


# --- SCHEMA E ARQUIVOS DE DADOS ---
ARQUIVO_QUESTOES = "dados_questoes.csv"
COLUNAS_QUESTOES = ["ID", "Topico", "Pergunta", "Alt_A", "Alt_B", "Alt_C", "Alt_D",
                    "Resposta_Correta", "Explicacao", "Sua_Resposta", "Confianca", "Data_Resposta"]

def _garantir_arquivo_questoes():
    if not os.path.exists(ARQUIVO_QUESTOES):
        pd.DataFrame(columns=COLUNAS_QUESTOES).to_csv(ARQUIVO_QUESTOES, index=False)
    else:
        df = pd.read_csv(ARQUIVO_QUESTOES)
        colunas_faltantes = [col for col in COLUNAS_QUESTOES if col not in df.columns]
        if colunas_faltantes:
            for col in colunas_faltantes:
                df[col] = ""
            df.to_csv(ARQUIVO_QUESTOES, index=False)

@st.cache_resource
def _executar_garantia_uma_vez():
    _garantir_arquivo_questoes()
    return True

_executar_garantia_uma_vez()


# --- KANBAN: DADOS EM SESSION_STATE (por sessão do navegador) ---
# Cada usuário terá seu próprio Kanban isolado na memória do navegador.
# Os dados NÃO são persistidos em disco — só existem enquanto a aba estiver aberta.
ARQUIVO_TAREFAS = "dados_tarefas.csv"

def _inicializar_kanban():
    if "kanban_tarefas" not in st.session_state:
        if os.path.exists(ARQUIVO_TAREFAS):
            try:
                df_t = pd.read_csv(ARQUIVO_TAREFAS)
                tarefas = []
                for _, row in df_t.iterrows():
                    tarefas.append({
                        "tarefa": str(row.get('Tarefa', '')),
                        "descricao": str(row.get('Descricao', '')),
                        "status": str(row.get('Status', 'Pendente')),
                        "prioridade": str(row.get('Prioridade', 'Média')),
                        "data": str(row.get('Data_Criacao', datetime.date.today()))
                    })
                st.session_state.kanban_tarefas = tarefas
            except Exception:
                st.session_state.kanban_tarefas = []
        else:
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

# --- INTEGRAÇÃO COM IA REMOVIDA ---
# As questões devem ser inseridas manualmente no CSV localmente.


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

    # Menu: público vê 3 opções
    menu_opcoes = ["📊 Dashboard", "✍️ Praticar Questões", "📋 Minhas Metas"]

    opcao = st.radio("Navegação:", menu_opcoes)

    st.divider()
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
        # 2. Backup do CSV removido para manter isolamento total da sessão.

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
    
    def sort_key(t):
        try:
            return int(t.split('.')[0])
        except:
            return 999
            
    opcoes_topicos = ["Todos os tópicos"] + sorted(topicos_unicos, key=sort_key)
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


# --- ROTEAMENTO ---
if opcao == "📊 Dashboard":
    pagina_dashboard()
elif opcao == "✍️ Praticar Questões":
    pagina_questoes()
elif opcao == "📋 Minhas Metas":
    pagina_kanban()
import streamlit as st
import pandas as pd
import datetime
import plotly.express as px
import os
from groq import Groq
from dotenv import load_dotenv
import json

# --- CONFIGURAÇÃO INICIAL ---
load_dotenv()
st.set_page_config(page_title="Portal de Estudos DP-700", page_icon="📊", layout="wide")

# FIX DE PERFORMANCE: Groq Client instanciado 1x e mantido em memória entre reruns
@st.cache_resource
def get_groq_client():
    key = os.getenv("GROQ_API_KEY")
    return Groq(api_key=key) if key else None

groq_client = get_groq_client()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# --- SCHEMA E ARQUIVOS DE DADOS ---
ARQUIVO_QUESTOES = "dados_questoes.csv"
ARQUIVO_TAREFAS  = "dados_tarefas.csv"
COLUNAS_QUESTOES = ["ID", "Topico", "Pergunta", "Alt_A", "Alt_B", "Alt_C", "Alt_D",
                    "Resposta_Correta", "Explicacao", "Sua_Resposta", "Confianca", "Data_Resposta"]
COLUNAS_TAREFAS  = ["Tarefa", "Descricao", "Status", "Prioridade", "Data_Criacao"]

def _garantir_arquivos():
    if not os.path.exists(ARQUIVO_QUESTOES):
        pd.DataFrame(columns=COLUNAS_QUESTOES).to_csv(ARQUIVO_QUESTOES, index=False)
    else:
        # Migração suave: adicionar colunas novas se não existirem
        df = pd.read_csv(ARQUIVO_QUESTOES)
        for col in COLUNAS_QUESTOES:
            if col not in df.columns:
                df[col] = ""
        df.to_csv(ARQUIVO_QUESTOES, index=False)

    if not os.path.exists(ARQUIVO_TAREFAS):
        pd.DataFrame(columns=COLUNAS_TAREFAS).to_csv(ARQUIVO_TAREFAS, index=False)

_garantir_arquivos()

# --- CACHE DE DADOS (TTL=30s, invalidado manualmente após escrita) ---
@st.cache_data(ttl=30)
def carregar_dados_questoes():
    return pd.read_csv(ARQUIVO_QUESTOES)

@st.cache_data(ttl=30)
def carregar_dados_tarefas():
    return pd.read_csv(ARQUIVO_TAREFAS)

def salvar_questoes(df: pd.DataFrame):
    df.to_csv(ARQUIVO_QUESTOES, index=False)
    st.cache_data.clear()

def salvar_tarefas(df: pd.DataFrame):
    df.to_csv(ARQUIVO_TAREFAS, index=False)
    st.cache_data.clear()


# --- INTEGRAÇÃO COM IA ---
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
    st.title("Menu Principal")

    data_prova = datetime.date(2026, 5, 23)
    dias_restantes = (data_prova - datetime.date.today()).days
    st.metric(label="🗓️ Dias para a Prova", value=dias_restantes)
    st.write(f"Prova: {data_prova.strftime('%d/%m/%Y')}")
    st.divider()

    opcao = st.radio("Ir para:", ["📊 Dashboard", "✍️ Praticar Questões", "📋 Tarefas", "⚙️ Configurações"])
    st.divider()
    st.caption("Desenvolvido para Ulisses de Pinho")


# --- PÁGINAS ---

def pagina_dashboard():
    st.title("📊 Painel de Resultados")
    df_q = carregar_dados_questoes()

    respondidas = df_q[df_q['Sua_Resposta'].notna() & (df_q['Sua_Resposta'] != "")]
    if respondidas.empty:
        st.warning("Você ainda não respondeu nenhuma questão. Vá para '✍️ Praticar Questões'!")
        return

    acertos = len(respondidas[respondidas['Resposta_Correta'].astype(str).str.strip().str.upper() ==
                              respondidas['Sua_Resposta'].astype(str).str.strip().str.upper()])
    erros = len(respondidas) - acertos
    taxa = (acertos / len(respondidas)) * 100

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Respondidas", len(respondidas))
    col2.metric("✅ Acertos", acertos)
    col3.metric("❌ Erros", erros)
    col4.metric("🏆 Taxa de Acerto", f"{taxa:.1f}%")
    st.divider()

    df_plot = respondidas.copy()
    df_plot['Resultado'] = df_plot.apply(
        lambda r: 'Acerto' if str(r['Resposta_Correta']).strip().upper() == str(r['Sua_Resposta']).strip().upper() else 'Erro', axis=1
    )

    col_g1, col_g2 = st.columns(2)
    with col_g1:
        st.subheader("Desempenho por Tópico")
        fig = px.histogram(df_plot, x="Topico", color="Resultado", barmode="group",
                           title="Acertos vs Erros por Tópico",
                           color_discrete_map={"Acerto": "#22c55e", "Erro": "#ef4444"})
        st.plotly_chart(fig, width='stretch')

    with col_g2:
        st.subheader("Termômetro de Confiança")
        fig2 = px.pie(df_plot, names="Confianca", title="Distribuição da Confiança")
        st.plotly_chart(fig2, width='stretch')


def pagina_questoes():
    st.title("✍️ Praticar Questões")
    tab_responder, tab_ia = st.tabs(["🎮 Responder", "🚀 Banco de Questões (Gerar IA)"])

    # ── TAB: GERAR COM IA ──
    with tab_ia:
        st.subheader("Gerar Lote de Questões com IA")
        st.write("Abasteça seu banco de questões local. Crie pacotes de simulado sobre os tópicos da prova DP-700.")
        
        if not GROQ_API_KEY:
            st.warning("Configure a chave GROQ_API_KEY no arquivo .env para usar esta funcionalidade.")
        else:
            col1, col2 = st.columns(2)
            topico_ia = col1.selectbox("Tópico da questão:", ["1. Planejar Ambiente", "2. Ingestão de Dados",
                                                             "3. Transformação Spark", "4. Modelagem Direct Lake",
                                                             "5. Segurança e Governança", "6. Monitoramento e Otimização", "7. RLS (Row-Level Security)","OLS (Object-Level Security)",
                                                             "8. T-SQL no Warehouse", "9. Configuração de Tenant e Capacidade","10. Shortcuts e Espelhamento (Mirroring)",
                                                             
                                                             ], key="top_ia")
            quantidade = col2.slider("Quantidade de questões:", min_value=10, max_value=30, value=10, step=5)
            
            if st.button("✨ Gerar e Salvar Lote Mágico"):
                with st.spinner(f"Llama 3.3 elaborando {quantidade} questões sobre '{topico_ia}'... Isso pode levar alguns segundos!"):
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
                    st.success(f"✅ Sucesso! {len(questoes_geradas)} questões geradas e salvas na fila.")
                    
                    with st.expander("👁️ Ver primeira questão gerada (Preview)"):
                        if questoes_geradas:
                            primeira = questoes_geradas[0]
                            st.markdown(f"**Enunciado:** {primeira.get('pergunta', '')}")
                            st.info(f"**Gabarito:** {primeira.get('resposta_correta', '').upper()}")
                            st.markdown(f"**Explicação:** {primeira.get('explicacao', '')}")

    # ── TAB: RESPONDER ──
    with tab_responder:
        st.subheader("Responder Questão da Fila")
        df_q = carregar_dados_questoes()

        if df_q.empty:
            st.info("Cadastre ou gere uma questão para começar a praticar.")
            return

        df_nao_resp = df_q[df_q['Sua_Resposta'].isna() | (df_q['Sua_Resposta'].astype(str).str.strip() == "")]
        pendentes = len(df_nao_resp)
        total = len(df_q)
        st.progress((total - pendentes) / total if total > 0 else 0,
                    text=f"{total - pendentes}/{total} questões respondidas")

        if df_nao_resp.empty:
            st.success("🎉 Você zerou a fila! Gere novas questões com a IA.")
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
            return f"{letra}) {texto}" if texto else letra

        opcoes = [_alt("A"), _alt("B"), _alt("C"), _alt("D")]

        with st.form("form_responder"):
            escolha = st.radio("Sua resposta:", opcoes, horizontal=False)
            confianca = st.select_slider("Nível de Confiança:", options=["Chute", "Pouco Confiante", "Confiante", "Certeza"])
            enviar = st.form_submit_button("📨 Enviar Resposta")

            if enviar:
                letra_escolhida = escolha[0]  # Pega apenas a letra (A, B, C ou D)
                correta = str(q['Resposta_Correta']).strip().upper()

                df_q.loc[df_q['ID'] == q['ID'], 'Sua_Resposta'] = letra_escolhida
                df_q.loc[df_q['ID'] == q['ID'], 'Confianca'] = confianca
                df_q.loc[df_q['ID'] == q['ID'], 'Data_Resposta'] = datetime.date.today()
                salvar_questoes(df_q)

                if letra_escolhida == correta:
                    st.success(f"✅ Correto! A resposta é **{correta})**")
                else:
                    st.error(f"❌ Errou! Você marcou **{letra_escolhida})**, mas a correta é **{correta})**")

                explicacao = str(q.get("Explicacao", "")).strip()
                if explicacao and explicacao not in ("", "nan"):
                    with st.expander("💡 Ver Explicação"):
                        st.info(explicacao)

                st.rerun()


def pagina_tarefas():
    st.title("📋 Sistema de Tarefas (Estudos)")

    df_t = carregar_dados_tarefas()

    # --- SCORECARDS ---
    if not df_t.empty:
        total = len(df_t)
        concluidas = len(df_t[df_t['Status'] == 'Concluído'])
        em_andamento = len(df_t[df_t['Status'] == 'Em Andamento'])
        pendentes = len(df_t[df_t['Status'] == 'Pendente'])

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("📌 Total", total)
        col2.metric("✅ Concluídas", concluidas)
        col3.metric("⏳ Em Andamento", em_andamento)
        col4.metric("📝 Pendentes", pendentes)
        st.divider()

    # --- NOVA TAREFA ---
    with st.expander("➕ Adicionar Nova Tarefa"):
        with st.form("form_nova_tarefa", clear_on_submit=True):
            tarefa = st.text_input("Sua Meta de Estudo (Ex: Ler Docs OneLake)")
            desc = st.text_area("Detalhes adicionais")
            c1, c2 = st.columns(2)
            prioridade = c1.selectbox("Prioridade", ["Alta", "Média", "Baixa"])
            status_inicial = c2.selectbox("Status Inicial", ["Pendente", "Em Andamento", "Concluído"])

            if st.form_submit_button("💾 Salvar Tarefa"):
                df_t_atual = carregar_dados_tarefas()
                nova_t = {"Tarefa": tarefa, "Descricao": desc, "Status": status_inicial,
                          "Prioridade": prioridade, "Data_Criacao": datetime.date.today()}
                salvar_tarefas(pd.concat([df_t_atual, pd.DataFrame([nova_t])], ignore_index=True))
                st.success("Tarefa adicionada!")
                st.rerun()

    if df_t.empty:
        st.info("Nenhuma tarefa cadastrada. Adicione uma meta acima para começar!")
        return

    # --- KANBAN BOARD ---
    st.subheader("Visualização Kanban")
    col_pendente, col_andamento, col_concluido = st.columns(3)

    # Função auxiliar para criar cards
    def criar_card(task_series, idx):
        cor_pri = {"Alta": "🔴", "Média": "🟡", "Baixa": "🟢"}.get(task_series['Prioridade'], "⚪")
        with st.container(border=True):
            st.markdown(f"**{cor_pri} {task_series['Tarefa']}**")
            if str(task_series['Descricao']).strip() and str(task_series['Descricao']).strip() != "nan":
                st.caption(task_series['Descricao'])
            
            # Selectbox para mudar status localmente no card
            novo_status = st.selectbox("Mover para:", ["Pendente", "Em Andamento", "Concluído"], 
                                      index=["Pendente", "Em Andamento", "Concluído"].index(task_series['Status']),
                                      key=f"status_{idx}", label_visibility="collapsed")
            
            if novo_status != task_series['Status']:
                df_t.at[idx, 'Status'] = novo_status
                salvar_tarefas(df_t)
                st.rerun()

    with col_pendente:
        st.markdown("### 📝 Pendente")
        df_p = df_t[df_t['Status'] == 'Pendente']
        for idx, row in df_p.iterrows():
            criar_card(row, idx)

    with col_andamento:
        st.markdown("### ⏳ Em Andamento")
        df_a = df_t[df_t['Status'] == 'Em Andamento']
        for idx, row in df_a.iterrows():
            criar_card(row, idx)

    with col_concluido:
        st.markdown("### ✅ Concluído")
        df_c = df_t[df_t['Status'] == 'Concluído']
        for idx, row in df_c.iterrows():
            criar_card(row, idx)



def pagina_configuracoes():
    st.title("⚙️ Configurações do Portal")
    st.subheader("Gerenciar Dados Locais")
    st.warning("Atenção: as ações abaixo apagam dados permanentemente.")

    col1, col2 = st.columns(2)
    if col1.button("🔥 Resetar Questões"):
        if os.path.exists(ARQUIVO_QUESTOES):
            os.remove(ARQUIVO_QUESTOES)
            _garantir_arquivos()
            st.cache_data.clear()
            st.success("Dados de questões resetados.")

    if col2.button("🔥 Resetar Tarefas"):
        if os.path.exists(ARQUIVO_TAREFAS):
            os.remove(ARQUIVO_TAREFAS)
            _garantir_arquivos()
            st.cache_data.clear()
            st.success("Dados de tarefas resetados.")


# --- ROTEAMENTO ---
if opcao == "📊 Dashboard":
    pagina_dashboard()
elif opcao == "✍️ Praticar Questões":
    pagina_questoes()
elif opcao == "📋 Tarefas":
    pagina_tarefas()
elif opcao == "⚙️ Configurações":
    pagina_configuracoes()
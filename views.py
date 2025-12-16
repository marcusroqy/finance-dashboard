import streamlit as st
import plotly.express as px

def render_overview_tab(monthly_flow, df_filtered, kpi_data):
    """Renderiza aba de Visão Geral (KPIs + Fluxo Mensal + Top Despesas)."""
    
    # 1. KPIs Globais (Movido para cá)
    entradas, saidas, saidas_abs, saldo, taxa_poupanca, delta_entradas, delta_saidas, meta_gastos = kpi_data
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Receitas", f"R$ {entradas:,.2f}", delta=f"{delta_entradas:+.1f}% vs Anterior")
    col2.metric("Despesas", f"R$ {saidas:,.2f}", delta=f"{delta_saidas:+.1f}% vs Anterior", delta_color="inverse")
    col3.metric("Saldo Líquido", f"R$ {saldo:,.2f}", delta=f"{taxa_poupanca:.1f}% Poupado")
    
    # Média Diária (Estimativa simples)
    days_range = (df_filtered['Data'].max() - df_filtered['Data'].min()).days + 1 if not df_filtered.empty else 1
    media_diaria = saidas_abs / days_range if days_range > 0 else 0
    col4.metric("Média Diária", f"R$ {media_diaria:,.2f}")
    
    if meta_gastos > 0:
        st.markdown("###")
        st.write(f"**Progresso da Meta:** R$ {saidas_abs:,.2f} / R$ {meta_gastos:,.2f}")
        percent = min(saidas_abs / meta_gastos, 1.0)
        st.progress(percent)
        
    st.divider()

    # 2. Gráficos (Fluxo e Top 5)
    col_main, col_detail = st.columns([2, 1])
    
    with col_main:
        fig_fluxo = px.bar(
            monthly_flow, x='Mes_Ano', y='Valor', color='Fluxo', barmode='group',
            color_discrete_map={'Entrada': '#2ECEC0', 'Saída': '#FF5A5F'},
            title="<b>Fluxo de Caixa Mensal</b>",
            text_auto='.2s', template='plotly_white'
        )
        fig_fluxo.update_traces(hovertemplate='%{y:,.2f}')
        fig_fluxo.update_layout(yaxis_title=None, xaxis_title=None, legend_title=None)
        st.plotly_chart(fig_fluxo, use_container_width=True)

    with col_detail:
        st.markdown("##### 🚨 Top 5 Despesas")
        top_expenses = df_filtered[df_filtered['Valor'] < 0].nsmallest(5, 'Valor')
        for _, row in top_expenses.iterrows():
            st.warning(f"**{row['Descrição']}**\n\nR$ {row['Valor']:,.2f} ({row['Data'].strftime('%d/%m')})")

import transform

def render_categories_tab(categories_ranking, expenses_df):
    """Renderiza aba de Categorias com Interatividade Master-Detail."""
    if not expenses_df.empty:
        # Layout: 70% Gráfico (Master), 30% Detalhes (Detail)
        col_cat1, col_cat2 = st.columns([2, 1])
        
        with col_cat1:
            st.markdown("### 📊 Ranking de Gastos")
            st.caption("Clique em uma barra para ver os detalhes da categoria.")
            
            fig_bar_cat = px.bar(
                categories_ranking, 
                orientation='h',
                title="",
                text_auto='.2s',
                color_discrete_sequence=['#4A90E2'],
                template='plotly_white'
            )
            fig_bar_cat.update_traces(hovertemplate='<b>%{y}</b><br>R$ %{x:,.2f}')
            fig_bar_cat.update_layout(
                yaxis_title=None, 
                xaxis_title="Total Gasto (R$)",
                margin=dict(l=0, r=0, t=0, b=0),
                height=400
            )
            
            # --- INTERATIVIDADE ---
            # on_select="rerun" faz o app rodar de novo quando clica
            event = st.plotly_chart(fig_bar_cat, use_container_width=True, on_select="rerun", selection_mode="points")
            
        with col_cat2:
            st.markdown("### 🔎 Detalhes")
            
            selected_category = None
            if event and event["selection"]["points"]:
                # Pega o Label Y do ponto clicado (que é a Categoria)
                point = event["selection"]["points"][0]
                selected_category = point["y"]
            
            if selected_category:
                st.info(f"**Categoria Selecionada:** {selected_category}")
                
                # Busca dados detalhados usando módulo transform
                grouped_details, raw_details = transform.get_category_details(expenses_df, selected_category)
                
                # Se for Transferências/Pix, tenta mostrar beneficiários
                if selected_category == 'Transferências' or selected_category == 'Pix Enviado':
                     st.caption("Principais Beneficiários:")
                else:
                     st.caption("Principais Descrições:")

                st.dataframe(
                    grouped_details[['Descrição', 'Valor Abs']].rename(columns={'Valor Abs': 'Valor'}),
                    column_config={
                        "Valor": st.column_config.NumberColumn(format="R$ %.2f"),
                    },
                    use_container_width=True,
                    height=300,
                    hide_index=True
                )
                
            else:
                st.info("👆 **Clique em uma barra** ao lado para ver o que compõe aquele gasto.")
                st.markdown("""
                <div style='text-align: center; color: #ccc; margin-top: 50px;'>
                    <span style='font-size: 3rem;'>🕵️</span><br>
                    Selecione uma categoria
                </div>
                """, unsafe_allow_html=True)

    else:
        st.info("Sem despesas para exibir.")

def render_pix_tab(pix_only, pix_rank, total_pix, qtd_pix, avg_pix, max_pix):
    """Renderiza aba de Pix (Métricas, Gráficos e Export)."""
    if pix_only is not None and not pix_only.empty:
        p1, p2, p3, p4 = st.columns(4)
        p1.metric("💸 Total Enviado", f"R$ {total_pix:,.2f}")
        p2.metric("🔢 Qtd. Transações", f"{qtd_pix}")
        p3.metric("📏 Ticket Médio", f"R$ {avg_pix:,.2f}")
        p4.metric("🔝 Maior Envio", f"R$ {max_pix:,.2f}")
        
        st.divider()
        
        col_pix1, col_pix2 = st.columns([1.5, 1])
        
        with col_pix1:
            st.markdown("##### 📈 Evolução dos Envios por Dia")
            pix_daily = pix_only.groupby('Data')['Valor Abs'].sum().reset_index()
            fig_pix_line = px.line(pix_daily, x='Data', y='Valor Abs', markers=True, template="plotly_white")
            fig_pix_line.update_traces(hovertemplate='<b>%{x|%d/%m/%Y}</b><br>R$ %{y:,.2f}<extra></extra>')
            fig_pix_line.update_layout(yaxis_title="Valor (R$)", xaxis_title=None)
            st.plotly_chart(fig_pix_line, use_container_width=True)

            st.markdown("##### 🏆 Ranking de Beneficiários")
            fig_pix_bar = px.bar(pix_rank, orientation='h', text_auto='.2s', template="plotly_white", color_discrete_sequence=['#EF553B'])
            fig_pix_bar.update_traces(hovertemplate='<b>%{y}</b><br>Total: R$ %{x:,.2f}<extra></extra>')
            fig_pix_bar.update_layout(yaxis_title=None, xaxis_title="Total (R$)")
            st.plotly_chart(fig_pix_bar, use_container_width=True)
            
        with col_pix2:
            st.markdown("##### 💾 Exportar Dados")
            csv_pix = pix_only[['Data', 'Descrição', 'Beneficiario_Pix', 'Valor Abs']].to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Baixar Relatório Pix (CSV)",
                data=csv_pix,
                file_name="relatorio_pix.csv",
                mime="text/csv",
                use_container_width=True
            )
            
            st.markdown("---")
            st.markdown("##### 📝 Últimas Transações")
            st.dataframe(
                pix_only[['Data', 'Beneficiario_Pix', 'Valor Abs']].sort_values('Data', ascending=False)
                .style.format({'Valor Abs': 'R$ {:,.2f}', 'Data': '{:%d/%m}'}),
                use_container_width=True,
                height=400
            )

    else:
        st.info("Nenhuma transferência Pix enviada identificada.")

def render_extract_tab(df_filtered):
    """Renderiza editor de dados interativo."""
    st.markdown("### 📝 Extrato Editável")
    
    # Garante que a coluna Banco existe (para compatibilidade com função antiga)
    cols_to_show = ['Data', 'Banco', 'Descrição', 'Categoria', 'Valor']
    if 'Banco' not in df_filtered.columns:
        cols_to_show.remove('Banco')
        
    edited = st.data_editor(
        df_filtered[cols_to_show].sort_values('Data', ascending=False),
        column_config={
            "Valor": st.column_config.NumberColumn(format="R$ %.2f"),
            "Data": st.column_config.DatetimeColumn(format="DD/MM/YYYY"),
            "Banco": st.column_config.TextColumn("Instituição"),
        },
        use_container_width=True, num_rows="dynamic", height=500
    )

def render_budget_tab(df, budgets, username):
    """Renderiza a aba de Metas de Gastos."""
    import budget_manager  # Import local
    
    col1, col2 = st.columns([2, 1])
    
    with col2:
        with st.container(border=True):
            st.markdown("### 🎯 Definir Meta")
            
            # Lista de categorias disponíveis
            all_cats = sorted(df['Categoria'].unique().tolist())
            if not all_cats:
                st.warning("Sem categorias para definir metas.")
                return

            cat_to_edit = st.selectbox("Escolha a Categoria", all_cats, key="budget_cat_sel")
            
            # Valor atual (se existir)
            current_val = budgets.get(cat_to_edit, 0.0)
            new_val = st.number_input("Limite Mensal (R$)", min_value=0.0, value=float(current_val), step=50.0, key="budget_val_in")
            
            if st.button("💾 Salvar Meta", use_container_width=True):
                # Salva
                updated_budgets = budget_manager.save_budget(username, cat_to_edit, new_val)
                st.success(f"Meta de {cat_to_edit} atualizada!")
                st.rerun() # Recarrega para atualizar visualização
                
    with col1:
        st.markdown("### 📊 Acompanhamento Mensal")
        
        if not budgets:
            st.info("👈 Defina sua primeira meta ao lado!")
        
        # Totais
        total_budget = sum(budgets.values())
        total_spent_general = df[df['Valor'] < 0]['Valor'].abs().sum()
        
        # Mostra barra geral se houver metas
        if total_budget > 0:
            st.caption(f"Visão Geral: R$ {total_spent_general:,.2f} gastos de R$ {total_budget:,.2f} previstos")
            overall_prog = min(total_spent_general / total_budget, 1.0)
            st.progress(overall_prog)
        
        st.markdown("---")
        
        # Renderiza barra por categoria meta
        # Calcula gastos por categoria
        spent_by_cat = df[df['Valor'] < 0].groupby('Categoria')['Valor'].sum().abs()
        
        # Ordena: Quem está mais perto de estourar aparece primeiro
        # Lista de tuplas (cat, %usage)
        cat_usage = []
        for cat, limit in budgets.items():
            spent = spent_by_cat.get(cat, 0.0)
            usage = spent / limit if limit > 0 else 0
            cat_usage.append((cat, limit, spent, usage))
            
        # Sort descending by usage
        cat_usage.sort(key=lambda x: x[3], reverse=True)
        
        for cat, limit, spent, usage in cat_usage:
            # Cor da barra e texto
            if usage >= 1.0:
                color = "red" # Estourou
                emoji = "🚨"
            elif usage >= 0.8:
                color = "orange" # Alerta
                emoji = "⚠️"
            else:
                color = "green" # Ok
                emoji = "✅"
                
            col_txt, col_bar = st.columns([1, 2])
            with col_txt:
                st.markdown(f"**{cat}** {emoji}")
                st.caption(f"R$ {spent:,.0f} / {limit:,.0f}")
                
            with col_bar:
                # Progress bar nativa não aceita cor diretamente facilmente sem CSS hack ou novas versões, 
                # mas podemos usar st.progress simples e contar com o emoji/contexto.
                # Ou usar Markdown HTML para cor. Vamos de st.progress padrão por enquanto + Markdown se crítico.
                # Hack visual: :red[...] no texto ajuda.
                st.progress(min(usage, 1.0))
                if usage > 1.0:
                    st.caption(f":red[Excedido em R$ {spent - limit:,.2f}]")

def render_manager_tab(username):
    """Renderiza a aba do Gestor de Contas (Listas Compartilhadas)."""
    import bills_manager
    from datetime import datetime, timedelta
    import calendar
    
    # --- SESSION STATE INIT ---
    if 'manager_view' not in st.session_state:
        st.session_state['manager_view'] = 'list_selection'
    if 'current_list_id' not in st.session_state:
        st.session_state['current_list_id'] = None
    if 'manager_ref_date' not in st.session_state:
        st.session_state['manager_ref_date'] = datetime.today().replace(day=1)

    # ==========================
    # VIEW 1: SELEÇÃO DE LISTA
    # ==========================
    if st.session_state['manager_view'] == 'list_selection':
        st.markdown("### 📂 Suas Listas")
        st.caption("Selecione um grupo ou crie um novo para começar.")
        
        col_lists, col_actions = st.columns([2, 1])
        
        with col_actions:
            with st.container(border=True):
                st.markdown("##### Nova Lista")
                tab1, tab2 = st.tabs(["Criar", "Entrar"])
                with tab1:
                    new_name = st.text_input("Nome", placeholder="Ex: Casa", key="new_list_name")
                    if st.button("Criar", type="primary", use_container_width=True):
                        if new_name:
                            _, code = bills_manager.create_list(new_name, username)
                            st.success(f"Criado! Código: {code}")
                            st.rerun()
                with tab2:
                    code_in = st.text_input("Código", placeholder="ABC123", key="join_code")
                    if st.button("Entrar", use_container_width=True):
                        ok, msg = bills_manager.join_list(code_in, username)
                        if ok: st.success(msg); st.rerun()
                        else: st.error(msg)
        
        with col_lists:
            my_lists = bills_manager.get_user_lists(username)
            if not my_lists:
                st.info("👋 Você ainda não participa de nenhuma lista.")
            else:
                for l in my_lists:
                    with st.container(border=True):
                         c1, c2 = st.columns([5, 1])
                         c1.markdown(f"#### 📁 {l['name']}")
                         if c2.button("Abrir", key=f"open_{l['id']}", use_container_width=True):
                             st.session_state['current_list_id'] = l['id']
                             st.session_state['manager_view'] = 'list_details'
                             st.rerun()

    # ===============================
    # VIEW 2: DETALHES DA LISTA (DASH)
    # ===============================
    elif st.session_state['manager_view'] == 'list_details':
        list_id = st.session_state['current_list_id']
        list_data = bills_manager.get_list_details(list_id)
        
        if not list_data:
            st.error("Lista não encontrada.")
            if st.button("Voltar"):
                st.session_state['manager_view'] = 'list_selection'
                st.rerun()
            return

        # --- HEADER (Navigation & Info) ---
        c_back, c_title, c_code = st.columns([1, 4, 2])
        if c_back.button("🔙 Voltar"):
            st.session_state['manager_view'] = 'list_selection'
            st.rerun()
            
        c_title.markdown(f"## 🏘️ {list_data['name']}")
        c_code.markdown(f"🔑 **{list_data['invite_code']}** (Convite)")
        
        st.divider()
        
        # --- MONTH NAVIGATION ---
        ref_date = st.session_state['manager_ref_date']
        col_nav1, col_nav2, col_nav3 = st.columns([1, 2, 1])
        
        with col_nav1:
            if st.button("◀️ Anterior", use_container_width=True):
                nm = ref_date.month - 1
                ny = ref_date.year
                if nm == 0: nm=12; ny-=1
                st.session_state['manager_ref_date'] = ref_date.replace(year=ny, month=nm)
                st.rerun()
                
        with col_nav2:
             pt_months = ["", "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
             month_display = f"{pt_months[ref_date.month]} {ref_date.year}"
             st.markdown(f"<h3 style='text-align: center; margin: 0; color: #4A90E2;'>{month_display}</h3>", unsafe_allow_html=True)
             
        with col_nav3:
            if st.button("Próximo ▶️", use_container_width=True):
                nm = ref_date.month + 1
                ny = ref_date.year
                if nm == 13: nm=1; ny+=1
                st.session_state['manager_ref_date'] = ref_date.replace(year=ny, month=nm)
                st.rerun()

        st.markdown("###") # Spacer

        # --- DATA FILTERING ---
        bills_all = list_data.get('bills', [])
        bills = []
        for b in bills_all:
             try:
                 bd = datetime.strptime(b['due_date'], "%Y-%m-%d").date()
                 if bd.year == ref_date.year and bd.month == ref_date.month:
                     bills.append(b)
             except: pass
        
        # --- KPIS & CARDS ---
        today = datetime.today().date()
        overdue = [b for b in bills if b['status'] != 'PAID' and datetime.strptime(b['due_date'], "%Y-%m-%d").date() < today]
        paid = [b for b in bills if b['status'] == 'PAID']
        pending = [b for b in bills if b['status'] != 'PAID' and b not in overdue] # Future pending
        next7 = [b for b in pending if today <= datetime.strptime(b['due_date'], "%Y-%m-%d").date() <= today + timedelta(days=7)]
        
        val_pending = sum(b['amount'] for b in overdue + pending)
        
        k1, k2, k3, k4 = st.columns(4)
        
        def _kpi_card(col, label, val, color="#FFF"):
            col.markdown(f"""
            <div style="border: 1px solid #333; border-radius: 8px; padding: 10px; text-align: center; background-color: #1E1E1E;">
                <span style="color: #888; font-size: 0.8rem;">{label}</span><br>
                <span style="color: {color}; font-size: 1.2rem; font-weight: bold;">{val}</span>
            </div>
            """, unsafe_allow_html=True)
            
        _kpi_card(k1, "Total Itens", len(bills))
        _kpi_card(k2, "Atrasados", len(overdue), "#FF4B4B" if overdue else "#FFF")
        _kpi_card(k3, "Próximos 7 Dias", len(next7), "#FFAE00" if next7 else "#FFF")
        _kpi_card(k4, "Valor Pendente", f"R$ {val_pending:,.2f}", "#6495ED")

        st.markdown("---")

        # --- ACTIONS SECTION ---
        ac1, ac2 = st.columns([3, 1])
        search = ac1.text_input("🔍 Buscar conta...", label_visibility="collapsed")
        
        # Use Expander instead of Popover for robustness
        with ac2:
            with st.expander("➕ Adicionar Item", expanded=False):
                with st.form("new_bill_simple"):
                    st.caption("Nova Conta")
                    n_name = st.text_input("Nome")
                    n_val = st.number_input("Valor", min_value=0.0, step=10.0)
                    n_due = st.date_input("Vencimento", value=datetime.today())
                    n_assignee = st.selectbox("Responsável", list_data['members'], index=0)
                    
                    if st.form_submit_button("Salvar"):
                        if not n_name:
                            st.error("Nome obrigatório")
                        else:
                            payload = {
                                "name": n_name,
                                "amount": n_val,
                                "due_date": n_due.strftime("%Y-%m-%d"),
                                "status": "PENDING",
                                "assignee": n_assignee
                            }
                            ok, msg = bills_manager.save_bill(list_id, payload, username)
                            if ok:
                                st.success("Salvo!")
                                st.rerun()
                            else:
                                st.error(msg)

        if search:
            bills = [b for b in bills if search.lower() in b['name'].lower()]
            # Filter sub-lists again
            overdue = [b for b in bills if b in overdue]
            pending = [b for b in bills if b in pending]
            paid = [b for b in bills if b in paid]

        # --- MAIN CONTENT ---
        main_col, side_col = st.columns([3, 1])
        
        # SIDEBAR: SPLIT
        with side_col:
            st.markdown("### 📊 Divisão")
            with st.container(border=True):
                # Calculate per assignee
                stats = {}
                for b in bills:
                    who = b.get('assignee', 'N/A')
                    if who not in stats: stats[who] = {'total':0, 'paid':0}
                    stats[who]['total'] += b['amount']
                    if b['status'] == 'PAID': stats[who]['paid'] += b['amount']
                
                if not stats:
                    st.caption("Sem dados.")
                
                for p, s in stats.items():
                    pend = s['total'] - s['paid']
                    st.markdown(f"**{p.split('@')[0]}**")
                    if pend > 0:
                        st.caption(f"Falta pagar: :red[R$ {pend:,.2f}]")
                    else:
                        st.caption(":green[Quitado!]")
                    st.progress(s['paid']/s['total'] if s['total'] > 0 else 0)
                    st.divider()

        # ROWS: BILLS
        with main_col:
            # Helper for rows
            def _render_row(b, style="default"):
                bid = b['id']
                bname = b['name']
                bamt = b['amount']
                bdate = datetime.strptime(b['due_date'], "%Y-%m-%d").strftime("%d/%m")
                bassign = b.get('assignee', '').split('@')[0]
                
                # Styles
                border_c = "#333"
                if style == "overdue": border_c = "#FF4B4B"
                elif style == "paid": border_c = "#2ECC71"
                
                with st.container(border=True):
                    # Hack CSS local if possible or just standard cols
                    c1, c2, c3, c4 = st.columns([3, 2, 2, 1.5])
                    c1.markdown(f"**{bname}**")
                    c1.caption(f"👤 {bassign}")
                    
                    c2.markdown(f"📅 {bdate}")
                    c3.markdown(f"R$ {bamt:,.2f}")
                    
                    with c4:
                        if style == "paid":
                            if st.button("↩️", key=f"rev_{bid}"):
                                bills_manager.toggle_status(list_id, bid, "PENDING")
                                st.rerun()
                        else:
                            if st.button("✅", key=f"pay_{bid}"):
                                bills_manager.toggle_status(list_id, bid, "PAID")
                                st.rerun()
                            if st.button("🗑️", key=f"del_{bid}"):
                                bills_manager.delete_bill(list_id, bid)
                                st.rerun()

            if overdue:
                st.markdown("#### 🚨 Atrasados")
                for x in overdue: _render_row(x, "overdue")
            
            st.markdown("#### 📅 Pendentes")
            if pending:
                for x in pending: _render_row(x, "default")
            elif not overdue:
                st.info("Nada pendente!")
                
            if paid:
                with st.expander(f"Pagos ({len(paid)})"):
                    for x in paid: _render_row(x, "paid")

def _render_bill_card_v2(bill, list_id, username, type):
    pass # Deprecated/Merged above


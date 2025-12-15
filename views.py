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

import streamlit as st
import pandas as pd

st.set_page_config(page_title="Rateio TI", layout="wide")

st.title("📊 Rateio de Licenças - Afonso França")

# Upload do arquivo
arquivo = st.file_uploader("📁 Suba sua planilha (CSV ou Excel)", type=["csv", "xlsx"])

if arquivo:
    # Ler arquivo
    if arquivo.name.endswith(".csv"):
        df = pd.read_csv(arquivo)
    else:
        df = pd.read_excel(arquivo)

    st.success("Arquivo carregado com sucesso!")

    # Mostrar colunas
    st.write("Colunas encontradas:", df.columns.tolist())

    # Verificar coluna Office
    if "Office" not in df.columns:
        st.error("A planilha precisa ter a coluna 'Office'")
    else:
        # Valor da fatura
        valor_total = st.number_input("💰 Valor total da fatura (R$)", min_value=0.0)

        if valor_total > 0:

            # Criar coluna de custo (se não existir)
            if "Custo (R$)" not in df.columns:
                df["Custo (R$)"] = 1

            # Agrupar por Office
            resumo = df.groupby("Office").agg(
                qtd_usuarios=("Office", "count"),
                custo_calculado=("Custo (R$)", "sum")
            ).reset_index()

            total_calculado = resumo["custo_calculado"].sum()

            resumo["percentual"] = resumo["custo_calculado"] / total_calculado
            resumo["valor_rateado"] = resumo["percentual"] * valor_total

            st.subheader("📊 Resultado do Rateio")

            for _, row in resumo.iterrows():
                st.success(
                    f"Centro de Custo {row['Office']} tem {int(row['qtd_usuarios'])} usuário(s), "
                    f"totalizando R$ {row['valor_rateado']:.2f}"
                )

            # Download Excel
            output = resumo.copy()
            output = output[["Office", "qtd_usuarios", "valor_rateado"]]

            output.columns = ["Centro de Custo", "Qtd Usuários", "Valor Rateado (R$)"]

            excel = output.to_excel(index=False)

            st.download_button(
                label="📥 Baixar Excel",
                data=excel,
                file_name="rateio.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
import streamlit as st
import pandas as pd
from io import BytesIO

st.set_page_config(page_title="Rateio TI", layout="wide")

st.title("📊 Rateio de Licenças - Afonso França")


def converter_valor_brl(texto):
    if not texto:
        return 0.0
    texto = str(texto).strip()
    texto = texto.replace("R$", "").replace(" ", "")
    texto = texto.replace(".", "").replace(",", ".")
    return float(texto)


def formatar_brl(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def identificar_empresa_por_office(office):
    if pd.isna(office):
        return "Não identificada"

    office = str(office).strip()
    prefixo = office[:2]

    mapa = {
        "01": "Afonso França",
        "02": "AFFIT",
        "03": "AFDI",
        "04": "AFSW",
    }

    return mapa.get(prefixo, "Não identificada")


arquivo = st.file_uploader("📁 Suba sua planilha (CSV ou Excel)", type=["csv", "xlsx"])

if arquivo:
    if arquivo.name.endswith(".csv"):
        df = pd.read_csv(arquivo)
    else:
        df = pd.read_excel(arquivo)

    st.success("Arquivo carregado com sucesso!")
    st.write("Colunas encontradas:", df.columns.tolist())

    if "Office" not in df.columns:
        st.error("A planilha precisa ter a coluna 'Office'")
        st.stop()

    # Cria/normaliza a coluna Empresa
    if "Empresa" not in df.columns:
        df["Empresa"] = df["Office"].apply(identificar_empresa_por_office)
    else:
        df["Empresa"] = df["Empresa"].fillna("")
        df.loc[df["Empresa"].astype(str).str.strip() == "", "Empresa"] = df["Office"].apply(identificar_empresa_por_office)

    # Garante coluna de custo
    if "Custo (R$)" not in df.columns:
        df["Custo (R$)"] = 1

    df["Custo (R$)"] = pd.to_numeric(df["Custo (R$)"], errors="coerce").fillna(0)

    # Campo valor total
    valor_total_input = st.text_input(
        "💰 Valor total da fatura (R$)",
        placeholder="Ex.: 168.610,17"
    )

    try:
        valor_total = converter_valor_brl(valor_total_input)
    except:
        valor_total = 0.0
        if valor_total_input:
            st.error("Digite o valor no formato 168.610,17")

    # Seletor de empresa
    empresas_disponiveis = sorted(df["Empresa"].dropna().astype(str).unique().tolist())
    opcoes_empresa = ["Todas"] + empresas_disponiveis

    empresa_selecionada = st.selectbox(
        "🏢 Selecione a empresa",
        options=opcoes_empresa
    )

    # Filtra empresa
    if empresa_selecionada == "Todas":
        df_filtrado = df.copy()
    else:
        df_filtrado = df[df["Empresa"] == empresa_selecionada].copy()

    st.subheader("📋 Prévia dos dados filtrados")
    st.dataframe(df_filtrado.head(20), use_container_width=True)

    if valor_total > 0:
        resumo = df_filtrado.groupby(["Empresa", "Office"]).agg(
            qtd_usuarios=("Office", "count"),
            custo_calculado=("Custo (R$)", "sum")
        ).reset_index()

        total_calculado = resumo["custo_calculado"].sum()

        if total_calculado == 0:
            st.error("A soma da coluna 'Custo (R$)' está zerada.")
        else:
            resumo["percentual"] = resumo["custo_calculado"] / total_calculado
            resumo["valor_rateado"] = resumo["percentual"] * valor_total
            resumo["valor_rateado"] = resumo["valor_rateado"].round(2)

            st.subheader("📊 Resultado do Rateio")

            total_usuarios = int(resumo["qtd_usuarios"].sum())
            total_centros = int(resumo["Office"].nunique())

            col1, col2, col3 = st.columns(3)
            col1.metric("Empresa selecionada", empresa_selecionada)
            col2.metric("Centros de custo", total_centros)
            col3.metric("Usuários considerados", total_usuarios)

            for _, row in resumo.iterrows():
                st.success(
                    f"Empresa {row['Empresa']} | Centro de Custo {row['Office']} tem "
                    f"{int(row['qtd_usuarios'])} usuário(s), totalizando {formatar_brl(row['valor_rateado'])}"
                )

            output = resumo[["Empresa", "Office", "qtd_usuarios", "valor_rateado"]].copy()
            output.columns = ["Empresa", "Centro de Custo", "Qtd Usuários", "Valor Rateado (R$)"]

            st.subheader("📑 Tabela final")
            st.dataframe(output, use_container_width=True)

            buffer = BytesIO()
            with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                output.to_excel(writer, index=False, sheet_name="Rateio")
                df_filtrado.to_excel(writer, index=False, sheet_name="Base_Filtrada")

            st.download_button(
                label="📥 Baixar Excel",
                data=buffer.getvalue(),
                file_name="rateio.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

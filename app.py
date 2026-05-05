import streamlit as st
import pandas as pd
from io import BytesIO

st.set_page_config(page_title="Rateio TI", layout="wide")

st.title("📊 Rateio de Licenças - Afonso França")


def converter_valor_brl(texto):
    if pd.isna(texto) or texto == "":
        return 0.0

    texto = str(texto).strip()
    texto = texto.replace("R$", "").replace(" ", "")

    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")

    try:
        return float(texto)
    except:
        return 0.0


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


arquivo = st.file_uploader(
    "📁 Suba sua planilha CSV ou Excel",
    type=["csv", "xlsx"]
)

if arquivo:
    if arquivo.name.endswith(".csv"):
        df = pd.read_csv(arquivo)
    else:
        df = pd.read_excel(arquivo)

    st.success("Arquivo carregado com sucesso!")
    st.write("Colunas encontradas:", df.columns.tolist())

    colunas_obrigatorias = ["Office", "Valor licenças (R$)"]

    for coluna in colunas_obrigatorias:
        if coluna not in df.columns:
            st.error(f"A planilha precisa ter a coluna '{coluna}'")
            st.stop()

    if "Empresa" not in df.columns:
        df["Empresa"] = df["Office"].apply(identificar_empresa_por_office)
    else:
        df["Empresa"] = df["Empresa"].fillna("")
        df.loc[df["Empresa"].astype(str).str.strip() == "", "Empresa"] = (
            df["Office"].apply(identificar_empresa_por_office)
        )

    if "Detalhamento do cálculo" not in df.columns:
        df["Detalhamento do cálculo"] = ""

    df["Valor licenças (R$)"] = df["Valor licenças (R$)"].apply(converter_valor_brl)

    valor_total_input = st.text_input(
        "💰 Valor total da fatura (R$)",
        placeholder="Ex.: 168.610,17"
    )

    valor_total = converter_valor_brl(valor_total_input)

    empresas_disponiveis = sorted(df["Empresa"].dropna().astype(str).unique().tolist())
    opcoes_empresa = ["Todas"] + empresas_disponiveis

    empresa_selecionada = st.selectbox(
        "🏢 Selecione a empresa",
        options=opcoes_empresa
    )

    if empresa_selecionada == "Todas":
        df_filtrado = df.copy()
    else:
        df_filtrado = df[df["Empresa"] == empresa_selecionada].copy()

    st.subheader("📋 Prévia dos dados filtrados")
    st.dataframe(df_filtrado.head(20), use_container_width=True)

    if valor_total > 0:
        resumo = df_filtrado.groupby(["Empresa", "Office"]).agg(
            qtd_usuarios=("Office", "count"),
            valor_licencas=("Valor licenças (R$)", "sum"),
            detalhamento=(
                "Detalhamento do cálculo",
                lambda x: " | ".join(
                    x.dropna().astype(str).str.strip().replace("", pd.NA).dropna().unique()
                )
            )
        ).reset_index()

        total_licencas = resumo["valor_licencas"].sum()

        if total_licencas == 0:
            st.error("A soma da coluna 'Valor licenças (R$)' está zerada.")
            st.stop()

        diferenca_fatura = valor_total - total_licencas

        resumo["percentual"] = resumo["valor_licencas"] / total_licencas
        resumo["ajuste_rateado"] = resumo["percentual"] * diferenca_fatura
        resumo["valor_final_rateado"] = resumo["valor_licencas"] + resumo["ajuste_rateado"]

        resumo["valor_licencas"] = resumo["valor_licencas"].round(2)
        resumo["ajuste_rateado"] = resumo["ajuste_rateado"].round(2)
        resumo["valor_final_rateado"] = resumo["valor_final_rateado"].round(2)
        resumo["percentual"] = (resumo["percentual"] * 100).round(2)

        st.subheader("📊 Resultado do Rateio")

        total_usuarios = int(resumo["qtd_usuarios"].sum())
        total_centros = int(resumo["Office"].nunique())

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Empresa selecionada", empresa_selecionada)
        col2.metric("Centros de custo", total_centros)
        col3.metric("Usuários considerados", total_usuarios)
        col4.metric("Diferença rateada", formatar_brl(diferenca_fatura))

        st.info(f"Total das licenças na planilha: {formatar_brl(total_licencas)}")
        st.info(f"Valor total da fatura: {formatar_brl(valor_total)}")

        for _, row in resumo.iterrows():
            st.success(
                f"Empresa {row['Empresa']} | Centro de Custo {row['Office']} possui "
                f"{int(row['qtd_usuarios'])} usuário(s), "
                f"licenças no valor de {formatar_brl(row['valor_licencas'])}, "
                f"ajuste de {formatar_brl(row['ajuste_rateado'])}, "
                f"totalizando {formatar_brl(row['valor_final_rateado'])}."
            )

        output = resumo[[
            "Empresa",
            "Office",
            "qtd_usuarios",
            "valor_licencas",
            "percentual",
            "ajuste_rateado",
            "valor_final_rateado",
            "detalhamento"
        ]].copy()

        output.columns = [
            "Empresa",
            "Centro de Custo",
            "Qtd Usuários",
            "Valor das Licenças (R$)",
            "Percentual (%)",
            "Ajuste Rateado (R$)",
            "Valor Final Rateado (R$)",
            "Detalhamento do Cálculo"
        ]

        st.subheader("📑 Tabela final")
        st.dataframe(output, use_container_width=True)

        buffer = BytesIO()

        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            output.to_excel(writer, index=False, sheet_name="Rateio")
            df_filtrado.to_excel(writer, index=False, sheet_name="Base_Filtrada")

        st.download_button(
            label="📥 Baixar Excel",
            data=buffer.getvalue(),
            file_name="rateio_licencas.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.warning("Informe o valor total da fatura para calcular o rateio.")

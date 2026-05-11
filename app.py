import streamlit as st
import pandas as pd
from io import BytesIO
import unicodedata

st.set_page_config(page_title="Rateio TI", layout="wide")

st.title("📊 Rateio de Licenças - Afonso França")


def normalizar_coluna(col):
    col = str(col).strip().lower()
    col = ''.join(
        c for c in unicodedata.normalize('NFD', col)
        if unicodedata.category(c) != 'Mn'
    )
    return col


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


def localizar_coluna(df, opcoes):
    for opcao in opcoes:
        if opcao in df.columns:
            return opcao
    return None


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

    df.columns = [normalizar_coluna(c) for c in df.columns]

    st.write("Colunas detectadas:", df.columns.tolist())

    colunas_obrigatorias = ["office", "valor licencas (r$)"]

    for coluna in colunas_obrigatorias:
        if coluna not in df.columns:
            st.error(f"Coluna obrigatória não encontrada: '{coluna}'")
            st.stop()

    if "empresa" not in df.columns:
        df["empresa"] = df["office"].apply(identificar_empresa_por_office)
    else:
        df["empresa"] = df["empresa"].fillna("")
        df.loc[df["empresa"].astype(str).str.strip() == "", "empresa"] = (
            df["office"].apply(identificar_empresa_por_office)
        )

    if "detalhamento do calculo" not in df.columns:
        df["detalhamento do calculo"] = ""

    df["valor licencas (r$)"] = df["valor licencas (r$)"].apply(converter_valor_brl)

    coluna_nome = localizar_coluna(df, [
        "nome",
        "usuario",
        "user",
        "nome usuario",
        "nome do usuario"
    ])

    coluna_departamento = localizar_coluna(df, [
        "departament",
        "departamento",
        "department",
        "setor",
        "area"
    ])

    valor_total_input = st.text_input(
        "💰 Valor total da fatura geral (R$)",
        placeholder="Ex: 168.610,17"
    )

    valor_total = converter_valor_brl(valor_total_input)

    st.subheader("🔎 Pesquisa")

    empresas = sorted(df["empresa"].dropna().astype(str).unique().tolist())
    empresa_selecionada = st.selectbox("🏢 Empresa", ["Todas"] + empresas)

    col_f1, col_f2, col_f3 = st.columns(3)

    with col_f1:
        pesquisa_centro = st.text_input(
            "Pesquisar Centro de Custo",
            placeholder="Ex: 01.02.0607 ou PATRIA"
        )

    with col_f2:
        pesquisa_nome = st.text_input(
            "Pesquisar Nome do Usuário",
            placeholder="Ex: João, Maria..."
        )

    with col_f3:
        pesquisa_departamento = st.text_input(
            "Pesquisar Departamento",
            placeholder="Ex: TI, RH, Financeiro..."
        )

    tem_pesquisa = (
        pesquisa_centro.strip()
        or pesquisa_nome.strip()
        or pesquisa_departamento.strip()
    )

    df_consulta = df.copy()

    if empresa_selecionada != "Todas":
        df_consulta = df_consulta[df_consulta["empresa"] == empresa_selecionada]

    if pesquisa_centro.strip():
        df_consulta = df_consulta[
            df_consulta["office"]
            .astype(str)
            .str.contains(pesquisa_centro.strip(), case=False, na=False)
        ]

    if pesquisa_nome.strip():
        if coluna_nome:
            df_consulta = df_consulta[
                df_consulta[coluna_nome]
                .astype(str)
                .str.contains(pesquisa_nome.strip(), case=False, na=False)
            ]
        else:
            st.warning("Coluna de nome do usuário não encontrada.")

    if pesquisa_departamento.strip():
        if coluna_departamento:
            df_consulta = df_consulta[
                df_consulta[coluna_departamento]
                .astype(str)
                .str.contains(pesquisa_departamento.strip(), case=False, na=False)
            ]
        else:
            st.warning("Coluna de departamento não encontrada.")

    if tem_pesquisa:
        df_rateio = df_consulta.copy()
        titulo_rateio = "Resultado da Pesquisa"
    else:
        df_rateio = df.copy()
        titulo_rateio = "Rateio Geral"

        if empresa_selecionada != "Todas":
            df_rateio = df_rateio[df_rateio["empresa"] == empresa_selecionada]

    st.subheader("📋 Base Encontrada")
    st.dataframe(df_consulta.head(100), use_container_width=True)
    st.info(f"Registros encontrados: {len(df_consulta)}")

    if valor_total > 0:

        if df_rateio.empty:
            st.error("Nenhum registro encontrado para calcular.")
            st.stop()

        resumo = df_rateio.groupby(["empresa", "office"]).agg(
            qtd_usuarios=("office", "count"),
            valor_licencas=("valor licencas (r$)", "sum"),
            detalhamento=(
                "detalhamento do calculo",
                lambda x: " | ".join(
                    x.dropna()
                    .astype(str)
                    .str.strip()
                    .replace("", pd.NA)
                    .dropna()
                    .unique()
                )
            )
        ).reset_index()

        total_licencas = resumo["valor_licencas"].sum()

        if total_licencas == 0:
            st.error("Total de licenças está zerado.")
            st.stop()

        if tem_pesquisa:
            valor_base_rateio = total_licencas
            diferenca = 0
            resumo["percentual"] = 1
            resumo["ajuste"] = 0
            resumo["valor_final"] = resumo["valor_licencas"]
        else:
            valor_base_rateio = valor_total
            diferenca = valor_total - total_licencas
            resumo["percentual"] = resumo["valor_licencas"] / total_licencas
            resumo["ajuste"] = resumo["percentual"] * diferenca
            resumo["valor_final"] = resumo["valor_licencas"] + resumo["ajuste"]

        resumo["valor_licencas"] = resumo["valor_licencas"].round(2)
        resumo["ajuste"] = resumo["ajuste"].round(2)
        resumo["valor_final"] = resumo["valor_final"].round(2)
        resumo["percentual"] = (resumo["percentual"] * 100).round(2)

        output = resumo[[
            "empresa",
            "office",
            "qtd_usuarios",
            "valor_licencas",
            "percentual",
            "ajuste",
            "valor_final",
            "detalhamento"
        ]]

        output.columns = [
            "Empresa",
            "Centro de Custo",
            "Qtd Usuários",
            "Valor Licenças (R$)",
            "% Participação",
            "Ajuste (R$)",
            "Valor Final (R$)",
            "Detalhamento"
        ]

        st.subheader(f"📊 {titulo_rateio}")

        col1, col2, col3, col4 = st.columns(4)

        col1.metric("Empresa", empresa_selecionada)
        col2.metric("Centros", output["Centro de Custo"].nunique())
        col3.metric("Usuários", int(output["Qtd Usuários"].sum()))
        col4.metric("Valor Encontrado", formatar_brl(output["Valor Final (R$)"].sum()))

        st.info(f"Total de licenças encontrado: {formatar_brl(total_licencas)}")

        if not tem_pesquisa:
            st.info(f"Fatura informada: {formatar_brl(valor_total)}")
            st.info(f"Diferença rateada: {formatar_brl(diferenca)}")

        st.subheader("📑 Resultado")
        st.dataframe(output, use_container_width=True)

        st.subheader("👥 Usuários / Itens Encontrados")
        st.dataframe(df_rateio, use_container_width=True)

        buffer = BytesIO()

        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            output.to_excel(writer, index=False, sheet_name="Resultado")
            df_rateio.to_excel(writer, index=False, sheet_name="Base Encontrada")
            df.to_excel(writer, index=False, sheet_name="Base Completa")

        st.download_button(
            "📥 Baixar Excel",
            data=buffer.getvalue(),
            file_name="resultado_rateio.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    else:
        st.warning("Informe o valor da fatura para calcular.")

else:
    st.info("Suba uma planilha para iniciar.")

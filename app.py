import ssl
ssl._create_default_https_context = ssl._create_unverified_context

import os
import streamlit as st
import pandas as pd
import plotly.express as px
from dotenv import load_dotenv
from langchain_community.llms import Tongyi
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

# 加载 API Key
load_dotenv()
api_key = os.getenv("DASHSCOPE_API_KEY")

# ── 页面设置 ──
st.set_page_config(page_title="AI 数据分析助手", page_icon="📊", layout="wide")
st.title("📊 AI 数据分析助手")
st.caption("上传 Excel / CSV，用自然语言描述需求，AI 自动生成分析结论和图表")

# ── 上传文件 ──
uploaded_file = st.file_uploader("上传数据文件", type=["xlsx", "csv"])

if uploaded_file:
    # 读取数据
    if uploaded_file.name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)

    st.success(f"数据加载完成 ✅  共 {len(df)} 行 × {len(df.columns)} 列")

    # 显示数据预览
    with st.expander("📋 数据预览"):
        st.dataframe(df.head(10))

    st.divider()

    # ── 问答区域 ──
    question = st.text_input(
        "💬 请描述你想分析的内容：",
        placeholder="例如：每个地区的总销售额是多少？画一个柱状图"
    )

    if question:
        with st.spinner("AI 分析中..."):

            # 把数据结构告诉 AI
            data_info = f"""
数据共 {len(df)} 行，列名和示例数据如下：
{df.dtypes.to_string()}

前5行数据：
{df.head().to_string()}

数值列统计：
{df.describe().to_string()}
"""
            # 让 AI 生成分析结论
            llm = Tongyi(
                model_name="qwen-turbo",
                dashscope_api_key=api_key,
                temperature=0.1
            )

            prompt = PromptTemplate.from_template("""
你是一个数据分析师，根据以下数据信息回答用户的问题，给出清晰的分析结论。
回答要简洁专业，重点突出关键数字和洞察。

数据信息：
{data_info}

用户问题：{question}

分析结论：""")

            chain = prompt | llm | StrOutputParser()
            answer = chain.invoke({"data_info": data_info, "question": question})

        # 显示 AI 结论
        st.markdown("### 🤖 AI 分析结论")
        st.write(answer)

        # ── 自动生成图表 ──
        st.markdown("### 📈 数据图表")

        # 根据问题关键词智能选择图表类型和字段
        col_options = df.columns.tolist()
        numeric_cols = df.select_dtypes(include="number").columns.tolist()
        category_cols = df.select_dtypes(exclude="number").columns.tolist()

        # 侧边栏让用户自定义图表
        with st.sidebar:
            st.markdown("### 🎛 图表设置")
            chart_type = st.selectbox(
                "图表类型",
                ["柱状图", "折线图", "饼图", "散点图"]
            )
            if category_cols:
                x_col = st.selectbox("X 轴 / 分类", category_cols)
            else:
                x_col = st.selectbox("X 轴", col_options)

            if numeric_cols:
                y_col = st.selectbox("Y 轴 / 数值", numeric_cols)
            else:
                y_col = st.selectbox("Y 轴", col_options)

            color_col = st.selectbox(
                "颜色分组（可选）",
                ["无"] + category_cols
            )

        color = None if color_col == "无" else color_col

        # 聚合数据
        if color:
            chart_df = df.groupby([x_col, color])[y_col].sum().reset_index()
        else:
            chart_df = df.groupby(x_col)[y_col].sum().reset_index()

        # 画图
        if chart_type == "柱状图":
            fig = px.bar(chart_df, x=x_col, y=y_col, color=color,
                        title=f"{x_col} vs {y_col}", text_auto=True)
        elif chart_type == "折线图":
            fig = px.line(chart_df, x=x_col, y=y_col, color=color,
                         title=f"{x_col} 趋势", markers=True)
        elif chart_type == "饼图":
            fig = px.pie(chart_df, names=x_col, values=y_col,
                        title=f"{y_col} 分布")
        elif chart_type == "散点图":
            fig = px.scatter(df, x=x_col, y=y_col, color=color,
                           title=f"{x_col} vs {y_col}")

        st.plotly_chart(fig, use_container_width=True)

        # 显示聚合数据表
        with st.expander("📋 查看图表数据"):
            st.dataframe(chart_df)
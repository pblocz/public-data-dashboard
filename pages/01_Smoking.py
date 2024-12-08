import streamlit as st
import requests
import polars as pl
from io import StringIO
import altair as alt


st.set_page_config(
    page_title="Smoking in Spain",
    page_icon="🚬",
    layout="wide",
    initial_sidebar_state="auto")

ine_data_path = "t00/ICV/dim3/l0"
ine_data_id = "33201"
url = f"https://www.ine.es/jaxi/files/_px/es/csv_bdsc/{ine_data_path}/{ine_data_id}.csv_bdsc?nocab=1"
web_data_url = f"https://www.ine.es/jaxi/Tabla.htm?path=/{ine_data_path}/&file={ine_data_id}.px&L=0"

@st.cache_data
def get_csv_data(url):
    resp = requests.get(url)
    data_text = resp.content.decode()
    buffer = StringIO(data_text)
    data = pl.read_csv(buffer, truncate_ragged_lines=True, separator=";", encoding="unicode")
    return data

data = get_csv_data(url)
total_name_col = "Total Nacional"
name_col = "Comunidades y Ciudades Autónomas"
period = "periodo"
value = "Total"

data_transformed = (
    data
    .with_columns(pl.col(name_col).str.splitn(" ", 2).struct.field("field_1").alias(name_col))
    .with_columns(pl.coalesce(pl.col(name_col), pl.col(total_name_col)).alias(name_col))
    .with_columns(
        pl.col(value).str.replace(r"\.", "").str.replace(r",", ".").cast(pl.Float64),
        pl.col(period).str.replace(r" \(P\)", "")
    )
)

table_data = (
    data_transformed
    .pivot(
        on=period,
        index=name_col,
        values=value,
        sort_columns=True
    )
)
all_communities = table_data.select(name_col).get_column(name_col) 

def get_chart(default_communities):
    selection = alt.selection_point(fields=[name_col], bind='legend', value=[{name_col: c} for c in default_communities])
    chart = (
        data_transformed.plot.line(
            x=period, 
            y=value, 
            color=alt.Color(
                name_col,
                scale=alt.Scale(domain=all_communities)
            )
        )
        .add_params(selection)
        .transform_filter(selection)
        .properties(
            height=450,
            autosize=alt.AutoSizeParams(type='fit')
        )
    )
    return chart


st.markdown(f'''
# Smoking stats
            
Data of smoking in Spain by community

Data source: [{web_data_url}]({web_data_url})  

#### Smoking by community
Use the legend to filter by clicking on one or multiselecting with shift + click or the selection box
''')

communities = st.multiselect("Choose communities", all_communities, [], label_visibility="collapsed")
st.markdown("####")  # Separator
st.altair_chart(get_chart(communities), use_container_width=True)

st.markdown('''
#### Data table
''')

st.dataframe(table_data, use_container_width=True)
import geopandas as gpd
from shapely.geometry import LineString, MultiLineString
import plotly.graph_objects as go
import dash
from dash import dcc, html, Input, Output
import plotly.io as pio

# 📂 Carregar dados GPKG
gdf = gpd.read_file("data/linhas_fiocruz.gpkg")
gdf = gdf[gdf.is_valid & ~gdf.is_empty]
x, y = list(gdf.union_all().centroid.coords)[0]

# Cores por versão
cores = {
    'original': 'blue',
    'licitada': 'green',
    'ajustada': 'red'
}

linhas_unicas = sorted(gdf['route_id'].unique())
versoes_unicas = sorted(gdf['versao'].unique())

def gerar_figura_plotly(linhas_selecionadas, versoes_selecionadas):
    fig = go.Figure()

    if not linhas_selecionadas or not versoes_selecionadas:
        return fig

    filtro = gdf[
        gdf['route_id'].isin(linhas_selecionadas) &
        gdf['versao'].isin(versoes_selecionadas)
    ]
    filtro = filtro[filtro.is_valid & ~filtro.is_empty]

    for _, row in filtro.iterrows():
        geom = row.geometry
        coords = []

        if geom.geom_type == "LineString":
            coords = list(geom.coords)
        elif geom.geom_type == "MultiLineString":
            for line in geom.geoms:
                coords.extend(line.coords)

        if coords:
            lons, lats = zip(*coords)
            fig.add_trace(go.Scattermapbox(
                lat=lats,
                lon=lons,
                mode="lines",
                name=f"Linha {row['route_id']} - {row['versao']}",
                line=dict(color=cores.get(row['versao'], 'gray'), width=3),
                hovertext=f"Linha {row['route_id']}<br>Versão: {row['versao']}"
            ))

    fig.update_layout(
        mapbox_style="carto-positron",
        mapbox_zoom=12,
        mapbox_center={"lat": y, "lon": x},
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        font=dict(
            family="Roboto, Arial, sans-serif",
            size=14,
            color="#333"
        ),
        legend=dict(
            title="Linhas e Versões",
            x=0.01,
            y=0.99,
            bgcolor='rgba(255,255,255,0.7)',
            bordercolor='black',
            borderwidth=1
        )
    )

    return fig

# 🖼️ app Dash
app = dash.Dash(__name__)
server = app.server  # 🔧 Necessário para Render rodar com gunicorn
app.title = "Mapa Interativo de Linhas"

app.layout = html.Div([
    html.H2("🚌 Mapa Interativo de Linhas de Transporte Público", style={"textAlign": "center"}),

    html.Div([
        html.Label("Selecionar Linhas:"),
        dcc.Dropdown(
            id='dropdown_linhas',
            options=[{'label': f"Linha {linha}", 'value': linha} for linha in linhas_unicas],
            value=linhas_unicas[:2],
            multi=True
        ),
    ], style={"width": "48%", "display": "inline-block"}),

    html.Div([
        html.Label("Selecionar Versões:"),
        dcc.Checklist(
            id='checklist_versoes',
            options=[{'label': v.capitalize(), 'value': v} for v in versoes_unicas],
            value=versoes_unicas,
            labelStyle={'display': 'inline-block', 'margin-right': '15px'}
        ),
    ], style={"width": "48%", "display": "inline-block", "verticalAlign": "top"}),

    dcc.Graph(id="mapa_plotly", style={"height": "80vh"})
])

@app.callback(
    Output("mapa_plotly", "figure"),
    Input("dropdown_linhas", "value"),
    Input("checklist_versoes", "value")
)
def atualizar_mapa(linhas_selecionadas, versoes_selecionadas):
    return gerar_figura_plotly(linhas_selecionadas, versoes_selecionadas)

#if __name__ == "__main__":
#    app.run_server(debug=True, host="0.0.0.0", port=8080)

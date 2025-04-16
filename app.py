import itertools
import os

import geopandas as gpd
from shapely.geometry import LineString, MultiLineString
import plotly.graph_objects as go
import dash
from dash import dcc, html, Input, Output
import plotly.io as pio
from flask import request, Response, send_from_directory  # 🧩 Novo

# 👤 Usuário e senha simples (ideal colocar em variáveis de ambiente)
USERNAME = os.getenv("DASH_USERNAME", "oswaldogcruz")
PASSWORD = os.getenv("DASH_PASSWORD", "25051900")

def check_auth(user, pw):
    return user == USERNAME and pw == PASSWORD

def authenticate():
    return Response(
        'Autenticação requerida', 401,
        {'WWW-Authenticate': 'Basic realm="Acesso restrito"'}
    )

def require_auth(func):
    def wrapper(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return func(*args, **kwargs)
    return wrapper

# 📂 Carregar dados GPKG
gdf = gpd.read_file("data/linhas_fiocruz.gpkg")
gdf = gdf[gdf.is_valid & ~gdf.is_empty]
x, y = list(gdf.union_all().centroid.coords)[0]

linhas_unicas = sorted(gdf['route_id'].unique())
versoes_unicas = sorted(gdf['versao'].unique())

# Styling lines
route_colors = {
    rid: color for rid, color in zip(
        linhas_unicas,
        ['#332288', '#88CCEE', '#44AA99', '#117733', '#999933',
         '#DDCC77', '#661100', '#CC6677', '#882255',
         '#6699CC', '#AA4499', '#3f51b5', '#000000',]
    )
}
linestyles = {
    'original': 1,
    'licitada': 2,
    'ajustada': 3.5,
}

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
            fig.add_trace(go.Scattermap(
                lat=lats,
                lon=lons,
                mode="lines",
                name=f"Linha {row['route_id']} - {row['versao']}",
                line=dict(
                    color=route_colors.get(row['route_id'], '#999999'),
                    width=linestyles.get(row['versao'], 3),
                ),
                hovertext=f"{row['route_id']}<br>Versão: {row['versao']}"
            ))

    fig.update_layout(
        map_style="carto-positron",
        map_zoom=12,
        map_center={"lat": y, "lon": x},
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

# 🔒 Protege o layout inteiro com autenticação
@server.before_request
def protect_routes():
    auth = request.authorization
    if not auth or not check_auth(auth.username, auth.password):
        return authenticate()

# 🛑 Adiciona o robots.txt
@server.route('/robots.txt')
def robots():
    return Response("User-agent: *\nDisallow: /", mimetype="text/plain")

app.title = "Mapa Interativo de Linhas"

app.layout = html.Div([
    html.H2("🚌 Linhas de Transporte Corporativo", style={"textAlign": "center"}),

    html.Div([
        html.Label("Selecionar Linhas:"),
        dcc.Dropdown(
            id='dropdown_linhas',
            options=[{'label': f"{linha}", 'value': linha} for linha in linhas_unicas],
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
    Input("checklist_versoes", "value"))
def atualizar_mapa(linhas_selecionadas, versoes_selecionadas):
    return gerar_figura_plotly(linhas_selecionadas, versoes_selecionadas)

if __name__ == '__main__':
    app.run(debug=True)
#if __name__ == "__main__":
#    app.run_server(debug=True, host="0.0.0.0", port=8080)

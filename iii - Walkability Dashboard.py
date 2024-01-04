import dash
from dash import dcc as dcc
from dash import html as html
from dash.dependencies import Input, Output, State
import plotly.graph_objects as go
import plotly.express as px
import geopandas as gpd
import pandas as pd
import numpy as np
import json


#########Load your data here
#Shapefile
pedLineShapefile = r"" #https://github.com/nehrou/walkability/blob/main/Ped%20Line%20Shapefile.zip

#GeoJSON data
pedLineJson = gpd.read_file(pedLineShapefile)
pedLineJson = pedLineJson.to_crs(epsg=4326)

#Dataframe
path = r"https://raw.githubusercontent.com/nehrou/walkability/main/20231221_134921_pedDataframe.csv"
pedDataframe = pd.read_csv(path)


#########Variables

lat = 10.6394
lon = -61.4002


walkability_colors = {
    'EXCELLENT': 'green',
    'GOOD': 'blue',
    'FAIR': 'yellow',
    'POOR': 'orange',
    'VERY POOR': 'red'
}


walkabilitySum = pedDataframe.groupby('WALK_CATEGORY')['SHAPE_Length'].sum().reset_index()

colors_walk = ['green', 'blue', 'yellow', 'orange', 'red']


# Ensure P_ID columns are of the same type (int64)
pedLineJson['P_ID'] = pedLineJson['P_ID'].astype('int64')
pedDataframe['P_ID'] = pedDataframe['P_ID'].astype('int64')

# Merge the GeoDataFrame with the DataFrame
merged_data = pedLineJson.merge(pedDataframe, on='P_ID')





######Functions 

# Filter for Map
def dataFilter(selectedWalkScore):
    if selectedWalkScore is None or 'ALL' in selectedWalkScore:
        filteredData = pedLineJson.copy()
    else:
        filteredData = pedLineJson[pedLineJson['WALK_CATEG'].isin(selectedWalkScore)]
    return filteredData


#Create map
def create_map(selectedWalkScore, map_state={}):
        # When no scores are selected, return an empty map with the basemap
    if not selectedWalkScore:
        fig = go.Figure(go.Scattermapbox())
        fig.update_layout(
            #height=400,
            #width= 600,
            autosize= True,
            margin=dict(l=2, r=2, t=2, b=2), # Remove margins
            mapbox_style="open-street-map",
            mapbox_zoom=map_state.get('zoom', 26),
            mapbox_center=map_state.get('center', {"lat": 10.6394, "lon": -61.4002}),
            legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01)

        )
        return fig
       
    filteredData = dataFilter(selectedWalkScore)  # Call dataFilter with only selectedWalkScore
    fig = go.Figure()

    # Process each walkability category
    for category, color in walkability_colors.items():
        category_data = filteredData[filteredData['WALK_CATEG'].str.strip() == category]
        for _, row in category_data.iterrows():
            if row['geometry'].geom_type == 'LineString':
                lon, lat = zip(*row['geometry'].coords)
                custom_data = [row['P_ID']] * len(lat)
                fig.add_trace(go.Scattermapbox(
                    lat=lat,
                    lon=lon,
                    mode='lines',
                    line=dict(color=color, width=2),
                    hoverinfo='text',
                    text=category,
                    customdata=[custom_data],
                    name=category,
                    connectgaps= True,
                ))

    # Apply stored map state if available
    map_center = map_state.get('center', {"lat": 10.6394, "lon": -61.4002})
    map_zoom = map_state.get('zoom', 16)

    fig.update_layout(
        autosize=True,
        margin=dict(l=2, r=2, t=2, b=2), # Remove margins
        mapbox_style="open-street-map",
        mapbox_center=map_center,
        mapbox_zoom=map_zoom,
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01)
    )

    names_set = set()
    fig.for_each_trace(
        lambda trace: names_set.add(trace.name) if trace.name not in names_set else trace.update(showlegend=False)
    )

    return fig


# Initialize app
app = dash.Dash(__name__, meta_tags=[{"name": "viewport", "content": "width=device-width"}],
                )
app.title = "Walkability Analysis"


# Create initial figures (map and histogram)
initial_map_figure = create_map(['EXCELLENT', 'GOOD', 'FAIR', 'POOR', 'VERY POOR'])


#---------------------------------WALKABILITY CHART GENERATION
walkabilityRating = go.Figure(data=[
                        go.Bar(
                            x=walkabilitySum['WALK_CATEGORY'],
                            y=walkabilitySum['SHAPE_Length'],
                            width= 0.95,
                            # xbins=dict(start=0, end=max(pedDataframe['WALK_TSCORE']), size=1),
                            # marker=dict(color='blue', line=dict(color='black', width=1.5)),
                            opacity=0.5                            
                        )
])


walkabilityRating.update_layout(
    title_text='Walkability Score Distribution',
    title_font_size=20,
    xaxis=dict(
        title='Walkability Score',
        # tickvals=np.arange(0.5, len(bin_edges_walk)),
        # ticktext=[str(i) for i in range(len(bin_edges_walk))],
    ),
    yaxis=dict(
        title='Length(m)',
    ),
    bargap=0.2)    

bar_colors = colors_walk * (len(pedDataframe['WALK_CATEGORY']) // len(colors_walk))
walkabilityRating.data[0].marker.color = bar_colors[:len(pedDataframe['WALK_CATEGORY'])]


#---------------------------------AESTHETICS CHART GENERATION

aestheticsRating = px.scatter(
    pedDataframe,
    x='AES_SCORE',
    y='SHAPE_Length',
    title='Aesthetics Score vs Network Length',
    labels={'AES_SCORE': 'Aesthetics Score', 'SHAPE_Length': 'Length(m)'},
    color_continuous_scale=px.colors.sequential.Viridis, 
)

aestheticsRating.update_layout(
    autosize=True,
    margin=dict(l=40, r=40, t=60, b=60),
    title_x = 0.5,
    title_font_size = 14
)


#---------------------------------DESTINATION CHART GENERATION

# Create the scatter plot
destinationRating = px.scatter(
    pedDataframe,
    x='DEST_SCORE',
    y='SHAPE_Length',
    title='Destination Score vs Network Length',
    labels={'DEST_SCORE': 'Destination Score', 'SHAPE_Length': 'Length(m)'},
    color_continuous_scale=px.colors.sequential.Viridis, 
)

destinationRating.update_layout(
    autosize=True,
    margin=dict(l=40, r=40, t=60, b=60),
    title_x = 0.5,
    title_font_size = 14
)
 
#---------------------------------CONSPICUOUS CHART GENERATION
    
# Create the scatter plot
conspicuousRating = px.scatter(
    pedDataframe,
    x='CON_SCORE',
    y='SHAPE_Length',
    title='Conspicuous Score vs Network Length',
    labels={'CON_SCORE': 'Conspicuous Score', 'SHAPE_Length': 'Length(m)'},
    color_continuous_scale=px.colors.sequential.Viridis, 
)

conspicuousRating.update_layout(
    autosize=True,
    margin=dict(l=40, r=40, t=60, b=60),
    title_x = 0.5,
    title_font_size = 14
)
 

#---------------------------------SAFETY CHART GENERATION
# Create the scatter plot
safetyRating = px.scatter(
    pedDataframe,
    x='SAFETY',
    y='SHAPE_Length',
    title='Safety Score vs Network Length',
    labels={'SAFETY': 'Safety Score', 'SHAPE_Length': 'Length(m)'},
    color_continuous_scale=px.colors.sequential.Viridis, 
)

safetyRating.update_layout(
    autosize=True,
    margin=dict(l=40, r=40, t=60, b=60),
    title_x = 0.5,
    title_font_size = 14
)

initial_histogram_figure = go.Figure()  
empty_figure = go.Figure()


# App layout
app.layout = html.Div([
    # Header and user controls
    html.Div(
        className="four columns div-user-controls",
        children=[
            html.H2("WALKABILITY APPLICATION" ),
            html.P("Select different Walkability ratings to update and refresh the map."),
            dcc.Dropdown(
                id="walk-selector",
                options=[
                    {'label': 'EXCELLENT', 'value': 'EXCELLENT'},
                    {'label': 'GOOD', 'value': 'GOOD'},
                    {'label': 'FAIR', 'value': 'FAIR'},
                    {'label': 'POOR', 'value': 'POOR'},
                    {'label': 'VERY POOR', 'value': 'VERY POOR'},
                ],
                multi=True,
                value=['EXCELLENT', 'GOOD', 'FAIR', 'POOR', 'VERY POOR'],
                placeholder="Select Walkability Rating",
        ),
        ],
    ),
    # Row for the map and the main graph
    html.Div(
        className="row",
        children=[
            html.Div(
                className="six columns",
                children=[dcc.Graph(id='map-display', figure=initial_map_figure)] 
            ),
            html.Div(
                className="six columns",
                children=[dcc.Graph(figure=walkabilityRating)]
            ),
        ]
    ),
    dcc.Store(id='map-state'),

    # Row for the inline graphs
    html.Div(
        className="graph-row",
        children=[
            html.Div(
                className="three columns",
                children=[dcc.Graph(id='graph-1', figure=aestheticsRating)]
            ),
            html.Div(
                className="three columns",
                children=[dcc.Graph(id='graph-2', figure=destinationRating)]
            ),
            html.Div(
                className="three columns",
                children=[dcc.Graph(id='graph-3', figure=conspicuousRating)]
            ),
            html.Div(
                className="three columns",
                children=[dcc.Graph(id='graph-4', figure=safetyRating)]
            ),
        ]
    ),
])


#Update map based on selected ratings
@app.callback(
    Output('map-display', 'figure'),
    [Input('walk-selector', 'value')],
    [State('map-state', 'data')])

def updateMap(selectedWalkScore, map_state):
    # print(f"Callback Triggered: {selectedWalkScore}")  # Debug print
    return create_map(selectedWalkScore, map_state or {})

# Callback to allow map to not reload at go to inital zoom
@app.callback(
    Output('map-state', 'data'),
    [Input('map-display', 'relayoutData')],
    [State('map-state', 'data')]
)
def save_map_state(relayoutData, current_state):
    if relayoutData and 'mapbox.center' in relayoutData:
        return {
            'center': relayoutData.get('mapbox.center'),
            'zoom': relayoutData.get('mapbox.zoom', current_state.get('zoom') if current_state else 15)
        }
    return current_state



#Callback to update graphs
@app.callback(
    [
        Output('graph-1', 'figure'),
        Output('graph-2', 'figure'),
        Output('graph-3', 'figure'),
        Output('graph-4', 'figure')
    ],
    [Input('walk-selector', 'value')]
)
def update_graphs(selectedWalkScore):
    if not selectedWalkScore:
        # Return the default figures if no selection is made
        return aestheticsRating, destinationRating, conspicuousRating, safetyRating

    # Filter the dataframe based on the selected categories
    filtered_df = pedDataframe[pedDataframe['WALK_CATEGORY'].isin(selectedWalkScore)]

    # Update each graph with the filtered data
    updated_aestheticsRating = px.scatter(
        filtered_df,
        x='AES_SCORE',
        y='SHAPE_Length',
        title='Aesthetics Score vs Network Length',
        labels={'AES_SCORE': 'Aesthetics Score', 'SHAPE_Length': 'Length(m)'},
        color_continuous_scale=px.colors.sequential.Viridis
    )

    updated_destinationRating = px.scatter(
        filtered_df,
        x='DEST_SCORE',
        y='SHAPE_Length',
        title='Destination Score vs Network Length',
        labels={'DEST_SCORE': 'Destination Score', 'SHAPE_Length': 'Length(m)'},
        color_continuous_scale=px.colors.sequential.Viridis
    )

    updated_conspicuousRating = px.scatter(
        filtered_df,
        x='CON_SCORE',
        y='SHAPE_Length',
        title='Conspicuous Score vs Network Length',
        labels={'CON_SCORE': 'Conspicuous Score', 'SHAPE_Length': 'Length(m)'},
        color_continuous_scale=px.colors.sequential.Viridis
    )

    updated_safetyRating = px.scatter(
        filtered_df,
        x='SAFETY',
        y='SHAPE_Length',
        title='Safety Score vs Network Length',
        labels={'SAFETY': 'Safety Score', 'SHAPE_Length': 'Length(m)'},
        color_continuous_scale=px.colors.sequential.Viridis
    )

    # Return the updated figures
    return updated_aestheticsRating, updated_destinationRating, updated_conspicuousRating, updated_safetyRating



if __name__ == "__main__":
    app.run_server(debug=True)

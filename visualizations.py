import numpy as np
import pandas as pd
import plotly



def plot_years_at_inauguration(presidents_data: pd.DataFrame):
    trace = plotly.graph_objs.Scatter(
        x = presidents_data['Inauguration Date'],
        y = presidents_data['Years at Inauguration'],
        mode = 'lines+markers',
        name = 'chart_a',
        marker = {'size': 7},
        text = presidents_data.index
    )

    layout = plotly.graph_objs.Layout(
        title = 'Years at Inauguration',
        xaxis = {'title': 'Inauguration Date'},
        yaxis = {'title': 'Years at Inauguration'},
    )

    plotly.offline.iplot(plotly.graph_objs.Figure(
        data = [trace],
        layout = layout
    ))


def plot_key_events_count(presidents_data: pd.DataFrame):
    trace = plotly.graph_objs.Scatter(
        x = presidents_data['Inauguration Date'],
        y = presidents_data['Key Events Count'],
        mode = 'lines+markers',
        name = 'chart_a',
        marker = {'size': 7},
        text = presidents_data.index
    )

    layout = plotly.graph_objs.Layout(
        title = 'Key Events Count',
        xaxis = {'title': 'Inauguration Date'},
        yaxis = {'title': 'Key Events Count'},
    )

    plotly.offline.iplot(plotly.graph_objs.Figure(
        data = [trace],
        layout = layout
    ))


def plot_years_at_inauguration_overlapping_histograms(presidents_data: pd.DataFrame):
    parties = {
        'Democrats': 'Dem',
        'Federalists': 'Fed', 
        'Republicans': 'Rep',
        'Unionists': 'Uni',
        'Whigs': 'Whi'
    }

    traces = {}
    for party in parties:
        party_filter = presidents_data['Political Party'].map(lambda x: parties[party] in x)
        traces[party] = plotly.graph_objs.Histogram(
            x = presidents_data.loc[party_filter, 'Years at Inauguration'],
            name = party,
            opacity = 0.5
        )

    layout = plotly.graph_objs.Layout(
        barmode='overlay',
        title = 'Histogram of Years at Inauguration',
        yaxis = {'title': 'Number of Presidents'},
        xaxis = {'title': 'Years at Inauguration'},
    )

    plotly.offline.iplot(plotly.graph_objs.Figure(
        data = [trace for trace in traces.values()],
        layout = layout
    ))


def plot_birth_places_and_paths_map(presidents_data: pd.DataFrame):
    birth_places = [plotly.graph_objs.Scattergeo(
        locationmode = 'USA-states',
        lon = presidents_data['Birth Place Longitude'],
        lat = presidents_data['Birth Place Latitude'],
        hoverinfo = 'text',
        text = presidents_data['Birth Place'],
        mode = 'markers',
        marker = plotly.graph_objs.scattergeo.Marker(
            size = 2,
            color = 'rgb(255, 0, 0)',
            line = plotly.graph_objs.scattergeo.marker.Line(
                width = 3,
                color = 'rgba(68, 68, 68, 0)'
            )
        )
    )]

    paths = []
    for i in range(len(presidents_data) - 1):
        paths.append(
            plotly.graph_objs.Scattergeo(
                locationmode = 'USA-states',
                lon = [
                    presidents_data['Birth Place Longitude'][i], 
                    presidents_data['Birth Place Longitude'][i + 1]
                ],
                lat = [
                    presidents_data['Birth Place Latitude'][i], 
                    presidents_data['Birth Place Latitude'][i + 1]
                ],
                mode = 'lines',
                line = plotly.graph_objs.scattergeo.Line(
                    width = 1,
                    color = 'red',
                )
            )
        )
    
    layout = plotly.graph_objs.Layout(
        title = plotly.graph_objs.layout.Title(
            text = 'US Presidents Birth Places Path'
        ),
        showlegend = False,
        geo = plotly.graph_objs.layout.Geo(
            scope = 'usa',
            projection = dict(type = 'albers usa'),
            showland = True,
            landcolor = 'rgb(243, 243, 243)',
            countrycolor = 'rgb(204, 204, 204)',
        ),
    )

    plotly.offline.iplot(plotly.graph_objs.Figure(
        data = birth_places + paths,
        layout = layout
    ))


def plot_vote_share_heatmap(presidents_data: pd.DataFrame):
    parties = {
        'Democrats': 'Dem',
        'Federalists': 'Fed', 
        'Republicans': 'Rep',
        'Unionists': 'Uni',
        'Whigs': 'Whi'
    }

    number_of_children_list = list(set(presidents_data['Number of Children']))
    political_party_list = list(parties.keys())
    vote_share_list = []

    for number in number_of_children_list:
        number_filter = presidents_data['Number of Children'] == number
        vote_share_per_number_of_children_list = []

        for party in political_party_list:
            party_filter = presidents_data['Political Party'].map(lambda x: parties[party] in x)
            vote_share = presidents_data.loc[
                number_filter & party_filter, 'Electoral Votes Share'
            ].mean()
            vote_share = None if np.isnan(vote_share) else vote_share
            vote_share_per_number_of_children_list.append(vote_share)

        vote_share_list.append(vote_share_per_number_of_children_list)

    trace = plotly.graph_objs.Heatmap(
        x = number_of_children_list,
        y = political_party_list,
        z = vote_share_list
    )

    plotly.offline.iplot([trace])

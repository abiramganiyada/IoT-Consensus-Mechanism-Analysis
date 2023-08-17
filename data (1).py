from ipaddress import IPv4Address
import uuid
import random
import copy
import pandas as pd
from pprint import pp
import dash
from dash import dcc,html
from dash import Input, Output
from dash import dash_table
import plotly.express as px
import plotly.graph_objs as go
from flask import Flask, request,jsonify
from pymongo import MongoClient
import requests
import calendar
import dash_auth

client = MongoClient('mongodb://localhost:27017/')

# select the database and collection
db = client['major']
collection = db['data']

data = collection.find()
nodes=[]
messages=[]
for d in data:
    d.pop('_id')  # remove the '_id' field from each document
    if 'port' in d:
        nodes.append(d)
    else:
        messages.append(d)
df1 = pd.DataFrame(nodes)
df1['peers']=df1['peers'].apply(', '.join)
df = pd.DataFrame(messages)
df = pd.concat([df.drop(['payload'], axis=1), df['payload'].apply(pd.Series)], axis=1)
#df['date'] = pd.to_datetime(df['date'], format='%d-%m-%Y')
df.sort_values(by='date',ascending = True, inplace = True)
df=df.reset_index(drop=True)
merged_df = pd.merge(df, df1, left_on='sender', right_on='id')
merged_df = merged_df.drop('id', axis=1)
grouped_df = merged_df.groupby('date').mean()
grouped_df = grouped_df.reset_index()
sender_counts = merged_df.groupby(['sender']).size().reset_index(name='count')
reciver_counts = merged_df.groupby(['receiver']).size().reset_index(name='count')

merged_df['date'] = pd.to_datetime(merged_df['date'], format='%Y-%m-%d %H:%M:%S')
sender_month_counts = merged_df.groupby([pd.Grouper(key='date', freq='M'), 'sender'])['sender'].count().reset_index(name='count')
receiver_month_counts = merged_df.groupby([pd.Grouper(key='date', freq='M'), 'receiver'])['receiver'].count().reset_index(name='count')
most_frequent_senders = sender_month_counts.loc[sender_month_counts.groupby(['date'])['count'].idxmax()]
most_frequent_receivers = receiver_month_counts.loc[receiver_month_counts.groupby(['date'])['count'].idxmax()]
mergedf = pd.merge(most_frequent_senders, most_frequent_receivers, on='date', suffixes=('_sender', '_receiver'))


merged_df['day_of_week'] = merged_df['date'].dt.dayofweek
groupeddf = merged_df.groupby(['receiver', pd.Grouper(key='date', freq='M'), 'day_of_week']).size().reset_index(name='count')
pivoted_df = pd.pivot_table(groupeddf, values='count', index=['receiver', 'date'], columns=['day_of_week'], fill_value=0)
pivoted_df['month'] = pivoted_df.index.get_level_values(1).strftime('%B')
pivoted_df = pivoted_df.reset_index()


VALID_USERNAME_PASSWORD_PAIRS = {
    'KUSHAL': 'Password'
}
stylesheets =['assets\Style.css']
app = dash.Dash(__name__)
server = app.server
app.title = 'IoT Consensus Mechanism-Analysis'
#app._favicon  ='assets\favicon.ico'
dash_auth.BasicAuth(
    app,
    VALID_USERNAME_PASSWORD_PAIRS,
)

@app.server.route('/store', methods=['POST'])
def insert_many_data():
    data_list = request.get_json()
    result = collection.insert_one(data_list)
    return jsonify({'success': True})
@app.server.route('/get', methods=['GET'])
def get_data():
    # get data from the collection
    data = collection.find()
    
    # convert data to a list of dictionaries
    data_list = []
    for d in data:
        d.pop('_id')  # remove the '_id' field from each document
        data_list.append(d)
    
    # return the data as a JSON response
    return (data_list)

app.layout =dash.html.Div(children=[
    dash.html.H1(['The Dashboard'],style = {'textAlign':'center'}),
    dash.html.H2('Nodes Data'),
    dash.dash_table.DataTable(
        data=df1.to_dict('records'),
        columns=[{"name": i, "id": i} for i in df1.columns],
        editable=True,
        sort_action="native",
        sort_mode="multi",
        column_selectable="single",
        row_selectable="multi",
        row_deletable=True,
        selected_columns=[],
        selected_rows=[],
        page_current= 0,
        page_size=8,
    ),
    html.H2("Select The Honest"),
    dcc.Dropdown(
        id='my-dropd',
        options=[{'label': temp, 'value': temp} for temp in df1['honest'].unique()],
        value=[df['temperature'].min()],
        multi=True
    ),
    html.Div(id='gr'),
    dash.html.H2('The Graph Between The Port And Peer'),
    dash.dcc.Graph(
        id='peer-graph',
        figure=px.scatter(df1, x='port', y='addr', color='peers')
    ),
    html.H2('The Pecentage Of Honest Values'), 
    dcc.Graph(
        id='honest-graph',
        figure={
            'data': [
                {
                    'labels': ['Honest', 'Dishonest'],
                    'values': [df1['honest'].value_counts()['true'], df1['honest'].value_counts()['false']],
                    'type': 'pie',
                    'name': 'honesty'
                }
            ],
            'layout': {
                'title': 'Honesty',
                'xaxis': {'title': 'Honest/Dishonest'},
                'yaxis': {'title': 'Count'}
            }
        }
    ),
    dash.dcc.Graph(
        id='graph1',
        figure=px.scatter(df1, x='port', y='addr', color='honest',title='The Graph On Addr And Port And Honest')
    ),
    dash.dcc.Graph(
        id='graph3',
        figure=px.line(df1, x='addr', y='port',title='The Graph On Addr And Port')
    ),
    dash.html.H2('The Messages'),
    dash.dash_table.DataTable(
        data=df.to_dict('records'),
        columns=[{"name": i, "id": i} for i in df.columns],
        editable=True,
        sort_action="native",
        sort_mode="multi",
        column_selectable="single",
        row_selectable="multi",
        row_deletable=True,
        selected_columns=[],
        selected_rows=[],
        page_current= 0,
        page_size=8,
    ),
    dash.dcc.Graph(
        id='graphmess',
        figure=px.scatter(df, x='sender', y='temperature',title='The Graph On Sender And Temperature')
    ),
    dcc.Graph(
        id='temperature-wind-speed-graph',
        figure={
            'data': [
                go.Bar(name='Temperature', x=df['date'], y=df['temperature']),
                go.Bar(name='Wind', x=df['date'], y=df['wind']),
                go.Bar(name='Speed', x=df['date'], y=df['speed'])
            ],
            'layout': go.Layout(
                title='Temperature, Wind, and Speed',
                barmode='stack'  # Add this line to stack the bars
            )
        }
    ),
    dash.dcc.Graph(
        id='wind-speed-graph',
        figure={
            'data': [
                go.Scatter(name='Wind', x=list(range(len(df['wind']))), y=df['wind'], mode='lines'),
                go.Scatter(name='Speed', x=list(range(len(df['speed']))), y=df['speed'], mode='lines')
            ],
            'layout': go.Layout(
                title=' Wind, and Speed',
                xaxis=dict(title='Time'),
            )
        }
    ),
    dcc.Slider(
        id='temperature-slider',
        min=df['temperature'].min(),
        max=df['temperature'].max(),
        step=1,
        value=df['temperature'].min(),
        marks={str(temperature): str(temperature) for temperature in df['temperature'].unique()}
    ),
    dcc.Graph(id='graph'),
    html.Br(),
    dcc.Slider(
        id='temperature',
        min=df['temperature'].min(),
        max=df['temperature'].max(),
        step=1,
        value=df['temperature'].min(),
        marks={str(temperature): str(temperature) for temperature in df['temperature'].unique()}
    ),
    dcc.Graph(id='grap'),
    html.Br(),
    dcc.Dropdown(
        id='my-dropdown',
        options=[{'label': temp, 'value': temp} for temp in df['date'].unique()],
        value=[df['date'].min()],
        multi=True
    ),
    html.Div(id='gra'),
    html.Br(),
    html.H2("The Combination Of Data"),
    dash.dash_table.DataTable(
        data=merged_df.to_dict('records'),
        columns=[{"name": i, "id": i} for i in merged_df.columns],
        editable=True,
        sort_action="native",
        sort_mode="multi",
        column_selectable="single",
        row_selectable="multi",
        row_deletable=True,
        selected_columns=[],
        selected_rows=[],
        page_current= 0,
        page_size=8,
    ),
    dash.dcc.Graph(
        id='honet-graph',
        figure=px.line(merged_df, x='sender', y='honest',title='The Graph On Sender and Honest')
    ),
    dash.dcc.Graph(
        id='sender-graph',
        figure=px.bar(merged_df, x='sender', y='temperature',color='honest',title='The Graph On Temperature and Sender')
    ),
    dash.dcc.Graph(
        id='date-honest-graph',
        figure=px.bar(merged_df, x='date', y='addr',color='honest',title='The Graph On Date And Honest')
    ),
    dash.dcc.Graph(
        id='date-port-graph',
        figure=px.bar(merged_df, x='date', y='addr',color='port',title='The Graph On Date,Addr And Port')
    ),
    html.H2("Select the Honest and Date"),
    dcc.Dropdown(
        id='sender-dropdown',
        options=[{'label': i, 'value': i} for i in merged_df['honest'].unique()],
        value=None,
        placeholder='Select a honest',
        multi=True
    ),
    dcc.Dropdown(
        id='receiver-date-dropdown',
        options=[{'label': i, 'value': i} for i in merged_df['date'].unique()],
        value=None,
        placeholder='Select a date',
        multi=True
    ),
    html.Br(),
    html.Div(id='output'),
    dcc.Graph(
        id='message-counts',
        figure={
            'data': [
                {'x': sender_counts['sender'], 'y': sender_counts['count'], 'type': 'bar'}
            ],
            'layout': {
                'xaxis': {'title': 'Sender'},
                'yaxis': {'title': 'Number of Messages'}
            }
        }
    ),
    dcc.Graph(
        id='received-counts',
        figure={
            'data': [
                {'x': reciver_counts['receiver'], 'y': reciver_counts['count'], 'type': 'bar'}
            ],
            'layout': {
                'xaxis': {'title': 'receiver'},
                'yaxis': {'title': 'Number of Messages'}
            }
        }
    ),
    dcc.Graph(
        id='mean-temperature-line-graph',
        figure=px.line(x=grouped_df['date'], y=grouped_df['temperature'],title='The Graph Between Temperature And Date')
    ),
    dcc.Graph(
        id='mean-speed-line-graph',
        figure=px.line(x=grouped_df['date'], y=grouped_df['speed'],title='The Graph Between Speed And Date')
    ),
    dcc.Graph(
        id='temperature-histogram',
        figure={
            'data': [
                go.Histogram(x=merged_df['temperature'])
            ],
            'layout': go.Layout(
                title='Temperature Distribution Histogram',
                xaxis_title='Temperature (Celsius)',
                yaxis_title='Count'
            )
        }
    ),
    dcc.Graph(
        id='frequent_count',
        figure=px.bar(mergedf, x='date', y=['count_sender', 'count_receiver'],labels={'value': 'Message Count', 'variable': 'Sender/Receiver', 'date': 'Month'},color_discrete_sequence=px.colors.qualitative.Plotly,title='Most Frequent Message Senders and Receivers, Grouped by Month')
    ),
])
@app.callback(Output('graph', 'figure'), [Input('temperature-slider', 'value')])
def update_graph(temperature):
    filtered_df = df[df['temperature'] >= temperature]
    figure={
            'data': [
                go.Scatter(name='Wind', x=list(range(len(filtered_df['wind']))), y=filtered_df['wind'], mode='lines'),
                go.Scatter(name='Speed', x=list(range(len(filtered_df['speed']))), y=filtered_df['speed'], mode='lines')
            ],
            'layout': go.Layout(
                title=' Wind, and Speed',
            )
        }
    return figure
@app.callback(Output('grap', 'figure'), [Input('temperature', 'value')])
def update_graph(temperature):

    filtered_d = df[df['temperature'] >= temperature]
    figur={
            'data': [
                go.Bar(name='Temperature', x=filtered_d['date'], y=filtered_d['temperature']),
                go.Bar(name='Wind', x=filtered_d['date'], y=filtered_d['wind']),
                go.Bar(name='Speed', x=filtered_d['date'], y=filtered_d['speed'])
            ],
            'layout': go.Layout(
                title='Temperature, Wind, and Speed',
            )
        }
    return figur
@app.callback(Output('gra', 'children'),
              [Input('my-dropdown', 'value')])
def update_graph(selected_temperatures):
    filte = df[df.date.isin(selected_temperatures)]
    return dash_table.DataTable(
        data=filte.to_dict('records'),
        columns=[{"name": i, "id": i} for i in filte.columns],
        editable=True,
        sort_action="native",
        sort_mode="multi",
        column_selectable="single",
        row_selectable="multi",
        row_deletable=True,
        selected_columns=[],
        selected_rows=[],
        page_current= 0,
        page_size=8,
    )
@app.callback(Output('gr', 'children'),
              [Input('my-dropd', 'value')])
def update_graph(selected_temperatures):
    filt = df1[df1.honest.isin(selected_temperatures)]
    return dash_table.DataTable(
        data=filt.to_dict('records'),
        columns=[{"name": i, "id": i} for i in filt.columns],
        editable=True,
        sort_action="native",
        sort_mode="multi",
        column_selectable="single",
        row_selectable="multi",
        row_deletable=True,
        selected_columns=[],
        selected_rows=[],
        page_current= 0,
        page_size=8,
    )
@app.callback(
    dash.dependencies.Output('output', 'children'),
    [dash.dependencies.Input('sender-dropdown', 'value'),
     dash.dependencies.Input('receiver-date-dropdown', 'value')]
)
def update_datatable(honest, date):
    if honest and date:
        filtdf = merged_df[(merged_df.honest.isin(honest)) & (merged_df.date.isin(date))]
        return dash_table.DataTable(
        data=filtdf.to_dict('records'),
        columns=[{"name": i, "id": i} for i in filtdf.columns],
        editable=True,
        sort_action="native",
        sort_mode="multi",
        column_selectable="single",
        row_selectable="multi",
        row_deletable=True,
        selected_columns=[],
        selected_rows=[],
        page_current= 0,
        page_size=8,
    )

if __name__ == '__main__':
    app.run_server(debug=True)
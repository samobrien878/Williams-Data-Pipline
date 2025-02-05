import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.express as px
import pandas as pd
from pymongo import MongoClient

#connect to MongoDB:
MONGO_URI = MONGO_URI = "mongodb+srv://____:____@serverlessinstance0.gqqyx4s.mongodb.net/"
DB_NAME = "training_data"
COLLECTION_NAME = "metrics"

client = MongoClient(MONGO_URI)
db = client[DB_NAME]
collection = db[COLLECTION_NAME]

def get_data():
    data = list(collection.find())
    df = pd.DataFrame(data)
    return df

app = dash.Dash(__name__)

app.layout = html.Div([
    html.H1("Williams Lab Data"),
    dcc.Dropdown(
        id = "ratID"
    ),
    dcc.Graph(id = 'graph')
])
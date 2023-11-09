from fastapi import FastAPI, HTTPException
from databases import Database
from pydantic import BaseModel
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, Float, Date
import os
import requests

# Database configurations
# Using the service name 'db' from docker-compose as the host
DATABASE_URL = "postgresql://myuser:mypassword@db/mystockdb"

# Initialize databases instance for async communication with PostgreSQL
database = Database(DATABASE_URL)

# SQLAlchemy table metadata
metadata = MetaData()

# FastAPI app instance
app = FastAPI()

# Define a table using SQLAlchemy
stocks = Table(
    "stocks",
    metadata,
    Column("id", Integer, primary_key=True, index=True),
    Column("ticker", String, index=True),
    Column("date", Date),
    Column("close", Float),
)

# Pydantic model for stock requests


class StockRequest(BaseModel):
    ticker: str


# Alpha Vantage configurations
# Get this from the environment variable
ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")
ALPHA_VANTAGE_URL = 'https://www.alphavantage.co/query'

# Fetch stock data function


async def fetch_stock_data(ticker: str):
    params = {
        'function': 'TIME_SERIES_DAILY',
        'symbol': ticker,
        'apikey': ALPHA_VANTAGE_API_KEY,
        'datatype': 'json',
    }
    response = requests.get(ALPHA_VANTAGE_URL, params=params)
    response.raise_for_status()  # Raises HTTPError for bad requests
    return response.json()


@app.on_event("startup")
async def startup():
    # Connect to the database
    await database.connect()


@app.on_event("shutdown")
async def shutdown():
    # Disconnect from the database
    await database.disconnect()


@app.post("/stock_data/")
async def create_stock_data(stock_request: StockRequest):
    stock_data = await fetch_stock_data(stock_request.ticker)
    # Process the Alpha Vantage API response and insert data into the database
    async with database.transaction():
        for date, daily_data in stock_data['Time Series (Daily)'].items():
            query = stocks.insert().values(
                ticker=stock_request.ticker,
                date=date,
                close=float(daily_data['4. close'])
            )
            await database.execute(query)
    return {"message": "Stock data inserted successfully."}

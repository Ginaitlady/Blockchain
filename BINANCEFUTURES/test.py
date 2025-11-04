import ccxt
import os
import math
import time
import pandas as pd
import requests
from dotenv import load_dotenv
load_dotenv()
from openai import OpenAI
from datetime import datetime

openai_api_key = os.getenv("OPENAI_API_KEY")
api_key = os.getenv("COINBASE_API_KEY")
secret_key = os.getenv("COINBASE_SECRET_KEY")

# SERP API Settings
serp_api_key = os.getenv("SERP_API_KEY")  # SERP_API_KEY needs to be added to the .env file

# Function to fetch latest Bitcoin news
def fetch_bitcoin_news():
    try:
        # Use SERP API to get latest news related to Bitcoin
        url = "https://serpapi.com/search.json"
        params = {
            "engine": "google_news",
            "q": "bitcoin",
            "gl": "us",
            "hl": "en",
            "api_key": serp_api_key
        }
        
        response = requests.get(url, params=params)
        if response.status_code == 200:
            data = response.json()
            news_results = data.get("news_results", [])
            
            # Extract only the 10 latest news items, including only title and date
            recent_news = []
            for i, news in enumerate(news_results[:10]):
                news_item = {
                    "title": news.get("title", ""),
                    "date": news.get("date", "")
                }
                recent_news.append(news_item)
            
            print(f"Collected {len(recent_news)} recent news articles (title and date only)")
            return recent_news
        else:
            print(f"Error fetching news: Status code {response.status_code}")
            return []
    except Exception as e:
        print(f"Error fetching news: {e}")
        return []
    
print(fetch_bitcoin_news())

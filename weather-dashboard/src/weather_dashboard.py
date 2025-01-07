import os
import json
import boto3
import requests
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class WeatherDashboard:
    def __init__(self):
        self.api_key = os.getenv('OPENWEATHER_API_KEY')
        self.bucket_name = os.getenv('AWS_BUCKET_NAME')
        self.s3_client = boto3.client('s3')

    def create_bucket_if_not_exists(self):
        """Create S3 bucket if it doesn't exist"""
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            print(f"Bucket {self.bucket_name} exists")
        except:
            print(f"Creating bucket {self.bucket_name}")
        try:
            self.s3_client.create_bucket(Bucket=self.bucket_name)
            print(f"Successfully created bucket {self.bucket_name}")
        except Exception as e:
            print(f"Error creating bucket: {e}")

    def fetch_weather(self, city):
        """Fetch weather data from OpenWeather API"""
        base_url = "http://api.openweathermap.org/data/2.5/weather"
        params = {
            "q": city,
            "appid": self.api_key,
            "units": "imperial"
        }
        
        try:
            response = requests.get(base_url, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching weather data: {e}")
            return None

    def save_to_s3(self, weather_data):
        """Save weather data to S3 bucket"""
        if not weather_data:
            return False

        file_name = "weather-dashboard/data.json"
        
        try:
            # Load existing data if it exists
            existing_data = []
            try:
                response = self.s3_client.get_object(Bucket=self.bucket_name, Key=file_name)
                existing_data = json.loads(response['Body'].read())
            except self.s3_client.exceptions.NoSuchKey:
                pass

            # Append new data
            existing_data.append(weather_data)

            # Save updated data
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=file_name,
                Body=json.dumps(existing_data),
                ContentType='application/json'
            )
            print("Successfully saved data to S3")
            return True
        except Exception as e:
            print(f"Error saving to S3: {e}")
            return False

def lambda_handler(event, context):
    dashboard = WeatherDashboard()
    dashboard.create_bucket_if_not_exists()
    cities = ["Philadelphia", "Seattle", "New York", "Texas", "Arizona", "Montana"]
    
    for city in cities:
        print(f"\nFetching weather for {city}...")
        weather_data = dashboard.fetch_weather(city)
        if weather_data:
            simplified_data = {
                "city": city,
                "temperature": weather_data['main']['temp'],
                "feels_like": weather_data['main']['feels_like'],
                "humidity": weather_data['main']['humidity'],
                "conditions": weather_data['weather'][0]['description'],
                "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            dashboard.save_to_s3(simplified_data) 


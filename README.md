# **🌦️ Streamlit Weather & Health Advisory**

An interactive web application built with Streamlit that provides 3-day weather forecasts and generates AI-powered health recommendations for user-selected locations.

## **Features**

* **Dynamic Site Management**: Users can select from a predefined list of locations (loaded from sites.json), add new sites during their session, and persistently edit the coordinates for existing sites.  
* **Interactive Map View**: Displays the selected location on a map for easy visualization and context.  
* **Dual Forecast Views**: Toggle between a high-level **Daily Summary** and a detailed **3-Hourly Forecast** for the next 72 hours.  
* **AI-Powered Health Advice**: Leverages the Google Gemini API to analyze the weather summary and generate crucial, structured health recommendations for different demographic groups (Adults, Children & Elderly, People with Morbidities).  
* **Data Export**: Download both the raw forecast data and the generated health recommendations as CSV files for offline analysis.  
* **Cache Management**: Includes an option to clear the cache for health recommendations to fetch fresh advice.

## **Technologies Used**

* **Frontend**: Streamlit  
* **Data Processing**: Pandas  
* **Weather Data**: [Open-Meteo API](https://open-meteo.com/)  
* **AI Recommendations**: Google Gemini API  
* **Version Control**: Git & GitHub

## **How to Run Locally**

1. **Clone the repository:**  
   git clone https://github.com/pranay-code/streamlit-weather-forecast-health-advisor.git  
   cd YOUR\_REPO\_NAME

2. **Create and activate a Conda environment:**  
   conda create \--name weather\_app python=3.9 \-y  
   conda activate weather\_app

3. **Install the required libraries:**  
   pip install \-r requirements.txt

4. **Set up your API Key:**  
   * Create a file named .streamlit/secrets.toml.  
   * Add your Google Gemini API key to this file:  
     GOOGLE\_API\_KEY \= "YOUR\_API\_KEY\_HERE"

5. **Run the application:**  
   streamlit run app.py  

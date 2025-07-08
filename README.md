# 🌍 Air Quality Dashboard

An interactive, real-time air quality monitoring dashboard built with Streamlit and Plotly. Visualize and track air quality metrics from locations worldwide with a beautiful, responsive interface that supports both light and dark modes.

## ✨ Features

- **Real-time Air Quality Data**: Get current air quality metrics (AQI, PM2.5, PM10, NO₂, O₃, etc.)
- **Global Location Support**: Search and track air quality for any location worldwide
- **Beautiful Visualizations**: Interactive charts and maps for better data understanding
- **Responsive Design**: Works perfectly on all devices from mobile to desktop
- **Dark/Light Mode**: Toggle between themes for comfortable viewing in any lighting
- **Weather Integration**: View current weather conditions alongside air quality data

## 🚀 Quick Start

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/air-quality-dashboard.git
   cd air-quality-dashboard
   ```

2. Create and activate a virtual environment (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install the required packages:
   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file and add your OpenWeatherMap API key:
   ```
   OPENWEATHER_API_KEY=your_api_key_here
   ```

5. Run the dashboard locally:
   ```bash
   streamlit run app.py
   ```

## 🌐 Deployment

### Streamlit Cloud (Recommended)

1. Push your code to a GitHub repository
2. Go to [Streamlit Cloud](https://share.streamlit.io/)
3. Click "New app" and select your repository
4. Set the branch to `main` and the main file to `app.py`
5. Add your environment variables in the "Advanced settings"
6. Click "Deploy!"

### Other Platforms

This app can also be deployed on:
- Heroku
- Render
- Google Cloud Run
- AWS Elastic Beanstalk
- Any platform that supports Python web applications

## 🔧 Dependencies

- Python 3.8+
- Streamlit
- Pandas
- Plotly
- Geopy
- Requests
- Python-dotenv

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Data provided by OpenWeatherMap API
- Built with ❤️ using Streamlit

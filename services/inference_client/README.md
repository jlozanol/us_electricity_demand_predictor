# US Electricity ML Training

A machine learning pipeline for predicting electricity demand across various US regions, based on data from the U.S. Energy Information Administration (EIA). The project includes automated data processing, model artifact retrieval from a model registry, and an interactive Streamlit dashboard for real-time visualization and analysis.

## Features

- **Regional Electricity Forecasting**: Predict electricity demand for different US regions
- **Automated Feature Engineering**: Transform raw electricity data into ML-ready features
- **XGBoost Integration**: Uses gradient boosting for accurate predictions
- **Interactive Dashboard**: Streamlit web application for data visualization
- **Flexible Architecture**: Modular design for easy extension and customization

## Project Structure

```
├── src/
│   ├── main.py              # Main pipeline and Streamlit app entry point
│   ├── config.py            # Configuration parameters for the main pipeline
│   ├── feature_creator.py   # Feature engineering utilities
│   ├── model_fetcher.py     # Model configuration and instantiation
│   └── plots.py             # Visualization and plotting functions
│   ├── models
│       ├── xgboost_model.py # Computation of the predicted electricity demand
├── model_artifacts/                  # Saved model artifacts
└── README.md
```

## Quick Start

### Prerequisites

- Python 3.8+
- Required packages (see Installation)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd us-electricity-ml-predictions
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```
   
   Or install manually:
   ```bash
   pip install streamlit pandas scikit-learn xgboost matplotlib seaborn numpy
   ```

## Configuration

Create a `.env` file with the following variables:

```env
REGION_NAMES=["CAL", "CAR", "CENT", "FLA", "MIDW", "NW", "NY", "SW"]
MODEL_STATUS=Production
HOURS_BACK=450
```

Create a `credentials.env` file with the following variables:

```credentials.env
COMET_API_KEY=your_comet_api_key
COMET_PROJECT_NAME=your_comet_project_name
COMET_WORKSPACE=your_comet_workspace_name
EIA_API_KEY=your_eia_api_key
```

### Running the Application

**Launch the Streamlit dashboard:**
```bash
streamlit run src/main.py
```

The application will open in your browser at `http://localhost:8501`

## Usage

### Interactive Dashboard

The Streamlit dashboard provides a comprehensive interface for electricity demand forecasting and analysis:

**Data Integration**
- **Automated Model Loading**: Downloads and loads pre-trained XGBoost models from the model registry
- **Real-time Data Fetching**: Queries the latest electricity and weather data from multiple sources:
  - **EIA API**: Historical and current electricity consumption data across US regions
  - **OpenMeteo API**: Current and forecasted weather conditions for corresponding regions
- **Data Synchronization**: Automatically aligns electricity and weather data by timestamp and region

**Prediction & Analysis**
- **On-demand Forecasting**: Generates electricity demand predictions using the latest available data
- **Multi-source Comparison**: Enables side-by-side analysis of:
  - **Actual consumption** (historical EIA data)
  - **Official EIA forecasts** (when available)
  - **ML model predictions** (XGBoost-generated forecasts)

**Visualization & Interaction**
- **Regional Selection**: Interactive dropdown to choose specific US electricity regions
- **Comparative Plotting**: Dynamic charts showing actual vs. predicted vs. official forecasts

## Data Requirements

The model expects electricity data with:
- Timestamp information
- Regional identifiers
- Historical electricity demand/consumption values acquired from EIA's API
- Weather data, acquired from openmeteo's API

## API Configuration
The application handles data acquisition automatically, but requires:

- EIA API Key: Free registration at EIA.gov
- OpenMeteo Access: No key required for standard usage limits
- Internet Connection: For real-time data fetching and model updates



## Contributing

We welcome contributions! Please:
1. Fork the repository
2. Create a feature branch
3. Submit a pull request with clear descriptions

For bug reports or feature requests, please open an issue.
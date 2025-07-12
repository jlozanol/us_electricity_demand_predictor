# US Electricity Demand Forecasting System

## Project Overview

This project implements a modular, end-to-end electricity demand forecasting system for the United States. Designed with scalability, automation, and real-time capabilities in mind, it supports reliable demand predictions by integrating data ingestion, feature engineering, model training, inference, and visualization pipelines. Built using modern MLOps practices, the system ensures high-quality predictions, simplified deployments, and continuous improvement.

---

## Business Problem

Power utilities in the U.S. face significant operational challenges due to unpredictable fluctuations in electricity demand:

- ⚡ **Overproduction** leads to energy waste and higher generation costs.  
- ⚠️ **Shortages** can result in brownouts or blackouts, reducing service reliability.  
- 🌍 **Inefficient resource allocation** increases carbon emissions and harms sustainability goals.

The ability to **predict hourly electricity demand across multiple U.S. regions** is essential for operational efficiency, grid stability, and cost control.

---

## ML Problem

Build an accurate, scalable ML system to predict **next-hour electricity demand** across U.S. regions based on recent demand and weather data. The model should learn regional consumption patterns and respond to external conditions such as holidays and temperature changes.

---

## Data Sources

The system integrates publicly available data sources for demand and weather analytics:

- 🏛 **Electricity Demand**: Hourly historical demand from the [U.S. EIA API](https://www.eia.gov/opendata/)  
- 🌦 **Weather Data**: Temperature, humidity, wind speed, and precipitation from the [Open-Meteo API](https://open-meteo.com/)

Both datasets are processed in batch and real-time modes and stored in a **Hopsworks Feature Store** for model training and inference.

---

## Architecture & Pipeline Philosophy

This project adopts a **three-pipeline architecture**, promoting modularity, maintainability, and real-time readiness:

### ⚙️ 1. Ingestion Pipeline  
- **Goal**: Collect raw demand and weather data from external APIs.
- **Microservices**: `ingest_demand`, `ingest_weather`
- **Transport Layer**: Kafka (via Quix Streams)

### 🔍 2. Feature Engineering & Storage Pipeline  
- **Goal**: Enrich raw data with time-based and statistical features, and persist in a ML feature store.
- **Microservices**: `feature_demand`, `to_featurestore_demand`, `to_featurestore_weather`
- **Store**: Hopsworks Feature Store (supports historical and live pipelines)

### 🧠 3. Modeling & Inference Pipeline  
- **Goal**: Train region-specific ML models and generate demand forecasts in real-time.
- **Microservices**: `demand_predictor`, `inference_client` (Streamlit dashboard)
- **Model Registry**: Comet ML

---

### 📊 Architecture Diagram

```plaintext
            +---------------------+         +----------------------+
            |   EIA API           |         |   Open-Meteo API     |
            +---------------------+         +----------------------+
                      |                             |
                      v                             v
           +------------------+           +------------------+
           | ingest_demand    |           | ingest_weather   |
           +------------------+           +------------------+
                      |                             |
                      | Kafka                       | Kafka
                      v                             v
           +--------------------+        +-------------------------+
           | feature_demand     |        | to_featurestore_weather |
           +--------------------+        +-------------------------+
                      |                             |
                      | Kafka                       |
                      v                             |
         +-------------------------+                |
         | to_featurestore_demand  |                |
         +-------------------------+                |
                      |                             |
                      v                             |
         +--------------------------+               |
         |  Hopsworks Feature Store |<--------------+
         +--------------------------+
                      |
                      v
            +----------------------+
            |  demand_predictor    |
            +----------------------+
                      |
                      v
         +----------------------------+
         |   Comet ML (Model Registry)|
         +----------------------------+
                      |
                      v
            +----------------------+
            |   inference_client   |
            |  (Streamlit App)     |
            +----------------------+
```

---

## Microservices Breakdown

### 1. Data Ingestion Services

- `ingest_demand`: Fetches electricity metrics from EIA API and streams to Kafka  
- `ingest_weather`: Fetches weather data from Open-Meteo API and streams to Kafka

### 2. Feature Engineering & Storage

- `feature_demand`: Enriches demand data with time and statistical features  
- `to_featurestore_demand`: Persists demand features in Hopsworks  
- `to_featurestore_weather`: Persists weather features in Hopsworks

### 3. Model Training & Inference

- `demand_predictor`: Trains XGBoost models with Comet ML tracking  
- `inference_client`: Provides an interactive Streamlit dashboard for forecasts

---

## Deployment & Monitoring

Each microservice is container-ready and follows `.env`-based configuration. Kafka (via Redpanda or Confluent) connects ingestion and feature pipelines. Hopsworks is the central feature store, and Comet ML is used for model registry and tracking.

> 🔧 **Planned Enhancements**  
> - Live streaming for all microservices  
> - Prometheus/Grafana observability  
> - CI/CD automation and retraining workflows  
> - REST-based inference API

---

## Summary

This project delivers a modular and production-ready pipeline for electricity demand forecasting with the following benefits:

- 🧠 **ML-Powered Predictions**: Accurate XGBoost models trained on region-specific features  
- 🔁 **Streaming Architecture**: Kafka-powered ingestion and processing for real-time scalability  
- 📦 **Feature & Model Store**: Centralized and reusable assets via Hopsworks and Comet ML  
- 📈 **Interactive App**: Easy-to-use dashboard for visualization and model evaluation  
- ⚙️ **MLOps Best Practices**: CI-ready, reproducible, and extensible services  

---

## Contact

For questions, collaboration, or suggestions, feel free to reach out:

- 📧 Email: [jlozanol@protonmail.com](mailto:jlozanol@protonmail.com)  
- 🔗 LinkedIn: [linkedin.com/in/jorgelozanol](https://www.linkedin.com/in/jorgelozanol)

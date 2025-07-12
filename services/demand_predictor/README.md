# Demand Predictor Service

## Overview

The service `demand_predictor` retrieves historical electricity demand and weather data from the [Hopsworks Feature Store](https://docs.hopsworks.ai/), trains a machine learning model using XGBoost, and registers the trained model in the [Comet ML Model Registry](https://www.comet.com/docs/v2/guides/model-management/model-registry/) for downstream use in real-time demand prediction systems.

---

## 📌 Overview

### What it does
- Connects to **Hopsworks** to retrieve time-aligned electricity demand and weather data via feature views.
- Trains a forecasting model (XGBoost regressor) on the retrieved dataset.
- Runs hyperparameter tuning with cross-validation.
- Logs experiments and evaluation metrics to **Comet ML**.
- Uploads the trained model artifact to **Comet ML Model Registry** under a given model name and version.

### Primary Use Case
The trained model is intended to be used for **real-time electricity demand prediction** based on live weather and recent demand data.

---

## 🗂️ Project Structure

- `main.py`: Main training pipeline. Loads features, trains models (XGBoost and optionally a dummy baseline), evaluates metrics, logs to Comet ML, and saves the model.
- `feature_reader.py`: Handles all Hopsworks interactions. Builds or retrieves a feature view by joining electricity demand and weather data.
- `config.py`: Defines and validates configuration schema using `pydantic`. Reads from environment or `.env` files.

---

## ⚙️ Configuration

Configuration is managed via `pydantic` and environment variables. You can set these in a `.env` file or pass them in directly.

Key parameters:
- `feature_view_name` / `feature_view_version`
- Feature group names and versions for demand and weather data
- List of `region_names` (must be within a valid set like `CAL`, `TEX`, `NW`, etc.)
- `hyperparameter_tuning_search_trials` and `hyperparameter_tuning_n_splits`
- `days_back`: Restricts training data to only recent days
- `debug_mode`: Enables debug-specific logging and output behavior

---

## 🚀 How to Run

```bash
python main.py
```

Or integrate `main()` in another Python script, passing in arguments programmatically.

Expected parameters for `main()`:
```python
main(
    hopsworks_project_name="your-project",
    hopsworks_api_key="your-key",
    comet_ml_api_key="your-key",
    comet_ml_project_name="your-comet-project",
    feature_view_name="your-feature-view",
    feature_view_version="your-version",
    demand_feat_group_name="your-feaure-group",
    demand_feat_group_version="your-version",
    weather_feat_group_name="your-feature-group",
    weather_feat_group_version="your-version",
    region_names=["CAL", "TEX", ...],  # Example regions
    hyperparameter_tuning_search_trials=int,
    hyperparameter_tuning_n_splits=int,
    model_status="your-model-status",
    days_back=int,
    debug_mode=False,
)
```

---

## ✅ Outputs

- Model performance metrics: MAE, RMSE, R²
- XGBoost model saved locally and registered in **Comet ML**
- Optional debug datasets saved to output path

---

## 🔒 Credentials

Credentials for Hopsworks and Comet ML should be provided via environment variables or through a secure `.env` file. The `ServicesCredentials` class in `config.py` is used to access them safely.

---

## 📦 Dependencies

- `hopsworks` and `hsfs`
- `comet_ml`
- `xgboost`
- `pydantic`, `pydantic-settings`
- `joblib`, `pandas`, `scikit-learn`
- `loguru` for logging

Install via:

```bash
pip install -r requirements.txt
```

---

## 🧩 Notes

- The microservice assumes feature views are correctly set up in Hopsworks. If not found, it attempts to create one.
- Region names must be from a predefined list (`VALID_REGIONS` in `config.py`).
- Dummy model is used as a simple baseline for comparison with XGBoost performance.

---

## License

MIT License

---

## Contact

For issues or collaboration, contact: `jlozanol@protonmail.com`

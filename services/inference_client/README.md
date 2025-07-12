# Forecasting and Visualization Pipeline (Streamlit App)

This project provides a modular pipeline for generating features, retrieving machine learning models, making time series predictions, and visualizing outputs through an interactive **Streamlit** interface.

---

## 📁 Project Structure

```
.
├── main.py              # Streamlit app entry point
├── config.py            # Configuration variables and constants
├── feature_creator.py   # Feature engineering for model inputs
├── model_fetcher.py     # Downloads pre-trained models (e.g., from Comet ML)
├── utils.py             # Utility functions for preprocessing and formatting
├── plots.py             # Visualization routines for prediction outputs
```

---

## 🧩 Module Overview

### `main.py`
Streamlit application entry point. It:
- Loads app configuration.
- Retrieves a trained model for a selected region.
- Builds features from input data.
- Generates predictions.
- Displays results with visualizations and metrics.

### `config.py`
Contains shared configuration:
- File paths
- API credentials
- Region and model mappings

### `feature_creator.py`
Encapsulates the logic for transforming raw input into model-ready features, including:
- Time-based features (hour, weekday)
- Lag and rolling statistics
- Weather data integration (if configured)

### `model_fetcher.py`
Handles the loading of machine learning models from Comet ML.

### `utils.py`
General-purpose utility functions, such as:
- Timestamp conversion
- File handling
- Display helpers

### `plots.py`
Creates charts to visualize predictions and feature trends. Used within the Streamlit interface.

---

## 🚀 Running the Streamlit App

To launch the app locally:

```bash
streamlit run main.py
```

> 📌 Make sure your environment is activated and all dependencies are installed.

---

## 📦 Requirements

This app relies on the following Python packages (among others):

- `streamlit`
- `pandas`
- `numpy`
- `matplotlib` or `plotly`
- `scikit-learn`
- `comet_ml` (if using model tracking)

You can install the dependencies with:

```bash
pip install -r requirements.txt
```

Or manually:

```bash
pip install streamlit pandas numpy matplotlib scikit-learn comet_ml
```

---

## 📌 Notes

- Ensure your configuration in `config.py` is correct (especially for file paths and API credentials).
- The application is modular and supports multiple **regions** with corresponding ML models.
- Designed to support real-time or near-real-time prediction pipelines via interactive input and visualization.

---

## Future Enhancements

- 📦 Add batching and backpressure support.
- 🧪 Add schema validation for incoming messages.
- 🚀 Add inference pipeline integration for end-to-end deployment.
- 🔧 Make transformations configurable (e.g., via YAML or JSON files).

---

## License

MIT License

---

## Contact

For issues or collaboration, contact: `jlozanol@protonmail.com`

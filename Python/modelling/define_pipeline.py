import numpy as np
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import OneHotEncoder, RobustScaler
from sklearn.pipeline import Pipeline
from xgboost import XGBClassifier


def define_pipeline(X, model_hyperparameters):
    """
    Doel: definieer de pipeline hier. Alle scripts en functies die de pipeline gebruiken
          zullen deze gebruiken
    Input:
        - X: dataframe waar alleen de feature kolommen bij zitten. X bepaalt welke
              features de pipeline zal gebruiken en verwachten
        - Model_hyperparameters: Per clustermodel hyperparameters uit de model.settings die worden gebruikt
    Output:
        - pipeline: sklearn pipeline gedefinieerd met alle verschillende stappen en hyperparameters
    """
    cat_columns = list(X.select_dtypes(include=["object", "category", "boolean"]))

    num_columns = list(X.select_dtypes(include=["number"]))

    categorical_transformer = Pipeline(
        steps=[
            (
                "imputer",
                SimpleImputer(
                    missing_values=np.nan, strategy="most_frequent", add_indicator=False
                ),
            ),
            (
                "encoder",
                OneHotEncoder(
                    handle_unknown="ignore", min_frequency=0.05, sparse_output=False
                ),
            ),
        ]
    )

    numeric_transformer = Pipeline(
        steps=[
            (
                "imputer",
                SimpleImputer(
                    missing_values=np.nan, strategy="median", add_indicator=False
                ),
            ),
            ("scaler", RobustScaler()),
        ]
    )

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", numeric_transformer, num_columns),
            ("cat", categorical_transformer, cat_columns),
        ]
    )

    model = XGBClassifier(**model_hyperparameters)

    pipeline = Pipeline(steps=[("transform", preprocessor), ("classifier", model)])

    pipeline.set_output(transform="pandas")

    return pipeline

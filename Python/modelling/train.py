import traceback
from pathlib import Path
from D_modelling.define_pipeline import define_pipeline
import os
import pickle
import logging
from Z_utilities.unify_cwd import unify_cwd


def train_model(df, poli, feature_list, model_hyperparameters):
    """
    Doel: train een model voor een poli
    Input:
        - df: dataframe waar de train dataset in zit
        - poli: polikliniek waar het model voor getrain moet worden, uit model_settings
        - feature_list: lijst met features om het model op te trainen, uit model_settings
        - model_hyperparameters: lijst met hyperparameters voor het model
    Output:
        - getraind model voor opgegeven polikliniek wordt opgeslagen in de models map
    """
    logger = logging.getLogger()
    logger.info(f"\nTrain voor polikliniek {poli}")

    y = df["voldaan_af"]
    X = df[feature_list]

    pipeline = define_pipeline(X, model_hyperparameters)
    try:
        pipeline.fit(X, y, classifier__sample_weight=df["weights"])
    except:
        pipeline.fit(X, y)
    cwd = Path.cwd()
    cwd = unify_cwd(cwd)

    path = cwd / "Python" / "models"
    # Check whether the specified path exists or not
    isExist = os.path.exists(path)

    if not isExist:
        # Create a new directory because it does not exist
        os.makedirs(path)
        logger.info(f"Map {path.as_posix()} aangemaakt")

    logger.info(f"Model opslaan voor {poli}")
    logger.info(f"Model hyperparameters voor {poli}: {model_hyperparameters}")
    filename = cwd / "Python" / "models" / ("trained_model_" + poli + ".pkl")
    pickle.dump(pipeline, open(filename, "wb"))


def train_all_models(df, polis, model_hyperparameters, feature_list, modelclusters):
    """
    Doel: train alle modellen, zowel de losse polis als de clustermodellen
    Input:
        - df: dataframe waar de train dataset in zit
        - poli: polikliniek waar het model voor getrain moet worden, uit model_settings
        - model_hyperparameters: dict met de gefinetunede hyperparameters voor elk model
        - feature_list: lijst met features om het model op te trainen, uit model_settings
        - modelclusters: lijst met alle poli-cluster mappings
    Output:
        - getrainde modellen voor opgegeven poliklinieken/clusters wordt opgeslagen in de models map
    """
    logger = logging.getLogger()
    for poli in polis:
        try:
            poli_hyperparameters = model_hyperparameters[f"{poli}"]
            df_poli = df.loc[df["polikliniek"] == poli, :].copy()
            train_model(
                df_poli, poli, feature_list, model_hyperparameters=poli_hyperparameters
            )
        except:
            fout = traceback.format_exc()
            logger.warning("Model voor polikliniek {} niet kunnen trainen".format(poli))
            logger.error("Foutmelding: {}".format(fout))
    for clusterkey, clusterlist in modelclusters.items():
        # per cluster de hyperparameters vanuit model.settings inlezen, de modelhyperparametersnaam is gelijk aan de clusterkey, bv SKZ
        clusterkey_hyperparameters = model_hyperparameters[f"{clusterkey}"]
        df_cluster = df.loc[df["polikliniek"].isin(clusterlist), :].copy()
        train_model(df_cluster, clusterkey, feature_list, clusterkey_hyperparameters)

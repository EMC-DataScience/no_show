import logging
import pandas as pd
from datetime import timedelta
import datetime
import json
from pathlib import Path
import os
from utilities.unify_cwd import unify_cwd


def init_modelsettings(*args):
    """
    Initialiseer de main. Dit bestaat voornamelijk uit het inlezen van de model_settings.json
    en die om te zetten in een aantal losse parameters als output
     Input:
    Geen, maar neemt wel aan dat model_settings.json in dezelfde map staat als init_main

    Output:
        - modus: de modus waar de main in gerund moet worden
        - models: lijst met poliklinieken waar we de main voor willen runnen
        - hyperparameters: hyperparameters per model
        - poliklinieken: vertaling van polikliniek naam naar agenda codes
        - feature_list: lijst met alle features die we willen meenemen bij de berekeningen
        - datum_range: dict met de datum range per modus waar de sql query op gerund moet worden
        - afspr_gesch: aantal dagen dat we terugkijken om de afspraakgeschiedenis van een patient te bepalen
        - beldienst_param: dict met parameters nodig om beldienst metrieken uit te rekenen
    """
    logger = logging.getLogger()
    # Laad de settings in
    cwd = Path.cwd()
    cwd = unify_cwd(cwd)

    with open(cwd / "Python" / "model_settings.json", "r", encoding="utf-8") as f:
        settings = json.load(f)
    modus = os.getenv("MODUS")
    logger.info(f"Pipeline modus: {modus}")
    if not modus:
        # De modus waar we de main op gaan uitvoeren
        modus = settings["modus"]
    settings["modus"] = modus
    logger.info(f"Modus: {modus}")
    # De lijst met de verschillende modellen die we willen trainen
    models = settings.get("models")
    logger.info(f"Main afvuren voor de modellen: {models}")

    # De dict die de polikliniek naar aan agenda codes koppelt
    agendas = settings.get("agendas")
    # De dict die de polikliniek naar aan agenda codes koppelt
    subagendas = settings.get("subagendas")
    # Pak alleen de poliklinieken/agenda codes die in models voorkomen
    poliklinieken = {}
    if agendas:
        ag = {k: v for (k, v) in agendas.items() if k in models}
        poliklinieken["agendas"] = ag
    if subagendas:
        subag = {k: v for (k, v) in subagendas.items() if k in models}
        poliklinieken["subagendas"] = subag
    settings["poliklinieken"] = poliklinieken

    # Datum range waar we de train data op baseren
    train_range = settings["train_range"]

    # Datum range waar we de holdout data op baseren
    holdout_range = settings["holdout_range"]

    # Datum range voor het project, waar we elke dag een lijst met voorspellingen aan willen toevoegen
    # Tel er een paar dagen bij op, hoe doen we het met het weekend?
    # maandag   bel je donderdag
    # dinsdag   bel je vrijdag
    # woensdag  bel je maandag en het weekend
    # donderdag bel je dinsdag
    # vrijdag   bel je woensdag
    beldagen = {1: 3, 2: 3, 3: 5, 4: 5, 5: 5}
    weekdag = datetime.datetime.weekday(datetime.datetime.now()) + 1
    if weekdag < 6:
        beldag = datetime.datetime.now() + timedelta(days=beldagen.get(weekdag))
        beldag_heledag_sql_string = f"{str(beldag.year)}-{('0' + str(beldag.month))[-2:]}-{('0' + str(beldag.day))[-2:]}"
        # Op woensdag bellen we ook voor het hele weekend, dus voor die dag moet de range wat groter
        if weekdag == 3:
            beldag_ondergrens = datetime.datetime.now() + timedelta(
                days=(beldagen.get(weekdag) - 2)
            )
        else:
            beldag_ondergrens = beldag
        beldag_ondergrens = beldag_ondergrens - pd.Timedelta(
            settings["voorspelperiode_in_dagen"] - 1, "D"
        )
        beldag_ondergrens_heledag_sql_string = f"{str(beldag_ondergrens.year)}-{('0' + str(beldag_ondergrens.month))[-2:]}-{('0' + str(beldag_ondergrens.day))[-2:]}"
        voorspel_range = [
            beldag_ondergrens_heledag_sql_string,
            beldag_heledag_sql_string,
        ]
    else:
        logger.info("Het is weekend, dus we doen geen voorspelling.")
        voorspel_range = ["NULL", "NULL"]

    datum_range = {
        "train": train_range,
        "holdout": holdout_range,
        "voorspel": voorspel_range,
    }
    settings["datum_range"] = datum_range

    datums = datum_range.get(modus.split("_")[-1])
    logger.info(f"Datum range: {datums}")

    return settings

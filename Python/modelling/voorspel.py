import pickle
from pathlib import Path
import numpy as np
import pandas as pd
import json
import logging

from A_readwrite.load_data import load_dataset
from A_readwrite.read_data import execute_query_text


def voorspel(df, poli, feature_list):
    """
    Doel: gebruik een getraind model voor een poli om een voorspelling te doen
    Input:
        - df: dataframe waar de voorspelling aan toegevoegd moet worden
        - poli: polikliniek waar het model voor getrain moet worden, uit model_settings
        - feature_list: lijst met features om het model op te trainen, uit model_settings
        - prop_pos: proportie van patienten die we op de bellijst willen hebben (de hoogste x procent)
    Output:
        - df: originele dataframe met 3 extra kolommen
                - predict: basis voorspelling van model (0 of 1)
                - predict_proba: proba voorspelling van het model (getal tussen 0 en 1)
                - predict_bellijst: voorspelling als we prop_pos van de patienten een 1 geven (0 of 1)
    """
    X = df[feature_list]

    cwd = Path.cwd()

    logger = logging.getLogger()
    logger.info(f"Model laden voor {poli}")
    filename = cwd / "Python" / "models" / (f"trained_model_{poli}.pkl")

    pipeline = pickle.load(open(filename, "rb"))

    df.loc[:, "predict"] = pipeline.predict(X).astype(int)
    df.loc[:, "predict_proba"] = pipeline.predict_proba(X)[:, 1]

    return df


def get_pos_labels(y_pred, prop_pos=0.35):
    """
    Doel: de hoogste prop_pos van y_pred omzetten naar een positief label
    Input:
        - y_pred: predicties
        - prop_pos: de proportie van de voorspellingen die in een positief label (1) omgezet moet worden
    Output:
        - y_pred_labels: de labels (0 of 1)
    """

    # de bovenste 35% selecteren op basis van een grens uit quantile vereist wat moeite.
    # zo is bij len(y_pred) == 2 een andere berekening van het quantile nodig dan bij len(y_pred) == 6
    bovengrens = np.quantile(y_pred, 1 - prop_pos, interpolation="higher")
    ondergrens = np.quantile(y_pred, 1 - prop_pos, interpolation="lower")

    bovengrens_gebruiken = (y_pred > ondergrens).mean() > prop_pos

    grens_quantile = bovengrens if bovengrens_gebruiken else ondergrens

    # de positieve labels als er groter dan de grens gebruikt wordt
    pos_klein = y_pred > grens_quantile
    # de positieve labels als er groter dan of gelijk aan de grens gebruikt wordt
    pos_groot = y_pred >= grens_quantile

    # meestal heeft pos_klein te weinig gevallen en pos_groot te veel.
    # dan krijgt pos_klein dus sowieso het positieve label,
    # en van de voorspellingen die wel in pos_groot zitten maar niet in pos_klein
    # wordt de benodigde fractie geselecteerd om op de gewenste prop_pos uit te komen.

    # reken uit hoeveel patienten er gewenst zijn gegeven de prop_pos
    nodig = len(y_pred) * prop_pos

    # aantal voorspellingen in de kleine en grote groepen
    klein = pos_klein.sum()
    groot = pos_groot.sum()

    # hoe groot is de groep met extra patienten waar we er een aantal uit kunnen selecteren?
    extra = (groot - klein).astype(int)

    # hoeveel moeten er geselecteerd worden?
    tekort = nodig - klein

    # wat moet de kans zijn per patient uit de 'extra-groep' dat ze geselecteerd worden?
    if tekort > 0:
        kans_extra = tekort / extra
    else:
        kans_extra = 0

    kans = np.select(
        condlist=[
            pos_klein == True,
            (pos_groot == True) & (pos_klein == False),
            (pos_groot == False) & (pos_klein == False),
        ],
        choicelist=[1, kans_extra, 0],
    )

    y_pred_labels = np.random.binomial(n=1, p=kans)

    return y_pred_labels


def test_controle_split(
    df,
    prop_pos=0.35,
    test_group_fraction=0.5,
    callcenter_fraction=0.5,
    sampling_per_poli_fraction=0.5,
):
    """
    Doel: doe de test controle split op patient niveau
    Input:
        - df: dataframe met de voorspelling die gesplitst moet worden
        - prop_pos: percentage van de patienten dat gebeld moet worden
        - test_group_fraction: percentage van de bellijst dat de testgroep wordt
        - callcenter_fraction: percentage van de testgroep dat de callcentergroep wordt
    Output:
        - df: originele dataframe met 2 extra kolommen
                - bellijst_testgroep: 0 of 1 of de afspraak in testgroep komt
                - bellijst_testgroep_callcenter: 0 of 1 of de afspraak in de callcenter testgroep komt
    """
    if len(df) > 0:
        patienten = (
            df[["patientnr", "polikliniek", "DATUM", "predict_proba"]]
            .sort_values(["patientnr", "DATUM", "predict_proba"])
            .drop_duplicates(subset=["patientnr", "DATUM"], keep="last")
            .reset_index(drop=True)
        )

        if sampling_per_poli_fraction > 0:
            # Splits in 2 groepen, gelijkmatig verdeeeld over alle polis
            patienten_A = patienten.groupby(["DATUM", "polikliniek"]).sample(
                frac=sampling_per_poli_fraction
            )
            patienten_B = patienten.drop(patienten_A.index)

            # A/B test op sampling strategie. A krijgt oude strategie (sample per dag per poli) en B krijgt nieuwe (per dag)
            patienten_A["predict_bellijst"] = patienten_A.groupby(
                ["DATUM", "polikliniek"]
            )["predict_proba"].transform(get_pos_labels, prop_pos=prop_pos)
            patienten_B["predict_bellijst"] = patienten_B.groupby(["DATUM"])[
                "predict_proba"
            ].transform(get_pos_labels, prop_pos=prop_pos)

            # Voeg alleen een kolom toe welke sampling strategie is gebruikt, dan merk je er aan de voorkant niks van maar dan kunnen we wel onze analyse doen
            patienten_A["predict_bellijst_sample_per_poli"] = 1

            patienten = pd.concat([patienten_A, patienten_B])
            patienten["predict_bellijst_sample_per_poli"] = patienten[
                "predict_bellijst_sample_per_poli"
            ].fillna(0)
        else:
            patienten["predict_bellijst"] = patienten.groupby(["DATUM"])[
                "predict_proba"
            ].transform(get_pos_labels, prop_pos=prop_pos)
            patienten["predict_bellijst_sample_per_poli"] = 0

        if patienten["predict_bellijst"].sum() > 0:
            # een gedeelte van de predict_bellijst gaat gebeld worden, de rest is controlegroep
            patienten["bellijst_testgroep"] = np.random.binomial(
                n=1, p=test_group_fraction * patienten["predict_bellijst"]
            )

            # een gedeelte van de bellijst_testgroep gaat door het callcenter gebeld worden, de rest door het studententeam
            patienten["bellijst_testgroep_callcenter"] = np.random.binomial(
                n=1, p=callcenter_fraction * patienten["bellijst_testgroep"]
            )

            df = df.drop(
                columns=[
                    "predict_bellijst",
                    "bellijst_testgroep",
                    "bellijst_testgroep_callcenter",
                ],
                errors="ignore",
            )
            df = df.merge(
                patienten[
                    [
                        "patientnr",
                        "DATUM",
                        "predict_bellijst",
                        "bellijst_testgroep",
                        "bellijst_testgroep_callcenter",
                        "predict_bellijst_sample_per_poli",
                    ]
                ],
                how="left",
                on=["patientnr", "DATUM"],
            )

        else:
            df[
                [
                    "predict_bellijst",
                    "bellijst_testgroep",
                    "bellijst_testgroep_callcenter",
                    "predict_bellijst_sample_per_poli",
                ]
            ] = 0

        return df


def voorspel_clusters(df, polis, modelmapping_voorspel, modelclusters, feature_list):
    """
    Doel: gebruik de getrainde modellen om voor elke poli volgende de aangegeven mapping een voorspelling te doen
    Input:
        - df: dataframe waar de voorspelling aan toegevoegd moet worden
        - polis: poliklinieken waar een voorspelling voor gedaan moet worden
        - modelmapping_voorspel: dict met welk model voor elke poli gebruikt moet worden
        - modelclusters: mapping met welke polis onder welk cluster vallen
        - feature_list: lijst met features om het model op te trainen, uit model_settings
    Output:
        - df: originele dataframe met 3 extra kolommen
                - predict: basis voorspelling van model (0 of 1)
                - predict_proba: proba voorspelling van het model (getal tussen 0 en 1)
                - predict_bellijst: voorspelling als we prop_pos van de patienten een 1 geven (0 of 1)
    """
    df_temp = []
    for poli in polis:
        voorspel_model = modelmapping_voorspel[poli]
        df_poli = df.loc[df["polikliniek"] == poli, :].copy()
        if len(df_poli) > 0:
            if voorspel_model in modelclusters.keys():
                df_temp.append(voorspel(df_poli, voorspel_model, feature_list))
            else:
                df_temp.append(voorspel(df_poli, poli, feature_list))
    df = pd.concat(df_temp)
    return df


def gebelde_patienten_afgelopen_week(DBA_server_settings):
    """
    Doel: Haalt alle patientnummers op die in de afgelopen week al op de bellijst hebben gestaan
    en die ook echt bereikt zijn
    Input:
        - DBA_server_settings: de DBA server waar alle belteam acties worden gelogd
    Output:
        - bereikte_patienten: array met alle patientnummers die de afgelopen week gebeld zijn
    """

    readserver_bellijstapp = DBA_server_settings["server"]
    database_bellijstapp = DBA_server_settings["database"]
    schema_bellijstapp = DBA_server_settings["schema"]

    # Haal de patienten op die gebeld zijn de afgelopen 7 dagen.
    # Er staat -8 dagen in de dateadd omdat Beldatum een datum veld is maar GETDATE() geeft ook een tijd terug
    where_statement = "Beldatum > DATEADD(day, -8, GETDATE())"
    bellijst_df = load_dataset(
        readserver=readserver_bellijstapp,
        database=database_bellijstapp,
        schema=schema_bellijstapp,
        table="Bellijst",
        where=where_statement,
    )
    bellijst_df["Beldatum"] = pd.to_datetime(bellijst_df["Beldatum"])

    patienten_df = load_dataset(
        readserver=readserver_bellijstapp,
        database=database_bellijstapp,
        schema=schema_bellijstapp,
        table="Bellijst_patienten",
    )
    bellijst_df = bellijst_df.merge(
        patienten_df[["ID", "Patientnummer"]],
        how="inner",
        left_on="Patient_ID",
        right_on="ID",
    )

    # Kies alleen de patieten die bereikt zijn om eruit te filteren
    bereikte_patienten = bellijst_df[bellijst_df["Patient_bereikt_ID"] == 1][
        "Patientnummer"
    ].unique()

    return bereikte_patienten


def momenteel_opgenomen_patienten(server_settings):
    """
    Doel: Haalt alle patientnummers op van de patienten die momenteel opgenomen worden
    Input:
        - serversettings
    Output:
        - Lijst patientnummers van de opgenomen patienten
    """

    cwd = Path.cwd()
    query_bestand = cwd / "Python" / "sql_queries" / ("opgenomen_patienten.sql")

    query = query_bestand.as_posix()
    with open(query_bestand, "r", encoding="utf-8") as f:
        query = f.read()

    query = query.replace("@schema", server_settings["readschema"])
    df_patienten = execute_query_text(
        query, server_settings["readserver"], server_settings["readdatabase"]
    )

    return df_patienten["patientnr"].values.tolist()


def patienten_nietbellen(bestandnaam):
    """
    Doel: Haalt alle patientnummers op van de patienten die hebben aangegeven
            dat ze niet gebeld willen worden. Deze staan opgeslagen in
            een json in dezelfde folder als de main

    Output:
        - Lijst patientnummers van de opgenomen patienten
    """

    cwd = Path.cwd()

    path = cwd / "Python" / f"{bestandnaam}"
    with open(path) as f:
        patienten_nietbellen = json.load(f)

    return patienten_nietbellen["patientnrs"]


def voorspelling_voor_bellijst(
    df,
    modelclusters,
    modelmapping_voorspel,
    poliklinieken,
    feature_list,
    beldienst_param,
):
    """
    Doel: Genereer de voorspelling voor de bellijst
    Input:
        - df: dataframe waar de voorspelling aan toegevoegd moet worden
        - modelmapping_voorspel: per poli mapping welk model gebruikt moet worden
        - poliklinieken: poliklinieken waar een voorspelling voor gedaan moet worden
        - feature_list: lijst met features om het model op te trainen, uit model_settings
        - beldienst_param: dict met de beldienst parameters
    Output:
        - df: originele dataframe met de voorspelling

    De voorspelling is ingericht dat een percentage van het aantal patienten wordt gebeld (ipv afspraken).
    Er is zowel een 50/50 splitsing voor controle/test groep gedaan, als ook een 50/50 van de testgroep
    in een groep voor het callcenter en voor het studenten belteam
    """

    # Filter de afspaken eruit waar voldaan ingevuld is (dat zijn geplande maar verplaatste afspraken)
    df = df[df["voldaan_af"].isna()]

    df = voorspel_clusters(
        df, poliklinieken, modelmapping_voorspel, modelclusters, feature_list
    )

    df = test_controle_split(
        df,
        beldienst_param.get("prop_pos"),
        beldienst_param.get("test_group_fraction"),
        beldienst_param.get("callcenter_fraction"),
        beldienst_param.get("sampling_per_poli_fraction"),
    )

    patienten = (
        df[["patientnr", "DATUM", "predict_bellijst", "bellijst_testgroep"]]
        .sort_values(["patientnr", "DATUM", "predict_bellijst", "bellijst_testgroep"])
        .drop_duplicates(subset=["patientnr", "DATUM"], keep="last")
        .copy()
    )
    df = df.drop(columns=["predict_bellijst", "bellijst_testgroep"])
    df = df.merge(patienten, how="left", on=["patientnr", "DATUM"])

    return df


def voorspel_per_dag(df, poli, feature_list, prop_pos=0.35):
    """
    Doel: gebruik een getraind model voor een poli om een voorspelling te doen op de manier zoals dat
            bij de bellijst gaat, namelijk 35% per dag
    Input:
        - df: dataframe waar de voorspelling aan toegevoegd moet worden
        - poli: polikliniek waar het model voor getrain moet worden, uit model_settings
        - feature_list: lijst met features om het model op te trainen, uit model_settings
        - prop_pos: proportie van patienten die we op de bellijst willen hebben (de hoogste x procent)
    Output:
        - df: originele dataframe met 3 extra kolommen
                - predict: basis voorspelling van model (0 of 1)
                - predict_proba: proba voorspelling van het model (getal tussen 0 en 1)
                - predict_bellijst: voorspelling als we prop_pos van de patienten een 1 geven (0 of 1)
    """
    X = df[feature_list]

    cwd = Path.cwd()

    logger = logging.getLogger()
    logger.info(f"Model laden voor {poli}")
    filename = cwd / "Python" / "models" / (f"trained_model_{poli}.pkl")

    pipeline = pickle.load(open(filename, "rb"))

    df.loc[:, "predict"] = pipeline.predict(X).astype(int)
    df.loc[:, "predict_proba"] = pipeline.predict_proba(X)[:, 1]

    # Alle datums die in de dataframe voorkomen
    datums = df["DATUM"].unique()
    # Loop over alle dagen, maak de voorspelling zoals die ingesteld is voor de bellijst en
    # verzamel alle voorspellingen
    df_pred = []
    for datum in datums:
        df_datum = df[df["DATUM"] == datum]
        if len(df_datum) > 0:
            # We willen een percantage van het aantal patienten hebben ipv een percentage van het aantal afspraken
            patienten = (
                df_datum[["patientnr", "polikliniek", "DATUM", "predict_proba"]]
                .sort_values(["patientnr", "DATUM", "predict_proba"])
                .drop_duplicates(subset=["patientnr", "DATUM"], keep="last")
            )
            # van de predict_proba krijgt de bovenste prop_pos het voorspelde label 1
            patienten["predict_bellijst"] = patienten.groupby(["DATUM"])[
                "predict_proba"
            ].transform(get_pos_labels, prop_pos=prop_pos)

            df_datum = df_datum.merge(
                patienten[["patientnr", "DATUM", "predict_bellijst"]],
                how="left",
                on=["patientnr", "DATUM"],
            )
        else:
            df_datum[["predict_bellijst"]] = 0
        df_pred.append(df_datum)

    df_pred = pd.concat(df_pred)

    return df_pred

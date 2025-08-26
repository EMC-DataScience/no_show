import pandas as pd


def filter_afspraken(
    df, datum_range, polis, afspraakcodes, subagendas_exclude, alle_polis=False
):
    """
    Doel: in de originele dataframe zit de afspraakgeschiedenis nog in. Filter hier
            naar alleen de afspraken in de opgegeven tijdsperiode
    Input:
        - df: dataframe waar alle features bij zijn aangemaakt
        - datum_range: datum range waar we eerder in de query hadden ingevuld waar we naar willen kijken
        - polis_dict: dict met alle poliklinieken/agenda codes
    Output:
        - df: dataframe gefilterd zodat alleen de relevante rijen nog over zijn
    df kan gebruikt worden om een model op te trainen of een voorspelling over te doen
    """
    # Als de arts (of het ziekenhuis) de reden is dan willen we er niet op trainen
    df = df[(df["voldaan_af"].isna()) | (df["voldaan_af"].isin(["J", "N"]))]
    df["voldaan_af"] = df["voldaan_af"].replace({"J": 0, "N": 1})

    # Filter op tijdsperiode waar we naar kijken
    lower_bound = pd.to_datetime(datum_range[0], format="%Y-%m-%d")
    upper_bound = pd.to_datetime(datum_range[1], format="%Y-%m-%d")
    date_mask = (df["DATUM"] >= lower_bound) & (df["DATUM"] <= upper_bound)
    df = df.loc[date_mask]
    # Filter op de poliklinieken waar we naar willen kijken
    if not alle_polis:
        df = df.loc[df["polikliniek"].isin(polis)]
    # Afspraken die minder dan een week vooruit zijn gepland willen we niet voor bellen
    df = df[df["dagen_tot_afspraak"] >= 7]
    # Afspraakhorizon van 3 maanden
    df = df[df["dagen_tot_afspraak"] < 90]

    df = df[(df["contacttype"] == "F") & (df["zonder_patient"] == 0)]
    # In de model_settings.json staat een lijst met agenda en bijbehorden afspraakcodes (geleverd door poliklinieken zelf)
    # waar met geen herinnering over wil. Deze zijn dus wel meegenomen in de preprocess en featurebuilding,
    # maar moeten uit de dataset
    for poli, code_dict in afspraakcodes.items():
        codes = code_dict.get("codes")
        include = code_dict.get("include")
        if include == "False":
            mask = (df["polikliniek"] == poli) & (df["CODE"].isin(codes))
        if include == "True":
            mask = (df["polikliniek"] == poli) & (~df["CODE"].isin(codes))
        df = df[~mask]

    for poli, code_dict in subagendas_exclude.items():
        codes = code_dict.get("subagendas")
        include = code_dict.get("include")
        if include == "False":
            mask = (df["polikliniek"] == poli) & (df["subagenda"].isin(codes))
        if include == "True":
            mask = (df["polikliniek"] == poli) & (~df["subagenda"].isin(codes))
        df = df[~mask]

    return df

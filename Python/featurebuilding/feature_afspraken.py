from datetime import datetime, timedelta
from workalendar.europe import NetherlandsWithSchoolHolidays as NL
import pandas as pd
import numpy as np

# from meteostat import Point, Daily, Hourly
import logsetup
import logging

import geopy.distance
from A_readwrite.load_data import load_dataset
import pickle
from pathlib import Path
from Z_utilities.unify_cwd import unify_cwd


def afstand_tot_ziekenhuis(df):
    """
    Functie die de afstand bepaald tussen de geregistreerde postcode van de patient
    en het ziekenhuis
    """
    logsetup.setup_logging()
    logger = logging.getLogger()

    logger.info("Postcodes inladen")
    cwd = Path.cwd()
    cwd = unify_cwd(cwd)
    postcodetabel_pkl = cwd / "Python" / "postcodes.pkl"
    # De lijst met alle postcodes is best flink, staat in de database maar als de
    # code een keer correct is doorlopen wordt het ook al pickle opgeslagen, dat
    # maakt de code een stuk sneller
    if postcodetabel_pkl.is_file():
        df_postcodes = pickle.load(open(postcodetabel_pkl, "rb"))
    else:
        logger.info("Postcodes pickle niet gevonden, laadt in uit database")
        df_postcodes = load_dataset(
            readserver="Annemarie",
            database="dena",
            schema="dbo",
            table="REF_Postcode_NL",
        )
        df_postcodes = (
            df_postcodes[["postcode", "lon", "lat"]]
            .sort_values(["postcode", "lon"])
            .drop_duplicates(subset=["postcode"], keep="first")
        )
        df_postcodes["postcode"] = df_postcodes["postcode"].apply(
            lambda x: x[:4] + " " + x[-2:]
        )
        pickle.dump(df_postcodes, open(postcodetabel_pkl, "wb"))

    # Pak alleen de postcodes uit de lijst die in het dataframe voorkomen
    df_postcodes = df_postcodes[df_postcodes["postcode"].isin(df["postcode"].unique())]
    # Bepaal de afstand
    coords_EMC = geopy.distance.lonlat("4.5301190909178", "51.955118652773")
    df_postcodes["distance"] = df_postcodes[["lon", "lat"]].apply(
        lambda x: geopy.distance.distance(
            geopy.distance.lonlat(x["lon"], x["lat"]), coords_EMC
        ).m,
        axis=1,
    )
    # lat en lon kolommen kunnen nu weg
    df_postcodes = df_postcodes.drop(columns=["lon", "lat"])
    # Merge op originele dataframe
    df = df.merge(df_postcodes, how="left", left_on="postcode", right_on="postcode")

    return df


def vakantie_check(df):
    """
    Deze functie genereert voor elk jaar de lijst met vakantiedagen en voegt toe
    of een afspraak op een vakantie dag valt
    """
    logger = logging.getLogger()

    # lijst met alle relevantie vakantiedatums aanmaken
    calendar = NL(region="middle", carnival_instead_of_spring=False)

    # De jaren waar overheen geloopt moet worden
    jaren = sorted(pd.DatetimeIndex(df["DATUM"]).year.unique().tolist())

    # Haal per jaar alle vakantiedagen op en maak er 1 grote lijst van
    for jaar in jaren:
        try:
            holiday_list_jaar = np.array(calendar.holidays(jaar))

            # Voeg een paar feestdagen toe die er niet in stonden
            extra1 = np.array(
                [
                    (
                        holiday_list_jaar[
                            holiday_list_jaar[:, 1] == "Ascension Thursday"
                        ][0, 0]
                        + timedelta(1),
                        "Ascension Friday",
                    )
                ]
            )
            extra2 = np.array(
                [
                    (
                        holiday_list_jaar[holiday_list_jaar[:, 1] == "Boxing Day"][0, 0]
                        - timedelta(21),
                        "Sinterklaas",
                    )
                ]
            )
            holiday_list_jaar = np.append(holiday_list_jaar, extra1, axis=0)
            holiday_list_jaar = np.append(holiday_list_jaar, extra2, axis=0)

            if jaar == min(jaren):
                holiday_list = holiday_list_jaar
            else:
                holiday_list = np.append(holiday_list, holiday_list_jaar, axis=0)
        except:
            logger.info(f"Voor jaar {jaar} de vakantiedagen niet kunnen ophalen")
    # Zet in dataframe
    df_holiday = pd.DataFrame({"DATUM": pd.to_datetime(holiday_list[:, 0])})
    df_holiday = df_holiday.drop_duplicates(subset=["DATUM"])
    # Feature maken of de datum in een vakantie valt
    df_holiday["vakantie"] = True
    df = df.merge(df_holiday, how="left", on="DATUM")
    df["vakantie"] = df["vakantie"].fillna(False)

    return df


def rolling_count_time_window(df_join, window_size, time_col, count_cols):
    """
    Functie om een kolom op te tellen binnen een tijdsraam, rekening houdend met de vertragin
    van de beldienst
    Input
    - df_join: dataframe waar de telling over gedaan moet worden
    - window_size: grootte van het tijdsraam in aantal dagen
    - time_col: de tijdskolom waar de telling op gebaseerd is
    - count_col: de kolom waar de telling over gedaan moet worden

    Output:
    - df_join met een extra kolom (rolling_count_(count_col)) met de telling binnen het tijdsraam
    """

    # Maak een kopie van het dataframe waar we de tellingen op gaan doen en
    # daarna terug-joinen op het originele dataframe
    df_rol = df_join[["patientnr", "afspraaknr", time_col] + count_cols].copy()

    # Bepaal de rolling count over 1 jaar
    df_rol_year = (
        df_rol.drop(columns=["afspraaknr"])
        .groupby("patientnr", as_index=False)
        .rolling(window=f"{window_size}D", on=time_col)
        .sum()
    )
    # Om de dagen uit te sluiten tussen bellen en plaatsvinden kunnen we de rolling
    # counts van 3/4/5 dagen van de grotere rolling count aftrekken (afhankelijk van de weekdag)
    df_rol_3 = (
        df_rol.drop(columns=["afspraaknr"])
        .groupby("patientnr", as_index=False)
        .rolling(window="3D", on=time_col)
        .sum()
    )
    df_rol_4 = (
        df_rol.drop(columns=["afspraaknr"])
        .groupby("patientnr", as_index=False)
        .rolling(window="4D", on=time_col)
        .sum()
    )
    df_rol_5 = (
        df_rol.drop(columns=["afspraaknr"])
        .groupby("patientnr", as_index=False)
        .rolling(window="5D", on=time_col)
        .sum()
    )

    # Zet de counts in hetzelfde dataframe
    df_rol[[f"rolling_count_365_{x}" for x in count_cols]] = df_rol_year[count_cols]
    df_rol[[f"rolling_count_3_{x}" for x in count_cols]] = df_rol_3[count_cols]
    df_rol[[f"rolling_count_4_{x}" for x in count_cols]] = df_rol_4[count_cols]
    df_rol[[f"rolling_count_5_{x}" for x in count_cols]] = df_rol_5[count_cols]

    # Join de count terug
    df_join = df_join.merge(
        df_rol.drop(columns=count_cols),
        how="left",
        on=["patientnr", "afspraaknr", time_col],
    )

    # Bepaal, afhankelijk van de weekdag, welke kolommen gebruikt moeten worden om de uiteindelijke
    # count te bepalen
    for count_col in count_cols:
        df_join.loc[
            df_join[time_col].apply(datetime.weekday).isin([0, 1, 2]),
            f"rolling_count_{count_col}",
        ] = (
            df_join[f"rolling_count_365_{count_col}"]
            - df_join[f"rolling_count_5_{count_col}"]
        )
        df_join.loc[
            df_join[time_col].apply(datetime.weekday).isin([3, 4, 5]),
            f"rolling_count_{count_col}",
        ] = (
            df_join[f"rolling_count_365_{count_col}"]
            - df_join[f"rolling_count_3_{count_col}"]
        )
        df_join.loc[
            df_join[time_col].apply(datetime.weekday).isin([6]),
            f"rolling_count_{count_col}",
        ] = (
            df_join[f"rolling_count_365_{count_col}"]
            - df_join[f"rolling_count_4_{count_col}"]
        )

        # Gooi de kolommen weg die in deze functie gemaakt zijn maar hierna niet meer relevant
        df_join = df_join.drop(
            columns=[
                f"rolling_count_365_{count_col}",
                f"rolling_count_3_{count_col}",
                f"rolling_count_4_{count_col}",
                f"rolling_count_5_{count_col}",
            ]
        )

    return df_join


def feature_afspraken(df, afspr_gesch):
    """
    Doel: Maak features aan voor no show model
    Input:
        - df: dataframe met output van preproces. Elke rij staat voor een 'gereserveerd tijdslot', een geblokkeerd moment die uiteindelijk een show/no show/verplaatsing/annulering werd
    Output:
        - df: dezelfde dataframe als input maar nu met extra kolommen (features) erbij

    """

    logsetup.setup_logging()
    logger = logging.getLogger()

    ############################################################################
    # Rolling count features
    ############################################################################

    logger.info("Bepaal rolling count features")

    # Maak de kolom 'beldag' aan. Om de train set zo eerlijk mogelijk op te zetten kunnen we
    # bij het aanmaken van de features alleen informatie mee van voor de beldag
    terugkijkdagen = {1: -5, 2: -5, 3: -5, 4: -3, 5: -3, 6: -3, 7: -4}
    df["weekdag"] = df["DATUM"].apply(datetime.weekday) + 1
    df["Beldatum"] = (
        df["DATUM"]
        + pd.to_timedelta(df["weekdag"].replace(terugkijkdagen), unit="d")
        + pd.to_timedelta(17, "h")
    )

    # Om de rolling counts (afspraken en no shows) te bepalen willen we
    # per afspraak alleen maar afspraken optellen die minder dan 1 jaar geleden
    # hebben plaatsgevonden

    # Check of een afspraak al een keer verplaatst is of niet. Sorteer eerst de dataframe
    df = df.sort_values(["patientnr", "afspraaknr", "actie_moment"])

    # Tel het aantal verplaatsingen binnen een afspraaknr. Er is een verplaatsing geweest als de
    # DATUM kolom van de vorige rij van die afspraak anders is dan de huidige kolom (minus 1 want een NaN wordt als anders gezien)
    # De MUTATIETYPE kolom is niet helemaal meer te vertrouwens vanwege de preprocessing
    df["verplaatsing"] = (~(df.groupby("afspraaknr")["DATUM"].shift(-1)).isna()).astype(
        int
    )

    # Sorteer op actie_moment, die geeft goed chronologisch weer wat er is gebeurd tijdens de afspraak mutaties
    df = df.sort_values(["patientnr", "actie_moment"])

    # Rolling count op het aantal geplande momenten, dus aantal rijen
    # De functie rolling_count_time_window telt de waardes in een specifieke kolom op. Als
    # we de rijen willen tellen is elke kolom waarde 1

    df["gepland"] = 1
    df["no_show"] = (df["voldaan_af"] == "N").astype(int)
    df["show"] = ((df["voldaan_af"] == "J") & (df["verplaatsing"] == 0)).astype(int)
    # Rolling count op het aantal verplaatsingen door de patient.
    door_pat = [
        "CS00000002",  # Verzoek patient
        "N",  # Patient niet verschenen / te laat gemeld (<24 uur)
        "CS00000003",  # Patient niet bereikbaar (telefonisch consult)
        "Q",  # Patient niet bereikbaar (telefonisch consult)
        "NF",  # No show (geen factuur)
        "P",  # Verzoek patient (>24 uur van tevoren afgemeld)
        "Z",  # Ik ben ziek
        "",  # Geen reden opgegeven, default is door patient?
    ]
    df["verplaatsing_door_pat"] = (
        (df["verplaatsing"] == 1) & (df["verplreden"].isin(door_pat))
    ).astype(int)

    count_columns = [
        "gepland",
        "show",
        "no_show",
        "verplaatsing",
        "verplaatsing_door_pat",
    ]
    df = rolling_count_time_window(
        df, window_size=afspr_gesch, time_col="actie_moment", count_cols=count_columns
    )
    df = df.drop(columns="gepland")

    # Tel het totaal aantal verplaatsingen
    df[["verplaatst", "verplaatst_door_pat"]] = (
        df[["afspraaknr", "verplaatsing", "verplaatsing_door_pat"]]
        .groupby(["afspraaknr"])[["verplaatsing", "verplaatsing_door_pat"]]
        .cumsum()
    )
    # Het percentage van het aantal geplande momenten die in een no-show is geeindigd
    df["no_show_perc"] = df["rolling_count_no_show"] / df["rolling_count_gepland"]
    df["no_show_perc"] = df["no_show_perc"].fillna(0)

    ############################################################################
    # Tijd sinds vorige show
    ############################################################################

    # Bepaal het aantal dagen sinds de patient voor het laatst gezien is, oftewel
    # wanneer de vorige show was.

    # Om de tijd tot de vorige show te berekenen nemen we eerst de shows zelf apart
    df_af = (
        df[
            ((df["voldaan_af"] == "J") | (df["voldaan_af"].isna()))
            & (df["verplaatsing"] == 0)
        ]
        .sort_values(["patientnr", "DATUM"])
        .drop_duplicates(subset=["patientnr", "afspraaknr"], keep="last")
    )

    # Sorteren is nodig voor de merge_asof functie
    df = df.sort_values("Beldatum")
    df_af = df_af.sort_values("DATUMTIJD")
    # Merge_asof doet een left join maar dan op basis van de dichtsbijzijnde match
    # ipv dat een exacte match geeist wordt. De merge op beldatum en de datum van shows
    # pakt deze functie dus de eerste show voor de beldatum
    df = pd.merge_asof(
        df,
        df_af[["patientnr", "DATUMTIJD"]].rename(columns={"DATUMTIJD": "vorige_show"}),
        by="patientnr",
        left_on="Beldatum",
        right_on="vorige_show",
        direction="backward",
    )

    # Bepaal op eenzelfde manier de tijd sinds de vorige noshow
    df_ns = (
        df[(df["voldaan_af"] == "N")]
        .sort_values(["patientnr", "DATUM"])
        .drop_duplicates(subset=["patientnr", "afspraaknr"], keep="last")
    )

    # Sorteren is nodig voor de merge_asof functie
    df = df.sort_values("Beldatum")
    df_ns = df_ns.sort_values("DATUMTIJD")
    df = pd.merge_asof(
        df,
        df_ns[["patientnr", "DATUMTIJD"]].rename(
            columns={"DATUMTIJD": "vorige_noshow"}
        ),
        by="patientnr",
        left_on="Beldatum",
        right_on="vorige_noshow",
        direction="backward",
    )

    # Bepaal op eenzelfde manier de uitkomst van de vorige afspraak
    df_prev = df.sort_values(["patientnr", "DATUMTIJD"]).drop_duplicates(
        subset=["patientnr", "DATUM"], keep="last"
    )
    # Sorteren is nodig voor de merge_asof functie
    df = df.sort_values("Beldatum")
    df_prev = df_prev.sort_values("DATUM")
    # Merge_asof doet een left join maar dan op basis van de dichtsbijzijnde match
    # ipv dat een exact match geeist wordt. De merge op beldatum en de datum van shows
    # pakt deze functie dus de eerst show voor de beldatum
    df = pd.merge_asof(
        df,
        df_prev[["patientnr", "DATUM", "voldaan_af"]].rename(
            columns={"voldaan_af": "vorige_voldaan"}
        ),
        by="patientnr",
        left_on="Beldatum",
        right_on="DATUM",
        direction="backward",
    )
    df = df.drop(columns="DATUM_y").rename(columns={"DATUM_x": "DATUM"})
    # Bepaald dagen sinds vorige show
    df["dagen_sinds_afspraak"] = (df["DATUMTIJD"] - df["vorige_show"]) / timedelta(
        days=1
    )
    df["dagen_sinds_noshow"] = (df["DATUMTIJD"] - df["vorige_noshow"]) / timedelta(
        days=1
    )

    # Zet dagen tot afspraak om in een integer aantal dagen
    df["dagen_tot_afspraak"] = df["dagen_tot_afspraak"].round("D").dt.days

    ############################################################################
    # Stiptheid patient
    ############################################################################

    # Voor de stiptheid kijken we alleen naar de vroegste afspraak per datum. Verplaatsingen
    # nemen we hiervoor niet mee (mochten ze toche en aankomsttijd hebben om een of andere reden)
    df = df.sort_values(["patientnr", "DATUM", "TIJD"])

    df_aankomst = df[(df["verplaatsing"] == 0)].drop_duplicates(["patientnr", "DATUM"])
    # Hoeveel minuten was de patient op tijd
    df_aankomst["min_op_tijd"] = (
        pd.to_datetime(df_aankomst["TIJDMIN"]) - pd.to_datetime(df_aankomst["aankomst"])
    ) / np.timedelta64(1, "m")
    # Rolling median op min_op_tijd, we nemen maar 1 jaar geschiedenis mee van de patient
    df_aankomst["rolling_min_op_tijd"] = df_aankomst.groupby("patientnr")[
        ["min_op_tijd", "DATUM"]
    ].apply(lambda x: x.rolling(f"{afspr_gesch}D", on="DATUM").median())["min_op_tijd"]
    # Verschuif de kolom in rij omlaag, voor de afspraak zelf weet je nog niet wanneer de patient aankomt
    df_aankomst["rolling_min_op_tijd"] = df_aankomst.groupby("patientnr")[
        "rolling_min_op_tijd"
    ].transform("shift")

    # Join terug op originele dataframe
    df = pd.merge(
        df,
        df_aankomst[["afspraaknr", "rolling_min_op_tijd", "DATUMTIJD"]],
        how="left",
        on=["afspraaknr", "DATUMTIJD"],
    )
    # Forward fill mochten er nog gaatjes zijn
    df["rolling_min_op_tijd"] = (
        df[["patientnr", "rolling_min_op_tijd"]]
        .groupby(["patientnr"])["rolling_min_op_tijd"]
        .ffill()
    )

    ############################################################################
    # Overige features
    ############################################################################
    logger.info("Bepaal overige features")

    # Afstand tot ziekenhuis
    df = afstand_tot_ziekenhuis(df)

    # Check of de afspraak een keer door de arts is verplaatst of niet
    df["verpl_door_arts"] = (df["voldaan_af"] == "Door Arts").astype(int)
    # Forward fill op deze kolom binnen elke afspraak, zodat onthouden wordt dat de afspraak een keer door de arts gemuteerd is
    df["verpl_door_arts"] = (
        df[["afspraaknr", "verpl_door_arts"]]
        .groupby(["afspraaknr"])["verpl_door_arts"]
        .cumsum()
    )

    # Patient is nieuw als die nog nooit een show is geweest.
    df["Nieuwe_patient"] = df["rolling_count_show"] < 1

    df["TIJD"] = df["TIJD"].str.split(":").str[0]
    df["TIJD"] = df["TIJD"].astype(float)

    # Eerst sorteren op patient, en datum zodat de feature creatie goed gaat
    # df.sort_values(by=['patientnr','JAAR','MAAND', 'DAG', 'TIJD'], ascending=True, inplace=True)
    df = df.sort_values(["patientnr", "DATUM", "TIJDMIN"])
    # Groepeer per datum en maak een kolom voor het aantal afspraken op die dag
    df["afspraken_dag"] = (
        df[df["actie_moment"] > df["Beldatum"]]
        .groupby(["patientnr", "DATUM"])["afspraaknr"]
        .transform("nunique")
    )

    df = vakantie_check(df)

    df["maand"] = df["DATUM"].dt.month_name()
    df["weekdag"] = df["weekdag"].astype(str)

    logger.info("Eind feature building")

    return df

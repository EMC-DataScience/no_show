import logsetup
import logging

import numpy as np
import pandas as pd
from datetime import date, timedelta


def preprocess_afspraken(df):
    """
    Doel: voorverwerking data zodat feature enginering gedaan kan worden. Er moet wat met kolommen geschoven worden omdat HiX veel data overschrijft. Zo willen we bijv voor
            verplaatsingen niet de datum waar het naartoe verplaatst is, maar waar het vandaan verplaatst is. Ook kunnen we hier al filteren op de juiste verplaatsredenen en
            makkelijk een paar eerste features aanmaken zoals dagen tussen maken van afspraak en plaatsvinden afspraak

    Input:
        - df: output van de SQL query met alle benodigde mutaties van de afspraken die we willen analyseren
    Output:
        - df: Afspraken voorverwerkt en klaar voor verdere feature enginering. Elke rij van deze df representeert een 'gereserveerd tijdslot', een afspraak waarvoor
                op de DATUMTIJD kolom een tijd voor gereserveerd was, en uiteindelijk is geresulteerd in een show, no show, verplaatsing of annulering.
    """
    logsetup.setup_logging()
    logger = logging.getLogger()

    logger.info("Begin preprocessing afspraken")
    # NaN werken fijner dan lege strings
    df = df.replace("", np.nan)

    # Soms staan er 2 adressen op iemands naam geregistreerd, bijv een officieel en een verblijf adres.
    # In de query is rekening gehouden met een aantal zaken (zoals alleen adressen in NL), maar
    # als laatste redmiddel doen we hier een hard coded ontdubbeling
    df = df.drop_duplicates(
        ["patientnr", "afspraaknr", "volgnummer", "mutatie_moment"], keep="first"
    )

    # De data die ingeladen wordt is een lijst met mutaties van de afspraak (exclusief de 'Wijzigingen' mutatietypes).
    # Soms zitten er nog mutaties in die hiervoor niet van waarde zijn (bijv dat een afspraak geautoriseerd is)
    # Sorteer op afspraaknummer/volgnummer, de eerste is hoe de afspraak aangemaakt is, de laatste is hoe die afgesloten is.
    # Als daar alle verplaatsingen aan toegevoegd worden hebben we alle relevantie acties
    df = df.sort_values(["afspraaknr", "volgnummer"])
    eerste = df.drop_duplicates(subset=["afspraaknr"], keep="first")
    laatste = df.drop_duplicates(subset=["afspraaknr"], keep="last")
    verplaatsing = df[df["MUTATIETYPE"] == "Verplaatst"]

    df = pd.concat([verplaatsing, eerste, laatste], ignore_index=True)

    # Als de laatste afspraak een verplaatsing is (voor afspraken in de toekomst), krijg je dubbele regels die verwijderd moeten worden
    df = df.drop_duplicates(subset=["volgnummer"])

    # Zet de datum velden om in datetime variabelen
    df["datum_tijd_am"] = pd.to_datetime(df["datum_tijd_am"], errors="coerce")
    df["datum_am"] = pd.to_datetime(df["datum_am"], errors="coerce")
    # Als de DATUM kolom leeg is (bij annuleringen), vul dan datum_am in
    df["DATUM"] = df["DATUM"].fillna(df["datum_am"])
    df["TIJD"] = df["TIJD"].fillna(df["tijd_am"])

    # Combineer tot een datum_tijd kolom
    df["DATUMTIJD"] = pd.to_datetime(df["DATUM"], errors="coerce") + pd.to_timedelta(
        df["TIJD"] + ":00", errors="coerce"
    )

    # Lijst met codes die duidelijk staan voor dat de patient de oorzaak is
    # Als er geen code staat opgegeven, ga er dan vauit dat de patient de reden is
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

    ############################################################################
    # Voorverwerking verplaatsingen
    ############################################################################

    logger.info("Verplaatsingen verwerken")
    # Bij verplaatsingen staat alleen de nieuwe data in de rij, waar het naar toe verplaatst is.
    # Voor de preprocessing willen we echter ook weten waar het vandaag verplaatst is,
    # die informatie moet eerst op dezelfde rij gezet worden.
    df = df.sort_values(["afspraaknr", "volgnummer"])
    df_group = df.groupby("afspraaknr")
    df["lag_duur"] = df_group["DUUR"].transform("shift")
    df["lag_code"] = df_group["CODE"].transform("shift")
    df["lag_datum_tijd_am"] = df_group["datum_tijd_am"].transform("shift")
    df["lag_datum_am"] = df_group["datum_am"].transform("shift")
    # toevoeging i.v.m. een error over het datatype
    df["lag_datum_tijd_am"] = df["lag_datum_tijd_am"].fillna(value=np.datetime64("nat"))

    # Reken de tijd uit tussen de mutatie en de geplande afspraak
    df["uren_voor_mut"] = (
        df["lag_datum_tijd_am"] - df["mutatie_moment"]
    ) / np.timedelta64(1, "h")

    # Creeer een kolom die aangeeft of de afspraak is verplaatst naar een ander moment op de dag.
    # Dit zijn verplaatsingen waar we niet in geinteresseerd zijn
    df["verpl_zelfde_dag"] = (
        df["lag_datum_tijd_am"].dt.date == df["datum_tijd_am"].dt.date
    )

    # Hoe ver de afspraak vooruit is gepland, is het verschil tussen het mutatiemoment en de (nieuwe geplande) afspraak datumtijd
    df["dagen_vooruit"] = df["datum_tijd_am"] - df["mutatie_moment"]
    # Schuif deze informatie 1 rij naar beneden zodat we per rij weten hoeveel dagen
    # er zitten tussen het maken van de afspraak en het plaatsvinden ervan.
    df["dagen_tot_afspraak"] = df.groupby("afspraaknr")["dagen_vooruit"].transform(
        "shift"
    )
    # Alleen bij de eerste mutatie moet de dagen_vooruit gepakt worden
    df["dagen_tot_afspraak"] = df["dagen_tot_afspraak"].fillna(df["dagen_vooruit"])
    # en bij verplaatsingen hebben we wel de dagen_vooruit kolom nodig
    df.loc[df["MUTATIETYPE"].isin(["Verplaatst"]), "dagen_tot_afspraak"] = df[
        "dagen_vooruit"
    ]

    # Nu de benodigde informatie in de rij zelf staat, kunnen we onnodige rijen wegfilteren
    # Dit is relevant voor bijv afspraken die zijn omgezet van fysiek naar telefonisch of andersom
    df = df[(df["contacttype"] == "F") & (df["zonder_patient"] == 0)]

    # Er zijn nu 5 verschillende soorten rijen die elk op een eigen manier gewerkt
    # moeten worden, (i) afspraken die nog niet hebben plaatsgevonden (ii) shows
    # (iii) no-shows (iv) verplaatsingen en (v) annuleringen
    logger.info("Verwerking verschillende afspraakmutaties")

    ############################################################################
    # Toekomstige afspraken
    ############################################################################

    # De afspraak zoals die gepland staat is de laatste mutatie van de afspraak
    K = df.sort_values(["afspraaknr", "volgnummer"]).drop_duplicates(
        subset=["afspraaknr"], keep="last"
    )
    # De geplande afspraken zijn degene met de datum na vandaag
    vandaag = date.today()
    K = K[
        (K["DATUM"] >= (pd.to_datetime(vandaag)))
        & (K["DATUM"] <= (pd.to_datetime(vandaag) + timedelta(30)))
    ]
    # Voor een afspraak die nog moet plaatsvinden is het actie moment het moment van plannen, dus de mutatie tijd van laatste mutatie
    K["actie_moment"] = K["DATUMTIJD"]

    ############################################################################
    # Shows
    ############################################################################

    # Voor de shows zit alle benodigde informatie voor de afspraak zit in de laatste rij van elke groep
    S = df[(df["voldaan_af"] == "J") & (df["DATUM"] <= pd.to_datetime(vandaag))].copy()
    S = S.sort_values(["afspraaknr", "volgnummer"]).drop_duplicates(
        subset=["afspraaknr"], keep="last"
    )
    # Voor een afspraak die is afgerond is het actie moment het moment dat de afspraak heeft plaatsgevonden
    S["actie_moment"] = S["DATUMTIJD"]

    ############################################################################
    # No-shows
    ############################################################################

    # Voor de no-shows zit alle benodigde informatie voor de afspraak zit in de laatste rij van elke groep
    NS = df[(df["voldaan_af"] == "N") & (df["DATUM"] <= pd.to_datetime(vandaag))].copy()
    # Pak ook bij no shows de laatste mutatie
    NS = NS.sort_values(["afspraaknr", "volgnummer"]).drop_duplicates(
        subset=["afspraaknr"], keep="last"
    )

    # Als er een andere code staat dan in door_pat, dan komt het door het ziekenhuis
    NS["voldaan_af"] = "Door Arts"
    NS.loc[
        (NS["verplreden"].isna()) | (NS["verplreden"].isin(door_pat)), "voldaan_af"
    ] = "N"

    # De verplaats reden P betekent dat de patient de afspraak op tijd heeft geannuleerd, dus dat is effectief een show
    NS.loc[NS["verplreden"] == "P", "voldaan_af"] = "J"
    # Voor een afspraak die is afgerond is het actie moment het moment dat de afspraak heeft plaatsgevonden
    NS["actie_moment"] = NS["DATUMTIJD"]

    ############################################################################
    # Verplaatsingen
    ############################################################################

    # De verplaatsingen die we willen meenemen als show/no-show
    V = df[
        (df["MUTATIETYPE"] == "Verplaatst") & (df["DATUM"] <= pd.to_datetime(vandaag))
    ].copy()
    # We kijken niet naar verplaatsingen naar een andere tijd op dezelfde dag
    V = V[V["verpl_zelfde_dag"] == False]

    # Alleen een no-show als die verplaatst is minder dan 24 uur van de tevoren
    # op initiatief van de patient. Anders is het ziekenhuis de oorzaak
    V["voldaan_af"] = "Door Arts"
    V.loc[
        ((V["verplreden"].isna()) | (V["verplreden"].isin(door_pat)))
        & (V["uren_voor_mut"] < 24),
        "voldaan_af",
    ] = "N"
    V.loc[
        ((V["verplreden"].isna()) | (V["verplreden"].isin(door_pat)))
        & (V["uren_voor_mut"] >= 24),
        "voldaan_af",
    ] = "J"

    V.loc[V["verplreden"] == "P", "voldaan_af"] = "J"

    # Bij een verplaatsing willen we weten waar het vandaan verplaatst is, en dus ook
    # wat de duur en de afspraakcode waren (voor de verplaatsing)
    V["DATUMTIJD"] = V["lag_datum_tijd_am"]
    V["DATUM"] = V["lag_datum_am"]
    V["DUUR"] = V["lag_duur"]
    V["CODE"] = V["lag_code"]

    # Bij een verplaatsing is de aankomst kolom leeg (komt nu uit een latere mutatie)
    V["aankomst"] = np.nan
    # Voor een verplaatsing is het actie moment wanneer de afspraak verplaatst is
    V["actie_moment"] = V["mutatie_moment"]

    ############################################################################
    # Annuleringen
    ############################################################################

    # Als laatste de annuleringen die op een net iets andere manier dan de verplaatsingen
    # verwerkt moeten worden
    A = df[
        (df["MUTATIETYPE"] == "Geannuleerd") & (df["DATUM"] <= pd.to_datetime(vandaag))
    ].copy()
    A = A.sort_values(["afspraaknr", "volgnummer"]).drop_duplicates(
        subset=["afspraaknr"], keep="last"
    )

    # Alleen een no-show als die verplaatst is minder dan 24 uur van de tevoren
    # op initiatief van de patient. Anders is het ziekenhuis de oorzaak

    A["voldaan_af"] = "Door Arts"
    A.loc[
        ((A["verplreden"].isna()) | (A["verplreden"].isin(door_pat)))
        & (A["uren_voor_mut"] < 24),
        "voldaan_af",
    ] = "N"
    A.loc[
        ((A["verplreden"].isna()) | (A["verplreden"].isin(door_pat)))
        & (A["uren_voor_mut"] >= 24),
        "voldaan_af",
    ] = "J"
    # De verplaats reden P betekent dat de patient de afspraak op tijd heeft geannuleerd, dus dat is effectief een show
    A.loc[A["verplreden"] == "P", "voldaan_af"] = "J"

    # Bij een annulering is de aankomst kolom leeg (komt nu uit een latere mutatie)
    A["aankomst"] = np.nan
    # Voor een verplaatsing is het actie moment wanneer de afspraak verplaatst is
    A["actie_moment"] = A["mutatie_moment"]

    ############################################################################
    # Hercombineren
    ############################################################################

    # Combineer nu de shows, no-shows en verplaatsingen. Check nu weer op afspraken die te ver vooruit zijn gepland (of achteraf zijn ingevoerd)
    # en afspraken die buiten de regulieren uren vallen
    df_preproc = pd.concat([S, NS, V, A, K], ignore_index=True)

    # Gooi wat lag_ kolommen weg die niet meer nodig zijn
    df_preproc = df_preproc.drop(
        columns=["lag_duur", "lag_code", "lag_datum_am", "lag_datum_tijd_am"]
    )

    df_preproc = df_preproc[~df_preproc["actie_moment"].isna()]
    ############################################################################
    # Afronden en overig
    ############################################################################

    df_preproc["DATUM"] = pd.to_datetime(df_preproc["DATUM"])
    # Combineer tot een datum_tijd kolom
    df_preproc["DATUMTIJD"] = pd.to_datetime(
        df_preproc["DATUM"], errors="coerce"
    ) + pd.to_timedelta(df_preproc["TIJD"] + ":00", errors="coerce")

    # Tijdelijke voor backwards compatability
    df_preproc["TIJDMIN"] = df_preproc["TIJD"]

    # Gooi afspraken weg die voor de invoerdatum hebben plaatsgevonden
    df_preproc = df_preproc[df_preproc["INVOERDAT"] < df_preproc["DATUM"]]

    # Soms hebben patienten combi afspraken, dan komen er 2 afspraken voor 1 show/noshow moment. Kies
    # een van de twee om mee verder te gaan, de aankomsttijd wordt maar bij 1 geregistreerd dus pak die (daarom sorteren op aankomst)
    df_preproc = df_preproc.sort_values(
        by=["patientnr", "DATUMTIJD", "aankomst"], na_position="last"
    )
    df_preproc = df_preproc.drop_duplicates(
        subset=["patientnr", "DATUMTIJD"], keep="first"
    )

    logger.info("Eind preprocessing afspraken")

    return df_preproc

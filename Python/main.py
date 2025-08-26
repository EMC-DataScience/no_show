import warnings
import logsetup
import logging

from init_modelsettings import init_modelsettings
from init_serversettings import init_serversettings

from readwrite import create_dataset, load_dataset, radiologie_verplaatsreden
from preprocess.preprocess_afspraken import preprocess_afspraken
from featurebuilding.feature_afspraken import feature_afspraken
from featurebuilding.filter_afspraken import filter_afspraken
from modelling.voorspel import (
    gebelde_patienten_afgelopen_week,
    momenteel_opgenomen_patienten,
    voorspelling_voor_bellijst,
    patienten_nietbellen,
)
from modelling.train import train_all_models

from DSPackage.write_data.check_db import check_voorspellingen_vandaag
from DSPackage.write_data.write import write_to_db
from DSPackage.utilities.pipeline_env import get_pipeline_env



warnings.filterwarnings("ignore")

logsetup.setup_logging()
logger = logging.getLogger()

# functies om data over infrastructuur op te halen
pipeline_env = get_pipeline_env()
server_settings = init_serversettings()
model_settings = init_modelsettings()
# update_package('ds_package', model_settings['package_buildid'], pipeline_env)
# Op de data is al preprocessing en feature building gedaan, haal alle data op uit de relevante noshow tabel

"""
Mogelijke modi:
    - create_train/holdout: maak de train/holdout dataset aan en schrijf in de noshow_train/holdout tabel
    - voorspel: maak de dataset aan waar we op willen voorspellen voor de bellijst en schrijf in de no_show_pred tabel (hier werkt de pipeline op)
    - train: haal de train dataset uit de noshow_train tabel en train modellen hierop
"""


if model_settings["modus"] in ("create_train", "create_holdout", "voorspel"):
    # Welke dataset we willen gebruiken halen we uit de naam van de modus
    submodus = model_settings["modus"].split("_")[-1]
    # Haal de relevante datum range op voor deze submodus
    dates = model_settings["datum_range"][submodus]
    # dates = ['2023-11-10', '2023-11-15']

    # Check of de voorspellingen voor vandaag al gedaan zijn, anders overslaan
    if submodus == "voorspel":
        vandaag_al_voorspeld = check_voorspellingen_vandaag(
            table="no_show_pred",
            server=server_settings["writeserver"],
            database=server_settings["writedatabase"],
            schema="NoShow",
        )
        if vandaag_al_voorspeld:
            logger.info("Voorspellingen voor vandaag al weggeschreven")
    else:
        vandaag_al_voorspeld = False

    if not vandaag_al_voorspeld:
        # Vuur query af op database om dataset in te laden
        df = create_dataset(
            server=server_settings["readserver"],
            database=server_settings["readdatabase"],
            schema=server_settings["readschema"],
            models=model_settings["models"],
            poliklinieken=model_settings["poliklinieken"],
            datum_range=dates,
            afspr_gesch=model_settings["afspr_gesch"],
        )

        # Omdat de verwijderreden voor de radiologie afspraken in een los onderdeel van HiX terecht komt
        # halen we die hier apart op. Dit doen we los omdat het anders een hoop dubbele regels oplevert
        # in de hoofdquery
        if "Radiologie" in model_settings["models"]:
            df = radiologie_verplaatsreden(
                df=df,
                server=server_settings["readserver"],
                database=server_settings["readdatabase"],
                schema=server_settings["readschema"],
                datum_range=dates,
                afspr_gesch=model_settings["afspr_gesch"],
            )
        if not df.empty:
            # Preprocessing
            df = preprocess_afspraken(df)
            # Feature building
            df = feature_afspraken(df=df, afspr_gesch=model_settings["afspr_gesch"])
            # Filter op datum en poli, afspraakgeschiedenis kan nu weg
            df = filter_afspraken(
                df == df,
                datum_range=dates,
                models=model_settings["models"],
                afspraakcodes=model_settings["afspraakcodes"],
                subagendas_exclude=model_settings["subagendas_exclude"],
            )

            if not df.empty:
                # Schrijf het resultaat weg in de relevante tabel
                write_table = f"noshow_{submodus}"
                # De voorspel database heet nog anders, hoe die tijdens de pilot was gedefinieerd
                if submodus == "voorspel":
                    # Alleen patienten die nog geen telefoontje hebben gehad de afgelopen week
                    gebelde_patienten = gebelde_patienten_afgelopen_week(
                        DBA_server_settings=server_settings["DBA_server"]
                    )
                    df = df[~df["patientnr"].isin(gebelde_patienten)]

                    # Opgenomen patienten hoeven niet gebeld te worden
                    opgenomen_patienten = momenteel_opgenomen_patienten(
                        server_settings=server_settings
                    )
                    df = df[~df["patientnr"].isin(opgenomen_patienten)]

                    # Patienten die niet gebeld willen worden kunnen eruit
                    nietbellen = patienten_nietbellen("patienten_nietbellen.json")
                    df = df[~df["patientnr"].isin(nietbellen)]

                    df = voorspelling_voor_bellijst(
                        df=df,
                        modelclusters=model_settings["modelclusters"],
                        modelmapping_voorspel=model_settings["modelmapping_voorspel"],
                        models=model_settings["models"],
                        feature_list=model_settings["feature_list"],
                        beldienst_param=model_settings["beldienst_param"],
                    )
                    replace = False
                    system_versioned = False
                    write_table = server_settings["tabel_voorspellingen"]
                    server_settings["writeschema"] = "NoShow"
                else:
                    replace = True
                    system_versioned = False

                write_to_db(
                    df,
                    table=write_table,
                    server=server_settings["writeserver"],
                    database=server_settings["writedatabase"],
                    schema=server_settings["writeschema"],
                    replace=replace,
                    pipeline_env=pipeline_env,
                    make_system_versioned=system_versioned,
                )
            else:
                logger.info("Geen afspraken gepland voor de beldag")
elif model_settings["modus"] in ("train"):
    # Welke dataset we willen gebruiken halen we uit de naam van de modus
    submodus = model_settings["modus"].split("_")[-1]

    # Op de data is al preprocessing en feature building gedaan, haal alle data op uit de relevante noshow tabel
    table = f"noshow_{submodus}"
    df = load_dataset(table=table, readserver=server_settings["writeserver"])
    # Sample (reproduceerbaar) 10 rijen per patientnr
    df = (
        df.groupby("patientnr")
        .sample(10, random_state=42, replace=True)
        .drop_duplicates()
    )
    train_all_models(
        df=df,
        polis=model_settings["models"],
        model_hyperparameters=model_settings["model_hyperparameters"],
        feature_list=model_settings["feature_list"],
        modelclusters=model_settings["modelclusters"],
    )

else:
    modus = model_settings["modus"]
    logger.warning(f"Onbekende modus gekozen: {modus}")

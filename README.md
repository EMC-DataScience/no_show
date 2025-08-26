# No-show model Erasmus MC

## Introductie

Deze repositry bevat de Python code die in het Erasmus MC gebruikt wordt voor het 'no-show model', een machine learning model waarmee de kans op no-show wordt ingeschat voor patiënten met een fysieke afspraak op de polikliniek. 

Dit model is gemaakt door het team Data Science van de afdeling Data + Analytics van het Erasmus MC. Voor vragen over deze code kan je mailen naar datascience@erasmusmc.nl.

## Intended Use
Deze repositry bevat niet alle code die gebruikt wordt om de bellijst dagelijks klaar te zetten voor de telefonisten omdat veel code specifiek is voor de infrastructuur van het Erasmus MC. De code in deze repositry is bedoeld om anderen inzicht te geven in het machine learning model, met name hoe de data verwerkt wordt, hoe het model getraind wordt en hoe de voorspellingen gegenereerd worden, om lezers te helpen zelf een vergelijkbaar model te maken en implementeren. Deze code kan dus niet direct ingezet worden in een andere (zorg)instelling maar moet zorgvuldig verwerkt worden in de lokale infrastructuur. Er zijn verwijzingen naar bestanden en folders niet bestaan omdat ze niet meegenomen zijn in deze repo. Het machine learning model dient zorgvuldig getest te worden voor het gebruikt kan worden. 

## Definitie no-show
De code in deze repositry gaat uit van de volgende definitie van een no-show:

Een patiënt is een 'no-show' als die een fysieke afspraak gepland had op de polikliniek maar hij/zij
1. verwacht werd maar niet is op komen dagen, waarna de zorgverlener de afspraak als 'no-show' heeft geregistreerd, of
2. de afspraak minder dan 24 uur voor het geplande moment op eigen initiatief heeft geannuleerd of verplaatst

Merk op dat het kan voorkomen dat een patiënt niet op is komen dagen maar dat de oorzaak bij de zorginstelling of zorgverlener zelf ligt. Het doel van dit model is om met een telefonische herinnering ervoor te voorkomen dat patiënten niet naar hun afspraak gaan terwijl dat wel mogelijk was. Als de zorginstelling of -verlener de oorzaak is, had de beldienst het niet kunnen voorkomen en is het voor het doel van deze beldienst geen no-show.

## Populatie
De beldienst wordt alleen ingezet op patiënten met een fysieke afspraak die minstens 7 dagen vooruit is gepland. Er is voor fysieke afspraken gekozen omdat de impact van een no-show bij een telefonische of elektronische afspraak relatief klein is t.o.v. een fysieke afspraak. Daarnaast is er gekozen voor de horizon van 7 dagen om te voorkomen dat patiënten gebeld worden voor een afspraak die ze kort geleden gemaakt hebben (en dus om overlast te voorkomen). Ook kan in de model_settings.json aangegeven worden welke agenda's/subagenda's/afspraakcodes uitgesloten moeten worden van de beldienst.

## Features 

Het AI model gebruikt de volgende features. Tenzij anders gemeld worden alleen afspraken meegenomen bij het bepalen van de onderstaande features als deze minder dan een jaar voor de geplande afspraak gepland waren. 

1. “distance”, float: afstand tussen de geregistreerde postcode en de locatie van het Erasmus MC. Deze afstand wordt hemelsbreed bepaald en maakt geen onderscheid in de richting. 
2. “LEEFTIJD”, float: leeftijd van de patient op het moment dat de afspraak gepland was 
3. “afspraken_dag”, float: het aantal afspraken dat de patient op de geplande dag heeft 
4. “rolling_min_op_tijd”, float: wanneer een naar het Erasmus MC komt voor een afspraak meldt deze zich eerst aan. Deze tijd wordt bij de afspraak geregistreerd. “rolling_min_op_tijd” is de median van het verschil tussen de aanmeldtijd en de afspraak tijd van de eerdere afspraken van deze patient. 
5. “dagen_tot_afspraak”, float: aantal dagen van het moment dat de afspraak gemaakt is tot de geplande datum 
6. “verplaatst_door_pat”, boolean: of deze afspraak een keer eerder al door de patient verplaatst is of niet 
7. “rolling_counts_no_show”, float: aantal keer dat de patient eerder no-show is geweest 
8. “rolling_counts_verplaatsing_door_pat”, float: aantal keer dat de patient eerder een afspraak heeft verplaatst 
9. “rolling_counts_show”, float: aantal keer dat de patient eerder show is geweest 
10. “vorige_voldaan”, boolean: of de vorige afspraak een no-show was of niet 
11. “dagen_sinds_noshow”, float: het aantal dagen eerder t.o.v. de geplande afspraak dat de patient een no-show was 
12. “weekdag”, string: dag van de week van de geplande afspraak 
13. “maand”, string: maand van het jaar van de geplande afspraak 
14. “constype_code”, string: het type consult van de afspraak. De mogelijke opties zijn “eerste consult”, “herhaal consult”, “verrichting”, “geen”. 

## Metric 

De belangrijkste performance metric is de recall van het model als 20% van de afspraken met de hoogste predict proba op de bellijst komen te staan. Deze recall wordt op dagbasis bepaald, wat inhoudt dat per dag de 20% hoogst risico patiënten worden aangemerkt als hoog risico en niet de 20% hoogst risico van de gehele train dataset

## Model 

Het uiteindelijke AI model(len) is een XGBoost classifier model. De parameters van de modellen kunnen in model_settings.json gezet worden. Per polikliniek is getest of een model getraind op afspraken van alleen die polikliniek (en eventueel vergelijkbare poliklinieken qua patiëntenpopulatie) een hogere voorspelkracht heeft dan een model getraind op een dataset waar alle poliklinieken in voorkomen.  

## Codestructuur

### Main

De main kan afgevuurd worden in verschillende modi, bijvoorbeeld om een voorspelling te genereren voor de bellijst of om een model te trainen. De main wordt aangestuurd vanuit model_settings.json (template hiervoor in de repositry te vinden). In de model_settings.json staat hoe de main doorlopen moet worden, maar daar staat ook andere essentiële informatie in over zoals hoe bepaalde poliklinieken geïdentificeerd kunnen worden of over welke periode data opgehaald moet worden voor de train dataset.

### Preprocessing

De code verwacht als input voor de preprocessingfunctie een dataframe met alle afspraakmutaties van alle afspraken die nodig zijn om de features te bepalen. Omdat sommige features afhankelijk zijn van de afspraakgeschiedenis van de patiënt, bestaat het input dataframe
1. Alle fysieke afspraken die een keer gepland waren binnen de aangegeven tijdsperiode op de aangegeven poliklinieken
2. Alle fysieke afspraken van de patiënten uit (1) bij het ziekenhuis binnen de aangegeven tijdshorizon (parameter 'afspr_gesch' in model_settings.json) voor de periode van (1)

Elke afspraak mutatie is een regel met een geplande datum en tijd voor de afspraak (en andere benodigde data nodig voor de features). Deze code is ontwikkeld in het Erasmus MC waar HiX gebruikt wordt. Het is dus mogelijk dat sommige delen van de code niet werken voor andere EPD systemen.

Niet alle mutaties zijn uiteindelijk nodig om de relevante features te bepalen. Voor de features zijn alleen de eerste en laatste mutatie nodig, samen met alle mutaties waarbij de afspraak verplaatst wordt. Voor sommige features is het nodig om informatie van vorige mutaties te gebruiken (bijv. om te bepalen hoe ver een afspraak vooruit is gepland). Dit wordt in het eerste deel van de code gebruikt. Daarna worden toekomstige afspraken, shows, no-shows, verplaatsingen en annuleringen apart verwerkt.

De output van de preprocessing bevat alle relevante afspraak mutaties, een mutatie waarbij een tijdslot voor een patiënt gepland was en waar een voorspelling voor gegenereerd moet worden. De output bevat dus ook afspraken die uiteindelijk (te laat of op tijd) verzet zijn maar wel gepland waren.

### Feature building

Hier worden features voor elk geplande afspraak gemaakt. Voor 'historische features', features gebaseerd op eerdere afspraken zoals het aantal keer eerder dat een patiënt no-show is geweest, kijken we binnen een raam van 1 jaar (dus de feature “rolling_count_no_show” geeft aan hoe vaak de patiënt in de afgelopen 365 dagen een no-show is geweest). Hier is voor gekozen om verandering in gedrag bij de patiënt beter te kunnen meenemen en om een consistentie in de features aan te houden (in tegenstelling tot bijvoorbeeld features op basis van alle eerdere afspraken). Ook wordt rekening gehouden met welke informatie beschikbaar is voor de telefonisten op het afgesproken belmoment. Er wordt 3 werkdagen van te voren gebeld, en daarom wordt er voor gezorgd dat features gemaakt worden op basis van data die beschikbaar was op dat belmoment.

### Train

Na het aanmaken van de features kan het model getraind worden. Er kunnen meerdere modellen getraind worden gebaseerd op verschillende groepen van poliklinieken. Zo blijft de mogelijkheid om te onderzoeken of het nuttiger is om een enkel model te trainen o.b.v. alle poliklinieken of voor elke polikliniek een los model te hebben.

### Voorspel

Met de voorspelfuncties kan voor elke afspraak het juiste model gebruikt worden om een voorspelling te genereren. De code genereert eerst voor elke rij een predict_proba. Daarna wordt op basis van de opgegeven proportie (in model_settings.json) het percentage van de hoogste predict_proba's geselecteerd voor de bellijst. Merk op dat voor het genereren van de voorspellingen de top x% van de hoogste predict_proba **per dag** wordt geselecteerd. Het is belangrijk dit consistent te gebruiken bij het valideren van het model op historische data. De performance van het model is heel anders als je de top x% pakt voor de (fictieve) bellijst i.p.v. de top x% per dag.
 
## Disclaimer

Aan de code en informatie in deze repositry alsmede eventueel advies van de eigenaar kunnen geen rechten worden ontleend.
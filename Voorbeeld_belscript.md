# Handleiding

## Doel van het project
### Hoofddoel
Patiënten dat niet komen op dagen voor een afspraak (“no-shows") verminderen. Dit doen we door patiënten telefonisch aan hun afspraak te herinneren.

We gaan dit gedurende 6 maanden doen. Eerder hebben we aangetoond dat dit voor 1 polikliniek werkt, het doel nu is om dat ook voor andere poliklinieken aan te tonen.

### Subdoel
Contactgegevens verbeteren of aan te vullen. We hebben ervaren dat de registratie van de contactgegevens matig is. Daardoor kunnen we patiënten regelmatig niet bereiken. Voor sommige patiënten staan bijvoorbeeld 4 telefoonnummers geregistreerd, maar slechts naar 1 wordt een sms verzonden. Door alle 4 de nummers te bellen, kunnen we registreren welk nummer correct is. En bij de email kunnen we door uitvragen ook de emailadressen verbeteren, daarop ontvangt de patiënt namelijk zijn afspraakbrief.

## Werkwijze
Patiënten worden drie werkdagen vóór hun afspraak gebeld (patiënten die op maandag of in het weekend een afspraak hebben worden op woensdagen gebeld). De website toont alleen de patiënten die op die dag gebeld moeten worden. Als telefonist bel je dus iedereen die op de website staat. Hierbij bellen we een patiënt minimaal 2 keer, en wanneer een patiënt meerdere telefoonnummers heeft bellen we ieder nummer 2 keer.

## Waarom doen we dit?
Regelmatig komen patiënten niet opdagen voor hun afspraak. Hierdoor krijgen patiënten niet op het juiste moment de zorg die ze nodig hebben. Daarnaast kunnen we minder patiënten helpen, we hebben namelijk 2 afspraken nodig voor het zien van 1 patiënt. Door patiënten te bellen helpen we ze te herinneren aan hun afspraak en kunnen we ervoor zorgen dat meer patiënten wel komen opdagen bij hun afspraak, of dat ze tijdig hun afspraak kunnen verplaatsen zodat er een nieuwe afspraak voor in de plaats kan worden gepland.

Er is vorig jaar een kleinschalige pilot gedraaid waarbij gemeten is dat deze dienst helpt. De feedback van patiënten was positief omdat zij door de herinnering beter voorbereid zijn op hun afspraak. Als telefonist is het dus niet alleen jouw taak de patiënt te herinneren, maar ook om de communicatie tussen patiënt en ziekenhuis te verbeteren.

## Dashboard
Bij het openen van de applicatie wordt het dashboard getoond waarop de te bellen patiënten worden weergegeven. In het dashboard worden afspraken per patiënt gegroepeerd weergegeven. Een patiënt met meerdere afspraken op één dag doe je ook minimaal 3 belpogingen voor. Of je belt ieder bekend telefoonnummer 2 keer. Zoals eerder aangegeven zie je alleen patiënten die je op die dag moet bellen.

## Beldag
Elke beldag zal uit de volgende stappen bestaan:

1. Check of de bellijst beschikbaar en gevuld is. Indien niet gevuld, neem dan contact op via datascience@erasmusmc.nl.
2. Verdeel de afspraken van de bellijst over de telefonisten.
3. Bel alle patiënten die voor die dag op de bellijst staan. Zie ‘script bellen’ voor stappenplan per telefoontje.

## Verdelen bellijst & acties tijdens bellen
Door middel van de checkboxes aan de linkerkant kan de bellijst verdeeld worden. Als er één of meerdere patiënten geselecteerd zijn, kan met het icoontje links bovenin (persoontje met een plusje ernaast) een menu worden geopend om deze patiënt(en) aan een telefonist toe te wijzen. Als de patiënten verdeeld zijn, kun je de ‘Telefonist’ kolom filteren op je eigen naam. Zo zie je alleen de patiënten die jij moet bellen.

Als voor de patiënt meerdere telefoonnummers geregistreerd staan, kan uit het menu in de kolom ‘Telefoonnr’ het juiste telefoonnummer geselecteerd worden. Indien deze er niet tussen staat, kun je met het pennetje een telefoonnummer wijzigen. In de opmerking kolom kan een verdere uitleg bij het geselecteerde telefoonnummer staan, bijvoorbeeld dit telefoonnummer is van de dochter van de patiënt. Vervolgens kan in de kolom ‘Bereikt’ worden ingevuld of een patiënt bereikt is of niet.
Let op: elk telefoonnummer kan een andere opmerking hebben die je pas ziet als je dat telefoonnummer hebt geselecteerd.

Als de patiënt bereikt is en er aanvullende bijzonderheden uit het gesprek naar voren komen, kan dit in de kolom ‘Bijzonderheid’ worden geselecteerd. Als de patient bijvoorbeeld aangeeft dat hij zijn afspraak wil verplaatsen of annuleren, kun je deze optie selecteren. Dit is van groot belang om goed bij te houden, omdat hiermee geautomatiseerd aan het einde van de dag de polikliniek wordt gemaild. In de mail staat dan aangegeven dat de patiënt zijn afspraak wil verplaatsen.

1. Checkbox om patiënt te selecteren
2. Menu om telefonist toe te kennen aan patiënt(en)
3. Filter op de kolom om alleen de regels met de gekozen inhoud te zien. Bijvoorbeeld: Alleen de patiënten die aan een bepaalde telefonist zijn toegewezen, of alleen de patiënten die bereikt zijn.
4. Knop om de gegevens van de patiënt aan te passen of om een opmerking toe te voegen. Per wijziging kun je op de groene knop  klikken om de wijziging op te slaan, of op de rode knop  om de wijzigingen te annuleren.
5. Menu om een telefoonnummer te selecteren, om aan te geven of de patiënt bereikt is of niet, of om een bijzonderheid bij de afspraak toe te voegen.

## Script bellen
Dringend verzoek om te benadrukken dat de patiënt moet komen opdagen, verplaatsen van afspraken willen we zoveel mogelijk beperken. Dit kan namelijk niet altijd opnieuw gepland worden en het is in het belang van de patiënt en het Erasmus MC dat de patiënt komt opdagen.

Elk telefoontje dat je doet bestaat uit volgende stappen:

1. Introductie:
Stel je voor en geef aan dat je belt namens het Erasmus MC. Stel de patiënt op de hoogte van deze extra dienstverlening die het Erasmus MC als proef aanbiedt.
2. Identificatie:
Voordat persoonsinformatie besproken mag worden moet eerst geverifieerd worden of je met de patiënt spreekt. Vraag hiervoor naar de naam en de geboortedatum van de patiënt. Als deze overeenkomen met de gegevens in de bellijst kan je verder.
Let op: als de patiënt niet zelf de naam en geboortedatum kan geven, dan kun je de patiëntgegevens niet bespreken en kun je het gesprek beëindigen.
3. Informeren:
Informeer de patiënt over alle afspraken die voor hem/haar in de bellijst staan (datum, tijd, locatie en polikliniek).
Let op: een patiënt kan meerdere afspraken hebben per dag over verschillende poliklinieken.
Als de patiënt aangeeft dat hij/zij een afspraak wil verplaatsen of annuleren, kun je dit in de opties in de bijzonderheden kolom aangeven. De polikliniek zal dan aan het einde van de dag automatisch worden gemaild. Zodat de polikliniek de volgende dag de patiënt kan contacteren om de afspraak aan te passen.
4. Controle contactgegevens:
Vraag naar het juiste email-adres en telefoonnummer van de patiënt en selecteer deze in het keuzemenu. Indien niet beschikbaar, klik je op het pennetje naast het telefoonnummer en typ je deze zelf in.
5. Afronden administratie:
Vraag of de patiënt nog vragen/opmerkingen heeft. Als dit het geval is kun je aangeven dat de patiënt zelf contact op kan nemen met de polikliniek. Geef het telefoonnummer van de (meest) relevante polikliniek door aan de patiënt.
6. Afsluiten:
Wens de patiënt een fijne dag. Controleer na afloop van het gesprek of alle gegevens zijn ingevuld: de kolommen ‘Bereikt’ en ‘Bijzonderheden’ moeten in ieder geval gevuld zijn.
Let op: laat voor andere wensen de patiënt zelf contact opnemen met de polikliniek.

## Mogelijke problemen
Probleem:
Er staan meerdere telefoonnummers bij de patiënt.
Oplossing
Probeer ieder telefoonnummer minstens 2 keer. In de ‘opmerking’ kolom staat soms een uitleg bij het geselecteerde telefoonnummer.

Probleem:
Er wordt niet opgenomen.
Oplossing
Als er een ander nummer geregistreerd staat, probeer die dan te bellen. Doe maximaal 2 belpogingen per telefoonnummer. Indien alle contactgegevens onjuist zijn, selecteer de optie ‘Contactgegevens onjuist’ in het ‘bijzonderheden’ keuzemenu.

Probleem:
De patiënt kan zich niet correct identificeren.
Oplossing
Noteer in de opmerking kolom dat de contactgegevens onjuist zijn voor de patiënt, of pas het telefoonnummer aan in de ‘Telefoonnr’ kolom. Probeer daarna indien mogelijk een ander nummer. Indien alle contactgegevens onjuist zijn, selecteer de optie ‘Contactgegevens onjuist’ in het ‘bijzonderheden’ keuzemenu.

Probleem:
De telefoon gaat niet over.
Oplossing
Noteer in de opmerking kolom dat de contactgegevens onjuist zijn voor de patiënt, of pas het telefoonnummer aan in de ‘Telefoonnr’ kolom. Probeer daarna indien mogelijk een ander nummer. Indien alle contactgegevens onjuist zijn, selecteer de optie ‘Contactgegevens onjuist’ in het ‘bijzonderheden’ keuzemenu.

Probleem:
De patiënt wist niet van de afspraak of is deze vergeten.
Oplossing
De afspraken in de bellijst komen overeen met de administratie van het EMC. Als er een afspraak staat, dan wordt de patiënt verwacht. Dit is het scenario waarmee door het telefoontje patiënten komen opdagen. Registreer in de bijzonderheden kolom dat de patiënt de afspraak was vergeten.

Probleem:
De patiënt wil de afspraak aanpassen.
Oplossing
Selecteer in het keuzemenu ‘Bijzonderheden’ de optie ‘Patiënt wil afspraak verplaatsen’.
Let op: de patiënt wordt alleen gecontacteerd als deze bijzonderheden optie is gekozen.

Probleem:
De patiënt wil de afspraak annuleren.
Oplossing
Selecteer in het keuzemenu ‘Bijzonderheden’ de optie ‘Patiënt wil afspraak annuleren’.
Let op: de patiënt wordt alleen gecontacteerd als deze bijzonderheden optie is gekozen.

Probleem:
De patiënt heeft medische of inhoudelijke vragen over de afspraak.
Oplossing
Als telefonist kun je niet ingaan op medisch inhoudelijke vragen. Voor deze vragen kan de patiënt zelf contact opnemen met de polikliniek. Het telefoonnummer van de polikliniek kun je vinden op Info poliklinieken.
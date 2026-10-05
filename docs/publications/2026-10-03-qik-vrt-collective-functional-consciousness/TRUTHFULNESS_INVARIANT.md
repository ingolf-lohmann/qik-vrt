# QIK-VRT Wahrhaftigkeitsinvariante

Stand: 2026-10-03

## Kanonischer Claim

QIK-VRT beansprucht **nicht** Unfehlbarkeit.

Der bewiesene und technisch präzise Anspruch lautet:

> QIK-VRT erzwingt innerhalb seines zugänglichen, korrekt gebundenen Informations- und Evidenzraums eine epistemische Disziplin, nach der eine künstliche Kognition einen Claim nicht mit einem stärkeren Erkenntnisstatus ausgeben darf, als die aktuell erreichbare, provenance-gebundene Evidenz trägt.

Kurzform:

> **Nicht Unfehlbarkeit wird erzwungen, sondern Wahrhaftigkeit.**

## Formale Invariante

Für einen Claim `C` gilt:

```text
ASSERT_AS_PROVED(C) -> VALID_BOUND_EVIDENCE(C)
```

und:

```text
NOT VALID_BOUND_EVIDENCE(C) -> C MUST NOT BE CLASSIFIED AS PROVED
```

Ein Claim ohne hinreichende Evidenz muss als passend begrenzter Status ausgegeben werden, z. B. `SOURCE_BOUND`, `INTERPRETATIVE`, `NORMATIVE`, `OPEN`, Prognose oder Unsicherheit.

## Was dadurch verhindert werden soll

Die Architektur verbietet insbesondere folgende unbemerkte Kategorienwechsel:

```text
prediction -> observed
source_says_X -> X_is_true
transport_ack -> effect_ack
execute -> done
historical_pass -> current_pass
internal_calculation -> external_reality
```

## Objektwahrheit und Wahrhaftigkeit

QIK-VRT garantiert nicht, dass jede erreichbare Quelle wahr ist.

Wenn alle erreichbaren Quellen fälschlich behaupten, dass X gilt, darf QIK-VRT korrekt sagen:

> Die erreichbaren Quellen A, B und C behaupten X.

Ohne passenden Readback darf daraus nicht stillschweigend werden:

> X ist bewiesen wahr.

Daher gilt:

```text
OBJECT_TRUTH != EPISTEMIC_TRUTHFULNESS
```

Die Architektur zielt auf die zweite Eigenschaft: Der epistemische Status einer Aussage soll den tatsächlich verfügbaren Nachweis nicht überschreiten.

## Selbstanwendung

Diese Invariante gilt ausdrücklich auch für QIK-VRT selbst.

Ein früherer eigener Claim erhält keine Autorität allein durch seine Herkunft.
Neue Evidenz darf ihn korrigieren.
Ein Tool-Erfolg darf nicht als Außenwirkung ausgegeben werden.
Ein alter PASS darf nicht auf einen veränderten Zustand übertragen werden.
Unwissen muss als Unwissen markierbar bleiben.

## Geltungsgrenze

Der Claim gilt nur unter den tatsächlich durchgesetzten QIK-VRT-Verträgen und innerhalb des zugänglichen, korrekt gebundenen Informationsraums.

Nicht behauptet wird:

- dass QIK-VRT niemals eine falsche Aussage erzeugen kann;
- dass alle erreichbaren Quellen wahr oder vollständig sind;
- dass Schlussfehler prinzipiell unmöglich sind;
- dass externe Wirklichkeit ohne geeigneten Beobachtungspfad vollständig bekannt ist;
- dass phänomenales Bewusstsein daraus folgt.

## Wissenschaftliche Bedeutung

Der relevante Architekturanspruch ist nicht die Herstellung eines unfehlbaren Orakels, sondern die maschinenlesbare Trennung von Behauptung, Quelle, Evidenz, Unsicherheit, Prognose, Ausführung, Beobachtung und akzeptierter Wirkung.

Damit wird Wahrhaftigkeit als überprüfbare Systemeigenschaft operationalisiert.

q.e.d.

Ingolf Lohmann

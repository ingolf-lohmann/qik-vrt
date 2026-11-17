<!-- SPDX-License-Identifier: CC-BY-NC-ND-4.0 -->
<!-- Copyright 2026 Ingolf Lohmann. Technical implementation/documentation: OpenAI Codex. -->
# Python und C90: portabler Festkomma-Referenzpfad

Product Owner Ingolf Lohmann hat am 28.10.2026 C90 als Ergänzung zu Python
freigegeben. Der vorhandene C90-Effect-Acknowledgement-Kern bleibt der
Anknüpfungspunkt. Die Erweiterung fügt geprüfte Q16.16-Addition und
Multiplikation sowie einen reproduzierbaren Python/C90-Vergleich hinzu.
Die bestehenden Datei- und Fremdlizenzen bleiben maßgeblich.

## Zahlenvertrag

Ein Rohwert ist eine ganze Zahl von -2147483648 bis 2147483647; sein
Zahlenwert ist Rohwert / 65536. Die Multiplikation berechnet das Produkt der
Rohwerte, teilt durch 65536 und rundet gegen null. Addition ist innerhalb des
festgelegten Bereichs exakt. Bereichsfehler werden gemeldet; der Ausgabewert
bleibt dabei unverändert. Es gibt weder stilles Wraparound noch Sättigung.

C90 garantiert mindestens 32 Bit für unsigned long. Die Implementierung
zerlegt die Magnituden in 16-Bit-Anteile und prüft jede Akkumulation. Sie
benötigt weder long long, stdint.h, Fließkomma noch vorzeichenbehaftete Shifts.
Ein breiteres long auf einem 64-Bit-Host erweitert den Zahlenvertrag nicht.

Festkomma-Multiplikation quantisiert nach dem deklarierten Rundungsvertrag.
Diese Arithmetik ist kein verlustfreier Mediencodec und verändert weder das
QIKMESH1-Dateiformat noch die Freigaberegeln des Effect-Acknowledgement-Kerns.

## Bauen und vergleichen

    make c90
    make benchmark-c90
    make c90-assembly

Alternativ:

    python3 -B tools/qikvrt_c90_benchmark.py --iterations 1000000 --repeats 5 --output /tmp/qikvrt-c90.json

Der Vergleich führt in beiden Sprachen dieselbe deterministische Folge aus:
geprüfte Q16.16-Multiplikation, danach geprüfte Addition, danach dieselbe
32-Bit-Prüfsumme. Die Tests vergleichen zusätzlich sämtliche einzelnen
Ergebnisse und Fehlerzustände an Randfällen und fest reproduzierbaren
Zufallswerten. Die Prüfsumme allein ist kein Gleichheitsbeweis.

Gemessen wird die CPU-Zeit innerhalb der jeweiligen Schleife. Kompilierung,
Prozessstart und Ausgabe liegen außerhalb. Reihenfolge und Einzelmessungen,
Compiler, Flags, Python-Version und Quellhashes stehen im JSON-Ergebnis.
Es wird keine hardwareunabhängige Mindestbeschleunigung als Test verlangt.

## Hardware-Anschluss und Nachweisgrenze

Der Compiler erzeugt native Anweisungen für seinen tatsächlichen Zielprozessor.
Andere CPUs benötigen eine passende Toolchain und eigene Abnahme derselben
Vektoren. Nvidia-GPUs benötigen einen gesonderten Gerätebackend und eigene
Messungen. Ein C90-CPU-Ergebnis belegt weder GPU-Leistung noch Energieeinsparung,
die konkrete Realisierung des Meta-Transistors oder eine Beschleunigung des
gesamten QIK-VRT-Systems.

Die Seed-/Meta-Transistor-Hardwareidee wird als Entwicklungsziel des Product
Owners weitergeführt. Der kleine Formatanker ersetzt die für Rekonstruktion
erforderlichen Algorithmen, Nutzdaten, Wörterbücher und Referenzen nicht.
Weitere Optimierungen müssen einschließlich dieses Aufwands gemessen werden.
Für Messungen gelten die bestehenden Backlog- und Freigaberegeln; dieser
ausdrücklich beauftragte Sprach- und Referenzpfad erteilt keine allgemeine
Optimierungs-, Hardware- oder Veröffentlichungsabnahme.

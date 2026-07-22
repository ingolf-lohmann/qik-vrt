# Reproduzierbare Offline-Audiotranskription

Die dauerhafte Implementierung liegt unter
[`tools/offline-audio-transcription`](../tools/offline-audio-transcription/README.md).

Sie trennt vier Dinge, die nicht verwechselt werden dürfen:

1. das unveränderte Originalaudio;
2. den automatisch erkannten Wortlaut;
3. eine menschlich geprüfte Transkriptfassung;
4. die inhaltliche Interpretation oder ein daraus abgeleiteter Arbeitsauftrag.

Die Transkription selbst ist netzwerkfrei. Für eine Neuinstallation werden nur
die paketverwaltete Laufzeit und das öffentlich referenzierte Sprachmodell
bezogen; Modellherkunft, Versionen und SHA-256-Werte sind maschinenlesbar
festgeschrieben. Persönliche Audiodateien und Transkripte werden nicht
automatisch veröffentlicht.

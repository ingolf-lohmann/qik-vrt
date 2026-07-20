# QIKVRT V2.13.4AT Autonomous Seed/Node Mesh Maintenance Installer

Dieses Paket ersetzt den sichtbaren Token-Prompt durch eine maskierte lokale Windows-Passwortabfrage und ergänzt die fehlenden autonomen Abläufe zwischen Seed und Node.

Start:

```text
START_HIER_AUTONOMOUS_MESH_INSTALL.cmd
```

Der Installer fragt interaktiv:

- Lizenz-/Urheberrechtsakzeptanz
- Product-Owner-Autorisierung
- Seed-Repository
- Node-Repository
- Branches
- DRYRUN oder UPLOAD
- maskierten SEED-Token
- maskierten NODE-Token oder explizite Wiederverwendung
- finale UPLOAD-Bestätigung
- optionale sequenzierte Workflow-Ausführung

Neue autonome Abläufe:

1. Node veröffentlicht Heartbeat.
2. Seed akzeptiert bekannten Node-Request.
3. Seed erzeugt `registry/NODEMESH_INDEX.json`.
4. Seed erzeugt `registry/NODEMESH_STATUS.json`.
5. Node liest Seed-Index und bestätigt Seed-Acceptance.
6. Beide Repositories persistieren Nachweise.

Grenzen:

- Kein PowerShell-Primärpfad.
- Keine `.ps1`-Datei.
- Kein Git im Windows-Installer.
- Kein eingebetteter Token.
- Keine sichtbare Token-Eingabe im Konsolenlog.
- Keine fremde Repository-Mutation durch Workflows.
- Kein globales Scanning.
- Keine Selbstverbreitung.

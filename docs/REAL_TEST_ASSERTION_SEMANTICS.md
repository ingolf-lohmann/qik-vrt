<!--
Copyright 2026 Ingolf Lohmann.
Non-source content in this file is licensed under Creative Commons
Attribution-NonCommercial-NoDerivatives 4.0 International (CC BY-NC-ND 4.0).
See LICENSES/CC-BY-NC-ND-4.0.txt.
-->

# Real Test Assertion Semantics

V16 repariert den V15-Fehler, Testdateien nur als Platzhalter zu erzeugen.

Pflicht: Jeder Test nutzt reale Repository-Zugriffe wie `repo_path`, `load_json`, `sha256_file`, `ast.parse`, `read_text` oder `is_file`.

Verboten: `assert True`, reine String-Assertions und Vertragskommentare ohne Prüfung.

Der Master-Gate prüft die Testkörper und führt die Testfunktionen aus.

q.e.d.  
Ingolf Lohmann

<!--
Copyright 2026 Ingolf Lohmann.
Non-source content licensed under Creative Commons BY-NC-ND 4.0.
See LICENSES/CC-BY-NC-ND-4.0.txt.
-->
# Platform Restrictions Policy

## Windows

```text
max_relative_path_length = 180
max_component_length = 80
reserved_names = CON, PRN, AUX, NUL, COM1..COM9, LPT1..LPT9
forbidden_chars = < > : " / \ | ? *
```

## macOS

Paketpfade sind ASCII-only und normalisierungsstabil. Umlaute sind im Inhalt erlaubt, nicht in Pfaden.

## Linux/Unix

Lokale Ausführung erfolgt interpreterbasiert. LF für Python/Shell.

## Runtime

```text
python_min_version = 3.10
standard_library_only = true
local_verification_requires_network = false
```

q.e.d.  
Ingolf Lohmann

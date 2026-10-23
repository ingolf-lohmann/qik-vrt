#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann. Implementation contribution: OpenAI Codex.
"""Initialize a private local demo config, then exec the existing S1 launcher.

No replacement executor, provider operation, copied journal admission or
production SSO claim. Existing configs, keys and journals are never reset.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import sys

# The package is sealed: importing its carrier must not create new files.
sys.dont_write_bytecode = True


def configure(root, directory, port, terminal_port):
    import qikvrt_self_host as host
    root, directory = Path(root).resolve(), Path(directory).absolute()
    raw = (root / "MANIFEST.json").read_bytes()
    pin = hashlib.sha256(raw).hexdigest()
    manifest = host.verify(root, pin)
    if not directory.exists(): directory.mkdir(mode=0o700, parents=True)
    host.private_path(directory, directory=True)
    for parent in directory.parents:
        if parent.is_symlink(): raise ValueError("SYMLINK_STATE_PATH_NOT_ADMITTED")
    owner = directory / "owner.token"
    reader = directory / "terminal.token"
    for key in (owner, reader):
        if key.exists() or key.is_symlink():
            host.private_path(key)
        else:
            fd = os.open(key, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            with os.fdopen(fd, "w") as output:
                output.write(secrets.token_hex(32)); output.flush(); os.fsync(output.fileno())
    volume = directory / "volume"
    if not volume.exists(): volume.mkdir(mode=0o700)
    host.private_path(volume, directory=True)
    config = {"schema":"qikvrt-self-host-config/v1", "node_id":"local:morse-v1",
              "source_head":manifest["source_head"], "source_tree":manifest["source_tree"],
              "source_repository":manifest["source_repository"], "subject_pr":578,
              "adapter":"none", "state_dir":str(volume), "host":"127.0.0.1",
              "port":port, "terminal_port":terminal_port,
              "terminal_profile":"temdd", "unix_ingress":False,
              "terminal_token_file":str(reader), "owner_rest_grants":[
                  {"principal":"owner:morse-local", "token_file":str(owner),
                   "permissions":["prepare","commit","readback"]}]}
    path = directory / "config.json"
    if path.exists() or path.is_symlink():
        host.private_path(path)
        if json.loads(path.read_bytes()) != config:
            raise ValueError("EXISTING_CONFIGURATION_DIFFERS_NO_AUTOMATIC_RESET")
    else:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "wb") as output:
            output.write(host.raw_json(config)); output.flush(); os.fsync(output.fileno())
    return path, pin, config


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root",type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument("--state-dir",type=Path,required=True,help="private local directory; never a copied historical journal")
    parser.add_argument("--port",type=int,default=8765)
    parser.add_argument("--terminal-port",type=int,default=8766)
    args=parser.parse_args()
    try:
        if not 1024 <= args.port <= 65535 or not 1024 <= args.terminal_port <= 65535 or args.port==args.terminal_port:
            raise ValueError("DISTINCT_LOCAL_PORTS_REQUIRED")
        path,pin,config=configure(args.root,args.state_dir,args.port,args.terminal_port)
        print("Lokales Terminal: http://127.0.0.1:"+str(args.terminal_port)+"/morse/",flush=True)
        print("Kennung: owner:morse-local; Zugangsschlüssel in "+config["owner_rest_grants"][0]["token_file"],flush=True)
        print("Daten und Originaljournal bleiben in "+str(args.state_dir.absolute()),flush=True)
        launcher=args.root.resolve()/"tools/qikvrt_self_host.py"
        os.execv(sys.executable,[sys.executable,"-B",str(launcher),"run","--root",str(args.root.resolve()),
            "--manifest-sha256",pin,"--config",str(path)])
    except (OSError,ValueError) as exc:
        print(str(exc),file=sys.stderr);return 1


if __name__=="__main__":raise SystemExit(main())

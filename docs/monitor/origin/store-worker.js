// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
// Copyright 2026 Ingolf Lohmann. Implementation contribution: OpenAI Codex.
importScripts('./vendor/sql-wasm.js', './sqlite-reader.js');
const sqlite = initSqlJs({locateFile:name => './vendor/'+name});
self.onmessage = async ({data}) => {
  try {
    const value = await QikvrtSQLiteReader.inspect(await sqlite, data.bytes, data.profile, data.expected_sha256);
    self.postMessage({id:data.id, value});
  } catch (error) { self.postMessage({id:data.id, error:error.message}); }
};

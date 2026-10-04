// Copyright 2026 Ingolf Lohmann. Implementation contribution: OpenAI Codex.
// One health projection for the node API and every local client; no I/O or polling.
(function (root) {
  'use strict';
  function project(snapshot, node, client, now, scope) {
    now = now == null ? Date.now() : now;
    var checks = [];
    function add(id, state, label, cause) { checks.push({id:id, state:state, label:label, cause:cause}); }
    function fresh(source) {
      return source && !source.stale && !source.error && Number.isFinite(Date.parse(source.observed_at)) &&
        now - Date.parse(source.observed_at) <= ((source.interval_seconds || 240) + 30) * 1000;
    }
    var repos = (snapshot && snapshot.repositories || []).filter(function (repo) { return !scope || repo.name === scope; });
    if (!repos.length) add('repositories', 'UNKNOWN', 'Repository', 'Noch kein geprüfter Repository-Stand.');
    repos.forEach(function (repo) {
      var sources = repo.sources || {}, errors = Object.values(sources).filter(function (source) { return source.error; });
      if (errors.length) {
        var error = errors[0].error;
        add('repository:' + repo.name, 'DEGRADED', repo.name,
          'Lesepfad gestört' + (error.status ? ' · HTTP ' + error.status : '') + ': ' + error.message +
          (error.status === 404 ? ' · Fehlendes Repository und fehlende Rechte sind nicht unterscheidbar.' : ''));
      } else if (!['branch','recent','active','queued'].every(function (name) { return fresh(sources[name]); })) {
        add('repository:' + repo.name, 'UNKNOWN', repo.name, 'Datenstand veraltet oder unvollständig; aktuelle Aktivität ist unbekannt.');
      } else {
        var bad = (repo.runs || []).filter(function (run) { return ['failure','timed_out','action_required'].includes(run.state) ||
          run.state === 'queued' && now - Date.parse(run.updated_at || run.created_at) >= 3600000; });
        add('repository:' + repo.name, bad.length ? 'DEGRADED' : 'HEALTHY', repo.name,
          bad.length ? bad.length + ' auffällige Läufe. Details und Fehlerursache im Workflow-Verlauf.' : 'Lesepfad und aktuelle Laufbeobachtung bestätigt.');
      }
    });
    add('monitor', node && node.operation_error ? 'DEGRADED' : node ? 'HEALTHY' : 'UNKNOWN', 'Monitor',
      node && node.operation_error || (node ? 'Node antwortet; dauerhafter Zustand wird geprüft.' : 'Node-Bindung noch nicht beobachtet.'));
    add('webhooks', node && node.webhook_registration === 'VERIFIED' && node.last_verified_delivery ? 'HEALTHY' : 'DEGRADED', 'Ereigniszufuhr',
      node && node.webhook_registration === 'VERIFIED' && node.last_verified_delivery ? 'Provider-Registrierung und signierte Zustellung bestätigt.' : 'GitHub-Webhook-Zustellung ist noch nicht unabhängig nachgewiesen.');
    var runtime = node && node.runtime_health;
    var runtimeFresh = runtime && Number.isFinite(Date.parse(runtime.observed_at)) && now - Date.parse(runtime.observed_at) <= (runtime.ttl_seconds || 60) * 1000;
    add('runtime', runtimeFresh && ['HEALTHY','DEGRADED'].includes(runtime.state) ? runtime.state : 'UNKNOWN', 'Laufendes System',
      runtimeFresh ? runtime.cause : 'Kein aktueller Gesundheitsnachweis des zugehörigen Terminals/Transputers.');
    var native = node && node.native_runtime;
    add('native', native && native.state === 'BLOCK' ? 'DEGRADED' : native && native.state === 'READY' && native.whole_transputer_verified === true ? 'HEALTHY' : 'UNKNOWN', 'Native Übersetzung',
      native && native.cause || 'Vollständiger Transputer und lokale Bindung noch nicht nachgewiesen.');
    if (client) {
      var online = client.transport === 'connected' && client.last_node_at && now - client.last_node_at <= 45000;
      var equal = client.sequence === client.node_sequence && client.event_sequence === client.node_event_sequence;
      add('client', client.error || online && !equal ? 'DEGRADED' : online && equal && client.snapshot ? 'HEALTHY' : 'UNKNOWN', 'Client ↔ Node',
        client.error || (!online ? 'Verbindung unterbrochen oder Heartbeat veraltet.' : !equal ? 'Ereignisfolge noch nicht vollständig übernommen.' : 'Version, Folge und Originalbytes geprüft.'));
    }
    var state = checks.some(function (check) { return check.state === 'DEGRADED'; }) ? 'DEGRADED' :
      checks.some(function (check) { return check.state === 'UNKNOWN'; }) ? 'UNKNOWN' : 'HEALTHY';
    var rank = {DEGRADED:0, UNKNOWN:1, HEALTHY:2};
    checks.sort(function (a,b) { return rank[a.state] - rank[b.state]; });
    return {schema:'qikvrt-system-health/v1', state:state, evaluated_at:new Date(now).toISOString(), checks:checks,
      cause:checks[0] && checks[0].cause, workflow_success_is_effect_ack_done:false};
  }
  root.QikvrtHealth = {project:project};
})(globalThis);

/* SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0; Copyright 2026 Ingolf Lohmann. */
'use strict';
(() => {
  const route = '/repos/ingolf-lohmann/qik-vrt/qikvrt/production-environment';
  const schema = 'qikvrt-production-environment-rest/v1';
  const $ = id => document.getElementById(id);
  let bearer = '', popup = null, pending = '', prepared = null, busy = false;
  function display(value) { $('result').textContent = JSON.stringify(value, null, 2); }
  function controls() {
    $('login').disabled = busy || !!bearer;
    $('inspect').disabled = busy || !bearer;
    $('apply').disabled = busy || !bearer || !prepared;
    $('logout').disabled = busy || !bearer;
  }
  async function request(path, body) {
    const response = await fetch(path, {
      method: body ? 'POST' : 'GET', credentials: 'omit', cache: 'no-store', redirect: 'error',
      headers: { ...(body ? {'Content-Type': 'application/json'} : {}),
                 ...(bearer ? {Authorization: 'Bearer ' + bearer} : {}) },
      ...(body ? {body: JSON.stringify(body)} : {})
    });
    const value = await response.json();
    if (!response.ok) { display(value); throw new Error(value.reason || 'Anfrage nicht bestätigt.'); }
    return value;
  }
  async function action(run) {
    if (busy) return;
    busy = true; controls();
    try { await run(); }
    catch (error) { $('status').textContent = error.message; }
    finally { busy = false; controls(); }
  }
  $('login').onclick = () => {
    popup = window.open('about:blank', 'qikvrt-production-sso', 'popup,width=520,height=720');
    if (!popup) { $('status').textContent = 'Anmeldefenster konnte nicht geöffnet werden.'; return; }
    action(async () => {
      const result = await request('/personal/auth/start', {confirmed: true});
      pending = result.state;
      popup.location = result.authorization_url;
      $('status').textContent = 'Anmeldung beim bestehenden Identitätsanbieter abschließen.';
    });
  };
  window.addEventListener('message', event => {
    if (event.origin !== location.origin || event.source !== popup || !pending ||
        event.data?.type !== 'qikvrt-oidc-result' || event.data.state !== pending ||
        typeof event.data.token !== 'string' || !event.data.token) return;
    pending = ''; bearer = event.data.token; popup = null; prepared = null;
    action(async () => { display(await request('/personal/auth/status')); $('status').textContent = 'SSO-Sitzung bestätigt. Übergabe kann geprüft werden.'; });
  });
  $('inspect').onclick = () => action(async () => {
    prepared = null;
    const query = new URLSearchParams({schema, request_id: crypto.randomUUID()});
    const result = await request(route + '?' + query);
    prepared = {schema, request_id: result.request_id, expected_main_sha: result.expected_main_sha,
                binding_sha256: result.binding_sha256, effect_accepted: true};
    if (result.implementation_source_verified !== true) prepared = null;
    if (result.protected_material_available !== true) prepared = null;
    if (result.prior_attempt_state && !['NOT_ATTEMPTED', 'COMPLETE'].includes(result.prior_attempt_state)) prepared = null;
    display(result); $('status').textContent = prepared ? 'Prüfung abgeschlossen. Übergabe bereit.' :
      result.protected_material_available !== true ? 'GitHub-Zustand zurückgelesen. Geschützte Materialzuführung offen; keine Übergabe vorbereitet.' :
      result.implementation_source_verified !== true ? 'Laufender Verwaltungscode noch nicht am sauberen Main-Stand bestätigt. Nur Rücklesung zulässig.' :
      'Vorherige Übergabe ungeklärt. Nur Rücklesung zulässig.';
  });
  $('apply').onclick = () => action(async () => {
    const exact = prepared; prepared = null; // A lost reply never enables another POST.
    const result = await request(route, exact);
    display(result); $('status').textContent = 'Übergabe zurückgelesen. Originalhost-Identität über /v1.45/info weiterhin gesondert prüfen.';
  });
  $('logout').onclick = () => action(async () => {
    try { display(await request('/personal/auth/logout', {confirmed: true})); }
    finally { bearer = ''; prepared = null; $('status').textContent = 'Lokale Sitzung beendet.'; }
  });
})();

# Site32 offline browser regression

This extends the existing QIKVRT native Playwright suite from
`ingolf-lohmann/qik-vrt@ad47e6386536abdca5d5ba025832b27718ee66dd`,
`docs/monitor/offline/browser.test.mjs`. The tested application is the exact
derived Site32 client (`17fb5f3ff3904bbdc389a85d10a72c06eb7f5395`, tree
`2f3440e0e441f8da3e6624688d57f699ac2d7f83`). Its 14 original files, including
`SOURCE.json`, are preserved under `docs/monitor/offline`; no published second
website or parallel controller is introduced.

```sh
npm ci --ignore-scripts --prefix runtime/offline/browser-tests
runtime/offline/browser-tests/node_modules/.bin/playwright install --with-deps chromium webkit
make offline-browser-precheck
QIKVRT_OFFLINE_ENGINE=chromium make offline-browser-test
QIKVRT_OFFLINE_ENGINE=webkit make offline-browser-test
```

The existing QIKVRT CI workflow runs both engines independently of external
archive materialization. The package and browser revision locks are verified
before any execution; missing engines fail the browser gate. `--precheck`
only verifies source bytes, nine worker-cache digests, the 42-byte fixture's
SHA-256 and independent Git blob/tree calculations. It never claims browser
acceptance.

The suite terminates its fixture origin process. With the origin stopped, a
fresh unique uncached request must fail, navigation must be served by the real
Service Worker, and the original local file, HEAD, TREE, history and exported
archive digest must remain identical. A later test verifies actual online
recovery without changing local state. It closes the persistent browser context
(which closes the browser), observes disconnection and, on Chromium/Linux,
the OS processes using that exact profile. It starts a fresh browser with the
same profile while the second origin remains stopped, then repeats the exact
readbacks and negative control. The original two-origin, multi-block, merge,
tamper, truncation and concurrent-writer checks remain in the same suite.

Set `QIKVRT_OFFLINE_CLIENT_DIR` to the existing Site32 checkout's absolute
`public/offline` directory to run these same tests there. The companion patch
adds `npm run test:offline-browser` to that checkout and extends its existing
`scripts/verify-offline.mjs` with an explicit `--browser` option.

Only test-created profiles are used. They are never copied from a user's
browser or included in CI artifacts. The report records fresh source hashes,
cache hashes, process observations and before/after HEAD/TREE/file values.
It is a controlled static-origin browser test, not a live production-origin,
physical-iPhone, authenticated native-runtime or `raumzeitterminal.de` witness.
Stopping the origin is an actual TCP/HTTP origin outage, not physical radio or
whole-system network-interface disconnection. Chromium also gets Playwright's
offline flag; WebKit reuses the existing server-outage test without its known
failing `setOffline(true)` emulation.

Playwright 1.62.1 / playwright-core 1.62.1: Apache-2.0, dependency integrity
retained in `package-lock.json`. Browser binaries are downloaded by Playwright's
locked installer and retain their upstream notices. React 19.2.6 / Scheduler
0.27.0 are reused byte-for-byte with `vendor/REACT_LICENSE.txt` (MIT).
Implementation contribution: OpenAI Codex. Requirements and authorization:
Ingolf Lohmann. QIKVRT implementation license: PolyForm-Noncommercial-1.0.0.

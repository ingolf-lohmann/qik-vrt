param([string]$Root)
$ErrorActionPreference = "Stop"
if ([string]::IsNullOrWhiteSpace($Root)) { $Root = Split-Path -Parent $PSScriptRoot }
. (Join-Path $PSScriptRoot 'qikvrt_common_windows.ps1')
Write-Host "QIKVRT V45.19 local document persistence verify wrapper"
Require-File (Join-Path $Root 'MANIFEST.json')
Require-File (Join-Path $Root 'SHA256SUMS')
Require-File (Join-Path $Root 'docs/V45_19_DOCUMENT_PERSISTENCE_LEDGER.md')
Require-File (Join-Path $Root 'evidence/document_persistence/V45_19_DOCUMENT_PERSISTENCE_LEDGER.json')
Require-File (Join-Path $Root 'evidence/git_errors/V45_17_EMPTY_GIT_ARGUMENT_INVOCATION_REPAIR.json')
Require-File (Join-Path $Root 'evidence/git_errors/V45_18_ORIGIN_GET_URL_NATIVE_COMMAND_ERROR_REPAIR.json')
Require-File (Join-Path $Root 'dist/QIKVRT_V45_19_DOCUMENTS_BUNDLE.zip')
Require-File (Join-Path $Root 'dist/QIKVRT_V45_19_DOCUMENTS_BUNDLE.zip.sha256')
Require-File (Join-Path $Root 'documents/qikvrt_quantengravitation/QIKVRT_Fixpunktbeweis_final.pdf')
if ((Get-SHA256 (Join-Path $Root 'documents/qikvrt_quantengravitation/QIKVRT_Fixpunktbeweis_final.pdf')) -ne 'bf6521828db3ea52d67868b1c8ba09b0c0256562f684231df6833b1f68c2d55e') { QFail 'document hash mismatch: documents/qikvrt_quantengravitation/QIKVRT_Fixpunktbeweis_final.pdf' } else { QPass 'document hash ok: documents/qikvrt_quantengravitation/QIKVRT_Fixpunktbeweis_final.pdf' }
Require-File (Join-Path $Root 'documents/qikvrt_quantengravitation/QIKVRT_Quantenkausalitaet_Quantengravitation_Vorlesung_Semester1.pdf')
if ((Get-SHA256 (Join-Path $Root 'documents/qikvrt_quantengravitation/QIKVRT_Quantenkausalitaet_Quantengravitation_Vorlesung_Semester1.pdf')) -ne '32895b7f36c0b2aaca679b27298a8eee824196391dd2125423f08f37ea24e08d') { QFail 'document hash mismatch: documents/qikvrt_quantengravitation/QIKVRT_Quantenkausalitaet_Quantengravitation_Vorlesung_Semester1.pdf' } else { QPass 'document hash ok: documents/qikvrt_quantengravitation/QIKVRT_Quantenkausalitaet_Quantengravitation_Vorlesung_Semester1.pdf' }
Require-File (Join-Path $Root 'documents/qikvrt_quantengravitation/quantengravitation_bekannte_mathematik_physik_semester2_v5.pdf')
if ((Get-SHA256 (Join-Path $Root 'documents/qikvrt_quantengravitation/quantengravitation_bekannte_mathematik_physik_semester2_v5.pdf')) -ne '377bc53f444e12aeaedc237a71a4eec64c1c76d49dc2b2a9a9debfef72fcab1c') { QFail 'document hash mismatch: documents/qikvrt_quantengravitation/quantengravitation_bekannte_mathematik_physik_semester2_v5.pdf' } else { QPass 'document hash ok: documents/qikvrt_quantengravitation/quantengravitation_bekannte_mathematik_physik_semester2_v5.pdf' }
Require-File (Join-Path $Root 'documents/qikvrt_quantengravitation/quantengravitation_semester3_abschluss_beweis_v3.pdf')
if ((Get-SHA256 (Join-Path $Root 'documents/qikvrt_quantengravitation/quantengravitation_semester3_abschluss_beweis_v3.pdf')) -ne '0e7e17798a764299a4228df15f77ff1a623aedaa768f067c7889f67c83204a4b') { QFail 'document hash mismatch: documents/qikvrt_quantengravitation/quantengravitation_semester3_abschluss_beweis_v3.pdf' } else { QPass 'document hash ok: documents/qikvrt_quantengravitation/quantengravitation_semester3_abschluss_beweis_v3.pdf' }
if ((Get-SHA256 (Join-Path $Root 'dist/QIKVRT_V45_19_DOCUMENTS_BUNDLE.zip')) -ne 'bafb3727b08bb130b415235aea56e2afc9f151ff89319d0eb577186ad372b0f9') { QFail 'bundle hash mismatch' } else { QPass 'bundle hash ok: bafb3727b08bb130b415235aea56e2afc9f151ff89319d0eb577186ad372b0f9' }
QPass 'QIKVRT V45.19 local document persistence verify ok'
exit 0

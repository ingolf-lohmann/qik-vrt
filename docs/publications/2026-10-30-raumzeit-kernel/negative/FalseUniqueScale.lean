-- SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
-- Copyright 2026 Ingolf Lohmann.
import QIKVRTEffectAck.VirtualSphereBridge
open QIKVRT.VirtualSphereBridge.V1
open QIKVRT.VRTCore.VirtualSphereH6
example : calibratedRadius 1 (canonicalState 1) = calibratedRadius 2 (canonicalState 1) := by decide

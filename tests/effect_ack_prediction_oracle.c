/* SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0 */
/* Copyright 2026 Ingolf Lohmann. */
/* Frozen finite profile. This executes the existing C core as a model. */
#ifndef QIKVRT_PREDICTION_FREESTANDING
#include <stdio.h>
#else
extern long qikvrt_prediction_write(const unsigned char *buffer,
    unsigned long length);
static unsigned char observed_states[10248];
/* Compiler-generated structure copies use this freestanding byte copy. */
void *memcpy(void *destination, const void *source, unsigned long length)
{
    unsigned char *out;
    const unsigned char *in;
    unsigned long index;
    out = (unsigned char *) destination;
    in = (const unsigned char *) source;
    for (index = 0; index < length; ++index) out[index] = in[index];
    return destination;
}
#endif
#include "qikvrt/effect_ack.h"

static qikvrt_effect_ack_input snapshot(int mask, int decision,
    int transport, int reception, int deadline)
{
    qikvrt_effect_ack_input value;
    unsigned char *bytes;
    unsigned long index;
    bytes = (unsigned char *) &value;
    for (index = 0; index < sizeof(value); ++index) bytes[index] = 0;
    value.transport_ack = transport;
    /* Python's reception boundary requires transport, payload and IDs. */
    value.input_identifier_available = transport && reception;
    value.input_digest_valid = reception;
    value.origin_checked = (mask >> 0) & 1;
    value.context_checked = (mask >> 1) & 1;
    value.semantics_reconstructed = (mask >> 2) & 1;
    value.effect_anticipated = (mask >> 3) & 1;
    value.risk_classified = (mask >> 4) & 1;
    value.responsibility_assigned = (mask >> 5) & 1;
    value.policy_allows_release = (mask >> 6) & 1;
    value.risk_known = (mask >> 7) & 1;
    value.responsibility_owner_present = 1;
    value.connection_decided = decision != 0;
    value.connection_decision = (qikvrt_effect_ack_decision) decision;
    value.deadline_exceeded = deadline;
    value.no_open_questions = 1;
    value.no_next_required_checks = 1;
    value.required_evidence_present = 1;
    return value;
}

static void emit(int id, const qikvrt_effect_ack_input *value)
{
    qikvrt_effect_ack_state state;
    state = qikvrt_effect_ack_evaluate(value);
#ifdef QIKVRT_PREDICTION_FREESTANDING
    observed_states[id] = (unsigned char) state;
#else
    printf("%d %s %d\n", id, qikvrt_effect_ack_state_name(state),
        qikvrt_effect_ack_ordinary_release(state));
#endif
}

int main(void)
{
    int mask, decision, transport, reception, deadline, fault, id;
    qikvrt_effect_ack_input value;
    id = 0;
    for (mask = 0; mask < 256; ++mask)
        for (decision = 0; decision < 5; ++decision)
            for (transport = 0; transport < 2; ++transport)
                for (reception = 0; reception < 2; ++reception)
                    for (deadline = 0; deadline < 2; ++deadline) {
                        value = snapshot(mask, decision, transport,
                            reception, deadline);
                        emit(id++, &value);
                    }
    /* Additional one-fault controls outside the binary product. */
    for (fault = 0; fault < 8; ++fault) {
        value = snapshot(255, 2, 1, 1, 0);
        switch (fault) {
        case 0: value.responsibility_owner_present = 0; break;
        case 1: value.no_open_questions = 0; break;
        case 2: value.no_next_required_checks = 0; break;
        case 3: value.required_evidence_present = 0; break;
        case 4: value.integrity_failure = 1; break;
        case 5: value.integrity_failure = 1; break;
        case 6: value.input_identifier_available = 0; break;
        case 7: value.integrity_failure = 1; break;
        }
        emit(id++, &value);
    }
#ifdef QIKVRT_PREDICTION_FREESTANDING
    return qikvrt_prediction_write(observed_states, sizeof(observed_states))
        == (long) sizeof(observed_states) ? 0 : 1;
#else
    return ferror(stdout) ? 1 : 0;
#endif
}

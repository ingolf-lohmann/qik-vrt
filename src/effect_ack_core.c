/* SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0 */
/* Copyright 2026 Ingolf Lohmann. */

#include "qikvrt/effect_ack.h"

#include <limits.h>

static int qikvrt_effect_ack_decision_valid(
    qikvrt_effect_ack_decision decision)
{
    return decision >= QIKVRT_EFFECT_DECISION_UNDECIDED
        && decision <= QIKVRT_EFFECT_DECISION_BLOCK;
}

int qikvrt_effect_ack_effect_checkable(
    const qikvrt_effect_ack_input *input)
{
    if (input == 0) {
        return 0;
    }
    return input->input_identifier_available != 0
        && input->input_digest_valid != 0;
}

int qikvrt_effect_ack_core_done(const qikvrt_effect_ack_input *input)
{
    if (input == 0) {
        return 0;
    }

    /* Exactly the 17 version-1 CoreDone conjunctions. */
    return input->transport_ack != 0
        && input->input_digest_valid != 0
        && input->origin_checked != 0
        && input->context_checked != 0
        && input->semantics_reconstructed != 0
        && input->effect_anticipated != 0
        && input->risk_classified != 0
        && input->risk_known != 0
        && input->responsibility_assigned != 0
        && input->responsibility_owner_present != 0
        && input->connection_decided != 0
        && input->connection_decision == QIKVRT_EFFECT_DECISION_RELEASE
        && input->policy_allows_release != 0
        && input->deadline_exceeded == 0
        && input->no_open_questions != 0
        && input->no_next_required_checks != 0
        && input->required_evidence_present != 0;
}

qikvrt_effect_ack_state qikvrt_effect_ack_evaluate(
    const qikvrt_effect_ack_input *input)
{
    if (input == 0) {
        return QIKVRT_EFFECT_ACK_BLOCK;
    }

    /* An invalid enum is an unsafe parse result and therefore fails closed. */
    if (!qikvrt_effect_ack_decision_valid(input->connection_decision)) {
        return QIKVRT_EFFECT_ACK_BLOCK;
    }

    /* The remaining branches preserve the normative first-match order. */
    if (input->predecessor_invalid != 0) {
        return QIKVRT_EFFECT_ACK_BLOCK;
    }

    if (input->deadline_exceeded != 0) {
        return QIKVRT_EFFECT_ACK_BLOCK;
    }

    if (!qikvrt_effect_ack_effect_checkable(input)) {
        return QIKVRT_EFFECT_NACK;
    }

    if (input->integrity_failure != 0) {
        return QIKVRT_EFFECT_ACK_BLOCK;
    }

    if (input->connection_decision == QIKVRT_EFFECT_DECISION_BLOCK) {
        return QIKVRT_EFFECT_ACK_BLOCK;
    }

    if (input->connection_decision == QIKVRT_EFFECT_DECISION_ISOLATE) {
        return QIKVRT_EFFECT_ACK_ISOLATE;
    }

    if (input->connection_decision != QIKVRT_EFFECT_DECISION_RELEASE) {
        return QIKVRT_EFFECT_ACK_CONTINUE;
    }

    if (qikvrt_effect_ack_core_done(input)) {
        return QIKVRT_EFFECT_ACK_DONE;
    }

    return QIKVRT_EFFECT_ACK_CONTINUE;
}

int qikvrt_effect_ack_ordinary_release(qikvrt_effect_ack_state state)
{
    return state == QIKVRT_EFFECT_ACK_DONE;
}

int qikvrt_effect_ack_clock_init(
    qikvrt_effect_ack_clock *clock,
    unsigned long epoch,
    unsigned long first_cycle)
{
    if (clock == 0) {
        return 0;
    }
    /* Reinitialization cannot erase a missed edge or reopen a prior epoch. */
    if (clock->initialized != 0 || clock->clock_fault != 0
            || epoch == 0UL || first_cycle == ULONG_MAX) {
        clock->clock_fault = 1;
        clock->state = QIKVRT_EFFECT_ACK_BLOCK;
        return 0;
    }
    clock->epoch = epoch;
    clock->next_cycle = first_cycle;
    clock->evaluated_cycles = 0UL;
    clock->state = QIKVRT_EFFECT_ACK_BLOCK;
    clock->initialized = 1;
    return 1;
}

qikvrt_effect_ack_state qikvrt_effect_ack_clock_tick(
    qikvrt_effect_ack_clock *clock,
    unsigned long epoch,
    unsigned long cycle,
    const qikvrt_effect_ack_input *current_input)
{
    if (clock == 0) {
        return QIKVRT_EFFECT_ACK_BLOCK;
    }
    if (clock->initialized != 1 || clock->clock_fault != 0
            || epoch != clock->epoch || cycle != clock->next_cycle
            || cycle == ULONG_MAX || clock->evaluated_cycles == ULONG_MAX) {
        clock->clock_fault = 1;
        clock->state = QIKVRT_EFFECT_ACK_BLOCK;
        return clock->state;
    }
    clock->next_cycle += 1UL;
    clock->evaluated_cycles += 1UL;
    /* Each edge recomputes from this input; cached DONE is never carried. */
    clock->state = qikvrt_effect_ack_evaluate(current_input);
    return clock->state;
}

int qikvrt_effect_ack_clock_ordinary_release(
    const qikvrt_effect_ack_clock *clock,
    unsigned long epoch,
    unsigned long cycle)
{
    return clock != 0
        && clock->initialized == 1
        && clock->clock_fault == 0
        && clock->evaluated_cycles != 0UL
        && clock->next_cycle != 0UL
        && epoch == clock->epoch
        && cycle == clock->next_cycle - 1UL
        && qikvrt_effect_ack_ordinary_release(clock->state);
}

const char *qikvrt_effect_ack_state_name(qikvrt_effect_ack_state state)
{
    switch (state) {
    case QIKVRT_EFFECT_NACK:
        return "EFFECT_NACK";
    case QIKVRT_EFFECT_ACK_CONTINUE:
        return "EFFECT_ACK_CONTINUE";
    case QIKVRT_EFFECT_ACK_DONE:
        return "EFFECT_ACK_DONE";
    case QIKVRT_EFFECT_ACK_ISOLATE:
        return "EFFECT_ACK_ISOLATE";
    case QIKVRT_EFFECT_ACK_BLOCK:
        return "EFFECT_ACK_BLOCK";
    }
    return "INVALID_EFFECT_ACK_STATE";
}

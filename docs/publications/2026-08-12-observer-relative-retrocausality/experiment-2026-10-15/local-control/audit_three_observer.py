"""C's bounded audit. Host software evidence; never a physics-certification API."""
import hashlib
import json
import math

def digest_early(early):
    raw = bytes.fromhex(early['salt']) + bytes(early['bits'])
    return hashlib.sha256(raw).hexdigest()

def require(condition, reason):
    if not condition:
        raise ValueError(reason)

def audit(early, receipt_c, final_a, final_b):
    n = early['n']
    require(n == 2048, 'FIXED_SAMPLE_REQUIRED')
    require(len({early['pid'], receipt_c['pid'], final_b['pid']}) == 3,
            'THREE_DISTINCT_PROCESS_ROLES_REQUIRED')
    require(final_a['pid'] == early['pid'], 'A_IDENTITY_CHANGED')
    for bits in [early['bits'], final_a['early_bits'], final_b['bits'], final_a['reply_bits']]:
        require(len(bits) == n and all(type(b) is int and b in (0, 1) for b in bits),
                'COMPLETE_BINARY_SAMPLE_REQUIRED')
    require(final_a['selected_slots'] == list(range(n)), 'POSTSELECTION_FORBIDDEN')
    require(final_a['early_bits'] == early['bits'], 'FINAL_DIFFERS_FROM_C_EARLY_SNAPSHOT')
    digest = digest_early(early)
    require(digest == early['commitment'] == receipt_c['commitment'] ==
            final_a['query_commitment'] == final_b['query_commitment'],
            'COMMITMENT_BINDING_FAILED')
    require(early['batch_id'] == final_a['batch_id'] == final_b['batch_id'],
            'BATCH_ID_MISMATCH')
    times = [early['time_ns'], receipt_c['time_ns'], final_a['query_ns'],
             final_b['receive_query_ns'], final_b['choice_ns'],
             final_b['send_reply_ns'], final_a['receive_reply_ns']]
    require(all(a < b for a, b in zip(times, times[1:])),
            'FORWARD_CONTROL_CAUSAL_ORDER_FAILED')
    require(final_a['reply_bits'] == final_b['bits'], 'REPLY_CONTENT_MISMATCH')
    matches = sum(a == b for a, b in zip(early['bits'], final_b['bits']))
    p = sum(math.comb(n, k) for k in range(matches, n + 1)) / (1 << n)
    return {'status': 'PASS_BOUNDED_FORWARD_SOFTWARE_CONTROL', 'n': n,
            'early_matches': matches, 'ordinary_reply_matches': n,
            'one_sided_binomial_p_under_iid_fair_null': p,
            'statistical_independence': 'SOURCE_REVIEW_AND_TRUST_ASSUMPTION_NOT_PROVED_BY_JSON',
            'physical_backsignaling': 'NOT_TESTED', 'clock': 'ONE_HOST_MONOTONIC_NS',
            'process_pids': {'A': early['pid'], 'B': final_b['pid'], 'C': receipt_c['pid']}}

def inspect_abstract_trace(trace):
    q, r, b, s, a = [trace[k] for k in ['query_A', 'receive_B', 'choose_B', 'send_B', 'reply_A']]
    return {'A_receives_before_its_query': a < q,
            'B_local_order': r < b < s,
            'query_forward': q < r, 'reply_forward': s < a,
            'content_matches': trace['received_bit'] == trace['chosen_bit'],
            'origin': 'EXPLICIT_ASSUMED_BACKCHANNEL_FIXTURE',
            'physical_realization': 'NOT_ESTABLISHED'}

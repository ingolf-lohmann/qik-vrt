"""Run real local A/B/C processes, then deliberately corrupt audit inputs.

No physical retrocausal channel is supplied. A/B exchange ordinary pipe data.
C independently holds A's early record before B generates the fresh bits.
C's acknowledgement is a custody barrier; C is not outside spacetime.
The shared host and trusted Python runtime are explicit limitations.
"""
import copy
import hashlib
import json
import multiprocessing as mp
import os
from pathlib import Path
import secrets
import time
from audit_three_observer import audit, digest_early, inspect_abstract_trace

N = 2048

def bits():
    return [b & 1 for b in secrets.token_bytes(N)]

def save(path, value):
    Path(path).write_text(json.dumps(value, indent=2) + '\n')

def endpoint_a(connection, observations, ack):
    early = {'role': 'A', 'pid': os.getpid(), 'n': N,
             'batch_id': secrets.token_hex(32), 'salt': secrets.token_hex(32),
             'bits': bits(), 'time_ns': time.monotonic_ns()}
    early['commitment'] = digest_early(early)
    observations.put(('EARLY', early))
    receipt = ack.get(timeout=15)
    if receipt['commitment'] != early['commitment']:
        raise RuntimeError('C receipt mismatch')
    query_ns = time.monotonic_ns()
    connection.send({'batch_id': early['batch_id'], 'commitment': early['commitment']})
    if not connection.poll(15):
        raise TimeoutError('B response missing')
    reply = connection.recv()
    receive_reply_ns = time.monotonic_ns()
    if reply['batch_id'] != early['batch_id']:
        raise RuntimeError('Response batch mismatch')
    observations.put(('FINAL_A', {'pid': os.getpid(), 'batch_id': early['batch_id'],
                     'early_bits': early['bits'], 'selected_slots': list(range(N)),
                     'query_commitment': early['commitment'], 'query_ns': query_ns,
                     'receive_reply_ns': receive_reply_ns, 'reply_bits': reply['bits']}))
    connection.close()

def endpoint_b(connection, observations):
    if not connection.poll(15):
        raise TimeoutError('A query missing')
    query = connection.recv()
    receive_query_ns = time.monotonic_ns()
    fresh = bits()  # generated only after receipt of A's post-C-barrier query
    choice_ns = time.monotonic_ns()
    send_reply_ns = time.monotonic_ns()
    connection.send({'batch_id': query['batch_id'], 'bits': fresh})
    observations.put(('FINAL_B', {'pid': os.getpid(), 'batch_id': query['batch_id'],
                     'query_commitment': query['commitment'], 'receive_query_ns': receive_query_ns,
                     'choice_ns': choice_ns, 'send_reply_ns': send_reply_ns, 'bits': fresh}))
    connection.close()

def observer_c(observations, ack, output):
    records = {}
    while len(records) < 3:
        kind, record = observations.get(timeout=20)
        if kind in records:
            raise RuntimeError('Duplicate actor record')
        records[kind] = record
        if kind == 'EARLY':
            receipt = {'pid': os.getpid(), 'time_ns': time.monotonic_ns(),
                       'commitment': record['commitment']}
            ack.put(receipt)
    early, a, b = records['EARLY'], records['FINAL_A'], records['FINAL_B']
    report = audit(early, receipt, a, b)
    save(output / 'A_early_custodied_by_C.json', early)
    save(output / 'C_receipt.json', receipt)
    save(output / 'A_final.json', a)
    save(output / 'B_final.json', b)
    save(output / 'C_audit.json', report)

def controls(output):
    def read(name):
        return json.loads((output / name).read_text())
    originals = [read(n) for n in ['A_early_custodied_by_C.json', 'C_receipt.json',
                                  'A_final.json', 'B_final.json']]
    outcomes = []
    mutations = [
        ('replace_early_record_with_future_bits',
         lambda e,c,a,b: a.update(early_bits=b['bits']), 'FINAL_DIFFERS_FROM_C_EARLY_SNAPSHOT'),
        ('remove_one_sender_slot', lambda e,c,a,b: b['bits'].pop(), 'COMPLETE_BINARY_SAMPLE_REQUIRED'),
        ('retain_only_matching_slots',
         lambda e,c,a,b: a.update(selected_slots=[i for i in range(N) if e['bits'][i]==b['bits'][i]]),
         'POSTSELECTION_FORBIDDEN'),
        ('forge_A_reply_clock',
         lambda e,c,a,b: a.update(receive_reply_ns=a['query_ns']-1),
         'FORWARD_CONTROL_CAUSAL_ORDER_FAILED'),
        ('substitute_other_batch', lambda e,c,a,b: b.update(batch_id='other'), 'BATCH_ID_MISMATCH')]
    for name, mutate, expected in mutations:
        data = copy.deepcopy(originals)
        mutate(*data)
        try:
            audit(*data)
        except ValueError as error:
            assert str(error) == expected, (name, str(error))
            outcomes.append({'control': name, 'rejected': True, 'reason': str(error)})
        else:
            raise AssertionError('Control was not rejected: ' + name)

    # Omniscient oracle writes every copy consistently: data coherence alone
    # cannot prove physical independence. This synthetic fixture MUST NOT
    # acquire physical-proof status even with 2048/2048 early matches.
    e,c,a,b = copy.deepcopy(originals)
    e['bits'] = b['bits'][:]
    a['early_bits'] = b['bits'][:]
    e['commitment'] = digest_early(e)
    c['commitment'] = a['query_commitment'] = b['query_commitment'] = e['commitment']
    oracle_report = audit(e,c,a,b)
    assert oracle_report['early_matches'] == N
    assert oracle_report['physical_backsignaling'] == 'NOT_TESTED'
    outcomes.append({'control': 'omniscient_future_oracle',
                     'early_matches': N, 'physical_proof_status_rejected': True,
                     'reason': 'SYNTHETIC_SHARED_FUTURE_DATA_NOT_A_PHYSICAL_CHANNEL'})
    trace = {'query_A':1, 'receive_B':2, 'choose_B':3, 'send_B':4,
             'reply_A':0, 'chosen_bit':1, 'received_bit':1}
    inspection = inspect_abstract_trace(trace)
    assert inspection['A_receives_before_its_query'] and not inspection['reply_forward']
    save(output / 'assumed_backchannel_fixture.json', {'trace':trace,'C_inspection':inspection})
    save(output / 'controls.json', outcomes)
    return outcomes

def main():
    output = Path(__file__).resolve().parent / 'evidence/three-observer'
    output.mkdir(parents=True, exist_ok=True)
    ctx = mp.get_context('spawn')
    left, right = ctx.Pipe()
    observations, ack = ctx.Queue(), ctx.Queue()
    processes = [ctx.Process(target=observer_c,args=(observations,ack,output),name='C'),
                 ctx.Process(target=endpoint_b,args=(right,observations),name='B'),
                 ctx.Process(target=endpoint_a,args=(left,observations,ack),name='A')]
    try:
        for process in processes:
            process.start()
        for process in processes:
            process.join(30)
            if process.is_alive() or process.exitcode != 0:
                raise RuntimeError(f'{process.name} failed or timed out: {process.exitcode}')
    finally:
        for process in processes:
            if process.is_alive():
                process.terminate(); process.join(5)
        left.close(); right.close()
    outcomes = controls(output)
    report = json.loads((output / 'C_audit.json').read_text())
    report['controls_passed'] = len(outcomes)
    report['assumed_reverse_channel'] = 'REPRESENTABLE_BUT_NOT_PHYSICALLY_REALIZED'
    save(output / 'summary.json', report)
    print(json.dumps(report, indent=2))

if __name__ == '__main__':
    main()

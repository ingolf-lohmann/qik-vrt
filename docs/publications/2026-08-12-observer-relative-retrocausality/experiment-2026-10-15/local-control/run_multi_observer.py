"""Extend the actual local control to 4/8 transceivers plus independent C.
All transport is an ordinary forward pipe; C holds the early record and audits.
Includes separate simulated reordering fixtures, never labelled measurements.
"""
import copy
import hashlib
import json
import math
import multiprocessing as mp
import os
from pathlib import Path
import secrets
import time
from audit_three_observer import digest_early, require
from run_three_observer import bits, save, N

def message_hash(message):
    return hashlib.sha256(json.dumps(message, sort_keys=True, separators=(',', ':')).encode()).hexdigest()

def xor(left, right):
    return [a ^ b for a, b in zip(left, right)]

def peer(role, incoming, outgoing, observations, ack):
    if role == 'A':
        early = {'role':'A', 'pid':os.getpid(), 'n':N, 'batch_id':secrets.token_hex(32),
                 'salt':secrets.token_hex(32), 'bits':bits(), 'time_ns':time.monotonic_ns()}
        early['commitment'] = digest_early(early)
        observations.put(('EARLY', early))
        receipt = ack.get(timeout=20)
        require(receipt['commitment']==early['commitment'], 'C_RECEIPT_MISMATCH')
        contribution = bits()
        choice_ns = time.monotonic_ns()
        message = {'batch_id':early['batch_id'], 'commitment':early['commitment'],
                   'bits':contribution}
        send_ns = time.monotonic_ns()
        outgoing.send(message)
        require(incoming.poll(20), 'RING_REPLY_MISSING')
        reply = incoming.recv()
        receive_ns = time.monotonic_ns()
        record = {'role':role, 'pid':os.getpid(), 'early_bits':early['bits'],
                  'choice_ns':choice_ns, 'send_ns':send_ns, 'receive_ns':receive_ns,
                  'contribution':contribution, 'sent':message, 'received':reply,
                  'selected_slots':list(range(N))}
    else:
        require(incoming.poll(20), 'RING_QUERY_MISSING')
        message = incoming.recv()
        receive_ns = time.monotonic_ns()
        contribution = bits()
        choice_ns = time.monotonic_ns()
        reply = {**message, 'bits':xor(message['bits'], contribution)}
        send_ns = time.monotonic_ns()
        outgoing.send(reply)
        record = {'role':role, 'pid':os.getpid(), 'receive_ns':receive_ns,
                  'choice_ns':choice_ns, 'send_ns':send_ns,
                  'contribution':contribution, 'received':message, 'sent':reply}
    observations.put(('PEER', record))
    incoming.close(); outgoing.close()

def audit_ring(roles, early, receipt, records):
    require(set(records)==set(roles), 'COMPLETE_ACTOR_SET_REQUIRED')
    require(len({r['pid'] for r in records.values()} | {receipt['pid']})==len(roles)+1,
            'DISTINCT_OBSERVER_AND_PEERS_REQUIRED')
    a = records['A']
    require(a['pid']==early['pid'], 'A_IDENTITY_CHANGED')
    require(a['early_bits']==early['bits'], 'C_CUSTODY_MISMATCH')
    require(a['selected_slots']==list(range(N)), 'POSTSELECTION_FORBIDDEN')
    require(early['commitment']==receipt['commitment']==digest_early(early), 'COMMITMENT_INVALID')
    require(early['time_ns'] < receipt['time_ns'] < a['choice_ns'] < a['send_ns'],
            'EARLY_CUSTODY_BARRIER_FAILED')
    for role in roles:
        r = records[role]
        require(len(r['contribution'])==N and all(type(b)is int and b in (0,1) for b in r['contribution']),
                'COMPLETE_BINARY_CONTRIBUTION_REQUIRED')
        for key in ['received','sent']:
            m = r[key]
            require(m['batch_id']==early['batch_id'] and m['commitment']==early['commitment'],
                    'MESSAGE_IDENTITY_MISMATCH')
            require(len(m['bits'])==N and all(type(b)is int and b in (0,1) for b in m['bits']),
                    'COMPLETE_BINARY_MESSAGE_REQUIRED')
        if role != 'A':
            require(r['receive_ns'] < r['choice_ns'] < r['send_ns'], 'LOCAL_PEER_ORDER_FAILED')
            require(r['sent']['bits']==xor(r['received']['bits'], r['contribution']), 'XOR_TRANSFORM_FAILED')
    require(a['sent']['bits']==a['contribution'], 'A_START_CONTENT_MISMATCH')
    edges = []
    for index, sender in enumerate(roles):
        receiver = roles[(index+1)%len(roles)]
        s,r = records[sender],records[receiver]
        require(s['send_ns'] < r['receive_ns'], 'FORWARD_EDGE_ORDER_FAILED')
        require(message_hash(s['sent'])==message_hash(r['received']), 'EDGE_CONTENT_BINDING_FAILED')
        edges.append({'sender':sender,'receiver':receiver,'send_ns':s['send_ns'],
                      'receive_ns':r['receive_ns'],'message_sha256':message_hash(s['sent'])})
    aggregate = [0]*N
    for role in roles:
        aggregate = xor(aggregate, records[role]['contribution'])
    require(a['received']['bits']==aggregate, 'RING_AGGREGATE_MISMATCH')
    matches = sum(x==y for x,y in zip(early['bits'],aggregate))
    p = sum(math.comb(N,k) for k in range(matches,N+1))/(1<<N)
    return {'status':'PASS_BOUNDED_FORWARD_SOFTWARE_CONTROL','transceivers':len(roles),
            'observer':'C','n':N,'early_matches':matches,'ordinary_reply_matches':N,
            'one_sided_binomial_p_under_iid_fair_null':p,
            'A_receive_after_A_send':a['receive_ns']>a['send_ns'],
            'A_round_trip_ns':a['receive_ns']-a['send_ns'],'edges':edges,
            'physical_backsignaling':'NOT_TESTED','clock':'ONE_HOST_MONOTONIC_NS',
            'process_pids':{**{r:records[r]['pid'] for r in roles},'C':receipt['pid']},
            'independence':'SHARED_HOST_AND_TRUSTED_SOFTWARE_LIMITATION'}

def observer(roles, observations, ack, output):
    records = {}
    early = receipt = None
    while len(records)<len(roles) or early is None:
        kind, item = observations.get(timeout=25)
        if kind == 'EARLY':
            require(early is None,'DUPLICATE_EARLY_RECORD')
            early = item
            receipt = {'pid':os.getpid(),'time_ns':time.monotonic_ns(),'commitment':item['commitment']}
            ack.put(receipt)
        else:
            require(item['role'] not in records,'DUPLICATE_PEER_RECORD')
            records[item['role']] = item
    report = audit_ring(roles,early,receipt,records)
    save(output/'C_custody_and_peer_records.json',{'roles':roles,'early':early,'receipt':receipt,'records':records})
    save(output/'C_audit.json',report)

def run(roles):
    output = Path(__file__).resolve().parent/'evidence'/f'{len(roles)}-transceivers'
    output.mkdir(parents=True,exist_ok=True)
    ctx = mp.get_context('spawn')
    links = [ctx.Pipe(duplex=False) for _ in roles]
    observations,ack = ctx.Queue(),ctx.Queue()
    processes = [ctx.Process(target=observer,args=(roles,observations,ack,output),name='C')]
    for i,role in enumerate(roles):
        processes.append(ctx.Process(target=peer,args=(role,links[(i-1)%len(roles)][0],
                         links[i][1],observations,ack),name=role))
    try:
        for process in processes: process.start()
        for process in processes:
            process.join(35)
            require(not process.is_alive() and process.exitcode==0, f'PROCESS_FAILED_{process.name}')
    finally:
        for process in processes:
            if process.is_alive(): process.terminate();process.join(5)
        for ends in links:
            for end in ends: end.close()
    bundle=json.loads((output/'C_custody_and_peer_records.json').read_text())
    controls=[]
    for name in ['clock','omit_peer','change_payload','postselection']:
        b=copy.deepcopy(bundle); r=b['records']
        expected={'clock':'FORWARD_EDGE_ORDER_FAILED','omit_peer':'COMPLETE_ACTOR_SET_REQUIRED',
                  'change_payload':'XOR_TRANSFORM_FAILED','postselection':'POSTSELECTION_FORBIDDEN'}[name]
        if name=='clock': r['A']['receive_ns']=r['A']['send_ns']-1
        if name=='omit_peer': del r[roles[-1]]
        if name=='change_payload': r[roles[1]]['sent']['bits'][0]^=1
        if name=='postselection': r['A']['selected_slots']=[]
        try: audit_ring(roles,b['early'],b['receipt'],r)
        except ValueError as error:
            require(str(error)==expected, 'WRONG_CONTROL_FAILURE_'+str(error))
            controls.append({'control':name,'rejected':True,'reason':str(error)})
        else: raise AssertionError('Failed to reject '+name)
    save(output/'controls.json',controls)
    # Positive delays can invert every source mark without receive-before-send.
    k=len(roles)
    reorder=[{'source_mark':i,'send_label':i,'receive_label':3*k-i,
              'positive_delay':3*k-2*i} for i in range(k)]
    arrival_order=sorted(reorder,key=lambda m:m['receive_label'])
    require([m['source_mark'] for m in arrival_order]==list(reversed(range(k))), 'REORDER_FIXTURE_FAILED')
    save(output/'reordering_fixture_SIMULATED.json',{'origin':'SIMULATED_POSITIVE_DELAYS',
         'messages':reorder,'arrival_source_order':[m['source_mark'] for m in arrival_order],
         'receive_before_own_send':False,'physical_measurement':False})
    report=json.loads((output/'C_audit.json').read_text());report['controls_passed']=len(controls)
    report['simulated_reordering_messages']=k
    save(output/'summary.json',report)
    return report

if __name__=='__main__':
    results=[run(roles) for roles in [['A','B','D','E'],['A','B','D','E','F','G','H','I']]]
    print(json.dumps([{key:r[key] for key in ['transceivers','observer','n','early_matches',
          'ordinary_reply_matches','A_receive_after_A_send','controls_passed','physical_backsignaling']}
          for r in results],indent=2))

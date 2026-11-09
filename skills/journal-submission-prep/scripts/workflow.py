"""Local manuscript facts and policy snapshot comparisons. No network or global memory."""
from copy import deepcopy
import json


def signature(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False)


def consolidate(observations, previous=None):
    previous = previous or {}
    manuscript = observations.get('manuscript_id')
    if not isinstance(manuscript, str) or not manuscript.strip():
        raise ValueError('A stable manuscript_id is required')
    if previous and previous.get('manuscript_id') != manuscript:
        raise ValueError('Cannot reuse facts from a different manuscript')
    sources = {s['id']: deepcopy(s) for s in previous.get('sources', [])}
    for source in observations.get('sources', []):
        if source.get('kind') not in {'document', 'author_confirmation', 'system_snapshot'} or not source.get('locator') or not source.get('evidence'):
            raise ValueError('Fact source needs kind, locator and evidence')
        if source['id'] in sources and sources[source['id']] != source:
            raise ValueError('Source IDs are immutable; use a new ID')
        sources[source['id']] = deepcopy(source)
    facts = {f['key']: deepcopy(f) for f in previous.get('facts', [])}
    seen = set()
    for observation in observations.get('facts', []):
        item = deepcopy(observation); key = item['key']
        if key in seen:
            raise ValueError('Consolidate duplicate keys into one observation with alternatives')
        seen.add(key)
        if item.get('status') not in {'observed', 'confirmed', 'missing', 'conflicting', 'not_applicable'}:
            raise ValueError('Invalid fact status')
        for flag in ('required', 'blocking'):
            if flag in item and type(item[flag]) is not bool:
                raise ValueError('Fact flags must be boolean')
        ids = item.get('source_ids', [])
        if any(s not in sources for s in ids) or (item['status'] != 'missing' and not ids):
            raise ValueError('Known facts require known evidence sources')
        if item['status'] in {'confirmed', 'not_applicable'} and not any(sources[s]['kind'] == 'author_confirmation' for s in ids):
            raise ValueError('Confirmed declarations need author confirmation evidence')
        if item['status'] in {'observed', 'confirmed', 'not_applicable'} and 'value' not in item:
            raise ValueError('Known fact needs a value')
        old = facts.get(key)
        if old:
            item['history'] = deepcopy(old.get('history', []))
            same_value = 'value' in item and 'value' in old and signature(item['value']) == signature(old['value'])
            if old['status'] == 'conflicting' and not (item['status'] in {'confirmed', 'not_applicable'} and item.get('supersedes') is True):
                item = {**item, 'status': 'conflicting', 'alternatives': old.get('alternatives', []),
                        'source_ids': list(dict.fromkeys(old.get('source_ids', []) + ids))}
            if item['status'] == 'missing' or (same_value and old['status'] in {'confirmed', 'not_applicable'}):
                merged = deepcopy(old)
                for flag in ('required', 'blocking', 'question'):
                    if flag in item: merged[flag] = item[flag]
                merged['source_ids'] = list(dict.fromkeys(old.get('source_ids', []) + ids))
                facts[key] = merged
                continue
            if not same_value and 'value' in old and 'value' in item:
                if item['status'] in {'confirmed', 'not_applicable'} and item.get('supersedes') is True:
                    item['history'].append({k: v for k, v in old.items() if k != 'history'})
                else:
                    item['status'] = 'conflicting'
                    item['alternatives'] = [old['value'], item['value']]
                    item['source_ids'] = list(dict.fromkeys(old.get('source_ids', []) + ids))
        item.pop('supersedes', None)
        facts[key] = item
    pending, new = [], []
    for fact in facts.values():
        if fact.get('required') and fact['status'] in {'missing', 'conflicting', 'observed'}:
            if not fact.get('question'):
                raise ValueError('Required unresolved fact needs an author question')
            fingerprint = signature([fact['status'], fact.get('value'), fact.get('alternatives'), fact.get('source_ids', [])])
            question = {'key': fact['key'], 'question': fact['question'], 'proposed_text': fact.get('proposed_text'),
                        'source_ids': fact.get('source_ids', []), 'blocking': fact.get('blocking', False)}
            pending.append(question)
            if fact.get('asked_fingerprint') != fingerprint:
                new.append(question)
                fact['asked_fingerprint'] = fingerprint
    registry = {'manuscript_id': manuscript, 'sources': list(sources.values()), 'facts': list(facts.values())}
    questions = {'manuscript_id': manuscript, 'new_questions': new, 'pending_questions': pending,
                 'blocking_keys': [q['key'] for q in pending if q['blocking']],
                 'instruction': 'Present new questions in one batch; unresolved items stay pending, never infer approval from silence.'}
    return registry, questions


def compare_profiles(old, new):
    before = {r['id']: r for r in old['rules']}; after = {r['id']: r for r in new['rules']}
    changed = [{'id': key, 'before': before[key], 'after': after[key]} for key in before.keys() & after.keys()
               if before[key] != after[key]]
    return {'before': {k: old[k] for k in ('journal', 'article_type', 'stage', 'checked_on')},
            'after': {k: new[k] for k in ('journal', 'article_type', 'stage', 'checked_on')},
            'added': [after[k] for k in sorted(after.keys() - before.keys())],
            'removed': [before[k] for k in sorted(before.keys() - after.keys())],
            'changed': sorted(changed, key=lambda r: r['id']),
            'source_snapshot_changed': old['sources'] != new['sources'],
            'limitations': 'ID-based review aid; changed rule IDs require semantic matching by the agent. Does not verify current policy.'}

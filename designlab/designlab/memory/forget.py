"""Deletion that propagates, and a restore that does not resurrect.

`naive_forget` deletes the tenant's own records, which is what a
"delete where customer_id = X" does. `forget` also follows
derived_from links, to any depth and across tenants: a note on a
companion's record that was made from this customer's memory is this
customer's data too. Every deletion leaves a tombstone.

`restore` loads a backup taken before the deletion. With
`replay=True` it applies the tombstones written since the backup
before any read, so a deleted memory does not come back.
"""
from __future__ import annotations

from dataclasses import replace


def naive_forget(store, tenant: str, reason: str = "erasure") -> list:
    ids = [r.memory_id for r in store.records.values()
           if r.tenant == tenant and r.status != "deleted"]
    for i in ids:
        store.delete(i, reason)
    return ids


def _derived_closure(store, seeds: set) -> set:
    out = set(seeds)
    grew = True
    while grew:
        grew = False
        for r in store.records.values():
            if r.memory_id in out or r.status == "deleted":
                continue
            if set(r.derived_from) & out:
                out.add(r.memory_id)
                grew = True
    return out


def forget(store, tenant: str, reason: str = "erasure") -> list:
    seeds = {r.memory_id for r in store.records.values()
             if r.tenant == tenant}
    targets = _derived_closure(store, seeds)
    done = []
    for i in sorted(targets):
        if store.records[i].status != "deleted":
            store.delete(i, reason)
            done.append(i)
    return done


def remaining(store, tenant: str) -> list:
    """Live records that are the tenant's or were made from them."""
    gone = {r.memory_id for r in store.records.values()
            if r.tenant == tenant}
    closure = _derived_closure(store, gone)
    return sorted(i for i in closure
                  if store.records[i].status != "deleted")


def snapshot(store) -> dict:
    return {"records": dict(store.records), "heads": dict(store.heads),
            "stones": len(store.tombstones)}


def restore(store, snap: dict, replay: bool = True) -> list:
    """Restore a snapshot; return ids that came back from the dead."""
    stones = store.tombstones[snap["stones"]:]
    store.records = dict(snap["records"])
    store.heads = dict(snap["heads"])
    if replay:
        for s in stones:
            r = store.records.get(s["memory"])
            if r is not None and r.status != "deleted":
                store.records[r.memory_id] = replace(r, status="deleted",
                                                     value="")
                for k, v in list(store.heads.items()):
                    if v == r.memory_id:
                        del store.heads[k]
    erased = {s["memory"] for s in store.tombstones}
    return sorted(i for i in erased
                  if i in store.records
                  and store.records[i].status != "deleted")

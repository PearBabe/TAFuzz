# Schema2 frontier scaling analysis

The immutable schema2 analyzer successfully completed indexing, model overlay,
predicate-occurrence binding, contextual graph construction, and all four AP
influence cones for the unchanged 38-TU libcoap input. It exhausted the 12 GiB
address-space limit before `frontier-staged`:

```text
wall_seconds=338.81
peak_rss_kib=12211308
last trace=cones-staged (1479584 KiB RSS)
terminal error=std::bad_alloc
```

Equivalent staged inputs retained from the preceding immutable diagnostic have
136,509 contextual nodes, 405,759 contextual edges, four cones with 202,524
members in total, 24 external actions, and 24 boundary attachments. The
inputs, graph, and cone sizes are identical across the diagnostic and schema2
runs.

The cone cardinalities are independently counted from the staged JSON:

```text
coap_con_wait_started                   51,024 members
coap_first_retransmit_deadline_reached  50,732 members
coap_matching_ack_or_reset_received     50,170 members
coap_attempt_cancelled                  50,598 members
```

Read-only source inspection localizes the scaling problem to the generic
frontier construction. `compute_frontier_candidates` iterates over every
action/cone pair. For each attachment contextual instance it recomputes a
forward closure, intersects that closure with every cone member, and passes
the complete intersection to `build_witness`. The union witness still stores
one `FrontierMeetAccount` per reached cone member plus complete forward-node
and forward-edge ID unions. It therefore removes per-meet witness objects but
does not remove the dominant action × cone × intersection materialization.

This finding is project-independent: the pressure follows artifact cardinality
and the frontier representation, not a libcoap name or hand-authored property
edge. Plausible generic remedies are to cache forward closure per unique
attachment-context key and to use a deduplicated/streamed witness ledger or a
digest-count-exemplar proof summary whose full membership is reproducible from
the certified graph and cone. Any representation change requires its own
schema version and verifier coverage.

No occurrence, frontier, recipe, actionability, or accuracy claim is made from
this failed atomic run. The detached verifier correctly reports `FAIL` because
there is no M5 certificate.

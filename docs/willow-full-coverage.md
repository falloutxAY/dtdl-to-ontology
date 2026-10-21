# Full Willow corpus coverage

The pinned Willow `Ontology` fixture at revision
`1d19b2584df02e05714628a57a7ddd69edeef29c` was loaded with all file
fingerprints verified and evaluated as a single complete converter selection.
This is an exhaustive **local compiler and compatibility sweep** of the 3,705
interfaces, not a claim that every interface was individually deployed or tested
in Fabric.

## Results

| Sweep | Result |
| --- | --- |
| Fixture loading | 3,705 interfaces; all pinned fingerprints match; no loader findings |
| Strict full-corpus planning | All 3,705 selected; 3,705 entity plans; 14,744 relationships; blocked |
| Strict full-item limits | 14,744 relationships exceed the 10,000 profile limit; 1,432,050 logical document nodes exceed the 1,000,000 local limit |
| All named loss policies approved | Still blocked: 25,297 findings; 3,690 interfaces have model-owned blocking findings; 15 have none |
| All-policy projected item limits | 3,723 entities and 14,780 relationships; relationships exceed the 10,000 per-item limit |
| Remaining source blockers | Missing `LeaseContract` target and the `WaterLeakEvent` annotation target mismatch |

The all-policy sweep enabled every declared compatibility policy for analysis;
it is **not** an approved production mapping. In particular, it does not waive
unbound relationship acceptance, untargeted relationships, missing targets,
invalid annotations or target capacity. Relationship-instance reification adds
edge entities and endpoint relationships, so its all-policy relationship total
is greater than the strict total.

Every interface was planned in the full-catalog selection. Per-interface rows in
the generated coverage CSV describe findings owned by that interface; they are
not isolated conversion results because a model may depend on other interfaces.
Global document/item limits are reported separately. No row should be read as
proof of service acceptance.

## Live Fabric evidence

The accepted bounded Building projection is the live service probe for the
representative subset: 10 types, 79 properties and 15 definition parts. It
includes explicit JSON-string projections for complex values and omissions for
22 relationships. A subsequent CLI run in the supplied Fabric test folder
created an Ontology, completed its regional long-running operation and retrieved
all 15 expected part paths. Semantic equivalence for that CLI run was not asserted.
Address has separate create/get-definition and UI acceptance evidence.

These are bounded probes, not per-interface probes. Unbound relationships and
native unbound complex structs remain unverified or rejected, respectively;
runtime ingestion, source constraints, units and device behavior were not tested.
The full source contains no `Telemetry` or `Command` declarations, so this corpus
cannot provide coverage evidence for those features.

## Reproduce and inspect

Acquire the pinned fixture with `python tools\fetch_willow.py .fixtures\willow`,
then run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_willow.py -q
```

The two full-corpus regression tests verify both strict planning and a sweep with
all named loss policies, including non-waivable findings and target-limit
measurements. Detailed, ignored local artifacts from the executed sweep are in
`output\willow-full-coverage-20261021\`: `coverage-summary.json` provides one
record per interface, `model-coverage.csv` is convenient for filtering, and the
strict/all-policy report JSON files contain full diagnostics. The fixture and
generated reports are not committed.

The current issue tracker records the remaining relationship, struct/component,
inheritance, metadata/runtime and scale gaps with `gap` and/or `workaround`
labels. The source defects are separately recorded as workarounds. See
[known gaps](known-gaps.md) and the
[live Fabric acceptance record](fabric-acceptance.md).

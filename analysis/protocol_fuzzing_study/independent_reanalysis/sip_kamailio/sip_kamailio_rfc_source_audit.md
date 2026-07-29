# SIP/Kamailio RFC and source audit

This audit is independent of the historical SIP catalog in this workspace.

## Evidence manifest summary

| ID | Source | SHA-256 | Access date |
|---|---|---:|---|
| RFC3261 | [rfc3261.txt](https://www.rfc-editor.org/rfc/rfc3261.txt) | `d513777f77fea01a4de9c0a2d9d6713cb53b8231f1b7a2ab56705f8d51b066dc` | 2026-07-13 |
| RFC6026 | [rfc6026.txt](https://www.rfc-editor.org/rfc/rfc6026.txt) | `4f81ec1638278f19b48a6976981c4aeb003ba5667ad2f944a96819be017b4ab9` | 2026-07-13 |
| RFC3261 errata | [rfc3261_errata.html](https://www.rfc-editor.org/errata/rfc3261) | `288ed47f43844f8911d009a9ef8388a5f4db5e916b43026049c169c3f33a6ccb` | 2026-07-13 |
| RFC6026 errata | [rfc6026_errata.html](https://www.rfc-editor.org/errata/rfc6026) | `7ec4a5e83e9c04e586bf235402f296773985a19c6ced1205ff155d834c466a27` | 2026-07-13 |
| Kamailio commit JSON | [kamailio_2648eb330b_commit.json](https://api.github.com/repos/kamailio/kamailio/commits/2648eb330b133a20f1398d59a28c53532106cad3) | `8d1a0d43b3b033f45d1162c42987b1198d726cdc2004bca37101de1639cef84d` | 2026-07-13 |
| Kamailio tarball | [kamailio_2648eb330b.tar.gz](https://github.com/kamailio/kamailio/archive/2648eb330b133a20f1398d59a28c53532106cad3.tar.gz) | `fc8c6b9d421cb9d500cf18aed44e053f85b49d468ed5268d874aab7e6afee919` | 2026-07-13 |
| ProfuzzBench Dockerfile | [Dockerfile](https://github.com/profuzzbench/profuzzbench/blob/8573ec81d68f2c1ffc8f5e605dfdd9c61fbeb074/subjects/SIP/Kamailio/Dockerfile) | `e48f21e34caad78f3e1aa2497cecf93d65d93805937c71d455c805ee4434e0dd` | 2026-07-13 |
| ProfuzzBench StateAFL Dockerfile | [Dockerfile-stateafl](https://github.com/profuzzbench/profuzzbench/blob/8573ec81d68f2c1ffc8f5e605dfdd9c61fbeb074/subjects/SIP/Kamailio/Dockerfile-stateafl) | `d9675c4dde25644d2723cf6215a91727fa672135f23b3f50b9c42c2b6b1b912e` | 2026-07-13 |
| ProfuzzBench README | [README.md](https://github.com/profuzzbench/profuzzbench/blob/8573ec81d68f2c1ffc8f5e605dfdd9c61fbeb074/subjects/SIP/Kamailio/README.md) | `fec461ccc9a3483522d83fc702458938193ffa9ea499637412c7eeee2e3fdd35` | 2026-07-13 |
| ProfuzzBench Kamailio patch | [kamailio.patch](https://github.com/profuzzbench/profuzzbench/blob/8573ec81d68f2c1ffc8f5e605dfdd9c61fbeb074/subjects/SIP/Kamailio/kamailio.patch) | `938137f182b5c2bc33e6dc081950f0ded5b0a3d23f8c82b3bbaa43be7ead5258` | 2026-07-13 |
| ProfuzzBench run.sh | [run.sh](https://github.com/profuzzbench/profuzzbench/blob/8573ec81d68f2c1ffc8f5e605dfdd9c61fbeb074/subjects/SIP/Kamailio/run.sh) | `4ec2e92b923f8fabfcd6925cb64c930fd8caac8156eb9dd917dae20cb3736fcb` | 2026-07-13 |
| ProfuzzBench run-stateafl.sh | [run-stateafl.sh](https://github.com/profuzzbench/profuzzbench/blob/8573ec81d68f2c1ffc8f5e605dfdd9c61fbeb074/subjects/SIP/Kamailio/run-stateafl.sh) | `4fe4361c08b8fe17834f1953efc21ae69c445f34049e3b0b82e217e4cf8c0a37` | 2026-07-13 |
| ProfuzzBench cov_script.sh | [cov_script.sh](https://github.com/profuzzbench/profuzzbench/blob/8573ec81d68f2c1ffc8f5e605dfdd9c61fbeb074/subjects/SIP/Kamailio/cov_script.sh) | `9b3394c79fe07cdfbc2e32f3649656610090c27a214cf34d28beb22cee28b571` | 2026-07-13 |
| ProfuzzBench run_pjsip.sh | [run_pjsip.sh](https://github.com/profuzzbench/profuzzbench/blob/8573ec81d68f2c1ffc8f5e605dfdd9c61fbeb074/subjects/SIP/Kamailio/run_pjsip.sh) | `296a237d03c4e4ea20a910423676a71667d70400eff041b3f84c2eeb650cd993` | 2026-07-13 |
| ProfuzzBench kamailio-basic.cfg | [kamailio-basic.cfg](https://github.com/profuzzbench/profuzzbench/blob/8573ec81d68f2c1ffc8f5e605dfdd9c61fbeb074/subjects/SIP/Kamailio/kamailio-basic.cfg) | `289483efdf34cc1bd612a9863417b16d39da524430722290d9c520cbe5eed309` | 2026-07-13 |

## Fixed implementation and benchmark facts

- Kamailio source commit: `2648eb330b133a20f1398d59a28c53532106cad3` ([GitHub commit](https://github.com/kamailio/kamailio/commit/2648eb330b133a20f1398d59a28c53532106cad3)).
- ProfuzzBench source commit: `8573ec81d68f2c1ffc8f5e605dfdd9c61fbeb074`.
- ProfuzzBench SIP/Kamailio Dockerfile pins Kamailio with `git checkout 2648eb3` and builds AFLNet/AFLnwe plus a gcov build.
- ProfuzzBench StateAFL Dockerfile creates a second Kamailio build for StateAFL adaptation.
- `kamailio.patch` disables the normal timer and slow-timer child processes and fixes the PRNG seed. Therefore timer callback properties need a reference build or profile caveat; this catalog does not pretend the patched campaign can observe every timer expiry.

## RFC sections used

- RFC3261 §17.2.1 INVITE server transaction: Proceeding/Completed/Confirmed, 100 Trying, retransmission, Timer H/I.
- RFC3261 §17.2.2 non-INVITE server transaction: Trying/Proceeding/Completed, Timer J and retransmission behavior.
- RFC3261 §17.2.3 transaction matching: magic-cookie branch, sent-by, method exception for ACK.
- RFC3261 §9.2 CANCEL server behavior.
- RFC3261 §16.7 and §16.10 stateful proxy response/CANCEL behavior.
- RFC6026 §7.1/§8.7 Accepted state and Timer L update for INVITE 2xx.

## Source mapping principle

APs are observable event predicates, not raw C variables.  Hooks are placed after protocol facts are committed: parse success, transaction creation/match, successful timer arm/cancel, and actual send-path success.

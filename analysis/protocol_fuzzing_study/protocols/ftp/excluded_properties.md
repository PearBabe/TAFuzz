# FTP 排除与待修候选

## 研究阶段排除：_staging/ietf_app_protocols/ftp/excluded.md

# FTP excluded candidates

## Result

RFC 959 and the FTP requirements in RFC 1123 were screened for numeric
greeting, reply, wait, idle, and connection timers.  The only fixed FTP timer
floor is RFC 1123 §4.1.3.2's default idle timeout of at least five minutes.
The locked `hfiref0x/LightFTP@5980ea1a0ee0e5c3015275f93445626f8c25c83a`
server has no corresponding timer or configuration field.  No proposal, AP
alphabet, formula, or positive/negative timed word was emitted.

## Exhaustive numeric-timing screening

- `FTP-IDLE-300` — RFC 1123 §4.1.3.2 says a Server-FTP SHOULD have a
  configurable idle timeout whose default is at least 5 minutes.  LightFTP's
  [`FTP_CONFIG`](https://github.com/hfiref0x/LightFTP/blob/5980ea1a0ee0e5c3015275f93445626f8c25c83a/Source/ftpserv.h#L36-L45)
  has no idle-timeout field; [`main`](https://github.com/hfiref0x/LightFTP/blob/5980ea1a0ee0e5c3015275f93445626f8c25c83a/Source/main.c#L91-L128)
  parses no such setting; and
  [`recvcmd`](https://github.com/hfiref0x/LightFTP/blob/5980ea1a0ee0e5c3015275f93445626f8c25c83a/Source/ftpserv.c#L1822-L1854)
  blocks in `recv`/`gnutls_record_recv` without an idle deadline.  The control
  loop closes only after receive or command termination at
  [`ftpserv.c:1913-1969`](https://github.com/hfiref0x/LightFTP/blob/5980ea1a0ee0e5c3015275f93445626f8c25c83a/Source/ftpserv.c#L1913-L1969).
  Rejected: `NO_FIXED_SOURCE_MAP`.

- `FTP-CLIENT-RESPONSE-TIMEOUT` — RFC 1123 §4.1.3.2 says a program-invoked
  User-FTP needs response timeouts, but supplies no value.  The locked target
  is a server and contains no User-FTP response-timer path.  Rejected:
  `NO_NUMERIC_BOUND`, `NO_FIXED_SOURCE_MAP`.

- `FTP-120-DYNAMIC` — RFC 959 §§4.2 and 5.4 define reply 120 as service ready
  in `nnn` minutes.  `nnn` is dynamic and has no standard default.  LightFTP's
  [reply table](https://github.com/hfiref0x/LightFTP/blob/5980ea1a0ee0e5c3015275f93445626f8c25c83a/Source/ftpserv.h#L149-L196)
  contains an immediate 220 greeting and no 120 path.  Rejected:
  `NO_NUMERIC_BOUND`, `NO_FIXED_SOURCE_MAP`.

- `FTP-PROMPT-REPLY` — RFC 959 §5.4 requires an alternating command/reply
  dialogue and calls the primary reply prompt, but gives no elapsed-time
  endpoint.  The fixed dispatch loop at
  [`ftpserv.c:1913-1953`](https://github.com/hfiref0x/LightFTP/blob/5980ea1a0ee0e5c3015275f93445626f8c25c83a/Source/ftpserv.c#L1913-L1953)
  therefore cannot supply a standard-derived deadline.  Rejected:
  `NO_NUMERIC_BOUND`.

- `FTP-TEMPORARY-FAILURE-HOURS` — RFC 1123 §4.1.2.11 uses “a few hours
  later” only to guide 4xx versus 5xx classification.  It defines neither a
  numeric interval nor a timed transition.  Rejected: `NO_NUMERIC_BOUND`,
  `FORMULA_UNSUPPORTED`.

## Safety and execution note

This was a document/source audit only.  No LightFTP service was built or
started, no FTP command was sent, and no formula or trace was executed.


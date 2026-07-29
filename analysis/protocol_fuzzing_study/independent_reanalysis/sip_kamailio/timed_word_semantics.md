# Timed-word semantics for Kamailio/SIP reanalysis

- Input model: pointwise finite timed word over complete AP valuations.
- Time unit: integer milliseconds.  RFC constants are converted to ms; 64*T1 uses the RFC default T1=500 ms unless the experiment profile explicitly overrides T1.
- Same-callback protocol events are represented using a deterministic adapter microstep expansion over a small `[0,2]` ms observation window.  This is not a network tolerance and must not be used to excuse late real-time behavior.
- Dynamic SIP identifiers (`Call-ID`, `CSeq`, Via `branch`, tags, sent-by, branch index) are correlation metadata only.  They never enter AP names or the automaton alphabet.
- Adapter order: packet/timer hook -> ProtocolEvent -> correlation -> per-property projection -> complete valuation timed word -> MightyPPL/MoniTAal monitor -> PTA prefix guidance.
- Missing hook data is `UNKNOWN` in the real oracle.  The validation traces here are synthetic positive/negative examples for formula construction only.
- Punctual intervals `[a,a]` are not used in the main catalog.  Deadline-exact claims would need an MTL/MITPPL extended appendix and timestamp-uncertainty policy.

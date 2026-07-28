# DICOM excluded candidates

| Candidate | Reason code | Evidence-based reason |
|---|---|---|
| Protocol-wide numeric ARTIM value | `NO_NUMERIC_BOUND` | DICOM PS3.8 Section 9.1.5 requires ARTIM to be configurable and intentionally gives no universal number. |
| Use ARTIM to bound association establishment/release | `NO_PUBLIC_NORMATIVE_TEXT` | PS3.8 explicitly says ARTIM should not oversee Association Establishment or Release at the application layer. |
| DIMSE response timeout | `NO_NUMERIC_BOUND` | PS3.8 upper-layer state machine provides no universal DIMSE response deadline; DCMTK's DIMSE timeout is configurable/unlimited by default. |
| A-RELEASE-RP / A-ABORT post-send exact timeout | `NO_FIXED_SOURCE_MAP` | DCMTK's path uses `PRV_DEFAULTTIMEOUT=-1` in relevant reads; no stable numeric default matches a main MITL property. |
| End-of-study timeout | `NO_PUBLIC_NORMATIVE_TEXT` | DCMTK application behavior, not a DICOM Upper Layer normative timer. |

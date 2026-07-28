# 多协议 MITL 真实性质索引

主目录只统计同时通过正式规范、固定源码、非 punctual MightyPPL 构造和正反 trace oracle 的条目。

| 协议 | 候选 | 收录 | 自动拒绝 | 已记录排除 | 状态 | 目录 |
|---|---:|---:|---:|---:|---|---|
| CoAP | 7 | 7 | 0 | 14 | PASS | [coap](./coap/mitl_property_catalog.md) |
| MQTT | 3 | 3 | 0 | 14 | PASS | [mqtt](./mqtt/mitl_property_catalog.md) |
| TCP | 9 | 9 | 0 | 48 | PASS | [tcp](./tcp/mitl_property_catalog.md) |
| QUIC | 7 | 7 | 0 | 7 | PASS | [quic](./quic/mitl_property_catalog.md) |
| DNS | 0 | 0 | 0 | 15 | NO_ADMITTED_PROPERTY | [dns](./dns/mitl_property_catalog.md) |
| TLS | 1 | 0 | 1 | 8 | NO_ADMITTED_PROPERTY | [tls](./tls/mitl_property_catalog.md) |
| DTLS | 4 | 3 | 1 | 10 | PARTIAL | [dtls](./dtls/mitl_property_catalog.md) |
| SSH | 1 | 1 | 0 | 5 | PASS | [ssh](./ssh/mitl_property_catalog.md) |
| RTSP | 1 | 1 | 0 | 10 | PASS | [rtsp](./rtsp/mitl_property_catalog.md) |
| FTP | 0 | 0 | 0 | 5 | NO_ADMITTED_PROPERTY | [ftp](./ftp/mitl_property_catalog.md) |
| SMTP | 7 | 7 | 0 | 6 | PASS | [smtp](./smtp/mitl_property_catalog.md) |
| SIP | 26 | 23 | 3 | 13 | PARTIAL | [sip](./sip/mitl_property_catalog.md) |
| DICOM | 1 | 1 | 0 | 5 | PASS | [dicom](./dicom/mitl_property_catalog.md) |
| Modbus/TCP | 0 | 0 | 0 | 6 | NO_ADMITTED_PROPERTY | [modbus_tcp](./modbus_tcp/mitl_property_catalog.md) |
| OPC UA | 8 | 8 | 0 | 6 | PASS | [opc_ua](./opc_ua/mitl_property_catalog.md) |
| DDS/RTPS | 5 | 5 | 0 | 6 | PASS | [dds_rtps](./dds_rtps/mitl_property_catalog.md) |
| CAN/UDS | 5 | 5 | 0 | 5 | PASS | [can_uds](./can_uds/mitl_property_catalog.md) |

合计收录：**80** 条。所有人工审核状态仍为 `PENDING`。

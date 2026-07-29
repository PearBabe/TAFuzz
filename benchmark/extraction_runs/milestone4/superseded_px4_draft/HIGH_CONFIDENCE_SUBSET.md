# 优先人工审核的 PX4 候选

以下六条拥有相对完整的“官方文档/参数元数据—运行时参数—源码绑定—MAVLink 结果观测”链，适合作为第一批
性质工程输入。这里的“高置信”只评价证据链，不表示性质已经被验证，也不表示实现满足。

1. `PX4-MC-CAND-002`：RC/Joystick selected-source silence → `COM_RC_LOSS_T` → manual-control-loss。
   最大缺口是“selected source”不能仅由测试器发送的 `MANUAL_CONTROL` 证明。
2. `PX4-MC-CAND-003`：最后一个被接收器分类为 `MAV_TYPE_GCS` 的 `HEARTBEAT` → `COM_DL_LOSS_T` →
   GCS loss。单一受控 GCS 配置下输入起点较清晰。
3. `PX4-MC-CAND-005`：Offboard proof loss → `COM_OF_LOSS_T` → 退出 Offboard/配置动作。
   必须先解决文档中 `2 Hz`、`>2 Hz` 和 `below 2 Hz` 的边界冲突。
4. `PX4-MC-CAND-006`：连续 landed → `COM_DISARM_LAND` → disarmed。`EXTENDED_SYS_STATE` 与
   `HEARTBEAT.base_mode` 可直接黑盒观测，但 mission/config override 例外尚待规范化。
5. `PX4-MC-CAND-008`：takeoff epoch → `0.9*COM_FLT_TIME_MAX` warning / `COM_FLT_TIME_MAX` RTL。
   Return 模式可直接观测，warning 需要与固件匹配的 EVENT 元数据。
6. `PX4-MC-CAND-009`：RTL destination loiter phase → `RTL_LAND_DELAY` → Land。阶段需要组合模式、目标和位置；
   文档默认 `0.5 s` 与参数元数据默认 `0.0 s` 冲突，因此只能使用每次运行读取的 `PARAM_VALUE`。

`PX4-MC-CAND-004`（Offboard admission）规范价值很高，但冻结源码审计尚未找到可直接绑定的一秒资格状态；
在得到接受事件或内部资格探针前，不列入首批纯黑盒判定。

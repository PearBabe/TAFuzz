# PGFuzz-MTL51 当前源码词项与原子命题绑定

## 一、状态图例

- `EXACT`：精确绑定：当前实体身份和该行所写的局部语义有直接源码证据。
- `MODELLED`：建模绑定：需要坐标、单位、有效性、历史样本或上下文转换。
- `UNRESOLVED`：尚未解决：当前证据不足，不能猜测等价实体或数值。
- `DIRECT`：可由列出的 MAVLink 字段直接读取；仍须执行所写缩放或枚举解码。
- `DERIVED`：需要组合多个字段、保存历史样本或执行数学换算。
- `CONDITIONAL`：只有消息已启用且有效性、配置或运行阶段条件成立时可用。
- `INSTRUMENTATION_REQUIRED`：标准 MAVLink 不提供等价字段，需要订阅内部状态或增加插桩。
- `UNRESOLVED`：没有找到可靠的当前观测定义。
- `PRIMARY_VALUE`：主真值来源；当前原子命题选定语义组中用于判真的核心实体。
- `SUPPORTING_EVIDENCE`：辅助证据；用于证明主值的形成、发送、关联或消费路径，不是额外合取条件。
- `ALTERNATIVE_SEMANTICS`：替代语义；与主组互斥的另一种论文词项解释，保留供人工切换，不同时判真。
- `PRIMARY_SELECTED`：已选定主语义组，没有其他互斥候选。
- `PRIMARY_WITH_ALTERNATIVES`：已选定主语义组，同时保留一个或多个互斥替代组供人工审核。
- `UNRESOLVED_PRIMARY`：主语义本身证据不足，补证前不计算真值。
- `NOT_ASSESSED`：未评估实现是否满足性质；源码只用于身份、位置和观测绑定。
- `uORB`：PX4 内部发布—订阅消息总线；内部状态不一定直接出现在 MAVLink 中。
- `TRACE_PREVIOUS_SAMPLE`：由监视器保存的前一有效样本；不是源码中的独立变量，也不是一秒前。
- `data type` 中文为“数据类型”，说明源码如何存储该值；`unit/coordinate` 中文为“单位/坐标系”，说明尺度、正方向和参考面。下表保留精确源码表述；源码绑定的 100 种数据类型和 61 种单位/坐标原值，以及当前输入目录的 7 种类型和 28 种单位原值，均在 [类型与单位字典](TYPE_UNIT_DICTIONARY.md) 中逐项解释。

## 二、总量

- 词项源码绑定行：227。
- 覆盖唯一系统—词项：107。
- 原子命题出现：178。
- 所有行固定 `implementation_satisfaction=NOT_ASSESSED`。

## 三、ArduPilot 词项绑定

| 论文词项 | 当前源码实体 | 绑定角色/候选组 | 类型/单位 | 置信度 | MAVLink 可观测性 | 证据位置 |
|---|---|---|---|---|---|---|
| `Mode_t` | `Copter::flightmode->mode_number()` | `PRIMARY_VALUE` / `Mode_t:primary` | Mode::Number (uint8_t enum) | `EXACT` | `DIRECT` | `baseline/ardupilot/ArduCopter/Copter.h:388` |
| `Mode_t` | `GCS_Copter::custom_mode()` | `SUPPORTING_EVIDENCE` / `Mode_t:primary` | uint32_t | `EXACT` | `DIRECT` | `baseline/ardupilot/ArduCopter/GCS_MAVLink_Copter.cpp:62` |
| `ACRO` | `Mode::Number::ACRO` | `PRIMARY_VALUE` / `ACRO:primary` | uint8_t enum | `EXACT` | `DIRECT` | `baseline/ardupilot/ArduCopter/mode.h:79` |
| `ALT_HOLD` | `Mode::Number::ALT_HOLD` | `PRIMARY_VALUE` / `ALT_HOLD:primary` | uint8_t enum | `EXACT` | `DIRECT` | `baseline/ardupilot/ArduCopter/mode.h:80` |
| `AUTO` | `Mode::Number::AUTO` | `PRIMARY_VALUE` / `AUTO:primary` | uint8_t enum | `EXACT` | `DIRECT` | `baseline/ardupilot/ArduCopter/mode.h:81` |
| `GUIDED` | `Mode::Number::GUIDED` | `PRIMARY_VALUE` / `GUIDED:primary` | uint8_t enum | `EXACT` | `DIRECT` | `baseline/ardupilot/ArduCopter/mode.h:82` |
| `LOITER` | `Mode::Number::LOITER` | `PRIMARY_VALUE` / `LOITER:primary` | uint8_t enum | `EXACT` | `DIRECT` | `baseline/ardupilot/ArduCopter/mode.h:83` |
| `RTL` | `Mode::Number::RTL` | `PRIMARY_VALUE` / `RTL:primary` | uint8_t enum | `EXACT` | `DIRECT` | `baseline/ardupilot/ArduCopter/mode.h:84` |
| `CIRCLE` | `Mode::Number::CIRCLE` | `PRIMARY_VALUE` / `CIRCLE:primary` | uint8_t enum | `EXACT` | `DIRECT` | `baseline/ardupilot/ArduCopter/mode.h:85` |
| `LAND` | `Mode::Number::LAND` | `PRIMARY_VALUE` / `LAND:primary` | uint8_t enum | `EXACT` | `DIRECT` | `baseline/ardupilot/ArduCopter/mode.h:86` |
| `DRIFT` | `Mode::Number::DRIFT` | `PRIMARY_VALUE` / `DRIFT:primary` | uint8_t enum | `EXACT` | `DIRECT` | `baseline/ardupilot/ArduCopter/mode.h:87` |
| `SPORT` | `Mode::Number::SPORT` | `PRIMARY_VALUE` / `SPORT:primary` | uint8_t enum | `EXACT` | `DIRECT` | `baseline/ardupilot/ArduCopter/mode.h:88` |
| `FLIP` | `Mode::Number::FLIP` | `PRIMARY_VALUE` / `FLIP:primary` | uint8_t enum | `EXACT` | `DIRECT` | `baseline/ardupilot/ArduCopter/mode.h:89` |
| `BRAKE` | `Mode::Number::BRAKE` | `PRIMARY_VALUE` / `BRAKE:primary` | uint8_t enum | `EXACT` | `DIRECT` | `baseline/ardupilot/ArduCopter/mode.h:92` |
| `Mode_t-1` | `previous_accepted(Copter::flightmode->mode_number())` | `PRIMARY_VALUE` / `Mode_t-1:primary` | Mode::Number / 枚举 | `MODELLED` | `DERIVED` | `baseline/ardupilot/ArduCopter/Copter.h:388` |
| `ALT_t` | `Copter::current_loc.alt` | `PRIMARY_VALUE` / `ALT_t:primary` | Location altitude (int32 centimetres internally) / m above Home after conversion | `MODELLED` | `CONDITIONAL` | `baseline/ardupilot/ArduCopter/Copter.h:469` |
| `ALT_t` | `Copter::read_inertia() -> change_alt_frame(ABOVE_HOME) with ABOVE_HOME fallback` | `SUPPORTING_EVIDENCE` / `ALT_t:primary` | Location altitude-frame conversion / m above Home after origin-to-Home conversion or explicit fallback | `EXACT` | `CONDITIONAL` | `baseline/ardupilot/ArduCopter/inertia.cpp:37` |
| `ALT_t-1` | `previous_accepted(Copter::current_loc.alt)` | `PRIMARY_VALUE` / `ALT_t-1:primary` | float after conversion / m above same reference | `MODELLED` | `DERIVED` | `baseline/ardupilot/ArduCopter/Copter.h:469` |
| `ALT_Baro` | `Copter::baro_alt_m` | `PRIMARY_VALUE` / `ALT_Baro:primary` | float / m above barometer reference/Home-oriented offset | `MODELLED` | `INSTRUMENTATION_REQUIRED` | `baseline/ardupilot/ArduCopter/Copter.h:461` |
| `ALT_Baro` | `Copter::baro_alt_m = AP_Baro::get_altitude()` | `SUPPORTING_EVIDENCE` / `ALT_Baro:primary` | float / m above barometer reference/Home-oriented offset | `EXACT` | `INSTRUMENTATION_REQUIRED` | `baseline/ardupilot/ArduCopter/sensors.cpp:8` |
| `ALT_GPS` | `AP_GPS::location().alt` | `PRIMARY_VALUE` / `ALT_GPS:primary` | Location altitude (int32 centimetres) / GPS Location altitude frame | `MODELLED` | `CONDITIONAL` | `baseline/ardupilot/libraries/AP_GPS/AP_GPS.h:328` |
| `ALT_src` | `AP_NavEKF3_core::activeHgtSource` | `PRIMARY_VALUE` / `ALT_src:runtime_active` | AP_NavEKF_Source::SourceZ enum | `MODELLED` | `INSTRUMENTATION_REQUIRED` | `baseline/ardupilot/libraries/AP_NavEKF3/AP_NavEKF3_core.h:1481` |
| `ALT_src` | `AP_NavEKF_Source::getActiveSourceSet(core_index)` | `SUPPORTING_EVIDENCE` / `ALT_src:runtime_active` | uint8_t source-set index / 0..2 selecting EK3 source set 1..3 | `EXACT` | `INSTRUMENTATION_REQUIRED` | `baseline/ardupilot/libraries/AP_NavEKF/AP_NavEKF_Source.h:66-68` |
| `ALT_src` | `AP_NavEKF_Source::getPosZSource(core_index)` | `SUPPORTING_EVIDENCE` / `ALT_src:runtime_active` | SourceZ enum | `EXACT` | `INSTRUMENTATION_REQUIRED` | `baseline/ardupilot/libraries/AP_NavEKF/AP_NavEKF_Source.cpp:239-247` |
| `ALT_src` | `AP_NavEKF_Source::_source_set[0].posz / EK3_SRC1_POSZ` | `ALTERNATIVE_SEMANTICS` / `ALT_src:configured_source_set_1` | AP_Int8 / SourceZ enum / 0:none, 1:barometer, 2:rangefinder, 3:GPS, 4:beacon, 6:external navigation | `MODELLED` | `DIRECT` | `baseline/ardupilot/libraries/AP_NavEKF/AP_NavEKF_Source.cpp:46` |
| `ALT_src` | `AP_NavEKF_Source::_source_set[1].posz / EK3_SRC2_POSZ` | `ALTERNATIVE_SEMANTICS` / `ALT_src:configured_source_sets_2_3` | AP_Int8 / SourceZ enum | `MODELLED` | `DIRECT` | `baseline/ardupilot/libraries/AP_NavEKF/AP_NavEKF_Source.cpp:82` |
| `ALT_src` | `AP_NavEKF_Source::_source_set[2].posz / EK3_SRC3_POSZ` | `ALTERNATIVE_SEMANTICS` / `ALT_src:configured_source_sets_2_3` | AP_Int8 / SourceZ enum | `MODELLED` | `DIRECT` | `baseline/ardupilot/libraries/AP_NavEKF/AP_NavEKF_Source.cpp:119` |
| `ALT_src` | `NavEKF3_core::selectHeightForFusion() -> activeHgtSource` | `SUPPORTING_EVIDENCE` / `ALT_src:runtime_active` | SourceZ selection and fallback assignments | `MODELLED` | `INSTRUMENTATION_REQUIRED` | `baseline/ardupilot/libraries/AP_NavEKF3/AP_NavEKF3_PosVelFusion.cpp:1268` |
| `Baro` | `AP_Baro::healthy()` | `PRIMARY_VALUE` / `Baro:health` | bool | `MODELLED` | `CONDITIONAL` | `baseline/ardupilot/libraries/AP_Baro/AP_Baro.h:58` |
| `Baro` | `SYS_STATUS pressure health uses AP_Baro::all_healthy()` | `SUPPORTING_EVIDENCE` / `Baro:health` | aggregated sensor-health bit | `EXACT` | `CONDITIONAL` | `baseline/ardupilot/libraries/GCS_MAVLink/GCS.cpp:491` |
| `Baro` | `AP_NavEKF_Source::SourceZ::BARO` | `ALTERNATIVE_SEMANTICS` / `Baro:source_enum` | SourceZ enum | `MODELLED` | `INSTRUMENTATION_REQUIRED` | `baseline/ardupilot/libraries/AP_NavEKF/AP_NavEKF_Source.h:30` |
| `Baro` | `activeHgtSource = AP_NavEKF_Source::SourceZ::BARO` | `SUPPORTING_EVIDENCE` / `Baro:source_enum` | SourceZ assignment | `MODELLED` | `INSTRUMENTATION_REQUIRED` | `baseline/ardupilot/libraries/AP_NavEKF3/AP_NavEKF3_PosVelFusion.cpp:1315` |
| `Pos_t` | `Copter::current_loc.lat,current_loc.lng` | `PRIMARY_VALUE` / `Pos_t:primary` | int32 latitude/longitude / degrees scaled by 1e7, WGS84 | `MODELLED` | `CONDITIONAL` | `baseline/ardupilot/ArduCopter/Copter.h:469` |
| `Pos_t-1` | `previous_accepted(Copter::current_loc.lat,lng)` | `PRIMARY_VALUE` / `Pos_t-1:primary` | position tuple / WGS84 degrees or derived metres | `MODELLED` | `DERIVED` | `baseline/ardupilot/ArduCopter/Copter.h:469` |
| `home_position` | `AP_AHRS::get_home()` | `PRIMARY_VALUE` / `home_position:home` | const Location& / WGS84 lat/lon and Location altitude | `EXACT` | `DIRECT` | `baseline/ardupilot/libraries/AP_AHRS/AP_AHRS.h:600` |
| `home_position` | `AP_AHRS::_home, AP_AHRS::_home_is_set` | `SUPPORTING_EVIDENCE` / `home_position:home` | Location plus bool / absolute Location frame after set_home conversion | `EXACT` | `DIRECT` | `baseline/ardupilot/libraries/AP_AHRS/AP_AHRS.h:857` |
| `home_position` | `AP_AHRS::set_home(): _home = tmp; _home_is_set = true` | `SUPPORTING_EVIDENCE` / `home_position:home` | Location assignment and validity latch | `EXACT` | `CONDITIONAL` | `baseline/ardupilot/libraries/AP_AHRS/AP_AHRS.cpp:2027` |
| `home_position` | `GCS_MAVLINK::send_home_position()` | `SUPPORTING_EVIDENCE` / `home_position:home` | HOME_POSITION encoder | `EXACT` | `DIRECT` | `baseline/ardupilot/libraries/GCS_MAVLink/GCS_Common.cpp:3107` |
| `home_position` | `ModeRTL::rtl_path.return_target` | `ALTERNATIVE_SEMANTICS` / `home_position:rtl_return_target` | Location / WGS84 position with explicit Location altitude frame | `MODELLED` | `INSTRUMENTATION_REQUIRED` | `baseline/ardupilot/ArduCopter/mode.h:1609` |
| `home_position` | `ModeRTL::compute_return_target(): rally-or-Home assignment` | `SUPPORTING_EVIDENCE` / `home_position:rtl_return_target` | Location assignment / absolute WGS84 Location after frame conversion | `EXACT` | `INSTRUMENTATION_REQUIRED` | `baseline/ardupilot/ArduCopter/mode_rtl.cpp:467-475` |
| `GroundALT` | `no type-compatible numeric GroundALT definition` | `PRIMARY_VALUE` / `GroundALT:untyped_unresolved` | undefined paper abstraction | `UNRESOLVED` | `UNRESOLVED` | `无当前位置` |
| `GroundALT` | `Copter::ap.land_complete` | `ALTERNATIVE_SEMANTICS` / `GroundALT:landed_state` | bool | `MODELLED` | `DIRECT` | `baseline/ardupilot/ArduCopter/Copter.h:361` |
| `GroundALT` | `relative_altitude ~= 0` | `ALTERNATIVE_SEMANTICS` / `GroundALT:home_zero_height` | float after scaling / m above Home | `UNRESOLVED` | `DERIVED` | `baseline/ardupilot/libraries/GCS_MAVLink/GCS_Common.cpp:6163` |
| `Roll_t` | `AP_AHRS::get_roll_rad()` | `PRIMARY_VALUE` / `Roll_t:primary` | float / radians, body attitude in navigation frame | `EXACT` | `DIRECT` | `baseline/ardupilot/libraries/AP_AHRS/AP_AHRS.h:636` |
| `Pitch_t` | `AP_AHRS::get_pitch_rad()` | `PRIMARY_VALUE` / `Pitch_t:primary` | float / radians, body attitude in navigation frame | `EXACT` | `DIRECT` | `baseline/ardupilot/libraries/AP_AHRS/AP_AHRS.h:637` |
| `Yaw_t` | `AP_AHRS::get_yaw_rad()` | `PRIMARY_VALUE` / `Yaw_t:primary` | float / radians, body attitude in navigation frame | `EXACT` | `DIRECT` | `baseline/ardupilot/libraries/AP_AHRS/AP_AHRS.h:638` |
| `Yaw_t-1` | `previous_accepted(AP_AHRS::get_yaw_rad())` | `PRIMARY_VALUE` / `Yaw_t-1:primary` | float / radians | `MODELLED` | `DERIVED` | `baseline/ardupilot/libraries/AP_AHRS/AP_AHRS.h:638` |
| `Roll_original` | `ModeFlip::orig_attitude_euler_rad.x` | `PRIMARY_VALUE` / `Roll_original:primary` | float component of Vector3f / radians | `EXACT` | `INSTRUMENTATION_REQUIRED` | `baseline/ardupilot/ArduCopter/mode.h:981` |
| `Pitch_original` | `ModeFlip::orig_attitude_euler_rad.y` | `PRIMARY_VALUE` / `Pitch_original:primary` | float component of Vector3f / radians | `EXACT` | `INSTRUMENTATION_REQUIRED` | `baseline/ardupilot/ArduCopter/mode.h:981` |
| `Yaw_original` | `ModeFlip::orig_attitude_euler_rad.z` | `PRIMARY_VALUE` / `Yaw_original:primary` | float component of Vector3f / radians | `EXACT` | `INSTRUMENTATION_REQUIRED` | `baseline/ardupilot/ArduCopter/mode.h:981` |
| `Roll_rate` | `FLIP_ROTATION_RATE_RADS` | `PRIMARY_VALUE` / `Roll_rate:control_request` | float macro constant / rad/s (400 deg/s) | `MODELLED` | `INSTRUMENTATION_REQUIRED` | `baseline/ardupilot/ArduCopter/mode_flip.cpp:23` |
| `Roll_rate` | `AP_AHRS::get_gyro().x` | `ALTERNATIVE_SEMANTICS` / `Roll_rate:actual_rate` | float / rad/s body x | `MODELLED` | `DIRECT` | `baseline/ardupilot/libraries/AP_AHRS/AP_AHRS.h:93` |
| `Roll_direction` | `ModeFlip::roll_dir` | `PRIMARY_VALUE` / `Roll_direction:commanded_direction` | int8_t (-1 left, +1 right) | `EXACT` | `INSTRUMENTATION_REQUIRED` | `baseline/ardupilot/ArduCopter/mode.h:995` |
| `Roll_direction` | `sign(AP_AHRS::get_gyro().x)` | `ALTERNATIVE_SEMANTICS` / `Roll_direction:actual_direction` | direction derived from float sign / body x angular-rate sign | `MODELLED` | `DIRECT` | `baseline/ardupilot/libraries/AP_AHRS/AP_AHRS.h:93` |
| `Roll_direction` | `ModeFlip::roll_dir = FLIP_ROLL_RIGHT or FLIP_ROLL_LEFT` | `SUPPORTING_EVIDENCE` / `Roll_direction:commanded_direction` | int8_t from RC roll control sign | `EXACT` | `INSTRUMENTATION_REQUIRED` | `baseline/ardupilot/ArduCopter/mode_flip.cpp:71` |
| `Roll_direction` | `FLIP_ROTATION_RATE_RADS * ModeFlip::roll_dir` | `SUPPORTING_EVIDENCE` / `Roll_direction:commanded_direction` | float roll-rate setpoint / rad/s body roll setpoint | `EXACT` | `INSTRUMENTATION_REQUIRED` | `baseline/ardupilot/ArduCopter/mode_flip.cpp:118` |
| `FLIP1` | `ModeFlip::_state == FlipState::Start` | `PRIMARY_VALUE` / `FLIP1:primary` | private FlipState enum | `MODELLED` | `INSTRUMENTATION_REQUIRED` | `baseline/ardupilot/ArduCopter/mode.h:984` |
| `FLIP3` | `ModeFlip::_state == FlipState::Recover` | `PRIMARY_VALUE` / `FLIP3:primary` | private FlipState enum | `MODELLED` | `INSTRUMENTATION_REQUIRED` | `baseline/ardupilot/ArduCopter/mode.h:988` |
| `Circle_radius_t` | `AC_Circle::get_radius_m()` | `PRIMARY_VALUE` / `Circle_radius_t:primary` | float / m target radius | `EXACT` | `INSTRUMENTATION_REQUIRED` | `baseline/ardupilot/libraries/AC_WPNav/AC_Circle.h:58` |
| `Circle_radius_t-1` | `previous_accepted(AC_Circle::get_radius_m())` | `PRIMARY_VALUE` / `Circle_radius_t-1:primary` | float / m target radius | `MODELLED` | `DERIVED` | `baseline/ardupilot/libraries/AC_WPNav/AC_Circle.h:58` |
| `Circle_speed_t` | `AC_Circle::get_rate_current()` | `PRIMARY_VALUE` / `Circle_speed_t:primary` | float / deg/s signed angular target rate | `MODELLED` | `INSTRUMENTATION_REQUIRED` | `baseline/ardupilot/libraries/AC_WPNav/AC_Circle.h:73` |
| `Circle_speed_t-1` | `previous_accepted(AC_Circle::get_rate_current())` | `PRIMARY_VALUE` / `Circle_speed_t-1:primary` | float / deg/s angular target magnitude | `MODELLED` | `DERIVED` | `baseline/ardupilot/libraries/AC_WPNav/AC_Circle.h:73` |
| `Circle_direction_t` | `sign(AC_Circle::get_rate_current())` | `PRIMARY_VALUE` / `Circle_direction_t:primary` | direction derived from float sign | `EXACT` | `INSTRUMENTATION_REQUIRED` | `baseline/ardupilot/libraries/AC_WPNav/AC_Circle.h:73` |
| `Circle_direction_t` | `AC_Circle::set_rate_degs() sign convention` | `SUPPORTING_EVIDENCE` / `Circle_direction_t:primary` | documented sign convention | `EXACT` | `INSTRUMENTATION_REQUIRED` | `baseline/ardupilot/libraries/AC_WPNav/AC_Circle.h:75-77` |
| `Throttle_t` | `Copter::channel_throttle->get_radio_in()` | `PRIMARY_VALUE` / `Throttle_t:primary` | int16_t raw PWM / microseconds/PWM | `EXACT` | `CONDITIONAL` | `baseline/ardupilot/libraries/RC_Channel/RC_Channel.h:96` |
| `RC_throttle_t` | `Copter::channel_throttle->get_radio_in()` | `PRIMARY_VALUE` / `RC_throttle_t:primary` | int16_t raw PWM / microseconds/PWM | `EXACT` | `CONDITIONAL` | `baseline/ardupilot/libraries/RC_Channel/RC_Channel.h:96` |
| `RC_pitch` | `Copter::channel_pitch->get_radio_in()` | `PRIMARY_VALUE` / `RC_pitch:primary` | int16_t raw PWM / microseconds/PWM | `EXACT` | `CONDITIONAL` | `baseline/ardupilot/libraries/RC_Channel/RC_Channel.h:96` |
| `RC_pitch_t` | `Copter::channel_pitch->get_radio_in()` | `PRIMARY_VALUE` / `RC_pitch_t:primary` | int16_t raw PWM / microseconds/PWM | `EXACT` | `CONDITIONAL` | `baseline/ardupilot/libraries/RC_Channel/RC_Channel.h:96` |
| `RC_roll` | `Copter::channel_roll->get_radio_in()` | `PRIMARY_VALUE` / `RC_roll:primary` | int16_t raw PWM / microseconds/PWM | `EXACT` | `CONDITIONAL` | `baseline/ardupilot/libraries/RC_Channel/RC_Channel.h:96` |
| `RC_roll_t` | `Copter::channel_roll->get_radio_in()` | `PRIMARY_VALUE` / `RC_roll_t:primary` | int16_t raw PWM / microseconds/PWM | `EXACT` | `CONDITIONAL` | `baseline/ardupilot/libraries/RC_Channel/RC_Channel.h:96` |
| `RC_yaw_t` | `Copter::channel_yaw->get_radio_in()` | `PRIMARY_VALUE` / `RC_yaw_t:primary` | int16_t raw PWM / microseconds/PWM | `EXACT` | `CONDITIONAL` | `baseline/ardupilot/libraries/RC_Channel/RC_Channel.h:96` |
| `RC_roll` | `Copter::channel_roll = &rc().get_roll_channel()` | `SUPPORTING_EVIDENCE` / `RC_roll:primary` | RC_Channel pointer assignment | `EXACT` | `CONDITIONAL` | `baseline/ardupilot/ArduCopter/radio.cpp:23` |
| `RC_roll_t` | `Copter::channel_roll = &rc().get_roll_channel()` | `SUPPORTING_EVIDENCE` / `RC_roll_t:primary` | RC_Channel pointer assignment | `EXACT` | `CONDITIONAL` | `baseline/ardupilot/ArduCopter/radio.cpp:23` |
| `RC_pitch` | `Copter::channel_pitch = &rc().get_pitch_channel()` | `SUPPORTING_EVIDENCE` / `RC_pitch:primary` | RC_Channel pointer assignment | `EXACT` | `CONDITIONAL` | `baseline/ardupilot/ArduCopter/radio.cpp:24` |
| `RC_pitch_t` | `Copter::channel_pitch = &rc().get_pitch_channel()` | `SUPPORTING_EVIDENCE` / `RC_pitch_t:primary` | RC_Channel pointer assignment | `EXACT` | `CONDITIONAL` | `baseline/ardupilot/ArduCopter/radio.cpp:24` |
| `Throttle_t` | `Copter::channel_throttle = &rc().get_throttle_channel()` | `SUPPORTING_EVIDENCE` / `Throttle_t:primary` | RC_Channel pointer assignment | `EXACT` | `CONDITIONAL` | `baseline/ardupilot/ArduCopter/radio.cpp:25` |
| `RC_throttle_t` | `Copter::channel_throttle = &rc().get_throttle_channel()` | `SUPPORTING_EVIDENCE` / `RC_throttle_t:primary` | RC_Channel pointer assignment | `EXACT` | `CONDITIONAL` | `baseline/ardupilot/ArduCopter/radio.cpp:25` |
| `RC_yaw_t` | `Copter::channel_yaw = &rc().get_yaw_channel()` | `SUPPORTING_EVIDENCE` / `RC_yaw_t:primary` | RC_Channel pointer assignment | `EXACT` | `CONDITIONAL` | `baseline/ardupilot/ArduCopter/radio.cpp:26` |
| `RC_throttle_t-1` | `previous_accepted(channel_throttle->get_radio_in())` | `PRIMARY_VALUE` / `RC_throttle_t-1:primary` | int16_t / raw PWM | `MODELLED` | `DERIVED` | `baseline/ardupilot/libraries/RC_Channel/RC_Channel.h:96` |
| `RC_pitch_t-1` | `previous_accepted(channel_pitch->get_radio_in())` | `PRIMARY_VALUE` / `RC_pitch_t-1:primary` | int16_t / raw PWM | `MODELLED` | `DERIVED` | `baseline/ardupilot/libraries/RC_Channel/RC_Channel.h:96` |
| `RC_roll_t-1` | `previous_accepted(channel_roll->get_radio_in())` | `PRIMARY_VALUE` / `RC_roll_t-1:primary` | int16_t / raw PWM | `MODELLED` | `DERIVED` | `baseline/ardupilot/libraries/RC_Channel/RC_Channel.h:96` |
| `RC_yaw_t-1` | `previous_accepted(channel_yaw->get_radio_in())` | `PRIMARY_VALUE` / `RC_yaw_t-1:primary` | int16_t / raw PWM | `MODELLED` | `DERIVED` | `baseline/ardupilot/libraries/RC_Channel/RC_Channel.h:96` |
| `Armed` | `AP_Motors::armed()` | `PRIMARY_VALUE` / `Armed:primary` | bool | `EXACT` | `DIRECT` | `baseline/ardupilot/libraries/AP_Motors/AP_Motors_Class.h:117` |
| `Disarm` | `!AP_Motors::armed()` | `PRIMARY_VALUE` / `Disarm:primary` | bool | `EXACT` | `DIRECT` | `baseline/ardupilot/libraries/AP_Motors/AP_Motors_Class.h:117` |
| `RC_fail` | `Copter::failsafe.radio` | `PRIMARY_VALUE` / `RC_fail:primary` | 1-bit boolean | `EXACT` | `INSTRUMENTATION_REQUIRED` | `baseline/ardupilot/ArduCopter/Copter.h:402` |
| `GPS_fail` | `Copter::failsafe.ekf` | `PRIMARY_VALUE` / `GPS_fail:unresolved_paper_semantics` | 1-bit boolean | `UNRESOLVED` | `INSTRUMENTATION_REQUIRED` | `baseline/ardupilot/ArduCopter/Copter.h:404` |
| `GPS_fail` | `Copter::failsafe_ekf_event/off_event(): failsafe.ekf = true/false` | `SUPPORTING_EVIDENCE` / `GPS_fail:unresolved_paper_semantics` | bool state transitions | `EXACT` | `INSTRUMENTATION_REQUIRED` | `baseline/ardupilot/ArduCopter/ekf_check.cpp:169-226` |
| `GPS_fail` | `AP_GPS::status()` | `ALTERNATIVE_SEMANTICS` / `GPS_fail:fix_type_threshold` | AP_GPS_FixType enum | `MODELLED` | `CONDITIONAL` | `baseline/ardupilot/libraries/AP_GPS/AP_GPS.h:290` |
| `GPS_fail` | `AP_GPS::update_instance(): message timeout clears state and sets NONE/NO_GPS` | `SUPPORTING_EVIDENCE` / `GPS_fail:fix_type_threshold` | GPS state reset and fix-type assignment / GPS_TIMEOUT_MS uses AP_HAL::millis() | `EXACT` | `CONDITIONAL` | `baseline/ardupilot/libraries/AP_GPS/AP_GPS.cpp:887-905` |
| `GPS_fail` | `Copter::ap.gps_glitching` | `ALTERNATIVE_SEMANTICS` / `GPS_fail:gps_glitching` | bool | `MODELLED` | `CONDITIONAL` | `baseline/ardupilot/ArduCopter/Copter.h:371` |
| `GPS_fail` | `Copter::gpsglitch_check(): ap.gps_glitching = gps_glitching` | `SUPPORTING_EVIDENCE` / `GPS_fail:gps_glitching` | bool transition plus log/text event | `EXACT` | `CONDITIONAL` | `baseline/ardupilot/ArduCopter/events.cpp:310-323` |
| `GPS_count` | `AP_GPS::num_sats()` | `PRIMARY_VALUE` / `GPS_count:primary` | uint8_t / satellite count | `EXACT` | `CONDITIONAL` | `baseline/ardupilot/libraries/AP_GPS/AP_GPS.h:401` |
| `Speed_vertical_t` | `AP_AHRS::get_velocity_D(float&)` | `PRIMARY_VALUE` / `Speed_vertical_t:primary` | float / m/s NED down-positive | `MODELLED` | `CONDITIONAL` | `baseline/ardupilot/libraries/AP_AHRS/AP_AHRS.h:308` |
| `Parachute` | `AP_Parachute::released()` | `PRIMARY_VALUE` / `Parachute:released_latched` | bool | `EXACT` | `INSTRUMENTATION_REQUIRED` | `baseline/ardupilot/libraries/AP_Parachute/AP_Parachute.h:60` |
| `Parachute` | `AP_Parachute::release_initiated()` | `ALTERNATIVE_SEMANTICS` / `Parachute:release_initiated_latched` | bool | `MODELLED` | `INSTRUMENTATION_REQUIRED` | `baseline/ardupilot/libraries/AP_Parachute/AP_Parachute.h:63` |
| `Parachute` | `AP_Parachute::release(): _release_initiated = true` | `SUPPORTING_EVIDENCE` / `Parachute:release_initiated_latched` | bool latch | `EXACT` | `INSTRUMENTATION_REQUIRED` | `baseline/ardupilot/libraries/AP_Parachute/AP_Parachute.cpp:122` |
| `Parachute` | `AP_Parachute::update(): servo release command` | `SUPPORTING_EVIDENCE` / `Parachute:released_latched` | servo PWM command | `EXACT` | `INSTRUMENTATION_REQUIRED` | `baseline/ardupilot/libraries/AP_Parachute/AP_Parachute.cpp:147` |
| `Parachute` | `AP_Relay::set(PARACHUTE, true)` | `SUPPORTING_EVIDENCE` / `Parachute:released_latched` | relay command | `EXACT` | `INSTRUMENTATION_REQUIRED` | `baseline/ardupilot/libraries/AP_Parachute/AP_Parachute.cpp:153` |
| `Parachute` | `AP_Parachute::update(): _release_in_progress = true; _released = true` | `SUPPORTING_EVIDENCE` / `Parachute:released_latched` | two bool latches | `EXACT` | `INSTRUMENTATION_REQUIRED` | `baseline/ardupilot/libraries/AP_Parachute/AP_Parachute.cpp:157` |
| `Waypoint` | `no exact current Guided 'waypoint empty' symbol` | `PRIMARY_VALUE` / `Waypoint:guided_unresolved` | paper abstraction | `UNRESOLVED` | `UNRESOLVED` | `无当前位置` |
| `Waypoint` | `AP_Mission::present() / AP_Mission::_cmd_total > 1` | `ALTERNATIVE_SEMANTICS` / `Waypoint:mission_list_empty` | bool derived from uint16 command count | `MODELLED` | `CONDITIONAL` | `baseline/ardupilot/libraries/AP_Mission/AP_Mission.h:538` |
| `Waypoint` | `ModeGuided::guided_mode; ModeGuided::get_wp(Location&)` | `ALTERNATIVE_SEMANTICS` / `Waypoint:guided_submode_target` | Guided SubMode plus bool return | `MODELLED` | `INSTRUMENTATION_REQUIRED` | `baseline/ardupilot/ArduCopter/mode_guided.cpp:444` |
| `k` | `no current ArduPilot symbol` | `PRIMARY_VALUE` / `k:primary` | 未定义 | `UNRESOLVED` | `UNRESOLVED` | `无当前位置` |
| `RTL_ALT` | `ModeRTL::altitude_m / RTL_ALT_M` | `PRIMARY_VALUE` / `RTL_ALT:primary` | AP_Float / m above Home | `EXACT` | `DIRECT` | `baseline/ardupilot/ArduCopter/mode_rtl.cpp:8` |
| `LAND_SPEED_HIGH` | `ModeLand::land_speed_high_ms / LAND_SPD_HIGH_MS` | `PRIMARY_VALUE` / `LAND_SPEED_HIGH:primary` | AP_Float / m/s down-rate magnitude | `EXACT` | `DIRECT` | `baseline/ardupilot/ArduCopter/mode_land.cpp:15` |
| `LAND_SPEED` | `ModeLand::land_speed_ms / LAND_SPD_MS` | `PRIMARY_VALUE` / `LAND_SPEED:primary` | AP_Float / m/s down-rate magnitude | `EXACT` | `DIRECT` | `baseline/ardupilot/ArduCopter/mode_land.cpp:6` |
| `FS_EKF_ACTION` | `Parameters::fs_ekf_action / FS_EKF_ACTION` | `PRIMARY_VALUE` / `FS_EKF_ACTION:primary` | AP_Int8 enum / action enum | `EXACT` | `DIRECT` | `baseline/ardupilot/ArduCopter/Parameters.cpp:268` |
| `PILOT_SPEED_UP` | `ParametersG2::pilot_speed_up_ms / PILOT_SPD_UP` | `PRIMARY_VALUE` / `PILOT_SPEED_UP:primary` | AP_Float / m/s up-rate magnitude | `EXACT` | `DIRECT` | `baseline/ardupilot/ArduCopter/Parameters.cpp:1142` |
| `FS_THR_VALUE` | `Parameters::failsafe_throttle_value / FS_THR_VALUE` | `PRIMARY_VALUE` / `FS_THR_VALUE:primary` | AP_Int16 / raw PWM microseconds | `EXACT` | `DIRECT` | `baseline/ardupilot/ArduCopter/Parameters.cpp:132` |
| `CHUTE_ALT_MIN` | `AP_Parachute::_alt_min / CHUTE_ALT_MIN` | `PRIMARY_VALUE` / `CHUTE_ALT_MIN:primary` | AP_Int16 / m above Home | `EXACT` | `DIRECT` | `baseline/ardupilot/libraries/AP_Parachute/AP_Parachute.cpp:52` |

### ArduPilot 原子命题绑定状态

| 性质 | AP | 原子命题 | 语义组选择 | 状态 | 观测 | 判定说明 |
|---|---|---|---|---|---|---|
| `A.RTL1` | `A.RTL1-AP01` | `ALT_t < RTL_ALT` | `PRIMARY_SELECTED` | `MODELLED` | `CONDITIONAL` | 需要历史样本、坐标/单位换算、有效性条件、容差或上下文选择。 |
| `A.RTL1` | `A.RTL1-AP02` | `Mode_t = RTL` | `PRIMARY_SELECTED` | `EXACT` | `DIRECT` | 本原子命题可按列出的当前枚举、布尔状态或参数值直接判真。 |
| `A.RTL1` | `A.RTL1-AP03` | `ALT_t-1 < ALT_t` | `PRIMARY_SELECTED` | `MODELLED` | `CONDITIONAL` | 需要历史样本、坐标/单位换算、有效性条件、容差或上下文选择。 |
| `A.RTL2` | `A.RTL2-AP01` | `Mode_t = RTL` | `PRIMARY_SELECTED` | `EXACT` | `DIRECT` | 本原子命题可按列出的当前枚举、布尔状态或参数值直接判真。 |
| `A.RTL2` | `A.RTL2-AP02` | `ALT_t >= RTL_ALT` | `PRIMARY_SELECTED` | `MODELLED` | `CONDITIONAL` | 需要历史样本、坐标/单位换算、有效性条件、容差或上下文选择。 |
| `A.RTL2` | `A.RTL2-AP03` | `Pos_t != home_position` | `PRIMARY_WITH_ALTERNATIVES` | `MODELLED` | `CONDITIONAL` | 需要历史样本、坐标/单位换算、有效性条件、容差或上下文选择。 |
| `A.RTL2` | `A.RTL2-AP04` | `Pos_t-1 != Pos_t` | `PRIMARY_SELECTED` | `MODELLED` | `CONDITIONAL` | 需要历史样本、坐标/单位换算、有效性条件、容差或上下文选择。 |
| `A.RTL2` | `A.RTL2-AP05` | `ALT_t-1 = ALT_t` | `PRIMARY_SELECTED` | `MODELLED` | `CONDITIONAL` | 需要历史样本、坐标/单位换算、有效性条件、容差或上下文选择。 |
| `A.RTL3` | `A.RTL3-AP01` | `Mode_t = RTL` | `PRIMARY_SELECTED` | `EXACT` | `DIRECT` | 本原子命题可按列出的当前枚举、布尔状态或参数值直接判真。 |
| `A.RTL3` | `A.RTL3-AP02` | `ALT_t >= RTL_ALT` | `PRIMARY_SELECTED` | `MODELLED` | `CONDITIONAL` | 需要历史样本、坐标/单位换算、有效性条件、容差或上下文选择。 |
| `A.RTL3` | `A.RTL3-AP03` | `Pos_t = home_position` | `PRIMARY_WITH_ALTERNATIVES` | `MODELLED` | `CONDITIONAL` | 需要历史样本、坐标/单位换算、有效性条件、容差或上下文选择。 |
| `A.RTL3` | `A.RTL3-AP04` | `Mode_t = LAND` | `PRIMARY_SELECTED` | `EXACT` | `DIRECT` | 本原子命题可按列出的当前枚举、布尔状态或参数值直接判真。 |
| `A.RTL4` | `A.RTL4-AP01` | `Mode_t = LAND` | `PRIMARY_SELECTED` | `EXACT` | `DIRECT` | 本原子命题可按列出的当前枚举、布尔状态或参数值直接判真。 |
| `A.RTL4` | `A.RTL4-AP02` | `ALT_t = GroundALT` | `UNRESOLVED_PRIMARY` | `UNRESOLVED` | `UNRESOLVED` | 论文未定义 GroundALT 是数值高度、Home 高度、地形高度还是已落地状态；类型和参考面补证前不判真值。 |
| `A.RTL4` | `A.RTL4-AP03` | `Disarm = on` | `PRIMARY_SELECTED` | `EXACT` | `DIRECT` | 本原子命题可按列出的当前枚举、布尔状态或参数值直接判真。 |
| `A.FLIP1` | `A.FLIP1-AP01` | `Mode_t = FLIP` | `PRIMARY_SELECTED` | `EXACT` | `DIRECT` | 本原子命题可按列出的当前枚举、布尔状态或参数值直接判真。 |
| `A.FLIP1` | `A.FLIP1-AP02` | `Mode_t-1 in {ACRO,ALT_HOLD}` | `PRIMARY_SELECTED` | `MODELLED` | `DERIVED` | 需要历史样本、坐标/单位换算、有效性条件、容差或上下文选择。 |
| `A.FLIP1` | `A.FLIP1-AP03` | `Roll_t > 45deg` | `PRIMARY_SELECTED` | `EXACT` | `DIRECT` | 本原子命题可按列出的当前枚举、布尔状态或参数值直接判真。 |
| `A.FLIP1` | `A.FLIP1-AP04` | `Throttle_t <= 1500` | `PRIMARY_SELECTED` | `MODELLED` | `CONDITIONAL` | 需要历史样本、坐标/单位换算、有效性条件、容差或上下文选择。 |
| `A.FLIP1` | `A.FLIP1-AP05` | `ALT_t < 10m` | `PRIMARY_SELECTED` | `MODELLED` | `CONDITIONAL` | 需要历史样本、坐标/单位换算、有效性条件、容差或上下文选择。 |
| `A.FLIP1` | `A.FLIP1-AP06` | `Roll_t < 45deg` | `PRIMARY_SELECTED` | `EXACT` | `DIRECT` | 本原子命题可按列出的当前枚举、布尔状态或参数值直接判真。 |
| `A.FLIP1` | `A.FLIP1-AP07` | `Throttle_t >= 1500` | `PRIMARY_SELECTED` | `MODELLED` | `CONDITIONAL` | 需要历史样本、坐标/单位换算、有效性条件、容差或上下文选择。 |
| `A.FLIP1` | `A.FLIP1-AP08` | `ALT_t > 10m` | `PRIMARY_SELECTED` | `MODELLED` | `CONDITIONAL` | 需要历史样本、坐标/单位换算、有效性条件、容差或上下文选择。 |
| `A.FLIP2` | `A.FLIP2-AP01` | `Mode_t = FLIP` | `PRIMARY_SELECTED` | `EXACT` | `DIRECT` | 本原子命题可按列出的当前枚举、布尔状态或参数值直接判真。 |
| `A.FLIP2` | `A.FLIP2-AP02` | `-90deg <= Roll_t <= 45deg` | `PRIMARY_SELECTED` | `EXACT` | `DIRECT` | 本原子命题可按列出的当前枚举、布尔状态或参数值直接判真。 |
| `A.FLIP2` | `A.FLIP2-AP03` | `Roll_rate = 400deg/s` | `PRIMARY_WITH_ALTERNATIVES` | `MODELLED` | `INSTRUMENTATION_REQUIRED` | 需要历史样本、坐标/单位换算、有效性条件、容差或上下文选择。 |
| `A.FLIP2` | `A.FLIP2-AP04` | `Roll_direction = right` | `PRIMARY_WITH_ALTERNATIVES` | `EXACT` | `INSTRUMENTATION_REQUIRED` | 本原子命题可按列出的当前枚举、布尔状态或参数值直接判真。 |
| `A.FLIP3` | `A.FLIP3-AP01` | `Mode_t = FLIP3` | `PRIMARY_SELECTED` | `MODELLED` | `INSTRUMENTATION_REQUIRED` | 需要历史样本、坐标/单位换算、有效性条件、容差或上下文选择。 |
| `A.FLIP3` | `A.FLIP3-AP02` | `F_[0,k](Roll_t = Roll_original)` | `UNRESOLVED_PRIMARY` | `UNRESOLVED` | `UNRESOLVED` | 包含未公开时间上界、未定义航点空状态或已删除且无等价替代的参数。 |
| `A.FLIP3` | `A.FLIP3-AP03` | `F_[0,k](Pitch_t = Pitch_original)` | `UNRESOLVED_PRIMARY` | `UNRESOLVED` | `UNRESOLVED` | 包含未公开时间上界、未定义航点空状态或已删除且无等价替代的参数。 |
| `A.FLIP3` | `A.FLIP3-AP04` | `F_[0,k](Yaw_t = Yaw_original)` | `UNRESOLVED_PRIMARY` | `UNRESOLVED` | `UNRESOLVED` | 包含未公开时间上界、未定义航点空状态或已删除且无等价替代的参数。 |
| `A.FLIPGeneral` | `A.FLIPGeneral-AP01` | `Mode_t = FLIP1` | `PRIMARY_SELECTED` | `MODELLED` | `INSTRUMENTATION_REQUIRED` | 需要历史样本、坐标/单位换算、有效性条件、容差或上下文选择。 |
| `A.FLIPGeneral` | `A.FLIPGeneral-AP02` | `F_[0,2.5s](Mode_t = FLIP3)` | `PRIMARY_SELECTED` | `MODELLED` | `INSTRUMENTATION_REQUIRED` | 需要历史样本、坐标/单位换算、有效性条件、容差或上下文选择。 |
| `A.ALT_HOLD1` | `A.ALT_HOLD1-AP01` | `ALT_src = Baro` | `PRIMARY_WITH_ALTERNATIVES` | `MODELLED` | `INSTRUMENTATION_REQUIRED` | 需要历史样本、坐标/单位换算、有效性条件、容差或上下文选择。 |
| `A.ALT_HOLD1` | `A.ALT_HOLD1-AP02` | `ALT_t = ALT_Baro` | `PRIMARY_SELECTED` | `MODELLED` | `INSTRUMENTATION_REQUIRED` | 需要历史样本、坐标/单位换算、有效性条件、容差或上下文选择。 |
| `A.ALT_HOLD1` | `A.ALT_HOLD1-AP03` | `ALT_t != ALT_GPS` | `PRIMARY_SELECTED` | `MODELLED` | `CONDITIONAL` | 需要历史样本、坐标/单位换算、有效性条件、容差或上下文选择。 |
| `A.ALT_HOLD2` | `A.ALT_HOLD2-AP01` | `Mode_t = ALT_HOLD` | `PRIMARY_SELECTED` | `EXACT` | `DIRECT` | 本原子命题可按列出的当前枚举、布尔状态或参数值直接判真。 |
| `A.ALT_HOLD2` | `A.ALT_HOLD2-AP02` | `Throttle_t = 1500` | `PRIMARY_SELECTED` | `MODELLED` | `CONDITIONAL` | 需要历史样本、坐标/单位换算、有效性条件、容差或上下文选择。 |
| `A.ALT_HOLD2` | `A.ALT_HOLD2-AP03` | `ALT_t-1 = ALT_t` | `PRIMARY_SELECTED` | `MODELLED` | `CONDITIONAL` | 需要历史样本、坐标/单位换算、有效性条件、容差或上下文选择。 |
| `A.CIRCLE1` | `A.CIRCLE1-AP01` | `Mode_t = CIRCLE` | `PRIMARY_SELECTED` | `EXACT` | `DIRECT` | 本原子命题可按列出的当前枚举、布尔状态或参数值直接判真。 |
| `A.CIRCLE1` | `A.CIRCLE1-AP02` | `RC_pitch < 1500` | `PRIMARY_SELECTED` | `MODELLED` | `CONDITIONAL` | 需要历史样本、坐标/单位换算、有效性条件、容差或上下文选择。 |
| `A.CIRCLE1` | `A.CIRCLE1-AP03` | `Circle_radius_t > 0` | `PRIMARY_SELECTED` | `MODELLED` | `INSTRUMENTATION_REQUIRED` | 需要历史样本、坐标/单位换算、有效性条件、容差或上下文选择。 |
| `A.CIRCLE1` | `A.CIRCLE1-AP04` | `Circle_radius_t < Circle_radius_t-1` | `PRIMARY_SELECTED` | `MODELLED` | `INSTRUMENTATION_REQUIRED` | 需要历史样本、坐标/单位换算、有效性条件、容差或上下文选择。 |
| `A.CIRCLE2` | `A.CIRCLE2-AP01` | `Mode_t = CIRCLE` | `PRIMARY_SELECTED` | `EXACT` | `DIRECT` | 本原子命题可按列出的当前枚举、布尔状态或参数值直接判真。 |
| `A.CIRCLE2` | `A.CIRCLE2-AP02` | `RC_pitch > 1500` | `PRIMARY_SELECTED` | `MODELLED` | `CONDITIONAL` | 需要历史样本、坐标/单位换算、有效性条件、容差或上下文选择。 |
| `A.CIRCLE2` | `A.CIRCLE2-AP03` | `Circle_radius_t > Circle_radius_t-1` | `PRIMARY_SELECTED` | `MODELLED` | `INSTRUMENTATION_REQUIRED` | 需要历史样本、坐标/单位换算、有效性条件、容差或上下文选择。 |
| `A.CIRCLE3` | `A.CIRCLE3-AP01` | `Mode_t = CIRCLE` | `PRIMARY_SELECTED` | `EXACT` | `DIRECT` | 本原子命题可按列出的当前枚举、布尔状态或参数值直接判真。 |
| `A.CIRCLE3` | `A.CIRCLE3-AP02` | `RC_roll > 1500` | `PRIMARY_SELECTED` | `MODELLED` | `CONDITIONAL` | 需要历史样本、坐标/单位换算、有效性条件、容差或上下文选择。 |
| `A.CIRCLE3` | `A.CIRCLE3-AP03` | `Circle_direction_t = clockwise` | `PRIMARY_SELECTED` | `EXACT` | `INSTRUMENTATION_REQUIRED` | 本原子命题可按列出的当前枚举、布尔状态或参数值直接判真。 |
| `A.CIRCLE3` | `A.CIRCLE3-AP04` | `Circle_speed_t > Circle_speed_t-1` | `PRIMARY_SELECTED` | `MODELLED` | `INSTRUMENTATION_REQUIRED` | 需要历史样本、坐标/单位换算、有效性条件、容差或上下文选择。 |
| `A.CIRCLE4` | `A.CIRCLE4-AP01` | `Mode_t = CIRCLE` | `PRIMARY_SELECTED` | `EXACT` | `DIRECT` | 本原子命题可按列出的当前枚举、布尔状态或参数值直接判真。 |
| `A.CIRCLE4` | `A.CIRCLE4-AP02` | `RC_roll > 1500` | `PRIMARY_SELECTED` | `MODELLED` | `CONDITIONAL` | 需要历史样本、坐标/单位换算、有效性条件、容差或上下文选择。 |
| `A.CIRCLE4` | `A.CIRCLE4-AP03` | `Circle_direction_t = counterclockwise` | `PRIMARY_SELECTED` | `EXACT` | `INSTRUMENTATION_REQUIRED` | 本原子命题可按列出的当前枚举、布尔状态或参数值直接判真。 |
| `A.CIRCLE4` | `A.CIRCLE4-AP04` | `Circle_speed_t < Circle_speed_t-1` | `PRIMARY_SELECTED` | `MODELLED` | `INSTRUMENTATION_REQUIRED` | 需要历史样本、坐标/单位换算、有效性条件、容差或上下文选择。 |
| `A.CIRCLE5` | `A.CIRCLE5-AP01` | `Mode_t = CIRCLE` | `PRIMARY_SELECTED` | `EXACT` | `DIRECT` | 本原子命题可按列出的当前枚举、布尔状态或参数值直接判真。 |
| `A.CIRCLE5` | `A.CIRCLE5-AP02` | `RC_roll < 1500` | `PRIMARY_SELECTED` | `MODELLED` | `CONDITIONAL` | 需要历史样本、坐标/单位换算、有效性条件、容差或上下文选择。 |
| `A.CIRCLE5` | `A.CIRCLE5-AP03` | `Circle_direction_t = counterclockwise` | `PRIMARY_SELECTED` | `EXACT` | `INSTRUMENTATION_REQUIRED` | 本原子命题可按列出的当前枚举、布尔状态或参数值直接判真。 |
| `A.CIRCLE5` | `A.CIRCLE5-AP04` | `Circle_speed_t > Circle_speed_t-1` | `PRIMARY_SELECTED` | `MODELLED` | `INSTRUMENTATION_REQUIRED` | 需要历史样本、坐标/单位换算、有效性条件、容差或上下文选择。 |
| `A.CIRCLE6` | `A.CIRCLE6-AP01` | `Mode_t = CIRCLE` | `PRIMARY_SELECTED` | `EXACT` | `DIRECT` | 本原子命题可按列出的当前枚举、布尔状态或参数值直接判真。 |
| `A.CIRCLE6` | `A.CIRCLE6-AP02` | `RC_roll < 1500` | `PRIMARY_SELECTED` | `MODELLED` | `CONDITIONAL` | 需要历史样本、坐标/单位换算、有效性条件、容差或上下文选择。 |
| `A.CIRCLE6` | `A.CIRCLE6-AP03` | `Circle_direction_t = clockwise` | `PRIMARY_SELECTED` | `EXACT` | `INSTRUMENTATION_REQUIRED` | 本原子命题可按列出的当前枚举、布尔状态或参数值直接判真。 |
| `A.CIRCLE6` | `A.CIRCLE6-AP04` | `Circle_speed_t < Circle_speed_t-1` | `PRIMARY_SELECTED` | `MODELLED` | `INSTRUMENTATION_REQUIRED` | 需要历史样本、坐标/单位换算、有效性条件、容差或上下文选择。 |
| `A.CIRCLE7` | `A.CIRCLE7-AP01` | `Mode_t = CIRCLE` | `PRIMARY_SELECTED` | `EXACT` | `DIRECT` | 本原子命题可按列出的当前枚举、布尔状态或参数值直接判真。 |
| `A.CIRCLE7` | `A.CIRCLE7-AP02` | `RC_roll_t = RC_roll_t-1` | `PRIMARY_SELECTED` | `MODELLED` | `CONDITIONAL` | 需要历史样本、坐标/单位换算、有效性条件、容差或上下文选择。 |
| `A.CIRCLE7` | `A.CIRCLE7-AP03` | `RC_pitch_t = RC_pitch_t-1` | `PRIMARY_SELECTED` | `MODELLED` | `CONDITIONAL` | 需要历史样本、坐标/单位换算、有效性条件、容差或上下文选择。 |
| `A.CIRCLE7` | `A.CIRCLE7-AP04` | `RC_yaw_t = RC_yaw_t-1` | `PRIMARY_SELECTED` | `MODELLED` | `CONDITIONAL` | 需要历史样本、坐标/单位换算、有效性条件、容差或上下文选择。 |
| `A.CIRCLE7` | `A.CIRCLE7-AP05` | `RC_throttle_t <= RC_throttle_t-1 or RC_throttle_t >= RC_throttle_t-1` | `PRIMARY_SELECTED` | `MODELLED` | `CONDITIONAL` | 需要历史样本、坐标/单位换算、有效性条件、容差或上下文选择。 |
| `A.LAND1` | `A.LAND1-AP01` | `Mode_t = LAND` | `PRIMARY_SELECTED` | `EXACT` | `DIRECT` | 本原子命题可按列出的当前枚举、布尔状态或参数值直接判真。 |
| `A.LAND1` | `A.LAND1-AP02` | `ALT_t >= 10m` | `PRIMARY_SELECTED` | `MODELLED` | `CONDITIONAL` | 需要历史样本、坐标/单位换算、有效性条件、容差或上下文选择。 |
| `A.LAND1` | `A.LAND1-AP03` | `Speed_vertical_t = LAND_SPEED_HIGH` | `PRIMARY_SELECTED` | `MODELLED` | `CONDITIONAL` | 需要历史样本、坐标/单位换算、有效性条件、容差或上下文选择。 |
| `A.LAND2` | `A.LAND2-AP01` | `Mode_t = LAND` | `PRIMARY_SELECTED` | `EXACT` | `DIRECT` | 本原子命题可按列出的当前枚举、布尔状态或参数值直接判真。 |
| `A.LAND2` | `A.LAND2-AP02` | `ALT_t < 10m` | `PRIMARY_SELECTED` | `MODELLED` | `CONDITIONAL` | 需要历史样本、坐标/单位换算、有效性条件、容差或上下文选择。 |
| `A.LAND2` | `A.LAND2-AP03` | `Speed_vertical_t = LAND_SPEED` | `PRIMARY_SELECTED` | `MODELLED` | `CONDITIONAL` | 需要历史样本、坐标/单位换算、有效性条件、容差或上下文选择。 |
| `A.AUTO1` | `A.AUTO1-AP01` | `Mode_t = AUTO` | `PRIMARY_SELECTED` | `EXACT` | `DIRECT` | 本原子命题可按列出的当前枚举、布尔状态或参数值直接判真。 |
| `A.AUTO1` | `A.AUTO1-AP02` | `RC_roll_t = RC_roll_t-1` | `PRIMARY_SELECTED` | `MODELLED` | `CONDITIONAL` | 需要历史样本、坐标/单位换算、有效性条件、容差或上下文选择。 |
| `A.AUTO1` | `A.AUTO1-AP03` | `RC_pitch_t = RC_pitch_t-1` | `PRIMARY_SELECTED` | `MODELLED` | `CONDITIONAL` | 需要历史样本、坐标/单位换算、有效性条件、容差或上下文选择。 |
| `A.AUTO1` | `A.AUTO1-AP04` | `RC_throttle_t = RC_throttle_t-1` | `PRIMARY_SELECTED` | `MODELLED` | `CONDITIONAL` | 需要历史样本、坐标/单位换算、有效性条件、容差或上下文选择。 |
| `A.AUTO1` | `A.AUTO1-AP05` | `RC_yaw_t <= RC_yaw_t-1 or RC_yaw_t >= RC_yaw_t-1` | `PRIMARY_SELECTED` | `MODELLED` | `CONDITIONAL` | 需要历史样本、坐标/单位换算、有效性条件、容差或上下文选择。 |
| `A.BRAKE1` | `A.BRAKE1-AP01` | `Mode_t = BRAKE` | `PRIMARY_SELECTED` | `EXACT` | `DIRECT` | 本原子命题可按列出的当前枚举、布尔状态或参数值直接判真。 |
| `A.BRAKE1` | `A.BRAKE1-AP02` | `F_[0,k](Pos_t = Pos_t-1)` | `UNRESOLVED_PRIMARY` | `UNRESOLVED` | `UNRESOLVED` | 包含未公开时间上界、未定义航点空状态或已删除且无等价替代的参数。 |
| `A.DRIFT1` | `A.DRIFT1-AP01` | `GPS_fail = on` | `UNRESOLVED_PRIMARY` | `UNRESOLVED` | `UNRESOLVED` | 论文 GPS_fail 与当前位置/EKF 故障状态没有精确等价证据。 |
| `A.DRIFT1` | `A.DRIFT1-AP02` | `Mode_t = DRIFT` | `PRIMARY_SELECTED` | `EXACT` | `DIRECT` | 本原子命题可按列出的当前枚举、布尔状态或参数值直接判真。 |
| `A.DRIFT1` | `A.DRIFT1-AP03` | `F_[0,k](Mode_t = FS_EKF_ACTION)` | `UNRESOLVED_PRIMARY` | `UNRESOLVED` | `UNRESOLVED` | 包含未公开时间上界、未定义航点空状态或已删除且无等价替代的参数。 |
| `A.LOITER1` | `A.LOITER1-AP01` | `Mode_t = LOITER` | `PRIMARY_SELECTED` | `EXACT` | `DIRECT` | 本原子命题可按列出的当前枚举、布尔状态或参数值直接判真。 |
| `A.LOITER1` | `A.LOITER1-AP02` | `Pos_t = Pos_t-1` | `PRIMARY_SELECTED` | `MODELLED` | `CONDITIONAL` | 需要历史样本、坐标/单位换算、有效性条件、容差或上下文选择。 |
| `A.LOITER1` | `A.LOITER1-AP03` | `Yaw_t = Yaw_t-1` | `PRIMARY_SELECTED` | `MODELLED` | `DERIVED` | 需要历史样本、坐标/单位换算、有效性条件、容差或上下文选择。 |
| `A.LOITER1` | `A.LOITER1-AP04` | `ALT_t-1 = ALT_t` | `PRIMARY_SELECTED` | `MODELLED` | `CONDITIONAL` | 需要历史样本、坐标/单位换算、有效性条件、容差或上下文选择。 |
| `A.GUIDED1` | `A.GUIDED1-AP01` | `Mode_t = GUIDED` | `PRIMARY_SELECTED` | `EXACT` | `DIRECT` | 本原子命题可按列出的当前枚举、布尔状态或参数值直接判真。 |
| `A.GUIDED1` | `A.GUIDED1-AP02` | `Waypoint = empty` | `UNRESOLVED_PRIMARY` | `UNRESOLVED` | `UNRESOLVED` | 包含未公开时间上界、未定义航点空状态或已删除且无等价替代的参数。 |
| `A.GUIDED1` | `A.GUIDED1-AP03` | `Pos_t = Pos_t-1` | `PRIMARY_SELECTED` | `MODELLED` | `CONDITIONAL` | 需要历史样本、坐标/单位换算、有效性条件、容差或上下文选择。 |
| `A.GUIDED1` | `A.GUIDED1-AP04` | `Yaw_t = Yaw_t-1` | `PRIMARY_SELECTED` | `MODELLED` | `DERIVED` | 需要历史样本、坐标/单位换算、有效性条件、容差或上下文选择。 |
| `A.GUIDED1` | `A.GUIDED1-AP05` | `ALT_t-1 = ALT_t` | `PRIMARY_SELECTED` | `MODELLED` | `CONDITIONAL` | 需要历史样本、坐标/单位换算、有效性条件、容差或上下文选择。 |
| `A.SPORT1` | `A.SPORT1-AP01` | `Mode_t = SPORT` | `PRIMARY_SELECTED` | `EXACT` | `DIRECT` | 本原子命题可按列出的当前枚举、布尔状态或参数值直接判真。 |
| `A.SPORT1` | `A.SPORT1-AP02` | `Speed_vertical_t = PILOT_SPEED_UP` | `PRIMARY_SELECTED` | `MODELLED` | `CONDITIONAL` | 需要历史样本、坐标/单位换算、有效性条件、容差或上下文选择。 |
| `A.RC.FS1` | `A.RC.FS1-AP01` | `Mode_t = ACRO` | `PRIMARY_SELECTED` | `EXACT` | `DIRECT` | 本原子命题可按列出的当前枚举、布尔状态或参数值直接判真。 |
| `A.RC.FS1` | `A.RC.FS1-AP02` | `Throttle_t < FS_THR_VALUE` | `PRIMARY_SELECTED` | `MODELLED` | `CONDITIONAL` | 需要历史样本、坐标/单位换算、有效性条件、容差或上下文选择。 |
| `A.RC.FS1` | `A.RC.FS1-AP03` | `Armed = true` | `PRIMARY_SELECTED` | `EXACT` | `DIRECT` | 本原子命题可按列出的当前枚举、布尔状态或参数值直接判真。 |
| `A.RC.FS1` | `A.RC.FS1-AP04` | `Disarm = on` | `PRIMARY_SELECTED` | `EXACT` | `DIRECT` | 本原子命题可按列出的当前枚举、布尔状态或参数值直接判真。 |
| `A.RC.FS2` | `A.RC.FS2-AP01` | `Throttle_t < FS_THR_VALUE` | `PRIMARY_SELECTED` | `MODELLED` | `CONDITIONAL` | 需要历史样本、坐标/单位换算、有效性条件、容差或上下文选择。 |
| `A.RC.FS2` | `A.RC.FS2-AP02` | `RC_fail = on` | `PRIMARY_SELECTED` | `MODELLED` | `INSTRUMENTATION_REQUIRED` | 需要历史样本、坐标/单位换算、有效性条件、容差或上下文选择。 |
| `A.CHUTE1` | `A.CHUTE1-AP01` | `Parachute = on` | `PRIMARY_WITH_ALTERNATIVES` | `EXACT` | `INSTRUMENTATION_REQUIRED` | 本原子命题可按列出的当前枚举、布尔状态或参数值直接判真。 |
| `A.CHUTE1` | `A.CHUTE1-AP02` | `Armed = true` | `PRIMARY_SELECTED` | `EXACT` | `DIRECT` | 本原子命题可按列出的当前枚举、布尔状态或参数值直接判真。 |
| `A.CHUTE1` | `A.CHUTE1-AP03` | `Mode_t notin {FLIP,ACRO}` | `PRIMARY_SELECTED` | `EXACT` | `DIRECT` | 本原子命题可按列出的当前枚举、布尔状态或参数值直接判真。 |
| `A.CHUTE1` | `A.CHUTE1-AP04` | `ALT_t <= ALT_t-1` | `PRIMARY_SELECTED` | `MODELLED` | `CONDITIONAL` | 需要历史样本、坐标/单位换算、有效性条件、容差或上下文选择。 |
| `A.CHUTE1` | `A.CHUTE1-AP05` | `ALT_t > CHUTE_ALT_MIN` | `PRIMARY_SELECTED` | `MODELLED` | `CONDITIONAL` | 需要历史样本、坐标/单位换算、有效性条件、容差或上下文选择。 |
| `A.GPS.FS1` | `A.GPS.FS1-AP01` | `GPS_fail = on` | `UNRESOLVED_PRIMARY` | `UNRESOLVED` | `UNRESOLVED` | 论文 GPS_fail 与当前位置/EKF 故障状态没有精确等价证据。 |
| `A.GPS.FS1` | `A.GPS.FS1-AP02` | `GPS_count < 4` | `PRIMARY_SELECTED` | `EXACT` | `CONDITIONAL` | 本原子命题可按列出的当前枚举、布尔状态或参数值直接判真。 |
| `A.GPS.FS2` | `A.GPS.FS2-AP01` | `GPS_fail = on` | `UNRESOLVED_PRIMARY` | `UNRESOLVED` | `UNRESOLVED` | 论文 GPS_fail 与当前位置/EKF 故障状态没有精确等价证据。 |
| `A.GPS.FS2` | `A.GPS.FS2-AP02` | `Baro = on` | `PRIMARY_WITH_ALTERNATIVES` | `MODELLED` | `CONDITIONAL` | 需要历史样本、坐标/单位换算、有效性条件、容差或上下文选择。 |
| `A.GPS.FS2` | `A.GPS.FS2-AP03` | `ALT_src = Baro` | `PRIMARY_WITH_ALTERNATIVES` | `MODELLED` | `INSTRUMENTATION_REQUIRED` | 需要历史样本、坐标/单位换算、有效性条件、容差或上下文选择。 |

## 三、PX4 词项绑定

| 论文词项 | 当前源码实体 | 绑定角色/候选组 | 类型/单位 | 置信度 | MAVLink 可观测性 | 证据位置 |
|---|---|---|---|---|---|---|
| `Mode_t` | `vehicle_status.nav_state` | `PRIMARY_VALUE` / `Mode_t:primary` | uint8 enum | `EXACT` | `DIRECT` | `baseline/px4/msg/versioned/VehicleStatus.msg:35` |
| `Mode_t` | `get_px4_custom_mode(vehicle_status.nav_state)` | `SUPPORTING_EVIDENCE` / `Mode_t:primary` | uint32 packed custom_mode | `EXACT` | `DIRECT` | `baseline/px4/src/modules/commander/px4_custom_mode.h:102` |
| `ALTITUDE` | `vehicle_status_s::NAVIGATION_STATE_ALTCTL` | `PRIMARY_VALUE` / `ALTITUDE:primary` | uint8 enum | `EXACT` | `DIRECT` | `baseline/px4/msg/versioned/VehicleStatus.msg:37` |
| `POSITION` | `vehicle_status_s::NAVIGATION_STATE_POSCTL` | `PRIMARY_VALUE` / `POSITION:primary` | uint8 enum | `EXACT` | `DIRECT` | `baseline/px4/msg/versioned/VehicleStatus.msg:38` |
| `HOLD` | `vehicle_status_s::NAVIGATION_STATE_AUTO_LOITER` | `PRIMARY_VALUE` / `HOLD:primary` | uint8 enum | `EXACT` | `DIRECT` | `baseline/px4/msg/versioned/VehicleStatus.msg:40` |
| `RTL` | `vehicle_status_s::NAVIGATION_STATE_AUTO_RTL` | `PRIMARY_VALUE` / `RTL:primary` | uint8 enum | `EXACT` | `DIRECT` | `baseline/px4/msg/versioned/VehicleStatus.msg:41` |
| `LAND` | `vehicle_status_s::NAVIGATION_STATE_AUTO_LAND` | `PRIMARY_VALUE` / `LAND:primary` | uint8 enum | `EXACT` | `DIRECT` | `baseline/px4/msg/versioned/VehicleStatus.msg:54` |
| `ORBIT` | `vehicle_status_s::NAVIGATION_STATE_ORBIT` | `PRIMARY_VALUE` / `ORBIT:primary` | uint8 enum | `EXACT` | `DIRECT` | `baseline/px4/msg/versioned/VehicleStatus.msg:57` |
| `ALT_t` | `vehicle_global_position.alt` | `PRIMARY_VALUE` / `ALT_t:global_amsl` | float32 / m AMSL | `MODELLED` | `CONDITIONAL` | `baseline/px4/msg/versioned/VehicleGlobalPosition.msg:15` |
| `ALT_t` | `EKF2::PublishGlobalPosition(): lla.altitude(), alt_valid, alt_reset_counter` | `SUPPORTING_EVIDENCE` / `ALT_t:global_amsl` | vehicle_global_position altitude plus validity/reset metadata / m AMSL | `EXACT` | `INSTRUMENTATION_REQUIRED` | `baseline/px4/src/modules/ekf2/EKF2.cpp:1200-1212` |
| `ALT_t` | `MavlinkStreamGlobalPositionInt::send(): msg.alt = gpos.alt * 1000` | `SUPPORTING_EVIDENCE` / `ALT_t:global_amsl` | int32 millimetres / mm AMSL | `EXACT` | `CONDITIONAL` | `baseline/px4/src/modules/mavlink/streams/GLOBAL_POSITION_INT.hpp:87` |
| `ALT_t` | `vehicle_global_position.alt - home_position.alt` | `ALTERNATIVE_SEMANTICS` / `ALT_t:relative_home` | float32 / m above Home | `MODELLED` | `CONDITIONAL` | `baseline/px4/src/modules/mavlink/streams/GLOBAL_POSITION_INT.hpp:77` |
| `ALT_t` | `vehicle_global_position.alt - selected RTL destination altitude` | `ALTERNATIVE_SEMANTICS` / `ALT_t:relative_rtl_destination` | float derived from current AMSL and selected destination AMSL / m above Home, safe point, or mission landing destination | `MODELLED` | `INSTRUMENTATION_REQUIRED` | `baseline/px4/src/modules/navigator/rtl.cpp:477-530` |
| `ALT_t` | `vehicle_global_position.alt - takeoff-reference altitude captured at command/activation` | `ALTERNATIVE_SEMANTICS` / `ALT_t:relative_takeoff_reference` | trace-derived float / m above takeoff reference | `MODELLED` | `DERIVED` | `baseline/px4/src/modules/navigator/takeoff.cpp:188-199` |
| `ALT_t` | `-vehicle_local_position.z` | `ALTERNATIVE_SEMANTICS` / `ALT_t:local_ned` | float32 / m above local NED origin | `MODELLED` | `CONDITIONAL` | `baseline/px4/msg/versioned/VehicleLocalPosition.msg:17` |
| `ALT_t` | `vehicle_local_position.dist_bottom` | `ALTERNATIVE_SEMANTICS` / `ALT_t:distance_to_ground` | float32 / m distance above bottom/ground surface | `MODELLED` | `CONDITIONAL` | `baseline/px4/msg/versioned/VehicleLocalPosition.msg:61` |
| `ALT_t-1` | `previous_accepted(vehicle_global_position.alt)` | `PRIMARY_VALUE` / `ALT_t-1:global_amsl` | float32 or trace-derived float / m AMSL | `MODELLED` | `DERIVED` | `baseline/px4/msg/versioned/VehicleGlobalPosition.msg:15` |
| `ALT_t-1` | `previous_accepted(vehicle_global_position.alt-home_position.alt)` | `ALTERNATIVE_SEMANTICS` / `ALT_t-1:relative_home` | float32 or trace-derived float / m above Home | `MODELLED` | `DERIVED` | `baseline/px4/src/modules/mavlink/streams/GLOBAL_POSITION_INT.hpp:77` |
| `ALT_t-1` | `previous_accepted(-vehicle_local_position.z)` | `ALTERNATIVE_SEMANTICS` / `ALT_t-1:local_ned` | float32 or trace-derived float / m above local NED origin | `MODELLED` | `DERIVED` | `baseline/px4/msg/versioned/VehicleLocalPosition.msg:17` |
| `ALT_t-1` | `previous_accepted(vehicle_local_position.dist_bottom)` | `ALTERNATIVE_SEMANTICS` / `ALT_t-1:distance_to_ground` | float32 or trace-derived float / m distance to ground | `MODELLED` | `DERIVED` | `baseline/px4/msg/versioned/VehicleLocalPosition.msg:61` |
| `ALT_t-1` | `previous_accepted(current AMSL-selected RTL destination AMSL)` | `ALTERNATIVE_SEMANTICS` / `ALT_t-1:relative_rtl_destination` | float32 or trace-derived float / m above selected RTL destination | `MODELLED` | `DERIVED` | `baseline/px4/src/modules/navigator/rtl.cpp:477` |
| `ALT_t-1` | `previous_accepted(current AMSL-captured takeoff reference AMSL)` | `ALTERNATIVE_SEMANTICS` / `ALT_t-1:relative_takeoff_reference` | float32 or trace-derived float / m above takeoff reference | `MODELLED` | `DERIVED` | `baseline/px4/src/modules/navigator/takeoff.cpp:188` |
| `Pos_t` | `vehicle_global_position.lat,lon` | `PRIMARY_VALUE` / `Pos_t:global_wgs84` | float64 tuple / degrees WGS84 | `MODELLED` | `DIRECT` | `baseline/px4/msg/versioned/VehicleGlobalPosition.msg:13` |
| `Pos_t` | `vehicle_local_position.x,y` | `ALTERNATIVE_SEMANTICS` / `Pos_t:local_ned` | float32 tuple / m local NED | `MODELLED` | `CONDITIONAL` | `baseline/px4/msg/versioned/VehicleLocalPosition.msg:15` |
| `Pos_t-1` | `previous_accepted(vehicle_global_position.lat,lon)` | `PRIMARY_VALUE` / `Pos_t-1:global_wgs84` | position tuple / WGS84 degrees | `MODELLED` | `DERIVED` | `baseline/px4/msg/versioned/VehicleGlobalPosition.msg:13` |
| `Pos_t-1` | `previous_accepted(vehicle_local_position.x,y)` | `ALTERNATIVE_SEMANTICS` / `Pos_t-1:local_ned` | position tuple / m local NED | `MODELLED` | `DERIVED` | `baseline/px4/msg/versioned/VehicleLocalPosition.msg:15` |
| `home_position` | `home_position.lat,lon` | `PRIMARY_VALUE` / `home_position:primary` | float64 tuple / degrees WGS84 | `EXACT` | `DIRECT` | `baseline/px4/msg/versioned/HomePosition.msg:7` |
| `GroundALT` | `no type-compatible numeric GroundALT definition` | `PRIMARY_VALUE` / `GroundALT:untyped_unresolved` | undefined paper abstraction | `UNRESOLVED` | `UNRESOLVED` | `无当前位置` |
| `GroundALT` | `vehicle_land_detected.landed` | `ALTERNATIVE_SEMANTICS` / `GroundALT:landed_state` | bool | `MODELLED` | `DIRECT` | `baseline/px4/msg/versioned/VehicleLandDetected.msg:8` |
| `GroundALT` | `home_position.alt` | `ALTERNATIVE_SEMANTICS` / `GroundALT:home_amsl` | float32 / m AMSL | `MODELLED` | `DIRECT` | `baseline/px4/msg/versioned/HomePosition.msg:9` |
| `GroundALT` | `vehicle_global_position.terrain_alt` | `ALTERNATIVE_SEMANTICS` / `GroundALT:terrain_amsl` | float32 / m WGS84 terrain altitude | `UNRESOLVED` | `INSTRUMENTATION_REQUIRED` | `baseline/px4/msg/versioned/VehicleGlobalPosition.msg:30` |
| `Yaw_t` | `vehicle_local_position.heading` | `PRIMARY_VALUE` / `Yaw_t:primary` | float32 / radians in NED tangent plane | `EXACT` | `DIRECT` | `baseline/px4/msg/versioned/VehicleLocalPosition.msg:42` |
| `Yaw_t-1` | `previous_accepted(vehicle_local_position.heading)` | `PRIMARY_VALUE` / `Yaw_t-1:primary` | float32 / radians | `MODELLED` | `DERIVED` | `baseline/px4/msg/versioned/VehicleLocalPosition.msg:42` |
| `Speed_vertical_t` | `vehicle_local_position.vz` | `PRIMARY_VALUE` / `Speed_vertical_t:primary` | float32 / m/s NED down-positive | `MODELLED` | `DIRECT` | `baseline/px4/msg/versioned/VehicleLocalPosition.msg:28` |
| `Circle_radius_t` | `FlightTaskOrbit::_orbit_radius` | `PRIMARY_VALUE` / `Circle_radius_t:target_radius` | float / m target radius | `EXACT` | `INSTRUMENTATION_REQUIRED` | `baseline/px4/src/modules/flight_mode_manager/tasks/Orbit/FlightTaskOrbit.hpp:119` |
| `Circle_radius_t` | `fabs(orbit_status.radius)` | `SUPPORTING_EVIDENCE` / `Circle_radius_t:target_radius` | float32 / m | `EXACT` | `DIRECT` | `baseline/px4/msg/OrbitStatus.msg:10` |
| `Circle_radius_t-1` | `previous_accepted(fabs(orbit_status.radius))` | `PRIMARY_VALUE` / `Circle_radius_t-1:primary` | float32 / m | `MODELLED` | `DERIVED` | `baseline/px4/msg/OrbitStatus.msg:10` |
| `Circle_direction_t` | `sign(orbit_status.radius)` | `PRIMARY_VALUE` / `Circle_direction_t:target_encoded_direction` | bool derived from float sign | `MODELLED` | `DIRECT` | `baseline/px4/src/modules/flight_mode_manager/tasks/Orbit/FlightTaskOrbit.cpp:138` |
| `Circle_direction_t` | `sign(FlightTaskOrbit::_orbit_velocity)` | `SUPPORTING_EVIDENCE` / `Circle_direction_t:target_encoded_direction` | direction derived from float sign / signed target tangential velocity | `EXACT` | `INSTRUMENTATION_REQUIRED` | `baseline/px4/src/modules/flight_mode_manager/tasks/Orbit/FlightTaskOrbit.hpp:118` |
| `Circle_direction_t` | `FlightTaskOrbit::applyCommandParameters(): command.param1 sign -> _orbit_velocity` | `SUPPORTING_EVIDENCE` / `Circle_direction_t:target_encoded_direction` | signed float target velocity / param1 radius sign plus param2 m/s speed | `EXACT` | `CONDITIONAL` | `baseline/px4/src/modules/flight_mode_manager/tasks/Orbit/FlightTaskOrbit.cpp:68` |
| `Circle_direction_t` | `MavlinkStreamOrbitStatus::send()` | `SUPPORTING_EVIDENCE` / `Circle_direction_t:target_encoded_direction` | signed radius encoder | `EXACT` | `DIRECT` | `baseline/px4/src/modules/mavlink/streams/ORBIT_EXECUTION_STATUS.hpp:70` |
| `Circle_direction_t` | `sign(cross_2d(position - orbit_center, horizontal_velocity))` | `ALTERNATIVE_SEMANTICS` / `Circle_direction_t:actual_motion_direction` | direction derived from position, center and velocity / one common local tangent frame | `MODELLED` | `DERIVED` | `baseline/px4/msg/versioned/VehicleLocalPosition.msg:26` |
| `Circle_speed_t` | `fabs(FlightTaskOrbit::_orbit_velocity)` | `PRIMARY_VALUE` / `Circle_speed_t:target_tangential_speed` | float / m/s target tangential speed magnitude | `MODELLED` | `INSTRUMENTATION_REQUIRED` | `baseline/px4/src/modules/flight_mode_manager/tasks/Orbit/FlightTaskOrbit.hpp:118` |
| `Circle_speed_t` | `hypot(vehicle_local_position.vx, vehicle_local_position.vy)` | `ALTERNATIVE_SEMANTICS` / `Circle_speed_t:actual_ground_speed` | float32 / m/s actual horizontal ground speed | `MODELLED` | `DERIVED` | `baseline/px4/msg/versioned/VehicleLocalPosition.msg:26` |
| `Circle_speed_t-1` | `previous_accepted(fabs(FlightTaskOrbit::_orbit_velocity))` | `PRIMARY_VALUE` / `Circle_speed_t-1:target_tangential_speed` | float / m/s | `MODELLED` | `DERIVED` | `baseline/px4/src/modules/flight_mode_manager/tasks/Orbit/FlightTaskOrbit.hpp:118` |
| `Circle_speed_t-1` | `previous_accepted(hypot(vehicle_local_position.vx,vehicle_local_position.vy))` | `ALTERNATIVE_SEMANTICS` / `Circle_speed_t-1:actual_ground_speed` | float / m/s | `MODELLED` | `DERIVED` | `baseline/px4/msg/versioned/VehicleLocalPosition.msg:26` |
| `RC_pitch` | `manual_control_setpoint.pitch` | `ALTERNATIVE_SEMANTICS` / `RC_pitch:normalized_manual_control` | float32 normalized [-1,1] | `MODELLED` | `DIRECT` | `baseline/px4/msg/versioned/ManualControlSetpoint.msg:27` |
| `RC_pitch` | `input_rc.values[RC_MAP_PITCH-1]` | `PRIMARY_VALUE` / `RC_pitch:raw_pwm` | uint16 raw PWM / microseconds/PWM | `MODELLED` | `CONDITIONAL` | `baseline/px4/src/modules/rc_update/rc_update.cpp:440` |
| `RC_pitch` | `RCUpdate::_rc.function[FUNCTION_PITCH] = RC_MAP_PITCH - 1` | `SUPPORTING_EVIDENCE` / `RC_pitch:raw_pwm` | int8 channel-index mapping | `EXACT` | `DIRECT` | `baseline/px4/src/modules/rc_update/rc_update.cpp:195` |
| `RC_roll` | `manual_control_setpoint.roll` | `ALTERNATIVE_SEMANTICS` / `RC_roll:normalized_manual_control` | float32 normalized [-1,1] | `MODELLED` | `DIRECT` | `baseline/px4/msg/versioned/ManualControlSetpoint.msg:26` |
| `RC_roll` | `input_rc.values[RC_MAP_ROLL-1]` | `PRIMARY_VALUE` / `RC_roll:raw_pwm` | uint16 raw PWM / microseconds/PWM | `MODELLED` | `CONDITIONAL` | `baseline/px4/src/modules/rc_update/rc_update.cpp:440` |
| `RC_roll` | `RCUpdate::_rc.function[FUNCTION_ROLL] = RC_MAP_ROLL - 1` | `SUPPORTING_EVIDENCE` / `RC_roll:raw_pwm` | int8 channel-index mapping | `EXACT` | `DIRECT` | `baseline/px4/src/modules/rc_update/rc_update.cpp:194` |
| `Throttle_t` | `manual_control_setpoint.throttle` | `ALTERNATIVE_SEMANTICS` / `Throttle_t:normalized_manual_control` | float32 normalized [-1,1] | `MODELLED` | `DIRECT` | `baseline/px4/msg/versioned/ManualControlSetpoint.msg:29` |
| `Throttle_t` | `input_rc.values[RC_MAP_THROTTLE-1]` | `PRIMARY_VALUE` / `Throttle_t:raw_pwm` | uint16 raw PWM / microseconds/PWM | `MODELLED` | `CONDITIONAL` | `baseline/px4/src/modules/rc_update/rc_update.cpp:440` |
| `Throttle_t` | `RCUpdate::_rc.function[FUNCTION_THROTTLE] = RC_MAP_THROTTLE - 1` | `SUPPORTING_EVIDENCE` / `Throttle_t:raw_pwm` | int8 channel-index mapping | `EXACT` | `DIRECT` | `baseline/px4/src/modules/rc_update/rc_update.cpp:193` |
| `RC_pitch` | `manual_control_setpoint.data_source == SOURCE_RC` | `SUPPORTING_EVIDENCE` / `RC_pitch:normalized_manual_control` | uint8 source enum and field | `EXACT` | `INSTRUMENTATION_REQUIRED` | `baseline/px4/msg/versioned/ManualControlSetpoint.msg:8-17` |
| `RC_roll` | `manual_control_setpoint.data_source == SOURCE_RC` | `SUPPORTING_EVIDENCE` / `RC_roll:normalized_manual_control` | uint8 source enum and field | `EXACT` | `INSTRUMENTATION_REQUIRED` | `baseline/px4/msg/versioned/ManualControlSetpoint.msg:8-17` |
| `Throttle_t` | `manual_control_setpoint.data_source == SOURCE_RC` | `SUPPORTING_EVIDENCE` / `Throttle_t:normalized_manual_control` | uint8 source enum and field | `EXACT` | `INSTRUMENTATION_REQUIRED` | `baseline/px4/msg/versioned/ManualControlSetpoint.msg:8-17` |
| `RC_t` | `failsafe_flags.manual_control_signal_lost` | `ALTERNATIVE_SEMANTICS` / `RC_t:manual_control_availability` | bool | `EXACT` | `CONDITIONAL` | `baseline/px4/msg/FailsafeFlags.msg:39` |
| `RC_t` | `manual_control_setpoint.valid && age <= COM_RC_LOSS_T` | `SUPPORTING_EVIDENCE` / `RC_t:manual_control_availability` | derived bool | `EXACT` | `DERIVED` | `baseline/px4/src/modules/commander/HealthAndArmingChecks/checks/rcAndDataLinkCheck.cpp:48` |
| `RC_t` | `HIGH_LATENCY2.failure_flags |= HL_FAILURE_FLAG_RC_RECEIVER` | `SUPPORTING_EVIDENCE` / `RC_t:manual_control_availability` | uint16 failure bitmask | `EXACT` | `CONDITIONAL` | `baseline/px4/src/modules/mavlink/streams/HIGH_LATENCY2.hpp:484` |
| `RC_t` | `!(input_rc.rc_lost || input_rc.rc_failsafe)` | `PRIMARY_VALUE` / `RC_t:physical_receiver` | bool derived from receiver flags | `MODELLED` | `CONDITIONAL` | `baseline/px4/msg/InputRc.msg:29` |
| `RC_t` | `input_rc.timestamp_last_signal` | `SUPPORTING_EVIDENCE` / `RC_t:physical_receiver` | uint64 boot-time timestamp / microseconds since system start | `EXACT` | `INSTRUMENTATION_REQUIRED` | `baseline/px4/msg/InputRc.msg:22` |
| `RC_t` | `input_rc.input_source` | `SUPPORTING_EVIDENCE` / `RC_t:physical_receiver` | uint8 RC_INPUT_SOURCE enum | `EXACT` | `INSTRUMENTATION_REQUIRED` | `baseline/px4/msg/InputRc.msg:36` |
| `RC_t` | `input_rc.rc_lost` | `SUPPORTING_EVIDENCE` / `RC_t:physical_receiver` | bool receiver frame-loss state | `MODELLED` | `CONDITIONAL` | `baseline/px4/msg/InputRc.msg:30` |
| `Disarm` | `vehicle_status.arming_state == ARMING_STATE_DISARMED` | `PRIMARY_VALUE` / `Disarm:vehicle_arming_state` | uint8 enum comparison | `EXACT` | `DIRECT` | `baseline/px4/msg/versioned/VehicleStatus.msg:10` |
| `Disarm` | `vehicle_status_s::ARMING_STATE_DISARMED` | `SUPPORTING_EVIDENCE` / `Disarm:vehicle_arming_state` | uint8 value 1 | `EXACT` | `DIRECT` | `baseline/px4/msg/versioned/VehicleStatus.msg:11` |
| `Disarm` | `actuator_armed.armed == false` | `SUPPORTING_EVIDENCE` / `Disarm:vehicle_arming_state` | bool | `EXACT` | `DIRECT` | `baseline/px4/msg/ActuatorArmed.msg:3` |
| `Command_t` | `vehicle_command.command` | `PRIMARY_VALUE` / `Command_t:input_event` | uint32 command ID | `MODELLED` | `CONDITIONAL` | `baseline/px4/msg/versioned/VehicleCommand.msg:190` |
| `Command_t` | `vehicle_command.param1..param7,source_system,source_component` | `SUPPORTING_EVIDENCE` / `Command_t:input_event` | command envelope fields | `EXACT` | `CONDITIONAL` | `baseline/px4/msg/versioned/VehicleCommand.msg:183-196` |
| `Command_t` | `MavlinkReceiver::handle_message_command_long(): COMMAND_LONG -> vehicle_command` | `SUPPORTING_EVIDENCE` / `Command_t:input_event` | MAVLink command envelope to vehicle_command_s | `EXACT` | `CONDITIONAL` | `baseline/px4/src/modules/mavlink/mavlink_receiver.cpp:484-500` |
| `Command_t` | `MavlinkReceiver::handle_message_command_int(): COMMAND_INT -> vehicle_command` | `SUPPORTING_EVIDENCE` / `Command_t:input_event` | MAVLink command envelope to vehicle_command_s | `EXACT` | `CONDITIONAL` | `baseline/px4/src/modules/mavlink/mavlink_receiver.cpp:520-545` |
| `Command_t` | `MavlinkReceiver::handle_message_command_both(): publish vehicle_command` | `SUPPORTING_EVIDENCE` / `Command_t:input_event` | templated common command path | `EXACT` | `CONDITIONAL` | `baseline/px4/src/modules/mavlink/mavlink_receiver.cpp:548-753` |
| `Command_t` | `Commander::handle_command(): VEHICLE_CMD_NAV_TAKEOFF acceptance` | `ALTERNATIVE_SEMANTICS` / `Command_t:accepted_event` | vehicle_command_ack result | `EXACT` | `DIRECT` | `baseline/px4/src/modules/commander/Commander.cpp:1064` |
| `Command_t` | `Commander::answer_command(): publish vehicle_command_ack` | `SUPPORTING_EVIDENCE` / `Command_t:accepted_event` | vehicle_command_ack_s | `EXACT` | `DIRECT` | `baseline/px4/src/modules/commander/Commander.cpp:2673` |
| `Command_t` | `vehicle_status.nav_state == NAVIGATION_STATE_AUTO_TAKEOFF` | `ALTERNATIVE_SEMANTICS` / `Command_t:execution_state` | uint8 navigation state | `EXACT` | `DIRECT` | `baseline/px4/src/modules/navigator/navigator_main.cpp:799` |
| `takeoff` | `vehicle_command_s::VEHICLE_CMD_NAV_TAKEOFF` | `PRIMARY_VALUE` / `takeoff:primary` | uint16 value 22 | `EXACT` | `DIRECT` | `baseline/px4/msg/versioned/VehicleCommand.msg:17` |
| `Target_ALT` | `position_setpoint_triplet.current.alt` | `PRIMARY_VALUE` / `Target_ALT:amsl_navigator_setpoint` | float32 / m AMSL | `MODELLED` | `CONDITIONAL` | `baseline/px4/msg/PositionSetpoint.msg:24` |
| `Target_ALT` | `position_setpoint_triplet.current` | `SUPPORTING_EVIDENCE` / `Target_ALT:amsl_navigator_setpoint` | PositionSetpoint current container | `EXACT` | `INSTRUMENTATION_REQUIRED` | `baseline/px4/msg/PositionSetpointTriplet.msg:7` |
| `Target_ALT` | `rep->current.alt = cmd.param7` | `SUPPORTING_EVIDENCE` / `Target_ALT:amsl_navigator_setpoint` | float32 / m AMSL | `EXACT` | `CONDITIONAL` | `baseline/px4/src/modules/navigator/navigator_main.cpp:636` |
| `Target_ALT` | `position_setpoint_triplet.current.alt - home_position.alt` | `ALTERNATIVE_SEMANTICS` / `Target_ALT:relative_home` | float derived from two AMSL altitudes / m above Home | `MODELLED` | `DERIVED` | `baseline/px4/src/modules/mavlink/streams/POSITION_TARGET_GLOBAL_INT.hpp:75-84` |
| `Target_ALT` | `position_setpoint_triplet.current.alt - captured takeoff-reference altitude` | `ALTERNATIVE_SEMANTICS` / `Target_ALT:relative_takeoff_reference` | trace-derived float / m above takeoff reference | `MODELLED` | `DERIVED` | `baseline/px4/src/modules/navigator/takeoff.cpp:188-199` |
| `GPS_loss` | `sensor_gps.timestamp,fix_type` | `PRIMARY_VALUE` / `GPS_loss:primary` | uint64 time plus uint8 enum | `MODELLED` | `DIRECT` | `baseline/px4/msg/SensorGps.msg:3` |
| `GPS_loss` | `sensor_gps.fix_type` | `SUPPORTING_EVIDENCE` / `GPS_loss:primary` | uint8 fix enum | `MODELLED` | `DIRECT` | `baseline/px4/msg/SensorGps.msg:22` |
| `GPS_fail` | `failsafe_flags.global_position_invalid` | `PRIMARY_VALUE` / `GPS_fail:global_position_invalid` | bool | `MODELLED` | `INSTRUMENTATION_REQUIRED` | `baseline/px4/msg/FailsafeFlags.msg:32` |
| `GPS_fail` | `global_position_invalid = !checkPosVelValidity(...) ` | `SUPPORTING_EVIDENCE` / `GPS_fail:global_position_invalid` | bool | `MODELLED` | `CONDITIONAL` | `baseline/px4/src/modules/commander/HealthAndArmingChecks/checks/estimatorCheck.cpp:681` |
| `k` | `no current PX4 symbol` | `PRIMARY_VALUE` / `k:primary` | 未定义 | `UNRESOLVED` | `UNRESOLVED` | `无当前位置` |
| `RTL_RETURN_ALT` | `RTL_RETURN_ALT` | `PRIMARY_VALUE` / `RTL_RETURN_ALT:primary` | float32 / m above selected RTL destination | `EXACT` | `DIRECT` | `baseline/px4/src/modules/navigator/rtl_params.c:59` |
| `RTL_DESCEND_ALT` | `RTL_DESCEND_ALT` | `PRIMARY_VALUE` / `RTL_DESCEND_ALT:primary` | float32 / m above selected RTL destination | `EXACT` | `DIRECT` | `baseline/px4/src/modules/navigator/rtl_params.c:75` |
| `RTL_LAND_DELAY` | `RTL_LAND_DELAY` | `PRIMARY_VALUE` / `RTL_LAND_DELAY:primary` | float32 / s | `EXACT` | `DIRECT` | `baseline/px4/src/modules/navigator/rtl_params.c:89` |
| `MPC_LAND_SPEED` | `MPC_LAND_SPEED` | `PRIMARY_VALUE` / `MPC_LAND_SPEED:primary` | float32 / m/s down-rate magnitude | `EXACT` | `DIRECT` | `baseline/px4/src/modules/mc_pos_control/multicopter_takeoff_land_params.c:111` |
| `MIS_LTRMIN_ALT` | `NAV_MIN_LTR_ALT` | `PRIMARY_VALUE` / `MIS_LTRMIN_ALT:primary` | float32 / m above Home | `MODELLED` | `DIRECT` | `baseline/px4/src/modules/navigator/navigator_params.c:192` |
| `MIS_TAKEOFF_ALT` | `MIS_TAKEOFF_ALT` | `PRIMARY_VALUE` / `MIS_TAKEOFF_ALT:primary` | float32 / m relative takeoff altitude | `EXACT` | `DIRECT` | `baseline/px4/src/modules/navigator/mission_params.c:58` |
| `MPC_TKO_SPEED` | `MPC_TKO_SPEED` | `PRIMARY_VALUE` / `MPC_TKO_SPEED:primary` | float32 / m/s up-rate magnitude | `EXACT` | `DIRECT` | `baseline/px4/src/modules/mc_pos_control/multicopter_takeoff_land_params.c:57` |
| `RTL_RETURN_ALT` | `RTL::_param_rtl_return_alt` | `SUPPORTING_EVIDENCE` / `RTL_RETURN_ALT:primary` | ParamFloat class member | `EXACT` | `DIRECT` | `baseline/px4/src/modules/navigator/rtl.h:236` |
| `RTL_DESCEND_ALT` | `RtlDirect::_param_rtl_descend_alt` | `SUPPORTING_EVIDENCE` / `RTL_DESCEND_ALT:primary` | ParamFloat class member | `EXACT` | `DIRECT` | `baseline/px4/src/modules/navigator/rtl_direct.h:176` |
| `RTL_LAND_DELAY` | `RtlDirect::_param_rtl_land_delay` | `SUPPORTING_EVIDENCE` / `RTL_LAND_DELAY:primary` | ParamFloat class member | `EXACT` | `DIRECT` | `baseline/px4/src/modules/navigator/rtl_direct.h:177` |
| `MPC_LAND_SPEED` | `FlightTaskAuto::_param_mpc_land_speed` | `SUPPORTING_EVIDENCE` / `MPC_LAND_SPEED:primary` | ParamFloat class member | `EXACT` | `DIRECT` | `baseline/px4/src/modules/flight_mode_manager/tasks/Auto/FlightTaskAuto.hpp:169` |
| `MPC_TKO_SPEED` | `FlightTaskAuto::_param_mpc_tko_speed` | `SUPPORTING_EVIDENCE` / `MPC_TKO_SPEED:primary` | ParamFloat class member | `EXACT` | `DIRECT` | `baseline/px4/src/modules/flight_mode_manager/tasks/Auto/FlightTaskAuto.hpp:178` |
| `MIS_LTRMIN_ALT` | `Navigator::_param_min_ltr_alt` | `SUPPORTING_EVIDENCE` / `MIS_LTRMIN_ALT:primary` | ParamFloat class member | `MODELLED` | `DIRECT` | `baseline/px4/src/modules/navigator/navigator.h:437` |
| `MIS_TAKEOFF_ALT` | `Navigator::_param_mis_takeoff_alt` | `SUPPORTING_EVIDENCE` / `MIS_TAKEOFF_ALT:primary` | ParamFloat class member | `EXACT` | `DIRECT` | `baseline/px4/src/modules/navigator/navigator.h:442` |
| `RTL_RETURN_ALT` | `_param_rtl_return_alt.get()` | `SUPPORTING_EVIDENCE` / `RTL_RETURN_ALT:primary` | runtime parameter value consumed by control/navigation logic | `EXACT` | `INSTRUMENTATION_REQUIRED` | `baseline/px4/src/modules/navigator/rtl.cpp:477` |
| `RTL_RETURN_ALT` | `_param_rtl_return_alt.get()` | `SUPPORTING_EVIDENCE` / `RTL_RETURN_ALT:primary` | runtime parameter value consumed by control/navigation logic | `EXACT` | `INSTRUMENTATION_REQUIRED` | `baseline/px4/src/modules/navigator/rtl.cpp:530` |
| `RTL_DESCEND_ALT` | `_param_rtl_descend_alt.get()` | `SUPPORTING_EVIDENCE` / `RTL_DESCEND_ALT:primary` | runtime parameter value consumed by control/navigation logic | `EXACT` | `INSTRUMENTATION_REQUIRED` | `baseline/px4/src/modules/navigator/rtl_direct.cpp:587` |
| `RTL_LAND_DELAY` | `_param_rtl_land_delay.get()` | `SUPPORTING_EVIDENCE` / `RTL_LAND_DELAY:primary` | runtime parameter value consumed by control/navigation logic | `EXACT` | `INSTRUMENTATION_REQUIRED` | `baseline/px4/src/modules/navigator/rtl_direct.cpp:166` |
| `RTL_LAND_DELAY` | `_param_rtl_land_delay.get()` | `SUPPORTING_EVIDENCE` / `RTL_LAND_DELAY:primary` | runtime parameter value consumed by control/navigation logic | `EXACT` | `INSTRUMENTATION_REQUIRED` | `baseline/px4/src/modules/navigator/rtl_direct.cpp:307` |
| `RTL_LAND_DELAY` | `_param_rtl_land_delay.get() < -FLT_EPSILON` | `SUPPORTING_EVIDENCE` / `RTL_LAND_DELAY:primary` | runtime parameter value consumed by control/navigation logic | `EXACT` | `INSTRUMENTATION_REQUIRED` | `baseline/px4/src/modules/navigator/rtl_direct.cpp:309` |
| `MPC_LAND_SPEED` | `_param_mpc_land_speed.get()` | `SUPPORTING_EVIDENCE` / `MPC_LAND_SPEED:primary` | runtime parameter value consumed by control/navigation logic | `EXACT` | `INSTRUMENTATION_REQUIRED` | `baseline/px4/src/modules/flight_mode_manager/tasks/Auto/FlightTaskAuto.cpp:234` |
| `MPC_LAND_SPEED` | `_param_mpc_land_speed.get()` | `SUPPORTING_EVIDENCE` / `MPC_LAND_SPEED:primary` | runtime parameter value consumed by control/navigation logic | `EXACT` | `INSTRUMENTATION_REQUIRED` | `baseline/px4/src/modules/flight_mode_manager/tasks/Descend/FlightTaskDescend.cpp:52` |
| `MPC_TKO_SPEED` | `_param_mpc_tko_speed.get()` | `SUPPORTING_EVIDENCE` / `MPC_TKO_SPEED:primary` | runtime parameter value consumed by control/navigation logic | `EXACT` | `INSTRUMENTATION_REQUIRED` | `baseline/px4/src/modules/flight_mode_manager/tasks/Auto/FlightTaskAuto.cpp:812` |
| `MIS_TAKEOFF_ALT` | `Navigator::get_param_mis_takeoff_alt()` | `SUPPORTING_EVIDENCE` / `MIS_TAKEOFF_ALT:primary` | runtime parameter value consumed by control/navigation logic | `EXACT` | `INSTRUMENTATION_REQUIRED` | `baseline/px4/src/modules/navigator/takeoff.cpp:188` |
| `MIS_LTRMIN_ALT` | `Navigator::get_loiter_min_alt()` | `SUPPORTING_EVIDENCE` / `MIS_LTRMIN_ALT:primary` | runtime parameter value consumed by control/navigation logic | `MODELLED` | `INSTRUMENTATION_REQUIRED` | `baseline/px4/src/modules/navigator/mission_block.cpp:727` |
| `COM_POS_FS_DELAY` | `COM_POS_FS_DELAY` | `PRIMARY_VALUE` / `COM_POS_FS_DELAY:primary` | removed seconds parameter | `UNRESOLVED` | `UNRESOLVED` | `baseline/px4/docs/en/releases/1.16.md:58` |
| `COM_POS_FS_DELAY` | `EKF2_NOAID_TOUT` | `ALTERNATIVE_SEMANTICS` / `COM_POS_FS_DELAY:ekf2_noaid_tout_non_equivalent` | int32 microseconds parameter / us maximum inertial dead-reckoning time | `UNRESOLVED` | `DIRECT` | `baseline/px4/src/modules/ekf2/module.yaml:76` |
| `COM_POS_FS_DELAY` | `COM_POS_FS_EPH` | `ALTERNATIVE_SEMANTICS` / `COM_POS_FS_DELAY:com_pos_fs_eph_non_equivalent` | float32 accuracy threshold / m horizontal position uncertainty | `UNRESOLVED` | `DIRECT` | `baseline/px4/src/modules/commander/commander_params.c:538` |
| `COM_POS_FS_DELAY` | `EstimatorChecks::setModeRequirementFlags(): _param_com_pos_fs_eph.get()` | `ALTERNATIVE_SEMANTICS` / `COM_POS_FS_DELAY:com_pos_fs_eph_non_equivalent` | float position-accuracy threshold comparison / m EPH threshold | `UNRESOLVED` | `INSTRUMENTATION_REQUIRED` | `baseline/px4/src/modules/commander/HealthAndArmingChecks/checks/estimatorCheck.cpp:664` |
| `COM_POS_FS_DELAY` | `Ekf::updateHorizontalDeadReckoningstatus(): _params.ekf2_noaid_tout` | `ALTERNATIVE_SEMANTICS` / `COM_POS_FS_DELAY:ekf2_noaid_tout_non_equivalent` | uint64 timeout comparison / microseconds since last horizontal aiding | `UNRESOLVED` | `INSTRUMENTATION_REQUIRED` | `baseline/px4/src/modules/ekf2/EKF/ekf_helper.cpp:880` |

### PX4 原子命题绑定状态

| 性质 | AP | 原子命题 | 语义组选择 | 状态 | 观测 | 判定说明 |
|---|---|---|---|---|---|---|
| `PX.RTL1` | `PX.RTL1-AP01` | `ALT_t < RTL_RETURN_ALT` | `PRIMARY_WITH_ALTERNATIVES` | `MODELLED` | `INSTRUMENTATION_REQUIRED` | 需要历史样本、坐标/单位换算、有效性条件、容差或上下文选择。 |
| `PX.RTL1` | `PX.RTL1-AP02` | `Mode_t = RTL` | `PRIMARY_SELECTED` | `EXACT` | `DIRECT` | 本原子命题可按列出的当前枚举、布尔状态或参数值直接判真。 |
| `PX.RTL1` | `PX.RTL1-AP03` | `ALT_t-1 < ALT_t` | `PRIMARY_WITH_ALTERNATIVES` | `MODELLED` | `INSTRUMENTATION_REQUIRED` | 需要历史样本、坐标/单位换算、有效性条件、容差或上下文选择。 |
| `PX.RTL2` | `PX.RTL2-AP01` | `Mode_t = RTL` | `PRIMARY_SELECTED` | `EXACT` | `DIRECT` | 本原子命题可按列出的当前枚举、布尔状态或参数值直接判真。 |
| `PX.RTL2` | `PX.RTL2-AP02` | `ALT_t >= RTL_RETURN_ALT` | `PRIMARY_WITH_ALTERNATIVES` | `MODELLED` | `INSTRUMENTATION_REQUIRED` | 需要历史样本、坐标/单位换算、有效性条件、容差或上下文选择。 |
| `PX.RTL2` | `PX.RTL2-AP03` | `Pos_t != home_position` | `PRIMARY_WITH_ALTERNATIVES` | `MODELLED` | `DIRECT` | 需要历史样本、坐标/单位换算、有效性条件、容差或上下文选择。 |
| `PX.RTL2` | `PX.RTL2-AP04` | `Pos_t-1 != Pos_t` | `PRIMARY_WITH_ALTERNATIVES` | `MODELLED` | `DERIVED` | 需要历史样本、坐标/单位换算、有效性条件、容差或上下文选择。 |
| `PX.RTL2` | `PX.RTL2-AP05` | `ALT_t-1 = ALT_t` | `PRIMARY_WITH_ALTERNATIVES` | `MODELLED` | `INSTRUMENTATION_REQUIRED` | 需要历史样本、坐标/单位换算、有效性条件、容差或上下文选择。 |
| `PX.RTL3` | `PX.RTL3-AP01` | `Mode_t = RTL` | `PRIMARY_SELECTED` | `EXACT` | `DIRECT` | 本原子命题可按列出的当前枚举、布尔状态或参数值直接判真。 |
| `PX.RTL3` | `PX.RTL3-AP02` | `ALT_t >= RTL_RETURN_ALT` | `PRIMARY_WITH_ALTERNATIVES` | `MODELLED` | `INSTRUMENTATION_REQUIRED` | 需要历史样本、坐标/单位换算、有效性条件、容差或上下文选择。 |
| `PX.RTL3` | `PX.RTL3-AP03` | `Pos_t = home_position` | `PRIMARY_WITH_ALTERNATIVES` | `MODELLED` | `DIRECT` | 需要历史样本、坐标/单位换算、有效性条件、容差或上下文选择。 |
| `PX.RTL3` | `PX.RTL3-AP04` | `Mode_t = LAND` | `PRIMARY_SELECTED` | `EXACT` | `DIRECT` | 本原子命题可按列出的当前枚举、布尔状态或参数值直接判真。 |
| `PX.RTL4` | `PX.RTL4-AP01` | `Mode_t = RTL` | `PRIMARY_SELECTED` | `MODELLED` | `DIRECT` | 命题实体可定位，但所在性质存在论文公式冲突，不能据此修复整条公式。 |
| `PX.RTL4` | `PX.RTL4-AP02` | `RTL_DESCEND_ALT = -1` | `PRIMARY_SELECTED` | `MODELLED` | `DIRECT` | 命题实体可定位，但所在性质存在论文公式冲突，不能据此修复整条公式。 |
| `PX.RTL4` | `PX.RTL4-AP03` | `RTL_LAND_DELAY = -1` | `PRIMARY_SELECTED` | `MODELLED` | `DIRECT` | 命题实体可定位，但所在性质存在论文公式冲突，不能据此修复整条公式。 |
| `PX.RTL4` | `PX.RTL4-AP04` | `Pos_t = Pos_t-1` | `PRIMARY_WITH_ALTERNATIVES` | `MODELLED` | `DERIVED` | 需要历史样本、坐标/单位换算、有效性条件、容差或上下文选择。 |
| `PX.RTL4` | `PX.RTL4-AP05` | `ALT_t-1 = ALT_t` | `PRIMARY_WITH_ALTERNATIVES` | `MODELLED` | `INSTRUMENTATION_REQUIRED` | 需要历史样本、坐标/单位换算、有效性条件、容差或上下文选择。 |
| `PX.RTL5` | `PX.RTL5-AP01` | `Mode_t = LAND` | `PRIMARY_SELECTED` | `EXACT` | `DIRECT` | 本原子命题可按列出的当前枚举、布尔状态或参数值直接判真。 |
| `PX.RTL5` | `PX.RTL5-AP02` | `ALT_t = GroundALT` | `UNRESOLVED_PRIMARY` | `UNRESOLVED` | `UNRESOLVED` | 论文未定义 GroundALT 是数值高度、Home 高度、地形高度还是已落地状态；类型和参考面补证前不判真值。 |
| `PX.RTL5` | `PX.RTL5-AP03` | `Disarm = on` | `PRIMARY_SELECTED` | `EXACT` | `DIRECT` | 本原子命题可按列出的当前枚举、布尔状态或参数值直接判真。 |
| `PX.ORBIT1` | `PX.ORBIT1-AP01` | `Mode_t = ORBIT` | `PRIMARY_SELECTED` | `EXACT` | `DIRECT` | 本原子命题可按列出的当前枚举、布尔状态或参数值直接判真。 |
| `PX.ORBIT1` | `PX.ORBIT1-AP02` | `RC_pitch < 1500` | `PRIMARY_WITH_ALTERNATIVES` | `MODELLED` | `CONDITIONAL` | 需要历史样本、坐标/单位换算、有效性条件、容差或上下文选择。 |
| `PX.ORBIT1` | `PX.ORBIT1-AP03` | `Circle_radius_t > 0` | `PRIMARY_SELECTED` | `MODELLED` | `INSTRUMENTATION_REQUIRED` | 需要历史样本、坐标/单位换算、有效性条件、容差或上下文选择。 |
| `PX.ORBIT1` | `PX.ORBIT1-AP04` | `Circle_radius_t < Circle_radius_t-1` | `PRIMARY_SELECTED` | `MODELLED` | `INSTRUMENTATION_REQUIRED` | 需要历史样本、坐标/单位换算、有效性条件、容差或上下文选择。 |
| `PX.ORBIT2` | `PX.ORBIT2-AP01` | `Mode_t = ORBIT` | `PRIMARY_SELECTED` | `EXACT` | `DIRECT` | 本原子命题可按列出的当前枚举、布尔状态或参数值直接判真。 |
| `PX.ORBIT2` | `PX.ORBIT2-AP02` | `RC_pitch > 1500` | `PRIMARY_WITH_ALTERNATIVES` | `MODELLED` | `CONDITIONAL` | 需要历史样本、坐标/单位换算、有效性条件、容差或上下文选择。 |
| `PX.ORBIT2` | `PX.ORBIT2-AP03` | `Circle_radius_t > Circle_radius_t-1` | `PRIMARY_SELECTED` | `MODELLED` | `INSTRUMENTATION_REQUIRED` | 需要历史样本、坐标/单位换算、有效性条件、容差或上下文选择。 |
| `PX.ORBIT3` | `PX.ORBIT3-AP01` | `Mode_t = ORBIT` | `PRIMARY_SELECTED` | `EXACT` | `DIRECT` | 本原子命题可按列出的当前枚举、布尔状态或参数值直接判真。 |
| `PX.ORBIT3` | `PX.ORBIT3-AP02` | `RC_roll > 1500` | `PRIMARY_WITH_ALTERNATIVES` | `MODELLED` | `CONDITIONAL` | 需要历史样本、坐标/单位换算、有效性条件、容差或上下文选择。 |
| `PX.ORBIT3` | `PX.ORBIT3-AP03` | `Circle_direction_t = clockwise` | `PRIMARY_WITH_ALTERNATIVES` | `MODELLED` | `DIRECT` | 需要历史样本、坐标/单位换算、有效性条件、容差或上下文选择。 |
| `PX.ORBIT3` | `PX.ORBIT3-AP04` | `Circle_speed_t > Circle_speed_t-1` | `PRIMARY_WITH_ALTERNATIVES` | `MODELLED` | `INSTRUMENTATION_REQUIRED` | 需要历史样本、坐标/单位换算、有效性条件、容差或上下文选择。 |
| `PX.ORBIT4` | `PX.ORBIT4-AP01` | `Mode_t = ORBIT` | `PRIMARY_SELECTED` | `EXACT` | `DIRECT` | 本原子命题可按列出的当前枚举、布尔状态或参数值直接判真。 |
| `PX.ORBIT4` | `PX.ORBIT4-AP02` | `RC_roll > 1500` | `PRIMARY_WITH_ALTERNATIVES` | `MODELLED` | `CONDITIONAL` | 需要历史样本、坐标/单位换算、有效性条件、容差或上下文选择。 |
| `PX.ORBIT4` | `PX.ORBIT4-AP03` | `Circle_direction_t = counterclockwise` | `PRIMARY_WITH_ALTERNATIVES` | `MODELLED` | `DIRECT` | 需要历史样本、坐标/单位换算、有效性条件、容差或上下文选择。 |
| `PX.ORBIT4` | `PX.ORBIT4-AP04` | `Circle_speed_t < Circle_speed_t-1` | `PRIMARY_WITH_ALTERNATIVES` | `MODELLED` | `INSTRUMENTATION_REQUIRED` | 需要历史样本、坐标/单位换算、有效性条件、容差或上下文选择。 |
| `PX.ORBIT5` | `PX.ORBIT5-AP01` | `Mode_t = ORBIT` | `PRIMARY_SELECTED` | `EXACT` | `DIRECT` | 本原子命题可按列出的当前枚举、布尔状态或参数值直接判真。 |
| `PX.ORBIT5` | `PX.ORBIT5-AP02` | `Circle_radius_t < 100m` | `PRIMARY_SELECTED` | `MODELLED` | `INSTRUMENTATION_REQUIRED` | 需要历史样本、坐标/单位换算、有效性条件、容差或上下文选择。 |
| `PX.ORBIT6` | `PX.ORBIT6-AP01` | `Mode_t = ORBIT` | `PRIMARY_SELECTED` | `MODELLED` | `DIRECT` | 命题实体可定位，但所在性质存在论文公式冲突，不能据此修复整条公式。 |
| `PX.ORBIT6` | `PX.ORBIT6-AP02` | `Circle_speed_t < 2m/s^2` | `PRIMARY_WITH_ALTERNATIVES` | `MODELLED` | `INSTRUMENTATION_REQUIRED` | 需要历史样本、坐标/单位换算、有效性条件、容差或上下文选择。 |
| `PX.LAND1` | `PX.LAND1-AP01` | `Mode_t = LAND` | `PRIMARY_SELECTED` | `EXACT` | `DIRECT` | 本原子命题可按列出的当前枚举、布尔状态或参数值直接判真。 |
| `PX.LAND1` | `PX.LAND1-AP02` | `Speed_vertical_t = MPC_LAND_SPEED` | `PRIMARY_SELECTED` | `MODELLED` | `DIRECT` | 需要历史样本、坐标/单位换算、有效性条件、容差或上下文选择。 |
| `PX.ALTITUDE1` | `PX.ALTITUDE1-AP01` | `Mode_t = ALTITUDE` | `PRIMARY_SELECTED` | `EXACT` | `DIRECT` | 本原子命题可按列出的当前枚举、布尔状态或参数值直接判真。 |
| `PX.ALTITUDE1` | `PX.ALTITUDE1-AP02` | `Throttle_t = 1500` | `PRIMARY_WITH_ALTERNATIVES` | `MODELLED` | `CONDITIONAL` | 需要历史样本、坐标/单位换算、有效性条件、容差或上下文选择。 |
| `PX.ALTITUDE1` | `PX.ALTITUDE1-AP03` | `ALT_t-1 = ALT_t` | `PRIMARY_WITH_ALTERNATIVES` | `MODELLED` | `CONDITIONAL` | 需要历史样本、坐标/单位换算、有效性条件、容差或上下文选择。 |
| `PX.POSITION1` | `PX.POSITION1-AP01` | `Mode_t = POSITION` | `PRIMARY_SELECTED` | `EXACT` | `DIRECT` | 本原子命题可按列出的当前枚举、布尔状态或参数值直接判真。 |
| `PX.POSITION1` | `PX.POSITION1-AP02` | `Pos_t = Pos_t-1` | `PRIMARY_WITH_ALTERNATIVES` | `MODELLED` | `DERIVED` | 需要历史样本、坐标/单位换算、有效性条件、容差或上下文选择。 |
| `PX.HOLD1` | `PX.HOLD1-AP01` | `Mode_t = HOLD` | `PRIMARY_SELECTED` | `EXACT` | `DIRECT` | 本原子命题可按列出的当前枚举、布尔状态或参数值直接判真。 |
| `PX.HOLD1` | `PX.HOLD1-AP02` | `Pos_t = Pos_t-1` | `PRIMARY_WITH_ALTERNATIVES` | `MODELLED` | `DERIVED` | 需要历史样本、坐标/单位换算、有效性条件、容差或上下文选择。 |
| `PX.HOLD1` | `PX.HOLD1-AP03` | `Yaw_t = Yaw_t-1` | `PRIMARY_SELECTED` | `MODELLED` | `DERIVED` | 需要历史样本、坐标/单位换算、有效性条件、容差或上下文选择。 |
| `PX.HOLD1` | `PX.HOLD1-AP04` | `ALT_t-1 = ALT_t` | `PRIMARY_WITH_ALTERNATIVES` | `MODELLED` | `CONDITIONAL` | 需要历史样本、坐标/单位换算、有效性条件、容差或上下文选择。 |
| `PX.HOLD2` | `PX.HOLD2-AP01` | `Mode_t = HOLD` | `PRIMARY_SELECTED` | `EXACT` | `DIRECT` | 本原子命题可按列出的当前枚举、布尔状态或参数值直接判真。 |
| `PX.HOLD2` | `PX.HOLD2-AP02` | `MIS_LTRMIN_ALT != -1` | `PRIMARY_SELECTED` | `MODELLED` | `DIRECT` | 需要历史样本、坐标/单位换算、有效性条件、容差或上下文选择。 |
| `PX.HOLD2` | `PX.HOLD2-AP03` | `ALT_t < MIS_LTRMIN_ALT` | `PRIMARY_WITH_ALTERNATIVES` | `MODELLED` | `CONDITIONAL` | 需要历史样本、坐标/单位换算、有效性条件、容差或上下文选择。 |
| `PX.HOLD2` | `PX.HOLD2-AP04` | `ALT_t-1 < ALT_t` | `PRIMARY_WITH_ALTERNATIVES` | `MODELLED` | `CONDITIONAL` | 需要历史样本、坐标/单位换算、有效性条件、容差或上下文选择。 |
| `PX.HOLD2` | `PX.HOLD2-AP05` | `Target_ALT = MIS_LTRMIN_ALT` | `PRIMARY_WITH_ALTERNATIVES` | `MODELLED` | `DERIVED` | 需要历史样本、坐标/单位换算、有效性条件、容差或上下文选择。 |
| `PX.TAKEOFF1` | `PX.TAKEOFF1-AP01` | `Command_t = takeoff` | `PRIMARY_WITH_ALTERNATIVES` | `MODELLED` | `CONDITIONAL` | 需要历史样本、坐标/单位换算、有效性条件、容差或上下文选择。 |
| `PX.TAKEOFF1` | `PX.TAKEOFF1-AP02` | `ALT_t <= MIS_TAKEOFF_ALT` | `PRIMARY_WITH_ALTERNATIVES` | `MODELLED` | `DERIVED` | 需要历史样本、坐标/单位换算、有效性条件、容差或上下文选择。 |
| `PX.TAKEOFF1` | `PX.TAKEOFF1-AP03` | `Target_ALT = MIS_TAKEOFF_ALT` | `PRIMARY_WITH_ALTERNATIVES` | `MODELLED` | `DERIVED` | 需要历史样本、坐标/单位换算、有效性条件、容差或上下文选择。 |
| `PX.TAKEOFF2` | `PX.TAKEOFF2-AP01` | `Command_t = takeoff` | `PRIMARY_WITH_ALTERNATIVES` | `MODELLED` | `CONDITIONAL` | 需要历史样本、坐标/单位换算、有效性条件、容差或上下文选择。 |
| `PX.TAKEOFF2` | `PX.TAKEOFF2-AP02` | `Speed_vertical_t = MPC_TKO_SPEED` | `PRIMARY_SELECTED` | `MODELLED` | `DIRECT` | 需要历史样本、坐标/单位换算、有效性条件、容差或上下文选择。 |
| `PX.GPS.FS1` | `PX.GPS.FS1-AP01` | `GPS_loss = on` | `PRIMARY_SELECTED` | `MODELLED` | `DIRECT` | 需要历史样本、坐标/单位换算、有效性条件、容差或上下文选择。 |
| `PX.GPS.FS1` | `PX.GPS.FS1-AP02` | `F_[0,COM_POS_FS_DELAY+k](GPS_fail = on)` | `UNRESOLVED_PRIMARY` | `UNRESOLVED` | `UNRESOLVED` | 包含未公开时间上界、未定义航点空状态或已删除且无等价替代的参数。 |
| `PX.GPS.FS2` | `PX.GPS.FS2-AP01` | `GPS_fail = on` | `UNRESOLVED_PRIMARY` | `UNRESOLVED` | `UNRESOLVED` | 论文 GPS_fail 与当前位置/EKF 故障状态没有精确等价证据。 |
| `PX.GPS.FS2` | `PX.GPS.FS2-AP02` | `RC_t = on` | `PRIMARY_WITH_ALTERNATIVES` | `MODELLED` | `CONDITIONAL` | 需要历史样本、坐标/单位换算、有效性条件、容差或上下文选择。 |
| `PX.GPS.FS2` | `PX.GPS.FS2-AP03` | `Mode_t = ALTITUDE` | `PRIMARY_SELECTED` | `EXACT` | `DIRECT` | 本原子命题可按列出的当前枚举、布尔状态或参数值直接判真。 |
| `PX.GPS.FS3` | `PX.GPS.FS3-AP01` | `GPS_fail = on` | `UNRESOLVED_PRIMARY` | `UNRESOLVED` | `UNRESOLVED` | 论文 GPS_fail 与当前位置/EKF 故障状态没有精确等价证据。 |
| `PX.GPS.FS3` | `PX.GPS.FS3-AP02` | `RC_t = off` | `PRIMARY_WITH_ALTERNATIVES` | `MODELLED` | `CONDITIONAL` | 需要历史样本、坐标/单位换算、有效性条件、容差或上下文选择。 |
| `PX.GPS.FS3` | `PX.GPS.FS3-AP03` | `Mode_t = LAND` | `PRIMARY_SELECTED` | `EXACT` | `DIRECT` | 本原子命题可按列出的当前枚举、布尔状态或参数值直接判真。 |

## 四、审核边界

绑定为 `EXACT` 只说明该原子命题的局部字段或枚举身份可精确判定，不说明整条时序性质正确，也不说明固件满足它。参数默认值、当前运行值和作者历史值分别保存；运行中能否修改及何时生效尚未逐参数写入验证。

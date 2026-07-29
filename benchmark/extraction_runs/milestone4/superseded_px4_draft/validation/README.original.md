# PX4 草案验证

`validate_px4_artifacts.py` 只做静态一致性检查：YAML/CSV 可解析、候选 ID 唯一、AP/OBS 引用存在、冻结语料
SHA-256 和行数仍一致、源码锚点未越界，以及所有候选保持 `NOT_ASSESSED`/`NOT_VALIDATED`。

运行：

```sh
python3 benchmark/PX4/validation/validate_px4_artifacts.py
```

脚本依赖 PyYAML。本轮验证不等于 MITL 语法验证、轨迹验证或 SITL 判定；这些三项在每个性质文件中仍为
`NOT_RUN`。脚本是只读的，不修改冻结仓库或 benchmark 文件。

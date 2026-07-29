# FGS FSE 2024 工件复现记录

## 结论

复现状态为 `BLOCKED_UPSTREAM_ARTIFACT_UNAVAILABLE`，不是成功复现。

2026-07-18 获取的 [Zenodo 12770067](https://zenodo.org/records/12770067)
公开记录只含一页 `README.pdf`。该文档将全部可执行内容和源码放在
`rmrepo/fgs:latest` Docker 镜像中，但 Docker Hub 当前对该仓库返回 HTTP
404，registry 对 `latest` manifest 返回 `UNAUTHORIZED`。因此无法获得镜像
digest、`/root/Reproduce/fgs`、`test.ll`、源码或 NIST 用例，作者给出的 smoke
和 846 例 NIST 实验均未运行。

本记录没有重实现 FGS，也没有把其他 SVF 分析器冒充成原始工件。FGS 可以继续
作为论文方法和预期结果对照，但在镜像或官方源码恢复以前，不能作为 RIFT 的已执行
runtime baseline。

机器上的 Docker Desktop Linux engine 同时没有启动，但这不是主阻塞：使用独立
registry 客户端绕过 Docker daemon 后，官方镜像仍无法解析。

## 已冻结材料

| 材料 | 来源 | 大小 | SHA-256 |
|---|---|---:|---|
| `external/fgs/README.pdf` | Zenodo 12770067 唯一用户文件 | 374,218 B | `bcb3f26337e3cb265f00041ef991dd0beec3d08f3275c9c01f9735c25656823a` |
| `external/fgs/zenodo-record-12770067.json` | Zenodo API 元数据快照 | 4,588 B | `533ebaf6ec5e08d7ed2b5a106987bf39265f90569fcfbe3fda5a81d1017b0d32` |
| `external/fgs/fse24a.pdf` | 作者公开论文 PDF | 1,060,212 B | `c6b40cac82794586edfa1d87b395075acc0c7733d6243116f01ab3091dff3e18` |

Zenodo 对 README 给出的 MD5 是
`d8215b6bdd9fb6ad3c9862ff0f4e9dac`，本地下载与之相符。完整机器可读记录见
`artifact_manifest.json`。

## 官方执行契约

README 只规定了以下流程：

```sh
docker pull rmrepo/fgs:latest
docker run -dit --name FGS rmrepo/fgs bash
docker exec -it FGS bash
cd /root/Reproduce
./fgs test.ll
```

预期 smoke 结果是在输出末尾报告一个 use-after-free bug。自定义输入接口为：

```sh
/root/Reproduce/fgs BITCODE_PATH
```

文档声称源码位于 `/root/FGS/src`，但 Zenodo 没有独立上传该源码。文档也没有提供
批量运行 846 个 NIST 程序的命令、预期逐例结果或镜像 digest。

论文报告的原实验环境是 Ubuntu 18.04、8 核 2.60 GHz Intel Xeon、128 GiB
内存和 LLVM 14.0.0。论文表 5 报告 NIST 四类共 846 例全部为 TP、0 FP；这些是
论文中的预期值，不是本次观测值。

## 实际检查及证据

### 1. Zenodo 内容与历史版本

```sh
curl -fsSL https://zenodo.org/api/records/12770067/files
curl -fsSL https://zenodo.org/api/records/12770067/versions
```

观测结果：

- 当前公开记录恰好一个用户文件 `README.pdf`；
- concept record 共有五个版本；
- 其余四个版本没有公开文件，且较早版本为 restricted；
- 论文参考文献给出的 11077099 已指向 12770067。

证据：`raw/zenodo-files.json`、`raw/zenodo-versions.json`。

### 2. Docker Hub 与 OCI registry

```sh
crane digest rmrepo/fgs:latest
curl https://hub.docker.com/v2/repositories/rmrepo/fgs/
```

观测结果：

- `crane digest` 退出码 1；registry 的 HEAD/GET 均返回
  `UNAUTHORIZED: authentication required`；
- Docker Hub repository API 返回 HTTP 404 和 `object not found`；
- 另用匿名 pull token 直接请求 registry manifest，token endpoint 为 200，
  manifest 仍为 401。

证据：`raw/crane-digest.*`、`raw/dockerhub-repository.*` 和
`raw/registry-anonymous-manifest.txt`。证据文件没有保存 registry token 或本地
credential。

### 3. 作者说明中的 SVF 合并去向

Zenodo 说明称工件将合并入 [SVF](https://github.com/SVF-tools/SVF)。检查当时的
SVF `master` commit `ef219315275384b545aae338ed95e5c2b202d814` 完整 tree，
没有匹配 FGS、PSTA、tempo-spatial 或 multi-point slicing 的路径。这里仅证明
指定 commit 的 tree 中没有可识别实现，不能证明作者从未在其他私有或历史分支
保存代码。

证据：`raw/svf-master-search.txt`。

### 4. 本地执行环境

本机为 Ubuntu 22.04.5 WSL2，约 15 GiB RAM、4 GiB swap、32 个逻辑 CPU；
可用 Clang/LLVM 18.1.8。任务资源上限为 12 GiB RSS 和 24 小时。Docker Desktop
客户端存在但 engine 未运行。由于镜像在 registry 端不可取得，未消耗资源尝试
smoke 或 NIST，更没有用本机 LLVM 18 替代镜像中的 LLVM 14。

证据：`raw/environment.txt` 和 `raw/docker-desktop-version.*`。

## 对 RIFT 比较实验的处理

在主实验表中必须这样记录 FGS：

```text
availability = UPSTREAM_ARTIFACT_UNAVAILABLE
smoke = NOT_RUN
nist_846 = NOT_RUN
runtime_metrics = NA
paper_reported_results = EXTERNAL_CLAIM_NOT_REPRODUCED
```

可以做的方法级比较：FGS 是为 path-sensitive typestate analysis 保留多点时序与
空间相关性的 ICFG 简化方法；RIFT 的目标则是从 MITL AP 反向寻找外部可控影响源、
前置状态与变异方向。不能据此声称 RIFT 在运行时间、内存或精度上超过 FGS。

如需替代可执行 baseline，应另外选择具备固定 commit、公开源码、完整 benchmark
命令和可获得输入集的 CCF-A 工件，并把它与 FGS 分开标识。

## 恢复条件与后续步骤

仅在获得下列任一材料后恢复本项复现：

1. 作者重新公开 `rmrepo/fgs`，并提供 immutable image digest；
2. 获得作者发布的 OCI/Docker tar，能记录其 SHA-256 和来源；
3. 获得与论文对应的官方源码 commit、构建依赖、NIST 输入清单和逐例 oracle。

恢复后按以下顺序执行：

1. 先按 digest 拉取或 `docker load`，记录 image ID、RepoDigest 和层大小；
2. 在 12 GiB RSS/24 小时总预算下运行官方 `test.ll` smoke；
3. 固定 NIST 846 项文件列表及哈希，先每类一例，再跑分层子集，最后才跑全集；
4. 记录每例退出码、wall time、peak RSS、TP/FP 与原论文表 5 的差异；
5. 不修改镜像内源码，原始复现成功后才做 RIFT 适配实验。

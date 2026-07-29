# Frozen external documentation sources

`ardupilot_wiki/` is a sparse, shallow checkout of the official ArduPilot wiki repository at commit `209e532bc97e5a41966f8c9ab483323c264cae08`. It contains the `common`, `copter`, `plane`, and `rover` documentation trees used by the corpus extractor.

This documentation commit is `MAIN_ONLY`, not a release tag paired by ArduPilot with source commit `8f2e5db2…`. Each accepted property must therefore record that version relationship and must be rejected or downgraded if its behavior cannot be bound to the frozen source identity. Git history or a newer wiki checkout must not silently replace this corpus.

PX4 v1.17 English documentation is read directly from the release-pinned `baseline/px4/docs/en` tree, so no second checkout is required.

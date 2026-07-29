// SPDX-FileCopyrightText: 2025 Wang Zhen <wz@nudt.edu.cn>
//
// SPDX-License-Identifier: Apache-2.0

# Benchmarks with Infeasible Control Flow Paths

This set of benchmarks is designed to test the accuracy of path-insensitive methods in the presence of multiple paths in loops, including infeasible paths. These programs contain branches that are logically conflicting or unreachable, which can lead to false positives if the analysis does not properly handle path sensitivity.

## Programs

- `conflict_branch1.c`: A loop with conflicting conditions that may lead to over-approximation.
- `conflict_branch2.c`: Similar to conflict_branch1 but with different variables.
- `conflict_branch3.c`: Involves conditional assignments with constants.
- `conflict_branch4.c`: Uses a state variable to track conditions, with potential infeasible paths.
- `conflict_branch5.c`: Extends conflict_branch4 with more variables to create deeper dependencies.
- `unreach_branch1.c`: Contains a condition that is always false, making a branch unreachable.
- `unreach_branch2.c`: Another example of an unreachable branch due to loop conditions.
- `unreach_branch3.c`: Tests a condition that cannot be true within the loop.
- `unreach_branch4.c`: Contains a nested condition that is always false.
- `unreach_branch5.c`: Uses a condition that is logically impossible (x>y and x<y).

## Purpose

These benchmarks are intended for the ReachSafety-ControlFlow category in SV-COMP. They challenge tools using path-insensitive methods to precisely handle path conditions and avoid false positives by correctly identifying infeasible paths.

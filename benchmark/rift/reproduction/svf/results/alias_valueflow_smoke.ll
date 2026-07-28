; ModuleID = 'benchmark/rift/reproduction/svf/results/alias_valueflow_smoke.bc'
source_filename = "benchmark/rift/reproduction/svf/cases/alias_valueflow_smoke.c"
target datalayout = "e-m:e-p270:32:32-p271:32:32-p272:64:64-i64:64-i128:128-f80:128-n8:16:32:64-S128"
target triple = "x86_64-pc-linux-gnu"

@command_value = internal global i32 0, align 4, !dbg !0
@unrelated_value = internal global i32 0, align 4, !dbg !5

; Function Attrs: noinline nounwind optnone uwtable
define dso_local i32 @main() #0 !dbg !16 {
entry:
  %retval = alloca i32, align 4
  %source = alloca ptr, align 8
  %through_call = alloca ptr, align 8
  %other = alloca ptr, align 8
  store i32 0, ptr %retval, align 4
  call void @llvm.dbg.declare(metadata ptr %source, metadata !20, metadata !DIExpression()), !dbg !22
  store ptr @command_value, ptr %source, align 8, !dbg !22
  call void @llvm.dbg.declare(metadata ptr %through_call, metadata !23, metadata !DIExpression()), !dbg !24
  %0 = load ptr, ptr %source, align 8, !dbg !25
  %call = call ptr @forward_pointer(ptr noundef %0), !dbg !26
  store ptr %call, ptr %through_call, align 8, !dbg !24
  call void @llvm.dbg.declare(metadata ptr %other, metadata !27, metadata !DIExpression()), !dbg !28
  store ptr @unrelated_value, ptr %other, align 8, !dbg !28
  %1 = load ptr, ptr %source, align 8, !dbg !29
  %2 = load ptr, ptr %through_call, align 8, !dbg !30
  call void @MAYALIAS(ptr noundef %1, ptr noundef %2), !dbg !31
  %3 = load ptr, ptr %source, align 8, !dbg !32
  %4 = load ptr, ptr %other, align 8, !dbg !33
  call void @NOALIAS(ptr noundef %3, ptr noundef %4), !dbg !34
  %5 = load ptr, ptr %through_call, align 8, !dbg !35
  call void @commit_value(ptr noundef %5, i32 noundef 41), !dbg !36
  %6 = load i32, ptr @command_value, align 4, !dbg !37
  %cmp = icmp eq i32 %6, 41, !dbg !38
  %7 = zext i1 %cmp to i64, !dbg !37
  %cond = select i1 %cmp, i32 0, i32 1, !dbg !37
  ret i32 %cond, !dbg !39
}

; Function Attrs: nocallback nofree nosync nounwind speculatable willreturn memory(none)
declare void @llvm.dbg.declare(metadata, metadata, metadata) #1

; Function Attrs: noinline nounwind optnone uwtable
define internal ptr @forward_pointer(ptr noundef %input) #0 !dbg !40 {
entry:
  %input.addr = alloca ptr, align 8
  store ptr %input, ptr %input.addr, align 8
  call void @llvm.dbg.declare(metadata ptr %input.addr, metadata !43, metadata !DIExpression()), !dbg !44
  %0 = load ptr, ptr %input.addr, align 8, !dbg !45
  ret ptr %0, !dbg !46
}

declare void @MAYALIAS(ptr noundef, ptr noundef) #2

declare void @NOALIAS(ptr noundef, ptr noundef) #2

; Function Attrs: noinline nounwind optnone uwtable
define internal void @commit_value(ptr noundef %destination, i32 noundef %value) #0 !dbg !47 {
entry:
  %destination.addr = alloca ptr, align 8
  %value.addr = alloca i32, align 4
  store ptr %destination, ptr %destination.addr, align 8
  call void @llvm.dbg.declare(metadata ptr %destination.addr, metadata !50, metadata !DIExpression()), !dbg !51
  store i32 %value, ptr %value.addr, align 4
  call void @llvm.dbg.declare(metadata ptr %value.addr, metadata !52, metadata !DIExpression()), !dbg !53
  %0 = load i32, ptr %value.addr, align 4, !dbg !54
  %1 = load ptr, ptr %destination.addr, align 8, !dbg !55
  store i32 %0, ptr %1, align 4, !dbg !56
  ret void, !dbg !57
}

attributes #0 = { noinline nounwind optnone uwtable "frame-pointer"="all" "min-legal-vector-width"="0" "no-trapping-math"="true" "stack-protector-buffer-size"="8" "target-cpu"="x86-64" "target-features"="+cmov,+cx8,+fxsr,+mmx,+sse,+sse2,+x87" "tune-cpu"="generic" }
attributes #1 = { nocallback nofree nosync nounwind speculatable willreturn memory(none) }
attributes #2 = { "frame-pointer"="all" "no-trapping-math"="true" "stack-protector-buffer-size"="8" "target-cpu"="x86-64" "target-features"="+cmov,+cx8,+fxsr,+mmx,+sse,+sse2,+x87" "tune-cpu"="generic" }

!llvm.dbg.cu = !{!2}
!llvm.module.flags = !{!8, !9, !10, !11, !12, !13, !14}
!llvm.ident = !{!15}

!0 = !DIGlobalVariableExpression(var: !1, expr: !DIExpression())
!1 = distinct !DIGlobalVariable(name: "command_value", scope: !2, file: !3, line: 11, type: !7, isLocal: true, isDefinition: true)
!2 = distinct !DICompileUnit(language: DW_LANG_C11, file: !3, producer: "Ubuntu clang version 18.1.8 (++20240731024944+3b5b5c1ec4a3-1~exp1~20240731145000.144)", isOptimized: false, flags: "/usr/lib/llvm-18/bin/clang -g -O0 -fno-discard-value-names -emit-llvm -c benchmark/rift/reproduction/svf/cases/alias_valueflow_smoke.c -o benchmark/rift/reproduction/svf/results/alias_valueflow_smoke.bc", runtimeVersion: 0, emissionKind: FullDebug, globals: !4, splitDebugInlining: false, nameTableKind: None)
!3 = !DIFile(filename: "benchmark/rift/reproduction/svf/cases/alias_valueflow_smoke.c", directory: "/home/lqq/project/TAFuzz", checksumkind: CSK_MD5, checksum: "55d21fd391379c4df8b0465ea048d95e")
!4 = !{!0, !5}
!5 = !DIGlobalVariableExpression(var: !6, expr: !DIExpression())
!6 = distinct !DIGlobalVariable(name: "unrelated_value", scope: !2, file: !3, line: 12, type: !7, isLocal: true, isDefinition: true)
!7 = !DIBasicType(name: "int", size: 32, encoding: DW_ATE_signed)
!8 = !{i32 7, !"Dwarf Version", i32 5}
!9 = !{i32 2, !"Debug Info Version", i32 3}
!10 = !{i32 1, !"wchar_size", i32 4}
!11 = !{i32 8, !"PIC Level", i32 2}
!12 = !{i32 7, !"PIE Level", i32 2}
!13 = !{i32 7, !"uwtable", i32 2}
!14 = !{i32 7, !"frame-pointer", i32 2}
!15 = !{!"Ubuntu clang version 18.1.8 (++20240731024944+3b5b5c1ec4a3-1~exp1~20240731145000.144)"}
!16 = distinct !DISubprogram(name: "main", scope: !3, file: !3, line: 25, type: !17, scopeLine: 26, flags: DIFlagPrototyped, spFlags: DISPFlagDefinition, unit: !2, retainedNodes: !19)
!17 = !DISubroutineType(types: !18)
!18 = !{!7}
!19 = !{}
!20 = !DILocalVariable(name: "source", scope: !16, file: !3, line: 27, type: !21)
!21 = !DIDerivedType(tag: DW_TAG_pointer_type, baseType: !7, size: 64)
!22 = !DILocation(line: 27, column: 10, scope: !16)
!23 = !DILocalVariable(name: "through_call", scope: !16, file: !3, line: 28, type: !21)
!24 = !DILocation(line: 28, column: 10, scope: !16)
!25 = !DILocation(line: 28, column: 41, scope: !16)
!26 = !DILocation(line: 28, column: 25, scope: !16)
!27 = !DILocalVariable(name: "other", scope: !16, file: !3, line: 29, type: !21)
!28 = !DILocation(line: 29, column: 10, scope: !16)
!29 = !DILocation(line: 31, column: 14, scope: !16)
!30 = !DILocation(line: 31, column: 22, scope: !16)
!31 = !DILocation(line: 31, column: 5, scope: !16)
!32 = !DILocation(line: 32, column: 13, scope: !16)
!33 = !DILocation(line: 32, column: 21, scope: !16)
!34 = !DILocation(line: 32, column: 5, scope: !16)
!35 = !DILocation(line: 34, column: 18, scope: !16)
!36 = !DILocation(line: 34, column: 5, scope: !16)
!37 = !DILocation(line: 35, column: 12, scope: !16)
!38 = !DILocation(line: 35, column: 26, scope: !16)
!39 = !DILocation(line: 35, column: 5, scope: !16)
!40 = distinct !DISubprogram(name: "forward_pointer", scope: !3, file: !3, line: 14, type: !41, scopeLine: 15, flags: DIFlagPrototyped, spFlags: DISPFlagLocalToUnit | DISPFlagDefinition, unit: !2, retainedNodes: !19)
!41 = !DISubroutineType(types: !42)
!42 = !{!21, !21}
!43 = !DILocalVariable(name: "input", arg: 1, scope: !40, file: !3, line: 14, type: !21)
!44 = !DILocation(line: 14, column: 60, scope: !40)
!45 = !DILocation(line: 16, column: 12, scope: !40)
!46 = !DILocation(line: 16, column: 5, scope: !40)
!47 = distinct !DISubprogram(name: "commit_value", scope: !3, file: !3, line: 19, type: !48, scopeLine: 21, flags: DIFlagPrototyped, spFlags: DISPFlagLocalToUnit | DISPFlagDefinition, unit: !2, retainedNodes: !19)
!48 = !DISubroutineType(types: !49)
!49 = !{null, !21, !7}
!50 = !DILocalVariable(name: "destination", arg: 1, scope: !47, file: !3, line: 19, type: !21)
!51 = !DILocation(line: 19, column: 57, scope: !47)
!52 = !DILocalVariable(name: "value", arg: 2, scope: !47, file: !3, line: 20, type: !7)
!53 = !DILocation(line: 20, column: 57, scope: !47)
!54 = !DILocation(line: 22, column: 20, scope: !47)
!55 = !DILocation(line: 22, column: 6, scope: !47)
!56 = !DILocation(line: 22, column: 18, scope: !47)
!57 = !DILocation(line: 23, column: 1, scope: !47)

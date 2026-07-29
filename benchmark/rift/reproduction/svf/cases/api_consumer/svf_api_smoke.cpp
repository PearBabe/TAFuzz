/*
 * External-consumer smoke for the installed SVF 3.2 CMake package.
 * This is not a RIFT analysis: it only proves that the project-independent
 * SVFIR, ICFG, Andersen and SVFG interfaces are consumable without editing
 * the official SVF source tree.
 */
#include "Graphs/SVFG.h"
#include "MSSA/SVFGBuilder.h"
#include "SVF-LLVM/LLVMModule.h"
#include "SVF-LLVM/SVFIRBuilder.h"
#include "SVFIR/SVFIR.h"
#include "WPA/Andersen.h"

#include "llvm/Support/ManagedStatic.h"

#include <iostream>
#include <string>
#include <vector>

int main(int argc, char **argv)
{
    if (argc != 2)
    {
        std::cerr << "usage: svf_api_smoke INPUT.bc\n";
        return 2;
    }

    const std::vector<std::string> modules{argv[1]};
    SVF::LLVMModuleSet::buildSVFModule(modules);

    SVF::SVFIRBuilder builder;
    SVF::SVFIR *svfir = builder.build();
    SVF::AndersenWaveDiff *andersen =
        SVF::AndersenWaveDiff::createAndersenWaveDiff(svfir);

    SVF::SVFGBuilder svfg_builder;
    SVF::SVFG *svfg = svfg_builder.buildFullSVFG(andersen);

    std::cout << "SVF_API_SMOKE=PASS\n"
              << "SVFIR_NODES=" << svfir->getPAGNodeNum() << "\n"
              << "ICFG_NODES=" << svfir->getICFG()->getTotalNodeNum() << "\n"
              << "SVFG_NODES=" << svfg->getTotalNodeNum() << "\n";

    SVF::AndersenWaveDiff::releaseAndersenWaveDiff();
    SVF::SVFIR::releaseSVFIR();
    SVF::LLVMModuleSet::releaseLLVMModuleSet();
    llvm::llvm_shutdown();
    return 0;
}

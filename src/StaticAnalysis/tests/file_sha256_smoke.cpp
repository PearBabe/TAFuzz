#include "rift/core/sha256.h"
#include "rift/core/types.h"

#include <algorithm>
#include <chrono>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

namespace fs = std::filesystem;

class TemporaryFile {
public:
    TemporaryFile()
        : path_(fs::temp_directory_path() /
                ("rift-file-sha256-" + std::to_string(
                    std::chrono::steady_clock::now()
                        .time_since_epoch()
                        .count()) + ".bin")) {}

    TemporaryFile(const TemporaryFile &) = delete;
    TemporaryFile &operator=(const TemporaryFile &) = delete;

    ~TemporaryFile() {
        std::error_code ignored;
        fs::remove(path_, ignored);
    }

    [[nodiscard]] const fs::path &path() const { return path_; }

private:
    fs::path path_;
};

void require(bool condition, const std::string &message) {
    if (!condition) {
        throw std::runtime_error(message);
    }
}

void write_repeated_zeroes(
    const fs::path &path, const std::uint64_t byte_count) {
    std::ofstream output(path, std::ios::binary | std::ios::trunc);
    require(static_cast<bool>(output), "cannot create large digest fixture");
    constexpr std::size_t kBlockBytes = 1024U * 1024U;
    const std::vector<char> block(kBlockBytes, '\0');
    std::uint64_t remaining = byte_count;
    while (remaining != 0U) {
        const std::size_t count = static_cast<std::size_t>(
            std::min<std::uint64_t>(remaining, block.size()));
        output.write(block.data(), static_cast<std::streamsize>(count));
        require(static_cast<bool>(output), "failed to stream large digest fixture");
        remaining -= count;
    }
    output.close();
    require(static_cast<bool>(output), "failed to close large digest fixture");
    require(fs::file_size(path) == byte_count, "large digest fixture has wrong size");
}

}  // namespace

int main(int argc, char **argv) {
    try {
        if (argc == 3) {
            const std::string observed = rift::core::sha256_file(argv[1]);
            require(observed == argv[2], "supplied file SHA-256 differs");
            std::cout << "PASS file SHA-256 " << observed << '\n';
            return 0;
        }
        require(argc == 1, "usage: rift_file_sha256_smoke [file expected_sha256]");
        require(
            rift::core::sha256_hex("") ==
                "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            "empty in-memory SHA-256 changed");
        require(
            rift::core::sha256_hex("abc") ==
                "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
            "small in-memory SHA-256 changed");
        const std::string padding_boundary(56U, 'a');
        rift::core::Sha256 incremental;
        incremental.update(padding_boundary.data(), 1U);
        incremental.update(padding_boundary.data() + 1U, 7U);
        incremental.update(padding_boundary.data() + 8U, 48U);
        require(
            rift::core::sha256_digest_hex(incremental.final()) ==
                "b35439a4ac6f0948b6d6f9e3c6af0f5f590ce20f1bde7090ef7970686ec6738a",
            "incremental SHA-256 padding boundary changed");

        TemporaryFile small;
        {
            std::ofstream output(small.path(), std::ios::binary | std::ios::trunc);
            output << "abc";
        }
        require(
            rift::core::sha256_file(small.path()) ==
                "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
            "small file SHA-256 changed");

        // LLVM 18's SHA256 implementation stores ByteCount in uint32_t and
        // produces a non-standard digest after byte_count * 8 crosses 2^32.
        // This fixture is one byte above that 512 MiB boundary.  It is written
        // and hashed in bounded 1 MiB blocks, then removed by RAII.
        constexpr std::uint64_t kBoundaryBytes = 512ULL * 1024ULL * 1024ULL;
        TemporaryFile large;
        write_repeated_zeroes(large.path(), kBoundaryBytes + 1U);
        require(
            rift::core::sha256_file(large.path()) ==
                "7c40fe5ce847740d0f0d0cdde3949d6585804cdec3ae61a15b923165699c8137",
            "file SHA-256 is incorrect above the 512 MiB bit-length boundary");

        std::cout << "PASS file SHA-256 small vectors and 512 MiB boundary\n";
        return 0;
    } catch (const std::exception &error) {
        std::cerr << "FAIL " << error.what() << '\n';
        return 1;
    }
}

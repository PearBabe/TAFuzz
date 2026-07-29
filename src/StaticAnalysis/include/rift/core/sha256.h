#ifndef RIFT_CORE_SHA256_H
#define RIFT_CORE_SHA256_H

#include <array>
#include <cstddef>
#include <cstdint>
#include <filesystem>
#include <string>

namespace rift::core {

// Standards-compliant streaming SHA-256 with a 64-bit message-length field.
// LLVM 18's llvm::SHA256 stores ByteCount in uint32_t and therefore emits a
// non-standard digest once the message length in bits crosses 2^32.
class Sha256 {
public:
    Sha256();

    void update(const void *data, std::size_t size);
    [[nodiscard]] std::array<std::uint8_t, 32> final();

private:
    void compress(const std::uint8_t *block);

    std::array<std::uint32_t, 8> state_{};
    std::array<std::uint8_t, 64> buffer_{};
    std::uint64_t byte_count_ = 0;
    std::size_t buffer_size_ = 0;
    bool finalized_ = false;
};

[[nodiscard]] std::string sha256_digest_hex(
    const std::array<std::uint8_t, 32> &digest);

}  // namespace rift::core

#endif

#include "rift/core/sha256.h"

#include "rift/core/types.h"

#include <algorithm>
#include <array>
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <limits>
#include <sstream>
#include <stdexcept>
#include <string>

namespace rift::core {
namespace {

constexpr std::array<std::uint32_t, 64> kRoundConstants{
    0x428a2f98U, 0x71374491U, 0xb5c0fbcfU, 0xe9b5dba5U,
    0x3956c25bU, 0x59f111f1U, 0x923f82a4U, 0xab1c5ed5U,
    0xd807aa98U, 0x12835b01U, 0x243185beU, 0x550c7dc3U,
    0x72be5d74U, 0x80deb1feU, 0x9bdc06a7U, 0xc19bf174U,
    0xe49b69c1U, 0xefbe4786U, 0x0fc19dc6U, 0x240ca1ccU,
    0x2de92c6fU, 0x4a7484aaU, 0x5cb0a9dcU, 0x76f988daU,
    0x983e5152U, 0xa831c66dU, 0xb00327c8U, 0xbf597fc7U,
    0xc6e00bf3U, 0xd5a79147U, 0x06ca6351U, 0x14292967U,
    0x27b70a85U, 0x2e1b2138U, 0x4d2c6dfcU, 0x53380d13U,
    0x650a7354U, 0x766a0abbU, 0x81c2c92eU, 0x92722c85U,
    0xa2bfe8a1U, 0xa81a664bU, 0xc24b8b70U, 0xc76c51a3U,
    0xd192e819U, 0xd6990624U, 0xf40e3585U, 0x106aa070U,
    0x19a4c116U, 0x1e376c08U, 0x2748774cU, 0x34b0bcb5U,
    0x391c0cb3U, 0x4ed8aa4aU, 0x5b9cca4fU, 0x682e6ff3U,
    0x748f82eeU, 0x78a5636fU, 0x84c87814U, 0x8cc70208U,
    0x90befffaU, 0xa4506cebU, 0xbef9a3f7U, 0xc67178f2U,
};

constexpr std::uint32_t rotate_right(
    const std::uint32_t value, const unsigned count) {
    return (value >> count) | (value << (32U - count));
}

}  // namespace

Sha256::Sha256()
    : state_{
          0x6a09e667U,
          0xbb67ae85U,
          0x3c6ef372U,
          0xa54ff53aU,
          0x510e527fU,
          0x9b05688cU,
          0x1f83d9abU,
          0x5be0cd19U,
      } {}

void Sha256::compress(const std::uint8_t *block) {
    std::array<std::uint32_t, 64> words{};
    for (std::size_t index = 0; index < 16; ++index) {
        const std::size_t offset = index * 4U;
        words[index] =
            (static_cast<std::uint32_t>(block[offset]) << 24U) |
            (static_cast<std::uint32_t>(block[offset + 1U]) << 16U) |
            (static_cast<std::uint32_t>(block[offset + 2U]) << 8U) |
            static_cast<std::uint32_t>(block[offset + 3U]);
    }
    for (std::size_t index = 16; index < words.size(); ++index) {
        const std::uint32_t lower =
            rotate_right(words[index - 15U], 7U) ^
            rotate_right(words[index - 15U], 18U) ^
            (words[index - 15U] >> 3U);
        const std::uint32_t upper =
            rotate_right(words[index - 2U], 17U) ^
            rotate_right(words[index - 2U], 19U) ^
            (words[index - 2U] >> 10U);
        words[index] =
            words[index - 16U] + lower + words[index - 7U] + upper;
    }

    std::uint32_t a = state_[0];
    std::uint32_t b = state_[1];
    std::uint32_t c = state_[2];
    std::uint32_t d = state_[3];
    std::uint32_t e = state_[4];
    std::uint32_t f = state_[5];
    std::uint32_t g = state_[6];
    std::uint32_t h = state_[7];
    for (std::size_t index = 0; index < words.size(); ++index) {
        const std::uint32_t choose = (e & f) ^ ((~e) & g);
        const std::uint32_t majority = (a & b) ^ (a & c) ^ (b & c);
        const std::uint32_t sum_e =
            rotate_right(e, 6U) ^ rotate_right(e, 11U) ^
            rotate_right(e, 25U);
        const std::uint32_t sum_a =
            rotate_right(a, 2U) ^ rotate_right(a, 13U) ^
            rotate_right(a, 22U);
        const std::uint32_t first =
            h + sum_e + choose + kRoundConstants[index] + words[index];
        const std::uint32_t second = sum_a + majority;
        h = g;
        g = f;
        f = e;
        e = d + first;
        d = c;
        c = b;
        b = a;
        a = first + second;
    }
    state_[0] += a;
    state_[1] += b;
    state_[2] += c;
    state_[3] += d;
    state_[4] += e;
    state_[5] += f;
    state_[6] += g;
    state_[7] += h;
}

void Sha256::update(const void *data, const std::size_t size) {
    if (finalized_) {
        throw std::logic_error("SHA-256 update after final");
    }
    constexpr std::uint64_t kMaximumBytes =
        std::numeric_limits<std::uint64_t>::max() / 8U;
    if (size > kMaximumBytes - byte_count_) {
        throw std::length_error("SHA-256 input exceeds 64-bit bit length");
    }
    byte_count_ += static_cast<std::uint64_t>(size);
    const auto *bytes = static_cast<const std::uint8_t *>(data);
    std::size_t offset = 0;
    if (buffer_size_ != 0U) {
        const std::size_t count =
            std::min(size, buffer_.size() - buffer_size_);
        std::copy_n(bytes, count, buffer_.begin() + buffer_size_);
        buffer_size_ += count;
        offset += count;
        if (buffer_size_ == buffer_.size()) {
            compress(buffer_.data());
            buffer_size_ = 0;
        }
    }
    while (size - offset >= buffer_.size()) {
        compress(bytes + offset);
        offset += buffer_.size();
    }
    if (offset != size) {
        buffer_size_ = size - offset;
        std::copy_n(bytes + offset, buffer_size_, buffer_.begin());
    }
}

std::array<std::uint8_t, 32> Sha256::final() {
    if (finalized_) {
        throw std::logic_error("SHA-256 final called more than once");
    }
    finalized_ = true;
    const std::uint64_t bit_count = byte_count_ * 8U;
    buffer_[buffer_size_++] = 0x80U;
    if (buffer_size_ > 56U) {
        std::fill(buffer_.begin() + buffer_size_, buffer_.end(), 0U);
        compress(buffer_.data());
        buffer_size_ = 0;
    }
    std::fill(buffer_.begin() + buffer_size_, buffer_.begin() + 56U, 0U);
    for (std::size_t index = 0; index < 8U; ++index) {
        buffer_[56U + index] = static_cast<std::uint8_t>(
            bit_count >> (56U - index * 8U));
    }
    compress(buffer_.data());

    std::array<std::uint8_t, 32> digest{};
    for (std::size_t index = 0; index < state_.size(); ++index) {
        digest[index * 4U] = static_cast<std::uint8_t>(state_[index] >> 24U);
        digest[index * 4U + 1U] =
            static_cast<std::uint8_t>(state_[index] >> 16U);
        digest[index * 4U + 2U] =
            static_cast<std::uint8_t>(state_[index] >> 8U);
        digest[index * 4U + 3U] = static_cast<std::uint8_t>(state_[index]);
    }
    return digest;
}

std::string sha256_digest_hex(
    const std::array<std::uint8_t, 32> &digest) {
    std::ostringstream stream;
    stream << std::hex << std::setfill('0');
    for (const std::uint8_t byte : digest) {
        stream << std::setw(2) << static_cast<unsigned>(byte);
    }
    return stream.str();
}

std::string sha256_hex(const std::string &bytes) {
    Sha256 hasher;
    hasher.update(bytes.data(), bytes.size());
    return sha256_digest_hex(hasher.final());
}

std::string sha256_file(const std::filesystem::path &path) {
    std::ifstream input(path, std::ios::binary);
    if (!input) {
        throw std::runtime_error("cannot open " + path.string());
    }
    Sha256 hasher;
    std::array<char, 64U * 1024U> buffer{};
    while (input) {
        input.read(buffer.data(), static_cast<std::streamsize>(buffer.size()));
        const std::streamsize count = input.gcount();
        if (count > 0) {
            hasher.update(buffer.data(), static_cast<std::size_t>(count));
        }
    }
    if (!input.eof()) {
        throw std::runtime_error("failed while hashing " + path.string());
    }
    return sha256_digest_hex(hasher.final());
}

}  // namespace rift::core

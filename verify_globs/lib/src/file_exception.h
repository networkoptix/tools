#pragma once

#include <exception>
#include <string>

namespace verify_globs {

class FileException: public std::exception
{
public:
    explicit FileException(const std::string& msg): m_message(msg) {}
    const char* what() const noexcept { return m_message.c_str(); }

private:
    const std::string m_message;
};

} // namespace verify_globs

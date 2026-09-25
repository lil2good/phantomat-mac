#pragma once

#if defined(__aarch64__)
#include <funchook.h>
#include <memory>
#include <exception>
#include <stdexcept>
#include <vector>

class PhantomatHook {
  public:
    void* m_original;

    PhantomatHook(const void* source, const void* destination) : m_original(const_cast<void*>(source)), handle(funchook_create()) {
        if (!handle)
            throw std::bad_alloc();
        if (funchook_prepare(handle, &m_original, const_cast<void*>(destination))) {
            const std::string error = funchook_error_message(handle);
            funchook_destroy(handle);
            throw std::runtime_error("ARM64 hook preparation: " + error);
        }
    }

    bool hook() {
        if (active)
            return true;
        const auto result = funchook_install(handle, 0);
        if (result)
            Log::logger->log(Log::ERR, "[phantomat-arm64] {}", funchook_error_message(handle));
        active = result == 0;
        return active;
    }

    bool unhook() {
        if (!active)
            return true;
        const auto result = funchook_uninstall(handle, 0);
        if (result)
            Log::logger->log(Log::ERR, "[phantomat-arm64] {}", funchook_error_message(handle));
        else
            active = false;
        return !active;
    }

    ~PhantomatHook() {
        unhook();
        funchook_destroy(handle);
    }

    PhantomatHook(const PhantomatHook&) = delete;
    PhantomatHook& operator=(const PhantomatHook&) = delete;

  private:
    funchook_t* handle;
    bool active = false;
};

static std::vector<std::unique_ptr<PhantomatHook>> arm64Hooks;

static PhantomatHook* createPhantomatHook(HANDLE, const void* source, const void* destination) {
    auto hook = std::make_unique<PhantomatHook>(source, destination);
    const auto result = hook.get();
    arm64Hooks.push_back(std::move(hook));
    return result;
}

static void releasePhantomatHooks() {
    arm64Hooks.clear();
}

struct PhantomatHookInitGuard {
    int exceptions = std::uncaught_exceptions();
    ~PhantomatHookInitGuard() {
        if (std::uncaught_exceptions() > exceptions)
            releasePhantomatHooks();
    }
};
#else
using PhantomatHook = CFunctionHook;
static auto createPhantomatHook(HANDLE owner, const void* source, const void* destination) {
    return HyprlandAPI::createFunctionHook(owner, source, destination);
}
static void releasePhantomatHooks() {}
struct PhantomatHookInitGuard {};
#endif

#define WLR_USE_UNSTABLE
#include <hyprland/src/plugins/PluginAPI.hpp>
#include <hyprland/src/managers/input/InputManager.hpp>
#include <hyprland/src/managers/input/UnifiedWorkspaceSwipeGesture.hpp>
#include <sstream>

static SP<SHyprCtlCommand> command;
APICALL EXPORT std::string PLUGIN_API_VERSION() { return HYPRLAND_API_VERSION; }
APICALL EXPORT PLUGIN_DESCRIPTION_INFO PLUGIN_INIT(HANDLE handle) {
    if (std::string(__hyprland_api_get_hash()) != __hyprland_api_get_client_hash())
        throw std::runtime_error("swipe probe ABI mismatch");
    command = HyprlandAPI::registerHyprCtlCommand(handle, SHyprCtlCommand{
        .name = "swipeprobe", .exact = false, .fn = [](eHyprCtlOutputFormat, std::string args) {
            std::istringstream input(args);
            std::string name, action;
            double delta = 0;
            input >> name >> action >> delta;
            if (action == "begin") g_pInputManager->onSwipeBegin({.fingers = 3});
            else if (action == "update") g_pInputManager->onSwipeUpdate({.fingers = 3, .delta = {delta, 0.0}});
            else if (action == "end") g_pInputManager->onSwipeEnd({});
            else if (action == "scroll") {
                g_pInputManager->onMouseWheel({.timeMs = Time::millis(Time::steadyNow()), .source = WL_POINTER_AXIS_SOURCE_FINGER, .delta = delta});
                g_pInputManager->onPointerFrame();
            }
            return g_pUnifiedWorkspaceSwipe->isGestureInProgress() ? "active" : "idle";
        }});
    return {"swipeprobe", "Nested compositor swipe regression driver", "local", "1"};
}
APICALL EXPORT void PLUGIN_EXIT() { command.reset(); }

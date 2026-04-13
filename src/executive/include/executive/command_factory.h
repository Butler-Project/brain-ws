#pragma once

#include "executive/command_builder.h"
#include <map>
#include <memory>
#include <string>

namespace executive {

// Registers all available commands at construction time.
// Returns command instances by name.
class CommandFactory {
public:
    explicit CommandFactory(const ExecutionContext& ctx) {
        CommandBuilder builder;
        builder.set_context(ctx);

        commands_["move_to"] = builder.build_move_to();
        commands_["show_me_around"] = builder.build_show_me_around();
    }

    HighLevelCommand* find(const std::string& command_name) {
        auto it = commands_.find(command_name);
        if (it != commands_.end()) {
            return it->second.get();
        }
        return nullptr;
    }

    std::string available_commands() const {
        std::string result;
        for (const auto& [name, _] : commands_) {
            if (!result.empty()) result += ", ";
            result += name;
        }
        return result;
    }

private:
    std::map<std::string, std::unique_ptr<HighLevelCommand>> commands_;
};

}  // namespace executive

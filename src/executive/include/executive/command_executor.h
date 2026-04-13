#pragma once

#include "executive/high_level_command.h"
#include <memory>
#include <vector>

namespace executive {

class CommandExecutor {
public:
    explicit CommandExecutor(std::vector<std::unique_ptr<HighLevelCommand>> commands)
        : commands_(std::move(commands))
    {}

    bool execute_all(ProgressCallback on_progress) {
        for (size_t i = 0; i < commands_.size(); ++i) {
            auto& cmd = commands_[i];
            on_progress("Executing command " + std::to_string(i + 1) + "/" +
                        std::to_string(commands_.size()) + ": " + cmd->get_name());

            if (!cmd->execute(on_progress)) {
                on_progress("Command " + cmd->get_name() + " failed.");
                return false;
            }
        }

        on_progress("All commands completed successfully.");
        return true;
    }

    size_t size() const { return commands_.size(); }

    const HighLevelCommand& at(size_t index) const { return *commands_.at(index); }

private:
    std::vector<std::unique_ptr<HighLevelCommand>> commands_;
};

}  // namespace executive

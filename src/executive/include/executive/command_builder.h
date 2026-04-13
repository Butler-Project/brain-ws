#pragma once

#include "executive/move_to_command.h"
#include "executive/show_me_around_command.h"
#include <memory>

namespace executive {

class CommandBuilder {
public:
    CommandBuilder& set_context(const ExecutionContext& ctx) {
        ctx_ = ctx;
        return *this;
    }

    std::unique_ptr<MoveToCommand> build_move_to() const {
        return std::make_unique<MoveToCommand>(ctx_);
    }

    std::unique_ptr<ShowMeAroundCommand> build_show_me_around() const {
        return std::make_unique<ShowMeAroundCommand>(ctx_);
    }

private:
    ExecutionContext ctx_;
};

}  // namespace executive

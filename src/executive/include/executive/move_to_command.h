#pragma once

#include "executive/high_level_command.h"

namespace executive {

class MoveToCommand : public HighLevelCommand {
public:
    explicit MoveToCommand(ExecutionContext ctx)
        : HighLevelCommand(std::move(ctx))
    {}

    std::string get_name() const override { return "move_to"; }

    void configure(const std::vector<Landmark>& landmarks) override {
        RCLCPP_INFO(
            ctx_.node->get_logger(),
            "MoveToCommand::configure called with %zu landmarks",
            landmarks.size());

        if (!landmarks.empty()) {
            destination_ = landmarks[0].position;
            destination_name_ = landmarks[0].name;
            RCLCPP_INFO(
                ctx_.node->get_logger(),
                "MoveToCommand configured for landmark '%s' at x=%.3f, y=%.3f",
                destination_name_.c_str(),
                destination_.x,
                destination_.y);
        } else {
            RCLCPP_ERROR(
                ctx_.node->get_logger(),
                "MoveToCommand received no landmarks during configure");
        }
    }

    bool execute(ProgressCallback on_progress) override {
        RCLCPP_INFO(
            ctx_.node->get_logger(),
            "MoveToCommand::execute starting for destination '%s'",
            destination_name_.c_str());
        status_ = CommandStatus::IN_EXECUTION;

        on_progress("MoveTo: starting navigation to " + destination_name_);
        if (!navigate_to(destination_, on_progress, destination_name_)) {
            RCLCPP_ERROR(
                ctx_.node->get_logger(),
                "MoveToCommand failed while navigating to '%s'",
                destination_name_.c_str());
            status_ = CommandStatus::FAILED;
            return false;
        }

        on_progress("MoveTo: destination reached, entering wait phase");
        if (!wait(on_progress)) {
            RCLCPP_ERROR(
                ctx_.node->get_logger(),
                "MoveToCommand failed while waiting at '%s'",
                destination_name_.c_str());
            status_ = CommandStatus::FAILED;
            return false;
        }

        status_ = CommandStatus::NAVIGATING_HOME;
        on_progress("MoveTo: wait completed, returning home");
        if (!navigate_to(ctx_.home, on_progress, "home")) {
            RCLCPP_ERROR(
                ctx_.node->get_logger(),
                "MoveToCommand failed while returning home from '%s'",
                destination_name_.c_str());
            status_ = CommandStatus::FAILED;
            return false;
        }

        status_ = CommandStatus::COMPLETED;
        RCLCPP_INFO(
            ctx_.node->get_logger(),
            "MoveToCommand completed successfully for '%s'",
            destination_name_.c_str());
        on_progress("MoveTo(" + destination_name_ + ") completed.");
        return true;
    }

private:
    Position destination_;
    std::string destination_name_{"destination"};
};

}  // namespace executive

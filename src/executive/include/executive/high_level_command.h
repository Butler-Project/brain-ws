#pragma once

#include "executive/execution_context.h"
#include <chrono>
#include <functional>
#include <string>
#include <vector>

namespace executive {

struct Landmark {
    std::string name;
    Position position;
};

enum class CommandStatus {
    PENDING,
    IN_EXECUTION,
    WAITING,
    NAVIGATING_HOME,
    COMPLETED,
    FAILED
};

inline std::string to_string(CommandStatus status) {
    switch (status) {
        case CommandStatus::PENDING:          return "pending";
        case CommandStatus::IN_EXECUTION:     return "in_execution";
        case CommandStatus::WAITING:          return "waiting";
        case CommandStatus::NAVIGATING_HOME:  return "navigating_home";
        case CommandStatus::COMPLETED:        return "completed";
        case CommandStatus::FAILED:           return "failed";
    }
    return "unknown";
}

using ProgressCallback = std::function<void(const std::string& status_msg)>;

class HighLevelCommand {
public:
    explicit HighLevelCommand(ExecutionContext ctx)
        : ctx_(std::move(ctx))
    {}

    virtual ~HighLevelCommand() = default;

    // Configure with landmarks for this execution
    virtual void configure(const std::vector<Landmark>& landmarks) = 0;

    virtual bool execute(ProgressCallback on_progress) = 0;
    virtual std::string get_name() const = 0;
    virtual CommandStatus get_status() const { return status_; }

    // Reset to PENDING so the command can be re-executed
    virtual void reset() { status_ = CommandStatus::PENDING; }

protected:
    ExecutionContext ctx_;
    CommandStatus status_{CommandStatus::PENDING};

    bool navigate_to(const Position& target,
                     ProgressCallback on_progress, const std::string& label)
    {
        using NavigateToPose = nav2_msgs::action::NavigateToPose;
        using namespace std::chrono_literals;

        RCLCPP_INFO(
            ctx_.node->get_logger(),
            "HighLevelCommand::navigate_to starting for '%s' at x=%.3f, y=%.3f",
            label.c_str(),
            target.x,
            target.y);

        if (cancel_requested()) {
            RCLCPP_WARN(
                ctx_.node->get_logger(),
                "HighLevelCommand::navigate_to aborted before send because cancellation was requested for '%s'",
                label.c_str());
            on_progress("Cancellation requested before navigating to " + label);
            return false;
        }

        auto goal = NavigateToPose::Goal();
        goal.pose = ctx_.to_pose_stamped(target);

        on_progress("Navigating to " + label +
                    " (x=" + std::to_string(target.x) +
                    ", y=" + std::to_string(target.y) + ")");

        auto send_future = ctx_.nav2_client->async_send_goal(goal);
        if (send_future.wait_for(std::chrono::seconds(10)) != std::future_status::ready) {
            RCLCPP_ERROR(
                ctx_.node->get_logger(),
                "HighLevelCommand::navigate_to failed to send goal for '%s'",
                label.c_str());
            on_progress("Failed to send navigation goal to " + label);
            return false;
        }

        auto goal_handle = send_future.get();
        if (!goal_handle) {
            RCLCPP_ERROR(
                ctx_.node->get_logger(),
                "HighLevelCommand::navigate_to goal rejected for '%s'",
                label.c_str());
            on_progress("Navigation goal rejected for " + label);
            return false;
        }

        RCLCPP_INFO(
            ctx_.node->get_logger(),
            "HighLevelCommand::navigate_to goal accepted for '%s'",
            label.c_str());

        set_active_nav_goal(goal_handle);
        auto result_future = ctx_.nav2_client->async_get_result(goal_handle);
        while (rclcpp::ok()) {
            const auto rc = result_future.wait_for(200ms);
            if (rc == std::future_status::ready) {
                break;
            }

            if (!cancel_requested()) {
                continue;
            }

            on_progress("Cancellation requested while navigating to " + label);
            auto cancel_future = ctx_.nav2_client->async_cancel_goal(goal_handle);
            if (cancel_future.wait_for(5s) != std::future_status::ready) {
                clear_active_nav_goal();
                RCLCPP_ERROR(
                    ctx_.node->get_logger(),
                    "HighLevelCommand::navigate_to failed to cancel goal for '%s'",
                    label.c_str());
                on_progress("Failed to cancel navigation goal for " + label);
                return false;
            }

            clear_active_nav_goal();
            RCLCPP_WARN(
                ctx_.node->get_logger(),
                "HighLevelCommand::navigate_to cancelled goal for '%s'",
                label.c_str());
            return false;
        }

        auto result = result_future.get();
        clear_active_nav_goal();
        if (result.code == rclcpp_action::ResultCode::CANCELED) {
            RCLCPP_WARN(
                ctx_.node->get_logger(),
                "HighLevelCommand::navigate_to result was CANCELED for '%s'",
                label.c_str());
            on_progress("Navigation cancelled for " + label);
            return false;
        }
        if (result.code != rclcpp_action::ResultCode::SUCCEEDED) {
            RCLCPP_ERROR(
                ctx_.node->get_logger(),
                "HighLevelCommand::navigate_to failed for '%s' with result code %d",
                label.c_str(),
                static_cast<int>(result.code));
            on_progress("Navigation failed for " + label);
            return false;
        }

        RCLCPP_INFO(
            ctx_.node->get_logger(),
            "HighLevelCommand::navigate_to completed successfully for '%s'",
            label.c_str());
        on_progress("Arrived at " + label);
        return true;
    }

    bool wait(ProgressCallback on_progress) {
        using namespace std::chrono_literals;

        status_ = CommandStatus::WAITING;
        on_progress("Waiting " + std::to_string(ctx_.wait_time_seconds) + " seconds...");
        const auto deadline =
            std::chrono::steady_clock::now() +
            std::chrono::milliseconds(static_cast<int64_t>(ctx_.wait_time_seconds * 1000));

        while (std::chrono::steady_clock::now() < deadline) {
            if (cancel_requested()) {
                on_progress("Waiting interrupted by cancellation request.");
                return false;
            }
            rclcpp::sleep_for(100ms);
        }

        return !cancel_requested();
    }

    bool cancel_requested() const {
        return ctx_.shared_state && ctx_.shared_state->cancel_requested.load();
    }

    void set_active_nav_goal(const ExecutionContext::Nav2GoalHandle::SharedPtr& goal_handle) {
        if (!ctx_.shared_state) {
            return;
        }
        std::lock_guard<std::mutex> lock(ctx_.shared_state->nav_goal_mutex);
        ctx_.shared_state->active_nav_goal = goal_handle;
    }

    void clear_active_nav_goal() {
        if (!ctx_.shared_state) {
            return;
        }
        std::lock_guard<std::mutex> lock(ctx_.shared_state->nav_goal_mutex);
        ctx_.shared_state->active_nav_goal.reset();
    }
};

}  // namespace executive

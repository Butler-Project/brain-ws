#pragma once

#include <atomic>
#include <condition_variable>
#include <mutex>
#include <rclcpp/rclcpp.hpp>
#include <rclcpp_action/rclcpp_action.hpp>
#include <tf2_ros/buffer.h>
#include <tf2_ros/transform_listener.h>
#include <high_level_reasoning_interface/msg/system_state.hpp>
#include <high_level_reasoning_interface/action/execute_command.hpp>
#include <high_level_reasoning_interface/action/system_operative_check.hpp>
#include "executive/execution_context.h"
#include "executive/command_factory.h"
#include "executive/landmark_registry.h"

class ExecutiveNode : public rclcpp::Node {
public:
    using ExecuteCommand = high_level_reasoning_interface::action::ExecuteCommand;
    using ExecuteGoalHandle = rclcpp_action::ServerGoalHandle<ExecuteCommand>;
    using SystemState = high_level_reasoning_interface::msg::SystemState;
    using SystemOperativeCheck = high_level_reasoning_interface::action::SystemOperativeCheck;
    using NavigateToPose = nav2_msgs::action::NavigateToPose;

    ExecutiveNode();

private:
    static std::string normalize_command_name(const std::string& command);

    void synchronize_startup();
    void aggregated_state_callback(const SystemState::SharedPtr msg);
    std::string startup_blocker_description_locked() const;
    void build_commands();

    bool check_operative(std::string& error_out);
    void execute_cancel_command(const std::shared_ptr<ExecuteGoalHandle> goal_handle);
    bool cancel_active_navigation(std::string& error_out);
    bool navigate_to_position(
        const executive::Position& target,
        const std::function<void(const std::string&)>& on_progress,
        const std::string& label,
        bool track_cancellation);

    rclcpp_action::GoalResponse handle_goal(
        const rclcpp_action::GoalUUID& uuid,
        std::shared_ptr<const ExecuteCommand::Goal> goal);
    rclcpp_action::CancelResponse handle_cancel(
        const std::shared_ptr<ExecuteGoalHandle> goal_handle);
    void handle_accepted(
        const std::shared_ptr<ExecuteGoalHandle> goal_handle);

    void execute(const std::shared_ptr<ExecuteGoalHandle> goal_handle);

    rclcpp_action::Server<ExecuteCommand>::SharedPtr action_server_;
    rclcpp::Subscription<SystemState>::SharedPtr aggregated_state_sub_;
    rclcpp_action::Client<SystemOperativeCheck>::SharedPtr operative_client_;
    rclcpp_action::Client<NavigateToPose>::SharedPtr nav2_client_;

    std::shared_ptr<tf2_ros::Buffer> tf_buffer_;
    std::shared_ptr<tf2_ros::TransformListener> tf_listener_;
    rclcpp::TimerBase::SharedPtr startup_timer_;

    executive::Position home_position_;
    bool home_saved_{false};
    SystemState aggregated_state_;
    bool aggregated_state_received_{false};
    std::mutex startup_mutex_;
    std::string last_startup_blocker_;
    std::shared_ptr<executive::ExecutionContext::SharedState> execution_shared_state_;
    std::mutex execution_state_mutex_;
    std::condition_variable execution_state_cv_;
    bool command_in_progress_{false};

    std::unique_ptr<executive::CommandFactory> command_factory_;
    std::shared_ptr<executive::LandmarkRegistry> landmark_registry_;
};

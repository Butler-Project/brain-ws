#pragma once

#include <rclcpp/rclcpp.hpp>
#include <rclcpp_action/rclcpp_action.hpp>
#include <high_level_reasoning_interface/msg/system_state.hpp>
#include <high_level_reasoning_interface/action/system_operative_check.hpp>
#include <map>
#include <mutex>
#include <string>

class ModelManagerNode : public rclcpp::Node {
public:
    using SystemState = high_level_reasoning_interface::msg::SystemState;
    using SystemOperativeCheck = high_level_reasoning_interface::action::SystemOperativeCheck;
    using GoalHandle = rclcpp_action::ServerGoalHandle<SystemOperativeCheck>;

    ModelManagerNode();

private:
    void state_callback(const SystemState::SharedPtr msg);
    void log_incoming_state_locked(const SystemState::SharedPtr msg);
    std::string build_incoming_state_summary(const SystemState::SharedPtr msg) const;
    void log_aggregated_state_locked();
    std::string build_aggregated_state_summary_locked() const;
    bool is_field_known_locked(uint8_t field) const;
    bool evaluate_operative_locked(std::vector<std::string>& issues) const;

    rclcpp_action::GoalResponse handle_goal(
        const rclcpp_action::GoalUUID& uuid,
        std::shared_ptr<const SystemOperativeCheck::Goal> goal);
    rclcpp_action::CancelResponse handle_cancel(
        const std::shared_ptr<GoalHandle> goal_handle);
    void handle_accepted(
        const std::shared_ptr<GoalHandle> goal_handle);

    rclcpp::Subscription<SystemState>::SharedPtr state_sub_;
    rclcpp::Publisher<SystemState>::SharedPtr aggregated_state_pub_;
    rclcpp_action::Server<SystemOperativeCheck>::SharedPtr action_server_;

    std::mutex state_mutex_;
    SystemState aggregated_state_;
    uint8_t aggregated_valid_fields_{0};
    std::map<uint8_t, std::string> last_logged_incoming_summaries_;
    std::string last_logged_summary_;
};

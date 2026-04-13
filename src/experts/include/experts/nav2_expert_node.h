#pragma once

#include <rclcpp/rclcpp.hpp>
#include <rclcpp_action/rclcpp_action.hpp>
#include <nav2_msgs/action/navigate_to_pose.hpp>
#include <high_level_reasoning_interface/msg/system_state.hpp>

class Nav2ExpertNode : public rclcpp::Node {
public:
    using SystemState = high_level_reasoning_interface::msg::SystemState;
    using NavigateToPose = nav2_msgs::action::NavigateToPose;

    Nav2ExpertNode();

private:
    void timer_callback();

    rclcpp_action::Client<NavigateToPose>::SharedPtr nav2_client_;
    rclcpp::Publisher<SystemState>::SharedPtr pub_;
    rclcpp::TimerBase::SharedPtr timer_;
};

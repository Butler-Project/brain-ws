#pragma once

#include <rclcpp/rclcpp.hpp>
#include <lifecycle_msgs/srv/get_state.hpp>
#include <high_level_reasoning_interface/msg/system_state.hpp>

class AmclExpertNode : public rclcpp::Node {
public:
    using SystemState = high_level_reasoning_interface::msg::SystemState;
    using GetState = lifecycle_msgs::srv::GetState;

    AmclExpertNode();

private:
    void timer_callback();
    void publish_state(uint8_t amcl_state);

    rclcpp::Client<GetState>::SharedPtr amcl_state_client_;
    rclcpp::Publisher<SystemState>::SharedPtr pub_;
    rclcpp::TimerBase::SharedPtr timer_;
};

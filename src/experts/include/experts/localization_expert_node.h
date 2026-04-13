#pragma once

#include <rclcpp/rclcpp.hpp>
#include <tf2_ros/buffer.h>
#include <tf2_ros/transform_listener.h>
#include <high_level_reasoning_interface/msg/system_state.hpp>

class LocalizationExpertNode : public rclcpp::Node {
public:
    using SystemState = high_level_reasoning_interface::msg::SystemState;

    LocalizationExpertNode();

private:
    void timer_callback();

    rclcpp::Publisher<SystemState>::SharedPtr pub_;
    rclcpp::TimerBase::SharedPtr timer_;

    std::shared_ptr<tf2_ros::Buffer> tf_buffer_;
    std::shared_ptr<tf2_ros::TransformListener> tf_listener_;
};

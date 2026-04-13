#pragma once

#include <rclcpp/rclcpp.hpp>
#include <visualization_msgs/msg/marker_array.hpp>
#include <high_level_reasoning_interface/msg/system_state.hpp>
#include <vector>
#include <string>

class LandmarksExpertNode : public rclcpp::Node {
public:
    using SystemState = high_level_reasoning_interface::msg::SystemState;

    LandmarksExpertNode();

private:
    void landmarks_callback(const visualization_msgs::msg::MarkerArray::SharedPtr msg);
    void timer_callback();

    rclcpp::Subscription<visualization_msgs::msg::MarkerArray>::SharedPtr landmarks_sub_;
    rclcpp::Publisher<SystemState>::SharedPtr pub_;
    rclcpp::TimerBase::SharedPtr timer_;

    bool landmarks_received_{false};
    std::vector<std::string> landmark_names_;
};

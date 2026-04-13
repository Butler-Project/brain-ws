#pragma once

#include <rclcpp/rclcpp.hpp>
#include <nav_msgs/msg/occupancy_grid.hpp>
#include <high_level_reasoning_interface/msg/system_state.hpp>

class MapExpertNode : public rclcpp::Node {
public:
    using SystemState = high_level_reasoning_interface::msg::SystemState;

    MapExpertNode();

private:
    void map_callback(const nav_msgs::msg::OccupancyGrid::SharedPtr msg);
    void timer_callback();

    rclcpp::Subscription<nav_msgs::msg::OccupancyGrid>::SharedPtr map_sub_;
    rclcpp::Publisher<SystemState>::SharedPtr pub_;
    rclcpp::TimerBase::SharedPtr timer_;

    bool map_received_{false};
    rclcpp::Time last_map_time_;
};

#pragma once

#include <rclcpp/rclcpp.hpp>
#include <sensor_msgs/msg/laser_scan.hpp>
#include <nav_msgs/msg/odometry.hpp>
#include <high_level_reasoning_interface/msg/system_state.hpp>
#include <chrono>

class SensorExpertNode : public rclcpp::Node {
public:
    using SystemState = high_level_reasoning_interface::msg::SystemState;

    SensorExpertNode();

private:
    void scan_callback(const sensor_msgs::msg::LaserScan::SharedPtr msg);
    void odom_callback(const nav_msgs::msg::Odometry::SharedPtr msg);
    void timer_callback();

    rclcpp::Subscription<sensor_msgs::msg::LaserScan>::SharedPtr scan_sub_;
    rclcpp::Subscription<nav_msgs::msg::Odometry>::SharedPtr odom_sub_;
    rclcpp::Publisher<SystemState>::SharedPtr pub_;
    rclcpp::TimerBase::SharedPtr timer_;

    rclcpp::Time last_scan_time_;
    rclcpp::Time last_odom_time_;
    bool scan_received_{false};
    bool odom_received_{false};

    static constexpr double TIMEOUT_SEC = 3.0;
};

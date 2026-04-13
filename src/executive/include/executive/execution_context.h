#pragma once

#include <atomic>
#include <rclcpp/rclcpp.hpp>
#include <rclcpp_action/rclcpp_action.hpp>
#include <nav2_msgs/action/navigate_to_pose.hpp>
#include <geometry_msgs/msg/pose_stamped.hpp>
#include <memory>
#include <mutex>
#include <string>

namespace executive {

struct Position {
    double x{0.0};
    double y{0.0};

    double distance_to(const Position& other) const {
        double dx = x - other.x;
        double dy = y - other.y;
        return std::sqrt(dx * dx + dy * dy);
    }
};

struct ExecutionContext {
    using NavigateToPose = nav2_msgs::action::NavigateToPose;
    using Nav2Client = rclcpp_action::Client<NavigateToPose>;
    using Nav2GoalHandle = rclcpp_action::ClientGoalHandle<NavigateToPose>;

    struct SharedState {
        std::atomic_bool cancel_requested{false};
        std::mutex nav_goal_mutex;
        Nav2GoalHandle::SharedPtr active_nav_goal;
    };

    rclcpp::Node::SharedPtr node;
    Nav2Client::SharedPtr nav2_client;
    std::shared_ptr<SharedState> shared_state;
    Position home;
    double wait_time_seconds{10.0};

    geometry_msgs::msg::PoseStamped to_pose_stamped(const Position& pos) const {
        geometry_msgs::msg::PoseStamped pose;
        pose.header.frame_id = "map";
        pose.header.stamp = node->get_clock()->now();
        pose.pose.position.x = pos.x;
        pose.pose.position.y = pos.y;
        pose.pose.position.z = 0.0;
        pose.pose.orientation.w = 1.0;
        return pose;
    }
};

}  // namespace executive

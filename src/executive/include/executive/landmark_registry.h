#pragma once

#include <rclcpp/rclcpp.hpp>
#include <visualization_msgs/msg/marker_array.hpp>
#include "executive/execution_context.h"
#include "executive/high_level_command.h"
#include <map>
#include <mutex>
#include <string>
#include <vector>

namespace executive {

class LandmarkRegistry {
public:
    explicit LandmarkRegistry(rclcpp::Node* node)
        : node_(node)
    {
        sub_ = node_->create_subscription<visualization_msgs::msg::MarkerArray>(
            "/landmarks", rclcpp::QoS(1).transient_local(),
            std::bind(&LandmarkRegistry::landmarks_callback, this, std::placeholders::_1));
    }

    // Check if a landmark name exists
    bool is_valid(const std::string& name) const {
        std::lock_guard<std::mutex> lock(mutex_);
        return landmarks_.count(name) > 0;
    }

    // Validate a list of names, returns invalid ones
    std::vector<std::string> find_invalid(const std::vector<std::string>& names) const {
        std::lock_guard<std::mutex> lock(mutex_);
        std::vector<std::string> invalid;
        for (const auto& name : names) {
            if (landmarks_.count(name) == 0) {
                invalid.push_back(name);
            }
        }
        return invalid;
    }

    // Resolve landmark names to Landmark structs (skips unknown)
    std::vector<Landmark> resolve(const std::vector<std::string>& names) const {
        std::lock_guard<std::mutex> lock(mutex_);
        std::vector<Landmark> result;
        for (const auto& name : names) {
            auto it = landmarks_.find(name);
            if (it != landmarks_.end()) {
                result.push_back({name, it->second});
            }
        }
        return result;
    }

    // Get ALL available landmarks
    std::vector<Landmark> get_all() const {
        std::lock_guard<std::mutex> lock(mutex_);
        std::vector<Landmark> result;
        for (const auto& [name, pos] : landmarks_) {
            result.push_back({name, pos});
        }
        return result;
    }

    // Get all available landmark names
    std::vector<std::string> get_names() const {
        std::lock_guard<std::mutex> lock(mutex_);
        std::vector<std::string> result;
        for (const auto& [name, _] : landmarks_) {
            result.push_back(name);
        }
        return result;
    }

    bool has_landmarks() const {
        std::lock_guard<std::mutex> lock(mutex_);
        return !landmarks_.empty();
    }

private:
    void landmarks_callback(const visualization_msgs::msg::MarkerArray::SharedPtr msg) {
        std::lock_guard<std::mutex> lock(mutex_);
        landmarks_.clear();

        for (const auto& marker : msg->markers) {
            if (!marker.text.empty()) {
                Position pos;
                pos.x = marker.pose.position.x;
                pos.y = marker.pose.position.y;
                landmarks_[marker.text] = pos;
            }
        }

        RCLCPP_INFO(node_->get_logger(), "LandmarkRegistry updated: %zu landmarks available.",
            landmarks_.size());
    }

    rclcpp::Node* node_;
    rclcpp::Subscription<visualization_msgs::msg::MarkerArray>::SharedPtr sub_;
    mutable std::mutex mutex_;
    std::map<std::string, Position> landmarks_;
};

}  // namespace executive

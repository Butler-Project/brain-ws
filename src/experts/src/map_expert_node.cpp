#include "experts/map_expert_node.h"

using namespace std::chrono_literals;

MapExpertNode::MapExpertNode()
    : Node("map_expert")
{
    map_sub_ = create_subscription<nav_msgs::msg::OccupancyGrid>(
        "/map", rclcpp::QoS(1).transient_local(),
        std::bind(&MapExpertNode::map_callback, this, std::placeholders::_1));

    pub_ = create_publisher<SystemState>("HighLevelSystemState", 10);
    timer_ = create_wall_timer(1s, std::bind(&MapExpertNode::timer_callback, this));

    RCLCPP_INFO(get_logger(), "Map expert started. Monitoring /map topic.");
}

void MapExpertNode::map_callback(const nav_msgs::msg::OccupancyGrid::SharedPtr /*msg*/)
{
    map_received_ = true;
    last_map_time_ = now();
}

void MapExpertNode::timer_callback()
{
    SystemState state;
    state.stamp = now();
    state.valid_fields = SystemState::FIELD_MAP;

    if (map_received_) {
        state.map_state = SystemState::MAP_HAS_MAP;
    } else {
        state.map_state = SystemState::MAP_NOT_AVAILABLE;
    }

    pub_->publish(state);
}

int main(int argc, char** argv)
{
    rclcpp::init(argc, argv);
    rclcpp::spin(std::make_shared<MapExpertNode>());
    rclcpp::shutdown();
    return 0;
}

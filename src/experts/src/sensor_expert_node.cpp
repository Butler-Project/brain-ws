#include "experts/sensor_expert_node.h"

using namespace std::chrono_literals;

SensorExpertNode::SensorExpertNode()
    : Node("sensor_expert")
{
    scan_sub_ = create_subscription<sensor_msgs::msg::LaserScan>(
        "/scan", 10,
        std::bind(&SensorExpertNode::scan_callback, this, std::placeholders::_1));

    odom_sub_ = create_subscription<nav_msgs::msg::Odometry>(
        "/odom", 10,
        std::bind(&SensorExpertNode::odom_callback, this, std::placeholders::_1));

    pub_ = create_publisher<SystemState>("HighLevelSystemState", 10);
    timer_ = create_wall_timer(1s, std::bind(&SensorExpertNode::timer_callback, this));

    RCLCPP_INFO(get_logger(), "Sensor expert started. Monitoring /scan and /odom topics.");
}

void SensorExpertNode::scan_callback(const sensor_msgs::msg::LaserScan::SharedPtr /*msg*/)
{
    scan_received_ = true;
    last_scan_time_ = now();
}

void SensorExpertNode::odom_callback(const nav_msgs::msg::Odometry::SharedPtr /*msg*/)
{
    odom_received_ = true;
    last_odom_time_ = now();
}

void SensorExpertNode::timer_callback()
{
    SystemState state;
    state.stamp = now();
    state.valid_fields = SystemState::FIELD_LIDAR | SystemState::FIELD_ODOMETRY;
    auto current_time = now();

    // Check lidar
    if (scan_received_ && (current_time - last_scan_time_).seconds() < TIMEOUT_SEC) {
        state.lidar_state = SystemState::LIDAR_OK;
    } else {
        state.lidar_state = SystemState::LIDAR_NOK;
    }

    // Check odometry
    if (odom_received_ && (current_time - last_odom_time_).seconds() < TIMEOUT_SEC) {
        state.odometry_state = SystemState::ODOMETRY_OK;
    } else {
        state.odometry_state = SystemState::ODOMETRY_NOK;
    }

    pub_->publish(state);
}

int main(int argc, char** argv)
{
    rclcpp::init(argc, argv);
    rclcpp::spin(std::make_shared<SensorExpertNode>());
    rclcpp::shutdown();
    return 0;
}

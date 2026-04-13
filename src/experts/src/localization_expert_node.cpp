#include "experts/localization_expert_node.h"
#include <tf2/exceptions.h>

using namespace std::chrono_literals;

LocalizationExpertNode::LocalizationExpertNode()
    : Node("localization_expert")
{
    tf_buffer_ = std::make_shared<tf2_ros::Buffer>(get_clock());
    tf_listener_ = std::make_shared<tf2_ros::TransformListener>(*tf_buffer_);

    pub_ = create_publisher<SystemState>("HighLevelSystemState", 10);
    timer_ = create_wall_timer(1s, std::bind(&LocalizationExpertNode::timer_callback, this));

    RCLCPP_INFO(get_logger(), "Localization expert started. Monitoring map -> base_link TF.");
}

void LocalizationExpertNode::timer_callback()
{
    SystemState state;
    state.stamp = now();
    state.valid_fields = SystemState::FIELD_LOCALIZATION;

    try {
        tf_buffer_->lookupTransform("map", "base_link", tf2::TimePointZero);
        state.current_location = SystemState::LOCALIZATION_OK;
    } catch (const tf2::TransformException&) {
        state.current_location = SystemState::LOCALIZATION_NOK;
    }

    pub_->publish(state);
}

int main(int argc, char** argv)
{
    rclcpp::init(argc, argv);
    rclcpp::spin(std::make_shared<LocalizationExpertNode>());
    rclcpp::shutdown();
    return 0;
}

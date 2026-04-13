#include "experts/landmarks_expert_node.h"

using namespace std::chrono_literals;

LandmarksExpertNode::LandmarksExpertNode()
    : Node("landmarks_expert")
{
    landmarks_sub_ = create_subscription<visualization_msgs::msg::MarkerArray>(
        "/landmarks", rclcpp::QoS(1).transient_local(),
        std::bind(&LandmarksExpertNode::landmarks_callback, this, std::placeholders::_1));

    pub_ = create_publisher<SystemState>("HighLevelSystemState", 10);
    timer_ = create_wall_timer(1s, std::bind(&LandmarksExpertNode::timer_callback, this));

    RCLCPP_INFO(get_logger(), "Landmarks expert started. Monitoring /landmarks topic.");
}

void LandmarksExpertNode::landmarks_callback(
    const visualization_msgs::msg::MarkerArray::SharedPtr msg)
{
    landmark_names_.clear();
    for (const auto& marker : msg->markers) {
        if (!marker.text.empty()) {
            landmark_names_.push_back(marker.text);
        }
    }
    landmarks_received_ = !landmark_names_.empty();

    RCLCPP_INFO(get_logger(), "Received %zu landmarks.", landmark_names_.size());
}

void LandmarksExpertNode::timer_callback()
{
    SystemState state;
    state.stamp = now();
    state.valid_fields = SystemState::FIELD_LANDMARKS;

    if (landmarks_received_) {
        state.landmarks_state = SystemState::LANDMARKS_OK;
        state.landmark_names = landmark_names_;
    } else {
        state.landmarks_state = SystemState::LANDMARKS_NOK;
    }

    pub_->publish(state);
}

int main(int argc, char** argv)
{
    rclcpp::init(argc, argv);
    rclcpp::spin(std::make_shared<LandmarksExpertNode>());
    rclcpp::shutdown();
    return 0;
}

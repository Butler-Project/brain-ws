#include "experts/nav2_expert_node.h"

using namespace std::chrono_literals;

Nav2ExpertNode::Nav2ExpertNode()
    : Node("nav2_expert")
{
    nav2_client_ = rclcpp_action::create_client<NavigateToPose>(
        this, "navigate_to_pose");

    pub_ = create_publisher<SystemState>("HighLevelSystemState", 10);
    timer_ = create_wall_timer(2s, std::bind(&Nav2ExpertNode::timer_callback, this));

    RCLCPP_INFO(get_logger(), "Nav2 expert started. Monitoring navigate_to_pose action server.");
}

void Nav2ExpertNode::timer_callback()
{
    SystemState state;
    state.stamp = now();
    state.valid_fields = SystemState::FIELD_NAV2;

    if (nav2_client_->action_server_is_ready()) {
        state.nav2_state = SystemState::NAV2_OK;
    } else {
        state.nav2_state = SystemState::NAV2_NOK;
    }

    pub_->publish(state);
}

int main(int argc, char** argv)
{
    rclcpp::init(argc, argv);
    rclcpp::spin(std::make_shared<Nav2ExpertNode>());
    rclcpp::shutdown();
    return 0;
}

#include "experts/amcl_expert_node.h"
#include <lifecycle_msgs/msg/state.hpp>

using namespace std::chrono_literals;

AmclExpertNode::AmclExpertNode()
    : Node("amcl_expert")
{
    amcl_state_client_ = create_client<GetState>("/amcl/get_state");
    pub_ = create_publisher<SystemState>("HighLevelSystemState", 10);
    timer_ = create_wall_timer(2s, std::bind(&AmclExpertNode::timer_callback, this));

    RCLCPP_INFO(get_logger(), "AMCL expert started. Monitoring /amcl lifecycle state.");
}

void AmclExpertNode::timer_callback()
{
    RCLCPP_INFO(get_logger(), "timer_callback triggered");

    if (!amcl_state_client_->wait_for_service(0s)) {
        RCLCPP_WARN(get_logger(), "AMCL service /amcl/get_state not discovered yet");
        publish_state(SystemState::AMCL_NOK);
        return;
    }

    RCLCPP_INFO(get_logger(), "AMCL service discovered, sending async request");

    auto request = std::make_shared<GetState::Request>();
    amcl_state_client_->async_send_request(request,
        [this](rclcpp::Client<GetState>::SharedFuture future) {
            const auto response = future.get();
            RCLCPP_INFO(get_logger(), "AMCL get_state response: id=%d label='%s'",
                        response->current_state.id, response->current_state.label.c_str());

            if (response->current_state.id == lifecycle_msgs::msg::State::PRIMARY_STATE_ACTIVE) {
                RCLCPP_INFO(get_logger(), "AMCL is ACTIVE -> publishing AMCL_OK");
                publish_state(SystemState::AMCL_OK);
            } else {
                RCLCPP_WARN(get_logger(), "AMCL is NOT active (id=%d) -> publishing AMCL_NOK",
                            response->current_state.id);
                publish_state(SystemState::AMCL_NOK);
            }
        });
}

void AmclExpertNode::publish_state(uint8_t amcl_state)
{
    SystemState state;
    state.stamp = now();
    state.valid_fields = SystemState::FIELD_AMCL;
    state.amcl_state = amcl_state;
    pub_->publish(state);
    RCLCPP_INFO(get_logger(), "Published AMCL state: %s",
                amcl_state == SystemState::AMCL_OK ? "OK" : "NOK");
}

int main(int argc, char** argv)
{
    rclcpp::init(argc, argv);
    rclcpp::spin(std::make_shared<AmclExpertNode>());
    rclcpp::shutdown();
    return 0;
}

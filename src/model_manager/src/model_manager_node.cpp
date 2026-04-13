#include "model_manager/model_manager_node.h"
#include <sstream>

ModelManagerNode::ModelManagerNode()
    : Node("model_manager")
{
    state_sub_ = create_subscription<SystemState>(
        "HighLevelSystemState", 10,
        std::bind(&ModelManagerNode::state_callback, this, std::placeholders::_1));
    aggregated_state_pub_ = create_publisher<SystemState>(
        "AggregatedSystemState", rclcpp::QoS(1).transient_local());

    action_server_ = rclcpp_action::create_server<SystemOperativeCheck>(
        this, "system_operative_check",
        std::bind(&ModelManagerNode::handle_goal, this,
                  std::placeholders::_1, std::placeholders::_2),
        std::bind(&ModelManagerNode::handle_cancel, this,
                  std::placeholders::_1),
        std::bind(&ModelManagerNode::handle_accepted, this,
                  std::placeholders::_1));

    RCLCPP_INFO(get_logger(),
        "ModelManager ready. Subscribed to HighLevelSystemState. Action: system_operative_check");
}

void ModelManagerNode::state_callback(const SystemState::SharedPtr msg)
{
    std::lock_guard<std::mutex> lock(state_mutex_);
    uint8_t fields = msg->valid_fields;
    log_incoming_state_locked(msg);
    aggregated_valid_fields_ |= fields;

    if (fields & SystemState::FIELD_MAP) {
        aggregated_state_.map_state = msg->map_state;
    }
    if (fields & SystemState::FIELD_LOCALIZATION) {
        aggregated_state_.current_location = msg->current_location;
    }
    if (fields & SystemState::FIELD_LIDAR) {
        aggregated_state_.lidar_state = msg->lidar_state;
    }
    if (fields & SystemState::FIELD_ODOMETRY) {
        aggregated_state_.odometry_state = msg->odometry_state;
    }
    if (fields & SystemState::FIELD_LANDMARKS) {
        aggregated_state_.landmarks_state = msg->landmarks_state;
        aggregated_state_.landmark_names = msg->landmark_names;
    }
    if (fields & SystemState::FIELD_NAV2) {
        aggregated_state_.nav2_state = msg->nav2_state;
    }
    if (fields & SystemState::FIELD_AMCL) {
        aggregated_state_.amcl_state = msg->amcl_state;
    }

    aggregated_state_.stamp = msg->stamp;
    aggregated_state_.valid_fields = aggregated_valid_fields_;

    aggregated_state_pub_->publish(aggregated_state_);
    log_aggregated_state_locked();
}

void ModelManagerNode::log_incoming_state_locked(const SystemState::SharedPtr msg)
{
    const std::string summary = build_incoming_state_summary(msg);
    const auto it = last_logged_incoming_summaries_.find(msg->valid_fields);
    if (it != last_logged_incoming_summaries_.end() && it->second == summary) {
        return;
    }

    last_logged_incoming_summaries_[msg->valid_fields] = summary;
    RCLCPP_INFO(get_logger(), "%s", summary.c_str());
}

std::string ModelManagerNode::build_incoming_state_summary(const SystemState::SharedPtr msg) const
{
    std::ostringstream summary;
    summary << "Incoming HighLevelSystemState | valid_fields=" << static_cast<int>(msg->valid_fields);

    if (msg->valid_fields & SystemState::FIELD_MAP) {
        summary << ", map=" << (msg->map_state == SystemState::MAP_HAS_MAP ? "OK" : "NOK");
    }
    if (msg->valid_fields & SystemState::FIELD_LOCALIZATION) {
        summary << ", localization=" <<
            (msg->current_location == SystemState::LOCALIZATION_OK ? "OK" : "NOK");
    }
    if (msg->valid_fields & SystemState::FIELD_LIDAR) {
        summary << ", lidar=" << (msg->lidar_state == SystemState::LIDAR_OK ? "OK" : "NOK");
    }
    if (msg->valid_fields & SystemState::FIELD_ODOMETRY) {
        summary << ", odometry=" <<
            (msg->odometry_state == SystemState::ODOMETRY_OK ? "OK" : "NOK");
    }
    if (msg->valid_fields & SystemState::FIELD_LANDMARKS) {
        summary << ", landmarks=" <<
            (msg->landmarks_state == SystemState::LANDMARKS_OK ? "OK" : "NOK");
        summary << ", landmarks_count=" << msg->landmark_names.size();
        if (!msg->landmark_names.empty()) {
            summary << " [";
            for (size_t i = 0; i < msg->landmark_names.size(); ++i) {
                if (i > 0) {
                    summary << ", ";
                }
                summary << msg->landmark_names[i];
            }
            summary << "]";
        }
    }
    if (msg->valid_fields & SystemState::FIELD_NAV2) {
        summary << ", nav2=" << (msg->nav2_state == SystemState::NAV2_OK ? "OK" : "NOK");
    }
    if (msg->valid_fields & SystemState::FIELD_AMCL) {
        summary << ", amcl=" << (msg->amcl_state == SystemState::AMCL_OK ? "OK" : "NOK");
    }

    return summary.str();
}

void ModelManagerNode::log_aggregated_state_locked()
{
    const std::string summary = build_aggregated_state_summary_locked();
    if (summary == last_logged_summary_) {
        return;
    }

    last_logged_summary_ = summary;
    RCLCPP_INFO(get_logger(), "%s", summary.c_str());
}

std::string ModelManagerNode::build_aggregated_state_summary_locked() const
{
    auto state_label = [this](bool known, bool ok) -> std::string {
        if (!known) {
            return "UNKNOWN";
        }
        return ok ? "OK" : "NOK";
    };

    std::ostringstream summary;
    summary << "Aggregated system state | "
            << "map=" << state_label(
                aggregated_valid_fields_ & SystemState::FIELD_MAP,
                aggregated_state_.map_state == SystemState::MAP_HAS_MAP)
            << ", localization=" << state_label(
                aggregated_valid_fields_ & SystemState::FIELD_LOCALIZATION,
                aggregated_state_.current_location == SystemState::LOCALIZATION_OK)
            << ", lidar=" << state_label(
                aggregated_valid_fields_ & SystemState::FIELD_LIDAR,
                aggregated_state_.lidar_state == SystemState::LIDAR_OK)
            << ", odometry=" << state_label(
                aggregated_valid_fields_ & SystemState::FIELD_ODOMETRY,
                aggregated_state_.odometry_state == SystemState::ODOMETRY_OK)
            << ", landmarks=" << state_label(
                aggregated_valid_fields_ & SystemState::FIELD_LANDMARKS,
                aggregated_state_.landmarks_state == SystemState::LANDMARKS_OK)
            << ", nav2=" << state_label(
                aggregated_valid_fields_ & SystemState::FIELD_NAV2,
                aggregated_state_.nav2_state == SystemState::NAV2_OK)
            << ", amcl=" << state_label(
                aggregated_valid_fields_ & SystemState::FIELD_AMCL,
                aggregated_state_.amcl_state == SystemState::AMCL_OK);

    if (aggregated_valid_fields_ & SystemState::FIELD_LANDMARKS) {
        summary << ", landmarks_count=" << aggregated_state_.landmark_names.size();
        if (!aggregated_state_.landmark_names.empty()) {
            summary << " [";
            for (size_t i = 0; i < aggregated_state_.landmark_names.size(); ++i) {
                if (i > 0) {
                    summary << ", ";
                }
                summary << aggregated_state_.landmark_names[i];
            }
            summary << "]";
        }
    }

    return summary.str();
}

bool ModelManagerNode::is_field_known_locked(uint8_t field) const
{
    return (aggregated_valid_fields_ & field) != 0;
}

bool ModelManagerNode::evaluate_operative_locked(std::vector<std::string>& issues) const
{
    issues.clear();

    if (!is_field_known_locked(SystemState::FIELD_MAP)) {
        issues.push_back("map_unknown");
    } else if (aggregated_state_.map_state != SystemState::MAP_HAS_MAP) {
        issues.push_back("map_not_available");
    }

    if (!is_field_known_locked(SystemState::FIELD_LOCALIZATION)) {
        issues.push_back("localization_unknown");
    } else if (aggregated_state_.current_location != SystemState::LOCALIZATION_OK) {
        issues.push_back("no_localization");
    }

    if (!is_field_known_locked(SystemState::FIELD_LIDAR)) {
        issues.push_back("lidar_unknown");
    } else if (aggregated_state_.lidar_state != SystemState::LIDAR_OK) {
        issues.push_back("lidar_nok");
    }

    if (!is_field_known_locked(SystemState::FIELD_ODOMETRY)) {
        issues.push_back("odometry_unknown");
    } else if (aggregated_state_.odometry_state != SystemState::ODOMETRY_OK) {
        issues.push_back("odometry_nok");
    }

    if (!is_field_known_locked(SystemState::FIELD_LANDMARKS)) {
        issues.push_back("landmarks_unknown");
    } else if (aggregated_state_.landmarks_state != SystemState::LANDMARKS_OK) {
        issues.push_back("landmarks_nok");
    }

    if (!is_field_known_locked(SystemState::FIELD_NAV2)) {
        issues.push_back("nav2_unknown");
    } else if (aggregated_state_.nav2_state != SystemState::NAV2_OK) {
        issues.push_back("nav2_nok");
    }

    if (!is_field_known_locked(SystemState::FIELD_AMCL)) {
        issues.push_back("amcl_unknown");
    } else if (aggregated_state_.amcl_state != SystemState::AMCL_OK) {
        issues.push_back("amcl_nok");
    }

    return issues.empty();
}

rclcpp_action::GoalResponse ModelManagerNode::handle_goal(
    const rclcpp_action::GoalUUID& /*uuid*/,
    std::shared_ptr<const SystemOperativeCheck::Goal> /*goal*/)
{
    return rclcpp_action::GoalResponse::ACCEPT_AND_EXECUTE;
}

rclcpp_action::CancelResponse ModelManagerNode::handle_cancel(
    const std::shared_ptr<GoalHandle> /*goal_handle*/)
{
    return rclcpp_action::CancelResponse::ACCEPT;
}

void ModelManagerNode::handle_accepted(
    const std::shared_ptr<GoalHandle> goal_handle)
{
    auto result = std::make_shared<SystemOperativeCheck::Result>();

    std::lock_guard<std::mutex> lock(state_mutex_);

    result->operative = evaluate_operative_locked(result->issues);

    RCLCPP_INFO(get_logger(), "System operative: %s", result->operative ? "YES" : "NO");
    goal_handle->succeed(result);
}

int main(int argc, char** argv)
{
    rclcpp::init(argc, argv);
    rclcpp::spin(std::make_shared<ModelManagerNode>());
    rclcpp::shutdown();
    return 0;
}

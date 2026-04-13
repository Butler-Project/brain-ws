#include "executive/executive_node.h"
#include <tf2/exceptions.h>
#include <algorithm>
#include <cctype>
#include <thread>

using namespace std::chrono_literals;

ExecutiveNode::ExecutiveNode()
    : Node("executive")
{
    tf_buffer_ = std::make_shared<tf2_ros::Buffer>(get_clock());
    tf_listener_ = std::make_shared<tf2_ros::TransformListener>(*tf_buffer_);
    execution_shared_state_ = std::make_shared<executive::ExecutionContext::SharedState>();

    operative_client_ = rclcpp_action::create_client<SystemOperativeCheck>(
        this, "system_operative_check");

    nav2_client_ = rclcpp_action::create_client<NavigateToPose>(
        this, "navigate_to_pose");
    aggregated_state_sub_ = create_subscription<SystemState>(
        "AggregatedSystemState", rclcpp::QoS(1).transient_local(),
        std::bind(&ExecutiveNode::aggregated_state_callback, this, std::placeholders::_1));

    // LandmarkRegistry subscribes to /landmarks and keeps them up to date
    landmark_registry_ = std::make_shared<executive::LandmarkRegistry>(
        this);

    action_server_ = rclcpp_action::create_server<ExecuteCommand>(
        this, "execute_command",
        std::bind(&ExecutiveNode::handle_goal, this,
                  std::placeholders::_1, std::placeholders::_2),
        std::bind(&ExecutiveNode::handle_cancel, this,
                  std::placeholders::_1),
        std::bind(&ExecutiveNode::handle_accepted, this,
                  std::placeholders::_1));

    synchronize_startup();

    RCLCPP_INFO(get_logger(),
        "Executive node starting. Waiting for synchronized system state before registering commands...");
}

void ExecutiveNode::synchronize_startup()
{
    startup_timer_ = create_wall_timer(1s, [this]() {
        if (home_saved_ || command_factory_) {
            return;
        }

        std::string blocker;
        {
            std::lock_guard<std::mutex> lock(startup_mutex_);
            blocker = startup_blocker_description_locked();
            if (blocker != last_startup_blocker_) {
                last_startup_blocker_ = blocker;
                if (!blocker.empty()) {
                    RCLCPP_INFO(get_logger(), "Executive startup waiting: %s", blocker.c_str());
                }
            }
        }

        if (!blocker.empty()) {
            return;
        }

        try {
            auto transform = tf_buffer_->lookupTransform("map", "base_link", tf2::TimePointZero);
            home_position_.x = transform.transform.translation.x;
            home_position_.y = transform.transform.translation.y;
            home_saved_ = true;

            RCLCPP_INFO(get_logger(), "Home position saved: x=%.3f, y=%.3f",
                home_position_.x, home_position_.y);

            build_commands();
            startup_timer_->cancel();
        } catch (const tf2::TransformException& ex) {
            RCLCPP_INFO(get_logger(),
                "Executive startup waiting: map -> base_link not yet available in executive tf buffer (%s)",
                ex.what());
        }
    });
}

void ExecutiveNode::aggregated_state_callback(const SystemState::SharedPtr msg)
{
    std::lock_guard<std::mutex> lock(startup_mutex_);
    aggregated_state_ = *msg;
    aggregated_state_received_ = true;
}

std::string ExecutiveNode::startup_blocker_description_locked() const
{
    if (!aggregated_state_received_) {
        return "aggregated system state not received yet";
    }

    std::vector<std::string> blockers;
    const uint8_t fields = aggregated_state_.valid_fields;

    if (!(fields & SystemState::FIELD_MAP)) {
        blockers.push_back("map_unknown");
    } else if (aggregated_state_.map_state != SystemState::MAP_HAS_MAP) {
        blockers.push_back("map_not_available");
    }

    if (!(fields & SystemState::FIELD_LOCALIZATION)) {
        blockers.push_back("localization_unknown");
    } else if (aggregated_state_.current_location != SystemState::LOCALIZATION_OK) {
        blockers.push_back("no_localization");
    }

    if (!(fields & SystemState::FIELD_LIDAR)) {
        blockers.push_back("lidar_unknown");
    } else if (aggregated_state_.lidar_state != SystemState::LIDAR_OK) {
        blockers.push_back("lidar_nok");
    }

    if (!(fields & SystemState::FIELD_ODOMETRY)) {
        blockers.push_back("odometry_unknown");
    } else if (aggregated_state_.odometry_state != SystemState::ODOMETRY_OK) {
        blockers.push_back("odometry_nok");
    }

    if (!(fields & SystemState::FIELD_LANDMARKS)) {
        blockers.push_back("landmarks_unknown");
    } else if (aggregated_state_.landmarks_state != SystemState::LANDMARKS_OK) {
        blockers.push_back("landmarks_nok");
    }

    if (!(fields & SystemState::FIELD_NAV2)) {
        blockers.push_back("nav2_unknown");
    } else if (aggregated_state_.nav2_state != SystemState::NAV2_OK) {
        blockers.push_back("nav2_nok");
    }

    if (!(fields & SystemState::FIELD_AMCL)) {
        blockers.push_back("amcl_unknown");
    } else if (aggregated_state_.amcl_state != SystemState::AMCL_OK) {
        blockers.push_back("amcl_nok");
    }

    if (!blockers.empty()) {
        std::string description = "system not operative yet: ";
        for (size_t i = 0; i < blockers.size(); ++i) {
            if (i > 0) {
                description += ", ";
            }
            description += blockers[i];
        }
        return description;
    }

    if (!landmark_registry_->has_landmarks()) {
        return "landmark registry not populated yet";
    }

    if (!tf_buffer_->canTransform("map", "base_link", tf2::TimePointZero)) {
        return "map -> base_link not yet available in executive tf buffer";
    }

    return "";
}

void ExecutiveNode::build_commands()
{
    executive::ExecutionContext ctx;
    ctx.node = shared_from_this();
    ctx.nav2_client = nav2_client_;
    ctx.shared_state = execution_shared_state_;
    ctx.home = home_position_;

    command_factory_ = std::make_unique<executive::CommandFactory>(ctx);

    RCLCPP_INFO(get_logger(), "Commands registered: [%s]",
        command_factory_->available_commands().c_str());
    RCLCPP_INFO(get_logger(), "Executive node ready. Action: execute_command (plus special command: cancel)");
}

std::string ExecutiveNode::normalize_command_name(const std::string& command)
{
    std::string normalized;
    normalized.reserve(command.size());

    for (char ch : command) {
        if (std::isspace(static_cast<unsigned char>(ch))) {
            normalized.push_back('_');
            continue;
        }
        normalized.push_back(static_cast<char>(std::tolower(static_cast<unsigned char>(ch))));
    }

    return normalized;
}

bool ExecutiveNode::check_operative(std::string& error_out)
{
    if (!operative_client_->wait_for_action_server(5s)) {
        error_out = "system_operative_check action server not available";
        return false;
    }

    auto check_goal = SystemOperativeCheck::Goal();
    auto future = operative_client_->async_send_goal(check_goal);

    if (future.wait_for(5s) != std::future_status::ready) {
        error_out = "Failed to send operative check request";
        return false;
    }

    auto check_handle = future.get();
    if (!check_handle) {
        error_out = "Operative check goal rejected";
        return false;
    }

    auto result_future = operative_client_->async_get_result(check_handle);
    if (result_future.wait_for(5s) != std::future_status::ready) {
        error_out = "Timeout waiting for operative check result";
        return false;
    }

    auto check_result = result_future.get().result;

    if (!check_result->operative) {
        error_out.clear();
        for (size_t i = 0; i < check_result->issues.size(); ++i) {
            if (i > 0) error_out += ", ";
            error_out += check_result->issues[i];
        }
        return false;
    }

    return true;
}

rclcpp_action::GoalResponse ExecutiveNode::handle_goal(
    const rclcpp_action::GoalUUID& /*uuid*/,
    std::shared_ptr<const ExecuteCommand::Goal> goal)
{
    RCLCPP_INFO(get_logger(), "Received command: '%s' with %zu landmarks",
        goal->command.c_str(), goal->landmarks_to_visit.size());
    return rclcpp_action::GoalResponse::ACCEPT_AND_EXECUTE;
}

rclcpp_action::CancelResponse ExecutiveNode::handle_cancel(
    const std::shared_ptr<ExecuteGoalHandle> /*goal_handle*/)
{
    RCLCPP_INFO(get_logger(), "Command execution cancelled.");
    return rclcpp_action::CancelResponse::ACCEPT;
}

void ExecutiveNode::handle_accepted(
    const std::shared_ptr<ExecuteGoalHandle> goal_handle)
{
    std::thread([this, goal_handle]() { execute(goal_handle); }).detach();
}

void ExecutiveNode::execute(const std::shared_ptr<ExecuteGoalHandle> goal_handle)
{
    auto result = std::make_shared<ExecuteCommand::Result>();
    auto feedback = std::make_shared<ExecuteCommand::Feedback>();
    const auto& goal = goal_handle->get_goal();
    const auto command_name = normalize_command_name(goal->command);

    result->command_echo = command_name;

    if (command_name == "cancel") {
        execute_cancel_command(goal_handle);
        return;
    }

    // Step 1: Check commands are built
    if (!command_factory_) {
        result->status = "not_able_to_execute";
        result->error_description = "Executive not ready: startup synchronization still in progress";
        goal_handle->succeed(result);
        return;
    }

    {
        std::unique_lock<std::mutex> lock(execution_state_mutex_);
        if (command_in_progress_) {
            result->status = "not_able_to_execute";
            result->error_description = "Another high-level command is already in execution. Send Cancel first.";
            goal_handle->succeed(result);
            return;
        }

        command_in_progress_ = true;
        execution_shared_state_->cancel_requested.store(false);
    }

    // Step 2: Find command by name
    auto* command = command_factory_->find(command_name);
    if (!command) {
        result->status = "not_able_to_execute";
        result->error_description = "Unknown command '" + command_name +
            "'. Available: [" + command_factory_->available_commands() + ", cancel]";
        RCLCPP_ERROR(get_logger(), "%s", result->error_description.c_str());
        {
            std::lock_guard<std::mutex> lock(execution_state_mutex_);
            command_in_progress_ = false;
        }
        execution_state_cv_.notify_all();
        goal_handle->succeed(result);
        return;
    }

    // Step 3: Check system operative state
    feedback->current_status = "checking_system_state";
    goal_handle->publish_feedback(feedback);

    std::string error;
    if (!check_operative(error)) {
        RCLCPP_WARN(get_logger(), "System not operative: %s", error.c_str());
        result->status = "not_able_to_execute";
        result->error_description = error;
        {
            std::lock_guard<std::mutex> lock(execution_state_mutex_);
            command_in_progress_ = false;
        }
        execution_state_cv_.notify_all();
        goal_handle->succeed(result);
        return;
    }

    // Step 4: Resolve landmarks
    std::vector<executive::Landmark> landmarks;

    if (goal->landmarks_to_visit.empty()) {
        // No landmarks specified: use ALL available (for show_me_around)
        landmarks = landmark_registry_->get_all();
        if (landmarks.empty()) {
            result->status = "not_able_to_execute";
            result->error_description = "No landmarks available in the system";
            {
                std::lock_guard<std::mutex> lock(execution_state_mutex_);
                command_in_progress_ = false;
            }
            execution_state_cv_.notify_all();
            goal_handle->succeed(result);
            return;
        }
        RCLCPP_INFO(get_logger(), "No landmarks specified, using all %zu available.",
            landmarks.size());
    } else {
        // Validate requested landmarks
        auto invalid = landmark_registry_->find_invalid(goal->landmarks_to_visit);
        if (!invalid.empty()) {
            std::string invalid_str;
            for (size_t i = 0; i < invalid.size(); ++i) {
                if (i > 0) invalid_str += ", ";
                invalid_str += "'" + invalid[i] + "'";
            }

            auto available_names = landmark_registry_->get_names();
            std::string available_str;
            for (size_t i = 0; i < available_names.size(); ++i) {
                if (i > 0) available_str += ", ";
                available_str += available_names[i];
            }

            result->status = "not_able_to_execute";
            result->error_description = "Invalid landmarks: " + invalid_str +
                ". Available: [" + available_str + "]";
            RCLCPP_ERROR(get_logger(), "%s", result->error_description.c_str());
            {
                std::lock_guard<std::mutex> lock(execution_state_mutex_);
                command_in_progress_ = false;
            }
            execution_state_cv_.notify_all();
            goal_handle->succeed(result);
            return;
        }

        landmarks = landmark_registry_->resolve(goal->landmarks_to_visit);
    }

    // Step 5: Configure command with landmarks and execute
    bool success = false;
    try {
        RCLCPP_INFO(
            get_logger(),
            "Preparing command '%s' with %zu resolved landmarks",
            command->get_name().c_str(),
            landmarks.size());
        command->configure(landmarks);

        RCLCPP_INFO(get_logger(), "Executing command: %s", command->get_name().c_str());
        result->status = "in_execution";

        feedback->current_status = "in_execution";
        goal_handle->publish_feedback(feedback);

        success = command->execute(
            [this, &goal_handle, &feedback](const std::string& status_msg) {
                RCLCPP_INFO(get_logger(), "Command feedback: %s", status_msg.c_str());
                feedback->current_status = status_msg;
                goal_handle->publish_feedback(feedback);
            });
    } catch (const std::exception& ex) {
        RCLCPP_ERROR(
            get_logger(),
            "Command '%s' threw std::exception: %s",
            command->get_name().c_str(),
            ex.what());
        result->status = "failed";
        result->error_description = std::string("Unhandled exception while executing command: ") + ex.what();
    } catch (...) {
        RCLCPP_ERROR(
            get_logger(),
            "Command '%s' threw an unknown exception",
            command->get_name().c_str());
        result->status = "failed";
        result->error_description = "Unhandled unknown exception while executing command";
    }

    if (success) {
        result->status = "completed";
        result->error_description = "";
    } else if (execution_shared_state_->cancel_requested.load()) {
        result->status = "cancelled";
        result->error_description = "Command cancelled by Cancel request";
    } else if (result->status != "failed") {
        result->status = "failed";
        result->error_description = "Command execution failed";
    }

    // Always reset command to initial state, ready for next execution
    command->reset();

    {
        std::lock_guard<std::mutex> lock(execution_state_mutex_);
        command_in_progress_ = false;
    }
    execution_state_cv_.notify_all();

    if (result->status == "cancelled") {
        goal_handle->abort(result);
    } else {
        goal_handle->succeed(result);
    }
}

void ExecutiveNode::execute_cancel_command(const std::shared_ptr<ExecuteGoalHandle> goal_handle)
{
    auto result = std::make_shared<ExecuteCommand::Result>();
    auto feedback = std::make_shared<ExecuteCommand::Feedback>();
    result->command_echo = "cancel";

    if (!home_saved_) {
        result->status = "not_able_to_execute";
        result->error_description = "Home position not available yet";
        goal_handle->succeed(result);
        return;
    }

    feedback->current_status = "cancel_requested";
    goal_handle->publish_feedback(feedback);

    execution_shared_state_->cancel_requested.store(true);

    std::string cancel_error;
    if (!cancel_active_navigation(cancel_error) && !cancel_error.empty()) {
        feedback->current_status = cancel_error;
        goal_handle->publish_feedback(feedback);
    }

    {
        std::unique_lock<std::mutex> lock(execution_state_mutex_);
        execution_state_cv_.wait_for(lock, 15s, [this]() {
            return !command_in_progress_;
        });
    }

    execution_shared_state_->cancel_requested.store(false);

    feedback->current_status = "returning_home";
    goal_handle->publish_feedback(feedback);

    const bool home_ok = navigate_to_position(
        home_position_,
        [goal_handle, feedback](const std::string& status_msg) {
            feedback->current_status = status_msg;
            goal_handle->publish_feedback(feedback);
        },
        "home",
        false);

    if (home_ok) {
        result->status = "completed";
        result->error_description = "";
        goal_handle->succeed(result);
        return;
    }

    result->status = "failed";
    result->error_description = "Cancel request processed, but failed to return home";
    goal_handle->abort(result);
}

bool ExecutiveNode::cancel_active_navigation(std::string& error_out)
{
    executive::ExecutionContext::Nav2GoalHandle::SharedPtr active_goal;
    {
        std::lock_guard<std::mutex> lock(execution_shared_state_->nav_goal_mutex);
        active_goal = execution_shared_state_->active_nav_goal;
    }

    if (!active_goal) {
        error_out.clear();
        return true;
    }

    auto cancel_future = nav2_client_->async_cancel_goal(active_goal);
    if (cancel_future.wait_for(5s) != std::future_status::ready) {
        error_out = "Failed to cancel current navigation goal";
        return false;
    }

    error_out.clear();
    return true;
}

bool ExecutiveNode::navigate_to_position(
    const executive::Position& target,
    const std::function<void(const std::string&)>& on_progress,
    const std::string& label,
    bool track_cancellation)
{
    auto goal = NavigateToPose::Goal();
    executive::ExecutionContext ctx;
    ctx.node = shared_from_this();
    ctx.nav2_client = nav2_client_;
    ctx.shared_state = execution_shared_state_;
    ctx.home = home_position_;
    goal.pose = ctx.to_pose_stamped(target);

    on_progress("Navigating to " + label +
                " (x=" + std::to_string(target.x) +
                ", y=" + std::to_string(target.y) + ")");

    auto send_future = nav2_client_->async_send_goal(goal);
    if (send_future.wait_for(10s) != std::future_status::ready) {
        on_progress("Failed to send navigation goal to " + label);
        return false;
    }

    auto goal_handle = send_future.get();
    if (!goal_handle) {
        on_progress("Navigation goal rejected for " + label);
        return false;
    }

    if (track_cancellation) {
        std::lock_guard<std::mutex> lock(execution_shared_state_->nav_goal_mutex);
        execution_shared_state_->active_nav_goal = goal_handle;
    }

    auto result_future = nav2_client_->async_get_result(goal_handle);
    if (result_future.wait_for(5min) != std::future_status::ready) {
        on_progress("Navigation timeout for " + label);
        return false;
    }

    if (track_cancellation) {
        std::lock_guard<std::mutex> lock(execution_shared_state_->nav_goal_mutex);
        execution_shared_state_->active_nav_goal.reset();
    }

    const auto result = result_future.get();
    if (result.code != rclcpp_action::ResultCode::SUCCEEDED) {
        on_progress("Navigation failed for " + label);
        return false;
    }

    on_progress("Arrived at " + label);
    return true;
}

int main(int argc, char** argv)
{
    rclcpp::init(argc, argv);
    auto node = std::make_shared<ExecutiveNode>();
    rclcpp::executors::MultiThreadedExecutor executor;
    executor.add_node(node);
    executor.spin();
    rclcpp::shutdown();
    return 0;
}

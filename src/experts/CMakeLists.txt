cmake_minimum_required(VERSION 3.8)
project(experts)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(high_level_reasoning_interface REQUIRED)
find_package(nav_msgs REQUIRED)
find_package(sensor_msgs REQUIRED)
find_package(tf2_ros REQUIRED)
find_package(tf2 REQUIRED)
find_package(visualization_msgs REQUIRED)
find_package(rclcpp_action REQUIRED)
find_package(nav2_msgs REQUIRED)
find_package(lifecycle_msgs REQUIRED)

# Map Expert
add_executable(map_expert_node src/map_expert_node.cpp)
target_include_directories(map_expert_node PRIVATE include)
ament_target_dependencies(map_expert_node
  rclcpp high_level_reasoning_interface nav_msgs
)

# Localization Expert
add_executable(localization_expert_node src/localization_expert_node.cpp)
target_include_directories(localization_expert_node PRIVATE include)
ament_target_dependencies(localization_expert_node
  rclcpp high_level_reasoning_interface tf2_ros tf2
)

# Sensor Expert
add_executable(sensor_expert_node src/sensor_expert_node.cpp)
target_include_directories(sensor_expert_node PRIVATE include)
ament_target_dependencies(sensor_expert_node
  rclcpp high_level_reasoning_interface sensor_msgs nav_msgs
)

# Landmarks Expert
add_executable(landmarks_expert_node src/landmarks_expert_node.cpp)
target_include_directories(landmarks_expert_node PRIVATE include)
ament_target_dependencies(landmarks_expert_node
  rclcpp high_level_reasoning_interface visualization_msgs
)

# Nav2 Expert
add_executable(nav2_expert_node src/nav2_expert_node.cpp)
target_include_directories(nav2_expert_node PRIVATE include)
ament_target_dependencies(nav2_expert_node
  rclcpp rclcpp_action high_level_reasoning_interface nav2_msgs
)

# AMCL Expert
add_executable(amcl_expert_node src/amcl_expert_node.cpp)
target_include_directories(amcl_expert_node PRIVATE include)
ament_target_dependencies(amcl_expert_node
  rclcpp high_level_reasoning_interface lifecycle_msgs
)

install(TARGETS
  map_expert_node
  localization_expert_node
  sensor_expert_node
  landmarks_expert_node
  nav2_expert_node
  amcl_expert_node
  DESTINATION lib/${PROJECT_NAME}
)

if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  set(ament_cmake_copyright_FOUND TRUE)
  set(ament_cmake_cpplint_FOUND TRUE)
  ament_lint_auto_find_test_dependencies()
endif()

ament_package()

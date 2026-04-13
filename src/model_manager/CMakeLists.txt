cmake_minimum_required(VERSION 3.8)
project(model_manager)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(rclcpp_action REQUIRED)
find_package(high_level_reasoning_interface REQUIRED)

add_executable(model_manager_node src/model_manager_node.cpp)
target_include_directories(model_manager_node PRIVATE include)
ament_target_dependencies(model_manager_node
  rclcpp rclcpp_action high_level_reasoning_interface
)

install(TARGETS model_manager_node DESTINATION lib/${PROJECT_NAME})

if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  set(ament_cmake_copyright_FOUND TRUE)
  set(ament_cmake_cpplint_FOUND TRUE)
  ament_lint_auto_find_test_dependencies()
endif()

ament_package()

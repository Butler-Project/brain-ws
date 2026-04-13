#!/usr/bin/env python3
import yaml
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, DurabilityPolicy
from visualization_msgs.msg import Marker, MarkerArray


class LandmarksPublisher(Node):
    def __init__(self):
        super().__init__('landmarks_publisher')

        self.declare_parameter('landmarks_file', '')
        self.declare_parameter('marker_scale', 0.3)
        self.declare_parameter('marker_color.r', 0.0)
        self.declare_parameter('marker_color.g', 1.0)
        self.declare_parameter('marker_color.b', 0.0)
        self.declare_parameter('marker_color.a', 1.0)

        landmarks_file = self.get_parameter('landmarks_file').get_parameter_value().string_value
        if not landmarks_file:
            self.get_logger().error("Parameter 'landmarks_file' not set")
            return

        landmarks = self._load_landmarks(landmarks_file)
        if landmarks is None:
            return

        qos = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)
        self.publisher_ = self.create_publisher(MarkerArray, '/landmarks', qos)

        self._publish_markers(landmarks)
        self.get_logger().info(f'Published {len(landmarks)} landmarks from {landmarks_file}')

    def _load_landmarks(self, file_path):
        try:
            with open(file_path, 'r') as f:
                data = yaml.safe_load(f)
            if 'landmarks' not in data:
                self.get_logger().error(f"No 'landmarks' key in {file_path}")
                return None
            return data['landmarks']
        except Exception as e:
            self.get_logger().error(f'Failed to load landmarks: {e}')
            return None

    def _publish_markers(self, landmarks):
        scale = self.get_parameter('marker_scale').get_parameter_value().double_value
        r = self.get_parameter('marker_color.r').get_parameter_value().double_value
        g = self.get_parameter('marker_color.g').get_parameter_value().double_value
        b = self.get_parameter('marker_color.b').get_parameter_value().double_value
        a = self.get_parameter('marker_color.a').get_parameter_value().double_value

        marker_array = MarkerArray()
        marker_id = 0

        for name, coords in landmarks.items():
            # Sphere
            sphere = Marker()
            sphere.header.frame_id = 'map'
            sphere.header.stamp = self.get_clock().now().to_msg()
            sphere.ns = 'landmarks'
            sphere.id = marker_id
            marker_id += 1
            sphere.type = Marker.SPHERE
            sphere.action = Marker.ADD
            sphere.pose.position.x = float(coords['x'])
            sphere.pose.position.y = float(coords['y'])
            sphere.pose.position.z = 0.1
            sphere.pose.orientation.w = 1.0
            sphere.scale.x = scale
            sphere.scale.y = scale
            sphere.scale.z = scale
            sphere.color.r = r
            sphere.color.g = g
            sphere.color.b = b
            sphere.color.a = a
            marker_array.markers.append(sphere)

            # Text label
            text = Marker()
            text.header.frame_id = 'map'
            text.header.stamp = self.get_clock().now().to_msg()
            text.ns = 'landmarks_text'
            text.id = marker_id
            marker_id += 1
            text.type = Marker.TEXT_VIEW_FACING
            text.action = Marker.ADD
            text.pose.position.x = float(coords['x'])
            text.pose.position.y = float(coords['y'])
            text.pose.position.z = 0.5
            text.pose.orientation.w = 1.0
            text.scale.z = 0.3
            text.color.r = 1.0
            text.color.g = 1.0
            text.color.b = 1.0
            text.color.a = 1.0
            text.text = name
            marker_array.markers.append(text)

        self.publisher_.publish(marker_array)


def main():
    rclpy.init()
    node = LandmarksPublisher()
    rclpy.spin(node)
    rclpy.shutdown()


if __name__ == '__main__':
    main()

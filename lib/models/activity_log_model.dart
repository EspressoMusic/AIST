class ActivityLogModel {
  const ActivityLogModel({
    required this.event,
    required this.message,
    required this.timestamp,
  });

  final String event;
  final String message;
  final DateTime timestamp;
}

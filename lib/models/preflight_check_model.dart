class PreflightCheckModel {
  const PreflightCheckModel({
    required this.title,
    required this.passed,
    required this.message,
  });

  final String title;
  final bool passed;
  final String message;
}

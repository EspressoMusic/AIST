// Short UI dates for API ISO strings and DateTime.

String formatShortDateTime(dynamic value) {
  if (value == null) return '';
  final DateTime? dt = value is DateTime
      ? value.toLocal()
      : DateTime.tryParse(value.toString())?.toLocal();
  if (dt == null) return '';
  final d = dt.day.toString().padLeft(2, '0');
  final mo = dt.month.toString().padLeft(2, '0');
  final h = dt.hour.toString().padLeft(2, '0');
  final mi = dt.minute.toString().padLeft(2, '0');
  return '$d/$mo $h:$mi';
}

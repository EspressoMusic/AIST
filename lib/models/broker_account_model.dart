class BrokerAccountModel {
  const BrokerAccountModel({
    required this.id,
    required this.brokerName,
    required this.apiKeyMasked,
    required this.isPaper,
    required this.isConnected,
    this.connectedAt,
  });

  final String id;
  final String brokerName;
  final String apiKeyMasked;
  final bool isPaper;
  final bool isConnected;
  final DateTime? connectedAt;

  BrokerAccountModel copyWith({
    String? id,
    String? brokerName,
    String? apiKeyMasked,
    bool? isPaper,
    bool? isConnected,
    DateTime? connectedAt,
  }) {
    return BrokerAccountModel(
      id: id ?? this.id,
      brokerName: brokerName ?? this.brokerName,
      apiKeyMasked: apiKeyMasked ?? this.apiKeyMasked,
      isPaper: isPaper ?? this.isPaper,
      isConnected: isConnected ?? this.isConnected,
      connectedAt: connectedAt ?? this.connectedAt,
    );
  }

  Map<String, dynamic> toMap() {
    return {
      'id': id,
      'brokerName': brokerName,
      'apiKeyMasked': apiKeyMasked,
      'isPaper': isPaper,
      'isConnected': isConnected,
      'connectedAt': connectedAt?.millisecondsSinceEpoch,
    };
  }

  factory BrokerAccountModel.fromMap(Map<String, dynamic> map) {
    return BrokerAccountModel(
      id: map['id'] as String? ?? '',
      brokerName: map['brokerName'] as String? ?? '',
      apiKeyMasked: map['apiKeyMasked'] as String? ?? '',
      isPaper: map['isPaper'] as bool? ?? true,
      isConnected: map['isConnected'] as bool? ?? false,
      connectedAt: map['connectedAt'] == null
          ? null
          : DateTime.fromMillisecondsSinceEpoch(map['connectedAt'] as int),
    );
  }
}

import 'dart:convert';

import 'package:shared_preferences/shared_preferences.dart';

import '../models/broker_account_model.dart';

class BrokerStorageService {
  static const _brokerConnectionKey = 'broker.connection';

  Future<BrokerAccountModel?> loadBrokerConnection() async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString(_brokerConnectionKey);
    if (raw == null || raw.isEmpty) return null;
    return BrokerAccountModel.fromMap(jsonDecode(raw) as Map<String, dynamic>);
  }

  Future<void> saveBrokerConnection(BrokerAccountModel account) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_brokerConnectionKey, jsonEncode(account.toMap()));
  }

  Future<void> clearBrokerConnection() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_brokerConnectionKey);
  }
}

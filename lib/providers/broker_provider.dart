import 'package:flutter/foundation.dart';

import '../models/broker_account_model.dart';
import '../services/broker_storage_service.dart';

class BrokerProvider extends ChangeNotifier {
  BrokerProvider({BrokerStorageService? storageService})
    : _storageService = storageService ?? BrokerStorageService();

  final BrokerStorageService _storageService;

  BrokerAccountModel? _connectedAccount;
  bool _isInitialized = false;
  bool _isBusy = false;

  BrokerAccountModel? get connectedAccount => _connectedAccount;
  bool get isInitialized => _isInitialized;
  bool get isBusy => _isBusy;
  bool get isConnected => _connectedAccount?.isConnected ?? false;
  bool get isPaperOrDemo => _connectedAccount?.isPaper ?? false;

  Future<void> init() async {
    if (_isInitialized) return;
    _connectedAccount = await _storageService.loadBrokerConnection();
    final connected = _connectedAccount?.isConnected ?? false;
    final paper = _connectedAccount?.isPaper ?? false;
    if (_connectedAccount == null || !connected || !paper) {
      final account = BrokerAccountModel(
        id: 'local-demo',
        brokerName: 'Demo Broker',
        apiKeyMasked: 'DEMO_****',
        isPaper: true,
        isConnected: true,
        connectedAt: DateTime.now(),
      );
      _connectedAccount = account;
      await _storageService.saveBrokerConnection(account);
    }
    _isInitialized = true;
    notifyListeners();
  }

  Future<void> connectBroker({
    required String brokerName,
    required bool isPaper,
  }) async {
    _isBusy = true;
    notifyListeners();
    final account = BrokerAccountModel(
      id: DateTime.now().millisecondsSinceEpoch.toString(),
      brokerName: brokerName,
      apiKeyMasked: _dummyMaskedKey(brokerName),
      isPaper: isPaper,
      isConnected: true,
      connectedAt: DateTime.now(),
    );
    _connectedAccount = account;
    await _storageService.saveBrokerConnection(account);
    _isBusy = false;
    notifyListeners();
  }

  Future<void> disconnectBroker() async {
    _isBusy = true;
    notifyListeners();
    _connectedAccount = null;
    await _storageService.clearBrokerConnection();
    _isBusy = false;
    notifyListeners();
  }

  String _dummyMaskedKey(String brokerName) {
    final prefix = brokerName.replaceAll(' ', '').toUpperCase();
    final end = prefix.length < 4 ? prefix.length : 4;
    return '${prefix.substring(0, end)}_****_DEMO';
  }
}

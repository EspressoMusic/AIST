import 'package:flutter/foundation.dart';

import '../models/user_model.dart';
import '../services/auth_storage_service.dart';

class AuthProvider extends ChangeNotifier {
  AuthProvider({AuthStorageService? storageService})
    : _storageService = storageService ?? AuthStorageService();

  final AuthStorageService _storageService;

  bool _isInitialized = false;
  bool _isAuthenticated = false;
  bool _isBusy = false;
  String? _errorMessage;
  UserModel? _currentUser;

  bool get isInitialized => _isInitialized;
  bool get isAuthenticated => _isAuthenticated;
  bool get isBusy => _isBusy;
  String? get errorMessage => _errorMessage;
  UserModel? get currentUser => _currentUser;

  Future<void> init() async {
    if (_isInitialized) return;
    final user = await _storageService.getSessionUser();
    _currentUser = user;
    _isAuthenticated = user != null;
    _isInitialized = true;
    notifyListeners();
  }

  Future<bool> login({required String email, required String password}) async {
    _setBusy(true);
    _errorMessage = null;
    notifyListeners();

    final credentials = await _storageService.getRegisteredCredentials();
    if (credentials == null) {
      _errorMessage = 'No registered user found. Please register first.';
      _setBusy(false);
      notifyListeners();
      return false;
    }

    final (registeredUser, registeredPassword) = credentials;
    if (registeredUser.email.toLowerCase() != email.toLowerCase() ||
        registeredPassword != password) {
      _errorMessage = 'Invalid email or password.';
      _setBusy(false);
      notifyListeners();
      return false;
    }

    _currentUser = registeredUser;
    _isAuthenticated = true;
    await _storageService.saveSessionUser(registeredUser);
    _setBusy(false);
    notifyListeners();
    return true;
  }

  Future<bool> register({
    required String name,
    required String email,
    required String password,
  }) async {
    _setBusy(true);
    _errorMessage = null;
    notifyListeners();

    final user = UserModel(name: name, email: email);
    await _storageService.saveRegisteredUser(user: user, password: password);
    await _storageService.saveSessionUser(user);
    _currentUser = user;
    _isAuthenticated = true;

    _setBusy(false);
    notifyListeners();
    return true;
  }

  Future<void> logout() async {
    _setBusy(true);
    notifyListeners();
    await _storageService.clearSession();
    _currentUser = null;
    _isAuthenticated = false;
    _errorMessage = null;
    _setBusy(false);
    notifyListeners();
  }

  void clearError() {
    _errorMessage = null;
    notifyListeners();
  }

  void _setBusy(bool value) {
    _isBusy = value;
  }
}

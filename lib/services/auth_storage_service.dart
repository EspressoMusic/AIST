import 'dart:convert';

import 'package:shared_preferences/shared_preferences.dart';

import '../models/user_model.dart';

class AuthStorageService {
  static const _sessionUserKey = 'auth.sessionUser';
  static const _registeredUserKey = 'auth.registeredUser';
  static const _registeredPasswordKey = 'auth.registeredPassword';

  Future<UserModel?> getSessionUser() async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString(_sessionUserKey);
    if (raw == null || raw.isEmpty) return null;
    return UserModel.fromMap(jsonDecode(raw) as Map<String, dynamic>);
  }

  Future<void> saveSessionUser(UserModel user) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_sessionUserKey, jsonEncode(user.toMap()));
  }

  Future<void> clearSession() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_sessionUserKey);
  }

  Future<void> saveRegisteredUser({
    required UserModel user,
    required String password,
  }) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_registeredUserKey, jsonEncode(user.toMap()));
    await prefs.setString(_registeredPasswordKey, password);
  }

  Future<(UserModel, String)?> getRegisteredCredentials() async {
    final prefs = await SharedPreferences.getInstance();
    final rawUser = prefs.getString(_registeredUserKey);
    final password = prefs.getString(_registeredPasswordKey);
    if (rawUser == null || password == null) return null;
    final user = UserModel.fromMap(jsonDecode(rawUser) as Map<String, dynamic>);
    return (user, password);
  }
}

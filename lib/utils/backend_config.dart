import 'dart:io';

/// Base URL for the local FastAPI backend (demo only — no API keys in the app).
///
/// **Port 8001** — enforced explicitly below for desktop / USB / LAN.
///
/// | Scenario | URL |
/// |----------|-----|
/// | Desktop (Windows / Linux / macOS) | `http://127.0.0.1:8001` |
/// | Android `USE_USB_REVERSE=true` | `http://127.0.0.1:8001` |
/// | Physical Android (LAN) | `http://192.168.1.173:8001` |
/// | Android emulator (`ANDROID_EMULATOR=true`) | `http://10.0.2.2:8001` |
///
/// USB reverse:
/// ```bash
/// adb reverse tcp:8001 tcp:8001
/// flutter run --dart-define=USE_USB_REVERSE=true
/// ```
///
/// Emulator:
/// ```bash
/// flutter run --dart-define=ANDROID_EMULATOR=true
/// ```
class BackendConfig {
  BackendConfig._();

  /// Matches backend listen port on the dev PC.
  static const int backendPort = 8001;

  /// Desktop & USB reverse — loopback on device tunnels to host :8001.
  static const String desktopAndUsbReverseUrl = 'http://127.0.0.1:8001';

  /// Physical phone on same LAN as PC (update host if DHCP changes).
  static const String physicalLanUrl = 'http://192.168.1.173:8001';

  static const bool _useUsbReverse = bool.fromEnvironment(
    'USE_USB_REVERSE',
    defaultValue: false,
  );

  static const bool _androidEmulator = bool.fromEnvironment(
    'ANDROID_EMULATOR',
    defaultValue: false,
  );

  static String get defaultBaseUrl {
    if (Platform.isWindows ||
        Platform.isLinux ||
        Platform.isMacOS) {
      return desktopAndUsbReverseUrl;
    }

    if (Platform.isAndroid) {
      if (_useUsbReverse) {
        return desktopAndUsbReverseUrl;
      }
      if (_androidEmulator) {
        return 'http://10.0.2.2:$backendPort';
      }
      return physicalLanUrl;
    }

    return desktopAndUsbReverseUrl;
  }
}

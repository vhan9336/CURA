import "package:flet/flet.dart";
import "package:flutter/services.dart";

class CuraAndroidService extends FletService {
  CuraAndroidService({required super.control});

  static const MethodChannel _channel =
      MethodChannel("com.cura.android/native");

  @override
  void init() {
    super.init();
    control.addInvokeMethodListener(_invokeMethod);
  }

  Future<dynamic> _invokeMethod(String method, dynamic args) {
    return _channel.invokeMethod<dynamic>(method, args);
  }

  @override
  void dispose() {
    control.removeInvokeMethodListener(_invokeMethod);
    super.dispose();
  }
}

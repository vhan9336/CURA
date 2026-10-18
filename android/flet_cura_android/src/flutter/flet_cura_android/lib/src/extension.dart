import "package:flet/flet.dart";

import "cura_android_service.dart";

class Extension extends FletExtension {
  @override
  FletService? createService(Control control) {
    if (control.type == "CuraAndroid") {
      return CuraAndroidService(control: control);
    }
    return null;
  }
}

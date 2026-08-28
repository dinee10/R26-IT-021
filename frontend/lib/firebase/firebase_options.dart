import 'package:firebase_core/firebase_core.dart';
import 'package:flutter/foundation.dart';

class DefaultFirebaseOptions {
  static FirebaseOptions get currentPlatform {
    if (kIsWeb) {
      return web;
    }

    switch (defaultTargetPlatform) {
      case TargetPlatform.android:
        return android;
      case TargetPlatform.iOS:
      case TargetPlatform.macOS:
      case TargetPlatform.windows:
      case TargetPlatform.linux:
      case TargetPlatform.fuchsia:
        return web;
    }
  }

  static const FirebaseOptions web = FirebaseOptions(
    apiKey: 'AIzaSyBwehMo_fDE2_Nv1PX5LAz5BpPmjo6j8ws',
    appId: '1:1077216604890:web:126ecea2c0a107d9752be3',
    messagingSenderId: '1077216604890',
    projectId: 'ayurplant-ad761',
    authDomain: 'ayurplant-ad761.firebaseapp.com',
    storageBucket: 'ayurplant-ad761.firebasestorage.app',
  );

  static const FirebaseOptions android = FirebaseOptions(
    apiKey: 'AIzaSyBwehMo_fDE2_Nv1PX5LAz5BpPmjo6j8ws',
    appId: '1:1077216604890:android:126ecea2c0a107d9752be3',
    messagingSenderId: '1077216604890',
    projectId: 'ayurplant-ad761',
    storageBucket: 'ayurplant-ad761.firebasestorage.app',
  );
}

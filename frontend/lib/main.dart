import 'package:firebase_core/firebase_core.dart';
import 'package:flutter/material.dart';

import 'firebase/firebase_options.dart';
import 'screens/auth_gate.dart';
import 'screens/startup_error_page.dart';
import 'theme/app_colors.dart';


void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  Object? startupError;

  try {
    await Firebase.initializeApp(
      options: DefaultFirebaseOptions.currentPlatform,
    );
  } catch (error) {
    startupError = error;
  }

  runApp(AyurPlantApp(startupError: startupError));
}

class AyurPlantApp extends StatelessWidget {
  const AyurPlantApp({super.key, this.startupError});

  final Object? startupError;

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'AyurPlant',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: AppColors.primary,
          brightness: Brightness.light,
        ),
        scaffoldBackgroundColor: AppColors.surface,
        useMaterial3: true,
      ),
      home: startupError == null
          ? const AuthGate()
          : StartupErrorPage(error: startupError!),

    );
  }
}
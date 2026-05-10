import 'package:flutter/material.dart';

import 'screens/detector_screen.dart';

void main() {
  runApp(const HerbalDetectorApp());
}

class HerbalDetectorApp extends StatelessWidget {
  const HerbalDetectorApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      title: 'Herbal Plant Detector',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFF2F7D46),
          brightness: Brightness.light,
        ),
        useMaterial3: true,
      ),
      home: const DetectorScreen(),
    );
  }
}

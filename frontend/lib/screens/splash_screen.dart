import 'package:flutter/material.dart';

import '../theme/app_colors.dart';

/// Visible while Firebase Authentication and the onboarding preference load.
/// No artificial delay: returning users are not made to wait unnecessarily.
class SplashScreen extends StatelessWidget {
  const SplashScreen({super.key});

  @override
  Widget build(BuildContext context) {

    return Scaffold(
      backgroundColor: AppColors.surface,
      body: Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Image.asset(
              'assets/images/logo_transparent.png',
              height: 92,
              width: 92,
              errorBuilder: (_, __, ___) => Icon(
                Icons.eco_rounded,
                color: AppColors.primary,
                size: 72,
              ),
            ),
            const SizedBox(height: 16),
            Text(
              'AyurPlant',
              style: TextStyle(
                color: AppColors.text,
                fontSize: 28,
                fontWeight: FontWeight.w800,
              ),
            ),
            const SizedBox(height: 6),
            Text(
              'Sri Lankan medicinal plants',
              style: TextStyle(color: AppColors.muted),
            ),
            const SizedBox(height: 30),
            SizedBox(
              width: 26,
              height: 26,
              child: CircularProgressIndicator(
                strokeWidth: 2.6,
                color: AppColors.primary,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

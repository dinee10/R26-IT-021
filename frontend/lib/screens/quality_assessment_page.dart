import 'package:flutter/material.dart';
import '../theme/app_colors.dart';

class QualityAssessmentPage extends StatelessWidget {
  const QualityAssessmentPage({super.key});

  @override
  Widget build(BuildContext context) {
    return const _FeaturePageShell(
      title: 'Assess Quality',
      icon: Icons.camera_enhance_rounded,
      subtitle: 'Quality assessment feature workspace',
    );
  }
}

class _FeaturePageShell extends StatelessWidget {
  const _FeaturePageShell({
    required this.title,
    required this.icon,
    required this.subtitle,
  });

  final String title;
  final IconData icon;
  final String subtitle;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(title), centerTitle: false),
      body: SafeArea(
        child: Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(icon, color: AppColors.primary, size: 58),
              const SizedBox(height: 16),
              Text(
                title,
                style: const TextStyle(
                  color: AppColors.text,
                  fontSize: 24,
                  fontWeight: FontWeight.w900,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                subtitle,
                style: const TextStyle(
                  color: AppColors.muted,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

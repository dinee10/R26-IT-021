import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';
import 'ai_assistant_page.dart';
import 'cultivation_page.dart';
import 'identify_plant_page.dart';
import 'quality_assessment_page.dart';
import '../theme/app_colors.dart';
import '../widgets/feature_tile.dart';
import '../widgets/user_avatar.dart';

class HomePage extends StatelessWidget {
  const HomePage({super.key});

  @override
  Widget build(BuildContext context) {
    final user = FirebaseAuth.instance.currentUser;
    final name = _firstName(user?.displayName) ?? 'AyurPlant';

    return Scaffold(
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.fromLTRB(24, 22, 24, 24),
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Container(
                  width: 36,
                  height: 36,
                  decoration: BoxDecoration(
                    color: AppColors.text,
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Padding(
                    padding: const EdgeInsets.all(5),
                    child: Image.asset(
                      'assets/images/logo_transparent.png',
                      fit: BoxFit.contain,
                    ),
                  ),
                ),
                IconButton(
                  onPressed: () {},
                  icon: const Icon(Icons.tune_rounded),
                ),
              ],
            ),
            const SizedBox(height: 28),
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'Good morning,',
                        style: TextStyle(
                          color: AppColors.muted,
                          fontSize: 14,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        name,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(
                          color: AppColors.text,
                          fontSize: 24,
                          fontWeight: FontWeight.w900,
                        ),
                      ),
                    ],
                  ),
                ),
                UserAvatar(user: user, radius: 27),
              ],
            ),
            const SizedBox(height: 20),
            const AssistantShortcut(),
            const SizedBox(height: 28),
            GridView.count(
              crossAxisCount: 2,
              crossAxisSpacing: 14,
              mainAxisSpacing: 14,
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              childAspectRatio: 0.95,
              children: [
                FeatureTile(
                  title: 'Identify Plant',
                  subtitle: 'Detect plant species',
                  icon: Icons.camera_alt_rounded,
                  color: const Color(0xFFD0F8DD),
                  iconColor: AppColors.primary,
                  onTap: () => _openFeature(context, const IdentifyPlantPage()),
                ),
                FeatureTile(
                  title: 'Assess Quality',
                  subtitle: 'Check medicinal suitability',
                  icon: Icons.camera_enhance_rounded,
                  color: const Color(0xFFF7DDB1),
                  iconColor: const Color(0xFFE99A1E),
                  onTap: () =>
                      _openFeature(context, const QualityAssessmentPage()),
                ),
                FeatureTile(
                  title: 'AI Assistant',
                  subtitle: 'Ask plant questions',
                  icon: Icons.auto_awesome_rounded,
                  color: const Color(0xFFEEF9D9),
                  iconColor: const Color(0xFFA8E04E),
                  onTap: () => _openFeature(context, const AiAssistantPage()),
                ),
                FeatureTile(
                  title: 'Cultivation',
                  subtitle: 'Plan crops and income',
                  icon: Icons.eco_rounded,
                  color: const Color(0xFFF8DFD8),
                  iconColor: const Color(0xFFE36F4D),
                  onTap: () => _openFeature(context, const CultivationPage()),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  static String? _firstName(String? displayName) {
    if (displayName == null || displayName.trim().isEmpty) {
      return null;
    }
    return displayName.trim().split(RegExp(r'\s+')).first;
  }

  static void _openFeature(BuildContext context, Widget page) {
    Navigator.of(context).push(
      MaterialPageRoute<void>(builder: (_) => page),
    );
  }
}

class AssistantShortcut extends StatelessWidget {
  const AssistantShortcut({super.key});

  @override
  Widget build(BuildContext context) {
    return Container(
      height: 52,
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppColors.border),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.06),
            blurRadius: 16,
            offset: const Offset(0, 8),
          ),
        ],
      ),
      child: const Row(
        children: [
          SizedBox(width: 14),
          Icon(Icons.auto_awesome_rounded, color: AppColors.muted, size: 20),
          SizedBox(width: 10),
          Expanded(
            child: Text(
              'Ask about plants, symptoms, or cultivation...',
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(
                color: AppColors.muted,
                fontSize: 14,
                fontWeight: FontWeight.w700,
              ),
            ),
          ),
          SizedBox(width: 12),
        ],
      ),
    );
  }
}

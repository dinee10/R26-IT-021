import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';

import '../theme/app_colors.dart';
import '../widgets/user_avatar.dart';
import 'ai_assistant_page.dart';
import 'cultivation_page.dart';
import 'identify_plant_page.dart';
import 'quality_assessment_page.dart';

/// Updated AyurPlant home screen (light theme only).
/// Uses the existing four feature destinations and existing image assets.
/// No theme controller, dark mode switching, or additional dependencies.
class HomePage extends StatelessWidget {
  const HomePage({super.key});

  @override
  Widget build(BuildContext context) {
    final user = FirebaseAuth.instance.currentUser;
    final firstName = _firstName(user?.displayName) ?? 'there';

    return Scaffold(
      backgroundColor: AppColors.surface,
      body: SafeArea(
        child: LayoutBuilder(
          builder: (context, constraints) {
            final isMobile = constraints.maxWidth < 600;
            final columns = constraints.maxWidth >= 900
                ? 4
                : constraints.maxWidth < 360
                    ? 1
                    : 2;

            return ListView(
              padding: EdgeInsets.fromLTRB(
                isMobile ? 16 : 28,
                18,
                isMobile ? 16 : 28,
                30,
              ),
              children: [
                Center(
                  child: ConstrainedBox(
                    constraints: const BoxConstraints(maxWidth: 1040),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        const _HomeTopBar(),
                        const SizedBox(height: 22),
                        Row(
                          crossAxisAlignment: CrossAxisAlignment.center,
                          children: [
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    '${_greeting()},',
                                    style: const TextStyle(
                                      color: AppColors.muted,
                                      fontSize: 13,
                                      fontWeight: FontWeight.w600,
                                    ),
                                  ),
                                  const SizedBox(height: 4),
                                  Text(
                                    firstName,
                                    maxLines: 1,
                                    overflow: TextOverflow.ellipsis,
                                    style: TextStyle(
                                      color: AppColors.text,
                                      fontSize: isMobile ? 25 : 30,
                                      fontWeight: FontWeight.w800,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                            const SizedBox(width: 12),
                            UserAvatar(user: user, radius: 25),
                          ],
                        ),
                        const SizedBox(height: 20),
                        const _HerbalHero(),
                        const SizedBox(height: 16),
                        AssistantShortcut(
                          onTap: () => _openFeature(
                            context,
                            const AiAssistantPage(),
                          ),
                        ),
                        const SizedBox(height: 26),
                        Text(
                          'Explore AyurPlant',
                          style: TextStyle(
                            color: AppColors.text,
                            fontSize: isMobile ? 19 : 22,
                            fontWeight: FontWeight.w800,
                          ),
                        ),
                        const SizedBox(height: 4),
                        const Text(
                          'Choose what you would like to discover today.',
                          style: TextStyle(
                            color: AppColors.muted,
                            fontSize: 13,
                          ),
                        ),
                        const SizedBox(height: 14),
                        GridView.count(
                          crossAxisCount: columns,
                          mainAxisSpacing: 12,
                          crossAxisSpacing: 12,
                          mainAxisExtent: columns == 1
                              ? 244
                              : columns == 4
                                  ? 264
                                  : 254,
                          shrinkWrap: true,
                          physics: const NeverScrollableScrollPhysics(),
                          children: [
                            _FeatureCard(
                              title: 'Identify Plant',
                              description:
                                  'Recognize leaves, seeds and flowers from photos.',
                              imageAsset:
                                  'assets/images/home_identify_light.png',
                              fallbackIcon: Icons.camera_alt_rounded,
                              background: const Color(0xFFE1F6E5),
                              onTap: () => _openFeature(
                                context,
                                const IdentifyPlantPage(),
                              ),
                            ),
                            _FeatureCard(
                              title: 'Assess Quality',
                              description:
                                  'Examine supported plant health and quality indicators.',
                              imageAsset:
                                  'assets/images/home_quality_light.png',
                              fallbackIcon: Icons.fact_check_rounded,
                              background: const Color(0xFFF9ECCF),
                              onTap: () => _openFeature(
                                context,
                                const QualityAssessmentPage(),
                              ),
                            ),
                            _FeatureCard(
                              title: 'Herbal AI Assistant',
                              description:
                                  'Ask about traditional uses and plant care in Sinhala or English.',
                              imageAsset:
                                  'assets/images/home_assistant_light.png',
                              fallbackIcon: Icons.forum_rounded,
                              background: const Color(0xFFE5F3E2),
                              onTap: () => _openFeature(
                                context,
                                const AiAssistantPage(),
                              ),
                            ),
                            _FeatureCard(
                              title: 'Cultivation Guide',
                              description:
                                  'Find medicinal crops suited to your growing conditions.',
                              imageAsset:
                                  'assets/images/home_cultivation_light.png',
                              fallbackIcon: Icons.spa_rounded,
                              background: const Color(0xFFEDF3D9),
                              onTap: () => _openFeature(
                                context,
                                const CultivationPage(),
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 16),
                        const _PhotoTip(),
                      ],
                    ),
                  ),
                ),
              ],
            );
          },
        ),
      ),
    );
  }

  static String _greeting() {
    final hour = DateTime.now().hour;
    if (hour >= 5 && hour < 12) return 'Good morning';
    if (hour >= 12 && hour < 17) return 'Good afternoon';
    return 'Good evening';
  }

  static String? _firstName(String? displayName) {
    final trimmed = displayName?.trim();
    if (trimmed == null || trimmed.isEmpty) return null;
    return trimmed.split(RegExp(r'\s+')).first;
  }

  static void _openFeature(BuildContext context, Widget page) {
    Navigator.of(context).push(
      MaterialPageRoute<void>(builder: (_) => page),
    );
  }
}

class _HomeTopBar extends StatelessWidget {
  const _HomeTopBar();

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Container(
          width: 44,
          height: 44,
          padding: const EdgeInsets.all(5),
          decoration: BoxDecoration(
            color: const Color(0xFF202721),
            borderRadius: BorderRadius.circular(13),
          ),
          child: Image.asset(
            'assets/images/logo_transparent.png',
            fit: BoxFit.contain,
            errorBuilder: (_, __, ___) => const Icon(
              Icons.eco_rounded,
              color: Colors.white,
            ),
          ),
        ),
        const SizedBox(width: 10),
        const Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'AyurPlant',
                style: TextStyle(
                  color: AppColors.text,
                  fontSize: 19,
                  fontWeight: FontWeight.w800,
                ),
              ),
              Text(
                'SRI LANKAN MEDICINAL PLANTS',
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(
                  color: AppColors.muted,
                  fontSize: 9,
                  fontWeight: FontWeight.w700,
                  letterSpacing: 0.6,
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

/// Banner uses a compact version at narrow widths to avoid RenderFlex overflow.
class _HerbalHero extends StatelessWidget {
  const _HerbalHero();

  @override
  Widget build(BuildContext context) {
    const background = Color(0xFFE7F4E7);
    const headline = Color(0xFF20452B);
    const subtitle = Color(0xFF52765A);

    return LayoutBuilder(
      builder: (context, constraints) {
        final compact = constraints.maxWidth < 320;
        return ClipRRect(
          borderRadius: BorderRadius.circular(22),
          child: SizedBox(
            height: compact ? 144 : 158,
            child: Stack(
              children: [
                const Positioned.fill(child: ColoredBox(color: background)),
                Positioned(
                  right: -18,
                  top: -15,
                  bottom: -15,
                  width: constraints.maxWidth * 0.45,
                  child: Icon(
                    Icons.spa_rounded,
                    size: compact ? 78 : 120,
                    color: const Color(0xFFB7D8BB),
                  ),
                ),
                Positioned.fill(
                  child: DecoratedBox(
                    decoration: BoxDecoration(
                      gradient: LinearGradient(
                        colors: [
                          background,
                          background.withValues(alpha: 0.94),
                          background.withValues(alpha: 0.35),
                        ],
                        stops: const [0, 0.63, 1],
                      ),
                    ),
                  ),
                ),
                Positioned.fill(
                  child: Padding(
                    padding: const EdgeInsets.all(18),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        const Text(
                          'EXPLORE NATURE',
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: TextStyle(
                            color: subtitle,
                            fontSize: 10,
                            fontWeight: FontWeight.w800,
                            letterSpacing: 1.1,
                          ),
                        ),
                        const SizedBox(height: 7),
                        Text(
                          compact
                              ? 'Discover medicinal plants'
                              : 'Discover the wisdom\nof medicinal plants',
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                          style: TextStyle(
                            color: headline,
                            fontSize: compact ? 16 : 20,
                            fontWeight: FontWeight.w800,
                            height: 1.13,
                          ),
                        ),
                        const SizedBox(height: 7),
                        const Text(
                          'Identify • Learn • Grow',
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: TextStyle(
                            color: subtitle,
                            fontSize: 12,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ],
            ),
          ),
        );
      },
    );
  }
}

class _FeatureCard extends StatelessWidget {
  const _FeatureCard({
    required this.title,
    required this.description,
    required this.imageAsset,
    required this.fallbackIcon,
    required this.background,
    required this.onTap,
  });

  final String title;
  final String description;
  final String imageAsset;
  final IconData fallbackIcon;
  final Color background;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: background,
      borderRadius: BorderRadius.circular(18),
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(13),
                  child: SizedBox(
                    width: double.infinity,
                    child: Image.asset(
                      imageAsset,
                      fit: BoxFit.cover,
                      errorBuilder: (_, __, ___) => Center(
                        child: Icon(
                          fallbackIcon,
                          size: 55,
                          color: const Color(0xFF419657),
                        ),
                      ),
                    ),
                  ),
                ),
              ),
              const SizedBox(height: 10),
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Expanded(
                    child: Text(
                      title,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                        color: Color(0xFF243428),
                        fontSize: 14,
                        height: 1.15,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                  ),
                  const Icon(
                    Icons.arrow_forward_rounded,
                    color: Color(0xFF243428),
                    size: 17,
                  ),
                ],
              ),
              const SizedBox(height: 4),
              Text(
                description,
                maxLines: 3,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(
                  color: Color(0xFF526455),
                  fontSize: 11,
                  height: 1.25,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// Public widget retained for compatibility with other existing screens.
class AssistantShortcut extends StatelessWidget {
  const AssistantShortcut({super.key, this.onTap});

  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.white,
      borderRadius: BorderRadius.circular(15),
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: onTap,
        child: Container(
          height: 56,
          padding: const EdgeInsets.symmetric(horizontal: 15),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(15),
            border: Border.all(color: AppColors.border),
          ),
          child: const Row(
            children: [
              Icon(
                Icons.auto_awesome_rounded,
                color: AppColors.primary,
                size: 22,
              ),
              SizedBox(width: 12),
              Expanded(
                child: Text(
                  'Ask the Herbal AI Assistant',
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(
                    color: AppColors.text,
                    fontSize: 13,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
              Icon(
                Icons.arrow_forward_ios_rounded,
                color: AppColors.muted,
                size: 16,
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _PhotoTip extends StatelessWidget {
  const _PhotoTip();

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 15, vertical: 14),
      decoration: BoxDecoration(
        color: const Color(0xFFF1F7EF),
        borderRadius: BorderRadius.circular(15),
        border: Border.all(color: AppColors.border),
      ),
      child: const Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(
            Icons.info_outline_rounded,
            color: AppColors.primary,
            size: 20,
          ),
          SizedBox(width: 10),
          Expanded(
            child: Text(
              'Photo tip: Use clear, well-lit images of a single plant part for better identification.',
              style: TextStyle(
                color: AppColors.muted,
                fontSize: 12,
                height: 1.35,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

import 'package:flutter/material.dart';

import '../theme/app_colors.dart';

/// Three first-time screens; the third ends in Get Started.
/// Authentication and account creation remain in the existing LoginPage.
class OnboardingPage extends StatefulWidget {
  const OnboardingPage({
    super.key,
    required this.onGetStarted,
    required this.onSkip,
  });

  final Future<void> Function() onGetStarted;
  final Future<void> Function() onSkip;

  @override
  State<OnboardingPage> createState() => _OnboardingPageState();
}

class _OnboardingPageState extends State<OnboardingPage> {
  final PageController _pageController = PageController();
  int _currentPage = 0;
  bool _finishing = false;

  @override
  void dispose() {
    _pageController.dispose();
    super.dispose();
  }

  Future<void> _next() async {
    if (_finishing) return;
    if (_currentPage < 2) {
      await _pageController.nextPage(
        duration: const Duration(milliseconds: 320),
        curve: Curves.easeInOutCubic,
      );
      return;
    }
    await _finish(skip: false);
  }

  Future<void> _finish({required bool skip}) async {
    if (_finishing) return;
    setState(() => _finishing = true);
    try {
      if (skip) {
        await widget.onSkip();
      } else {
        await widget.onGetStarted();
      }
    } finally {
      if (mounted) setState(() => _finishing = false);
    }
  }

  @override
  Widget build(BuildContext context) {

    return Scaffold(
      backgroundColor: AppColors.surface,
      body: SafeArea(
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 560),
            child: Padding(
              padding: const EdgeInsets.fromLTRB(24, 16, 24, 20),
              child: Column(
                children: [
                  Row(
                    children: [
                      Icon(Icons.eco_rounded, color: AppColors.primary, size: 27),
                      const SizedBox(width: 8),
                      Text(
                        'AyurPlant',
                        style: TextStyle(
                          color: AppColors.text,
                          fontWeight: FontWeight.w800,
                          fontSize: 20,
                        ),
                      ),
                      const Spacer(),
                      if (_currentPage < 2)
                        TextButton(
                          onPressed: _finishing
                              ? null
                              : () => _finish(skip: true),
                          child: const Text('Skip'),
                        ),
                    ],
                  ),
                  const SizedBox(height: 12),
                  Expanded(
                    child: PageView(
                      controller: _pageController,
                      onPageChanged: (index) =>
                          setState(() => _currentPage = index),
                      children: const [
                        _OnboardingSlide(
                          index: 0,
                          title: 'Discover medicinal plants',
                          subtitle:
                              'Identify Sri Lankan medicinal plants using photos of leaves, seeds, or flowers.',
                          firstIcon: Icons.camera_alt_rounded,
                          firstTitle: 'Identify Plant',
                          firstDetail: 'Explore plant species from photos',
                          secondIcon: Icons.fact_check_outlined,
                          secondTitle: 'Assess Quality',
                          secondDetail: 'Examine supported plant quality indicators',
                        ),
                        _OnboardingSlide(
                          index: 1,
                          title: 'Learn and grow',
                          subtitle:
                              'Ask plant questions and explore recommendations for growing medicinal crops.',
                          firstIcon: Icons.forum_rounded,
                          firstTitle: 'Herbal AI Assistant',
                          firstDetail: 'Ask in Sinhala or English',
                          secondIcon: Icons.spa_rounded,
                          secondTitle: 'Cultivation Guide',
                          secondDetail: 'Explore suitable plants for your conditions',
                        ),
                        _OnboardingSlide(
                          index: 2,
                          title: 'Welcome to AyurPlant',
                          subtitle:
                              'Your companion for exploring Sri Lankan medicinal plants, their knowledge, and cultivation.',
                          firstIcon: Icons.eco_rounded,
                          firstTitle: 'Identify · Learn · Grow',
                          firstDetail: 'Explore nature through technology',
                          secondIcon: Icons.shield_outlined,
                          secondTitle: 'Explore responsibly',
                          secondDetail: 'Herbal information is educational, not medical advice',
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 12),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: List.generate(3, (index) {
                      final active = index == _currentPage;
                      return AnimatedContainer(
                        duration: const Duration(milliseconds: 240),
                        margin: const EdgeInsets.symmetric(horizontal: 4),
                        height: 7,
                        width: active ? 28 : 7,
                        decoration: BoxDecoration(
                          color: active ? AppColors.primary : AppColors.border,
                          borderRadius: BorderRadius.circular(99),
                        ),
                      );
                    }),
                  ),
                  const SizedBox(height: 20),
                  SizedBox(
                    width: double.infinity,
                    height: 54,
                    child: FilledButton.icon(
                      onPressed: _finishing ? null : _next,
                      style: FilledButton.styleFrom(
                        backgroundColor: AppColors.primary,
                        foregroundColor: const Color(0xFF12301D),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(16),
                        ),
                      ),
                      icon: _finishing
                          ? const SizedBox(
                              width: 18,
                              height: 18,
                              child: CircularProgressIndicator(strokeWidth: 2),
                            )
                          : Icon(
                              _currentPage == 2
                                  ? Icons.rocket_launch_outlined
                                  : Icons.arrow_forward_rounded,
                            ),
                      label: Text(
                        _currentPage == 2 ? 'Get Started' : 'Next',
                        style: const TextStyle(fontWeight: FontWeight.w800),
                      ),
                    ),
                  ),
                  if (_currentPage == 2) ...[
                    const SizedBox(height: 6),
                    TextButton(
                      onPressed: _finishing ? null : () => _finish(skip: false),
                      child: Text(
                        'Already have an account? Log in',
                        style: TextStyle(color: AppColors.muted),
                      ),
                    ),
                  ] else ...[
                    const SizedBox(height: 10),
                    Text(
                      'Swipe to explore',
                      style: TextStyle(color: AppColors.muted, fontSize: 12),
                    ),
                  ],
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _OnboardingSlide extends StatelessWidget {
  const _OnboardingSlide({
    required this.index,
    required this.title,
    required this.subtitle,
    required this.firstIcon,
    required this.firstTitle,
    required this.firstDetail,
    required this.secondIcon,
    required this.secondTitle,
    required this.secondDetail,
  });

  final int index;
  final String title;
  final String subtitle;
  final IconData firstIcon;
  final String firstTitle;
  final String firstDetail;
  final IconData secondIcon;
  final String secondTitle;
  final String secondDetail;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final illustrationHeight =
            (constraints.maxHeight * 0.42).clamp(150.0, 245.0).toDouble();
        return SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const SizedBox(height: 8),
              _Illustration(index: index, height: illustrationHeight),
              const SizedBox(height: 28),
              Text(
                title,
                textAlign: TextAlign.center,
                style: TextStyle(
                  color: AppColors.text,
                  fontWeight: FontWeight.w900,
                  fontSize: 27,
                  height: 1.16,
                ),
              ),
              const SizedBox(height: 12),
              Text(
                subtitle,
                textAlign: TextAlign.center,
                style: TextStyle(
                  color: AppColors.muted,
                  fontSize: 15,
                  height: 1.5,
                ),
              ),
              const SizedBox(height: 24),
              _FeatureRow(icon: firstIcon, title: firstTitle, detail: firstDetail),
              const SizedBox(height: 10),
              _FeatureRow(icon: secondIcon, title: secondTitle, detail: secondDetail),
              const SizedBox(height: 14),
            ],
          ),
        );
      },
    );
  }
}

/// Uses locally bundled botanical illustrations in the light design.
/// The images are assets: onboarding does not require Internet access.
class _Illustration extends StatelessWidget {
  const _Illustration({required this.index, required this.height});

  final int index;
  final double height;

  @override
  Widget build(BuildContext context) {
    final artwork = switch (index) {
      0 => 'onboarding_discover',
      1 => 'onboarding_learn',
      _ => 'onboarding_welcome',
    };
    final imagePath = 'assets/images/${artwork}_light.png';

    final background = switch (index) {
      0 => const Color(0xFFE1F6E8),
      1 => const Color(0xFFF4EACA),
      _ => const Color(0xFFE7F5EF),
    };
    final fallbackIcon = switch (index) {
      0 => Icons.local_florist_rounded,
      1 => Icons.menu_book_rounded,
      _ => Icons.eco_rounded,
    };
    final label = switch (index) {
      0 => 'A medicinal plant being identified with a phone camera',
      1 => 'Herbal reference books with an AI assistant',
      _ => 'The AyurPlant emblem over a green landscape',
    };

    return Semantics(
      image: true,
      label: label,
      child: Container(
        height: height,
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
        decoration: BoxDecoration(
          color: background,
          borderRadius: BorderRadius.circular(28),
        ),
        child: ClipRRect(
          borderRadius: BorderRadius.circular(22),
          child: Image.asset(
            imagePath,
            fit: BoxFit.contain,
            width: double.infinity,
            height: double.infinity,
            filterQuality: FilterQuality.high,
            gaplessPlayback: true,
            errorBuilder: (_, __, ___) => Center(
              child: Icon(
                fallbackIcon,
                color: const Color(0xFF329B56),
                size: 94,
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _FeatureRow extends StatelessWidget {
  const _FeatureRow({
    required this.icon,
    required this.title,
    required this.detail,
  });

  final IconData icon;
  final String title;
  final String detail;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 13, horizontal: 14),
      decoration: BoxDecoration(
        color: Colors.white,
        border: Border.all(color: AppColors.border),
        borderRadius: BorderRadius.circular(17),
      ),
      child: Row(
        children: [
          Container(
            height: 39,
            width: 39,
            decoration: BoxDecoration(
              color: AppColors.primary.withValues(alpha: 0.12),
              borderRadius: BorderRadius.circular(12),
            ),
            child: Icon(icon, size: 21, color: AppColors.primary),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: TextStyle(
                    color: AppColors.text,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  detail,
                  style: TextStyle(color: AppColors.muted, fontSize: 12),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

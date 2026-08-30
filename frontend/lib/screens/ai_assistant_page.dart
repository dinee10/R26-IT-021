import 'package:flutter/material.dart';

import '../theme/app_colors.dart';
import 'chat/general_public_chat_page.dart';
import 'chat/practitioner_chat_page.dart';
import 'chat/researcher_chat_page.dart';
import 'chat/student_chat_page.dart';

class _PersonaOption {
  final String label;
  final String description;
  final IconData icon;
  final Color color;
  final WidgetBuilder pageBuilder;

  const _PersonaOption({
    required this.label,
    required this.description,
    required this.icon,
    required this.color,
    required this.pageBuilder,
  });
}


class AiAssistantPage extends StatelessWidget {
  const AiAssistantPage({super.key});

  static final List<_PersonaOption> _options = [
    _PersonaOption(
      label: "General Public",
      description: "Simple, everyday explanations",
      icon: Icons.eco_outlined,
      color: AppColors.primary,
      pageBuilder: (_) => const GeneralPublicChatPage(),
    ),
    _PersonaOption(
      label: "Practitioner",
      description: "Clinical detail and safety notes",
      icon: Icons.medical_services_outlined,
      color: const Color(0xFF1E6F9F),
      pageBuilder: (_) => const PractitionerChatPage(),
    ),
    _PersonaOption(
      label: "Student",
      description: "Explanations for study and coursework",
      icon: Icons.school_outlined,
      color: const Color(0xFF8B5CF6),
      pageBuilder: (_) => const StudentChatPage(),
    ),
    _PersonaOption(
      label: "Researcher",
      description: "Evidence-forward, scientific detail",
      icon: Icons.science_outlined,
      color: const Color(0xFF2E5E4E),
      pageBuilder: (_) => const ResearcherChatPage(),
    ),
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text("Who's asking?"),
        centerTitle: false,
      ),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                "Pick how you'd like answers explained",
                style: TextStyle(
                  fontSize: 14,
                  color: AppColors.muted,
                  fontWeight: FontWeight.w500,
                ),
              ),
              const SizedBox(height: 16),
              Expanded(
                child: ListView.separated(
                  itemCount: _options.length,
                  separatorBuilder: (_, __) => const SizedBox(height: 12),
                  itemBuilder: (context, index) {
                    final option = _options[index];
                    return InkWell(
                      borderRadius: BorderRadius.circular(16),
                      onTap: () {
                        Navigator.push(
                          context,
                          MaterialPageRoute(builder: option.pageBuilder),
                        );
                      },
                      child: Container(
                        padding: const EdgeInsets.all(16),
                        decoration: BoxDecoration(
                          border: Border.all(color: AppColors.border),
                          borderRadius: BorderRadius.circular(16),
                        ),
                        child: Row(
                          children: [
                            Container(
                              padding: const EdgeInsets.all(10),
                              decoration: BoxDecoration(
                                color: option.color.withValues(alpha: 0.1),
                                borderRadius: BorderRadius.circular(12),
                              ),
                              child: Icon(option.icon, color: option.color),
                            ),
                            const SizedBox(width: 14),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    option.label,
                                    style: const TextStyle(
                                      fontWeight: FontWeight.bold,
                                      fontSize: 16,
                                      color: AppColors.text,
                                    ),
                                  ),
                                  const SizedBox(height: 2),
                                  Text(
                                    option.description,
                                    style: const TextStyle(
                                      fontSize: 13,
                                      color: AppColors.muted,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                            const Icon(Icons.chevron_right, color: AppColors.muted),
                          ],
                        ),
                      ),
                    );
                  },
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
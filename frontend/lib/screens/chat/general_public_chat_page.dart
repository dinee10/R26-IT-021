import 'package:flutter/material.dart';

import '../../theme/app_colors.dart';
import '../widgets/persona_chat_scaffold.dart';

class GeneralPublicChatPage extends StatelessWidget {
  const GeneralPublicChatPage({super.key});

  @override
  Widget build(BuildContext context) {
    return PersonaChatScaffold(
      personaLabel: "General Public",
      userTypeKey: "general_public",
      accentColor: AppColors.primary,
      icon: Icons.eco_outlined,
      greeting: "Ask about medicinal plants\nI'll keep it simple and easy to follow!",
      infoBanner: Container(
        width: double.infinity,
        color: AppColors.primary.withValues(alpha: 0.08),
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
        child: const Row(
          children: [
            Icon(Icons.info_outline, size: 16, color: AppColors.primary),
            SizedBox(width: 8),
            Expanded(
              child: Text(
                "Answers here use everyday language, not medical or botanical jargon.",
                style: TextStyle(fontSize: 12, color: AppColors.text),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
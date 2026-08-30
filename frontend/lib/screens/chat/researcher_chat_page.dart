
import 'package:flutter/material.dart';

import '../../theme/app_colors.dart';
import '../widgets/persona_chat_scaffold.dart';

class ResearcherChatPage extends StatelessWidget {
  const ResearcherChatPage({super.key});

  static const _accent = Color(0xFF2E5E4E);

  @override
  Widget build(BuildContext context) {
    return PersonaChatScaffold(
      personaLabel: "Researcher",
      userTypeKey: "researcher",
      accentColor: _accent,
      icon: Icons.science_outlined,
      greeting: "Ask about medicinal plants\nResponses favor evidence, scientific names, and source detail.",
      infoBanner: Container(
        width: double.infinity,
        color: _accent.withValues(alpha: 0.08),
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
        child: const Row(
          children: [
            Icon(Icons.biotech_outlined, size: 16, color: _accent),
            SizedBox(width: 8),
            Expanded(
              child: Text(
                "Prioritizes scientific evidence and terminology over simplified summaries.",
                style: TextStyle(fontSize: 12, color: AppColors.text),
              ),
            ),
          ],
        ),
      ),
    );
  }
}